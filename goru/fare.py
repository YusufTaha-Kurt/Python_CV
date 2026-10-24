"""Ders 5: Elle fare kontrolü: tıklama durum makinesi, fare arka uçları ve ElFaresi.

Üç katman vardır, aşağıdan yukarıya:
    PyAutoGuiFare / SahteFare   Fareyi gerçekten oynatan ya da sadece kaydeden "arka uç".
    TiklamaMakinesi             Çimdik olaylarını sol tuş basma / bırakma / tıklamaya çevirir.
    ElFaresi                    El noktalarını ekran koordinatına çevirip hepsini birleştirir.

Fare arka ucu dışarıdan verildiği için aynı kod hem gerçek fareyle hem `--sadece-izle`
modunda hem de testlerde çalışır.
"""

import math

import numpy as np

from . import jestler as j
from .cimdik import GuvenilirCimdik
from .filtreler import OneEuroFiltre


class PyAutoGuiFare:
    """Gerçek fare (işletim sistemi seviyesinde).

    Arka uç arayüzü (SahteFare ile aynı): bas() / birak() sol tuşu basılı tutar-bırakır,
    tikla() tek sol tık, sag_tikla() sağ tık, kaydir(miktar) tekerlek (+ yukarı).
    """

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
    """Hiçbir şeye dokunmaz, eylemleri `eylemler` listesine kaydeder (--sadece-izle ve testler için).

    PyAutoGuiFare ile aynı arayüze sahiptir, bu yüzden ikisi birbirinin yerine kullanılabilir.
    """

    def __init__(self, yazdir=False):
        self.eylemler = []
        self._yazdir = yazdir

    def _kaydet(self, eylem):
        """Eylemi listeye ekler (ve istenmişse konsola yazar)."""
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
        """olay: GuvenilirCimdik olayı, hedef: imlecin gitmek istediği nokta (ekran px).

        İmlecin donuk olup olmadığını döndürür; donukken ImlecSurucu imleci yerinde tutar.
        """
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
        """El kaybolduysa basılı kalmış tuşu bırakır (fare "yapışık" kalmasın)."""
        if self.durum == self.BASILI:
            self.fare.birak()
        self.durum = self.BOS
        self.donuk = False


class ElFaresi:
    """Bir elle tam fare: imleç, sol tık / çift tık / sürükleme, sağ tık.

    Her kare `isle(el, zaman, kare_boyutu)` çağrılır. Kameranın ortasındaki sanal çalışma
    alanı (kutu) bütün ekrana oranlanır, konum 1€ filtresinden geçer ve `surucu`
    (goru.imlec.ImlecSurucu) imleci 144 Hz'de oraya akıtır.

    surucu None ise imleç oynatılmaz (sadece izleme ve testler).
    """

    def __init__(self, fare, ayar=None, ekran=None, surucu=None, kutu_orani=0.18, imlec_noktasi="orta",
                 surukleme_esigi=0.025):
        if ekran is None:
            import pyautogui

            ekran = tuple(pyautogui.size())
        self.fare = fare
        self.ekran = ekran
        self.surucu = surucu
        self.kutu_orani = kutu_orani
        self.imlec_noktasi = imlec_noktasi
        self.sol = GuvenilirCimdik(j.ISARET_UCU, ayar)  # Başparmak + işaret: sol tuş
        self.sag = GuvenilirCimdik(j.ORTA_UCU, ayar)  # Başparmak + orta: sağ tık
        self.makine = TiklamaMakinesi(fare, surukleme_esigi * ekran[0])
        self.filtre = OneEuroFiltre(min_kesim=0.6, beta=6.0)
        self.kutu = None
        self.hedef = None

    def ayar_degistir(self, ayar):
        """Çalışırken çimdik eşiklerini değiştirir (örnekleyicinin önerisini uygularken)."""
        self.sol.ayar = self.sag.ayar = ayar

    @property
    def cimdik_aktif(self):
        """Sol ya da sağ çimdik şu an sürüyor mu?"""
        return self.sol.aktif or self.sag.aktif

    def isle(self, el, zaman, kare_boyutu):
        """Her karede çağır. `el` yoksa None ver. Çimdik olayını (ya da None) döndürür."""
        genislik, yukseklik = kare_boyutu
        # Kameranın kenarlarına kadar uzanmak yorucu: ortadaki küçültülmüş "çalışma kutusu"
        # bütün ekrana eşlenir. Kutu kenarına varınca imleç ekran kenarına varır.
        kx, ky = int(genislik * self.kutu_orani), int(yukseklik * self.kutu_orani)
        self.kutu = (kx, ky, genislik - kx, yukseklik - ky)
        if el is None:
            self.sifirla()
            self.filtre.sifirla()
            return None

        n = el.noktalar
        # 1) Güvenilir çimdik algılayıcıları: işaret = sol tuş, orta parmak = sağ tık
        olay = self.sol.guncelle(n, zaman)
        sag_olay = self.sag.guncelle(n, zaman)
        if self.imlec_noktasi == "kok":
            x, y = n[j.ISARET_KOK, :2]
        else:  # Başparmak ile işaret ucunun ortası: çimdikte en sabit nokta
            x, y = (n[j.BAS_UCU, :2] + n[j.ISARET_UCU, :2]) / 2
        # 2) Kare pikselini 0-1 aralığına, sonra filtreleyip ekran pikseline çevir
        x1, y1, x2, y2 = self.kutu
        nx, ny = np.clip((x - x1) / (x2 - x1), 0, 1), np.clip((y - y1) / (y2 - y1), 0, 1)
        fx, fy = self.filtre((nx, ny), zaman)
        self.hedef = (float(fx) * (self.ekran[0] - 1), float(fy) * (self.ekran[1] - 1))

        # 3) Tıklama makinesi karar verir; tıklama anında imleç kaymasın diye dondurulur
        donuk = self.makine.guncelle(olay, self.sol.kavrayabilir, self.hedef, zaman)
        if self.surucu is not None:
            self.surucu.dondur(donuk)
            self.surucu.hedef_ayarla(*self.hedef)
        if sag_olay == "basladi" and self.sag.kavrayabilir and self.makine.durum == TiklamaMakinesi.BOS:
            self.fare.sag_tikla()
        return olay

    def sifirla(self):
        """El kaybolduğunda her şeyi bırakır: basılı tuş, çimdik durumları, dondurulmuş imleç."""
        self.makine.sifirla()
        self.sol.sifirla()
        self.sag.sifirla()
        if self.surucu is not None:
            self.surucu.dondur(False)
