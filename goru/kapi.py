"""Ders 14: Kapı bekçisi. Yüz tanıma + canlılık testiyle kilit açma, sahip uzaklaşınca kilitleme.

    KILITLI ──(sahip 1 sn boyunca tanındı)──> DOGRULANIYOR ──(canlılık testi geçti)──> ACIK
       ^                                           │                                    │
       └───────────(test kaldı / 3 sn bekle)───────┘                                    │
       └──────────────────────(sahip kilit_suresi boyunca görünmedi)────────────────────┘

Yayınlanan olaylar: kapi.dogrulaniyor, kapi.acildi, kapi.reddedildi, kapi.kilitlendi, kapi.yabanci
"""

import math

from .canlilik import CanlilikTesti

KILITLI, DOGRULANIYOR, ACIK = "kilitli", "dogrulaniyor", "acik"


class KapiBekcisi:
    def __init__(self, sahipler, yol=None, tanima_suresi=1.0, kilit_suresi=30.0, yabanci_suresi=2.0,
                 yabanci_araligi=30.0, red_beklemesi=3.0, canlilik=None):
        self.sahipler = set(sahipler)
        self.yol = yol
        self.tanima_suresi = tanima_suresi
        self.kilit_suresi = kilit_suresi
        self.yabanci_suresi = yabanci_suresi
        self.yabanci_araligi = yabanci_araligi
        self.red_beklemesi = red_beklemesi
        self.canlilik = canlilik if canlilik is not None else CanlilikTesti()
        self.durum = KILITLI
        self.kisi = None  # Kapıyı açan / açmaya çalışan sahip
        self._sahip_baslangic = None
        self._yabanci_baslangic = None
        self._son_yabanci_uyarisi = -math.inf
        self._son_sahip_gorulme = 0.0
        self._bekle_bitis = -math.inf

    @property
    def sahip_burada(self):
        """Kapı açık mı (başka modüller "sadece sahip varken çalış" için kullanabilir)."""
        return self.durum == ACIK

    def _yayinla(self, ad, **veri):
        if self.yol is not None:
            self.yol.yayinla(ad, **veri)

    def guncelle(self, kimlikler, yuz, zaman):
        """kimlikler: bu karede görülen yüzlerin isimleri (tanınmayan: None).
        yuz: canlılık testi için MediaPipe yüzü (goru.yuz.Yuz) ya da None. Dönüş: durum."""
        sahip = next((k for k in kimlikler if k in self.sahipler), None)
        yabanci_var = any(k is None for k in kimlikler)

        # Yabancı: tanınmayan bir yüz yeterince uzun süre görünürse (her durumda) uyar
        if yabanci_var:
            self._yabanci_baslangic = self._yabanci_baslangic if self._yabanci_baslangic is not None else zaman
            if (zaman - self._yabanci_baslangic >= self.yabanci_suresi
                    and zaman - self._son_yabanci_uyarisi > self.yabanci_araligi):
                self._son_yabanci_uyarisi = zaman
                self._yayinla("kapi.yabanci", durum=self.durum)
        else:
            self._yabanci_baslangic = None

        if self.durum == KILITLI:
            if sahip is None or zaman < self._bekle_bitis:
                self._sahip_baslangic = None
            else:
                self._sahip_baslangic = self._sahip_baslangic if self._sahip_baslangic is not None else zaman
                if zaman - self._sahip_baslangic >= self.tanima_suresi:
                    self.durum, self.kisi = DOGRULANIYOR, sahip
                    self.canlilik.baslat(zaman)
                    self._yayinla("kapi.dogrulaniyor", kisi=sahip)

        elif self.durum == DOGRULANIYOR:
            sonuc = self.canlilik.guncelle(yuz, zaman)
            if sonuc == "gecti":
                self.durum, self._son_sahip_gorulme = ACIK, zaman
                self._yayinla("kapi.acildi", kisi=self.kisi)
            elif sonuc == "kaldi":
                self.durum, self._sahip_baslangic = KILITLI, None
                self._bekle_bitis = zaman + self.red_beklemesi
                self._yayinla("kapi.reddedildi", kisi=self.kisi, neden=self.canlilik.neden)
                self.kisi = None

        elif self.durum == ACIK:
            if sahip is not None:
                self._son_sahip_gorulme = zaman
            elif zaman - self._son_sahip_gorulme > self.kilit_suresi:
                self._yayinla("kapi.kilitlendi", kisi=self.kisi)
                self.durum, self.kisi, self._sahip_baslangic = KILITLI, None, None
        return self.durum
