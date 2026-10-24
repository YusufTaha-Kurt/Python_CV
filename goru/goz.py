"""Ders 10: Göz kırpma algılama ve yorgunluk izleme.

Göz Açıklık Oranı (EAR, Soukupová & Čech 2016): Göz kapağının dikey açıklığının gözün
genişliğine oranı. Açık gözde ~0.3, kapalı gözde ~0.1. Oran olduğu için yüzün kameraya
uzaklığından bağımsızdır.

        p2   p3
    p1          p4        EAR = (|p2 - p6| + |p3 - p5|) / (2 |p1 - p4|)
        p6   p5

Sabit bir eşik herkese uymaz (gözlük, göz şekli, kamera açısı). Burada her gözün "açık"
tabanı son saniyelerden sürekli öğrenilir ve eşikler bu tabana oranlıdır.
"""

import math
from collections import deque

import numpy as np

# MediaPipe yüz noktaları: p1..p6. Bu indeksler aynalamadan bağımsız olarak hep görüntünün
# aynı tarafındaki göze denk gelir (Ders 9'da doğrulandı). Aynalı görüntüde ekranın solundaki
# göz, kullanıcının kendi sol gözüdür.
EKRAN_SOL_GOZ = (33, 160, 158, 133, 153, 144)
EKRAN_SAG_GOZ = (263, 387, 385, 362, 380, 373)


def ear(noktalar, goz):
    p = noktalar[list(goz), :2]
    yatay = max(float(np.linalg.norm(p[0] - p[3])), 1e-6)
    return float(np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])) / (2 * yatay)


class GozKirpmaAlgilayici:
    """`guncelle()` her kare çağrılır ve bu karede biten olayları liste olarak döndürür:

        "dogal"         İki göz kısa süre kapandı (< 0.35 sn): doğal göz kırpma
        "bilincli"      İki göz bilerek kapatıldı (0.35 - 1.5 sn): tıklama için
        "uzun"          İki göz 1.5 sn'den uzun kapalı kaldı ve açıldı
        "mikro_uyku"    İki göz 1.5 sn'dir kapalı (henüz açılmadı, bir kez)
        "goz_kirp_sol" / "goz_kirp_sag"   Tek göz kırpma (ekranda görünen taraf)
    """

    ISINMA_KARESI = 15

    def __init__(self, kapanma_orani=0.62, acilma_orani=0.78, dogal_sinir=0.35, uzun_sinir=1.5,
                 tek_goz_min=0.2, tek_goz_max=1.0):
        self.kapanma_orani = kapanma_orani
        self.acilma_orani = acilma_orani
        self.dogal_sinir = dogal_sinir
        self.uzun_sinir = uzun_sinir
        self.tek_goz_min = tek_goz_min
        self.tek_goz_max = tek_goz_max
        self.sifirla()

    def sifirla(self):
        self.ear = [0.0, 0.0]
        self.taban = [None, None]
        self.kapali = [False, False]
        self._acik_gecmisi = [deque(maxlen=300), deque(maxlen=300)]  # ~10 sn açık göz örneği
        self._iki_kapali_baslangic = None
        self._mikro_uyku_bildirildi = False
        self._tek = None  # (kapanan göz, başlangıç, diğer göz hep açık kaldı mı)

    @property
    def hazir(self):
        return self.taban[0] is not None and self.taban[1] is not None

    @property
    def ikisi_kapali(self):
        return self.kapali[0] and self.kapali[1]

    def esikler(self, i):
        return self.taban[i] * self.kapanma_orani, self.taban[i] * self.acilma_orani

    def guncelle(self, noktalar, zaman):
        self.ear = [ear(noktalar, EKRAN_SOL_GOZ), ear(noktalar, EKRAN_SAG_GOZ)]
        for i in (0, 1):
            if self.taban[i] is None:
                self._acik_gecmisi[i].append(self.ear[i])
                if len(self._acik_gecmisi[i]) >= self.ISINMA_KARESI:
                    self.taban[i] = float(np.percentile(self._acik_gecmisi[i], 70))
        if not self.hazir:
            return []

        onceki = list(self.kapali)
        for i in (0, 1):
            kapanma, acilma = self.esikler(i)
            if not self.kapali[i] and self.ear[i] < kapanma:
                self.kapali[i] = True
            elif self.kapali[i] and self.ear[i] > acilma:
                self.kapali[i] = False
            if not self.kapali[i] and self.ear[i] > acilma:
                # Taban sadece net açık karelerden öğrenilir; %70'lik dilim yarım kırpmalara dayanıklı
                self._acik_gecmisi[i].append(self.ear[i])
                self.taban[i] = float(np.percentile(self._acik_gecmisi[i], 70))

        olaylar = []
        # İki göz birlikte
        if self.ikisi_kapali:
            if self._iki_kapali_baslangic is None:
                self._iki_kapali_baslangic = zaman
                self._tek = None  # İkisi de kapandıysa bu bir tek göz kırpma değil
            elif zaman - self._iki_kapali_baslangic >= self.uzun_sinir and not self._mikro_uyku_bildirildi:
                self._mikro_uyku_bildirildi = True
                olaylar.append("mikro_uyku")
        elif self._iki_kapali_baslangic is not None:
            sure = zaman - self._iki_kapali_baslangic
            olaylar.append("dogal" if sure < self.dogal_sinir else "bilincli" if sure < self.uzun_sinir else "uzun")
            self._iki_kapali_baslangic = None
            self._mikro_uyku_bildirildi = False

        # Tek göz: biri kapanır, diğeri hep açık kalır
        if self._iki_kapali_baslangic is None:
            for i in (0, 1):
                if self.kapali[i] and not onceki[i] and not self.kapali[1 - i]:
                    self._tek = (i, zaman, True)
            if self._tek is not None:
                i, baslangic, temiz = self._tek
                if self.kapali[1 - i]:
                    temiz = False
                    self._tek = (i, baslangic, False)
                if not self.kapali[i]:
                    sure = zaman - baslangic
                    if temiz and self.tek_goz_min <= sure < self.tek_goz_max:
                        olaylar.append("goz_kirp_sol" if i == 0 else "goz_kirp_sag")
                    self._tek = None
        return olaylar


class YorgunlukIzleyici:
    """PERCLOS (gözlerin kapalı kaldığı zaman oranı), dakikadaki göz kırpma ve esneme.

    PERCLOS sürücü yorgunluğu araştırmalarında en çok kullanılan ölçüdür: son bir dakikada
    gözlerin kapalı olduğu zamanın oranı ~%15'i geçerse kişi yorgun kabul edilir.
    """

    def __init__(self, pencere=60.0, perclos_esigi=0.15, esneme_esigi=0.6, esneme_suresi=1.2,
                 uyari_araligi=30.0, en_az_veri=20.0):
        self.pencere = pencere
        self.perclos_esigi = perclos_esigi
        self.esneme_esigi = esneme_esigi
        self.esneme_suresi = esneme_suresi
        self.uyari_araligi = uyari_araligi
        self.en_az_veri = en_az_veri
        self._kareler = deque()  # (zaman, gözler kapalı mı)
        self._kirpmalar = deque()
        self._esneme_baslangic = None
        self._esnedi = False
        self._son_uyari = -math.inf
        self.esneme_sayisi = 0
        self.perclos = 0.0

    @property
    def kirpma_hizi(self):
        """Son penceredeki göz kırpma sayısı, dakikaya oranlanmış."""
        return len(self._kirpmalar) * 60.0 / self.pencere

    def guncelle(self, gozler_kapali, olaylar, agiz_acikligi, zaman):
        """Dönüş: bu karede verilecek uyarılar ("mikro_uyku", "yorgunluk", "esneme")."""
        self._kareler.append((zaman, gozler_kapali))
        while self._kareler and zaman - self._kareler[0][0] > self.pencere:
            self._kareler.popleft()
        self.perclos = sum(k for _, k in self._kareler) / len(self._kareler)
        for olay in olaylar:
            if olay in ("dogal", "bilincli"):
                self._kirpmalar.append(zaman)
        while self._kirpmalar and zaman - self._kirpmalar[0] > self.pencere:
            self._kirpmalar.popleft()

        uyarilar = []
        if agiz_acikligi > self.esneme_esigi:
            if self._esneme_baslangic is None:
                self._esneme_baslangic = zaman
            elif zaman - self._esneme_baslangic >= self.esneme_suresi and not self._esnedi:
                self._esnedi = True
                self.esneme_sayisi += 1
                uyarilar.append("esneme")
        else:
            self._esneme_baslangic, self._esnedi = None, False

        veri_suresi = zaman - self._kareler[0][0]
        if "mikro_uyku" in olaylar:
            uyarilar.append("mikro_uyku")
        elif (veri_suresi >= self.en_az_veri and self.perclos > self.perclos_esigi
              and zaman - self._son_uyari > self.uyari_araligi):
            self._son_uyari = zaman
            uyarilar.append("yorgunluk")
        return uyarilar
