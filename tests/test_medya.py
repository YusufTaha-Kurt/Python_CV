from types import SimpleNamespace

import numpy as np
import pytest

from goru import jestler as j
from goru.medya import MedyaKontrol
from goru.olaylar import OlayYolu

from sentetik_el import sentetik_el

ACIK, KAPALI = True, False
L_ISARETI = (ACIK, ACIK, KAPALI, KAPALI, KAPALI)
AVUC = (ACIK,) * 5


def el(parmaklar, taraf="sag"):
    return SimpleNamespace(taraf=taraf, noktalar=sentetik_el(parmaklar))


class SahteSes:
    destekleniyor = True

    def __init__(self):
        self.ayarlanan = []
        self.sessiz = 0

    def seviye(self):
        return 0.5

    def seviye_ayarla(self, oran):
        self.ayarlanan.append(oran)

    def sessiz_degistir(self):
        self.sessiz += 1


def test_jest_yayincisi_olay_sirasi():
    yol = OlayYolu()
    olaylar = []
    yol.abone_ol(OlayYolu.HEPSI, olaylar.append)
    yayinci = j.JestYayincisi(yol, sure=0.3)

    for t in np.arange(0, 0.5, 1 / 30):
        yayinci.guncelle([el(AVUC)], t)
    yayinci.guncelle([], 0.6)

    adlar = [o.ad for o in olaylar]
    assert adlar == ["el.goruldu", "jest.degisti", "el.kayboldu"]
    assert olaylar[1].veri == {"el": "sag", "jest": "avuc", "parmak_sayisi": 5}
    assert yayinci.jest("sag") == j.Jest.BILINMIYOR  # el kayboldu


def test_jest_yayincisi_kaydirma_sadece_avucla():
    yol = OlayYolu()
    kaydirmalar = []
    yol.abone_ol("jest.kaydirma", kaydirmalar.append)
    yayinci = j.JestYayincisi(yol, sure=0.1)

    def hareket(parmaklar):
        for i, t in enumerate(np.arange(0, 0.6, 1 / 30)):
            e = el(parmaklar)
            e.noktalar[:, 0] += 100 + (900 * max(t - 0.2, 0))  # 0.2 sn bekle, sonra hızla sağa
            yayinci.guncelle([e], t + hareket.ofset)
        hareket.ofset += 1.0

    hareket.ofset = 0.0
    hareket((ACIK, ACIK, KAPALI, KAPALI, KAPALI))
    assert kaydirmalar == []
    hareket(AVUC)
    assert [o.veri["yon"] for o in kaydirmalar] == ["sag"]


def test_medya_ses_modu_ve_seviye():
    yol = OlayYolu()
    ses = SahteSes()
    medya = MedyaKontrol(yol, el="sag", ses=ses)
    yayinci = j.JestYayincisi(yol, sure=0.1)

    for t in np.arange(0, 0.3, 1 / 30):
        e = el(L_ISARETI)
        yayinci.guncelle([e], t)
        medya.isle(e, t)
    assert medya.ses_modu
    # Sentetik L elinde başparmak-işaret mesafesi aralığın üstünde -> seviye tam açık
    assert ses.ayarlanan and ses.ayarlanan[-1] == pytest.approx(1.0)

    e = el(AVUC)
    medya.isle(e, 0.4)
    assert not medya.ses_modu  # avuç açınca moddan çıkılır


def test_medya_diger_elin_jestini_yok_sayar():
    yol = OlayYolu()
    medya = MedyaKontrol(yol, el="sag", ses=SahteSes(), sadece_izle=True)
    yol.yayinla("jest.degisti", el="sol", jest="l_isareti")
    assert not medya.ses_modu
    yol.yayinla("jest.degisti", el="sag", jest="basparmak_yukari")
    assert medya.son_eylem == "oynat/duraklat"
