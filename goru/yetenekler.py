"""Ders 17: Servisin yetenekleri. Her biri önceki derslerden birinin servis içinde çalışan hali.

Bir yetenek her kare `isle(baglam)` ile çağrılır. Hangi takip modellerine ihtiyaç duyduğunu
`gerekenler` ile söyler ("el", "yuz", "poz"); servis sadece açık yeteneklerin istediği
modelleri çalıştırır. Sonuçlarını olay olarak yayınlar.

Yeni bir yetenek eklemek: `Yetenek`ten türet, `isle`yi yaz, YETENEKLER sözlüğüne ekle.
"""

import os
import sys
import threading

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bip(frekans=1000):
    """Sesli uyarı (sadece Windows). Ayrı iş parçacığında çalar, servisi bekletmez."""
    if sys.platform == "win32":
        import winsound

        threading.Thread(target=winsound.Beep, args=(frekans, 300), daemon=True).start()


class Yetenek:
    """Tüm yeteneklerin atası. Alt sınıf `isle(b)` yazar; `b` o karenin Baglam'ıdır (kare, eller, yüzler...)."""

    ad = "yetenek"
    gerekenler = frozenset()
    aralik = 1  # Kaç karede bir çalışır (ağır yetenekler için > 1)
    sahip_gerekli = False  # Kapı bekçisi "sadece sahip" modundayken sahip yokken durur
    on_plan = False  # True: ön plan iş parçacığında her kare (akıcılık); False: arka planda

    def __init__(self, yol, ayar, sadece_izle):
        self.yol = yol
        self.ayar = ayar
        self.sadece_izle = sadece_izle

    def isle(self, b):
        """Her kare (ya da `aralik` karede bir) çağrılır. Alt sınıf doldurur."""
        raise NotImplementedError

    def sifirla(self):
        """Sahip ayrıldığında / yetenek kapatıldığında: basılı tuşları bırak vb."""

    def durum(self):
        """Kontrol panelinde gösterilecek sözlük."""
        return {}

    def kapat(self):
        """Yetenek kapatılırken çağrılır (kaynakları bırak)."""
        self.sifirla()


class KontrolYetenegi(Yetenek):
    """Ders 8: Fare / medya / pencere modları, diğer elin parmak sayısıyla mod seçimi."""

    ad = "kontrol"
    gerekenler = frozenset({"el"})
    sahip_gerekli = True
    on_plan = True  # Fare her karede, hiçbir ağır modeli beklemeden

    def __init__(self, yol, ayar, sadece_izle):
        super().__init__(yol, ayar, sadece_izle)
        from .cimdik import CimdikAyarlari
        from .fare import ElFaresi, PyAutoGuiFare, SahteFare
        from .kisayollar import PencereKontrol, PyAutoGuiKlavye, SahteKlavye
        from .medya import MedyaKontrol
        from .modlar import ModSecici

        self.el = ayar.get("el", "sag")
        self.mod_eli = "sol" if self.el == "sag" else "sag"
        self.surucu = None
        if not sadece_izle:
            from .imlec import ImlecSurucu

            self.surucu = ImlecSurucu()
            self.surucu.baslat()
        fare = SahteFare() if sadece_izle else PyAutoGuiFare()
        klavye = SahteKlavye() if sadece_izle else PyAutoGuiKlavye()
        cimdik_ayari = CimdikAyarlari.yukle(os.path.join(KOK, "ayarlar", "cimdik.json"))
        self.faresi = ElFaresi(fare, cimdik_ayari, surucu=self.surucu, ekran=ayar.get("ekran"))
        self.medya = MedyaKontrol(yol, el=self.el, sadece_izle=sadece_izle)
        self.pencere = PencereKontrol(yol, el=self.el, klavye=klavye, fare=fare)
        self.secici = ModSecici(["FARE", "MEDYA", "PENCERE"], yol=yol)
        self.uyku = False
        yol.abone_ol("jest.degisti", self._yumruk)

    def _yumruk(self, olay):
        """Kontrol elinde yumruk: uyku modunu aç / kapat (uyurken hiçbir eylem yapılmaz)."""
        if olay.veri.get("el") == self.el and olay.veri["jest"] == "yumruk" and not self.faresi.cimdik_aktif:
            self.uyku = not self.uyku
            self.faresi.sifirla()
            self.yol.yayinla("kontrol.uyku", acik=self.uyku)

    def isle(self, b):
        """Kontrol eli fareyi / medyayı / pencereyi yönetir; mod elinin parmak sayısı modu seçer."""
        kontrol = next((e for e in b.eller if e.taraf == self.el), None)
        secen = next((e for e in b.eller if e.taraf == self.mod_eli), None)
        onceki = self.secici.mod
        self.secici.guncelle(secen, b.zaman)
        if onceki == "FARE" and self.secici.mod != "FARE":
            self.faresi.sifirla()
        self.medya.aktif = self.secici.mod == "MEDYA" and not self.uyku
        self.pencere.aktif = self.secici.mod == "PENCERE" and not self.uyku
        if self.secici.mod == "FARE" and not self.uyku:
            self.faresi.isle(kontrol, b.zaman, (b.kare.shape[1], b.kare.shape[0]))
        self.medya.isle(kontrol, b.zaman)
        self.pencere.isle(kontrol, b.jest(self.el), b.zaman)

    def sifirla(self):
        """Sahip ayrılınca basılı fare tuşunu bırakır ve medya / pencere kontrolünü kapatır."""
        self.faresi.sifirla()
        self.medya.aktif = self.pencere.aktif = False

    def durum(self):
        """Panelde görünen: hangi mod seçili, uyku modu açık mı."""
        return {"mod": self.secici.mod, "uyku": self.uyku}

    def kapat(self):
        """Fareyi bırakır ve 144 Hz imleç iş parçacığını durdurur."""
        self.sifirla()
        if self.surucu:
            self.surucu.durdur()


class YorgunlukYetenegi(Yetenek):
    """Ders 10: Göz kırpma, PERCLOS ve esneme ile yorgunluk uyarısı."""

    ad = "yorgunluk"
    gerekenler = frozenset({"yuz"})
    aralik = 2  # 15 Hz göz kırpmayı yakalamaya yeter

    def __init__(self, yol, ayar, sadece_izle):
        super().__init__(yol, ayar, sadece_izle)
        from .goz import GozKirpmaAlgilayici, YorgunlukIzleyici

        self.goz = GozKirpmaAlgilayici()
        self.izleyici = YorgunlukIzleyici(perclos_esigi=ayar.get("perclos_esigi", 0.15))

    def isle(self, b):
        """Göz kırpmayı izler, PERCLOS / esneme hesaplar; uyarıları `yorgunluk.uyari` olarak yayınlar."""
        if not b.yuzler:
            return
        yuz = b.yuzler[0]
        olaylar = self.goz.guncelle(yuz.noktalar, b.zaman)
        for uyari in self.izleyici.guncelle(self.goz.ikisi_kapali, olaylar, yuz.ifadeler.get("jawOpen", 0.0), b.zaman):
            self.yol.yayinla("yorgunluk.uyari", tur=uyari, perclos=round(self.izleyici.perclos, 3))
            if self.ayar.get("alarm") and uyari != "esneme" and not self.sadece_izle:
                _bip(1200)

    def durum(self):
        """Panelde görünen: son 1 dakikadaki PERCLOS ve dakikadaki göz kırpma sayısı."""
        return {"perclos": round(self.izleyici.perclos, 3), "kirpma_dk": round(self.izleyici.kirpma_hizi, 1)}


class MimikYetenegi(Yetenek):
    """Ders 11: Yüz ifadeleri. Varsayılan olarak sadece olay yayınlar; 'eylemler': true ile komut çalıştırır."""

    ad = "mimik"
    gerekenler = frozenset({"yuz", "el"})
    aralik = 2
    sahip_gerekli = True

    def __init__(self, yol, ayar, sadece_izle):
        super().__init__(yol, ayar, sadece_izle)
        from .mimik import MimikAlgilayici

        self.mimik = MimikAlgilayici()
        self.mimik.kalibre_et()

    def isle(self, b):
        """İfade skorlarını nötr tabana göre ölçekler; tetiklenen ifadeyi `mimik.ifade` olarak yayınlar."""
        if not b.yuzler:
            return
        from .mimik import el_yuzu_kapatiyor

        engel = el_yuzu_kapatiyor(b.yuzler[0], b.eller or [])
        for ifade in self.mimik.guncelle(b.yuzler[0].ifadeler, b.zaman, engel=engel):
            self.yol.yayinla("mimik.ifade", ifade=ifade)
            if self.ayar.get("eylemler") and not self.sadece_izle:
                self._eylem(ifade)

    def _eylem(self, ifade):
        """Ayarlarda `eylemler: true` ise ifadeyi gerçek komuta çevirir (ağız aç → oynat, dudak büz → sessiz)."""
        from .ses import medya_tusu

        if ifade == "agiz_acma":
            medya_tusu("playpause")
        elif ifade == "dudak_buzme":
            medya_tusu("volumemute")


class DurusYetenegi(Yetenek):
    """Ders 16: Duruş bekçisi ve vücut jestleri."""

    ad = "durus"
    gerekenler = frozenset({"poz"})
    aralik = 3  # Duruş yavaş değişir

    def __init__(self, yol, ayar, sadece_izle):
        super().__init__(yol, ayar, sadece_izle)
        from .egzersiz import DurusBekcisi, VucutJestleri

        self.durus = DurusBekcisi(uyari_suresi=ayar.get("uyari_suresi", 20.0), uyari_araligi=ayar.get("uyari_araligi", 300.0))
        self.jestler = VucutJestleri()

    def isle(self, b):
        """Duruşu izler (kambur / eğik omuz → `durus.uyari`) ve vücut jestlerini (`vucut.jest`) yayınlar."""
        if not b.pozlar:
            return
        for uyari in self.durus.guncelle(b.pozlar[0], b.zaman):
            self.yol.yayinla("durus.uyari", tur=uyari)
            if self.ayar.get("alarm") and not self.sadece_izle:
                _bip(880)
        jest = self.jestler.guncelle(b.pozlar[0], b.zaman)
        if jest:
            self.yol.yayinla("vucut.jest", jest=jest)

    def durum(self):
        """Panelde görünen: duruş kalibre edildi mi, şu an kambur / eğik mi."""
        return {"kalibre": self.durus.taban is not None, **{k: bool(v) for k, v in self.durus.durum().items()}}


class KapiYetenegi(Yetenek):
    """Ders 14: Kapı bekçisi. "sadece_sahip" açıksa diğer yetenekler sahip yokken durur."""

    ad = "kapi"
    aralik = 2  # Yüz tanıma her 2 karede bir

    def __init__(self, yol, ayar, sadece_izle):
        super().__init__(yol, ayar, sadece_izle)
        from .kapi import KapiBekcisi
        from .kimlik import KimlikVeritabani, YuzTanima

        self.veritabani = KimlikVeritabani(ayar.get("kimlikler", os.path.join(KOK, "kimlikler")))
        self.tanima = YuzTanima()
        sahipler = ayar.get("sahipler") or self.veritabani.isimler
        self.kapi = KapiBekcisi(sahipler, yol=yol, kilit_suresi=ayar.get("kilit_suresi", 60.0))
        if ayar.get("windows_kilitle") and not sadece_izle:
            yol.abone_ol("kapi.kilitlendi", lambda _: self._windows_kilitle())

    @staticmethod
    def _windows_kilitle():
        """Windows oturumunu kilitler (Win+L ile aynı)."""
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.LockWorkStation()

    @property
    def gerekenler(self):
        """Dinamik: MediaPipe yüz modeli sadece canlılık testi sırasında istenir (yüz TANIMA ayrı bir modeldir)."""
        from .kapi import DOGRULANIYOR

        # MediaPipe yüz modeli sadece canlılık testi sırasında gerekir
        return frozenset({"yuz"}) if self.kapi.durum == DOGRULANIYOR else frozenset()

    @property
    def sahip_burada(self):
        """Kapı açık mı? Servis bunu diğer yetenekleri durdurmak / başlatmak için kullanır."""
        return self.kapi.sahip_burada

    def isle(self, b):
        """Karedeki en çok 3 yüzü tanır, kimlikleri kapı bekçisine bildirir."""
        satirlar = self.tanima.bul(b.kare)[:3]
        kimlikler = [self.veritabani.tani(self.tanima.gomme(b.kare, s))[0] for s in satirlar]
        self.kapi.guncelle(kimlikler, b.yuzler[0] if b.yuzler else None, b.zaman)

    def durum(self):
        """Panelde görünen: kapı durumu (kilitli / dogrulaniyor / acik) ve kişi."""
        return {"durum": self.kapi.durum, "kisi": self.kapi.kisi}


class NesneYetenegi(Yetenek):
    """Ders 15: Nesne tespiti ve takibi (ağır: 3 karede bir)."""

    ad = "nesne"
    aralik = 3

    def __init__(self, yol, ayar, sadece_izle):
        super().__init__(yol, ayar, sadece_izle)
        from .nesne import NesneDedektoru
        from .takip import IoUTakipci

        self.dedektor = NesneDedektoru(skor_esigi=ayar.get("esik", 0.5), izinli=ayar.get("siniflar"))
        self.takipci = IoUTakipci(max_kayip=10)
        self.gorunenler = []

    def isle(self, b):
        """Nesneleri bul, ID ver; yeni görülen ve kaybolan nesneler için olay yayınla."""
        from .nesne import TURKCE

        self.gorunenler = self.takipci.guncelle(self.dedektor.isle(b.kare, b.zaman))
        for iz in self.takipci.yeni:
            self.yol.yayinla("nesne.goruldu", id=iz.id, nesne=TURKCE.get(iz.etiket, iz.etiket))
        for iz in self.takipci.biten:
            self.yol.yayinla("nesne.kayboldu", id=iz.id, nesne=TURKCE.get(iz.etiket, iz.etiket))

    def durum(self):
        """Panelde görünen: şu an görünen nesne türleri."""
        return {"nesneler": sorted({iz.etiket for iz in self.gorunenler})}

    def kapat(self):
        """Nesne modelini serbest bırakır."""
        self.dedektor.kapat()


# Servisin tanıdığı yetenekler: ad → sınıf. Yeni yetenek eklemek için sınıfını yazıp buraya ekle.
YETENEKLER = {y.ad: y for y in (KontrolYetenegi, YorgunlukYetenegi, MimikYetenegi, DurusYetenegi, KapiYetenegi,
                                NesneYetenegi)}
