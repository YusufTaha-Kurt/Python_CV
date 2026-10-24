"""Ders 15: IoU tabanlı çoklu nesne takibi (SORT algoritmasının sadeleştirilmiş hali).

Dedektör her karede nesneleri bağımsız bulur; hangi kutunun önceki karedeki hangi kutu
olduğunu bilmez. Takipçi her nesneye kalıcı bir kimlik (ID) verir:

  1. Tahmin: Her iz, son hızıyla bir kare ileri taşınır (sabit hız modeli).
  2. Eşleştirme: Aynı sınıftaki iz-tespit çiftleri IoU'ya (kesişim / birleşim) göre açgözlü
     eşleştirilir.
  3. Güncelleme: Eşleşen izler yeni kutuya geçer; eşleşmeyenler birkaç kare tahminle
     yaşatılır (dedektör bir an kaçırsa da ID değişmesin), eşleşmeyen tespitler yeni iz olur.
  4. Kesinleşme: Yeni iz ancak birkaç kare üst üste görülünce gösterilir (tek karelik sahte
     tespitler elenir).
"""

from dataclasses import dataclass, field

import numpy as np


def iou(a, b):
    """İki kutunun (x0, y0, x1, y1) kesişim / birleşim oranı."""
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    kesisim = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    birlesim = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - kesisim
    return kesisim / birlesim if birlesim > 0 else 0.0


@dataclass
class Iz:
    """Takip edilen bir nesnenin kaydı. `kayip`: art arda kaç karedir eşleşmedi."""

    id: int
    kutu: np.ndarray
    etiket: str
    skor: float
    hiz: np.ndarray = field(default_factory=lambda: np.zeros(4))
    gorulme: int = 1
    kayip: int = 0


class IoUTakipci:
    """Her karede `guncelle(tespitler)` çağır; kalıcı kimlikli (ID) nesne listesi al.

    `.yeni` o karede ilk kez kesinleşen, `.biten` kaybolan nesneleri verir (olay üretmek için).
    """

    def __init__(self, iou_esigi=0.3, max_kayip=15, min_gorulme=3):
        self.iou_esigi = iou_esigi
        self.max_kayip = max_kayip
        self.min_gorulme = min_gorulme
        self.izler = []
        self.yeni = []  # Bu karede kesinleşen izler
        self.biten = []  # Bu karede silinen (daha önce kesinleşmiş) izler
        self._sonraki_id = 1

    def guncelle(self, tespitler):
        """tespitler: .kutu, .etiket, .skor alanları olan nesneler. Dönüş: görünür, kesin izler."""
        self.yeni, self.biten = [], []
        # 1) Tahmin: her izi son hızıyla bir kare ileri taşı
        tahminler = [iz.kutu + iz.hiz for iz in self.izler]

        # 2) Eşleştirme: en yüksek IoU'dan başlayarak açgözlü eşle (her iz / tespit en çok bir kez)
        ciftler = sorted(
            ((iou(tahmin, t.kutu), i, k) for i, (iz, tahmin) in enumerate(zip(self.izler, tahminler))
             for k, t in enumerate(tespitler) if iz.etiket == t.etiket),
            reverse=True,
        )
        eslesen_iz, eslesen_tespit = set(), set()
        for deger, i, k in ciftler:
            if deger < self.iou_esigi:
                break
            if i in eslesen_iz or k in eslesen_tespit:
                continue
            eslesen_iz.add(i)
            eslesen_tespit.add(k)
            iz, yeni_kutu = self.izler[i], np.asarray(tespitler[k].kutu, dtype=float)
            iz.hiz = 0.6 * iz.hiz + 0.4 * (yeni_kutu - iz.kutu)
            iz.kutu, iz.skor, iz.kayip = yeni_kutu, tespitler[k].skor, 0
            iz.gorulme += 1
            if iz.gorulme == self.min_gorulme:
                self.yeni.append(iz)

        # 3) Eşleşmeyen izleri birkaç kare yaşat, yeni tespitlere yeni ID ver
        kalan = []
        for i, iz in enumerate(self.izler):
            if i not in eslesen_iz:
                iz.kayip += 1
                iz.kutu = tahminler[i]  # Görülmedi: tahminle ilerlet
                iz.hiz *= 0.5
            if iz.kayip <= self.max_kayip:
                kalan.append(iz)
            elif iz.gorulme >= self.min_gorulme:
                self.biten.append(iz)
        for k, t in enumerate(tespitler):
            if k not in eslesen_tespit:
                kalan.append(Iz(self._sonraki_id, np.asarray(t.kutu, dtype=float), t.etiket, t.skor))
                self._sonraki_id += 1
                if self.min_gorulme <= 1:
                    self.yeni.append(kalan[-1])
        self.izler = kalan
        return [iz for iz in self.izler if iz.gorulme >= self.min_gorulme and iz.kayip <= 3]
