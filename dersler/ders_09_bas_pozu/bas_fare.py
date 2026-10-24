"""
Ders 9 - Yüz İskeleti ve Baş Pozu

MediaPipe Face Landmarker ile 478 yüz noktası ve baş açıları (yaw / pitch / roll).
Açılar iki yoldan hesaplanır ve ekranda karşılaştırılır:
    MATRIS  MediaPipe'ın yüz dönüşüm matrisi (varsayılan)
    PNP     6 yüz noktası + genel 3D yüz modeli + cv2.solvePnP (klasik yöntem)

Uygulama: Başla imleç (eller serbest fare)
    Başını çevir                  İmleç hareket eder
    İmleci 1 sn bir yerde tut     Tıklar (bakarak tıklama, "dwell click")
İlk 1.5 sn ekranın ortasına bak: nötr pozun kalibre edilir.

Tuşlar:  c yeniden kalibre et   t bakarak tıklamayı aç / kapa   q çıkış

Çalıştırma (depo kökünden):
    python dersler/ders_09_bas_pozu/bas_fare.py --sadece-izle   # önce böyle dene
    python dersler/ders_09_bas_pozu/bas_fare.py
"""

import math

import cv2
import pyautogui

from goru import hud
from goru.bas_faresi import BasFaresi, BeklemeTiklayici
from goru.bas_pozu import matris_acilari, pnp_acilari
from goru.fare import PyAutoGuiFare, SahteFare
from goru.imlec import ImlecSurucu
from goru.uygulama import Uygulama, arguman_ayraci
from goru.yuz import YuzTakipci, yuz_ciz


def yon_oku(kare, yuz, yaw, pitch):
    """Burun ucundan, başın baktığı yöne doğru bir ok çizer."""
    burun = yuz.noktalar[1, :2]
    uzunluk = 4 * (yuz.kutu()[2] - yuz.kutu()[0]) / 3
    dx = math.sin(math.radians(yaw)) * uzunluk
    dy = -math.sin(math.radians(pitch)) * uzunluk
    bas = tuple(int(v) for v in burun)
    cv2.arrowedLine(kare, bas, (int(burun[0] + dx), int(burun[1] + dy)), hud.YESIL, 3, cv2.LINE_AA, tipLength=0.15)


def main():
    """Ders akışı (her karede): yüzü bul → baş açılarını iki yöntemle hesapla (ekranda karşılaştır)
    → BasFaresi açıları ekran hedefine çevirsin → imleç hareket etsin → 1 sn sabit kalırsa tıkla."""
    args = arguman_ayraci("Yüz İskeleti ve Baş Pozu").parse_args()
    ekran = tuple(pyautogui.size())
    fare = SahteFare(yazdir=True) if args.sadece_izle else PyAutoGuiFare()
    surucu = None if args.sadece_izle else ImlecSurucu()
    bas_faresi = BasFaresi(ekran)
    tiklayici = BeklemeTiklayici(sure=1.0, yaricap=0.02 * ekran[0])
    tiklama_acik = True
    fps = hud.FpsSayaci()
    if surucu:
        surucu.baslat()

    app = Uygulama(args, "Bas Pozu")
    with YuzTakipci() as takipci:
        for kare, simdi in app.kareler():
            yukseklik, genislik = kare.shape[:2]
            yuzler = takipci.isle(kare, simdi)
            satirlar = []
            if yuzler:
                yuz = yuzler[0]
                # Aynı açılar iki yoldan: MediaPipe matrisi (imleç bunu kullanır) ve klasik solvePnP
                yaw, pitch, roll = matris_acilari(yuz.donusum)
                pnp = pnp_acilari(yuz.noktalar, (genislik, yukseklik))
                yuz_ciz(kare, yuz)
                yon_oku(kare, yuz, yaw, pitch)
                # İlk 1.5 sn kalibrasyon (hedef None döner); sonra açılar ekran noktasına çevrilir
                hedef = bas_faresi.isle(yaw, pitch, simdi)
                if hedef is not None:
                    if surucu:
                        surucu.hedef_ayarla(*hedef)
                    if tiklama_acik and tiklayici.guncelle(hedef, simdi):
                        fare.tikla()
                satirlar += [
                    f"MATRIS yaw {yaw:+5.1f}  pitch {pitch:+5.1f}  roll {roll:+5.1f}",
                    f"PNP    yaw {pnp[0]:+5.1f}  pitch {pnp[1]:+5.1f}  roll {pnp[2]:+5.1f}" if pnp else "PNP    -",
                ]
                if not bas_faresi.kalibre:
                    satirlar.append((f"KALIBRASYON: ortaya bak %{int(bas_faresi.kalibrasyon_ilerlemesi(simdi) * 100)}",
                                     hud.TURUNCU))
                elif tiklama_acik:
                    satirlar.append((f"BAKARAK TIK: %{int(tiklayici.ilerleme * 100)}", hud.YESIL))
            else:
                tiklayici.sifirla()
                satirlar.append(("YUZ YOK", hud.TURUNCU))
            satirlar += [f"FPS: {fps.tik():.0f}", "c kalibre  t bakarak tik  q cikis"]
            hud.panel(kare, satirlar, baslik="BAS POZU // BASLA IMLEC")
            if bas_faresi.kalibre and tiklama_acik and tiklayici.ilerleme > 0:
                hud.reaktor_halkasi(kare, (genislik - 60, 60), tiklayici.ilerleme, yaricap=30)

            tus = app.goster(kare)
            if tus == ord("c"):
                bas_faresi.kalibre_et()
            elif tus == ord("t"):
                tiklama_acik = not tiklama_acik
                tiklayici.sifirla()

    if surucu:
        surucu.durdur()


if __name__ == "__main__":
    main()
