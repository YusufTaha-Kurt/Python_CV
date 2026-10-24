"""
Ders 10 - Göz Kırpma ve Yorgunluk

Göz Açıklık Oranı (EAR) ile göz kırpma algılama ve PERCLOS ile yorgunluk izleme.

Olaylar:
    Doğal kırpma (< 0.35 sn)     Sayılır (dakikadaki kırpma hızı)
    Bilinçli kırpma (0.35-1.5)   --fare açıksa SOL TIK
    Tek göz kırpma               --fare açıksa ekranın sağındaki gözle SAĞ TIK
    Gözler 1.5 sn kapalı          MİKRO UYKU uyarısı
    PERCLOS > %15 (son 1 dk)     YORGUNLUK uyarısı
    Uzun esneme                   Sayılır

--fare: Ders 9'daki başla imleçle birleşir. Başını çevirerek imleci yönet, gözlerini
kısa süre bilerek kapatarak tıkla: tamamen eller serbest bir fare.

Çalıştırma (depo kökünden):
    python dersler/ders_10_goz_kirpma/goz_kirpma.py                  # sadece izleme ve uyarı
    python dersler/ders_10_goz_kirpma/goz_kirpma.py --fare --alarm
"""

import sys
import threading
import time

import cv2
import pyautogui

from goru import hud
from goru.bas_faresi import BasFaresi
from goru.bas_pozu import matris_acilari
from goru.fare import PyAutoGuiFare, SahteFare
from goru.goz import EKRAN_SAG_GOZ, EKRAN_SOL_GOZ, GozKirpmaAlgilayici, YorgunlukIzleyici
from goru.imlec import ImlecSurucu
from goru.uygulama import Uygulama, arguman_ayraci
from goru.yuz import YuzTakipci, yuz_ciz

UYARI_METINLERI = {"mikro_uyku": "GOZLERIN KAPANDI!", "yorgunluk": "YORGUNSUN: MOLA VER", "esneme": "esneme"}


def bip():
    """Sesli uyarı, döngüyü bekletmeden (sadece Windows)."""
    if sys.platform == "win32":
        import winsound

        threading.Thread(target=winsound.Beep, args=(1200, 400), daemon=True).start()


def goz_ciz(kare, yuz, goz, kapali):
    """Gözleri konturla çizer: açık yeşil, kapalı kırmızı."""
    for indeksler, k in ((EKRAN_SOL_GOZ, kapali[0]), (EKRAN_SAG_GOZ, kapali[1])):
        noktalar = yuz.noktalar[list(indeksler), :2].astype(int)
        cv2.polylines(kare, [noktalar], True, hud.KIRMIZI if k else hud.YESIL, 2, cv2.LINE_AA)


def ear_cubugu(kare, x, etiket, deger, taban, kapanma):
    """Dikey EAR çubuğu ve kapanma eşiği çizgisi."""
    olcek = 0.45  # EAR ekseninin üst sınırı
    hud.cubuk(kare, (x, 120), (30, 200), deger / olcek, etiket)
    y = int(120 + 200 * (1 - kapanma / olcek))
    cv2.line(kare, (x - 6, y), (x + 36, y), hud.KIRMIZI, 2)
    y = int(120 + 200 * (1 - taban / olcek))
    cv2.line(kare, (x - 6, y), (x + 36, y), hud.BEYAZ, 1)


def main():
    """Ders akışı (her karede): yüzü bul → göz kırpma algılayıcı olay üretir (doğal / bilinçli / tek göz / mikro uyku)
    → yorgunluk izleyici PERCLOS ve esnemeyi hesaplar → uyarı / (isteğe bağlı) baş faresiyle tıklama."""
    ayrac = arguman_ayraci("Göz Kırpma ve Yorgunluk")
    ayrac.add_argument("--fare", action="store_true", help="Başla imleç + göz kırparak tıklama")
    ayrac.add_argument("--alarm", action="store_true", help="Yorgunlukta sesli uyarı")
    args = ayrac.parse_args()

    goz = GozKirpmaAlgilayici()
    yorgunluk = YorgunlukIzleyici()
    bas_faresi = surucu = fare = None
    if args.fare:
        bas_faresi = BasFaresi(tuple(pyautogui.size()))
        fare = SahteFare(yazdir=True) if args.sadece_izle else PyAutoGuiFare()
        surucu = None if args.sadece_izle else ImlecSurucu()
        if surucu:
            surucu.baslat()
    gecmis = []  # (zaman, olay)
    uyari = (None, 0.0)
    fps = hud.FpsSayaci()

    app = Uygulama(args, "Goz Kirpma")
    with YuzTakipci() as takipci:
        for kare, simdi in app.kareler():
            genislik = kare.shape[1]
            yuzler = takipci.isle(kare, simdi)
            if yuzler:
                yuz = yuzler[0]
                olaylar = goz.guncelle(yuz.noktalar, simdi)  # göz olayları
                uyarilar = yorgunluk.guncelle(goz.ikisi_kapali, olaylar, yuz.ifadeler.get("jawOpen", 0.0), simdi)
                for olay in olaylar + uyarilar:
                    print(f"[{time.strftime('%H:%M:%S')}] {olay}")
                    gecmis = (gecmis + [(simdi, olay)])[-4:]
                for u in uyarilar:
                    if u != "esneme":
                        uyari = (u, simdi)
                        if args.alarm and not args.sadece_izle:
                            bip()

                # --fare: baş imleci yönetir, bilinçli kırpma sol tık, sağ göz kırpma sağ tık
                if bas_faresi is not None:
                    yaw, pitch, _ = matris_acilari(yuz.donusum)
                    hedef = bas_faresi.isle(yaw, pitch, simdi)
                    if surucu and hedef:
                        # Göz kapanırken baş biraz oynar: herhangi bir göz kapalıyken imleci dondur
                        surucu.dondur(goz.kapali[0] or goz.kapali[1])
                        surucu.hedef_ayarla(*hedef)
                    if bas_faresi.kalibre:
                        if "bilincli" in olaylar:
                            fare.tikla()
                        if "goz_kirp_sag" in olaylar:
                            fare.sag_tikla()

                yuz_ciz(kare, yuz, (150, 150, 150))
                goz_ciz(kare, yuz, goz, goz.kapali)
                if goz.hazir:
                    ear_cubugu(kare, genislik - 120, "SOL", goz.ear[0], goz.taban[0], goz.esikler(0)[0])
                    ear_cubugu(kare, genislik - 60, "SAG", goz.ear[1], goz.taban[1], goz.esikler(1)[0])

            satirlar = [
                (f"GOZLER: {'KAPALI' if goz.ikisi_kapali else 'acik'}" if yuzler else "YUZ YOK", hud.YESIL),
                f"PERCLOS (1 dk): %{yorgunluk.perclos * 100:.1f}",
                f"Kirpma: {yorgunluk.kirpma_hizi:.0f}/dk   Esneme: {yorgunluk.esneme_sayisi}",
                f"FPS: {fps.tik():.0f}",
            ]
            if bas_faresi is not None and not bas_faresi.kalibre:
                satirlar.append((f"KALIBRASYON: ortaya bak %{int(bas_faresi.kalibrasyon_ilerlemesi(simdi) * 100)}", hud.TURUNCU))
            satirlar += [(f"{olay}", hud.TURUNCU) for _, olay in reversed(gecmis)]
            hud.panel(kare, satirlar, baslik="GOZ KIRPMA // YORGUNLUK")
            if uyari[0] and simdi - uyari[1] < 2.5:
                metin = UYARI_METINLERI[uyari[0]]
                cv2.rectangle(kare, (0, kare.shape[0] - 70), (genislik, kare.shape[0]), hud.KIRMIZI, -1)
                cv2.putText(kare, metin, (30, kare.shape[0] - 22), hud.FONT, 1.2, hud.BEYAZ, 3, cv2.LINE_AA)
            tus = app.goster(kare)
            if tus == ord("c") and bas_faresi is not None:
                bas_faresi.kalibre_et()

    if surucu:
        surucu.durdur()


if __name__ == "__main__":
    main()
