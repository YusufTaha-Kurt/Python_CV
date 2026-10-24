"""Model dosyalarını ilk kullanımda indirir ve models/ klasöründe saklar."""

import os
import urllib.request

# Depo kökündeki models/ klasörü (.gitignore'da, GitHub'a yüklenmez)
MODEL_KLASORU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

_MEDIAPIPE = "https://storage.googleapis.com/mediapipe-models"
_OPENCV_ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"

MODELLER = {
    # MediaPipe (Apache 2.0)
    "el": ("hand_landmarker.task", f"{_MEDIAPIPE}/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"),
    "yuz": ("face_landmarker.task", f"{_MEDIAPIPE}/face_landmarker/face_landmarker/float16/1/face_landmarker.task"),
    "poz": (
        "pose_landmarker_lite.task",
        f"{_MEDIAPIPE}/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
    ),
    "nesne": (
        "efficientdet_lite0.tflite",
        f"{_MEDIAPIPE}/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite",
    ),
    # OpenCV Zoo: YuNet yüz dedektörü (MIT) ve SFace yüz tanıma (Apache 2.0)
    "yunet": (
        "face_detection_yunet_2023mar.onnx",
        f"{_OPENCV_ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    ),
    "sface": (
        "face_recognition_sface_2021dec.onnx",
        f"{_OPENCV_ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    ),
}


def model_yolu(ad):
    """Modelin yerel yolunu döndürür, dosya yoksa önce indirir."""
    dosya_adi, url = MODELLER[ad]
    yol = os.path.join(MODEL_KLASORU, dosya_adi)
    if not os.path.exists(yol):
        os.makedirs(MODEL_KLASORU, exist_ok=True)
        print(f"'{dosya_adi}' modeli indiriliyor... Lütfen bekleyin.")
        # Önce geçici dosyaya indir: indirme yarıda kesilirse bozuk model kalmasın
        gecici_yol = yol + ".indiriliyor"
        urllib.request.urlretrieve(url, gecici_yol)
        os.replace(gecici_yol, yol)
        print("Model başarıyla indirildi!")
    return yol
