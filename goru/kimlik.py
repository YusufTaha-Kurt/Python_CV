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


class KayitToplayici:
    """Bir kişiden çeşitli açılardan örnek toplar.

    Birbirinin aynısı 15 örnek, tek bir örnekten daha iyi değildir. Yeni örnek ancak mevcut
    örneklerin hepsinden yeterince farklıysa eklenir: kullanıcı başını hafifçe çevirdikçe
    farklı açılar birikir.
    """

    def __init__(self, hedef=12, cesitlilik=0.93, en_kucuk_yuz=80, en_dusuk_skor=0.9):
        self.hedef = hedef
        self.cesitlilik = cesitlilik
        self.en_kucuk_yuz = en_kucuk_yuz
        self.en_dusuk_skor = en_dusuk_skor
        self.ornekler = []

    @property
    def tamam(self):
        """Hedef örnek sayısına ulaşıldı mı?"""
        return len(self.ornekler) >= self.hedef

    def dene(self, gomme, yuz_satiri):
        """Örnek uygunsa ekler ve True döndürür."""
        if min(yuz_satiri[2], yuz_satiri[3]) < self.en_kucuk_yuz or yuz_satiri[-1] < self.en_dusuk_skor:
            return False
        if any(float(gomme @ g) > self.cesitlilik for g in self.ornekler):
            return False
        self.ornekler.append(gomme)
        return True
