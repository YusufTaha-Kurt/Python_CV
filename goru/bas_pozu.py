"""Ders 9: Baş pozu (yaw / pitch / roll) iki yoldan.

1. `matris_acilari`: MediaPipe'ın yüz dönüşüm matrisinden. Hızlı ve kararlı; varsayılan.
2. `pnp_acilari`: Klasik yöntem. 6 yüz noktasının genel bir 3D yüz modelindeki konumlarıyla
   görüntüdeki konumları eşleştirilir ve kamera pozu cv2.solvePnP ile çözülür. Kamera
   kalibrasyonu yoksa odak uzaklığı ~ görüntü genişliği varsayılır.

İşaret kuralı (ekranda görünen, yani aynalanmış görüntüye göre):
    yaw   > 0   Yüz ekranın sağına dönük
    pitch > 0   Yüz yukarı bakıyor
    roll  > 0   Baş ekranın sağına yatık (saat yönü)
"""

import math

import numpy as np

# solvePnP için 6 nokta: (MediaPipe indeksi, genel yüz modelindeki konum; burun ucu orijin, y yukarı)
PNP_NOKTALARI = [
    (1, (0.0, 0.0, 0.0)),  # Burun ucu
    (152, (0.0, -330.0, -65.0)),  # Çene
    (33, (-225.0, 170.0, -135.0)),  # Görüntünün solundaki gözün dış köşesi
    (263, (225.0, 170.0, -135.0)),  # Görüntünün sağındaki gözün dış köşesi
    (61, (-150.0, -150.0, -125.0)),  # Ağzın sol köşesi
    (291, (150.0, -150.0, -125.0)),  # Ağzın sağ köşesi
]


def matris_acilari(donusum):
    """4x4 dönüşüm matrisinden (yaw, pitch, roll) derece.

    Matrisin 3. sütunu yüzün baktığı yön (kamera koordinatında, y yukarı),
    1. sütunu yüzün "sağ" ekseni.
    """
    r = np.asarray(donusum)[:3, :3]
    ileri, sag = r[:, 2], r[:, 0]
    yaw = math.degrees(math.atan2(ileri[0], ileri[2]))
    pitch = math.degrees(math.asin(float(np.clip(ileri[1], -1, 1))))
    roll = -math.degrees(math.atan2(sag[1], sag[0]))
    return yaw, pitch, roll


def pnp_acilari(noktalar, kare_boyutu):
    """Yüz noktalarından solvePnP ile (yaw, pitch, roll) derece. Çözülemezse None."""
    import cv2

    genislik, yukseklik = kare_boyutu
    model = np.array([p for _, p in PNP_NOKTALARI], dtype=np.float64)
    goruntu = np.array([noktalar[i, :2] for i, _ in PNP_NOKTALARI], dtype=np.float64)
    kamera = np.array([[genislik, 0, genislik / 2], [0, genislik, yukseklik / 2], [0, 0, 1]], dtype=np.float64)
    basarili, rvec, _ = cv2.solvePnP(model, goruntu, kamera, np.zeros(4), flags=cv2.SOLVEPNP_ITERATIVE)
    if not basarili:
        return None
    r, _ = cv2.Rodrigues(rvec)
    # Model y-yukarı, görüntü y-aşağı: OpenCV kamera koordinatını (y aşağı, z ileri) y-yukarı,
    # z kameraya doğru bir eksen takımına çevirip matris_acilari ile aynı kuralı uygula
    donusum = np.eye(4)
    donusum[:3, :3] = np.diag([1, -1, -1]) @ r
    return matris_acilari(donusum)


def yuz_acilari(yuz, kare_boyutu=None):
    """(yaw, pitch, roll) derece. Yüzün açıları: dönüşüm matrisi varsa onu, yoksa solvePnP'yi kullanır."""
    if yuz.donusum is not None:
        return matris_acilari(yuz.donusum)
    return pnp_acilari(yuz.noktalar, kare_boyutu)
