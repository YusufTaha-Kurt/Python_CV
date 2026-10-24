"""Ders 8: Mod seçici. Kontrol eli bir işi yaparken diğer el modu seçer.

Mod eli (varsayılan sol) 1, 2 ya da 3 düz parmak gösterip kısa bir süre tutarsa o sıradaki
moda geçilir. Yumruk (0) ve açık avuç (4) yok sayılır: el dinlenirken mod değişmesin.
"""

from . import jestler as j


class ModSecici:
    """Hangi modun (FARE / MEDYA / PENCERE) etkin olduğunu tutar ve diğer elin parmak sayısından değiştirir."""

    def __init__(self, modlar, yol=None, sure=0.6):
        self.modlar = list(modlar)
        self.mod = self.modlar[0]
        self.yol = yol
        self.sure = sure
        self._aday = None
        self._aday_zamani = 0.0

    def sec(self, mod):
        """Modu doğrudan seçer (klavye kısayolu vb.). Değiştiyse True."""
        if mod == self.mod or mod not in self.modlar:
            return False
        eski, self.mod = self.mod, mod
        if self.yol is not None:
            self.yol.yayinla("mod.degisti", mod=mod, onceki=eski)
        return True

    def guncelle(self, el, zaman):
        """Mod eli (ya da None) ile her kare çağrılır. Mod değiştiyse yeni modu döndürür."""
        sayi = j.duz_parmak_sayisi(el.noktalar) if el is not None else 0
        if not 1 <= sayi <= len(self.modlar):
            self._aday = None
            return None
        if sayi != self._aday:
            self._aday, self._aday_zamani = sayi, zaman
            return None
        if zaman - self._aday_zamani >= self.sure and self.sec(self.modlar[sayi - 1]):
            return self.mod
        return None
