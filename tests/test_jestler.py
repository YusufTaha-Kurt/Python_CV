import numpy as np
import pytest

from goru import jestler as j
from goru.jestler import Jest

from sentetik_el import dondur, sentetik_el

ACIK, KAPALI = True, False


@pytest.mark.parametrize(
    "parmaklar, beklenen",
    [
        ((KAPALI, KAPALI, KAPALI, KAPALI, KAPALI), Jest.YUMRUK),
        ((ACIK, ACIK, ACIK, ACIK, ACIK), Jest.AVUC),
        ((KAPALI, ACIK, KAPALI, KAPALI, KAPALI), Jest.ISARET),
        ((ACIK, ACIK, KAPALI, KAPALI, KAPALI), Jest.L_ISARETI),
        ((KAPALI, ACIK, ACIK, KAPALI, KAPALI), Jest.ZAFER),
        ((KAPALI, ACIK, KAPALI, KAPALI, ACIK), Jest.ROCK),
        ((ACIK, KAPALI, KAPALI, KAPALI, KAPALI), Jest.BASPARMAK_YUKARI),
        ((KAPALI, KAPALI, ACIK, KAPALI, KAPALI), Jest.BILINMIYOR),
    ],
)
def test_jest_tani(parmaklar, beklenen):
    noktalar = sentetik_el(parmaklar)
    assert j.parmak_durumlari(noktalar) == parmaklar
    assert j.jest_tani(noktalar) == beklenen


@pytest.mark.parametrize("derece", [-60, -30, 30, 60, 90])
def test_parmak_durumlari_donuse_dayanikli(derece):
    for parmaklar in [(ACIK,) * 5, (KAPALI,) * 5, (ACIK, ACIK, KAPALI, KAPALI, ACIK)]:
        assert j.parmak_durumlari(dondur(sentetik_el(parmaklar), derece)) == parmaklar


@pytest.mark.parametrize("olcek", [0.4, 1.0, 3.0])
def test_cimdik_orani_olcekten_bagimsiz(olcek):
    noktalar = sentetik_el() * olcek
    assert j.el_boyutu(noktalar) == pytest.approx(90 * olcek)
    assert j.cimdik_orani(noktalar) == pytest.approx(j.cimdik_orani(sentetik_el()))


def test_cimdik_orani_parmaklar_degince_sifir():
    noktalar = sentetik_el()
    noktalar[j.BAS_UCU] = noktalar[j.ISARET_UCU]
    assert j.cimdik_orani(noktalar) == pytest.approx(0.0)


def test_cimdik_histerezis():
    cimdik = j.CimdikAlgilayici(baslama=0.25, birakma=0.38)
    olaylar = [cimdik.guncelle(oran) for oran in [0.5, 0.3, 0.2, 0.3, 0.24, 0.37, 0.4, 0.3]]
    # 0.2'de başlar; eşik etrafındaki 0.3 / 0.24 / 0.37 dalgalanmaları bırakmaz; 0.4'te biter
    assert olaylar == [None, None, "basladi", None, None, None, "bitti", None]


def test_kararlilastirici_kenar_tetiklemeli():
    takip = j.JestKararlilastirici(sure=0.3)
    sonuclar = [takip.guncelle(Jest.YUMRUK, t) for t in np.arange(0, 2.0, 0.05)]
    # Yumruk 2 sn boyunca tutulsa da sadece BİR kez haber verilir (V1'deki tekrar eden toggle hatası)
    assert [s for s in sonuclar if s is not None] == [Jest.YUMRUK]
    assert takip.mevcut == Jest.YUMRUK


def test_kararlilastirici_kisa_titremeyi_yok_sayar():
    takip = j.JestKararlilastirici(sure=0.3)
    takip.guncelle(Jest.AVUC, 0.0)
    takip.guncelle(Jest.AVUC, 0.4)
    # 0.1 sn'lik yanlış tanıma kararlı jesti değiştirmemeli
    assert takip.guncelle(Jest.YUMRUK, 0.45) is None
    assert takip.guncelle(Jest.AVUC, 0.55) is None
    assert takip.mevcut == Jest.AVUC


def test_kaydirma_hizli_hareket():
    algilayici = j.KaydirmaAlgilayici(pencere=0.35, esik=1.6)
    sonuclar = [algilayici.guncelle((100 + 600 * t, 200), 90, t) for t in np.arange(0, 0.35, 1 / 30)]
    assert "sag" in sonuclar


def test_kaydirma_yavas_hareketi_saymaz():
    algilayici = j.KaydirmaAlgilayici(pencere=0.35, esik=1.6)
    sonuclar = [algilayici.guncelle((100 + 100 * t, 200), 90, t) for t in np.arange(0, 2, 1 / 30)]
    assert set(sonuclar) == {None}


def test_kaydirma_capraz_hareketi_saymaz():
    algilayici = j.KaydirmaAlgilayici(pencere=0.35, esik=1.6)
    sonuclar = [algilayici.guncelle((100 - 600 * t, 200 + 600 * t), 90, t) for t in np.arange(0, 0.35, 1 / 30)]
    assert set(sonuclar) == {None}
