import time
from types import SimpleNamespace

import numpy as np

from goru.olaylar import OlayYolu
from goru.servis import Servis, ayarlari_yukle, varsayilan_ayarlar
from goru.yetenekler import Yetenek

DT = 1 / 30
KARE = np.zeros((72, 128, 3), np.uint8)


class SahteTakipci:
    def __init__(self, ad):
        self.ad = ad
        self.sonuc = []
        self.cagri = 0
        self.kapatildi = False

    def isle(self, kare, zaman):
        self.cagri += 1
        return self.sonuc

    def kapat(self):
        self.kapatildi = True


def yetenek_sinifi(ad, gerekenler=(), aralik=1, hata=False, sahip_gerekli=False, on_plan=False):
    class Sahte(Yetenek):
        def __init__(self, yol, ayar, sadece_izle):
            super().__init__(yol, ayar, sadece_izle)
            self.baglamlar = []
            self.sifirlama = 0

        def isle(self, b):
            if hata:
                raise RuntimeError("bozuk")
            self.baglamlar.append(b)

        def sifirla(self):
            self.sifirlama += 1

    Sahte.ad, Sahte.gerekenler, Sahte.aralik = ad, frozenset(gerekenler), aralik
    Sahte.sahip_gerekli, Sahte.on_plan = sahip_gerekli, on_plan
    return Sahte


def servis_kur(siniflar, acik=None, **ayar):
    ayarlar = varsayilan_ayarlar()
    ayarlar["yetenekler"] = {ad: {"acik": ad in (acik or siniflar)} for ad in siniflar}
    ayarlar.update(ayar)
    takipciler = {}

    def fabrika(ad):
        takipciler[ad] = SahteTakipci(ad)
        return takipciler[ad]

    yol = OlayYolu()
    olaylar = []
    yol.abone_ol(OlayYolu.HEPSI, olaylar.append)
    servis = Servis(ayarlar, yol=yol, yetenek_siniflari=siniflar, takipci_fabrikasi=fabrika)
    return servis, takipciler, olaylar


def test_sadece_gereken_modeller_calisir():
    siniflar = {"a": yetenek_sinifi("a", {"el"}), "b": yetenek_sinifi("b", {"yuz"}), "c": yetenek_sinifi("c", {"poz"})}
    servis, takipciler, _ = servis_kur(siniflar, acik={"a", "b"})
    for i in range(3):
        servis.adim(KARE, i * DT)
    assert sorted(takipciler) == ["el", "yuz"]  # poz isteyen yetenek kapalı: poz modeli hiç yüklenmedi
    assert takipciler["el"].cagri == 3 and len(servis.yetenekler["a"].baglamlar) == 3


def test_aralik_agir_yetenekleri_seyreltir():
    servis, _, _ = servis_kur({"agir": yetenek_sinifi("agir", aralik=3)})
    for i in range(9):
        servis.adim(KARE, i * DT)
    assert len(servis.yetenekler["agir"].baglamlar) == 3


def test_ust_uste_hata_veren_yetenek_kapatilir_servis_devam_eder():
    siniflar = {"bozuk": yetenek_sinifi("bozuk", hata=True), "saglam": yetenek_sinifi("saglam")}
    servis, _, olaylar = servis_kur(siniflar)
    for i in range(10):
        servis.adim(KARE, i * DT)
    assert "bozuk" not in servis.yetenekler and len(servis.yetenekler["saglam"].baglamlar) == 10
    assert [o.veri["yetenek"] for o in olaylar if o.ad == "servis.hata"] == ["bozuk"]


def test_komutlar():
    siniflar = {"a": yetenek_sinifi("a"), "b": yetenek_sinifi("b")}
    servis, _, olaylar = servis_kur(siniflar, acik={"a"})
    assert servis.komut({"a": "yetenek_ac", "ad": "b"}) and "b" in servis.yetenekler
    assert servis.komut({"a": "yetenek_kapat", "ad": "a"}) and "a" not in servis.yetenekler
    assert not servis.komut({"a": "yetenek_ac", "ad": "yok"})
    servis.komut({"a": "duraklat"})
    assert servis.duraklatildi and servis.yetenekler["b"].sifirlama == 1
    servis.komut({"a": "devam"})
    assert not servis.duraklatildi
    assert servis.durum()["kapali_yetenekler"] == ["a"]


def test_kimse_yokken_bekleme_modu():
    servis, takipciler, olaylar = servis_kur({"a": yetenek_sinifi("a", {"el"})})
    servis.adim(KARE, 0.0)
    takipciler["el"].sonuc = []  # Kimse yok
    t = 0.0
    while t < 16:
        t += DT
        servis.adim(KARE, t)
    assert servis.bekleme and not servis.islenmeli(t + 0.1) and servis.islenmeli(t + 0.6)
    takipciler["el"].sonuc = [SimpleNamespace(taraf="sag", noktalar=np.zeros((21, 3)))]
    servis.adim(KARE, t + 0.5)
    assert not servis.bekleme
    assert [o.veri["acik"] for o in olaylar if o.ad == "servis.bekleme"] == [True, False]


def test_sadece_sahip_modu():
    class SahteKapi(Yetenek):
        ad = "kapi"
        sahip_burada = False

        def isle(self, b):
            pass

    siniflar = {"kapi": SahteKapi, "fare": yetenek_sinifi("fare", sahip_gerekli=True),
                "yorgunluk": yetenek_sinifi("yorgunluk")}
    servis, _, _ = servis_kur(siniflar)
    servis.ayarlar["yetenekler"]["kapi"]["sadece_sahip"] = True
    servis.adim(KARE, 0.0)
    assert servis.yetenekler["fare"].baglamlar == [] and servis.yetenekler["fare"].sifirlama == 1
    assert len(servis.yetenekler["yorgunluk"].baglamlar) == 1  # Sahip gerektirmeyen çalışmaya devam eder
    SahteKapi.sahip_burada = True
    servis.adim(KARE, DT)
    assert len(servis.yetenekler["fare"].baglamlar) == 1


class YavasTakipci(SahteTakipci):
    """Gerçek modeller gibi çıkarım sırasında GIL'i bırakan (uyuyan) takipçi."""

    SURELER = {"el": 0.005, "yuz": 0.03}

    def isle(self, kare, zaman):
        time.sleep(self.SURELER[self.ad])
        return super().isle(kare, zaman)


def test_paralel_on_plan_agir_yetenegi_beklemez():
    from goru.servis import _ArkaIsci

    siniflar = {"fare": yetenek_sinifi("fare", {"el"}, on_plan=True), "yorgunluk": yetenek_sinifi("yorgunluk", {"yuz"})}
    ayarlar = varsayilan_ayarlar()
    ayarlar["yetenekler"] = {ad: {"acik": True} for ad in siniflar}
    servis = Servis(ayarlar, yetenek_siniflari=siniflar, takipci_fabrikasi=YavasTakipci)
    arka = _ArkaIsci(servis)
    t0 = time.perf_counter()
    for i in range(30):
        b = servis.adim(KARE, i * DT, grup="on")
        arka.ver(KARE, i * DT, b.eller if "el" in b.calisan else None)
    on_plan_suresi = time.perf_counter() - t0
    time.sleep(0.1)
    arka.durdur()

    assert len(servis.yetenekler["fare"].baglamlar) == 30
    islenen = len(servis.yetenekler["yorgunluk"].baglamlar)
    # Sıralı çalışsaydı 30 x (5 + 30) ms = 1.05 sn sürerdi; ön plan ağır modeli beklemedi
    assert on_plan_suresi < 0.5
    assert 2 <= islenen < 30 and arka.atlanan > 0  # Arka plan yetişemedi, eski kareleri atladı
    assert servis._takipciler["el"].cagri == 30  # El modeli sadece ön planda, bir kez çalıştı


def test_ayarlari_yukle_birlestirir(tmp_path):
    yol = tmp_path / "ayar.json"
    yol.write_text('{"kaynak": "video.mp4", "yetenekler": {"durus": {"acik": true}}}', encoding="utf-8")
    ayarlar = ayarlari_yukle(yol)
    assert ayarlar["kaynak"] == "video.mp4" and ayarlar["yetenekler"]["durus"]["acik"]
    assert ayarlar["yetenekler"]["kontrol"]["acik"] and ayarlar["http"]["port"] == 8770  # Varsayılanlar korunur
