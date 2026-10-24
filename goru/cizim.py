"""Ders 8: Hava çizimi. İşaret parmağı kalem, iki parmak gezinme, açık avuç silme.

    Sadece işaret parmağı düz     Çiz
    İşaret + orta düz (zafer)     Kalemi kaldır, gezin. Bu sırada üstteki paletten renk seç
    Açık avuç (0.8 sn)            Tuvali temizle
"""

import os
import time

import cv2
import numpy as np

from . import jestler as j
from .filtreler import OneEuroFiltre

RENKLER = [
    ("mavi", (255, 200, 0)),
    ("yesil", (80, 220, 80)),
    ("kirmizi", (60, 60, 240)),
    ("sari", (0, 220, 255)),
    ("beyaz", (245, 245, 245)),
    ("silgi", None),
]
TEMIZLEME_SURESI = 0.8


def duz_parmaklar(noktalar):
    """(işaret, orta, yüzük, serçe) için gerçekten düz mü? (bkz. jestler.duz_parmak_sayisi)"""
    return tuple(j.kemer_orani(noktalar, uc) > 1.45 and j.kivrim(noktalar, uc) > 0.5 for uc in j.PARMAKLAR)


class HavaTuvali:
    def __init__(self, genislik, yukseklik, kalinlik=6):
        self.w, self.h = genislik, yukseklik
        self.tuval = np.zeros((yukseklik, genislik, 3), np.uint8)
        self.kalinlik = kalinlik
        self.renk_no = 0
        self.durum = "bekliyor"  # ciziyor | geziniyor | bekliyor
        self.uc = None
        self._onceki = None
        self._avuc_baslangic = None
        self._filtre = OneEuroFiltre(min_kesim=1.5, beta=8.0)
        boyut, bosluk = 64, 12
        x0 = (genislik - len(RENKLER) * (boyut + bosluk)) // 2
        self.palet = [(x0 + i * (boyut + bosluk), 12, boyut, boyut) for i in range(len(RENKLER))]

    @property
    def renk(self):
        return RENKLER[self.renk_no]

    def temizle(self):
        self.tuval[:] = 0

    def guncelle(self, el, zaman):
        """Her kare çağrılır. Olay döndürür: "temizlendi", "renk", ya da None."""
        if el is None:
            self._onceki, self.uc, self.durum, self._avuc_baslangic = None, None, "bekliyor", None
            self._filtre.sifirla()
            return None
        n = el.noktalar
        ham = n[j.ISARET_UCU, :2]
        fx, fy = self._filtre((ham[0] / self.w, ham[1] / self.h), zaman)
        self.uc = (int(fx * self.w), int(fy * self.h))
        isaret, orta, yuzuk, serce = duz_parmaklar(n)

        if isaret and orta and yuzuk and serce:  # Açık avuç: tutarsa temizle
            self._onceki, self.durum = None, "bekliyor"
            if self._avuc_baslangic is None:
                self._avuc_baslangic = zaman
            elif zaman - self._avuc_baslangic >= TEMIZLEME_SURESI:
                self._avuc_baslangic = None
                self.temizle()
                return "temizlendi"
            return None
        self._avuc_baslangic = None

        if isaret and not orta and not yuzuk:
            self.durum = "ciziyor"
            if self._onceki is not None:
                ad, renk = self.renk
                if renk is None:  # Silgi
                    cv2.line(self.tuval, self._onceki, self.uc, (0, 0, 0), self.kalinlik * 5, cv2.LINE_AA)
                else:
                    cv2.line(self.tuval, self._onceki, self.uc, renk, self.kalinlik, cv2.LINE_AA)
            self._onceki = self.uc
            return None

        self._onceki = None
        if isaret and orta:
            self.durum = "geziniyor"
            for i, (x, y, g, h) in enumerate(self.palet):
                if x <= self.uc[0] <= x + g and y <= self.uc[1] <= y + h and i != self.renk_no:
                    self.renk_no = i
                    return "renk"
        else:
            self.durum = "bekliyor"
        return None

    def birlestir(self, kare):
        """Tuvali kamera karesinin üstüne yazar (çizilmiş pikseller kareyi örter)."""
        maske = self.tuval.any(axis=2)
        kare[maske] = self.tuval[maske]
        return kare

    def palet_ciz(self, kare):
        for i, ((x, y, g, h), (ad, renk)) in enumerate(zip(self.palet, RENKLER)):
            if renk is None:
                cv2.rectangle(kare, (x, y), (x + g, y + h), (40, 40, 40), -1)
                cv2.putText(kare, "SIL", (x + 12, y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 2)
            else:
                cv2.rectangle(kare, (x, y), (x + g, y + h), renk, -1)
            kalin = 4 if i == self.renk_no else 1
            cv2.rectangle(kare, (x, y), (x + g, y + h), (255, 255, 255), kalin)

    def kaydet(self, klasor):
        os.makedirs(klasor, exist_ok=True)
        yol = os.path.join(klasor, time.strftime("cizim_%Y%m%d_%H%M%S.png"))
        cv2.imwrite(yol, self.tuval)
        return yol
