import math
from types import SimpleNamespace

import numpy as np
import pytest

from goru.bas_faresi import BasFaresi, BeklemeTiklayici
from goru.bas_pozu import PNP_NOKTALARI, matris_acilari
from goru.goz import EKRAN_SAG_GOZ, EKRAN_SOL_GOZ, GozKirpmaAlgilayici, YorgunlukIzleyici, ear
from goru.mimik import MimikAlgilayici, el_yuzu_kapatiyor

DT = 1 / 30


def donusum(yaw=0.0, pitch=0.0, roll=0.0):
    """Yüzün ileri ve sağ eksenlerinden 4x4 matris (kamera: x sağ, y yukarı, z kameraya doğru)."""
    y, p, r = (math.radians(a) for a in (yaw, pitch, roll))
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    rx = np.array([[1, 0, 0], [0, math.cos(p), math.sin(p)], [0, -math.sin(p), math.cos(p)]])
    rz = np.array([[math.cos(r), math.sin(r), 0], [-math.sin(r), math.cos(r), 0], [0, 0, 1]])
    m = np.eye(4)
    m[:3, :3] = ry @ rx @ rz
    return m


@pytest.mark.parametrize("yaw, pitch, roll", [(20, 0, 0), (-15, 0, 0), (0, 12, 0), (0, -8, 0), (0, 0, 25), (10, 5, -10)])
def test_matris_acilari(yaw, pitch, roll):
    assert matris_acilari(donusum(yaw, pitch, roll)) == pytest.approx((yaw, pitch, roll), abs=0.5)


def test_pnp_bilinen_pozu_geri_cozer():
    cv2 = pytest.importorskip("cv2")
    from goru.bas_pozu import pnp_acilari

    genislik, yukseklik = 1280, 720
    model = np.array([p for _, p in PNP_NOKTALARI], dtype=np.float64)
    kamera = np.array([[genislik, 0, genislik / 2], [0, genislik, yukseklik / 2], [0, 0, 1]], dtype=np.float64)
    # Ekranın sağına 15° dönük yüz. Model y-yukarı, OpenCV kamerası y-aşağı / z-ileri:
    # önce y ekseninde 15° döndür, sonra eksen takımını çevir (bkz. pnp_acilari)
    donme = cv2.Rodrigues(np.array([0.0, math.radians(15), 0.0]))[0]
    rvec = cv2.Rodrigues(np.diag([1.0, -1.0, -1.0]) @ donme)[0]
    goruntu, _ = cv2.projectPoints(model, rvec, np.array([0.0, 0.0, 2500.0]), kamera, np.zeros(4))
    noktalar = np.zeros((478, 3))
    for (i, _), (x, y) in zip(PNP_NOKTALARI, goruntu.reshape(-1, 2)):
        noktalar[i, :2] = (x, y)
    yaw, pitch, roll = pnp_acilari(noktalar, (genislik, yukseklik))
    assert yaw == pytest.approx(15, abs=1) and pitch == pytest.approx(0, abs=1) and roll == pytest.approx(0, abs=1)


# --- Başla imleç ve bakarak tıklama ---


def test_bas_faresi_kalibrasyon_ve_esleme():
    fare = BasFaresi((1920, 1080), yaw_araligi=18, pitch_araligi=11, kalibrasyon_suresi=1.0)
    t = 0.0
    while not fare.kalibre:  # Kalibrasyon: hafif sağa ve aşağı bakan bir "nötr"
        assert fare.isle(5.0, -3.0, t) is None
        t += DT
    assert t == pytest.approx(1.0 + DT, abs=DT) and fare.merkez == (5.0, -3.0)

    def yerles(yaw, pitch):
        nonlocal t
        for _ in range(60):
            hedef = fare.isle(yaw, pitch, t)
            t += DT
        return hedef

    assert yerles(5.0, -3.0) == pytest.approx((959.5, 539.5), abs=3)  # Nötr -> ekranın ortası
    assert yerles(5.0 + 18, -3.0)[0] == pytest.approx(1919, abs=3)  # Sağa 18° -> sağ kenar
    assert yerles(5.0, -3.0 + 11)[1] == pytest.approx(0, abs=3)  # Yukarı 11° -> üst kenar


def test_bakarak_tiklama():
    tik = BeklemeTiklayici(sure=1.0, yaricap=30)
    sonuclar = [tik.guncelle((500 + (i % 3), 300), i * DT) for i in range(60)]  # 2 sn hafif titreyerek dur
    assert sonuclar.count(True) == 1 and sonuclar.index(True) == 30
    assert not any(tik.guncelle((500 + 40 * i, 300), 2 + i * DT) for i in range(20))  # Hareket: tık yok


# --- Göz ---


def goz_yuzu(ear_sol, ear_sag):
    """Sadece göz noktaları dolu, istenen EAR değerlerinde sentetik bir yüz."""
    n = np.zeros((478, 3))
    for goz, ear_, x0 in ((EKRAN_SOL_GOZ, ear_sol, 100), (EKRAN_SAG_GOZ, ear_sag, 200)):
        h = 15 * ear_  # Göz genişliği 30: EAR = 4h / 60
        p1, p2, p3, p4, p5, p6 = goz
        n[p1, :2], n[p4, :2] = (x0, 0), (x0 + 30, 0)
        n[p2, :2], n[p3, :2] = (x0 + 10, -h), (x0 + 20, -h)
        n[p6, :2], n[p5, :2] = (x0 + 10, h), (x0 + 20, h)
    return n


def test_ear_hesabi():
    n = goz_yuzu(0.3, 0.1)
    assert ear(n, EKRAN_SOL_GOZ) == pytest.approx(0.3) and ear(n, EKRAN_SAG_GOZ) == pytest.approx(0.1)


def oynat(algilayici, dizi, t0=0.0):
    """dizi: [(ear_sol, ear_sag, kare sayısı), ...] -> tüm olaylar"""
    olaylar, t = [], t0
    for sol, sag, adet in dizi:
        for _ in range(adet):
            olaylar += algilayici.guncelle(goz_yuzu(sol, sag), t)
            t += DT
    return olaylar


ACIK, KAPALI = 0.30, 0.08


@pytest.mark.parametrize(
    "kapali_kare, beklenen",
    [(3, ["dogal"]), (20, ["bilincli"]), (60, ["mikro_uyku", "uzun"])],
)
def test_iki_goz_kirpma_turleri(kapali_kare, beklenen):
    g = GozKirpmaAlgilayici()
    assert oynat(g, [(ACIK, ACIK, 30), (KAPALI, KAPALI, kapali_kare), (ACIK, ACIK, 10)]) == beklenen


def test_tek_goz_kirpma_ve_dogal_kirpma_ayrimi():
    g = GozKirpmaAlgilayici()
    assert oynat(g, [(ACIK, ACIK, 30), (KAPALI, ACIK, 12), (ACIK, ACIK, 10)]) == ["goz_kirp_sol"]
    assert oynat(g, [(ACIK, KAPALI, 12), (ACIK, ACIK, 10)], t0=2.0) == ["goz_kirp_sag"]
    # Doğal kırpmada bir göz bir kare önce kapanabilir: bu tek göz kırpma sayılmamalı
    assert oynat(g, [(KAPALI, ACIK, 1), (KAPALI, KAPALI, 3), (ACIK, ACIK, 10)], t0=4.0) == ["dogal"]


def test_dar_gozlu_kullaniciya_uyum():
    """Açık göz EAR'ı 0.20 olan birinde sabit 0.2 eşiği her kareyi 'kapalı' sayardı."""
    g = GozKirpmaAlgilayici()
    olaylar = oynat(g, [(0.20, 0.20, 60), (0.05, 0.05, 4), (0.20, 0.20, 60)])
    assert olaylar == ["dogal"] and g.taban[0] == pytest.approx(0.20, abs=0.01)


def test_yorgunluk_perclos_ve_esneme():
    y = YorgunlukIzleyici(pencere=60, perclos_esigi=0.15, en_az_veri=20, uyari_araligi=30)
    uyarilar = []
    for i in range(30 * 30):  # 30 sn, karelerin %20'sinde gözler kapalı
        uyarilar += y.guncelle(i % 5 == 0, [], 0.0, i * DT)
    assert uyarilar == ["yorgunluk"] and y.perclos == pytest.approx(0.2, abs=0.01)
    esneme = [u for i in range(60) for u in y.guncelle(False, [], 0.8, 30 + i * DT)]
    assert esneme == ["esneme"] and y.esneme_sayisi == 1
    assert y.guncelle(True, ["mikro_uyku"], 0.0, 40) == ["mikro_uyku"]


# --- Mimik ---


def test_mimik_taban_ve_tetikleme():
    m = MimikAlgilayici(esik=0.5, sure=0.4, kalibrasyon_suresi=1.0)
    m.kalibre_et()
    notr = {"mouthSmileLeft": 0.4, "mouthSmileRight": 0.4}  # Ağız kenarları doğal olarak yukarıda
    for i in range(35):
        m.guncelle(notr, i * DT)
    assert not m.kalibre_ediliyor and m.taban["mouthSmileLeft"] == pytest.approx(0.4)
    gulumseme = {"mouthSmileLeft": 0.8, "mouthSmileRight": 0.8}
    tetik = [x for i in range(30) for x in m.guncelle(gulumseme, 2 + i * DT)]
    assert tetik == ["gulumseme"] and m.skorlar["gulumseme"] == pytest.approx(0.4 / 0.6, abs=0.01)


def test_mimik_engel_ve_ozel_esik():
    m = MimikAlgilayici(kalibrasyon_suresi=0.0)
    assert [x for i in range(30) for x in m.guncelle({"jawOpen": 0.9}, i * DT, engel=True)] == []
    assert [x for i in range(30) for x in m.guncelle({"mouthPucker": 0.65}, 2 + i * DT)] == []  # Özel eşik 0.7
    assert [x for i in range(30) for x in m.guncelle({"mouthPucker": 0.9}, 4 + i * DT)] == ["dudak_buzme"]


def test_el_yuzu_kapatiyor():
    yuz = SimpleNamespace(kutu=lambda: (100, 100, 300, 300))
    icerde = SimpleNamespace(noktalar=np.full((21, 3), 200.0))
    disarda = SimpleNamespace(noktalar=np.full((21, 3), 500.0))
    assert el_yuzu_kapatiyor(yuz, [disarda, icerde]) and not el_yuzu_kapatiyor(yuz, [disarda])
