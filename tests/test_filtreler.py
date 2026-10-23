import numpy as np
import pytest

from jarvis_vision.filtreler import OneEuroFiltre

FPS = 30


def _uygula(filtre, sinyal):
    return np.array([filtre(deger, i / FPS) for i, deger in enumerate(sinyal)])


def test_sabit_sinyal_degismez():
    cikti = _uygula(OneEuroFiltre(), np.full(50, 0.5))
    assert np.allclose(cikti, 0.5)


def _v1_yumusatma(sinyal, faktor=2):
    """V1'deki formül: onceki + (hedef - onceki) / yumusatma_faktoru"""
    cikti, onceki = [], sinyal[0]
    for deger in sinyal:
        onceki = onceki + (deger - onceki) / faktor
        cikti.append(onceki)
    return np.array(cikti)


def test_dururken_titremeyi_bastirir():
    rastgele = np.random.default_rng(0)
    gurultulu = 0.5 + rastgele.normal(0, 0.003, 600)
    cikti = _uygula(OneEuroFiltre(min_kesim=0.6, beta=6.0), gurultulu)
    assert cikti[30:].std() < gurultulu[30:].std() / 2.5


def test_v1_yumusatmasindan_hem_stabil_hem_hizli():
    rastgele = np.random.default_rng(1)
    gurultulu = 0.5 + rastgele.normal(0, 0.003, 600)
    rampa = np.linspace(0, 1, 31)  # 1 saniyede ekranı boydan boya geçen el

    filtre = lambda: OneEuroFiltre(min_kesim=0.6, beta=6.0)  # noqa: E731
    titreme_v1, titreme_v2 = _v1_yumusatma(gurultulu)[30:].std(), _uygula(filtre(), gurultulu)[30:].std()
    gecikme_v1, gecikme_v2 = rampa[-1] - _v1_yumusatma(rampa)[-1], rampa[-1] - _uygula(filtre(), rampa)[-1]

    assert titreme_v2 < titreme_v1 / 1.5
    assert gecikme_v2 < gecikme_v1


def test_beta_hizli_harekette_gecikmeyi_azaltir():
    rampa = np.linspace(0, 2, 60)  # saniyede 1 ekran genişliği hız
    gecikme_betasiz = np.abs(rampa - _uygula(OneEuroFiltre(beta=0.0), rampa))[-1]
    gecikme_betali = np.abs(rampa - _uygula(OneEuroFiltre(beta=8.0), rampa))[-1]
    assert gecikme_betali < gecikme_betasiz / 3


def test_vektor_girdi_ve_sifirlama():
    filtre = OneEuroFiltre()
    filtre((0.0, 0.0), 0.0)
    filtre((1.0, 1.0), 1 / FPS)
    filtre.sifirla()
    # Sıfırlandıktan sonra ilk değer olduğu gibi döner (eski konuma "çekilme" olmaz)
    assert filtre((0.3, 0.7), 2.0) == pytest.approx([0.3, 0.7])
