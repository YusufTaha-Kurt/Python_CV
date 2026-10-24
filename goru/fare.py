"""Ders 5: Çimdik olaylarını fare tuşlarına çeviren durum makinesi ve fare arka uçları."""

import math


class PyAutoGuiFare:
    """Gerçek fare (işletim sistemi seviyesinde)."""

    def __init__(self):
        import pyautogui

        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False
        self._p = pyautogui

    def bas(self):
        self._p.mouseDown(_pause=False)

    def birak(self):
        self._p.mouseUp(_pause=False)

    def tikla(self):
        self._p.click(_pause=False)

    def sag_tikla(self):
        self._p.rightClick(_pause=False)

    def kaydir(self, miktar):
        self._p.scroll(int(miktar), _pause=False)


class SahteFare:
    """Hiçbir şeye dokunmaz, eylemleri kaydeder (--sadece-izle ve testler için)."""

    def __init__(self, yazdir=False):
        self.eylemler = []
        self._yazdir = yazdir

    def _kaydet(self, eylem):
        self.eylemler.append(eylem)
        if self._yazdir:
            print(f"[FARE] {eylem}")

    def bas(self):
        self._kaydet("bas")

    def birak(self):
        self._kaydet("birak")

    def tikla(self):
        self._kaydet("tikla")

    def sag_tikla(self):
        self._kaydet("sag_tikla")

    def kaydir(self, miktar):
        self._kaydet(f"kaydir {int(miktar)}")


class TiklamaMakinesi:
    """Çimdik olaylarını sol tuş eylemlerine çevirir.

    Durumlar:
        BOS        Tuş bırakılmış.
        BEKLEMEDE  Çimdik başladı ama henüz tuşa basılmadı; imleç çimdik noktasında donuk.
                   Bu sırada çimdik bırakılırsa -> TIK. İptal edilirse -> hiçbir şey olmaz.
        BASILI     Çimdik deneme süresini geçti ya da el sürükleme eşiğini aştı -> tuş basılı.

    Ders 2'de çimdik başlar başlamaz tuşa basılıyordu. Yumruk yapan bir el geçerken kısa bir
    an çimdik gibi görünse bile tık oluyordu. Burada tuşa ancak çimdik deneme süresini
    atlattıktan sonra basılır; kısa çimdikler ise bırakıldıkları anda tık olur. İşletim
    sistemlerinde tık zaten bırakma anında işlendiği için kullanıcı gecikme hissetmez.
    """

    BOS, BEKLEMEDE, BASILI = "bos", "beklemede", "basili"

    def __init__(self, fare, surukleme_esigi_px, deneme_suresi=0.4, cift_tik_penceresi=0.3):
        self.fare = fare
        self.surukleme_esigi = surukleme_esigi_px
        self.deneme_suresi = deneme_suresi
        self.cift_tik_penceresi = cift_tik_penceresi
        self.durum = self.BOS
        self.donuk = False  # İmleç donuk mu? (tıklama anında kaymasın)
        self.kilit_noktasi = None
        self._baslangic = 0.0
        self._birakma = -math.inf

    def guncelle(self, olay, kavrayabilir, hedef, zaman):
        """olay: GuvenilirCimdik olayı, hedef: imlecin gitmek istediği nokta (ekran px)."""
        if (olay == "basladi" and kavrayabilir) or olay == "iyilesti":
            if self.durum == self.BOS:
                self.durum = self.BEKLEMEDE
                self._baslangic = zaman
                # Çift tık penceresindeysek imleç zaten donuk: ikinci tık aynı noktaya düşsün
                if not self.donuk:
                    self.donuk = True
                    self.kilit_noktasi = hedef
        elif olay == "bitti":
            if self.durum == self.BEKLEMEDE:
                self.fare.tikla()
            elif self.durum == self.BASILI:
                self.fare.birak()
            if self.durum != self.BOS:
                self.durum = self.BOS
                self._birakma = zaman
        elif olay == "iptal":
            if self.durum == self.BASILI:
                self.fare.birak()
            if self.durum != self.BOS:
                self.durum = self.BOS
                self.donuk = False

        uzaklasti = self.donuk and math.dist(hedef, self.kilit_noktasi) > self.surukleme_esigi
        if self.durum == self.BEKLEMEDE and (uzaklasti or zaman - self._baslangic >= self.deneme_suresi):
            self.fare.bas()
            self.durum = self.BASILI
        if self.donuk and (uzaklasti or (self.durum == self.BOS and zaman - self._birakma > self.cift_tik_penceresi)):
            self.donuk = False
        return self.donuk

    def sifirla(self):
        if self.durum == self.BASILI:
            self.fare.birak()
        self.durum = self.BOS
        self.donuk = False
