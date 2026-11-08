"""Kare kaynağı: canlı kamera, video dosyası ya da görsel dosyası."""

import os
import sys
import threading
import time

import cv2

GORSEL_UZANTILARI = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
YENIDEN_BAGLANMA_ARALIGI = 2.0  # saniye
YETERLI_FPS = 27  # Webcam'lerin çoğunun tavanı 30 FPS: buna ulaşan ilk ayar seçilir


def fps_olc(kamera, sure=1.0, isinma=3):
    """Kameranın gerçekte kaç FPS verdiğini kısaca ölçer (ilk birkaç kare ısınma sayılır)."""
    for _ in range(isinma):
        if not kamera.read()[0]:
            return 0.0
    bas = time.monotonic()
    kare_sayisi = 0
    while time.monotonic() - bas < sure:
        if not kamera.read()[0]:
            break
        kare_sayisi += 1
    return kare_sayisi / max(time.monotonic() - bas, 1e-6)


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
            self._secilen = None  # Ölçülerek seçilen (arka uç, genişlik, yükseklik)
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

    def _adaylar(self):
        """Denenecek (arka uç, genişlik, yükseklik) ayarları, tercih sırasıyla.

        Sıkıştırılmamış YUY2 formatında çoğu webcam 720p'de 10-15 FPS'e düşer. DirectShow bazı
        kameralarda MJPG isteğini yok sayar ve 720p'de 10 FPS'te kalır; aynı kamera Media
        Foundation (MSMF) ile 30 FPS verebilir. Hiçbiri yetmezse düşük çözünürlük denenir.
        """
        genislik, yukseklik, _ = self._ayarlar
        apiler = [cv2.CAP_DSHOW, cv2.CAP_MSMF] if sys.platform == "win32" else [cv2.CAP_ANY]
        cozunurlukler = [(genislik, yukseklik)]
        if genislik * yukseklik > 640 * 480:
            cozunurlukler.append((640, 480))
        return [(api, g, y) for g, y in cozunurlukler for api in apiler]

    def _ac(self, api, genislik, yukseklik):
        """Kamerayı verilen arka uç ve çözünürlükle açar; açılamazsa None."""
        kamera = cv2.VideoCapture(self.kaynak, api)
        if not kamera.isOpened():
            kamera.release()
            return None
        # FOURCC ayarı çözünürlükten ÖNCE yapılmalı
        kamera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        kamera.set(cv2.CAP_PROP_FRAME_WIDTH, genislik)
        kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, yukseklik)
        kamera.set(cv2.CAP_PROP_FPS, self._ayarlar[2])
        kamera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return kamera

    def _kamera_ac(self):
        """Kamerayı bu cihazda en yüksek FPS'i veren ayarla açar; açılamazsa None döner.

        Kameranın bildirdiği FPS'e güvenilmez (yukarıdaki kamera 60 der, 10 verir), her aday
        kısaca ölçülür. Yeterince hızlı bir aday bulununca aramayı bırakır; bulunamazsa en
        hızlısını seçer. Yeniden bağlanırken seçilen ayar ölçmeden tekrar kullanılır.
        """
        if self._secilen is not None:
            return self._ac(*self._secilen)
        en_iyi = None  # (fps, aday, kamera)
        for aday in self._adaylar():
            kamera = self._ac(*aday)
            if kamera is None:
                continue
            fps = fps_olc(kamera)
            # Yüksek çözünürlük önce denenir; sonraki aday ancak belirgin şekilde hızlıysa seçilir
            if en_iyi is None or fps > en_iyi[0] * 1.15:
                if en_iyi is not None:
                    en_iyi[2].release()
                en_iyi = (fps, aday, kamera)
            else:
                kamera.release()
            if en_iyi[0] >= YETERLI_FPS:
                break
        if en_iyi is None:
            return None
        fps, self._secilen, kamera = en_iyi
        api, genislik, yukseklik = self._secilen
        print(f"[Kamera] {genislik}x{yukseklik}, {kamera.getBackendName()}, ~{fps:.0f} FPS")
        return kamera

    def _oku_dongusu(self):
        """Arka plan iş parçacığı: sürekli kare okur, sadece en güncelini saklar, kopmada yeniden bağlanır."""
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
        """Kaynağı ve arka plan okuma iş parçacığını kapatır. Birden çok çağrılabilir."""
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
