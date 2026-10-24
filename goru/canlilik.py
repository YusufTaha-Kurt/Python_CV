"""Ders 13: Canlılık testi. Kameradaki yüz gerçek, canlı bir insan mı, yoksa bir fotoğraf mı?

Yüz tanıma tek başına bir fotoğrafla kandırılabilir. Bu modül rastgele sırayla hareketler
ister (göz kırp, gülümse, başını çevir, ağzını aç). Fotoğraf komutla hareket edemez.

Her görev bir DEĞİŞİM ister, bir durum değil: gülümseyen bir fotoğraf "gülümse" görevini
geçemez, çünkü görev başında nötr olup sonra gülümsemek gerekir. Baş çevirme de görev
başındaki açıya göre ölçülür.
"""

import random

from .bas_pozu import matris_acilari
from .goz import GozKirpmaAlgilayici

GOREVLER = {
    "goz_kirp": "Gozlerini kirp",
    "gulumse": "Gulumse",
    "basi_sola": "Basini sola cevir",
    "basi_saga": "Basini saga cevir",
    "agzi_ac": "Agzini ac",
}
YUZ_KAYIP_SINIRI = 1.0  # Yüz bu kadar saniye kaybolursa test başarısız


def _ortalama(ifadeler, *adlar):
    return sum(ifadeler.get(ad, 0.0) for ad in adlar) / len(adlar)


class CanlilikTesti:
    def __init__(self, adim_sayisi=3, adim_suresi=6.0, donus_acisi=15.0, rastgele=None):
        self.adim_sayisi = adim_sayisi
        self.adim_suresi = adim_suresi
        self.donus_acisi = donus_acisi
        self.rastgele = rastgele or random.Random()
        self.gorevler = []
        self.adim = 0
        self.sonuc = None  # None: sürüyor / henüz başlamadı, "gecti", "kaldi"
        self.neden = ""
        self.basladi = False

    @property
    def gorev(self):
        if not self.basladi or self.sonuc or self.adim >= len(self.gorevler):
            return None
        return self.gorevler[self.adim]

    @property
    def talimat(self):
        return GOREVLER.get(self.gorev, "")

    def kalan_sure(self, zaman):
        return max(0.0, self.adim_suresi - (zaman - self._adim_baslangic)) if self.gorev else 0.0

    def baslat(self, zaman):
        self.gorevler = self.rastgele.sample(list(GOREVLER), self.adim_sayisi)
        self.adim, self.sonuc, self.neden, self.basladi = 0, None, "", True
        self._goz = GozKirpmaAlgilayici()
        self._yuz_yok = None
        self._adim_baslat(zaman)

    def _adim_baslat(self, zaman):
        self._adim_baslangic = zaman
        self._yaw0 = None
        self._en_dusuk_gulumseme = 1.0
        self._en_dusuk_agiz = 1.0

    def _bitir(self, sonuc, neden=""):
        self.sonuc, self.neden = sonuc, neden

    def guncelle(self, yuz, zaman):
        """Her kare: yuz = goru.yuz.Yuz (ya da None). Dönüş: sonuç (None / "gecti" / "kaldi")."""
        if not self.basladi or self.sonuc:
            return self.sonuc
        if yuz is None:
            self._yuz_yok = self._yuz_yok if self._yuz_yok is not None else zaman
            if zaman - self._yuz_yok > YUZ_KAYIP_SINIRI:
                self._bitir("kaldi", "yuz kayboldu")
            return self.sonuc
        self._yuz_yok = None

        olaylar = self._goz.guncelle(yuz.noktalar, zaman)
        yaw = matris_acilari(yuz.donusum)[0] if yuz.donusum is not None else 0.0
        if self._yaw0 is None:
            self._yaw0 = yaw
        gulumseme = _ortalama(yuz.ifadeler, "mouthSmileLeft", "mouthSmileRight")
        agiz = yuz.ifadeler.get("jawOpen", 0.0)
        self._en_dusuk_gulumseme = min(self._en_dusuk_gulumseme, gulumseme)
        self._en_dusuk_agiz = min(self._en_dusuk_agiz, agiz)

        gorev = self.gorev
        basarili = {
            "goz_kirp": any(o in ("dogal", "bilincli") for o in olaylar),
            "gulumse": gulumseme > 0.6 and self._en_dusuk_gulumseme < 0.3,
            "agzi_ac": agiz > 0.5 and self._en_dusuk_agiz < 0.15,
            "basi_sola": yaw - self._yaw0 < -self.donus_acisi,
            "basi_saga": yaw - self._yaw0 > self.donus_acisi,
        }[gorev]
        if basarili:
            self.adim += 1
            if self.adim == len(self.gorevler):
                self._bitir("gecti")
            else:
                self._adim_baslat(zaman)
        elif zaman - self._adim_baslangic > self.adim_suresi:
            self._bitir("kaldi", f"zaman asimi: {GOREVLER[gorev]}")
        return self.sonuc
