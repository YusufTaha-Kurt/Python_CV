"""Ders 8: İki parmakla kaydırma, sanal masaüstü ve pencere yönetimi.

PENCERE modu jest sözlüğü (kontrol eli):
    Zafer (iki parmak) + yukarı / aşağı   Sayfayı kaydır (dokunmatik ekran gibi: içerik elle gelir)
    Avuçla sola kaydır                    Sağdaki sanal masaüstüne geç (Win+Ctrl+Sağ)
    Avuçla sağa kaydır                    Soldaki sanal masaüstüne geç (Win+Ctrl+Sol)
    Başparmak yukarı                      Pencereyi büyüt (Win+Yukarı)
    Rock (işaret + serçe)                 Pencereyi küçült (Win+Aşağı)
    L işareti                             Önceki pencereye geç (Alt+Tab)
"""

from . import jestler as j
from .filtreler import OneEuroFiltre

ISLER = {
    "basparmak_yukari": ("pencereyi buyut", ("win", "up")),
    "rock": ("pencereyi kucult", ("win", "down")),
    "l_isareti": ("pencere degistir", ("alt", "tab")),
}
# El sola kayınca içerik de sola kayar ve sağdaki masaüstü görünür (dokunmatik yüzey gibi)
KAYDIRMALAR = {
    "sol": ("sagdaki masaustu", ("ctrl", "win", "right")),
    "sag": ("soldaki masaustu", ("ctrl", "win", "left")),
}


class PyAutoGuiKlavye:
    def __init__(self):
        import pyautogui

        pyautogui.PAUSE = 0
        self._p = pyautogui

    def kisayol(self, *tuslar):
        self._p.hotkey(*tuslar, _pause=False)


class SahteKlavye:
    def __init__(self, yazdir=False):
        self.basilanlar = []
        self._yazdir = yazdir

    def kisayol(self, *tuslar):
        self.basilanlar.append("+".join(tuslar))
        if self._yazdir:
            print(f"[KLAVYE] {'+'.join(tuslar)}")


class Kaydirici:
    """Elin dikey hareketini fare tekerleği kaydırmasına çevirir.

    hassasiyet: Elin kendi boyu kadar hareketi kaç tekerlek birimine karşılık gelsin
    (Windows'ta bir tekerlek çentiği 120 birimdir). Küçük titremeler ölü bölgede yutulur.
    Birim birim gönderildiği için modern uygulamalarda kaydırma pürüzsüzdür.
    """

    def __init__(self, hassasiyet=1500, dogal=True, olu_bolge=0.004):
        self.hassasiyet = hassasiyet
        self.dogal = dogal
        self.olu_bolge = olu_bolge
        self._filtre = OneEuroFiltre(min_kesim=1.0, beta=5.0)
        self.sifirla()

    def sifirla(self):
        self._onceki = None
        self._birikim = 0.0
        self._filtre.sifirla()

    def guncelle(self, y, boy, zaman):
        """y: elin dikey konumu (px), boy: el boyu (px). Dönüş: bu kare kaydırılacak birim."""
        y = float(self._filtre(y / boy, zaman))
        if self._onceki is None:
            self._onceki = y
            return 0
        dy, self._onceki = y - self._onceki, y
        if abs(dy) < self.olu_bolge:
            return 0
        # Pozitif tekerlek = yukarı kaydır. Doğal modda el aşağı inince içerik de aşağı iner
        self._birikim += dy * self.hassasiyet * (1 if self.dogal else -1)
        tam = int(self._birikim / 10) * 10
        self._birikim -= tam
        return tam


class PencereKontrol:
    def __init__(self, yol, el="sag", klavye=None, fare=None):
        self.yol = yol
        self.el = el
        self.klavye = klavye if klavye is not None else PyAutoGuiKlavye()
        self.fare = fare  # kaydir(miktar) metodu olan nesne (goru.fare)
        self.aktif = True
        self.kaydirici = Kaydirici()
        self.kaydiriyor = False
        self.son_eylem = "-"
        yol.abone_ol("jest.degisti", self._jest_degisti)
        yol.abone_ol("jest.kaydirma", self._kaydirma)

    def _jest_degisti(self, olay):
        if self.aktif and olay.veri.get("el") == self.el and olay.veri["jest"] in ISLER:
            self._eylem(*ISLER[olay.veri["jest"]])

    def _kaydirma(self, olay):
        if self.aktif and olay.veri.get("el") == self.el:
            self._eylem(*KAYDIRMALAR[olay.veri["yon"]])

    def _eylem(self, ad, tuslar):
        self.son_eylem = ad
        self.yol.yayinla("pencere.eylem", eylem=ad)
        self.klavye.kisayol(*tuslar)

    def isle(self, el, jest, zaman):
        """Her kare: el = kontrol eli (ya da None), jest = elin kararlı jesti (JestYayincisi)."""
        self.kaydiriyor = self.aktif and el is not None and jest == j.Jest.ZAFER
        if not self.kaydiriyor:
            self.kaydirici.sifirla()
            return
        n = el.noktalar
        y = (n[j.ISARET_UCU, 1] + n[j.ORTA_UCU, 1]) / 2
        miktar = self.kaydirici.guncelle(y, j.el_boyutu(n), zaman)
        if miktar and self.fare is not None:
            self.fare.kaydir(miktar)
