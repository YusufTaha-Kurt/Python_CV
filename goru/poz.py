"""Ders 16: MediaPipe Pose Landmarker ile 33 vücut noktası.

Noktalar baştan ayağa dağılır (0 burun, 11-12 omuzlar, 13-14 dirsekler, 15-16 bilekler,
23-24 kalçalar, 25-26 dizler, 27-28 ayak bilekleri). Her nokta için bir de "görünürlük"
skoru gelir: kadraj dışında ya da kapalı kalan noktaların güvenilmez olduğunu söyler.
"""

import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .modeller import model_yolu

POZ_BAGLANTILARI = [(b.start, b.end) for b in vision.PoseLandmarksConnections.POSE_LANDMARKS]


@dataclass
class Poz:
    """Tek bir kişinin duruşu."""

    noktalar: np.ndarray  # (33, 3) piksel
    gorunurluk: np.ndarray  # (33,) 0-1: nokta görünüyor mu (kadraj dışı / kapalıysa düşük)


class PozTakipci:
    """Kareyi alır, bulunan kişinin Poz listesini döndürür (ElTakipci ile aynı kullanım; tek kişi)."""

    def __init__(self, tespit_guveni=0.5, takip_guveni=0.5):
        secenekler = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_yolu("poz")),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=tespit_guveni,
            min_pose_presence_confidence=tespit_guveni,
            min_tracking_confidence=takip_guveni,
        )
        self._dedektor = vision.PoseLandmarker.create_from_options(secenekler)
        self._son_zaman_ms = -1

    def isle(self, kare_bgr, zaman=None):
        """zaman: karenin zamanı (sn)."""
        yukseklik, genislik = kare_bgr.shape[:2]
        goruntu = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(kare_bgr, cv2.COLOR_BGR2RGB))
        zaman_ms = max(int((time.monotonic() if zaman is None else zaman) * 1000), self._son_zaman_ms + 1)
        self._son_zaman_ms = zaman_ms
        sonuc = self._dedektor.detect_for_video(goruntu, zaman_ms)
        pozlar = []
        for noktalar in sonuc.pose_landmarks:
            dizi = np.array([[n.x * genislik, n.y * yukseklik, n.z * genislik] for n in noktalar], dtype=np.float32)
            gorunurluk = np.array([n.visibility or 0.0 for n in noktalar], dtype=np.float32)
            pozlar.append(Poz(dizi, gorunurluk))
        return pozlar

    def kapat(self):
        """Modeli serbest bırakır."""
        self._dedektor.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.kapat()


def poz_ciz(kare, poz, renk=(255, 220, 0), esik=0.5):
    """İskeleti çizer; görünürlüğü `esik` altındaki noktalar ve kemikler atlanır."""
    n, g = poz.noktalar, poz.gorunurluk
    for a, b in POZ_BAGLANTILARI:
        if g[a] > esik and g[b] > esik:
            cv2.line(kare, tuple(int(v) for v in n[a, :2]), tuple(int(v) for v in n[b, :2]), renk, 2, cv2.LINE_AA)
    for i in range(len(n)):
        if g[i] > esik:
            cv2.circle(kare, (int(n[i, 0]), int(n[i, 1])), 4, (255, 255, 255), -1, cv2.LINE_AA)
