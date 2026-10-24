"""Ders 17: 7/24 servis. Seçilen yetenekler tek kamera ve tek süreçte, arka planda çalışır.

Başka bir uygulamaya bu modülü eklemenin iki yolu:

  Aynı süreç (Python):
      from goru.servis import Servis, varsayilan_ayarlar
      servis = Servis(varsayilan_ayarlar())
      servis.yol.abone_ol("jest.degisti", lambda olay: ...)
      servis.baslat()          # arka planda (thread)
      ...
      servis.durdur()

  Ayrı süreç (herhangi bir dil): Yerel HTTP arayüzü
      GET  http://127.0.0.1:8770/olaylar     Tüm olaylar, canlı (Server-Sent Events)
      GET  http://127.0.0.1:8770/durum.json  Anlık durum
      POST http://127.0.0.1:8770/komut       {"a": "duraklat" | "devam" | "yetenek_ac" | "yetenek_kapat", "ad": ...}

İki iş parçacığı:
  Ön plan    Akıcılık isteyen yetenekler (el ile fare / medya / pencere) her karede çalışır.
  Arka plan  Ağır ve yavaş değişen yetenekler (yorgunluk, duruş, mimik, kapı, nesne) en güncel
             kareyi alır; yetişemezse eski kareler atlanır ama ön plan hiç beklemez.
             MediaPipe çıkarım sırasında GIL'i bıraktığı için ikisi gerçekten paralel çalışır.

Dayanıklılık: Kamera koparsa yeniden bağlanır. Bir yetenek üst üste hata verirse kapatılır,
servis çalışmaya devam eder. Kimse görünmüyorsa enerji tasarrufu için kare hızı düşer.
"""

import contextlib
import copy
import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field

from .olaylar import JsonlKaydedici, OlayYolu

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_KLASORU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servis_web")
MAX_HATA = 5
IZINLI_KOMUTLAR = {"duraklat", "devam", "yetenek_ac", "yetenek_kapat"}

VARSAYILAN_AYARLAR = {
    "kaynak": 0,
    "cozunurluk": [960, 540],
    "sadece_izle": False,
    "onizleme": False,
    "paralel": True,
    "http": {"acik": True, "port": 8770},
    "kayit_klasoru": os.path.join(KOK, "servis_kayitlari"),
    "tasarruf": {"bekleme_suresi": 15.0, "bekleme_fps": 2.0},
    "yetenekler": {
        "kontrol": {"acik": True, "el": "sag"},
        "yorgunluk": {"acik": True, "alarm": False},
        "durus": {"acik": False, "alarm": False},
        "mimik": {"acik": False, "eylemler": False},
        "kapi": {"acik": False, "sadece_sahip": True, "windows_kilitle": False, "kilit_suresi": 60},
        "nesne": {"acik": False, "siniflar": None},
    },
}

log = logging.getLogger("goru.servis")


def varsayilan_ayarlar():
    return copy.deepcopy(VARSAYILAN_AYARLAR)


def ayarlari_yukle(yol):
    """JSON ayar dosyasını varsayılanların üstüne birleştirir (eksik anahtarlar varsayılan kalır)."""
    ayarlar = varsayilan_ayarlar()
    if yol and os.path.exists(yol):
        with open(yol, encoding="utf-8") as dosya:
            _birlestir(ayarlar, json.load(dosya))
    return ayarlar


def _birlestir(hedef, kaynak):
    for anahtar, deger in kaynak.items():
        if isinstance(deger, dict) and isinstance(hedef.get(anahtar), dict):
            _birlestir(hedef[anahtar], deger)
        else:
            hedef[anahtar] = deger


@dataclass
class Baglam:
    """Bir karede yeteneklere verilen her şey. Çalışmayan takipçilerin listesi boştur."""

    kare: object
    zaman: float
    eller: list = field(default_factory=list)
    yuzler: list = field(default_factory=list)
    pozlar: list = field(default_factory=list)
    jest: object = None  # jest(taraf) -> Jest: JestYayincisi'nin o el için kararlı jesti
    calisan: set = field(default_factory=set)  # Bu karede çalışan takipçiler


class _ArkaIsci:
    """Ağır yetenekleri ayrı bir iş parçacığında çalıştırır. Her zaman EN GÜNCEL kareyi işler."""

    def __init__(self, servis):
        self.servis = servis
        self.islem_ms = 0.0
        self.islenen = 0
        self.atlanan = 0
        self._is = None
        self._dur = False
        self._kosul = threading.Condition()
        self.thread = threading.Thread(target=self._dongu, daemon=True, name="goru-arka")
        self.thread.start()

    def ver(self, kare, zaman, eller):
        with self._kosul:
            if self._is is not None:
                self.atlanan += 1  # Önceki kare henüz işlenmedi: yenisiyle değiştir
            self._is = (kare, zaman, eller)
            self._kosul.notify()

    def _dongu(self):
        while True:
            with self._kosul:
                self._kosul.wait_for(lambda: self._is is not None or self._dur)
                if self._dur:
                    return
                (kare, zaman, eller), self._is = self._is, None
            t0 = time.perf_counter()
            try:
                self.servis.adim(kare, zaman, grup="arka", eller=eller)
            except Exception:
                log.exception("Arka plan adımı başarısız")
            self.islem_ms = 0.9 * self.islem_ms + 0.1 * (time.perf_counter() - t0) * 1000
            self.islenen += 1

    def durdur(self):
        with self._kosul:
            self._dur = True
            self._kosul.notify()
        self.thread.join(timeout=5)


class Servis:
    def __init__(self, ayarlar=None, yol=None, yetenek_siniflari=None, takipci_fabrikasi=None):
        from .yetenekler import YETENEKLER

        self.ayarlar = ayarlar or varsayilan_ayarlar()
        self.yol = yol or OlayYolu()
        self.sadece_izle = self.ayarlar.get("sadece_izle", False)
        self._siniflar = yetenek_siniflari or YETENEKLER
        self._takipci_fabrikasi = takipci_fabrikasi or _gercek_takipci
        self._takipciler = {}
        self.yetenekler = {}  # ad -> Yetenek (açık olanlar)
        self._yetenek_kilitleri = {}  # ad -> Lock: isle() ile kapat() aynı anda çalışmasın
        self._hatalar = {}
        self._kilit = threading.RLock()  # Yetenek sözlüğü, sayaçlar, takipçi oluşturma
        self._sayac = {None: 0, "on": 0, "arka": 0}
        self._durdur = threading.Event()
        self._thread = None
        self._arka = None
        self._yayin = None
        self._http_abonesi = None
        self.url = None
        self._kaydedici = None
        self.calisiyor = False
        self.duraklatildi = False
        self.bekleme = False
        self.kare_no = 0
        self.fps = 0.0
        self.islem_ms = 0.0
        self._son_varlik = None
        self._son_islenen = -1e9
        self._son_durum_yayini = 0.0
        self._baslangic = time.time()
        self._yayinci = None
        for ad, ayar in self.ayarlar["yetenekler"].items():
            if ayar.get("acik"):
                self._yetenek_ac(ad)

    # --- Yetenek yönetimi ---

    def _yetenek_ac(self, ad):
        with self._kilit:
            if ad in self.yetenekler or ad not in self._siniflar:
                return False
            try:
                yetenek = self._siniflar[ad](self.yol, self.ayarlar["yetenekler"].get(ad, {}), self.sadece_izle)
            except Exception as hata:
                log.exception("Yetenek açılamadı: %s", ad)
                self.yol.yayinla("servis.hata", yetenek=ad, hata=str(hata))
                return False
            self._yetenek_kilitleri[ad] = threading.Lock()
            self._hatalar[ad] = 0
            self.yetenekler[ad] = yetenek
        self.yol.yayinla("servis.yetenek", ad=ad, acik=True)
        return True

    def _yetenek_kapat(self, ad, neden="komut"):
        with self._kilit:
            yetenek = self.yetenekler.pop(ad, None)
            kilit = self._yetenek_kilitleri.get(ad) or contextlib.nullcontext()
        if yetenek is None:
            return False
        with kilit:  # Başka iş parçacığı tam o an isle() içindeyse bitmesini bekle
            try:
                yetenek.kapat()
            except Exception:
                log.exception("Yetenek kapatılırken hata: %s", ad)
        self.yol.yayinla("servis.yetenek", ad=ad, acik=False, neden=neden)
        return True

    def komut(self, komut):
        """Dış komut: {"a": "duraklat" | "devam" | "yetenek_ac" | "yetenek_kapat", "ad": ...}"""
        a = komut.get("a")
        if a == "yetenek_ac":
            return self._yetenek_ac(komut.get("ad"))
        if a == "yetenek_kapat":
            return self._yetenek_kapat(komut.get("ad"))
        if a == "duraklat":
            self.duraklatildi = True
            for ad, yetenek in list(self.yetenekler.items()):
                with self._yetenek_kilitleri[ad]:
                    yetenek.sifirla()
        elif a == "devam":
            self.duraklatildi = False
        else:
            return False
        self.yol.yayinla("servis.komut", a=a)
        return True

    # --- Bir karenin işlenmesi ---

    def _takipci(self, ad):
        with self._kilit:
            if ad not in self._takipciler:
                self._takipciler[ad] = self._takipci_fabrikasi(ad)
            return self._takipciler[ad]

    def gerekenler(self, grup=None):
        with self._kilit:
            secilen = [y for y in self.yetenekler.values() if grup is None or y.on_plan == (grup == "on")]
        return set().union(*(y.gerekenler for y in secilen)) if secilen else set()

    def sahip_burada(self):
        """Kapı bekçisi "sadece sahip" modundaysa sahip var mı; değilse None (kısıt yok)."""
        kapi = self.yetenekler.get("kapi")
        if kapi is None or not self.ayarlar["yetenekler"].get("kapi", {}).get("sadece_sahip", True):
            return None
        return kapi.sahip_burada

    def adim(self, kare, zaman, grup=None, eller=None):
        """Tek bir kareyi işler.

        grup: None = tüm yetenekler (tek iş parçacığı), "on" = ön plan, "arka" = arka plan.
        eller: Ön planın bu kare için bulduğu eller (arka plan el modelini ikinci kez çalıştırmasın).
        """
        from .jestler import JestYayincisi

        with self._kilit:
            if self._yayinci is None:
                self._yayinci = JestYayincisi(self.yol)
            sayac = self._sayac[grup]
            self._sayac[grup] += 1
            # Sadece bu karede sırası gelen yeteneklerin istediği modeller çalışır: 3 karede bir
            # çalışan duruş yeteneği varsa poz modeli de 3 karede bir çalışır (işlemci tasarrufu)
            sirasi_gelen = [(ad, y) for ad, y in self.yetenekler.items()
                            if (grup is None or y.on_plan == (grup == "on")) and sayac % y.aralik == 0]
            sahip = self.sahip_burada()
        gerekenler = set().union(*(y.gerekenler for _, y in sirasi_gelen)) if sirasi_gelen else set()

        b = Baglam(kare, zaman, jest=self._yayinci.jest)
        if eller is not None:
            b.eller = eller
        elif "el" in gerekenler:
            b.eller = self._takipci("el").isle(kare, zaman)
            b.calisan.add("el")
            self._yayinci.guncelle(b.eller, zaman)
        if "yuz" in gerekenler:
            b.yuzler = self._takipci("yuz").isle(kare, zaman)
            b.calisan.add("yuz")
        if "poz" in gerekenler:
            b.pozlar = self._takipci("poz").isle(kare, zaman)
            b.calisan.add("poz")
        if b.calisan:
            self._varlik_guncelle(bool(b.eller or b.yuzler or b.pozlar), zaman)
        elif grup != "arka" and not self.gerekenler():
            self._varlik_guncelle(True, zaman)  # Hiçbir yetenek görüntü modeli istemiyor: bekleme yok

        kapatilacak = []
        for ad, yetenek in sirasi_gelen:
            with self._yetenek_kilitleri[ad]:
                if self.yetenekler.get(ad) is not yetenek:
                    continue  # Bu arada kapatıldı
                if yetenek.sahip_gerekli and sahip is False:
                    yetenek.sifirla()
                    continue
                try:
                    yetenek.isle(b)
                    self._hatalar[ad] = 0
                except Exception as hata:
                    self._hatalar[ad] += 1
                    log.exception("Yetenek hatası (%s, %d. kez)", ad, self._hatalar[ad])
                    if self._hatalar[ad] >= MAX_HATA:
                        self.yol.yayinla("servis.hata", yetenek=ad, hata=str(hata))
                        kapatilacak.append(ad)
        for ad in kapatilacak:
            self._yetenek_kapat(ad, neden="ust uste hata")
        if grup != "arka":
            self.kare_no += 1
            self._son_islenen = zaman
        return b

    def _varlik_guncelle(self, biri_var, zaman):
        """Enerji tasarrufu: Kimse görünmüyorsa bekleme moduna geç."""
        with self._kilit:
            if self._son_varlik is None or biri_var:
                self._son_varlik = max(zaman, self._son_varlik or zaman)
            bekleme = zaman - self._son_varlik > self.ayarlar["tasarruf"]["bekleme_suresi"]
            degisti = bekleme != self.bekleme
            self.bekleme = bekleme
        if degisti:
            self.yol.yayinla("servis.bekleme", acik=bekleme)

    def islenmeli(self, zaman):
        """Bekleme modunda sadece saniyede `bekleme_fps` kare işlenir."""
        if not self.bekleme:
            return True
        return zaman - self._son_islenen >= 1.0 / self.ayarlar["tasarruf"]["bekleme_fps"]

    def durum(self):
        with self._kilit:
            yetenekler = dict(self.yetenekler)
        return {
            "calisiyor": self.calisiyor,
            "duraklatildi": self.duraklatildi,
            "bekleme": self.bekleme,
            "fps": round(self.fps, 1),
            "islem_ms": round(self.islem_ms, 1),
            "arka_ms": round(self._arka.islem_ms, 1) if self._arka else None,
            "arka_atlanan": self._arka.atlanan if self._arka else 0,
            "kare": self.kare_no,
            "sure_sn": round(time.time() - self._baslangic),
            "takipciler": sorted(self._takipciler),
            "yetenekler": {ad: y.durum() for ad, y in yetenekler.items()},
            "kapali_yetenekler": sorted(set(self._siniflar) - set(yetenekler)),
            "sahip_burada": self.sahip_burada(),
        }

    # --- Çalıştırma ---

    def _hazirla(self):
        klasor = self.ayarlar.get("kayit_klasoru")
        if klasor:
            os.makedirs(klasor, exist_ok=True)
            self._kaydedici = JsonlKaydedici(os.path.join(klasor, time.strftime("olaylar_%Y%m%d.jsonl")))
            self.yol.abone_ol(OlayYolu.HEPSI, self._kaydedici)
        http = self.ayarlar.get("http", {})
        if http.get("acik"):
            from .web import CanliYayin

            self._yayin = CanliYayin(WEB_KLASORU, port=http.get("port", 8770), izinli_komutlar=IZINLI_KOMUTLAR)
            self.url = self._yayin.baslat()
            self._http_abonesi = lambda olay: self._yayin.olay_yayinla(asdict(olay))
            self.yol.abone_ol(OlayYolu.HEPSI, self._http_abonesi)
            log.info("Kontrol paneli ve HTTP arayüzü: %s", self.url)
        if self.ayarlar.get("paralel", True):
            self._arka = _ArkaIsci(self)

    def calistir(self, kare_limiti=None):
        """Bloklayan ana döngü (durdur() çağrılana ya da kaynak bitene kadar)."""
        from .hud import FpsSayaci
        from .kamera import Kamera

        self._hazirla()
        genislik, yukseklik = self.ayarlar.get("cozunurluk", [960, 540])
        kamera = Kamera(self.ayarlar.get("kaynak", 0), genislik=genislik, yukseklik=yukseklik, yeniden_baglan=True)
        fps = FpsSayaci()
        self.calisiyor = True
        self.yol.yayinla("servis.basladi", yetenekler=sorted(self.yetenekler), paralel=self._arka is not None)
        try:
            while not self._durdur.is_set():
                if self._yayin is not None:
                    for k in self._yayin.komutlari_al():
                        self.komut(k)
                    if time.monotonic() - self._son_durum_yayini > 1.0:
                        self._son_durum_yayini = time.monotonic()
                        self._yayin.durum_yayinla(self.durum())
                if self.duraklatildi:
                    self._durdur.wait(0.2)
                    continue
                kare = kamera.oku(zaman_asimi=1.0)
                if kare is None:
                    if kamera.bitti:
                        break
                    continue
                zaman = kamera.zaman
                if not self.islenmeli(zaman):
                    continue
                t0 = time.perf_counter()
                if self._arka is not None:
                    b = self.adim(kare, zaman, grup="on")
                    self._arka.ver(kare, zaman, b.eller if "el" in b.calisan else None)
                else:
                    b = self.adim(kare, zaman)
                self.islem_ms = 0.9 * self.islem_ms + 0.1 * (time.perf_counter() - t0) * 1000
                self.fps = fps.tik()
                if self.ayarlar.get("onizleme"):
                    self._onizleme(b)
                if kare_limiti is not None and self.kare_no >= kare_limiti:
                    break
        finally:
            kamera.kapat()
            self._kapat()

    def _onizleme(self, b):
        import cv2

        from . import hud

        kare = b.kare.copy()
        for el in b.eller:
            hud.iskelet_ciz(kare, el.noktalar)
        hud.panel(kare, [f"{ad}: {y.durum()}" for ad, y in list(self.yetenekler.items())][:6]
                  + [f"FPS {self.fps:.0f}  on plan {self.islem_ms:.0f} ms" + ("  BEKLEME" if self.bekleme else "")],
                  baslik="PYTHON CV SERVIS")
        cv2.imshow("Python CV Servis", kare)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self._durdur.set()

    def baslat(self):
        """Servisi arka planda (thread) başlatır."""
        self._durdur.clear()
        self._thread = threading.Thread(target=self.calistir, daemon=True, name="goru-servis")
        self._thread.start()
        return self

    def durdur(self, bekle=5.0):
        self._durdur.set()
        if self._thread is not None and threading.current_thread() is not self._thread:
            self._thread.join(timeout=bekle)

    def _kapat(self):
        self.calisiyor = False
        if self._arka is not None:
            self._arka.durdur()
        for ad in list(self.yetenekler):
            self._yetenek_kapat(ad, neden="servis kapaniyor")
        for takipci in self._takipciler.values():
            try:
                takipci.kapat()
            except Exception:
                pass
        self._takipciler.clear()
        self.yol.yayinla("servis.durdu")
        if self._yayin is not None:
            self._yayin.durum_yayinla(self.durum())
            self.yol.abonelikten_cik(OlayYolu.HEPSI, self._http_abonesi)
            self._yayin.durdur()
            self._yayin = None
        if self._kaydedici is not None:
            self.yol.abonelikten_cik(OlayYolu.HEPSI, self._kaydedici)
            self._kaydedici.kapat()
            self._kaydedici = None
        if self.ayarlar.get("onizleme"):
            import cv2

            cv2.destroyAllWindows()


def _gercek_takipci(ad):
    if ad == "el":
        from .el import ElTakipci

        return ElTakipci(max_el=2)
    if ad == "yuz":
        from .yuz import YuzTakipci

        return YuzTakipci()
    if ad == "poz":
        from .poz import PozTakipci

        return PozTakipci()
    raise ValueError(f"Bilinmeyen takipçi: {ad}")
