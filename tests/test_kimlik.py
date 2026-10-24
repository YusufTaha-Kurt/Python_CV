import random
from types import SimpleNamespace

import numpy as np
import pytest

from goru.canlilik import CanlilikTesti
from goru.kapi import ACIK, DOGRULANIYOR, KILITLI, KapiBekcisi
from goru.kimlik import KayitToplayici, KimlikVeritabani, guvenli_isim
from goru.olaylar import OlayYolu

from test_yuz import donusum, goz_yuzu

DT = 1 / 30


def birim(v):
    return v / np.linalg.norm(v)


def kisi_vektorleri(tohum, adet, gurultu=0.25):
    """Aynı kişinin farklı fotoğraflarını taklit eden, ortak bir merkez etrafında vektörler."""
    rastgele = np.random.default_rng(tohum)
    merkez = birim(rastgele.normal(size=128))
    return [birim(merkez + gurultu * birim(rastgele.normal(size=128))) for _ in range(adet)]


def test_veritabani_tanir_reddeder_ve_kaydeder(tmp_path):
    db = KimlikVeritabani(tmp_path / "kimlikler")
    ali, ayse = kisi_vektorleri(1, 6), kisi_vektorleri(2, 6)
    db.ekle("Ali", ali[:5])
    db.ekle("Ayşe", ayse[:5])
    assert db.tani(ali[5])[0] == "Ali" and db.tani(ayse[5])[0] == "Ayşe"
    yabanci = kisi_vektorleri(3, 1)[0]
    isim, benzerlik = db.tani(yabanci)
    assert isim is None and benzerlik < db.esik

    yeniden = KimlikVeritabani(tmp_path / "kimlikler")  # Diskten geri yükle
    assert yeniden.isimler == ["Ali", "Ayşe"] and len(yeniden.kisiler["Ali"]) == 5
    yeniden.sil("Ali")
    assert KimlikVeritabani(tmp_path / "kimlikler").isimler == ["Ayşe"]


@pytest.mark.parametrize("isim, beklenen", [("Yusuf Taha", "Yusuf Taha"), ("../../etc", "etc"), ("ç-ö_ü", "ç-ö_ü")])
def test_guvenli_isim(isim, beklenen):
    assert guvenli_isim(isim) == beklenen


def test_guvenli_isim_bos():
    with pytest.raises(ValueError):
        guvenli_isim("../")


def test_kayit_toplayici_cesitlilik_ister():
    toplayici = KayitToplayici(hedef=3, cesitlilik=0.93)
    satir = np.array([0, 0, 120, 120] + [0] * 10 + [0.95])
    v = kisi_vektorleri(5, 3, gurultu=0.6)
    assert toplayici.dene(v[0], satir)
    assert not toplayici.dene(v[0], satir)  # Aynısı: atlanır
    assert not toplayici.dene(v[1], np.array([0, 0, 40, 40] + [0] * 10 + [0.95]))  # Çok küçük yüz
    assert toplayici.dene(v[1], satir) and toplayici.dene(v[2], satir) and toplayici.tamam


# --- Canlılık ---


def yuz(ear=0.3, gulumseme=0.0, agiz=0.0, yaw=0.0):
    return SimpleNamespace(
        noktalar=goz_yuzu(ear, ear),
        ifadeler={"mouthSmileLeft": gulumseme, "mouthSmileRight": gulumseme, "jawOpen": agiz},
        donusum=donusum(yaw=yaw),
    )


GOREV_HAREKETI = {
    "goz_kirp": [yuz(0.08)] * 3 + [yuz()] * 3,
    "gulumse": [yuz(gulumseme=0.8)] * 3,
    "agzi_ac": [yuz(agiz=0.7)] * 3,
    "basi_sola": [yuz(yaw=-25)] * 3,
    "basi_saga": [yuz(yaw=25)] * 3,
}


def oynat(test, kareler, t):
    for k in kareler:
        test.guncelle(k, t)
        t += DT
    return t


def test_canli_kisi_testi_gecer():
    test = CanlilikTesti(adim_sayisi=5, rastgele=random.Random(0))
    test.baslat(0.0)
    t = oynat(test, [yuz()] * 20, 0.0)  # Göz algılayıcısı ısınsın
    for gorev in list(test.gorevler):
        assert test.gorev == gorev
        t = oynat(test, GOREV_HAREKETI[gorev] + [yuz()] * 5, t)
    assert test.sonuc == "gecti"


@pytest.mark.parametrize("sabit", [yuz(), yuz(gulumseme=0.8), yuz(agiz=0.7), yuz(yaw=-30)])
def test_fotograf_testi_gecemez(sabit):
    """Sabit bir yüz (gülümseyen ya da ağzı açık bir fotoğraf bile) hiçbir görevi geçemez."""
    for tohum in range(5):
        test = CanlilikTesti(adim_sayisi=3, adim_suresi=2.0, rastgele=random.Random(tohum))
        test.baslat(0.0)
        oynat(test, [sabit] * 90, 0.0)
        assert test.sonuc == "kaldi" and test.adim == 0 and "zaman asimi" in test.neden


def test_yuz_kaybolursa_kalir():
    test = CanlilikTesti()
    test.baslat(0.0)
    oynat(test, [None] * 40, 0.0)
    assert test.sonuc == "kaldi" and test.neden == "yuz kayboldu"


# --- Kapı bekçisi ---


class SahteCanlilik:
    def __init__(self, sonuc_zamani, sonuc):
        self.sonuc_zamani, self.sonuc_, self.neden = sonuc_zamani, sonuc, "sahte"
        self.baslangic = None

    def baslat(self, zaman):
        self.baslangic = zaman

    def guncelle(self, yuz, zaman):
        return self.sonuc_ if zaman - self.baslangic >= self.sonuc_zamani else None


def kapi_oynat(kapi, kimlikler, saniye, t):
    for _ in range(int(saniye * 30)):
        kapi.guncelle(kimlikler, None, t)
        t += DT
    return t


def test_kapi_acilir_ve_sahip_gidince_kilitlenir():
    yol = OlayYolu()
    olaylar = []
    yol.abone_ol(OlayYolu.HEPSI, olaylar.append)
    kapi = KapiBekcisi({"Ali"}, yol=yol, kilit_suresi=5, canlilik=SahteCanlilik(2.0, "gecti"))
    t = kapi_oynat(kapi, ["Ali"], 0.5, 0.0)
    assert kapi.durum == KILITLI  # 1 sn tanınmadan doğrulamaya geçmez
    t = kapi_oynat(kapi, ["Ali"], 1.0, t)
    assert kapi.durum == DOGRULANIYOR
    t = kapi_oynat(kapi, ["Ali"], 2.5, t)
    assert kapi.durum == ACIK and kapi.sahip_burada and kapi.kisi == "Ali"
    t = kapi_oynat(kapi, [], 4.0, t)
    assert kapi.durum == ACIK  # Kısa süre ayrılmak kilitlemez
    t = kapi_oynat(kapi, [], 2.0, t)
    assert kapi.durum == KILITLI
    assert [o.ad for o in olaylar] == ["kapi.dogrulaniyor", "kapi.acildi", "kapi.kilitlendi"]


def test_canlilik_kalirsa_reddeder_ve_bekletir():
    yol = OlayYolu()
    olaylar = []
    yol.abone_ol(OlayYolu.HEPSI, olaylar.append)
    kapi = KapiBekcisi({"Ali"}, yol=yol, red_beklemesi=3.0, canlilik=SahteCanlilik(1.0, "kaldi"))
    t = kapi_oynat(kapi, ["Ali"], 2.5, 0.0)
    assert kapi.durum == KILITLI and olaylar[-1].ad == "kapi.reddedildi"
    t = kapi_oynat(kapi, ["Ali"], 2.0, t)
    assert kapi.durum == KILITLI  # Red sonrası bekleme süresinde yeniden denenmez


def test_yabanci_uyarisi_ve_yabanci_kapiyi_acamaz():
    yol = OlayYolu()
    olaylar = []
    yol.abone_ol("kapi.yabanci", olaylar.append)
    kapi = KapiBekcisi({"Ali"}, yol=yol, yabanci_araligi=30)
    kapi_oynat(kapi, [None], 10.0, 0.0)
    assert len(olaylar) == 1 and kapi.durum == KILITLI
