"""
Ders 14 - Kapı Bekçisi

Yüz tanıma (Ders 12) + canlılık testi (Ders 13) ile sanal bir kapı:

    KILITLI       Kayıtlı bir sahip 1 sn boyunca tanınırsa doğrulamaya geçer
    DOGRULANIYOR  Canlılık testi: ekrandaki 3 hareketi yap
    ACIK          "Hos geldin, <isim>". Sahip 30 sn görünmezse tekrar kilitlenir
                  (--windows-kilitle ile Windows oturumu da kilitlenir)

Tanınmayan biri 2 sn'den uzun görünürse uyarı verilir (--yabanci-kaydet ile o kare
guvenlik/ klasörüne kaydedilir).

Önce kendini kaydet:
    python dersler/ders_12_yuz_tanima/yuz_tanima.py --kaydet Yusuf
Sonra (depo kökünden):
    python dersler/ders_14_kapi_bekcisi/kapi_bekcisi.py
    python dersler/ders_14_kapi_bekcisi/kapi_bekcisi.py --windows-kilitle --kilit-suresi 60
"""

import ctypes
import os
import sys
import time

import cv2

from goru import hud
from goru.kapi import ACIK, DOGRULANIYOR, KILITLI, KapiBekcisi
from goru.kimlik import VARSAYILAN_ESIK, KimlikVeritabani, YuzTanima
from goru.olaylar import OlayYolu
from goru.uygulama import Uygulama, arguman_ayraci
from goru.yuz import YuzTakipci

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KIMLIK_KLASORU = os.path.join(KOK, "kimlikler")
GUVENLIK_KLASORU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guvenlik")
RENKLER = {KILITLI: hud.KIRMIZI, DOGRULANIYOR: hud.TURUNCU, ACIK: hud.YESIL}


def windows_kilitle():
    """Windows oturumunu kilitler (Win+L ile aynı). Başka işletim sistemlerinde bir şey yapmaz."""
    if sys.platform == "win32":
        ctypes.windll.user32.LockWorkStation()


def main():
    """Ders akışı: yüz tanıma (Ders 12) kimleri gördüğünü söyler → KapiBekcisi durum makinesi
    (KILITLI → DOGRULANIYOR → ACIK) canlılık testini (Ders 13) gerektiğinde çalıştırır →
    olaylara abone fonksiyonlar kilitleme ve yabancı kaydı gibi eylemleri yapar."""
    ayrac = arguman_ayraci("Kapı Bekçisi")
    ayrac.add_argument("--sahip", nargs="*", help="Kapıyı açabilecek kişiler (varsayılan: tüm kayıtlılar)")
    ayrac.add_argument("--kilit-suresi", type=float, default=30.0, help="Sahip bu kadar saniye görünmezse kilitle")
    ayrac.add_argument("--windows-kilitle", action="store_true", help="Kilitlenince Windows oturumunu da kilitle")
    ayrac.add_argument("--yabanci-kaydet", action="store_true", help="Yabancı görülünce kareyi kaydet")
    ayrac.add_argument("--esik", type=float, default=VARSAYILAN_ESIK)
    ayrac.add_argument("--kimlikler", default=KIMLIK_KLASORU, help="Kimlik veritabanı klasörü")
    args = ayrac.parse_args()

    veritabani = KimlikVeritabani(args.kimlikler, esik=args.esik)
    sahipler = args.sahip or veritabani.isimler
    if not sahipler:
        print("Kayıtlı kimse yok, kapı hiç açılmayacak. Önce kaydol:\n"
              "  python dersler/ders_12_yuz_tanima/yuz_tanima.py --kaydet ISIM")

    son_kare = {"kare": None}
    yol = OlayYolu()
    yol.abone_ol(OlayYolu.HEPSI, lambda o: print(f"[{time.strftime('%H:%M:%S')}] {o.ad} {o.veri}"))

    def kilitlendi(_):
        """kapi.kilitlendi olayı: istenmişse Windows oturumunu da kilitler."""
        if args.windows_kilitle and not args.sadece_izle:
            windows_kilitle()

    def yabanci(_):
        """kapi.yabanci olayı: istenmişse tanınmayan kişinin göründüğü kareyi guvenlik/ klasörüne kaydeder."""
        if args.yabanci_kaydet and son_kare["kare"] is not None:
            os.makedirs(GUVENLIK_KLASORU, exist_ok=True)
            yol_ = os.path.join(GUVENLIK_KLASORU, time.strftime("yabanci_%Y%m%d_%H%M%S.jpg"))
            cv2.imwrite(yol_, son_kare["kare"])
            print(f"[GUVENLIK] kaydedildi: {yol_}")

    yol.abone_ol("kapi.kilitlendi", kilitlendi)
    yol.abone_ol("kapi.yabanci", yabanci)
    kapi = KapiBekcisi(sahipler, yol=yol, kilit_suresi=args.kilit_suresi)
    tanima = YuzTanima()
    kimlikler, kutular = [], []
    fps = hud.FpsSayaci()

    app = Uygulama(args, "Kapi Bekcisi")
    with YuzTakipci() as yuz_takipci:
        for kare, simdi in app.kareler():
            son_kare["kare"] = kare.copy()
            genislik = kare.shape[1]
            # Tanıma her 2 karede bir yeterli; arada son sonuç kullanılır
            if app.kare_no % 2 == 1:
                yuzler = tanima.bul(kare)[:3]
                kutular = [s[:4].astype(int) for s in yuzler]
                kimlikler = [veritabani.tani(tanima.gomme(kare, s))[0] for s in yuzler]
            # MediaPipe yüz modeli sadece canlılık testi sırasında çalışır (işlemci tasarrufu)
            mp_yuz = None
            if kapi.durum == DOGRULANIYOR:
                mp_yuzler = yuz_takipci.isle(kare, simdi)
                mp_yuz = mp_yuzler[0] if mp_yuzler else None
            kapi.guncelle(kimlikler, mp_yuz, simdi)  # durum makinesi burada ilerler

            for (x, y, g, h), isim in zip(kutular, kimlikler):
                renk = hud.YESIL if isim in sahipler else hud.KIRMIZI
                cv2.rectangle(kare, (x, y), (x + g, y + h), renk, 2, cv2.LINE_AA)
                cv2.putText(kare, isim or "YABANCI", (x, y - 8), hud.FONT, 0.7, renk, 2, cv2.LINE_AA)

            renk = RENKLER[kapi.durum]
            if kapi.durum == ACIK:
                baslik = f"HOS GELDIN, {kapi.kisi.upper()}"
            elif kapi.durum == DOGRULANIYOR:
                baslik = f"{kapi.canlilik.talimat.upper()} ({kapi.canlilik.adim + 1}/{len(kapi.canlilik.gorevler)})"
            else:
                baslik = "KILITLI"
            cv2.rectangle(kare, (0, 0), (genislik, 70), renk, -1)
            cv2.putText(kare, baslik, (25, 50), hud.FONT, 1.3, hud.BEYAZ, 3, cv2.LINE_AA)
            hud.panel(kare, [f"Sahipler: {', '.join(sahipler) or '-'}", f"FPS: {fps.tik():.0f}", "q: cikis"],
                      sol_ust=(15, 85), baslik="KAPI BEKCISI")
            app.goster(kare)


if __name__ == "__main__":
    main()
