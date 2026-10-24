"""Testler için kamera gerektirmeyen sentetik el iskeleti üretir.

Koordinatlar piksel cinsindendir, y ekseni aşağı doğru artar (görüntü koordinatı).
Bilek (0, 0)'da, parmaklar yukarı (negatif y) bakar. El boyutu (bilek -> orta kök) = 90.
"""

import numpy as np

_BAS_ACIK = [(-20, -20), (-40, -40), (-55, -60), (-70, -80)]
_BAS_KAPALI = [(-20, -20), (-40, -40), (-55, -60), (10, -60)]
_PARMAK_X = (-20, 0, 20, 40)  # işaret, orta, yüzük, serçe
_ACIK_Y = (-90, -130, -155, -175)  # kök, PIP, DIP, uç
_KAPALI_Y = (-90, -120, -100, -85)


def sentetik_el(acik=(True, True, True, True, True)):
    """acik: (bas, isaret, orta, yuzuk, serce) parmaklarının açık olup olmadığı."""
    noktalar = [(0, 0)]
    noktalar += _BAS_ACIK if acik[0] else _BAS_KAPALI
    for x, parmak_acik in zip(_PARMAK_X, acik[1:]):
        noktalar += [(x, y) for y in (_ACIK_Y if parmak_acik else _KAPALI_Y)]
    dizi = np.zeros((21, 3), dtype=np.float32)
    dizi[:, :2] = noktalar
    return dizi


def sentetik_cimdik(diger_parmaklar_acik=True, aralik=0.0):
    """İşaret parmağı kıvrılıp başparmakla buluşmuş el.

    diger_parmaklar_acik=True  -> "OK işareti" (gerçek çimdik)
    diger_parmaklar_acik=False -> yumruk, başparmak işaretin üstünde (sahte çimdik)
    aralik: Başparmak ucu ile işaret ucu arasındaki mesafe (el boyuna oranla).
    """
    acik = diger_parmaklar_acik
    noktalar = sentetik_el((True, True, acik, acik, acik))
    noktalar[6, :2] = (-35, -120)  # işaret PIP
    noktalar[7, :2] = (-50, -115)  # işaret DIP
    noktalar[8, :2] = (-52, -97)  # işaret ucu
    noktalar[4, :2] = (-52 + 90 * aralik, -97)  # başparmak ucu
    return noktalar


def sentetik_pence(kapali=False):
    """Pençe: işaret, orta, yüzük kanca gibi kıvrık, serçe düz, başparmak uzakta.

    kapali=True: başparmak işaret ucuna kapanmış ("snap").
    """
    noktalar = sentetik_el((True, True, True, True, True))
    # Kancalar: kök -> PIP yukarı, DIP -> uç aşağı geri döner
    noktalar[5:9, :2] = [(-20, -90), (-25, -125), (-28, -140), (-35, -128)]
    noktalar[9:13, :2] = [(0, -90), (0, -127), (2, -143), (-3, -130)]
    noktalar[13:17, :2] = [(20, -90), (22, -124), (25, -138), (19, -126)]
    noktalar[17:21, :2] = [(40, -90), (40, -120), (40, -140), (40, -155)]
    noktalar[1:5, :2] = [(-20, -20), (-40, -40), (-60, -50), (-40, -125) if kapali else (-95, -50)]
    return noktalar


def dondur(noktalar, derece):
    """Eli bilek etrafında döndürür."""
    aci = np.radians(derece)
    matris = np.array([[np.cos(aci), -np.sin(aci)], [np.sin(aci), np.cos(aci)]])
    sonuc = noktalar.copy()
    sonuc[:, :2] = noktalar[:, :2] @ matris.T
    return sonuc
