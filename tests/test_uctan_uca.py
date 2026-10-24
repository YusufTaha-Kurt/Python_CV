"""Uçtan uca duman testleri: her ders gerçek modellerle, kamerasız ve penceresiz çalıştırılır.

Kaynak olarak örnek fotoğraflardan üretilen videolar kullanılır. Örnek veriler ilk çalıştırmada
tests/.veri/ klasörüne indirilir. MediaPipe kurulu değilse (CI) ya da internet yoksa testler atlanır.

    pytest -m uctan_uca          # sadece bunlar
    pytest -m "not uctan_uca"    # bunlar hariç
"""

import os
import subprocess
import sys
import urllib.request

import numpy as np
import pytest

pytest.importorskip("mediapipe")
cv2 = pytest.importorskip("cv2")

pytestmark = pytest.mark.uctan_uca

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERI = os.path.join(KOK, "tests", ".veri")

ORNEKLER = {
    "zafer.jpg": "https://storage.googleapis.com/mediapipe-tasks/gesture_recognizer/victory.jpg",
    "isaret.jpg": "https://storage.googleapis.com/mediapipe-tasks/gesture_recognizer/pointing_up.jpg",
    "basparmak.jpg": "https://storage.googleapis.com/mediapipe-tasks/gesture_recognizer/thumbs_up.jpg",
    "yuz.png": "https://storage.googleapis.com/mediapipe-assets/business-person.png",
    "kedi_kopek.jpg": "https://storage.googleapis.com/mediapipe-tasks/object_detector/cat_and_dog.jpg",
    "poz.jpg": "https://cdn.pixabay.com/photo/2019/03/12/20/39/girl-4051811_960_720.jpg",
}


def _ornek(ad):
    yol = os.path.join(VERI, ad)
    if not os.path.exists(yol):
        os.makedirs(VERI, exist_ok=True)
        try:
            urllib.request.urlretrieve(ORNEKLER[ad], yol)
        except Exception as hata:
            pytest.skip(f"Örnek veri indirilemedi ({ad}): {hata}")
    return yol


def _yerlestir(tuval, gorsel, merkez_x, yukseklik=420):
    oran = yukseklik / gorsel.shape[0]
    kucuk = cv2.resize(gorsel, None, fx=oran, fy=oran)
    h, w = kucuk.shape[:2]
    x0 = int(np.clip(merkez_x - w // 2, 0, tuval.shape[1] - w))
    y0 = (tuval.shape[0] - h) // 2
    tuval[y0 : y0 + h, x0 : x0 + w] = kucuk


@pytest.fixture(scope="session")
def el_videosu():
    """Zafer, işaret ve başparmak fotoğraflarından, eli yatayda kaydıran 3 sn'lik video."""
    yol = os.path.join(VERI, "el_hareket.mp4")
    if os.path.exists(yol):
        return yol
    gorseller = [cv2.imread(_ornek(ad)) for ad in ("zafer.jpg", "isaret.jpg", "basparmak.jpg")]
    yazici = cv2.VideoWriter(yol, cv2.VideoWriter_fourcc(*"mp4v"), 30, (1280, 720))
    for i in range(90):
        tuval = np.full((720, 1280, 3), 40, np.uint8)
        _yerlestir(tuval, gorseller[i // 30], 300 + i * 8)
        yazici.write(tuval)
    yazici.release()
    return yol


def calistir(betik, *argumanlar, zaman_asimi=180):
    ortam = dict(os.environ, PYTHONPATH=KOK, PYTHONIOENCODING="utf-8")
    sonuc = subprocess.run(
        [sys.executable, os.path.join(KOK, betik), "--pencere-yok", "--sadece-izle", *argumanlar],
        cwd=KOK,
        env=ortam,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=zaman_asimi,
    )
    assert sonuc.returncode == 0, f"{betik} hata verdi:\n{sonuc.stdout[-2000:]}\n{sonuc.stderr[-4000:]}"
    return sonuc.stdout


@pytest.mark.parametrize(
    "betik",
    [
        "dersler/ders_02_fare_v2/fare_v2.py",
        "dersler/ders_03_jest_merkezi/jest_merkezi.py",
        "dersler/ders_04_medya_kontrol/medya_kontrol.py",
    ],
)
def test_el_dersleri(betik, el_videosu):
    calistir(betik, "--kaynak", el_videosu)


def test_jest_merkezi_olay_uretir(el_videosu):
    cikti = calistir("dersler/ders_03_jest_merkezi/jest_merkezi.py", "--kaynak", el_videosu)
    assert "el.goruldu" in cikti
    assert "jest.degisti" in cikti
