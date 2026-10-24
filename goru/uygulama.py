"""Derslerin ortak iskeleti: komut satırı argümanları, kare döngüsü ve pencere.

Her ders aynı seçenekleri destekler:
    --kaynak 0              Kamera indeksi ya da video / görsel dosyası
    --pencere-yok           Görüntü penceresi açma (arka planda çalışma, otomatik testler)
    --kare-limiti 300       Bu kadar kare işleyip çık
    --sadece-izle           Fareye, klavyeye ve sese dokunma
"""

import argparse

import cv2

from .kamera import Kamera


def arguman_ayraci(aciklama):
    ayrac = argparse.ArgumentParser(description=aciklama)
    ayrac.add_argument("--kaynak", default="0", help="Kamera indeksi (0, 1, ...) ya da video / görsel dosyası")
    ayrac.add_argument("--pencere-yok", action="store_true", help="Görüntü penceresi açma")
    ayrac.add_argument("--kare-limiti", type=int, default=None, help="Bu kadar kare işleyip çık (test için)")
    ayrac.add_argument("--sadece-izle", action="store_true", help="Fareye, klavyeye ve sese dokunma")
    return ayrac


class Uygulama:
    """Kaynağı açar, kareleri sırayla verir, sonucu pencerede gösterir.

        app = Uygulama(args, "Pencere adı")
        for kare, zaman in app.kareler():
            ...
            app.goster(kare)
    """

    def __init__(self, args, pencere_adi, **kamera_ayarlari):
        self.args = args
        self.pencere_adi = pencere_adi
        self.kamera = Kamera(args.kaynak, **kamera_ayarlari)
        self.kare_no = 0
        self.son_tus = -1
        self._cikis = False

    def kareler(self):
        try:
            while not self._cikis:
                if self.args.kare_limiti is not None and self.kare_no >= self.args.kare_limiti:
                    break
                kare = self.kamera.oku()
                if kare is None:
                    if self.kamera.bitti:
                        break
                    continue  # Kamera geçici olarak yanıt vermiyor, yeniden bağlanıyor
                self.kare_no += 1
                yield kare, self.kamera.zaman
        finally:
            self.kapat()

    def goster(self, kare):
        """Kareyi gösterir ve basılan tuşu döndürür (-1: yok). q / ESC / pencereyi kapatmak çıkış yapar."""
        if self.args.pencere_yok:
            return -1
        cv2.imshow(self.pencere_adi, kare)
        self.son_tus = cv2.waitKey(1) & 0xFF
        if self.son_tus in (ord("q"), 27) or cv2.getWindowProperty(self.pencere_adi, cv2.WND_PROP_VISIBLE) < 1:
            self._cikis = True
        return self.son_tus

    def cik(self):
        self._cikis = True

    def kapat(self):
        if self.kamera is None:
            return
        self.kamera.kapat()
        self.kamera = None
        if not self.args.pencere_yok:
            cv2.destroyAllWindows()
