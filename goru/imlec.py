"""Kamera hızından bağımsız, akıcı imleç sürücüsü."""

import math
import threading
import time

import pyautogui

# V1'deki asıl takılma sebebi: PyAutoGUI her çağrıdan sonra varsayılan olarak 0.1 sn UYUR.
# Her karede moveTo çağrıldığı için döngü ~10 FPS'e kilitleniyordu.
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False


class ImlecSurucu:
    """İmleci ayrı bir thread'de, yüksek frekansta hedef noktaya doğru kaydırır.

    Kamera ~30 FPS verir. İmleç sadece kare geldiğinde oynatılırsa 33 ms'lik
    "basamaklar" oluşur ve 60-144 Hz monitörde göz bunu takılma olarak görür.
    Bu sınıf hedefi `hz` frekansında, her adımda kalan yolun bir kısmını kat ederek
    (üstel yaklaşma) takip eder. Kare gelmese bile imleç akmaya devam eder.

    takip_hizi: Büyüdükçe imleç hedefe daha çabuk ulaşır (1/saniye).
    """

    def __init__(self, hz=144, takip_hizi=22.0):
        self.hz = hz
        self.takip_hizi = takip_hizi
        x, y = pyautogui.position()
        self._konum = [float(x), float(y)]
        self._hedef = [float(x), float(y)]
        self._donmus = False
        self._kilit = threading.Lock()
        self._calisiyor = False
        self._thread = None

    def hedef_ayarla(self, x, y):
        with self._kilit:
            self._hedef = [float(x), float(y)]

    @property
    def donmus(self):
        return self._donmus

    def dondur(self, durum):
        """Dondurulmuş imleç hedef değişse de yerinden kıpırdamaz (tıklama anında kaymayı önler)."""
        with self._kilit:
            self._donmus = durum

    def baslat(self):
        self._calisiyor = True
        self._thread = threading.Thread(target=self._dongu, daemon=True)
        self._thread.start()

    def durdur(self):
        self._calisiyor = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def _dongu(self):
        adim = 1.0 / self.hz
        onceki = time.perf_counter()
        while self._calisiyor:
            simdi = time.perf_counter()
            dt, onceki = simdi - onceki, simdi
            with self._kilit:
                if not self._donmus:
                    # Zaman adımından bağımsız üstel yaklaşma: FPS dalgalansa da hız aynı kalır
                    k = 1.0 - math.exp(-self.takip_hizi * dt)
                    eski = (round(self._konum[0]), round(self._konum[1]))
                    self._konum[0] += (self._hedef[0] - self._konum[0]) * k
                    self._konum[1] += (self._hedef[1] - self._konum[1]) * k
                    yeni = (round(self._konum[0]), round(self._konum[1]))
                    if yeni != eski:
                        pyautogui.moveTo(*yeni, _pause=False)
            kalan = adim - (time.perf_counter() - simdi)
            if kalan > 0:
                time.sleep(kalan)
