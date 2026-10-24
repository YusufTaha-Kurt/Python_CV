"""
Ders 13 - Canlılık Testi

Yüz tanıma bir fotoğrafla kandırılabilir. Bu ders rastgele sırayla 3 hareket ister:
göz kırp, gülümse, başını sola / sağa çevir, ağzını aç. Her hareket 6 saniye içinde
yapılmalı. Fotoğraf komutla hareket edemediği için testi geçemez.

Tuşlar:  boşluk yeni test   q çıkış

Çalıştırma (depo kökünden):
    python dersler/ders_13_canlilik/canlilik_testi.py
    python dersler/ders_13_canlilik/canlilik_testi.py --kaynak fotograf.jpg   # fotoğrafla dene: KALIR
"""

import cv2

from goru import hud
from goru.canlilik import GOREVLER, CanlilikTesti
from goru.uygulama import Uygulama, arguman_ayraci
from goru.yuz import YuzTakipci, yuz_ciz


def main():
    """Ders akışı: test başlar (3 rastgele görev) → her karede yüz bulunur → CanlilikTesti görevin
    yapılıp yapılmadığına bakar → "gecti" / "kaldi". Boşluk tuşu yeni test başlatır."""
    args = arguman_ayraci("Canlılık Testi").parse_args()
    test = CanlilikTesti()
    bildirildi = False
    app = Uygulama(args, "Canlilik Testi")
    with YuzTakipci() as takipci:
        for kare, simdi in app.kareler():
            genislik = kare.shape[1]
            if not test.basladi:
                test.baslat(simdi)
            yuzler = takipci.isle(kare, simdi)
            yuz = yuzler[0] if yuzler else None
            sonuc = test.guncelle(yuz, simdi)  # None: sürüyor, "gecti" ya da "kaldi"
            if yuz is not None:
                yuz_ciz(kare, yuz)
            if sonuc and not bildirildi:
                bildirildi = True
                print(f"[CANLILIK] SONUC: {sonuc.upper()} {test.neden}")

            # Görev listesi: tamamlananlar yeşil, sıradaki turuncu
            for i, gorev in enumerate(test.gorevler):
                renk = hud.YESIL if i < test.adim else (hud.TURUNCU if i == test.adim and not sonuc else (120, 120, 120))
                cv2.putText(kare, f"{i + 1}. {GOREVLER[gorev]}", (genislik - 330, 50 + 34 * i), hud.FONT, 0.7,
                            renk, 2, cv2.LINE_AA)
            if test.gorev:
                cv2.putText(kare, test.talimat.upper(), (30, 80), hud.FONT, 1.4, hud.TURUNCU, 3, cv2.LINE_AA)
                kalan = test.kalan_sure(simdi) / test.adim_suresi
                cv2.rectangle(kare, (30, 100), (30 + int(400 * kalan), 112), hud.TURUNCU, -1)
            elif sonuc:
                renk, metin = (hud.YESIL, "CANLI: GECTI") if sonuc == "gecti" else (hud.KIRMIZI, "KALDI")
                cv2.rectangle(kare, (0, 30), (genislik, 120), renk, -1)
                cv2.putText(kare, metin, (30, 95), hud.FONT, 1.8, hud.BEYAZ, 4, cv2.LINE_AA)
                if test.neden:
                    cv2.putText(kare, test.neden, (30, 155), hud.FONT, 0.8, renk, 2, cv2.LINE_AA)
            if yuz is None:
                cv2.putText(kare, "YUZ YOK", (30, kare.shape[0] - 30), hud.FONT, 1.0, hud.KIRMIZI, 2, cv2.LINE_AA)

            if app.goster(kare) == ord(" "):
                test.baslat(simdi)
                bildirildi = False


if __name__ == "__main__":
    main()
