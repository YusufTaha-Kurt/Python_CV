"""
Ders 8 - Hava Çizimi

OpenCV Ders 3'teki fareyle çizim (paint) uygulamasının elle çalışan hali.

    Sadece işaret parmağı düz     Çiz
    İşaret + orta düz (zafer)     Kalemi kaldır, gezin. Üstteki paletten renk seç (parmağı kutuya götür)
    Açık avuç (0.8 sn tut)        Tuvali temizle

Tuşlar:  s kaydet (cizimler/ klasörüne)   + / - kalem kalınlığı   c temizle   q çıkış

Çalıştırma (depo kökünden):
    python dersler/ders_08_kontrol_merkezi/hava_cizimi.py
"""

import os

import cv2

from goru import hud
from goru.cizim import HavaTuvali
from goru.el import ElTakipci
from goru.uygulama import Uygulama, arguman_ayraci

KAYIT_KLASORU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cizimler")


def main():
    """Ders akışı: el bul → HavaTuvali parmak durumuna göre çizer / gezinir / siler → tuvali kamera karesine bindir."""
    ayrac = arguman_ayraci("Hava Çizimi")
    ayrac.add_argument("--el", choices=["sag", "sol"], default="sag", help="Çizen el")
    args = ayrac.parse_args()

    tuval = None
    mesaj = ""
    fps = hud.FpsSayaci()
    app = Uygulama(args, "Hava Cizimi")
    with ElTakipci(max_el=1) as takipci:
        for kare, simdi in app.kareler():
            yukseklik, genislik = kare.shape[:2]
            if tuval is None or (tuval.w, tuval.h) != (genislik, yukseklik):
                tuval = HavaTuvali(genislik, yukseklik)
            el = next((e for e in takipci.isle(kare, simdi) if e.taraf == args.el), None)
            olay = tuval.guncelle(el, simdi)
            if olay == "temizlendi":
                mesaj = "tuval temizlendi"
            elif olay == "renk":
                mesaj = f"renk: {tuval.renk[0]}"

            # Çizilenler kamera görüntüsünün üstüne bindirilir
            tuval.birlestir(kare)
            tuval.palet_ciz(kare)
            if el is not None:
                hud.iskelet_ciz(kare, el.noktalar, (120, 120, 120))
            if tuval.uc is not None:
                ad, renk = tuval.renk
                if tuval.durum == "ciziyor":
                    cv2.circle(kare, tuval.uc, tuval.kalinlik + 4, renk or (200, 200, 200), -1, cv2.LINE_AA)
                else:
                    cv2.circle(kare, tuval.uc, 14, hud.CAMGOBEGI, 2, cv2.LINE_AA)
            hud.panel(
                kare,
                [
                    (f"DURUM: {tuval.durum.upper()}", hud.YESIL),
                    f"RENK: {tuval.renk[0]}  KALINLIK: {tuval.kalinlik}",
                    (mesaj, hud.TURUNCU) if mesaj else f"FPS: {fps.tik():.0f}",
                    "s kaydet  +/- kalinlik  c temizle  q cikis",
                ],
                sol_ust=(15, 90),
                baslik="HAVA CIZIMI",
            )
            tus = app.goster(kare)
            if tus == ord("s"):
                mesaj = f"kaydedildi: {os.path.basename(tuval.kaydet(KAYIT_KLASORU))}"
                print(f"[CIZIM] {mesaj}")
            elif tus in (ord("+"), ord("=")):
                tuval.kalinlik = min(tuval.kalinlik + 2, 30)
            elif tus == ord("-"):
                tuval.kalinlik = max(tuval.kalinlik - 2, 2)
            elif tus == ord("c"):
                tuval.temizle()


if __name__ == "__main__":
    main()
