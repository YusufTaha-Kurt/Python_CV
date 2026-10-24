import json
from types import SimpleNamespace

import numpy as np
import pytest

from goru import hologram as hg
from goru.hologram import Masa, pence_pozu
from goru.olaylar import OlayYolu

from sentetik_el import sentetik_cimdik, sentetik_el, sentetik_pence

DT = 1 / 30
ACIK = (True,) * 5


def el(noktalar, x, y, taraf="sag"):
    """Eli, çimdik noktası (başparmak / işaret ucu ortası) (x, y)'ye gelecek şekilde taşır."""
    n = noktalar.copy()
    orta = (n[4, :2] + n[8, :2]) / 2
    n[:, :2] += np.array([x, y]) - orta
    return SimpleNamespace(taraf=taraf, noktalar=n)


class Oynatici:
    def __init__(self, masa):
        self.masa, self.t = masa, 0.0

    def kare(self, *eller, adet=1):
        for _ in range(adet):
            self.masa.guncelle(list(eller), self.t)
            self.t += DT


def test_tut_tasi_birak():
    masa = Masa()
    kart = masa.kart_ekle("Not", "gövde", x=300, y=300)
    o = Oynatici(masa)
    o.kare(el(sentetik_cimdik(), 300, 300), adet=3)
    assert kart.tutanlar == ["sag"] and kart.mod == "tasi"
    for i in range(30):  # Yavaşça sağa taşı
        o.kare(el(sentetik_cimdik(), 300 + 200 * (i + 1) / 30, 300))
    o.kare(el(sentetik_cimdik(), 500, 300), adet=10)
    assert kart.x == pytest.approx(500, abs=15)
    o.kare(el(sentetik_el(ACIK), 500, 300), adet=3)
    assert kart.mod == "serbest" and not kart.tutanlar and kart.vx == 0


def test_dokunmak_karti_acar():
    masa = Masa()
    kart = masa.kart_ekle("Not", "gövde", x=300, y=300)
    o = Oynatici(masa)
    o.kare(el(sentetik_cimdik(), 300, 300), adet=4)
    o.kare(el(sentetik_el(ACIK), 300, 300), adet=3)
    assert kart.acik
    assert kart.boyut()[1] == pytest.approx(kart.yukseklik * 2)


def test_firlatma_ve_surtunme():
    masa = Masa()
    kart = masa.kart_ekle("Not", x=300, y=360)
    o = Oynatici(masa)
    o.kare(el(sentetik_cimdik(), 300, 360), adet=15)  # Tut, deneme süresini geç
    for i in range(1, 7):  # 900 px/sn ile sağa savur
        o.kare(el(sentetik_cimdik(), 300 + 30 * i, 360))
    o.kare(el(sentetik_el(ACIK), 300 + 30 * 7, 360))
    o.kare(el(sentetik_el(ACIK), 300 + 30 * 8, 360))  # Hızlı elde bırakma iki açık kare ister
    assert kart.mod == "serbest" and kart.vx > hg.FIRLATMA_HIZI * masa.w
    x_birakma = kart.x
    o.kare(adet=90)  # El yok, 3 sn fizik (900 px/sn, e^-2t sürtünmeyle ~2.1 sn'de durur)
    assert kart.x > x_birakma + 100 and abs(kart.vx) < 0.01 * masa.w  # Uçtu ve sürtünmeyle durdu


def test_iki_elle_olceklendirme():
    masa = Masa()
    kart = masa.kart_ekle("Not", x=640, y=360)
    o = Oynatici(masa)
    sol = lambda x: el(sentetik_cimdik(), x, 360, "sol")  # noqa: E731
    sag = lambda x: el(sentetik_cimdik(), x, 360, "sag")  # noqa: E731
    o.kare(sol(590), sag(690), adet=3)
    assert kart.mod == "olcek" and len(kart.tutanlar) == 2
    for i in range(1, 31):
        o.kare(sol(590 - 50 * i / 30), sag(690 + 50 * i / 30))
    o.kare(sol(540), sag(740), adet=10)
    assert kart.olcek == pytest.approx(2.0, rel=0.1)


def test_modeli_tutup_beklemek_dondurme_moduna_gecirir():
    masa = Masa()
    model = masa.model_ekle("reaktor", x=900, y=400)
    o = Oynatici(masa)
    o.kare(el(sentetik_cimdik(), 900, 400), adet=40)
    assert model.mod == "don"
    for i in range(1, 21):
        o.kare(el(sentetik_cimdik(), 900 + 5 * i, 400))
    o.kare(el(sentetik_cimdik(), 1000, 400), adet=10)
    assert model.don_y == pytest.approx(100 / masa.w * hg.DONME_HASSASIYETI, rel=0.15)
    assert model.x == pytest.approx(900, abs=5)  # Döndürürken yer değiştirmez


def test_bos_cimdikle_patlatma():
    masa = Masa()
    model = masa.model_ekle("reaktor", x=1000, y=500)
    o = Oynatici(masa)
    o.kare(el(sentetik_cimdik(), 300, 300), adet=3)  # Boş bir yerde çimdik
    for i in range(1, 41):
        o.kare(el(sentetik_cimdik(), 300 + 6 * i, 300))
    assert model.patlama > 0.5
    o.kare(el(sentetik_el(ACIK), 540, 300), adet=3)
    assert model.patlama_hedef == pytest.approx(model.patlama, abs=0.05)  # Bırakınca olduğu yerde kalır


def test_dokunmak_modeli_patlatir():
    masa = Masa()
    model = masa.model_ekle("kup", x=600, y=400)
    o = Oynatici(masa)
    o.kare(el(sentetik_cimdik(), 600, 400), adet=4)
    o.kare(el(sentetik_el(ACIK), 600, 400), adet=40)
    assert model.patlama_hedef == 1.0 and model.patlama > 0.9


def test_pence_pozu():
    assert pence_pozu(sentetik_pence())
    assert not pence_pozu(sentetik_el(ACIK))
    assert not pence_pozu(sentetik_cimdik())
    assert not pence_pozu(sentetik_pence(kapali=True))  # Kapanmış pençe artık pençe değil


def test_pence_ile_uzaktan_cekme():
    yol = OlayYolu()
    olaylar = []
    yol.abone_ol(OlayYolu.HEPSI, olaylar.append)
    masa = Masa(pence=True, yol=yol)
    o = Oynatici(masa)
    # Pençenin nişan yönü bu sentetik elde sol-yukarı: hedefi oraya koy
    hedef = masa.kart_ekle("Hedef", x=520, y=270)
    yakin = el(sentetik_pence(), 835, 511)

    o.kare(el(sentetik_el(ACIK), 835, 511), adet=5)  # Önce açık el (geçiş yasası)
    o.kare(yakin, adet=20)
    imlec = masa.durum()["imlecler"][0]
    assert imlec["pence"] is not None and imlec["pence"]["hedef"] == hedef.id

    o.kare(yakin, adet=65)  # 2 sn'den fazla gerilim
    assert hedef.titreme > 0.5
    o.kare(el(sentetik_pence(kapali=True), 835, 511), adet=2)  # Pençeyi kapat
    assert hedef.mod in ("cekiliyor", "elde")
    assert "hologram.cekildi" in [x.ad for x in olaylar]

    o.kare(el(sentetik_pence(kapali=True), 835, 511), adet=40)
    assert hedef.mod == "elde" and np.hypot(hedef.x - 835, hedef.y - 511) < 60
    o.kare(el(sentetik_el(ACIK), 835, 511), adet=3)  # Avucu aç: bırak
    assert hedef.mod == "serbest"


def test_pence_erken_kapanirsa_cekmez():
    masa = Masa(pence=True)
    o = Oynatici(masa)
    hedef = masa.kart_ekle("Hedef", x=520, y=270)
    o.kare(el(sentetik_el(ACIK), 835, 511), adet=5)
    o.kare(el(sentetik_pence(), 835, 511), adet=25)  # Kurulur ama 2 sn dolmaz
    o.kare(el(sentetik_pence(kapali=True), 835, 511), adet=2)
    assert hedef.mod == "serbest"
    assert any("erken" in m for m, _ in masa.mesajlar)


def test_acik_elden_gelmeyen_pence_kurulmaz():
    masa = Masa(pence=True)
    o = Oynatici(masa)
    masa.kart_ekle("Hedef", x=520, y=270)
    o.kare(el(sentetik_pence(), 835, 511), adet=40)
    assert masa.durum()["imlecler"][0]["pence"] is None


def test_alkis_masayi_toparlar():
    masa = Masa(alkis=True)
    kart = masa.kart_ekle("Not", x=300, y=200)
    kart.x, kart.y = 900, 600  # Biri kartı başka yere koymuş
    o = Oynatici(masa)
    for i in range(8):  # İki dik avuç, 400 px'ten birbirine
        ara = 400 - 50 * i
        o.kare(el(sentetik_el(ACIK), 640 - ara / 2, 400, "sol"), el(sentetik_el(ACIK), 640 + ara / 2, 400, "sag"))
    assert (kart.x, kart.y) == pytest.approx((300, 200))


def test_durum_json_ve_komutlar():
    masa = Masa(pence=True)
    masa.kart_ekle("Not", "gövde")
    masa.model_ekle()
    masa.komut({"a": "kart_ekle", "baslik": "Dışarıdan", "govde": "x" * 5000})
    assert len(masa.nesneler) == 3 and len(masa.nesneler[-1].govde) == 1200
    o = Oynatici(masa)
    o.kare(el(sentetik_cimdik(), 100, 100))
    durum = json.loads(json.dumps(masa.durum()))
    assert durum["boyut"] == [1280, 720] and len(durum["nesneler"]) == 3 and len(durum["imlecler"]) == 1


def test_boyutla():
    masa = Masa()
    kart = masa.kart_ekle("Not", x=640, y=360)
    masa.boyutla(640, 480)
    assert (kart.x, kart.y) == (320, 240) and kart.genislik == pytest.approx(0.2 * 640)
