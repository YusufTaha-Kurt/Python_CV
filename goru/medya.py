"""Ders 4: Jestlerle medya ve ses kontrolü.

Jest sözlüğü:
    L işareti (başparmak + işaret açık)  -> SES MODU: iki parmak arası mesafe = ses seviyesi
    Avuç aç                              -> ses modundan çık (seviye olduğu yerde kalır)
    Avuçla sağa / sola kaydır            -> sonraki / önceki parça
    Başparmak yukarı                     -> oynat / duraklat
    Rock (işaret + serçe)                -> sesi kapat / aç

Ayrık eylemler (oynat, parça değiştir) JestYayincisi'nin olaylarına abone olarak çalışır.
Sürekli kontrol (ses seviyesi) her kare `isle()` ile güncellenir.
"""

import numpy as np

from . import jestler as j
from .filtreler import OneEuroFiltre
from .ses import SesKontrol, medya_tusu

# Başparmak-işaret mesafesinin (el boyutuna oranla) ses seviyesine eşlendiği aralık
SES_MIN_ORAN, SES_MAX_ORAN = 0.25, 1.1


class MedyaKontrol:
    def __init__(self, yol, el="sag", sadece_izle=False, ses=None):
        self.yol = yol
        self.el = el
        self.sadece_izle = sadece_izle
        self.ses = ses if ses is not None else SesKontrol()
        self.aktif = True  # Kontrol merkezinde sadece MEDYA modundayken True (Ders 8)
        self.ses_modu = False
        self.seviye = self.ses.seviye()
        self.son_eylem = "-"
        self._filtre = OneEuroFiltre(min_kesim=0.8, beta=2.0)
        yol.abone_ol("jest.degisti", self._jest_degisti)
        yol.abone_ol("jest.kaydirma", self._kaydirma)

    def _jest_degisti(self, olay):
        if not self.aktif or olay.veri.get("el") != self.el:
            return
        jest = olay.veri["jest"]
        if jest == j.Jest.L_ISARETI.value:
            self.ses_modu = True
            self._eylem("ses modu")
        elif jest == j.Jest.BASPARMAK_YUKARI.value:
            self._eylem("oynat/duraklat", lambda: medya_tusu("playpause"))
        elif jest == j.Jest.ROCK.value:
            self._eylem("sessiz ac/kapa", self.ses.sessiz_degistir)

    def _kaydirma(self, olay):
        if not self.aktif or olay.veri.get("el") != self.el:
            return
        if olay.veri["yon"] == "sag":
            self._eylem("sonraki parca", lambda: medya_tusu("nexttrack"))
        else:
            self._eylem("onceki parca", lambda: medya_tusu("prevtrack"))

    def _eylem(self, ad, fonksiyon=None):
        self.son_eylem = ad
        self.yol.yayinla("medya.eylem", eylem=ad)
        if fonksiyon and not self.sadece_izle:
            fonksiyon()

    def isle(self, el, zaman):
        """Her kare çağrılır. el: bu yeteneği yöneten el (görünmüyorsa None)."""
        if el is None or not self.aktif:
            self.ses_modu = False
            self._filtre.sifirla()
            return
        n = el.noktalar

        # Orta, yüzük veya serçe açılırsa moddan çık. İşaret parmağının durumuna bakılmaz:
        # başparmağa yaklaşırken bükülür ve "kapalı" görünebilir.
        _, _, orta, yuzuk, serce = j.parmak_durumlari(n)
        if self.ses_modu and (orta or yuzuk or serce):
            self.ses_modu = False
            self._filtre.sifirla()
        if not self.ses_modu:
            return

        oran = j.cimdik_orani(n, j.BAS_UCU, j.ISARET_UCU)
        ham_seviye = np.clip((oran - SES_MIN_ORAN) / (SES_MAX_ORAN - SES_MIN_ORAN), 0, 1)
        yeni_seviye = float(self._filtre(ham_seviye, zaman))
        # Her karede ses API'sini çağırmamak için %1'lik değişimleri bekle
        if abs(yeni_seviye - self.seviye) > 0.01:
            self.seviye = yeni_seviye
            if not self.sadece_izle:
                self.ses.seviye_ayarla(self.seviye)

    def gosterilen_seviye(self):
        """Ekranda gösterilecek seviye: ses modundayken hedef, değilse sistemin gerçek seviyesi."""
        if self.ses_modu or not self.ses.destekleniyor:
            return self.seviye
        return self.ses.seviye()
