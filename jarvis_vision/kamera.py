"""Gecikmesi düşük, thread'li kamera okuyucu."""

import sys
import threading

import cv2


class Kamera:
    """Kameradan arka planda sürekli kare okur, ana döngüye hep EN GÜNCEL kareyi verir.

    cv2.VideoCapture.read() bloklayan bir çağrıdır ve sürücü kareleri tamponda biriktirir.
    Ana döngü yapay zeka ile meşgulken biriken eski kareler gecikme (latency) demektir.
    Okumayı ayrı bir thread'e taşıyınca eski kareler atlanır, el ile imleç arasındaki
    gecikme düşer.
    """

    def __init__(self, indeks=0, genislik=1280, yukseklik=720, fps=60, ayna=True):
        # Windows'ta DirectShow hem daha hızlı açılır hem de MJPG (yüksek FPS) destekler
        api = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self._kamera = cv2.VideoCapture(indeks, api)
        if not self._kamera.isOpened():
            raise RuntimeError(f"Kamera açılamadı (indeks={indeks}). Farklı bir indeks deneyin: --kamera 1")

        # Sıkıştırılmamış YUY2 formatında çoğu webcam 720p'de 10-15 FPS'e düşer, MJPG ile 30-60 FPS verir.
        # FOURCC ayarı çözünürlükten ÖNCE yapılmalı.
        self._kamera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._kamera.set(cv2.CAP_PROP_FRAME_WIDTH, genislik)
        self._kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, yukseklik)
        self._kamera.set(cv2.CAP_PROP_FPS, fps)
        self._kamera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.ayna = ayna
        self._kare = None
        self._kare_no = 0
        self._son_verilen_no = 0
        self._calisiyor = True
        self._kosul = threading.Condition()
        self._thread = threading.Thread(target=self._oku_dongusu, daemon=True)
        self._thread.start()

    @property
    def cozunurluk(self):
        return int(self._kamera.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self._kamera.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def _oku_dongusu(self):
        while self._calisiyor:
            basarili, kare = self._kamera.read()
            with self._kosul:
                if not basarili:
                    self._calisiyor = False
                else:
                    self._kare = kare
                    self._kare_no += 1
                self._kosul.notify_all()

    def oku(self, zaman_asimi=2.0):
        """Bir önceki çağrıdan sonra gelen yeni kareyi bekler ve döndürür. Kamera kapandıysa None."""
        with self._kosul:
            yeni_var = self._kosul.wait_for(
                lambda: self._kare_no != self._son_verilen_no or not self._calisiyor, zaman_asimi
            )
            if not yeni_var or self._kare_no == self._son_verilen_no:
                return None
            self._son_verilen_no = self._kare_no
            kare = self._kare
        # read() her seferinde yeni bir dizi döndürdüğü için kilidin dışında işlemek güvenli
        return cv2.flip(kare, 1) if self.ayna else kare

    def kapat(self):
        self._calisiyor = False
        self._thread.join(timeout=1.0)
        self._kamera.release()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.kapat()
