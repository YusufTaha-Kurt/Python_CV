import math
from types import SimpleNamespace

import numpy as np
import pytest

from goru.egzersiz import (BURUN, SAG_BILEK, SAG_DIRSEK, SAG_OMUZ, SOL_BILEK, SOL_DIRSEK, SOL_OMUZ, DurusBekcisi,
                           TekrarSayaci, VucutJestleri, aci, egzersiz_acisi)
from goru.nesne import isaret_edilen
from goru.takip import IoUTakipci, iou

from sentetik_el import sentetik_el

DT = 1 / 30


def tespit(x0, y0, x1, y1, etiket="cup", skor=0.9):
    return SimpleNamespace(kutu=(x0, y0, x1, y1), etiket=etiket, skor=skor)


def test_iou():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(50 / 150)
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_takip_hareket_eden_nesnede_id_korunur():
    t = IoUTakipci(min_gorulme=3)
    gorulenler = [t.guncelle([tespit(100 + 8 * i, 100, 200 + 8 * i, 200)]) for i in range(30)]
    assert gorulenler[1] == []  # Henüz kesinleşmedi
    assert {iz.id for izler in gorulenler[2:] for iz in izler} == {1}


def test_takip_kisa_kayiptan_sonra_ayni_id():
    t = IoUTakipci(max_kayip=10)
    for i in range(10):
        t.guncelle([tespit(100 + 5 * i, 100, 200 + 5 * i, 200)])
    for _ in range(5):  # Dedektör 5 kare kaçırdı: iz hızıyla ilerletilir
        t.guncelle([])
    izler = t.guncelle([tespit(175, 100, 275, 200)])
    assert [iz.id for iz in izler] == [1]


def test_takip_yeni_nesne_ve_farkli_sinif():
    t = IoUTakipci(min_gorulme=1)
    t.guncelle([tespit(0, 0, 100, 100, "cup")])
    izler = t.guncelle([tespit(0, 0, 100, 100, "bottle"), tespit(300, 300, 400, 400, "cup")])
    assert sorted(iz.id for iz in izler) == [1, 2, 3] and len(t.yeni) == 2  # Eski fincan tahminle duruyor


def test_takip_biten_iz_bildirilir():
    t = IoUTakipci(max_kayip=3)
    for _ in range(5):
        t.guncelle([tespit(0, 0, 100, 100)])
    biten = []
    for _ in range(5):
        t.guncelle([])
        biten += t.biten
    assert [iz.id for iz in biten] == [1] and t.izler == []


def test_isaret_edilen_nesne():
    el = sentetik_el((False, True, False, False, False))  # İşaret parmağı yukarı (-y yönü)
    el[:, :2] += (500, 600)
    kutular = {"fincan": (450, 100, 550, 200), "sise": (700, 100, 800, 200), "yakin": (480, 300, 520, 340)}
    assert isaret_edilen(el, kutular) == "yakin"  # Işının ilk çarptığı
    del kutular["yakin"]
    assert isaret_edilen(el, kutular) == "fincan"
    assert isaret_edilen(el, {"sise": (700, 100, 800, 200)}) is None
    uc = el[8, :2]
    assert isaret_edilen(el, {"ic": (uc[0] - 5, uc[1] - 5, uc[0] + 5, uc[1] + 5), "dis": (0, 0, 2000, 2000)}) == "ic"


# --- Vücut ---


def test_aci():
    assert aci((1, 0), (0, 0), (0, 1)) == pytest.approx(90)
    assert aci((-1, 0), (0, 0), (1, 0)) == pytest.approx(180)


def test_tekrar_sayaci_histerezis():
    sayac = TekrarSayaci(asagi=100, yukari=160)
    acilar = [130 + 45 * math.cos(2 * math.pi * i / 60) for i in range(300)]  # 5 tam hareket
    acilar += [99, 101, 99, 101, 99]  # Eşik etrafında titreme: tekrar sayılmaz
    for a in acilar:
        sayac.guncelle(a)
    assert sayac.sayi == 5


def poz(omuz_y=300.0, burun_y=180.0, egim=0.0, bilekler=None, gorunur=1.0):
    n = np.zeros((33, 3))
    n[BURUN, :2] = (640, burun_y)
    n[SOL_OMUZ, :2] = (740, omuz_y + egim)
    n[SAG_OMUZ, :2] = (540, omuz_y - egim)
    n[SOL_DIRSEK, :2], n[SAG_DIRSEK, :2] = (760, 420), (520, 420)
    sol_bilek, sag_bilek = bilekler or ((770, 540), (510, 540))
    n[SOL_BILEK, :2], n[SAG_BILEK, :2] = sol_bilek, sag_bilek
    return SimpleNamespace(noktalar=n, gorunurluk=np.full(33, gorunur))


def test_egzersiz_acisi_gorunurlukle():
    p = poz()
    assert egzersiz_acisi(p, "biceps") == pytest.approx(aci(p.noktalar[11], p.noktalar[13], p.noktalar[15]), abs=1)
    assert egzersiz_acisi(poz(gorunur=0.2), "biceps") is None


def test_durus_bekcisi_kambur_ve_egik():
    d = DurusBekcisi(kalibrasyon_suresi=3, esik=0.8, uyari_suresi=10, uyari_araligi=60)
    t, uyarilar = 0.0, []
    for _ in range(120):  # 4 sn dik: kalibrasyon (oran = 120 / 200 = 0.6)
        uyarilar += d.guncelle(poz(), t)
        t += DT
    assert d.taban == pytest.approx(0.6)
    for _ in range(9 * 30):  # 9 sn kambur: henüz uyarı yok
        uyarilar += d.guncelle(poz(burun_y=220), t)
        t += DT
    assert uyarilar == [] and d.durum()["kambur"]
    for _ in range(2 * 30):
        uyarilar += d.guncelle(poz(burun_y=220), t)
        t += DT
    assert uyarilar == ["kambur"]
    for _ in range(11 * 30):  # Dik ama omuzlar eğik (~11°)
        uyarilar += d.guncelle(poz(egim=20), t)
        t += DT
    assert uyarilar == ["kambur", "egik_omuz"]


def test_vucut_jestleri():
    j = VucutJestleri(sure=0.5)
    sonuc = [j.guncelle(poz(bilekler=((700, 100), (580, 100))), i * DT) for i in range(30)]
    assert sonuc.count("eller_yukari") == 1
    sonuc = [j.guncelle(poz(bilekler=((1000, 300), (280, 300))), 1 + i * DT) for i in range(30)]
    assert sonuc.count("t_pozu") == 1
