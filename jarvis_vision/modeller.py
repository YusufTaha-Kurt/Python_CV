"""MediaPipe model dosyalarını ilk kullanımda indirir ve models/ klasöründe saklar."""

import os
import urllib.request

# Depo kökündeki models/ klasörü (.gitignore'da, GitHub'a yüklenmez)
MODEL_KLASORU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

MODELLER = {
    "el": (
        "hand_landmarker.task",
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    ),
    "yuz": (
        "face_landmarker.task",
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
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
