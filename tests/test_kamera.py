"""Kamera ayarı seçimi: gerçek kamera gerekmez, adaylar ve ölçülen FPS'ler taklit edilir."""

import pytest

cv2 = pytest.importorskip("cv2")

from goru import kamera as km  # noqa: E402


class SahteKamera:
    def __init__(self, aday):
        self.aday = aday
        self.serbest = False

    def release(self):
        self.serbest = True

    def getBackendName(self):
        return "SAHTE"


def _sec(monkeypatch, olculen):
    """`olculen`: aday -> FPS. Açılan kameraları da döndürür ki serbest bırakılanlar denetlensin."""
    acilan = []

    def ac(self, *aday):
        if aday not in olculen:
            return None
        acilan.append(SahteKamera(aday))
        return acilan[-1]

    monkeypatch.setattr(km.Kamera, "_ac", ac)
    monkeypatch.setattr(km, "fps_olc", lambda k: olculen[k.aday])
    nesne = km.Kamera.__new__(km.Kamera)
    nesne.kaynak, nesne._ayarlar, nesne._secilen = 0, (1280, 720, 60), None
    adaylar = nesne._adaylar()
    secilen = nesne._kamera_ac()
    return nesne, adaylar, secilen, acilan


def test_yavas_arka_uc_yerine_hizlisi_secilir(monkeypatch):
    """İlk aday 10 FPS'te kalır (DirectShow 720p YUY2), ikincisi 30 FPS verir ve arama orada biter."""
    nesne = km.Kamera.__new__(km.Kamera)
    nesne._ayarlar = (1280, 720, 60)
    adaylar = nesne._adaylar()
    olculen = {a: (10.0 if i == 0 else 30.0) for i, a in enumerate(adaylar)}
    nesne, _, secilen, acilan = _sec(monkeypatch, olculen)
    assert secilen.aday == adaylar[1] and nesne._secilen == adaylar[1]
    assert len(acilan) == 2 and acilan[0].serbest and not acilan[1].serbest


def test_hicbiri_yetmezse_en_hizlisi_secilir(monkeypatch):
    """Zayıf kamera: hiçbir aday 27 FPS'e ulaşmaz, düşük çözünürlük belirgin hızlıysa o seçilir."""
    nesne = km.Kamera.__new__(km.Kamera)
    nesne._ayarlar = (1280, 720, 60)
    adaylar = nesne._adaylar()
    olculen = {a: (8.0 if a[1] == 1280 else 15.0) for a in adaylar}
    _, _, secilen, acilan = _sec(monkeypatch, olculen)
    assert secilen.aday[1:] == (640, 480)
    assert sum(not k.serbest for k in acilan) == 1


def test_yakin_hizda_yuksek_cozunurluk_korunur(monkeypatch):
    nesne = km.Kamera.__new__(km.Kamera)
    nesne._ayarlar = (1280, 720, 60)
    adaylar = nesne._adaylar()
    olculen = {a: (20.0 if a[1] == 1280 else 21.0) for a in adaylar}
    _, _, secilen, _ = _sec(monkeypatch, olculen)
    assert secilen.aday[1:] == (1280, 720)


def test_yeniden_baglanirken_olcmeden_ayni_ayar(monkeypatch):
    nesne = km.Kamera.__new__(km.Kamera)
    nesne._ayarlar = (1280, 720, 60)
    ilk = nesne._adaylar()[0]
    nesne, _, _, _ = _sec(monkeypatch, {ilk: 30.0})
    monkeypatch.setattr(km, "fps_olc", lambda k: pytest.fail("yeniden bağlanırken ölçülmemeli"))
    assert nesne._kamera_ac().aday == ilk


def test_hicbir_kamera_acilmazsa_none(monkeypatch):
    _, _, secilen, _ = _sec(monkeypatch, {})
    assert secilen is None
