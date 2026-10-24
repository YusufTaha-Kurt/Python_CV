"""Ders 5: Yanlış tetiklemeye karşı katmanlı, güvenilir çimdik algılayıcı.

Sadece "iki parmak ucu yakın mı?" diye bakan bir algılayıcı (Ders 2) yumruğu, kenetlenmiş
elleri ve yüze dokunan eli de çimdik sanar. Bu sınıf yedi katman ekler:

  1. İmza (kontrast yasası): Gerçek çimdikte çimdik parmağı kıvrılır, diğer üç parmak
     dışarıda kalır ("OK işareti"). Yumrukta hepsi kıvrıktır. Avuç yan dönükken başparmağın
     yüzük köküne uzaklığı ikinci bir imza olarak kabul edilir.
  2. Onay: İmza iki ardışık karede görülmeli ya da üstel ortalaması eşiği geçmeli.
  3. İmkânsız geometri: Avuç en-boy oranı gerçek bir elde olamayacak kadar büyükse el
     hiçbir şey tetikleyemez.
  4. Hayalet kapısı: Çok hızlı hareket sırasında "doğan" çimdik hayalettir, bir şey kavrayamaz.
     El yavaşlayınca kendini iyileştirir.
  5. Hıza duyarlı bırakma: El hızlıyken bırakma eşiği yükselir ve iki kare art arda açık
     görülmelidir (bulanık parmaklar sahte bırakma üretmesin).
  6. Deneme süresi: Yeni çimdik ilk 400 ms boyunca imzasını korumalı, yoksa iptal edilir.
  7. Histerezis: Başlama eşiği bırakma eşiğinden küçüktür (Ders 2'den).

Fikirler barehands projesinden (jaredrhod, AGPL-3.0) esinlenmiştir; kod ve eşikler bu repo
için piksel uzayında yeniden yazılmıştır. Ayrıntılar: docs/referanslar/barehands_analizi.md
"""

import json
import math
import os
from collections import deque
from dataclasses import asdict, dataclass, fields

from . import jestler as j


@dataclass
class CimdikAyarlari:
    baslama: float = 0.30  # Parmak arası / el boyu: önden bakışta çimdik başlama eşiği
    baslama_profil: float = 0.38  # Avuç yan dönükken (ölçüm daha gürültülü, eşik daha geniş)
    birakma: float = 0.55  # Yavaş elde bırakma eşiği
    birakma_hizli: float = 0.70  # Hızlı elde bırakma eşiği
    kontrast: float = 0.18  # Diğer parmakların ortalama kemeri - çimdik parmağının kemeri
    arka_kemer: float = 1.30  # Diğer parmakların ortalama kemeri en az bu kadar olmalı (yumruk duvarı)
    profil_en_boy: float = 1.15  # Avuç en-boy oranı bunun altındaysa "yan dönük" sayılır
    profil_bas_uzakligi: float = 0.95  # Yan dönük avuçta başparmak ucu - yüzük kökü / el boyu
    imkansiz_en_boy: float = 8.0  # Bunun üstü gerçek bir el değil
    ema_esigi: float = 0.55
    hayalet_hizi: float = 4.5  # El boyu / saniye. Bu hızda doğan çimdik hayalettir
    iyilesme_hizi: float = 2.5  # Hayalet çimdik bu hızın altına inince kavrayabilir
    hizli_el: float = 4.0  # Bu hızın üstünde hıza duyarlı bırakma devreye girer
    deneme_suresi: float = 0.4
    deneme_hiz_siniri: float = 3.0  # Hızlı sürüklemede deneme süresi uygulanmaz (bulanıklık)
    deneme_kotu_kare: int = 4
    kontrast_zorunlu: bool = True  # False: imza aranmaz (Ders 2 davranışı + diğer katmanlar)

    @classmethod
    def yukle(cls, yol):
        """JSON dosyasından yükler; dosya yoksa varsayılanları döndürür."""
        if not yol or not os.path.exists(yol):
            return cls()
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
        gecerli = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in veri.items() if k in gecerli})

    def kaydet(self, yol):
        os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as dosya:
            json.dump(asdict(self), dosya, indent=2, ensure_ascii=False)


def olcumler(noktalar, uc=j.ISARET_UCU):
    """Çimdik kararında kullanılan ölçümler (örnekleyici ve hata ayıklama ekranı da kullanır)."""
    boy = j.el_boyutu(noktalar)
    digerleri = [j.kemer_orani(noktalar, u) for u in j.PARMAKLAR if u != uc]
    arka = sum(digerleri) / len(digerleri)
    return {
        "oran": j.mesafe(noktalar, j.BAS_UCU, uc) / boy,
        "kontrast": arka - j.kemer_orani(noktalar, uc),
        "arka": arka,
        "en_boy": j.avuc_en_boy(noktalar),
        "bas_uzakligi": j.mesafe(noktalar, j.BAS_UCU, j.YUZUK_KOK) / boy,
    }


class GuvenilirCimdik:
    """Bir elin başparmağı ile bir parmağı arasındaki çimdiği izler.

    `guncelle()` her kare çağrılır ve şu olaylardan birini (ya da None) döndürür:
        "basladi"   Çimdik başladı (hayalet olabilir, bkz. `kavrayabilir`)
        "iyilesti"  Hayalet çimdik yavaşladı, artık kavrayabilir
        "bitti"     Parmaklar açıldı
        "iptal"     Çimdik deneme süresinde imzasını kaybetti ya da el şekli imkânsızlaştı
    """

    HIZ_PENCERESI = 0.3  # Hız bu kadar saniyelik geçmişten hesaplanır

    def __init__(self, parmak_ucu=j.ISARET_UCU, ayarlar=None):
        self.uc = parmak_ucu
        self.ayar = ayarlar or CimdikAyarlari()
        self.sifirla()

    def sifirla(self):
        self.aktif = False
        self.hayalet = False
        self.imza = False
        self.hiz = 0.0
        self.olcum = {}
        self.nokta = None  # Başparmak ile parmak ucunun orta noktası
        self._ema = 0.0
        self._onceki_imza = False
        self._onceki_acik = False
        self._baslangic = 0.0
        self._kotu_kare = 0
        self._gecmis = deque()

    @property
    def kavrayabilir(self):
        return self.aktif and not self.hayalet

    def _hiz_guncelle(self, nokta, boy, zaman):
        self._gecmis.append((zaman, float(nokta[0]), float(nokta[1])))
        while len(self._gecmis) > 2 and zaman - self._gecmis[0][0] > self.HIZ_PENCERESI:
            self._gecmis.popleft()
        t0, x0, y0 = self._gecmis[0]
        dt = zaman - t0
        self.hiz = math.hypot(nokta[0] - x0, nokta[1] - y0) / dt / boy if dt > 0 else 0.0

    def guncelle(self, noktalar, zaman):
        a = self.ayar
        o = self.olcum = olcumler(noktalar, self.uc)
        self.nokta = (noktalar[j.BAS_UCU, :2] + noktalar[self.uc, :2]) / 2
        self._hiz_guncelle(self.nokta, j.el_boyutu(noktalar), zaman)

        # 1. İmza ve 2. onay
        profil = o["en_boy"] < a.profil_en_boy
        on_imza = o["kontrast"] > a.kontrast and o["arka"] > a.arka_kemer
        profil_imza = self.uc == j.ISARET_UCU and profil and o["bas_uzakligi"] > a.profil_bas_uzakligi
        self.imza = (on_imza or profil_imza) if a.kontrast_zorunlu else True
        self._ema = 0.7 * self._ema + 0.3 * (1.0 if self.imza else 0.0)
        onay = (self.imza and self._onceki_imza) or self._ema > a.ema_esigi
        self._onceki_imza = self.imza

        # 5. Hıza duyarlı bırakma okuması
        hizli = self.hiz > a.hizli_el
        acik = o["oran"] >= (a.birakma_hizli if hizli else a.birakma)
        birakilabilir = (acik and self._onceki_acik) if hizli else acik
        self._onceki_acik = acik

        # 3. İmkânsız geometri: bu el ne başlatabilir ne de tutabilir
        if o["en_boy"] > a.imkansiz_en_boy:
            if self.aktif:
                self.aktif = False
                return "iptal"
            return None

        if not self.aktif:
            esik = a.baslama_profil if profil else a.baslama
            if o["oran"] < esik and onay:
                self.aktif = True
                self._baslangic = zaman
                self._kotu_kare = 0
                self.hayalet = self.hiz > a.hayalet_hizi  # 4. Hayalet kapısı
                return "basladi"
            return None

        if birakilabilir:
            self.aktif = False
            return "bitti"
        # 6. Deneme süresi (hızlı sürüklemede bulanıklık sahte iptal üretmesin diye uygulanmaz)
        if zaman - self._baslangic < a.deneme_suresi and self.hiz < a.deneme_hiz_siniri:
            self._kotu_kare = 0 if self.imza else self._kotu_kare + 1
            if self._kotu_kare >= a.deneme_kotu_kare:
                self.aktif = False
                return "iptal"
        if self.hayalet and self.hiz < a.iyilesme_hizi:
            self.hayalet = False
            return "iyilesti"
        return None
