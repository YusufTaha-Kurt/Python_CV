"""Ders 15: Nesne tespiti (MediaPipe Object Detector, EfficientDet-Lite0, COCO'nun 80 sınıfı)
ve parmakla işaret edilen nesneyi bulma.

Dedektör her kareye bakıp "şurada %80 ihtimalle fincan var" diyen kutular üretir. Hafıza yoktur:
hangi kutunun önceki karedeki hangi nesne olduğunu bilmez (bunu takip.py çözer).
COCO sınıf adları İngilizcedir; ekranda göstermek için aşağıdaki TURKCE sözlüğü kullanılır.
"""

import time
from dataclasses import dataclass

import numpy as np

from . import jestler as j

# Ekranda cv2.putText ile yazılacağı için ASCII (Türkçe karakter yok)
TURKCE = {
    "person": "insan", "bicycle": "bisiklet", "car": "araba", "motorcycle": "motosiklet", "airplane": "ucak",
    "bus": "otobus", "train": "tren", "truck": "kamyon", "boat": "tekne", "traffic light": "trafik isigi",
    "fire hydrant": "yangin muslugu", "stop sign": "dur isareti", "parking meter": "park sayaci", "bench": "bank",
    "bird": "kus", "cat": "kedi", "dog": "kopek", "horse": "at", "sheep": "koyun", "cow": "inek",
    "elephant": "fil", "bear": "ayi", "zebra": "zebra", "giraffe": "zurafa", "backpack": "sirt cantasi",
    "umbrella": "semsiye", "handbag": "el cantasi", "tie": "kravat", "suitcase": "bavul", "frisbee": "frizbi",
    "skis": "kayak", "snowboard": "snowboard", "sports ball": "top", "kite": "ucurtma",
    "baseball bat": "beyzbol sopasi", "baseball glove": "beyzbol eldiveni", "skateboard": "kaykay",
    "surfboard": "sorf tahtasi", "tennis racket": "tenis raketi", "bottle": "sise", "wine glass": "kadeh",
    "cup": "fincan", "fork": "catal", "knife": "bicak", "spoon": "kasik", "bowl": "kase", "banana": "muz",
    "apple": "elma", "sandwich": "sandvic", "orange": "portakal", "broccoli": "brokoli", "carrot": "havuc",
    "hot dog": "sosisli", "pizza": "pizza", "donut": "donut", "cake": "pasta", "chair": "sandalye",
    "couch": "kanepe", "potted plant": "saksi bitkisi", "bed": "yatak", "dining table": "masa",
    "toilet": "klozet", "tv": "televizyon", "laptop": "dizustu", "mouse": "fare", "remote": "kumanda",
    "keyboard": "klavye", "cell phone": "telefon", "microwave": "mikrodalga", "oven": "firin",
    "toaster": "ekmek kizartma", "sink": "lavabo", "refrigerator": "buzdolabi", "book": "kitap",
    "clock": "saat", "vase": "vazo", "scissors": "makas", "teddy bear": "oyuncak ayi",
    "hair drier": "sac kurutma", "toothbrush": "dis fircasi",
}


@dataclass
class Tespit:
    """Tek bir tespit: nerede (kutu), ne (etiket) ve ne kadar emin (skor)."""

    kutu: tuple  # (x0, y0, x1, y1) piksel
    etiket: str  # COCO adı (İngilizce)
    skor: float

    @property
    def ad(self):
        """Türkçe (ASCII) ad; sözlükte yoksa İngilizce etiket."""
        return TURKCE.get(self.etiket, self.etiket)


class NesneDedektoru:
    """`skor_esigi`: bundan emin olmadığı tespitleri at. `izinli`: sadece bu sınıfları ara (örn. ["cup", "bottle"])."""

    def __init__(self, skor_esigi=0.4, max_sonuc=10, izinli=None):
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        from .modeller import model_yolu

        self._cv2, self._mp = cv2, mp
        secenekler = vision.ObjectDetectorOptions(
            base_options=python.BaseOptions(model_asset_path=model_yolu("nesne")),
            running_mode=vision.RunningMode.VIDEO,
            max_results=max_sonuc,
            score_threshold=skor_esigi,
            category_allowlist=list(izinli) if izinli else None,
        )
        self._dedektor = vision.ObjectDetector.create_from_options(secenekler)
        self._son_zaman_ms = -1

    def isle(self, kare_bgr, zaman=None):
        """Karedeki nesneleri Tespit listesi olarak döndürür."""
        goruntu = self._mp.Image(image_format=self._mp.ImageFormat.SRGB,
                                 data=self._cv2.cvtColor(kare_bgr, self._cv2.COLOR_BGR2RGB))
        zaman_ms = max(int((time.monotonic() if zaman is None else zaman) * 1000), self._son_zaman_ms + 1)
        self._son_zaman_ms = zaman_ms
        sonuc = self._dedektor.detect_for_video(goruntu, zaman_ms)
        tespitler = []
        for t in sonuc.detections:
            b = t.bounding_box
            kutu = (float(b.origin_x), float(b.origin_y), float(b.origin_x + b.width), float(b.origin_y + b.height))
            tespitler.append(Tespit(kutu, t.categories[0].category_name, float(t.categories[0].score)))
        return tespitler

    def kapat(self):
        """Modeli serbest bırakır."""
        self._dedektor.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.kapat()


def _isin_kutu(baslangic, yon, kutu):
    """Işının kutuya girdiği mesafe (slab yöntemi). Kesişmiyorsa None."""
    t_min, t_max = 0.0, np.inf
    for eksen in (0, 1):
        alt, ust = kutu[eksen], kutu[eksen + 2]
        if abs(yon[eksen]) < 1e-9:
            if not alt <= baslangic[eksen] <= ust:
                return None
            continue
        t1, t2 = (alt - baslangic[eksen]) / yon[eksen], (ust - baslangic[eksen]) / yon[eksen]
        t_min, t_max = max(t_min, min(t1, t2)), min(t_max, max(t1, t2))
        if t_min > t_max:
            return None
    return t_min


def isaret_edilen(el_noktalari, kutular):
    """Parmağın gösterdiği kutunun anahtarını döndürür. kutular: {anahtar: (x0, y0, x1, y1)}

    Önce parmak ucunun içinde olduğu kutu (birden çoksa en küçüğü), yoksa işaret parmağının
    kökünden ucuna uzanan ışının ilk çarptığı kutu.
    """
    uc = el_noktalari[j.ISARET_UCU, :2].astype(float)
    kok = el_noktalari[j.ISARET_KOK, :2].astype(float)
    icinde = [(k, (b[2] - b[0]) * (b[3] - b[1])) for k, b in kutular.items()
              if b[0] <= uc[0] <= b[2] and b[1] <= uc[1] <= b[3]]
    if icinde:
        return min(icinde, key=lambda x: x[1])[0]
    yon = uc - kok
    if np.linalg.norm(yon) < 1e-6:
        return None
    yon /= np.linalg.norm(yon)
    carpanlar = [(k, t) for k, b in kutular.items() if (t := _isin_kutu(uc, yon, b)) is not None]
    return min(carpanlar, key=lambda x: x[1])[0] if carpanlar else None
