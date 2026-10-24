"""Ders 6-7: Hologram masası. Elle tutulan, fırlatılan, büyütülen sanal nesneler.

Tüm etkileşim mantığı burada, kamera pikseli cinsinden çalışır; tarayıcı sadece
`Masa.durum()` çıktısını çizer (goru/hologram_web/). Böylece mantık kamera ve tarayıcı
olmadan, sentetik ellerle test edilebilir.

Ders 6:  tut-taşı, dokun (kartı aç / modeli patlat), fırlat, iki elle ölçekle,
         modeli tutup bekleyince döndür, boş çimdikle sürükleyerek patlat
Ders 7:  pençe ile uzaktan çekme, alkışla masayı toparlama

Etkileşim fikirleri barehands projesinden (jaredrhod, AGPL-3.0) esinlenmiştir; kod bu repo
için yeniden yazılmıştır. Ayrıntılar: docs/referanslar/barehands_analizi.md
"""

import math
import os
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from . import jestler as j
from .cimdik import CimdikAyarlari, GuvenilirCimdik
from .filtreler import OneEuroFiltre

# Uzunluklar kare genişliğine oranla, süreler saniye
DOKUNMA_SURESI = 0.3  # Bu süreden kısa ve az hareketli çimdik "dokunma" sayılır
DOKUNMA_HAREKETI = 0.03
FIRLATMA_HIZI = 0.25  # Kare genişliği / sn. Bırakma anındaki hız bunu aşarsa nesne fırlar
SURTUNME = 2.0  # 1/sn
SEKME = 0.6  # Kenara çarpınca korunan hız oranı
DONDURME_BEKLEMESI = 1.0  # Modeli tutup bu kadar sabit bekleyince döndürme moduna geçer
DONDURME_TOLERANSI = 0.025
DONME_HASSASIYETI = 15.0  # Radyan / kare genişliği
PATLATMA_ESIGI = 0.025  # Boş çimdik bu kadar yana gidince patlatma başlar
PATLATMA_MESAFESI = 0.27  # Bu kadar yana gitmek modeli tamamen açar
OLCEK_SINIRI = (0.4, 3.5)
# Ders 7
PENCE_POZ_KARESI = 14  # Pençe pozu bu kadar kare tutulmalı (~0.45 sn)
PENCE_ACIK_EL_SURESI = 0.9  # Pençe, son bu kadar saniye içinde açık elden oluşmalı
PENCE_KONI = 0.25  # Nişan konisinin genişliği (dik sapma / ileri mesafe)
PENCE_YAKIN = 0.125  # Bundan yakın nesneler pençeyle değil çimdikle alınır
PENCE_GERILIM_SURESI = 2.0  # Hedef bu kadar titremeden çekilemez
ALKIS_BEKLEME = 1.5


@dataclass
class Nesne:
    id: int
    tur: str  # "kart" | "gorsel" | "model"
    x: float
    y: float
    genislik: float
    yukseklik: float
    baslik: str = ""
    govde: str = ""
    kaynak: str = ""  # gorsel: URL, model: model türü ("reaktor", "kup")
    olcek: float = 1.0
    vx: float = 0.0
    vy: float = 0.0
    acik: bool = False  # Kart genişletilmiş mi
    don_x: float = 0.0
    don_y: float = 0.0
    patlama: float = 0.0
    patlama_hedef: float = 0.0
    titreme: float = 0.0  # Pençe gerilimi (0-1)
    mod: str = "serbest"  # serbest | tasi | don | olcek | cekiliyor | elde
    tutanlar: list = field(default_factory=list)
    cekici: str = None  # Nesneyi pençeyle çeken el
    ev: tuple = (0.0, 0.0)  # Toparlanınca döneceği yer
    _olcek0: tuple = (1.0, 1.0)

    def etiket(self):
        return self.baslik or self.kaynak or self.tur

    def boyut(self):
        uzama = 2.0 if (self.tur == "kart" and self.acik) else 1.0
        return self.genislik * self.olcek, self.yukseklik * self.olcek * uzama

    def sinir(self):
        g, y = self.boyut()
        return self.x - g / 2, self.y - y / 2, self.x + g / 2, self.y + y / 2

    def json(self):
        g, y = self.boyut()
        return {
            "id": self.id, "tur": self.tur, "x": round(self.x, 1), "y": round(self.y, 1),
            "g": round(g, 1), "h": round(y, 1), "baslik": self.baslik, "govde": self.govde,
            "kaynak": self.kaynak, "acik": self.acik, "don_x": round(self.don_x, 3),
            "don_y": round(self.don_y, 3), "patlama": round(self.patlama, 3),
            "titreme": round(self.titreme, 3), "mod": self.mod, "tutuluyor": bool(self.tutanlar),
        }


class _Pence:
    def __init__(self):
        self.faz = 0  # 0: boşta, 1: kurulu (nişan alıyor)
        self.poz = 0  # Pençe pozunun art arda görüldüğü kare sayısı (kaybedince 5 düşer)
        self.hedef = None
        self.isik_zamani = 0.0
        self.kayip_zamani = None
        self.yon = np.zeros(2)
        self.oranlar = deque()


class _El:
    def __init__(self, ayar):
        self.cimdik = GuvenilirCimdik(j.ISARET_UCU, ayar)
        self.filtre = OneEuroFiltre(min_kesim=1.0, beta=6.0)
        self.noktalar = None
        self.imlec = None
        self.gecmis = deque()  # (zaman, x, y): fırlatma hızı için
        self.tutulan = None
        self.ofset = np.zeros(2)
        self.kavrama_zamani = 0.0
        self.kavrama_noktasi = None
        self.sabit_zamani = 0.0  # Döndürme modu için "sabit bekleme" zamanlayıcısı
        self.sabit_noktasi = None
        self.don0 = None
        self.kazima = None  # Boş çimdikle patlatma durumu
        self.avuc_acik = False
        self.son_acik = -math.inf
        self.pence = _Pence()


def pence_pozu(n, icinde=False):
    """Pençe: işaret, orta ve yüzük kanca gibi kıvrık, serçe düz, başparmakla arası geniş.

    Giriş eşikleri sıkı, korunma eşikleri gevşek (histerezis): poz bir kez oturunca küçük
    titremeler onu bozmasın.
    """
    oran = j.cimdik_orani(n)
    c8, c12, c16, c20 = (j.kivrim(n, uc) for uc in (j.ISARET_UCU, j.ORTA_UCU, j.YUZUK_UCU, j.SERCE_UCU))
    ortalama = (c8 + c12 + c16) / 3

    def kanca(uc):  # 3D: uç-bilek / PIP-bilek. Kıvrık parmakta uç bileğe geri döner
        pip = j.PARMAKLAR[uc][1]
        return float(np.linalg.norm(n[uc] - n[j.BILEK]) / max(np.linalg.norm(n[pip] - n[j.BILEK]), 1e-6))

    kancalar = max(kanca(j.ISARET_UCU), kanca(j.ORTA_UCU), kanca(j.YUZUK_UCU))
    en_boy = j.avuc_en_boy(n)
    if icinde:
        return (0.68 < oran < 1.8 and c8 < 0.8 and c12 < 0.6 and c16 < 0.75 and ortalama < 0.55
                and c20 > -0.35 and en_boy > 0.48 and kancalar < 1.6)
    return (0.80 < oran < 1.45 and c8 < 0.6 and c12 < 0.35 and c16 < 0.55 and ortalama < 0.30
            and c20 > 0.1 and en_boy > 0.6 and kancalar < 1.5)


class Masa:
    def __init__(self, genislik=1280, yukseklik=720, ayarlar=None, pence=False, alkis=False, yol=None):
        self.w, self.h = genislik, yukseklik
        self.ayar = ayarlar or CimdikAyarlari()
        self.pence_acik = pence
        self.alkis_acik = alkis
        self.yol = yol
        self.nesneler = []
        self.mesajlar = deque(maxlen=6)
        self._eller = {}
        self._sonraki_id = 1
        self._yuva = 0
        self._zaman = 0.0
        self._son_zaman = None
        self._alkis_gecmisi = deque()
        self._son_alkis = -math.inf

    # --- İçerik ---

    def _ekle(self, nesne, x, y):
        if x is None or y is None:
            x, y = self._siradaki_yuva()
        nesne.x, nesne.y, nesne.ev = x, y, (x, y)
        self.nesneler.append(nesne)
        return nesne

    def _siradaki_yuva(self):
        i = self._yuva
        self._yuva += 1
        return self.w * (0.16 + 0.226 * (i % 4)), self.h * (0.24 + 0.46 * ((i // 4) % 2))

    def _yeni_id(self):
        self._sonraki_id += 1
        return self._sonraki_id - 1

    def kart_ekle(self, baslik, govde="", x=None, y=None):
        g = 0.2 * self.w
        return self._ekle(Nesne(self._yeni_id(), "kart", 0, 0, g, g * 0.62, baslik=baslik, govde=govde), x, y)

    def gorsel_ekle(self, kaynak, baslik="", x=None, y=None):
        g = 0.2 * self.w
        return self._ekle(Nesne(self._yeni_id(), "gorsel", 0, 0, g, g * 0.75, baslik=baslik, kaynak=kaynak), x, y)

    def model_ekle(self, tur="reaktor", x=None, y=None, boyut=0.17):
        g = boyut * self.w
        return self._ekle(Nesne(self._yeni_id(), "model", 0, 0, g, g, baslik=tur, kaynak=tur), x, y)

    def notlari_yukle(self, klasor):
        """Klasördeki .md dosyalarından kart üretir: ilk başlık = kart başlığı, gerisi = gövde."""
        for ad in sorted(os.listdir(klasor)):
            if ad.lower().endswith(".md"):
                with open(os.path.join(klasor, ad), encoding="utf-8") as dosya:
                    satirlar = [s.rstrip() for s in dosya.read().strip().splitlines()]
                baslik = satirlar[0].lstrip("# ").strip() if satirlar else ad
                self.kart_ekle(baslik, "\n".join(satirlar[1:]).strip())

    def boyutla(self, genislik, yukseklik):
        """Kamera beklenenden farklı çözünürlük verirse tüm masayı orantılı ölçekler."""
        if (genislik, yukseklik) == (self.w, self.h):
            return
        kx, ky = genislik / self.w, yukseklik / self.h
        for n in self.nesneler:
            n.x, n.y, n.ev = n.x * kx, n.y * ky, (n.ev[0] * kx, n.ev[1] * ky)
            n.genislik, n.yukseklik = n.genislik * kx, n.yukseklik * kx
        self.w, self.h = genislik, yukseklik
        self._eller.clear()

    def toparla(self):
        """Her şeyi bırak ve evine geri gönder."""
        for d in self._eller.values():
            d.tutulan, d.kazima = None, None
            self._pence_birak(d.pence)
        for n in self.nesneler:
            n.tutanlar.clear()
            n.mod, n.cekici = "serbest", None
            n.vx = n.vy = n.don_x = n.don_y = n.titreme = 0.0
            n.olcek, n.acik, n.patlama_hedef = 1.0, False, 0.0
            n.x, n.y = n.ev

    def komut(self, komut):
        """Dış komutlar (tarayıcı ya da başka bir uygulama). İzin listesi CanliYayin'da uygulanır."""
        if komut.get("a") == "kart_ekle":
            self.kart_ekle(str(komut.get("baslik", ""))[:80], str(komut.get("govde", ""))[:1200])
        elif komut.get("a") == "toparla":
            self.toparla()

    # --- Olaylar ---

    def _mesaj(self, metin):
        self.mesajlar.append((metin, self._zaman))

    def _olay(self, ad, nesne=None, mesaj=None, **veri):
        if mesaj:
            self._mesaj(mesaj)
        if self.yol is not None:
            if nesne is not None:
                veri.update(id=nesne.id, tur=nesne.tur, etiket=nesne.etiket())
            self.yol.yayinla(ad, **veri)

    # --- Ana güncelleme ---

    def guncelle(self, eller, zaman):
        """eller: `.taraf` ve `.noktalar` alanları olan nesneler (goru.el.El)."""
        dt = 0.0 if self._son_zaman is None else min(max(zaman - self._son_zaman, 0.0), 0.1)
        self._son_zaman = self._zaman = zaman
        gorulen = {e.taraf: e for e in eller}
        for anahtar in list(self._eller):
            if anahtar not in gorulen:
                self._el_kayboldu(anahtar)
        for anahtar, el in gorulen.items():
            if anahtar not in self._eller:
                self._eller[anahtar] = _El(self.ayar)
            self._el_guncelle(anahtar, self._eller[anahtar], el.noktalar, zaman, dt)
        self._iki_el_olcekle()
        if self.alkis_acik:
            self._alkis(zaman)
        self._fizik(dt)

    def _el_kayboldu(self, anahtar):
        d = self._eller.pop(anahtar)
        if d.tutulan is not None:
            self._birak(anahtar, d, self._zaman, iptal=True)
        self._pence_birak(d.pence)
        for n in self.nesneler:
            if n.cekici == anahtar:
                n.mod, n.cekici = "serbest", None

    def _el_guncelle(self, anahtar, d, n, zaman, dt):
        d.noktalar = n
        olay = d.cimdik.guncelle(n, zaman)
        ham = d.cimdik.nokta
        fx, fy = d.filtre((ham[0] / self.w, ham[1] / self.h), zaman)
        d.imlec = np.array([fx * self.w, fy * self.h])
        d.gecmis.append((zaman, d.imlec[0], d.imlec[1]))
        while len(d.gecmis) > 2 and zaman - d.gecmis[0][0] > 0.3:
            d.gecmis.popleft()

        acik_parmak = j.duz_parmak_sayisi(n)  # Kanca gibi kıvrık parmaklar sayılmaz (pençe açık el değildir)
        oran = d.cimdik.olcum["oran"]
        d.avuc_acik = acik_parmak >= 4 and oran > 0.8
        if d.avuc_acik or (acik_parmak >= 3 and oran > 0.7):
            d.son_acik = zaman

        if (olay == "basladi" and d.cimdik.kavrayabilir) or olay == "iyilesti":
            self._kavra(anahtar, d, zaman)
        elif olay in ("bitti", "iptal"):
            self._birak(anahtar, d, zaman, iptal=olay == "iptal")
            d.kazima = None

        if d.tutulan is not None:
            self._tasi(d, zaman)
        elif d.cimdik.kavrayabilir and d.kazima is not None:
            self._kazi(d)

        if self.pence_acik:
            self._pence(anahtar, d, zaman)
        self._cekilenler(anahtar, d, dt)

    # --- Ders 6: tut, taşı, bırak, fırlat ---

    def _isabet(self, nokta):
        pay = 0.012 * self.w
        for n in reversed(self.nesneler):  # Üstteki nesne önce
            x0, y0, x1, y1 = n.sinir()
            if x0 - pay <= nokta[0] <= x1 + pay and y0 - pay <= nokta[1] <= y1 + pay:
                return n
        return None

    def _kavra(self, anahtar, d, zaman):
        nesne = self._isabet(d.imlec)
        if nesne is None or len(nesne.tutanlar) >= 2 or nesne.mod == "cekiliyor":
            d.kazima = {}  # Boş çimdik: yana sürüklenirse patlatma
            return
        self.nesneler.remove(nesne)
        self.nesneler.append(nesne)  # Öne getir
        nesne.tutanlar.append(anahtar)
        nesne.vx = nesne.vy = 0.0
        nesne.cekici = None
        d.tutulan = nesne
        d.kavrama_zamani = d.sabit_zamani = zaman
        d.kavrama_noktasi = d.sabit_noktasi = d.imlec.copy()
        if len(nesne.tutanlar) == 1:
            nesne.mod = "tasi"
            d.ofset = np.array([nesne.x, nesne.y]) - d.imlec
        else:
            a, b = (self._eller[k].imlec for k in nesne.tutanlar)
            nesne.mod = "olcek"
            nesne._olcek0 = (max(float(np.linalg.norm(a - b)), 1.0), nesne.olcek)
        self._olay("hologram.tutuldu", nesne)

    def _birak(self, anahtar, d, zaman, iptal=False):
        nesne, d.tutulan = d.tutulan, None
        if nesne is None:
            return
        if anahtar in nesne.tutanlar:
            nesne.tutanlar.remove(anahtar)
        if nesne.tutanlar:  # Diğer el hâlâ tutuyor: tek elle taşımaya dön
            diger = self._eller[nesne.tutanlar[0]]
            nesne.mod = "tasi"
            diger.ofset = np.array([nesne.x, nesne.y]) - diger.imlec
            diger.sabit_zamani, diger.sabit_noktasi = zaman, diger.imlec.copy()
            return
        nesne.mod = "serbest"
        if iptal:
            return
        sure = zaman - d.kavrama_zamani
        hareket = float(np.linalg.norm(d.imlec - d.kavrama_noktasi))
        if sure < DOKUNMA_SURESI and hareket < DOKUNMA_HAREKETI * self.w:
            self._dokun(nesne)
            return
        vx, vy = self._tepe_hiz(d, zaman)
        hiz = math.hypot(vx, vy)
        if hiz > FIRLATMA_HIZI * self.w:
            nesne.vx, nesne.vy = vx, vy
            self._olay("hologram.firlatildi", nesne, hiz=round(hiz / self.w, 2))
        else:
            self._olay("hologram.birakildi", nesne)

    def _dokun(self, nesne):
        if nesne.tur == "model":
            nesne.patlama_hedef = 0.0 if nesne.patlama_hedef > 0.5 else 1.0
            mesaj = "model acildi" if nesne.patlama_hedef else "model kapandi"
        else:
            nesne.acik = not nesne.acik
            mesaj = None
        self._olay("hologram.dokunuldu", nesne, mesaj=mesaj)

    @staticmethod
    def _tepe_hiz(d, zaman):
        """Son 0.25 sn'deki en yüksek anlık hız: el bırakırken yavaşlasa da atış hızı korunur."""
        ornekler = [g for g in d.gecmis if zaman - g[0] <= 0.25]
        en_iyi = (0.0, 0.0)
        for (t0, x0, y0), (t1, x1, y1) in zip(ornekler, ornekler[1:]):
            if t1 > t0:
                v = ((x1 - x0) / (t1 - t0), (y1 - y0) / (t1 - t0))
                if math.hypot(*v) > math.hypot(*en_iyi):
                    en_iyi = v
        return en_iyi

    def _tasi(self, d, zaman):
        nesne = d.tutulan
        if nesne.mod == "tasi":
            if float(np.linalg.norm(d.imlec - d.sabit_noktasi)) > DONDURME_TOLERANSI * self.w:
                d.sabit_zamani, d.sabit_noktasi = zaman, d.imlec.copy()  # Hareket: zamanlayıcı yeniden
            elif nesne.tur == "model" and zaman - d.sabit_zamani > DONDURME_BEKLEMESI:
                nesne.mod = "don"
                d.don0 = (nesne.don_x, nesne.don_y, d.imlec.copy())
                self._olay("hologram.dondurme", nesne, mesaj="dondurme modu")
                return
            hedef = d.imlec + d.ofset
            nesne.x += (hedef[0] - nesne.x) * 0.6
            nesne.y += (hedef[1] - nesne.y) * 0.6
        elif nesne.mod == "don":
            don_x, don_y, p0 = d.don0
            nesne.don_y = don_y + (d.imlec[0] - p0[0]) / self.w * DONME_HASSASIYETI
            nesne.don_x = don_x + (d.imlec[1] - p0[1]) / self.w * DONME_HASSASIYETI

    def _kazi(self, d):
        """Hiçbir şeyi tutmayan çimdik yana sürüklenince en üstteki modelin parçaları açılır."""
        if "model" not in d.kazima:
            modeller = [n for n in self.nesneler if n.tur == "model"]
            m = modeller[-1] if modeller else None
            d.kazima = {"model": m, "x0": d.imlec[0], "taban": m.patlama if m else 0.0, "canli": False}
        m = d.kazima["model"]
        if m is None or m not in self.nesneler:
            return
        dx = d.imlec[0] - d.kazima["x0"]
        if not d.kazima["canli"] and abs(dx) > PATLATMA_ESIGI * self.w:
            d.kazima.update(canli=True, x0=d.imlec[0])  # Kasıtlı hareket: sıfır noktasını yeniden al
            return
        if d.kazima["canli"]:
            m.patlama = m.patlama_hedef = float(np.clip(d.kazima["taban"] + dx / (PATLATMA_MESAFESI * self.w), 0, 1))

    def _iki_el_olcekle(self):
        for n in self.nesneler:
            if n.mod == "olcek" and len(n.tutanlar) == 2:
                a, b = (self._eller[k].imlec for k in n.tutanlar)
                d0, s0 = n._olcek0
                n.olcek = float(np.clip(s0 * np.linalg.norm(a - b) / d0, *OLCEK_SINIRI))
                orta = (a + b) / 2
                n.x += (orta[0] - n.x) * 0.5
                n.y += (orta[1] - n.y) * 0.5

    def _fizik(self, dt):
        for n in self.nesneler:
            if n.mod == "serbest" and (n.vx or n.vy):
                n.x += n.vx * dt
                n.y += n.vy * dt
                sonum = math.exp(-SURTUNME * dt)
                n.vx *= sonum
                n.vy *= sonum
                g, y = n.boyut()
                if n.x < g / 2 or n.x > self.w - g / 2:
                    n.x = float(np.clip(n.x, g / 2, self.w - g / 2))
                    n.vx = -n.vx * SEKME
                if n.y < y / 2 or n.y > self.h - y / 2:
                    n.y = float(np.clip(n.y, y / 2, self.h - y / 2))
                    n.vy = -n.vy * SEKME
                if math.hypot(n.vx, n.vy) < 0.01 * self.w:
                    n.vx = n.vy = 0.0
            n.patlama += (n.patlama_hedef - n.patlama) * min(1.0, dt * 5)

    # --- Ders 7: pençe ve alkış ---

    def _pence_birak(self, p):
        if p.hedef is not None:
            p.hedef.titreme = 0.0
        p.faz, p.hedef, p.kayip_zamani = 0, None, None

    def _pence(self, anahtar, d, zaman):
        p, n = d.pence, d.noktalar
        tutuyor = d.tutulan is not None or any(x.cekici == anahtar for x in self.nesneler)
        poz = pence_pozu(n, icinde=p.faz > 0)
        p.poz = p.poz + 1 if poz else max(0, p.poz - 5)

        # Kapanma ("snap"): ağız ya çok kapalı ya da son 280 ms içinde hızla kapandı
        oran = d.cimdik.olcum["oran"]
        p.oranlar.append((zaman, oran))
        while p.oranlar and zaman - p.oranlar[0][0] > 0.4:
            p.oranlar.popleft()
        tepe = max(o for t, o in p.oranlar if zaman - t <= 0.28)
        kapandi = oran < 0.34 or (oran < 0.48 and tepe - oran > 0.22)

        if p.faz == 0:
            # Geçiş yasası: pençe bir şekil değil bir harekettir. Açık elden oluşmalı, yoksa
            # gevşek duran kıvrık bir el pençe sanılır.
            if (not tutuyor and p.poz >= PENCE_POZ_KARESI and self._isabet(d.imlec) is None
                    and zaman - d.son_acik < PENCE_ACIK_EL_SURESI):
                p.faz, p.hedef, p.kayip_zamani = 1, None, None
                self._mesaj("pence hazir: nisan al")
            return

        if poz:
            p.kayip_zamani = None
        elif p.kayip_zamani is None:
            p.kayip_zamani = zaman
        if tutuyor or (p.kayip_zamani is not None and not kapandi and zaman - p.kayip_zamani > 0.3):
            self._pence_birak(p)
            return

        if kapandi and p.hedef is not None:
            hedef = p.hedef
            erken = zaman - p.isik_zamani < PENCE_GERILIM_SURESI
            self._pence_birak(p)
            if erken:
                self._mesaj("cok erken: hedef 2 sn titresin")
            else:
                hedef.mod, hedef.cekici, hedef.vx, hedef.vy = "cekiliyor", anahtar, 0.0, 0.0
                self._olay("hologram.cekildi", hedef, mesaj=f"cekildi: {hedef.etiket()}")
            return

        if poz:
            # Nişan: başparmak-işaret çizgisinin normali, avuçtan dışarı doğru
            t4, t8 = n[j.BAS_UCU, :2], n[j.ISARET_UCU, :2]
            avuc = (n[j.ISARET_KOK, :2] + n[j.SERCE_KOK, :2]) / 2
            yon = np.array([-(t8[1] - t4[1]), t8[0] - t4[0]], dtype=float)
            if np.dot(yon, d.imlec - avuc) < 0:
                yon = -yon
            p.yon = yon / max(np.linalg.norm(yon), 1e-6)
            en_iyi, en_iyi_sapma = None, math.inf
            for x in self.nesneler:
                if x.tutanlar or x.mod in ("cekiliyor", "elde"):
                    continue
                v = np.array([x.x, x.y]) - d.imlec
                ileri = float(np.dot(v, p.yon))
                if np.linalg.norm(v) < PENCE_YAKIN * self.w or ileri <= 0:
                    continue
                sapma = abs(v[0] * p.yon[1] - v[1] * p.yon[0])
                if sapma <= PENCE_KONI * ileri and sapma < en_iyi_sapma:
                    en_iyi, en_iyi_sapma = x, sapma
            if en_iyi is not p.hedef:
                if p.hedef is not None:
                    p.hedef.titreme = 0.0
                p.hedef, p.isik_zamani = en_iyi, zaman
                if en_iyi is not None:
                    self._mesaj(f"nisan: {en_iyi.etiket()}")
        if p.hedef is not None:
            p.hedef.titreme = min(1.0, (zaman - p.isik_zamani) / 4.0)

    def _cekilenler(self, anahtar, d, dt):
        """Pençeyle çekilen nesne ele uçar, el açılana kadar elde taşınır."""
        for x in self.nesneler:
            if x.cekici != anahtar:
                continue
            fark = d.imlec - np.array([x.x, x.y])
            if x.mod == "cekiliyor":
                k = min(1.0, dt * 7)
                x.x += fark[0] * k
                x.y += fark[1] * k
                if np.linalg.norm(fark) < 0.025 * self.w:
                    x.mod = "elde"
            elif x.mod == "elde":
                x.x += fark[0] * 0.6
                x.y += fark[1] * 0.6
                if d.avuc_acik:
                    x.mod, x.cekici = "serbest", None
                    x.vx, x.vy = self._tepe_hiz(d, self._zaman)
                    self._olay("hologram.birakildi", x)

    def _alkis(self, zaman):
        eller = [d for d in self._eller.values() if d.noktalar is not None]
        if len(eller) < 2:
            self._alkis_gecmisi.clear()
            return
        a, b = eller[:2]

        def dik(d):  # 1: parmaklar tam yukarı bakıyor
            n = d.noktalar
            return (n[j.BILEK, 1] - n[j.ORTA_KOK, 1]) / j.el_boyutu(n)

        def merkez(d):
            return (d.noktalar[j.BILEK, :2] + d.noktalar[j.ORTA_KOK, :2]) / 2

        boy = (j.el_boyutu(a.noktalar) + j.el_boyutu(b.noktalar)) / 2
        mesafe = float(np.linalg.norm(merkez(a) - merkez(b))) / boy
        self._alkis_gecmisi.append((zaman, mesafe))
        while self._alkis_gecmisi and zaman - self._alkis_gecmisi[0][0] > 0.6:
            self._alkis_gecmisi.popleft()
        hizla_yaklasti = max(m for _, m in self._alkis_gecmisi) > 3.0
        if (mesafe < 1.3 and hizla_yaklasti and dik(a) > 0.6 and dik(b) > 0.6
                and zaman - a.son_acik < 0.5 and zaman - b.son_acik < 0.5
                and a.tutulan is None and b.tutulan is None and zaman - self._son_alkis > ALKIS_BEKLEME):
            self._son_alkis = zaman
            self._alkis_gecmisi.clear()
            self.toparla()
            self._olay("hologram.alkis", mesaj="alkis: masa toparlandi")

    # --- Tarayıcıya giden durum ---

    def durum(self):
        imlecler = []
        for anahtar, d in self._eller.items():
            if d.imlec is None:
                continue
            p = d.pence
            imlecler.append({
                "el": anahtar, "x": round(float(d.imlec[0]), 1), "y": round(float(d.imlec[1]), 1),
                "cimdik": d.cimdik.aktif, "kavrayabilir": d.cimdik.kavrayabilir, "hayalet": d.cimdik.hayalet,
                "tutuyor": d.tutulan is not None, "oran": round(d.cimdik.olcum.get("oran", 1.0), 2),
                "pence": {"hedef": p.hedef.id if p.hedef else None, "yon": [round(float(v), 3) for v in p.yon],
                          "gerilim": round(p.hedef.titreme, 2) if p.hedef else 0.0} if p.faz else None,
            })
        return {
            "boyut": [self.w, self.h],
            "nesneler": [n.json() for n in self.nesneler],
            "imlecler": imlecler,
            "mesajlar": [m for m, t in self.mesajlar if self._zaman - t < 2.5],
            "ozellikler": {"pence": self.pence_acik, "alkis": self.alkis_acik},
        }
