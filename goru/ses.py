"""Sistem ses seviyesi ve medya tuşları."""

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
        return self._hacim is not None

    def seviye(self):
        return float(self._hacim.GetMasterVolumeLevelScalar()) if self._hacim else 0.0

    def seviye_ayarla(self, oran):
        if self._hacim:
            self._hacim.SetMasterVolumeLevelScalar(min(max(oran, 0.0), 1.0), None)

    def sessiz_mi(self):
        return bool(self._hacim.GetMute()) if self._hacim else False

    def sessiz_degistir(self):
        if self._hacim:
            self._hacim.SetMute(not self.sessiz_mi(), None)
        else:
            medya_tusu("volumemute")


def medya_tusu(ad):
    """ad: "playpause", "nexttrack", "prevtrack", "volumemute" """
    # pyautogui burada içe aktarılır: ekranı olmayan ortamlarda (CI) modül yine de yüklenebilsin
    import pyautogui

    pyautogui.press(ad, _pause=False)
