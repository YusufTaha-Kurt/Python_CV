"""Kare kaynağı: canlı kamera, video dosyası ya da görsel dosyası."""

import os
import sys
import threading
import time

import cv2

GORSEL_UZANTILARI = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
YENIDEN_BAGLANMA_ARALIGI = 2.0  # saniye


def kaynak_coz(kaynak):
    """'0' veya 0 -> kamera indeksi, diğer her şey -> dosya yolu."""
    if isinstance(kaynak, int):
        return kaynak
    kaynak = str(kaynak)
    return int(kaynak) if kaynak.isdigit() else kaynak


class Kamera:
    """Üç tür kaynağı aynı arayüzle sunar: `oku()` bir kare, `zaman` o karenin zamanı (sn).

    * Kamera (indeks): Okuma ayrı thread'de yapılır. cv2.VideoCapture.read() bloklayan bir
      çağrıdır ve sürücü kareleri tamponda biriktirir; thread sayesinde eski kareler atlanır,
      ana döngü hep EN GÜNCEL kareyi alır. Kamera koparsa (USB çıkarıldı, başka uygulama aldı)
      `yeniden_baglan` açıksa birkaç saniyede bir yeniden açmayı dener: 7/24 çalışma için şart.
    * Video dosyası: Kareler sırayla, hiçbiri atlanmadan okunur. `zaman` videonun kendi
      zamanıdır; böylece kayıttan yapılan testler gerçek zamanlı çalışmayla aynı sonucu verir.
    * Görsel dosyası: Aynı görsel 30 FPS'lik bir video gibi tekrar tekrar verilir.
    """

    def __init__(self, kaynak=0, genislik=1280, yukseklik=720, fps=60, ayna=True, yeniden_baglan=True):
        self.kaynak = kaynak_coz(kaynak)
        self.ayna = ayna
        self.bitti = False
        self.zaman = 0.0
        self._kare_no = 0
        self._kamera = self._video = self._gorsel = None

        if isinstance(self.kaynak, int):
            self._ayarlar = (genislik, yukseklik, fps)
            self._yeniden_baglan = yeniden_baglan
            self._kamera = self._kamera_ac()
            if self._kamera is None:
                raise RuntimeError(f"Kamera açılamadı (indeks={self.kaynak}). Farklı bir indeks deneyin: --kaynak 1")
            self._kare = None
            self._kare_zamani = 0.0
            self._son_verilen_no = 0
            self._durdur = threading.Event()
            self._kosul = threading.Condition()
            self._thread = threading.Thread(target=self._oku_dongusu, daemon=True)
            self._thread.start()
        elif os.path.splitext(self.kaynak)[1].lower() in GORSEL_UZANTILARI:
            self._gorsel = cv2.imread(self.kaynak)
            if self._gorsel is None:
                raise RuntimeError(f"Görsel okunamadı: {self.kaynak}")
            self._video_fps = 30.0
        else:
            self._video = cv2.VideoCapture(self.kaynak)
            if not self._video.isOpened():
                raise RuntimeError(f"Video açılamadı: {self.kaynak}")
            self._video_fps = self._video.get(cv2.CAP_PROP_FPS) or 30.0

    def _kamera_ac(self):
        # Windows'ta DirectShow hem daha hızlı açılır hem de MJPG (yüksek FPS) destekler
        api = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        kamera = cv2.VideoCapture(self.kaynak, api)
        if not kamera.isOpened():
            kamera.release()
            return None
        genislik, yukseklik, fps = self._ayarlar
        # Sıkıştırılmamış YUY2 formatında çoğu webcam 720p'de 10-15 FPS'e düşer, MJPG ile 30-60 FPS verir.
        # FOURCC ayarı çözünürlükten ÖNCE yapılmalı.
        kamera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        kamera.set(cv2.CAP_PROP_FRAME_WIDTH, genislik)
        kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, yukseklik)
        kamera.set(cv2.CAP_PROP_FPS, fps)
        kamera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return kamera

    def _oku_dongusu(self):
        while not self._durdur.is_set():
            basarili, kare = self._kamera.read() if self._kamera is not None else (False, None)
            if basarili:
                with self._kosul:
                    self._kare, self._kare_zamani = kare, time.monotonic()
                    self._kare_no += 1
                    self._kosul.notify_all()
                continue
            if not self._yeniden_baglan:
                with self._kosul:
                    self.bitti = True
                    self._kosul.notify_all()
                return
            # Kamera koptu: bırak, biraz bekle, yeniden açmayı dene
            if self._kamera is not None:
                self._kamera.release()
                self._kamera = None
                print("[Kamera] Bağlantı koptu, yeniden bağlanılıyor...")
            if self._durdur.wait(YENIDEN_BAGLANMA_ARALIGI):
                return
            self._kamera = self._kamera_ac()
            if self._kamera is not None:
                print("[Kamera] Yeniden bağlandı.")

    def oku(self, zaman_asimi=2.0):
        """Yeni kareyi döndürür. Kaynak bittiyse ya da kamera yanıt vermiyorsa None.

        None geldiğinde `bitti` True ise kaynak tükenmiştir; False ise kamera geçici olarak
        yanıt vermiyordur (yeniden bağlanıyor) ve tekrar denenebilir.
        """
        if self._gorsel is not None:
            kare = self._gorsel.copy()
            self.zaman = self._kare_no / self._video_fps
            self._kare_no += 1
        elif self._video is not None:
            basarili, kare = self._video.read()
            if not basarili:
                self.bitti = True
                return None
            self.zaman = self._kare_no / self._video_fps
            self._kare_no += 1
        else:
            with self._kosul:
                yeni_var = self._kosul.wait_for(
                    lambda: self._kare_no != self._son_verilen_no or self.bitti, zaman_asimi
                )
                if not yeni_var or self._kare_no == self._son_verilen_no:
                    return None
                self._son_verilen_no = self._kare_no
                kare, self.zaman = self._kare, self._kare_zamani
        # read() her seferinde yeni bir dizi döndürdüğü için kilidin dışında işlemek güvenli
        return cv2.flip(kare, 1) if self.ayna else kare

    def kapat(self):
        if hasattr(self, "_durdur"):  # Canlı kamera: önce okuma thread'ini durdur, sonra bırak
            self._durdur.set()
            self._thread.join(timeout=YENIDEN_BAGLANMA_ARALIGI + 1)
        if self._kamera is not None:
            self._kamera.release()
            self._kamera = None
        if self._video is not None:
            self._video.release()
            self._video = None
        self.bitti = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.kapat()
