"""Ders 9: MediaPipe Face Landmarker'ı saran yüz takip modülü (478 nokta + 52 ifade skoru)."""

import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .modeller import model_yolu

_B = vision.FaceLandmarksConnections
YUZ_KONTURLARI = [(b.start, b.end) for b in _B.FACE_LANDMARKS_CONTOURS]
IRIS_BAGLANTILARI = [(b.start, b.end) for b in _B.FACE_LANDMARKS_LEFT_IRIS + _B.FACE_LANDMARKS_RIGHT_IRIS]


@dataclass
class Yuz:
    noktalar: np.ndarray  # (478, 3): piksel cinsinden x, y ve göreli derinlik z
    ifadeler: dict  # Blendshape adı -> skor (0-1), örn. "jawOpen", "mouthSmileLeft"
    donusum: np.ndarray  # 4x4: kanonik yüz modelinden kamera koordinatına dönüşüm (None olabilir)

    def kutu(self):
        """(x0, y0, x1, y1) piksel"""
        x0, y0 = self.noktalar[:, :2].min(axis=0)
        x1, y1 = self.noktalar[:, :2].max(axis=0)
        return float(x0), float(y0), float(x1), float(y1)


class YuzTakipci:
    def __init__(self, max_yuz=1, tespit_guveni=0.5, takip_guveni=0.5):
        secenekler = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_yolu("yuz")),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=max_yuz,
            min_face_detection_confidence=tespit_guveni,
            min_face_presence_confidence=tespit_guveni,
            min_tracking_confidence=takip_guveni,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self._dedektor = vision.FaceLandmarker.create_from_options(secenekler)
        self._son_zaman_ms = -1

    def isle(self, kare_bgr, zaman=None):
        yukseklik, genislik = kare_bgr.shape[:2]
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(kare_bgr, cv2.COLOR_BGR2RGB))
        zaman_ms = max(int((time.monotonic() if zaman is None else zaman) * 1000), self._son_zaman_ms + 1)
        self._son_zaman_ms = zaman_ms
        sonuc = self._dedektor.detect_for_video(mp_image, zaman_ms)

        yuzler = []
        for i, noktalar in enumerate(sonuc.face_landmarks):
            dizi = np.array([[n.x * genislik, n.y * yukseklik, n.z * genislik] for n in noktalar], dtype=np.float32)
            ifadeler = {k.category_name: float(k.score) for k in sonuc.face_blendshapes[i]} if sonuc.face_blendshapes else {}
            donusum = np.array(sonuc.facial_transformation_matrixes[i]) if sonuc.facial_transformation_matrixes else None
            yuzler.append(Yuz(dizi, ifadeler, donusum))
        return yuzler

    def kapat(self):
        self._dedektor.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.kapat()


def yuz_ciz(kare, yuz, renk=(255, 220, 0)):
    n = yuz.noktalar
    for a, b in YUZ_KONTURLARI:
        cv2.line(kare, tuple(int(v) for v in n[a, :2]), tuple(int(v) for v in n[b, :2]), renk, 1, cv2.LINE_AA)
    for a, b in IRIS_BAGLANTILARI:
        cv2.line(kare, tuple(int(v) for v in n[a, :2]), tuple(int(v) for v in n[b, :2]), (255, 255, 255), 1, cv2.LINE_AA)
