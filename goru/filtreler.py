"""Titreşim giderme filtreleri (Ders 2).

Kameradan gelen nokta konumları sensör gürültüsü yüzünden her karede birkaç piksel titrer.
Bu titreme doğrudan imlece yansırsa imleç elin sabit dururken bile "karıncalanır".
Çözüm: konumu yumuşatmak. Ama yumuşatma gecikme demektir; hızlı harekette imleç elin
arkasında kalır. Bu dosyadaki filtre bu ikilemi hıza göre ayarlanan yumuşatmayla çözer.
"""

import math

import numpy as np


def _alfa(kesim_frekansi, dt):
    """Kesim frekansını (Hz) üstel yumuşatma katsayısına (0-1) çevirir.

    Yeni değerin sonuca katılma oranıdır: 1'e yakınsa filtre neredeyse yok, 0'a yakınsa
    çok güçlü yumuşatma var. `dt` (iki kare arası süre) hesaba katıldığı için FPS
    dalgalansa da filtre aynı davranır.
    """
    tau = 1.0 / (2 * math.pi * kesim_frekansi)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFiltre:
    """1€ Filtresi (Casiez, Roussel, Vogel - CHI 2012).

    V1'deki sabit yumuşatma ikilemi: faktör büyükse imleç hantal, küçükse titrek.
    1€ filtresi kesim frekansını HIZA göre ayarlar:
      * El yavaşken / dururken -> düşük kesim frekansı -> güçlü yumuşatma (titreme yok)
      * El hızlıyken          -> yüksek kesim frekansı -> az yumuşatma (gecikme yok)

    min_kesim: Durağan haldeki kesim frekansı (Hz). Düşürmek titremeyi azaltır.
    beta:      Hıza duyarlılık. Artırmak hızlı harekette gecikmeyi azaltır.
    """

    def __init__(self, min_kesim=1.0, beta=0.0, turev_kesim=1.0):
        self.min_kesim = min_kesim
        self.beta = beta
        self.turev_kesim = turev_kesim
        self.sifirla()

    def sifirla(self):
        """Geçmişi unutur. El kaybolup tekrar göründüğünde eski konuma doğru "süzülmesin" diye çağır."""
        self._onceki_deger = None
        self._onceki_turev = None
        self._onceki_zaman = None

    def __call__(self, deger, zaman):
        """Ham değeri (sayı ya da numpy dizisi) ve zamanı (sn) alır, yumuşatılmış değeri döndürür."""
        deger = np.asarray(deger, dtype=np.float64)
        if self._onceki_deger is None:
            self._onceki_deger = deger
            self._onceki_turev = np.zeros_like(deger)
            self._onceki_zaman = zaman
            return deger

        dt = zaman - self._onceki_zaman
        if dt <= 0:
            return self._onceki_deger

        # 1) Hızı (türevi) hesapla ve onu da hafifçe yumuşat
        turev = (deger - self._onceki_deger) / dt
        a_turev = _alfa(self.turev_kesim, dt)
        turev = a_turev * turev + (1 - a_turev) * self._onceki_turev

        # 2) Hıza göre kesim frekansını belirle ve değeri filtrele
        kesim = self.min_kesim + self.beta * np.linalg.norm(turev)
        a = _alfa(kesim, dt)
        filtreli = a * deger + (1 - a) * self._onceki_deger

        self._onceki_deger, self._onceki_turev, self._onceki_zaman = filtreli, turev, zaman
        return filtreli
