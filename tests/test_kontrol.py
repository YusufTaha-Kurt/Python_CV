from types import SimpleNamespace

import numpy as np
import pytest

from goru import jestler as j
from goru.cizim import HavaTuvali
from goru.fare import ElFaresi, SahteFare
from goru.kisayollar import Kaydirici, PencereKontrol, SahteKlavye
from goru.modlar import ModSecici
from goru.olaylar import OlayYolu

from sentetik_el import sentetik_cimdik, sentetik_el, sentetik_pence

DT = 1 / 30
ACIK = (True,) * 5
ISARET = (False, True, False, False, False)
ZAFER = (False, True, True, False, False)


def el(noktalar, dx=0.0, dy=0.0, taraf="sag"):
    n = noktalar.copy()
    n[:, 0] += dx
    n[:, 1] += dy
    return SimpleNamespace(taraf=taraf, noktalar=n)


def test_duz_parmak_sayisi():
    assert j.duz_parmak_sayisi(sentetik_el(ACIK)) == 4
    assert j.duz_parmak_sayisi(sentetik_el(ZAFER)) == 2
    assert j.duz_parmak_sayisi(sentetik_el((False,) * 5)) == 0
    # Pençede kancalar bileğe uzak kalsa da düz sayılmaz (sadece serçe düz)
    assert j.duz_parmak_sayisi(sentetik_pence()) == 1
    assert sum(j.parmak_durumlari(sentetik_pence())[1:]) == 4  # Basit kural bunu "açık el" sanar


# --- Kaydırma ---


def test_kaydirici_dogal_yon_ve_miktar():
    k = Kaydirici(hassasiyet=1500)
    toplam = sum(k.guncelle(400 + 90 * i / 30, 90, i * DT) for i in range(31))  # 1 el boyu aşağı
    toplam += sum(k.guncelle(490, 90, (31 + i) * DT) for i in range(15))  # Dur, filtre yetişsin
    assert toplam == pytest.approx(1500, abs=60)


def test_kaydirici_sabit_elde_kaydirmaz_ve_ters_yon():
    k = Kaydirici()
    rastgele = np.random.default_rng(0)
    assert sum(k.guncelle(400 + rastgele.normal(0, 0.3), 90, i * DT) for i in range(90)) == 0
    k2 = Kaydirici(dogal=False)
    assert sum(k2.guncelle(400 + 3 * i, 90, i * DT) for i in range(30)) < 0


def test_pencere_kontrol_jestler_ve_aktiflik():
    yol, klavye, fare = OlayYolu(), SahteKlavye(), SahteFare()
    pencere = PencereKontrol(yol, el="sag", klavye=klavye, fare=fare)
    yol.yayinla("jest.degisti", el="sag", jest="basparmak_yukari")
    yol.yayinla("jest.kaydirma", el="sag", yon="sol")
    yol.yayinla("jest.degisti", el="sol", jest="rock")  # Diğer el: yok sayılır
    pencere.aktif = False
    yol.yayinla("jest.degisti", el="sag", jest="rock")  # Mod kapalı: yok sayılır
    assert klavye.basilanlar == ["win+up", "ctrl+win+right"]


def test_pencere_zafer_ile_kaydirir():
    yol, fare = OlayYolu(), SahteFare()
    pencere = PencereKontrol(yol, klavye=SahteKlavye(), fare=fare)
    for i in range(40):
        pencere.isle(el(sentetik_el(ZAFER), dy=3 * i), j.Jest.ZAFER, i * DT)
    assert fare.eylemler and all(e.startswith("kaydir ") and int(e.split()[1]) > 0 for e in fare.eylemler)
    fare.eylemler.clear()
    for i in range(40):  # Başka jestle hareket kaydırmaz
        pencere.isle(el(sentetik_el(ACIK), dy=3 * i), j.Jest.AVUC, (40 + i) * DT)
    assert fare.eylemler == []


# --- Mod seçici ---


def test_mod_secici_parmak_sayisiyla():
    yol = OlayYolu()
    olaylar = []
    yol.abone_ol("mod.degisti", olaylar.append)
    secici = ModSecici(["FARE", "MEDYA", "PENCERE"], yol=yol, sure=0.6)
    sonuclar = [secici.guncelle(el(sentetik_el(ZAFER), taraf="sol"), i * DT) for i in range(25)]
    assert secici.mod == "MEDYA" and sonuclar.count("MEDYA") == 1
    for i in range(40):  # Açık avuç ve yumruk modu değiştirmez
        secici.guncelle(el(sentetik_el(ACIK), taraf="sol"), 1 + i * DT)
        secici.guncelle(el(sentetik_el((False,) * 5), taraf="sol"), 1 + i * DT)
    assert secici.mod == "MEDYA"
    assert [o.veri for o in olaylar] == [{"mod": "MEDYA", "onceki": "FARE"}]


def test_mod_secici_kisa_gosterimi_yok_sayar():
    secici = ModSecici(["FARE", "MEDYA", "PENCERE"], sure=0.6)
    for i in range(10):  # 0.33 sn
        secici.guncelle(el(sentetik_el(ISARET), taraf="sol"), i * DT)
        secici.guncelle(el(sentetik_el((False, True, True, True, False)), taraf="sol"), i * DT)
    assert secici.mod == "FARE"


# --- ElFaresi ---


def orta_parmak_cimdigi():
    n = sentetik_el(ACIK)
    n[9:13, :2] = [(0, -90), (-15, -120), (-30, -115), (-32, -97)]
    n[4, :2] = (-32, -97)
    return n


def test_el_faresi_tik_ve_sag_tik():
    fare = SahteFare()
    faresi = ElFaresi(fare, ekran=(1920, 1080))
    t = 0.0
    for n in [sentetik_cimdik()] * 4 + [sentetik_el(ACIK)] * 15 + [orta_parmak_cimdigi()] * 4 + [sentetik_el(ACIK)] * 3:
        faresi.isle(el(n, 640, 500), t, (1280, 720))
        t += DT
    assert fare.eylemler == ["tikla", "sag_tikla"]
    assert faresi.hedef is not None and 0 <= faresi.hedef[0] < 1920


def test_el_faresi_el_kaybolunca_tusu_birakir():
    fare = SahteFare()
    faresi = ElFaresi(fare, ekran=(1920, 1080))
    for i in range(20):  # Uzun çimdik: tuş basılı
        faresi.isle(el(sentetik_cimdik(), 640, 500), i * DT, (1280, 720))
    faresi.isle(None, 1.0, (1280, 720))
    assert fare.eylemler == ["bas", "birak"]


# --- Hava çizimi ---


def test_hava_tuvali_cizer_gezinir_temizler():
    tuval = HavaTuvali(1280, 720)
    for i in range(20):  # İşaret parmağıyla sağa çiz
        tuval.guncelle(el(sentetik_el(ISARET), 400 + 10 * i, 500), i * DT)
    assert tuval.durum == "ciziyor" and tuval.tuval.any()
    cizili = int(tuval.tuval.any(axis=2).sum())

    for i in range(20):  # Zaferle gezin: yeni çizgi yok
        tuval.guncelle(el(sentetik_el(ZAFER), 400 + 10 * i, 600), (20 + i) * DT)
    assert tuval.durum == "geziniyor" and int(tuval.tuval.any(axis=2).sum()) == cizili

    olaylar = [tuval.guncelle(el(sentetik_el(ACIK), 600, 500), (40 + i) * DT) for i in range(30)]
    assert "temizlendi" in olaylar and not tuval.tuval.any()


def test_hava_tuvali_paletten_renk_secer():
    tuval = HavaTuvali(1280, 720)
    x, y, g, h = tuval.palet[2]
    uc = sentetik_el(ZAFER)[j.ISARET_UCU, :2]
    olaylar = [tuval.guncelle(el(sentetik_el(ZAFER), x + g / 2 - uc[0], y + h / 2 - uc[1]), i * DT) for i in range(10)]
    assert "renk" in olaylar and tuval.renk[0] == "kirmizi"
