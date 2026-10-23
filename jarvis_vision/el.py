"""MediaPipe Hand Landmarker'ı saran el takip modülü."""

import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .modeller import model_yolu

EL_BAGLANTILARI = [(b.start, b.end) for b in vision.HandLandmarksConnections.HAND_CONNECTIONS]

# Görüntü cv2.flip ile aynalandığında fiziksel sağ el MediaPipe'ta 'Left' görünür (Ders 1'de test edildi).
# Aynalama yoksa etiketler tersine döner.
AYNALI_TARAF = {"Left": "sag", "Right": "sol"}
AYNASIZ_TARAF = {"Left": "sol", "Right": "sag"}


@dataclass
class El:
    noktalar: np.ndarray  # (21, 3): piksel cinsinden x, y ve göreli derinlik z
    taraf: str  # "sag" / "sol" (kullanıcının kendi bakış açısından fiziksel el)
    skor: float


class ElTakipci:
    """Kareyi alır, bulunan elleri El listesi olarak döndürür.

    V1'de RunningMode.IMAGE kullanılıyordu: her kare sıfırdan "el ara" demekti.
    VIDEO modunda MediaPipe bir önceki karedeki eli takip eder, her karede tam
    tespit yapmaz. Hem daha hızlı hem de noktalar daha az titrer.
    """

    def __init__(self, max_el=2, tespit_guveni=0.6, takip_guveni=0.5, ayna=True):
        secenekler = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_yolu("el")),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_el,
            min_hand_detection_confidence=tespit_guveni,
            min_hand_presence_confidence=tespit_guveni,
            min_tracking_confidence=takip_guveni,
        )
        self._dedektor = vision.HandLandmarker.create_from_options(secenekler)
        self._taraf_esleme = AYNALI_TARAF if ayna else AYNASIZ_TARAF
        self._son_zaman_ms = -1

    def isle(self, kare_bgr):
        yukseklik, genislik = kare_bgr.shape[:2]
        rgb_kare = cv2.cvtColor(kare_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_kare)

        # VIDEO modu kesin artan zaman damgası ister
        zaman_ms = max(int(time.monotonic() * 1000), self._son_zaman_ms + 1)
        self._son_zaman_ms = zaman_ms
        sonuc = self._dedektor.detect_for_video(mp_image, zaman_ms)

        eller = []
        for el_noktalari, taraf in zip(sonuc.hand_landmarks, sonuc.handedness):
            # z, x ile aynı ölçekte gelir; bu yüzden genişlikle çarpılır
            noktalar = np.array(
                [[n.x * genislik, n.y * yukseklik, n.z * genislik] for n in el_noktalari], dtype=np.float32
            )
            eller.append(El(noktalar, self._taraf_esleme[taraf[0].category_name], taraf[0].score))
        return eller

    def kapat(self):
        self._dedektor.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.kapat()
