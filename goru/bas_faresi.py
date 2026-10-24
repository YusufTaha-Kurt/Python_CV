"""Ders 9: Başla imleç ve bakarak tıklama (eller serbest fare).

Baş açıları (yaw, pitch) ekrana oranlanır. Herkesin "düz bakış" pozu farklı olduğu için
ilk saniyelerde nötr poz kalibre edilir ve açılar bu merkeze göre ölçülür.
"""

import math
import statistics

import numpy as np

from .filtreler import OneEuroFiltre


class BeklemeTiklayici:
    """İmleç `sure` boyunca `yaricap` içinde kalırsa bir kez tıklar (dwell click).

    Ellerini kullanamayanlar için klasik erişilebilirlik tekniği. Tıkladıktan sonra imleç
    yerinden oynamadan ikinci tık olmaz.
    """

    def __init__(self, sure=1.0, yaricap=35.0):
        self.sure = sure
        self.yaricap = yaricap
        self.sifirla()

    def sifirla(self):
        self.ilerleme = 0.0
        self._merkez = None
        self._baslangic = 0.0
        self._tiklandi = False

    def guncelle(self, nokta, zaman):
        if self._merkez is None or math.dist(nokta, self._merkez) > self.yaricap:
            self._merkez, self._baslangic, self._tiklandi, self.ilerleme = nokta, zaman, False, 0.0
            return False
        if self._tiklandi:
            return False
        self.ilerleme = min(1.0, (zaman - self._baslangic) / self.sure)
        if self.ilerleme >= 1.0:
            self._tiklandi = True
            return True
        return False


class BasFaresi:
    """yaw ±yaw_araligi derece -> ekranın solu / sağı, pitch ±pitch_araligi -> altı / üstü."""

    def __init__(self, ekran, yaw_araligi=18.0, pitch_araligi=11.0, kalibrasyon_suresi=1.5):
        self.ekran = ekran
        self.yaw_araligi = yaw_araligi
        self.pitch_araligi = pitch_araligi
        self.kalibrasyon_suresi = kalibrasyon_suresi
        self.filtre = OneEuroFiltre(min_kesim=0.8, beta=4.0)
        self.merkez = None
        self.hedef = None
        self._ornekler = []
        self._kal_baslangic = None

    @property
    def kalibre(self):
        return self.merkez is not None

    def kalibrasyon_ilerlemesi(self, zaman):
        if self.kalibre:
            return 1.0
        if self._kal_baslangic is None:
            return 0.0
        return min(1.0, (zaman - self._kal_baslangic) / self.kalibrasyon_suresi)

    def kalibre_et(self):
        """Nötr pozu yeniden ölç (kullanıcı ekranın ortasına bakmalı)."""
        self.merkez, self._ornekler, self._kal_baslangic = None, [], None
        self.filtre.sifirla()

    def isle(self, yaw, pitch, zaman):
        """Açılar (derece) -> ekran hedefi (px). Kalibrasyon sürerken None."""
        if not self.kalibre:
            if self._kal_baslangic is None:
                self._kal_baslangic = zaman
            self._ornekler.append((yaw, pitch))
            if zaman - self._kal_baslangic >= self.kalibrasyon_suresi:
                self.merkez = (statistics.median(o[0] for o in self._ornekler),
                               statistics.median(o[1] for o in self._ornekler))
            return None
        yaw0, pitch0 = self.merkez
        nx = np.clip(0.5 + (yaw - yaw0) / (2 * self.yaw_araligi), 0, 1)
        ny = np.clip(0.5 - (pitch - pitch0) / (2 * self.pitch_araligi), 0, 1)  # Yukarı bakınca imleç yukarı
        fx, fy = self.filtre((nx, ny), zaman)
        self.hedef = (float(fx) * (self.ekran[0] - 1), float(fy) * (self.ekran[1] - 1))
        return self.hedef
