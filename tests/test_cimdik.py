import numpy as np
import pytest

from goru import jestler as j
from goru.cimdik import CimdikAyarlari, GuvenilirCimdik, olcumler
from goru.fare import SahteFare, TiklamaMakinesi
from goru.ornekleyici import Ornekleyici, cimdik_ayari_oner, esik_oner

from sentetik_el import sentetik_cimdik, sentetik_el

FPS = 30
DT = 1 / FPS
ACIK_EL = (True,) * 5


def oynat(cimdik, kareler, t0=0.0):
    """kareler: nokta dizileri listesi. Dönüş: [(kare no, olay)]"""
    return [(i, o) for i, n in enumerate(kareler) if (o := cimdik.guncelle(n, t0 + i * DT))]


def test_olcumler_ok_isareti_ve_yumruk():
    ok = olcumler(sentetik_cimdik(True))
    yumruk = olcumler(sentetik_cimdik(False))
    assert ok["oran"] < 0.1 and yumruk["oran"] < 0.1  # İkisinde de parmak uçları değiyor
    assert ok["kontrast"] > 0.5 and ok["arka"] > 1.8
    assert yumruk["kontrast"] < 0 and yumruk["arka"] < 1.0


def test_kivrim_aciyla_olculur():
    acik, kapali = sentetik_el(ACIK_EL), sentetik_el((False,) * 5)
    assert j.kivrim(acik, j.ORTA_UCU) == pytest.approx(1.0)
    assert j.kivrim(kapali, j.ORTA_UCU) == pytest.approx(-1.0)


def test_gercek_cimdik_baslar_ve_biter():
    olaylar = oynat(GuvenilirCimdik(), [sentetik_cimdik()] * 15 + [sentetik_el(ACIK_EL)] * 3)
    # İmza iki ardışık karede görülünce (2. kare) başlar, el açılınca biter
    assert olaylar == [(1, "basladi"), (15, "bitti")]


def test_yumruk_cimdik_sayilmaz():
    """Başparmak işaret ucunun üstünde ama diğer parmaklar kıvrık: Ders 2 bunu tık sayardı."""
    cimdik = GuvenilirCimdik()
    assert oynat(cimdik, [sentetik_cimdik(False)] * 60) == []
    assert j.cimdik_orani(sentetik_cimdik(False)) < 0.25  # Ders 2 eşiğinin altında


def test_imza_zorunlu_degilse_yumruk_da_baslar():
    cimdik = GuvenilirCimdik(ayarlar=CimdikAyarlari(kontrast_zorunlu=False))
    assert oynat(cimdik, [sentetik_cimdik(False)] * 5)[0][1] == "basladi"


def test_deneme_suresinde_imzasini_kaybeden_cimdik_iptal_olur():
    """Eli yumruk yaparken bir an OK işaretinden geçmek (barehands'in 'fold-through' hatası)."""
    kareler = [sentetik_cimdik(True)] * 2 + [sentetik_cimdik(False)] * 6
    assert oynat(GuvenilirCimdik(), kareler) == [(1, "basladi"), (5, "iptal")]


def test_deneme_suresinden_sonra_imza_kaybi_iptal_etmez():
    kareler = [sentetik_cimdik(True)] * 20 + [sentetik_cimdik(False)] * 10
    assert oynat(GuvenilirCimdik(), kareler) == [(1, "basladi")]


def _kaydir(noktalar, dx):
    yeni = noktalar.copy()
    yeni[:, 0] += dx
    return yeni


def test_hizli_harekette_dogan_cimdik_hayalettir_ve_yavaslayinca_iyilesir():
    cimdik = GuvenilirCimdik()
    hizli = [_kaydir(sentetik_cimdik(), 30 * i) for i in range(12)]  # 900 px/sn = 10 el boyu/sn
    son = hizli[-1]
    olaylar = oynat(cimdik, hizli + [son] * 15)
    assert olaylar[0] == (1, "basladi")
    assert ("iyilesti" in [o for _, o in olaylar]) and not cimdik.hayalet


def test_hizli_elde_tek_bulanik_kare_birakmaz():
    cimdik = GuvenilirCimdik()
    kareler = [sentetik_cimdik()] * 15  # Yavaşken başla, deneme süresini geç
    kareler += [_kaydir(sentetik_cimdik(), 30 * i) for i in range(1, 12)]  # Hızlan
    bulanik = _kaydir(sentetik_cimdik(aralik=0.75), 30 * 12)  # Tek karelik sahte açılma
    kareler += [bulanik, _kaydir(sentetik_cimdik(), 30 * 13)]
    assert [o for _, o in oynat(cimdik, kareler)] == ["basladi"]
    assert cimdik.aktif


def test_yavas_elde_tek_acik_kare_birakir():
    kareler = [sentetik_cimdik()] * 15 + [sentetik_cimdik(aralik=0.6)]
    assert [o for _, o in oynat(GuvenilirCimdik(), kareler)] == ["basladi", "bitti"]


def test_imkansiz_geometri_hicbir_sey_tetiklemez():
    garip = sentetik_cimdik()
    garip[j.SERCE_KOK, :2] = garip[j.ISARET_KOK, :2] + (5, 0)  # Avuç genişliği ~0
    assert j.avuc_en_boy(garip) > 8
    assert oynat(GuvenilirCimdik(), [garip] * 10) == []


def test_ayarlar_kaydet_yukle(tmp_path):
    yol = tmp_path / "ayarlar" / "cimdik.json"
    CimdikAyarlari(kontrast=0.33, baslama=0.27).kaydet(yol)
    yuklenen = CimdikAyarlari.yukle(yol)
    assert yuklenen.kontrast == 0.33 and yuklenen.baslama == 0.27
    assert CimdikAyarlari.yukle(tmp_path / "yok.json") == CimdikAyarlari()


# --- Tıklama durum makinesi ---


def makine():
    return TiklamaMakinesi(SahteFare(), surukleme_esigi_px=40, deneme_suresi=0.4, cift_tik_penceresi=0.3)


def test_kisa_cimdik_tik_olur():
    m = makine()
    m.guncelle("basladi", True, (100, 100), 0.0)
    assert m.donuk and m.fare.eylemler == []
    m.guncelle(None, True, (105, 100), 0.1)
    m.guncelle("bitti", False, (105, 100), 0.2)
    assert m.fare.eylemler == ["tikla"]
    assert m.donuk  # Çift tık penceresi
    m.guncelle(None, False, (105, 100), 0.6)
    assert not m.donuk


def test_uzun_cimdik_basili_tutar():
    m = makine()
    m.guncelle("basladi", True, (100, 100), 0.0)
    for t in np.arange(DT, 0.6, DT):
        m.guncelle(None, True, (100, 100), t)
    assert m.fare.eylemler == ["bas"] and m.durum == TiklamaMakinesi.BASILI
    m.guncelle("bitti", False, (100, 100), 0.7)
    assert m.fare.eylemler == ["bas", "birak"]


def test_cimdikle_hareket_hemen_surukler():
    m = makine()
    m.guncelle("basladi", True, (100, 100), 0.0)
    m.guncelle(None, True, (160, 100), 0.1)  # Deneme süresi dolmadan eşiği aştı
    assert m.fare.eylemler == ["bas"] and not m.donuk


def test_iptal_edilen_cimdik_hicbir_sey_yapmaz():
    m = makine()
    m.guncelle("basladi", True, (100, 100), 0.0)
    m.guncelle("iptal", False, (100, 100), 0.15)
    m.guncelle(None, False, (100, 100), 1.0)
    assert m.fare.eylemler == [] and not m.donuk


def test_hayalet_cimdik_iyilesince_baslar():
    m = makine()
    m.guncelle("basladi", False, (100, 100), 0.0)  # Hayalet: kavrayamaz
    assert m.durum == TiklamaMakinesi.BOS
    m.guncelle("iyilesti", True, (300, 100), 0.2)
    m.guncelle("bitti", False, (300, 100), 0.3)
    assert m.fare.eylemler == ["tikla"]


def test_cift_tik_ayni_noktaya_duser():
    m = makine()
    m.guncelle("basladi", True, (100, 100), 0.0)
    m.guncelle("bitti", False, (100, 100), 0.1)
    m.guncelle("basladi", True, (115, 100), 0.25)  # Pencere içinde, imleç hâlâ donuk
    assert m.kilit_noktasi == (100, 100)
    m.guncelle("bitti", False, (115, 100), 0.35)
    assert m.fare.eylemler == ["tikla", "tikla"]


# --- Örnekleyici ---


def test_esik_kanyonun_ortasindan_kesilir():
    assert esik_oner([0.5, 0.6, 0.7], [0.0, 0.1, 0.3]) == {"esik": 0.4, "yon": ">", "ayrik": True}
    ters = esik_oner([0.1, 0.2], [0.6, 0.9])
    assert ters["yon"] == "<" and ters["esik"] == pytest.approx(0.4)
    assert esik_oner([0.2, 0.5, 0.6], [0.1, 0.3, 0.4])["ayrik"] is False


def test_ornekleyici_ve_ayar_onerisi():
    ornek = Ornekleyici(sure=1.0)
    for etiket, n in (("cimdik", sentetik_cimdik(True)), ("yumruk", sentetik_cimdik(False))):
        ornek.baslat(etiket, 0.0)
        bitti = [ornek.ekle(olcumler(n), t) for t in np.arange(0, 1.05, DT)]
        assert bitti.count(True) == 1 and not ornek.kayitta
    ozet = ornek.ozet("cimdik")
    assert ozet["kontrast"][0] > 0.5
    yeni, rapor = cimdik_ayari_oner(ornek, CimdikAyarlari())
    # Önerilen eşik iki pozun tam ortasında: ikisini de doğru sınıflandırır
    assert olcumler(sentetik_cimdik(False))["kontrast"] < yeni.kontrast < olcumler(sentetik_cimdik(True))["kontrast"]
    assert 0.20 <= yeni.baslama <= 0.45 and len(rapor) == 3
