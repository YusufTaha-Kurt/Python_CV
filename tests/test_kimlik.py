import random
from types import SimpleNamespace

import numpy as np
import pytest

from goru.canlilik import CanlilikTesti
from goru.kapi import ACIK, DOGRULANIYOR, KILITLI, KapiBekcisi
from goru.kimlik import KimlikVeritabani, YonluKayit, guvenli_isim, yuz_yonu
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


def yunet_satiri(yatay=0.0, dikey=0.0, boyut=120):
    """Sentetik YuNet satırı: gözler 60 px aralıklı; burun yatayda `yatay` göz arası,
    dikeyde göz-ağız arasının `0.5 + dikey` kadarı aşağıda."""
    goz1, goz2 = (100, 100), (160, 100)
    burun = (130 + 60 * yatay, 100 + 60 * (0.5 + dikey))
    agiz1, agiz2 = (110, 160), (150, 160)
    return np.array([70, 60, boyut, boyut, *goz1, *goz2, *burun, *agiz1, *agiz2, 0.95], dtype=np.float32)


def test_yuz_yonu():
    assert yuz_yonu(yunet_satiri()) == pytest.approx((0.0, 0.5))
    assert yuz_yonu(yunet_satiri(yatay=-0.2, dikey=0.1)) == pytest.approx((-0.2, 0.6))


def test_yonlu_kayit_adim_adim_ilerler():
    kayit = YonluKayit()
    v = iter(kisi_vektorleri(5, 40, gurultu=0.6))
    t = 0.0

    def dene(satir):
        nonlocal t
        t += 0.1
        return kayit.dene(next(v), satir, t)

    assert kayit.komut == "Kameraya duz bak"
    assert not dene(yunet_satiri(boyut=40))  # Çok küçük yüz
    assert all(dene(yunet_satiri()) for _ in range(3))
    assert kayit.adimlar[kayit.adim][0] == "sol"
    assert not dene(yunet_satiri(yatay=0.2))  # Yanlış yön: alınmaz
    assert dene(yunet_satiri(yatay=-0.2)) and dene(yunet_satiri(yatay=-0.2))
    assert dene(yunet_satiri(yatay=0.2)) and dene(yunet_satiri(yatay=0.2))
    assert dene(yunet_satiri(dikey=-0.12)) and dene(yunet_satiri(dikey=-0.12))
    assert dene(yunet_satiri(dikey=0.12)) and dene(yunet_satiri(dikey=0.12))
    assert kayit.tamam and len(kayit.ornekler) == kayit.hedef == 11


def test_yonlu_kayit_aci_yakalanamazsa_takilmaz():
    """Kullanıcı başını yeterince çeviremese de adım süresi dolunca örnek alınır."""
    kayit = YonluKayit(adim_suresi=8.0)
    v = kisi_vektorleri(6, 10, gurultu=0.6)
    for i in range(3):
        kayit.dene(v[i], yunet_satiri(), i * 0.1)
    assert not kayit.dene(v[3], yunet_satiri(yatay=-0.03), 1.0)  # Adım başladı, açı yetersiz
    assert not kayit.dene(v[4], yunet_satiri(yatay=-0.03), 5.0)
    assert kayit.dene(v[5], yunet_satiri(yatay=-0.03), 9.5)  # 8 sn doldu


def test_yonlu_kayit_ayni_kareyi_almaz():
    kayit = YonluKayit()
    v = kisi_vektorleri(7, 1)[0]
    assert kayit.dene(v, yunet_satiri(), 0.0)
    assert not kayit.dene(v, yunet_satiri(), 0.1)


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
