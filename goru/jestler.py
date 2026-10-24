"""El jestleri: parmak durumları, çimdik, statik jestler ve kaydırma (swipe).

Bu modül sadece numpy kullanır; girdi olarak (21, 3) boyutlu nokta dizisi alır.
Bu sayede kamera ve model olmadan, sentetik verilerle test edilebilir.
"""

import time
from collections import deque
from enum import Enum

import numpy as np

# MediaPipe el nokta indeksleri (kök = MCP, PIP = orta boğum, DIP = uç boğum)
BILEK = 0
BAS_IP, BAS_UCU = 3, 4
ISARET_KOK, ISARET_PIP, ISARET_DIP, ISARET_UCU = 5, 6, 7, 8
ORTA_KOK, ORTA_PIP, ORTA_DIP, ORTA_UCU = 9, 10, 11, 12
YUZUK_KOK, YUZUK_PIP, YUZUK_DIP, YUZUK_UCU = 13, 14, 15, 16
SERCE_KOK, SERCE_PIP, SERCE_DIP, SERCE_UCU = 17, 18, 19, 20

PARMAK_ADLARI = ("bas", "isaret", "orta", "yuzuk", "serce")
# Dört parmağın eklemleri: uç -> (kök, PIP, DIP, uç)
PARMAKLAR = {
    ISARET_UCU: (ISARET_KOK, ISARET_PIP, ISARET_DIP, ISARET_UCU),
    ORTA_UCU: (ORTA_KOK, ORTA_PIP, ORTA_DIP, ORTA_UCU),
    YUZUK_UCU: (YUZUK_KOK, YUZUK_PIP, YUZUK_DIP, YUZUK_UCU),
    SERCE_UCU: (SERCE_KOK, SERCE_PIP, SERCE_DIP, SERCE_UCU),
}


def mesafe(noktalar, a, b):
    return float(np.linalg.norm(noktalar[a, :2] - noktalar[b, :2]))


def el_boyutu(noktalar):
    """Bilek ile orta parmak kökü arası mesafe. El kameraya yaklaşıp uzaklaştıkça
    tüm mesafeler bu değere bölünerek ölçekten bağımsız hale getirilir."""
    return max(mesafe(noktalar, BILEK, ORTA_KOK), 1e-6)


def parmak_durumlari(noktalar):
    """Her parmak için açık (True) / kapalı (False) döndürür: (bas, isaret, orta, yuzuk, serce).

    Dört parmak: Uç, bileğe orta boğumdan (PIP) daha uzaksa parmak açıktır.
    Başparmak: Uç, serçe köküne IP ekleminden daha uzaksa açıktır.
    İki kural da elin dönüşünden bağımsızdır (sadece mesafe kıyaslanır).
    """
    bas_acik = mesafe(noktalar, BAS_UCU, SERCE_KOK) > mesafe(noktalar, BAS_IP, SERCE_KOK)
    digerleri = tuple(
        mesafe(noktalar, uc, BILEK) > mesafe(noktalar, pip, BILEK)
        for uc, pip in ((ISARET_UCU, ISARET_PIP), (ORTA_UCU, ORTA_PIP), (YUZUK_UCU, YUZUK_PIP), (SERCE_UCU, SERCE_PIP))
    )
    return (bas_acik,) + digerleri


def cimdik_orani(noktalar, a=BAS_UCU, b=ISARET_UCU):
    """İki parmak ucu arası mesafenin el boyutuna oranı.

    V1'de sabit 25 piksel eşiği vardı: el kameradan uzaklaşınca tıklama tetiklenmiyor,
    yaklaşınca kendiliğinden tetikleniyordu. Oran kullanınca mesafe sorun olmaktan çıkar.
    """
    return mesafe(noktalar, a, b) / el_boyutu(noktalar)


def kemer_orani(noktalar, uc):
    """Parmak ucunun bileğe uzaklığı / parmak kökünün bileğe uzaklığı.

    Düz parmakta ~1.8-2.0, kıvrık parmakta ~1.0 civarıdır. Dönmeden bağımsızdır.
    """
    kok = PARMAKLAR[uc][0]
    return mesafe(noktalar, uc, BILEK) / max(mesafe(noktalar, kok, BILEK), 1e-6)


def avuc_en_boy(noktalar):
    """Avuç uzunluğu (bilek -> orta kök) / avuç genişliği (işaret kökü -> serçe kökü).

    El kameraya yan dönünce genişlik daralır ve oran büyür. Gerçek bir elde olamayacak kadar
    büyük değerler, takip modelinin el şeklini "uydurduğunu" gösterir.
    """
    return el_boyutu(noktalar) / max(mesafe(noktalar, ISARET_KOK, SERCE_KOK), 1e-6)


def kivrim(noktalar, uc):
    """Parmağın kıvrımı: (kök -> PIP) ile (DIP -> uç) birim vektörlerinin 3D nokta çarpımı.

    Düz parmakta iki segment aynı yöne bakar (~ +1), kanca gibi kıvrılınca uç segment geri
    döner (< 0). Parmak kameraya doğru uzandığında 2D mesafeler kısalıp yanıltır, ama
    segmentler arası açı her bakış açısında korunur.
    """
    kok, pip, dip, uc_ = PARMAKLAR[uc]
    p = noktalar[pip] - noktalar[kok]
    d = noktalar[uc_] - noktalar[dip]
    return float(np.dot(p, d) / max(np.linalg.norm(p) * np.linalg.norm(d), 1e-9))


def duz_parmak_sayisi(noktalar):
    """Gerçekten DÜZ uzanan parmak sayısı (başparmak hariç, 0-4).

    `parmak_durumlari` sadece uç-bilek mesafesine bakar; kanca gibi kıvrılmış bir parmağın ucu
    da bileğe uzak kalabildiği için "açık" sayılabilir. Burada ayrıca parmağın düz olması
    (kıvrım açısı) aranır. Açık avuç / pençe gibi ince ayrımlar için bunu kullan.
    """
    return sum(1 for uc in PARMAKLAR if kemer_orani(noktalar, uc) > 1.45 and kivrim(noktalar, uc) > 0.5)


class Jest(Enum):
    BILINMIYOR = "bilinmiyor"
    YUMRUK = "yumruk"
    AVUC = "avuc"
    ISARET = "isaret"
    ZAFER = "zafer"
    L_ISARETI = "l_isareti"
    BASPARMAK_YUKARI = "basparmak_yukari"
    ROCK = "rock"


def jest_tani(noktalar):
    """Parmak durumlarından statik jesti çıkarır."""
    bas, isaret, orta, yuzuk, serce = parmak_durumlari(noktalar)
    dort_parmak = (isaret, orta, yuzuk, serce)

    if not any(dort_parmak):
        # Başparmak yukarı: başparmak açık ve ucu bileğin belirgin şekilde üstünde (y ekseni aşağı doğru artar)
        if bas and noktalar[BAS_UCU, 1] < noktalar[BILEK, 1] - 0.5 * el_boyutu(noktalar):
            return Jest.BASPARMAK_YUKARI
        return Jest.YUMRUK
    if all(dort_parmak):
        return Jest.AVUC if bas else Jest.BILINMIYOR
    if dort_parmak == (True, False, False, False):
        return Jest.L_ISARETI if bas else Jest.ISARET
    if dort_parmak == (True, True, False, False):
        return Jest.ZAFER
    if dort_parmak == (True, False, False, True):
        return Jest.ROCK
    return Jest.BILINMIYOR


class CimdikAlgilayici:
    """Histerezisli çimdik algılayıcı.

    Tek eşik kullanılırsa oran eşiğin etrafında gidip gelirken saniyede onlarca
    tık/bırak üretilir. Başlama eşiği bırakma eşiğinden küçük tutularak arada bir
    "ölü bölge" bırakılır: bir kez çimdik başladıysa bitmesi için parmakların
    belirgin şekilde açılması gerekir.
    """

    def __init__(self, baslama=0.25, birakma=0.38):
        assert baslama < birakma
        self.baslama = baslama
        self.birakma = birakma
        self.aktif = False

    def guncelle(self, oran):
        """Durum değiştiyse "basladi" / "bitti", değişmediyse None döndürür."""
        if not self.aktif and oran < self.baslama:
            self.aktif = True
            return "basladi"
        if self.aktif and oran > self.birakma:
            self.aktif = False
            return "bitti"
        return None

    def sifirla(self):
        self.aktif = False


class JestKararlilastirici:
    """Bir jestin geçerli sayılması için belirli süre kesintisiz görülmesini şart koşar.

    V1'de yumruk tutulduğu sürece uyku modu her saniye aç/kapa oluyordu.
    Bu sınıf sadece jest DEĞİŞTİĞİNDE bir kez haber verir (kenar tetikleme).
    """

    def __init__(self, sure=0.3):
        self.sure = sure
        self.mevcut = Jest.BILINMIYOR
        self._aday = Jest.BILINMIYOR
        self._aday_baslangic = 0.0

    def guncelle(self, jest, zaman=None):
        """Kararlı jest değiştiyse yeni jesti, değişmediyse None döndürür."""
        zaman = time.monotonic() if zaman is None else zaman
        if jest != self._aday:
            self._aday, self._aday_baslangic = jest, zaman
        if self._aday != self.mevcut and zaman - self._aday_baslangic >= self.sure:
            self.mevcut = self._aday
            return self.mevcut
        return None

    def sifirla(self):
        self.mevcut = self._aday = Jest.BILINMIYOR


class KaydirmaAlgilayici:
    """Elin yatay hızlı hareketini (swipe) algılar.

    Son `pencere` saniyelik konumlar tutulur. Bu sürede el, el boyutunun `esik`
    katı kadar yatay yol aldıysa ve dikey sapma küçükse kaydırma sayılır.
    """

    def __init__(self, pencere=0.35, esik=1.6, bekleme=0.6):
        self.pencere = pencere
        self.esik = esik
        self.bekleme = bekleme
        self._gecmis = deque()
        self._son_tetikleme = -float("inf")

    def guncelle(self, nokta, boyut, zaman=None):
        """Kaydırma algılandıysa "sag" / "sol", yoksa None döndürür."""
        zaman = time.monotonic() if zaman is None else zaman
        self._gecmis.append((zaman, float(nokta[0]), float(nokta[1])))
        while self._gecmis and zaman - self._gecmis[0][0] > self.pencere:
            self._gecmis.popleft()

        if zaman - self._son_tetikleme < self.bekleme or len(self._gecmis) < 3:
            return None
        _, x0, y0 = self._gecmis[0]
        dx, dy = nokta[0] - x0, nokta[1] - y0
        if abs(dx) > self.esik * boyut and abs(dy) < 0.6 * abs(dx):
            self._son_tetikleme = zaman
            self._gecmis.clear()
            return "sag" if dx > 0 else "sol"
        return None

    def sifirla(self):
        self._gecmis.clear()


class JestYayincisi:
    """Ders 3: Her el için kararlı jestleri ve kaydırmaları OlayYolu'na yayınlar.

    Yayınlanan olaylar:
        el.goruldu / el.kayboldu   {el}
        jest.degisti               {el, jest, parmak_sayisi}
        jest.kaydirma              {el, yon}

    `eller`, `.taraf` ve `.noktalar` alanları olan nesnelerin listesidir (goru.el.El).
    """

    def __init__(self, yol, sure=0.3):
        self.yol = yol
        self.sure = sure
        self._durumlar = {}  # taraf -> (JestKararlilastirici, KaydirmaAlgilayici)

    def guncelle(self, eller, zaman):
        gorulen = {e.taraf: e for e in eller}
        for taraf in list(self._durumlar):
            if taraf not in gorulen:
                del self._durumlar[taraf]
                self.yol.yayinla("el.kayboldu", el=taraf)

        for taraf, el in gorulen.items():
            if taraf not in self._durumlar:
                self._durumlar[taraf] = (JestKararlilastirici(self.sure), KaydirmaAlgilayici())
                self.yol.yayinla("el.goruldu", el=taraf)
            kararli, kaydirma = self._durumlar[taraf]
            n = el.noktalar

            yeni_jest = kararli.guncelle(jest_tani(n), zaman)
            if yeni_jest is not None:
                self.yol.yayinla(
                    "jest.degisti", el=taraf, jest=yeni_jest.value, parmak_sayisi=sum(parmak_durumlari(n))
                )

            # Kaydırma sadece açık avuçla yapılır; böylece fare hareketi kaydırma sanılmaz
            if kararli.mevcut == Jest.AVUC:
                yon = kaydirma.guncelle(n[ORTA_KOK], el_boyutu(n), zaman)
                if yon:
                    self.yol.yayinla("jest.kaydirma", el=taraf, yon=yon)
            else:
                kaydirma.sifirla()

    def jest(self, taraf):
        """Elin şu anki kararlı jesti (el görünmüyorsa BILINMIYOR)."""
        durum = self._durumlar.get(taraf)
        return durum[0].mevcut if durum else Jest.BILINMIYOR
