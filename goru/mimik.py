"""Ders 11: Yüz ifadeleriyle komut. MediaPipe'ın 52 ifade skorundan (blendshape) üst düzey ifadeler.

Herkesin "nötr" yüzü farklıdır: bazı insanların ağız kenarları doğal olarak yukarıdadır,
bazılarının kaşları hep biraz kalkıktır, sakal / bıyık bazı skorları kaydırır. Bu yüzden her
skor kişinin nötr tabanına göre yeniden ölçeklenir:

    skor = (ham - taban) / (1 - taban)

Taban iki aşamada bulunur:
  1. Kalibrasyon: ilk birkaç saniyenin medyanı (kullanıcı ifadesiz durur).
  2. Uyarlanır taban: Kalibrasyon anında el yüzdeyse ya da kullanıcı gülümsüyorsa taban
     kirlenir. İnsanlar zamanlarının çoğunu nötr yüzle geçirdiği için son 30 saniyenin
     %30'luk dilimi nötr yüzü iyi tahmin eder; taban buna doğru sürekli düzeltilir.
"""

import statistics
from collections import deque

import numpy as np

# Üst düzey ifade → MediaPipe blendshape adları. Birden çok ad varsa skorların ortalaması alınır
# (örn. sol ve sağ dudak köşesi). Yeni bir ifade eklemek için buraya bir satır yeter.
IFADELER = {
    "gulumseme": ("mouthSmileLeft", "mouthSmileRight"),
    "kas_kaldirma": ("browInnerUp", "browOuterUpLeft", "browOuterUpRight"),
    "kas_catma": ("browDownLeft", "browDownRight"),
    "agiz_acma": ("jawOpen",),
    "dudak_buzme": ("mouthPucker",),
    "yanak_sisirme": ("cheekPuff",),
}
_ADLAR = sorted({ad for adlar in IFADELER.values() for ad in adlar})
# Kasıtsız da sık yapılan ifadeler için daha sıkı eşik ve daha uzun tutma süresi.
# Dudak büzmek dikkat toplarken çok yapılır (gerçek videoda gözlük düzeltirken tetiklendi).
OZEL_ESIKLER = {"dudak_buzme": (0.7, 0.6)}  # ifade: (eşik, süre)


def el_yuzu_kapatiyor(yuz, eller, oran=0.3):
    """Bir elin noktalarının en az `oran`ı yüz kutusunun içindeyse True.

    El yüzü kapattığında model görmediği ağzı / kaşları "uydurur"; o anki ifadeler güvenilmez.
    """
    x0, y0, x1, y1 = yuz.kutu()
    for el in eller:
        n = el.noktalar
        icinde = (n[:, 0] > x0) & (n[:, 0] < x1) & (n[:, 1] > y0) & (n[:, 1] < y1)
        if icinde.mean() >= oran:
            return True
    return False


class MimikAlgilayici:
    """`guncelle()` her kare çağrılır; bu karede tetiklenen ifadelerin listesini döndürür.

    Bir ifade skoru `esik`i `sure` boyunca aşınca bir kez tetiklenir (kenar tetikleme) ve
    skor `birakma`nın altına inene kadar yeniden tetiklenmez (histerezis).
    """

    def __init__(self, esik=0.5, birakma=0.3, sure=0.4, kalibrasyon_suresi=2.0, taban_penceresi=30.0):
        self.esik = esik
        self.birakma = birakma
        self.sure = sure
        self.kalibrasyon_suresi = kalibrasyon_suresi
        self.taban_penceresi = taban_penceresi
        self.taban = {}
        self.skorlar = {ifade: 0.0 for ifade in IFADELER}
        self.aktif = set()
        self._esik_ustu = {}
        self._kalibrasyon = None
        self._kal_baslangic = None
        self._gecmis = deque()  # (zaman, {ad: ham değer}) uyarlanır taban için
        self._sayac = 0

    @property
    def kalibre_ediliyor(self):
        """Nötr yüz şu an ölçülüyor mu? (Bu sürede komut tetiklenmez.)"""
        return self._kalibrasyon is not None

    def kalibre_et(self):
        """Nötr yüzü yeniden ölç (kullanıcı birkaç saniye ifadesiz durmalı)."""
        self._kalibrasyon, self._kal_baslangic = [], None
        self._gecmis.clear()
        self.aktif.clear()
        self._esik_ustu.clear()

    def kalibrasyon_ilerlemesi(self, zaman):
        """Kalibrasyonun tamamlanma oranı (0-1); bittiyse 1."""
        if not self.kalibre_ediliyor or self._kal_baslangic is None:
            return 0.0 if self.kalibre_ediliyor else 1.0
        return min(1.0, (zaman - self._kal_baslangic) / self.kalibrasyon_suresi)

    def _taban_guncelle(self, ifadeler, zaman):
        """Son 30 sn'lik geçmişin %30'luk diliminden nötr tabanı sürekli yeniden tahmin eder."""
        self._sayac += 1
        if self._sayac % 3:  # Her 3 karede bir örnek yeter
            return
        self._gecmis.append((zaman, {ad: ifadeler.get(ad, 0.0) for ad in _ADLAR}))
        while self._gecmis and zaman - self._gecmis[0][0] > self.taban_penceresi:
            self._gecmis.popleft()
        if len(self._gecmis) >= 20 and not self.kalibre_ediliyor:  # En az ~2 sn veri
            for ad in _ADLAR:
                self.taban[ad] = float(np.percentile([o[ad] for _, o in self._gecmis], 30))

    def guncelle(self, ifadeler, zaman, engel=False):
        """engel=True: yüz kapalı (örn. el yüzde); skorlar hesaplanır ama yeni komut tetiklenmez."""
        if self.kalibre_ediliyor:
            if self._kal_baslangic is None:
                self._kal_baslangic = zaman
            self._kalibrasyon.append(dict(ifadeler))
            if not engel:
                self._taban_guncelle(ifadeler, zaman)  # Uyarlanır taban da şimdiden dolmaya başlasın
            if zaman - self._kal_baslangic >= self.kalibrasyon_suresi:
                self.taban = {ad: statistics.median(o.get(ad, 0.0) for o in self._kalibrasyon) for ad in _ADLAR}
                self._kalibrasyon = None
            return []
        if not engel:
            self._taban_guncelle(ifadeler, zaman)

        # Her ifade için: tabana göre ölçekle → eşiği SÜRE boyunca aşarsa bir kez tetikle
        yeni = []
        for ifade, adlar in IFADELER.items():
            degerler = []
            for ad in adlar:
                taban = self.taban.get(ad, 0.0)
                degerler.append((ifadeler.get(ad, 0.0) - taban) / max(1.0 - taban, 0.1))
            skor = min(1.0, max(0.0, sum(degerler) / len(degerler)))
            self.skorlar[ifade] = skor
            esik, sure = OZEL_ESIKLER.get(ifade, (self.esik, self.sure))

            if ifade in self.aktif:
                if skor < self.birakma:
                    self.aktif.discard(ifade)
            elif skor >= esik and not engel:
                baslangic = self._esik_ustu.setdefault(ifade, zaman)
                if zaman - baslangic >= sure:
                    self.aktif.add(ifade)
                    del self._esik_ustu[ifade]
                    yeni.append(ifade)
            else:
                self._esik_ustu.pop(ifade, None)
        return yeni
