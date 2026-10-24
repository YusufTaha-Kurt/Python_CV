"""Sistem ses seviyesi ve medya tuşları (Ders 4).

Ses seviyesini doğrudan okumak/yazmak için Windows Core Audio arayüzü (pycaw kütüphanesi)
kullanılır; "sesi %10 artır" tuşuna basmaktan çok daha hassastır. Oynat/sonraki gibi
medya tuşları ise PyAutoGUI ile gönderilir.
"""

import sys


class SesKontrol:
    """Windows'ta pycaw ile ses seviyesini doğrudan (0.0 - 1.0) ayarlar.

    Diğer işletim sistemlerinde veya pycaw kurulu değilse `destekleniyor` False olur.
    Bu durumda sadece medya tuşları (oynat/durdur, sonraki parça) çalışır.
    """

    def __init__(self):
        self._hacim = None
        if sys.platform != "win32":
            return
        try:
            from pycaw.pycaw import AudioUtilities

            hoparlor = AudioUtilities.GetSpeakers()
            if hasattr(hoparlor, "EndpointVolume"):  # pycaw >= 2025
                self._hacim = hoparlor.EndpointVolume
            else:  # Eski pycaw sürümleri
                from ctypes import POINTER, cast

                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import IAudioEndpointVolume

                arayuz = hoparlor.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._hacim = cast(arayuz, POINTER(IAudioEndpointVolume))
        except Exception as hata:
            print(f"[SesKontrol] Ses aygıtına erişilemedi, sadece medya tuşları kullanılacak: {hata}")

    @property
    def destekleniyor(self):
        """Ses seviyesi doğrudan okunup yazılabiliyor mu? (Windows + pycaw gerekir.)"""
        return self._hacim is not None

    def seviye(self):
        """Sistem ses seviyesi, 0.0 (sessiz) - 1.0 (tam). Desteklenmiyorsa 0.0."""
        return float(self._hacim.GetMasterVolumeLevelScalar()) if self._hacim else 0.0

    def seviye_ayarla(self, oran):
        """Sistem ses seviyesini 0.0 - 1.0 aralığında ayarlar (dışına taşan değer kırpılır)."""
        if self._hacim:
            self._hacim.SetMasterVolumeLevelScalar(min(max(oran, 0.0), 1.0), None)

    def sessiz_mi(self):
        """Ses şu an kapalı mı?"""
        return bool(self._hacim.GetMute()) if self._hacim else False

    def sessiz_degistir(self):
        """Sesi kapatır / açar. pycaw yoksa klavyenin "sessiz" tuşuna basar."""
        if self._hacim:
            self._hacim.SetMute(not self.sessiz_mi(), None)
        else:
            medya_tusu("volumemute")


def medya_tusu(ad):
    """ad: "playpause", "nexttrack", "prevtrack", "volumemute" """
    # pyautogui burada içe aktarılır: ekranı olmayan ortamlarda (CI) modül yine de yüklenebilsin
    import pyautogui

    pyautogui.press(ad, _pause=False)
