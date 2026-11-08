"""Ders 12: Yüz tanıma. YuNet ile yüz bulma, SFace ile 128 boyutlu yüz gömme vektörü.

Bir yüz, onu temsil eden 128 sayılık bir vektöre (gömme) çevrilir. Aynı kişinin farklı
fotoğraflarının vektörleri birbirine yakın, farklı kişilerinki uzaktır. Yakınlık kosinüs
benzerliğiyle ölçülür (vektörler birim uzunluğa normalize edildiği için iç çarpım).

Ölçülen (tests ve README): aynı kişi aynalı / karanlık / küçük / döndürülmüş 0.95-0.97,
farklı kişiler 0.01-0.24. SFace'in önerdiği eşik 0.363; kapı bekçisi için 0.40 kullanılır.

Gizlilik: Gömme vektörleri biyometrik veridir. Sadece yerel `kimlikler/` klasöründe tutulur
ve .gitignore'dadır.
"""

import os
import re

import numpy as np

from .modeller import model_yolu

VARSAYILAN_ESIK = 0.40


class YuzTanima:
    """İki aşamalı tanıma hattı: önce YuNet yüzü bulur (`bul`), sonra SFace onu vektöre çevirir (`gomme`).

    Bu sınıf kimseyi "tanımaz"; sadece sayısal vektör üretir. Hangi vektörün kime ait olduğunu
    aşağıdaki KimlikVeritabani karar verir.
    """

    def __init__(self, tespit_esigi=0.85):
        import cv2

        self._dedektor = cv2.FaceDetectorYN.create(model_yolu("yunet"), "", (320, 320), tespit_esigi, 0.3, 5000)
        self._tanima = cv2.FaceRecognizerSF.create(model_yolu("sface"), "")
        self._boyut = None

    def bul(self, kare):
        """Karedeki yüzleri bulur (büyükten küçüğe). YuNet satırları: [x, y, g, h, 5 nokta (10 sayı), skor]. En büyük yüz önce."""
        yukseklik, genislik = kare.shape[:2]
        if self._boyut != (genislik, yukseklik):
            self._dedektor.setInputSize((genislik, yukseklik))
            self._boyut = (genislik, yukseklik)
        _, yuzler = self._dedektor.detect(kare)
        if yuzler is None:
            return []
        return sorted(yuzler, key=lambda y: -y[2] * y[3])

    def gomme(self, kare, yuz_satiri):
        """Yüzü göz noktalarına göre hizalar, 128 boyutlu birim vektör döndürür."""
        hizali = self._tanima.alignCrop(kare, yuz_satiri)
        vektor = self._tanima.feature(hizali).flatten().astype(np.float32)
        return vektor / max(float(np.linalg.norm(vektor)), 1e-9)


def guvenli_isim(isim):
    """Dosya adı olarak güvenli hale getirir ("../" gibi kaçışları engeller)."""
    temiz = re.sub(r"[^\w\- ]", "", isim, flags=re.UNICODE).strip()
    if not temiz:
        raise ValueError(f"Geçersiz isim: {isim!r}")
    return temiz


class KimlikVeritabani:
    """Her kişi için birden çok gömme vektörü: <klasör>/<isim>.npy"""

    def __init__(self, klasor, esik=VARSAYILAN_ESIK):
        self.klasor = klasor
        self.esik = esik
        self.kisiler = {}
        if os.path.isdir(klasor):
            for ad in sorted(os.listdir(klasor)):
                if ad.endswith(".npy"):
                    self.kisiler[ad[:-4]] = np.load(os.path.join(klasor, ad))

    @property
    def isimler(self):
        """Kayıtlı kişilerin alfabetik listesi."""
        return sorted(self.kisiler)

    def ekle(self, isim, gommeler):
        """Kişiye yeni örnekler ekler (varsa eskilerin yanına) ve diske yazar. Güvenli hâle getirilmiş adı döndürür."""
        isim = guvenli_isim(isim)
        yeni = np.asarray(gommeler, dtype=np.float32).reshape(-1, 128)
        self.kisiler[isim] = np.vstack([self.kisiler[isim], yeni]) if isim in self.kisiler else yeni
        os.makedirs(self.klasor, exist_ok=True)
        np.save(os.path.join(self.klasor, f"{isim}.npy"), self.kisiler[isim])
        return isim

    def sil(self, isim):
        """Kişiyi ve dosyasını siler (biyometrik veriyi kaldırmak için)."""
        isim = guvenli_isim(isim)
        self.kisiler.pop(isim, None)
        yol = os.path.join(self.klasor, f"{isim}.npy")
        if os.path.exists(yol):
            os.remove(yol)

    def tani(self, gomme):
        """(isim ya da None, en yüksek benzerlik). Her kişinin en benzer örneği kullanılır.

        Benzerlik eşiğin altındaysa isim None döner: yani "bu kayıtlı biri değil".
        `ornekler @ gomme` birim vektörlerde kosinüs benzerliğidir (iç çarpım).
        """
        en_iyi, en_iyi_benzerlik = None, -1.0
        for isim, ornekler in self.kisiler.items():
            benzerlik = float(np.max(ornekler @ gomme))
            if benzerlik > en_iyi_benzerlik:
                en_iyi, en_iyi_benzerlik = isim, benzerlik
        return (en_iyi if en_iyi_benzerlik >= self.esik else None), en_iyi_benzerlik


def yuz_yonu(yuz_satiri):
    """YuNet'in 5 noktasından kabaca baş yönü: (yatay, dikey).

    yatay: Burnun iki gözün ortasından yana kayması, göz arası mesafeye oranla. Aynalı
           görüntüde baş kullanıcının soluna dönünce eksi, sağına dönünce artı olur.
    dikey: Burnun göz çizgisi ile ağız arasındaki yeri (0 göz, 1 ağız). Baş yukarı kalkınca
           küçülür, aşağı inince büyür.
    Mutlak değerler kişiden kişiye değişir; YonluKayit bunları "düz bakış" tabanına göre kullanır.
    """
    s = np.asarray(yuz_satiri, dtype=np.float32)
    goz1, goz2, burun, agiz1, agiz2 = s[4:6], s[6:8], s[8:10], s[10:12], s[12:14]
    goz_orta, agiz_orta = (goz1 + goz2) / 2, (agiz1 + agiz2) / 2
    goz_arasi = max(float(np.linalg.norm(goz2 - goz1)), 1e-6)
    yatay = float(burun[0] - goz_orta[0]) / goz_arasi
    dikey = float(burun[1] - goz_orta[1]) / max(float(agiz_orta[1] - goz_orta[1]), 1e-6)
    return yatay, dikey


# (ad, ekranda gösterilecek komut, örnek sayısı)
KAYIT_ADIMLARI = (
    ("orta", "Kameraya duz bak", 3),
    ("sol", "Basini yavasca SOLA cevir", 2),
    ("sag", "Basini yavasca SAGA cevir", 2),
    ("yukari", "Basini hafifce YUKARI kaldir", 2),
    ("asagi", "Basini hafifce ASAGI indir", 2),
)


class YonluKayit:
    """Kullanıcıyı adım adım yönlendirerek farklı açılardan örnek toplar.

    Eski toplayıcı hiçbir yön söylemiyordu ve birbirine benzeyen kareleri sessizce atlıyordu;
    kullanıcı neyi yanlış yaptığını bilemiyordu. Burada her adımda ekranda ne yapılacağı yazar.
    Örnek, baş istenen yöne yeterince döndüğünde alınır. Bir adımda `adim_suresi` içinde
    istenen açı yakalanamazsa (kamera açısı, gözlük) o adımda açıya bakılmadan örnek alınır,
    böylece kayıt hiçbir adımda takılı kalmaz.
    """

    def __init__(self, adimlar=KAYIT_ADIMLARI, yatay_esigi=0.10, dikey_esigi=0.07, ayni_ornek=0.97,
                 adim_suresi=8.0, en_kucuk_yuz=80, en_dusuk_skor=0.9):
        self.adimlar = adimlar
        self.yatay_esigi = yatay_esigi
        self.dikey_esigi = dikey_esigi
        self.ayni_ornek = ayni_ornek
        self.adim_suresi = adim_suresi
        self.en_kucuk_yuz = en_kucuk_yuz
        self.en_dusuk_skor = en_dusuk_skor
        self.ornekler = []
        self.adim = 0
        self._adim_ornegi = 0
        self._adim_baslangic = None
        self._orta_yonler = []
        self.taban = None  # Düz bakıştaki (yatay, dikey)
        self.yon = (0.0, 0.0)  # Son karedeki yön, tabana göre

    @property
    def hedef(self):
        return sum(adet for *_, adet in self.adimlar)

    @property
    def tamam(self):
        return self.adim >= len(self.adimlar)

    @property
    def komut(self):
        """Şu an ekranda gösterilecek yönerge."""
        return "Tamam" if self.tamam else self.adimlar[self.adim][1]

    def kalan_sure(self, zaman):
        """Bu adımda açıya bakılmadan örnek alınmaya başlanana kadar kalan süre (sn)."""
        if self._adim_baslangic is None:
            return self.adim_suresi
        return max(0.0, self.adim_suresi - (zaman - self._adim_baslangic))

    def _istenen_yonde(self, ad):
        yatay, dikey = self.yon
        return {
            "orta": abs(yatay) < self.yatay_esigi and abs(dikey) < self.dikey_esigi,
            "sol": yatay < -self.yatay_esigi,
            "sag": yatay > self.yatay_esigi,
            "yukari": dikey < -self.dikey_esigi,
            "asagi": dikey > self.dikey_esigi,
        }[ad]

    def dene(self, gomme, yuz_satiri, zaman):
        """Örnek bu adıma uygunsa ekler ve True döndürür."""
        if self.tamam:
            return False
        if self._adim_baslangic is None:
            self._adim_baslangic = zaman
        if min(yuz_satiri[2], yuz_satiri[3]) < self.en_kucuk_yuz or yuz_satiri[-1] < self.en_dusuk_skor:
            return False
        ad, _, adet = self.adimlar[self.adim]
        ham = yuz_yonu(yuz_satiri)
        if ad == "orta" and self.taban is None:
            self.yon = (0.0, 0.0)  # Taban henüz yok: düz bakış adımında her yön kabul
        else:
            taban = self.taban if self.taban is not None else ham
            self.yon = (ham[0] - taban[0], ham[1] - taban[1])
        sure_doldu = zaman - self._adim_baslangic >= self.adim_suresi
        if not (sure_doldu or ad == "orta" or self._istenen_yonde(ad)):
            return False
        if any(float(gomme @ g) > self.ayni_ornek for g in self.ornekler):
            return False  # Birebir aynı kare: bir şey katmaz
        self.ornekler.append(gomme)
        if ad == "orta":
            self._orta_yonler.append(ham)
            self.taban = tuple(np.median(np.array(self._orta_yonler), axis=0))
        self._adim_ornegi += 1
        if self._adim_ornegi >= adet:
            self.adim += 1
            self._adim_ornegi = 0
            self._adim_baslangic = None
        return True
