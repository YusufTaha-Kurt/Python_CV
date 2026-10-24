"""
Ders 16 - Vücut Pozu

MediaPipe Pose Landmarker ile 33 vücut noktası. Üç iş birden:

    Egzersiz sayacı   Eklem açısıyla tekrar sayar (--egzersiz squat | biceps | sinav)
    Duruş bekçisi     Masa başında kambur oturunca ya da yana yaslanınca uyarır
                      (ilk 3 sn dik otur: duruşun kalibre edilir)
    Vücut jestleri    İki el yukarı, T pozu

Tuşlar:  c duruşu yeniden kalibre et   r sayacı sıfırla   q çıkış

Çalıştırma (depo kökünden):
    python dersler/ders_16_vucut_pozu/vucut_pozu.py
    python dersler/ders_16_vucut_pozu/vucut_pozu.py --egzersiz biceps
"""

import sys
import threading
import time

import cv2

from goru import hud
from goru.egzersiz import EGZERSIZLER, DurusBekcisi, TekrarSayaci, VucutJestleri, egzersiz_acisi
from goru.olaylar import OlayYolu
from goru.poz import PozTakipci, poz_ciz
from goru.uygulama import Uygulama, arguman_ayraci

UYARILAR = {"kambur": "DIK OTUR", "egik_omuz": "OMUZLARINI DUZELT"}


def bip():
    """Sesli uyarı, döngüyü bekletmeden (sadece Windows)."""
    if sys.platform == "win32":
        import winsound

        threading.Thread(target=winsound.Beep, args=(880, 300), daemon=True).start()


def main():
    """Ders akışı (her karede): vücut noktalarını bul → seçilen egzersizin eklem açısını ölç → tekrar say →
    duruş bekçisi kambur / eğik omuzu izle → iki el yukarı / T pozu gibi vücut jestlerini tanı."""
    ayrac = arguman_ayraci("Vücut Pozu")
    ayrac.add_argument("--egzersiz", choices=sorted(EGZERSIZLER), default="squat")
    ayrac.add_argument("--alarm", action="store_true", help="Duruş uyarısında ses çal")
    args = ayrac.parse_args()

    egzersiz = EGZERSIZLER[args.egzersiz]
    sayac = TekrarSayaci(egzersiz["asagi"], egzersiz["yukari"])
    durus = DurusBekcisi()
    jestler = VucutJestleri()
    yol = OlayYolu()
    yol.abone_ol(OlayYolu.HEPSI, lambda o: print(f"[{time.strftime('%H:%M:%S')}] {o.ad} {o.veri}"))
    uyari = (None, 0.0)
    fps = hud.FpsSayaci()

    app = Uygulama(args, "Vucut Pozu")
    with PozTakipci() as takipci:
        for kare, simdi in app.kareler():
            yukseklik, genislik = kare.shape[:2]
            pozlar = takipci.isle(kare, simdi)
            aci_ = None
            if pozlar:
                poz = pozlar[0]
                poz_ciz(kare, poz)
                # Açı eşiklerin altına inip tekrar üstüne çıkınca 1 tekrar sayılır
                aci_ = egzersiz_acisi(poz, args.egzersiz)
                if sayac.guncelle(aci_):
                    yol.yayinla("egzersiz.tekrar", egzersiz=args.egzersiz, sayi=sayac.sayi)
                for u in durus.guncelle(poz, simdi):
                    yol.yayinla("durus.uyari", tur=u)
                    uyari = (u, simdi)
                    if args.alarm and not args.sadece_izle:
                        bip()
                jest = jestler.guncelle(poz, simdi)
                if jest:
                    yol.yayinla("vucut.jest", jest=jest)

            # Büyük tekrar sayacı
            cv2.putText(kare, str(sayac.sayi), (genislik - 150, 120), hud.FONT, 3.5, hud.YESIL, 8, cv2.LINE_AA)
            cv2.putText(kare, egzersiz["ad"], (genislik - 230, 160), hud.FONT, 0.8, hud.BEYAZ, 2, cv2.LINE_AA)
            satirlar = [
                (f"ACI: {aci_:.0f} derece  ({sayac.faz})" if aci_ is not None else "ACI: eklemler gorunmuyor", hud.YESIL),
                f"Esikler: asagi < {egzersiz['asagi']}  yukari > {egzersiz['yukari']}",
            ]
            if durus.taban is None:
                satirlar.append((f"DURUS KALIBRASYONU: dik otur %{int(durus.kalibrasyon_ilerlemesi(simdi) * 100)}",
                                 hud.TURUNCU))
            elif durus.oran is not None:
                anlik = durus.durum()
                satirlar.append((f"Durus: %{100 * durus.oran / durus.taban:.0f}  egim {durus.egim:+.0f}",
                                 hud.TURUNCU if any(anlik.values()) else hud.YESIL))
            satirlar += [f"Jest: {jestler.mevcut or '-'}", f"FPS: {fps.tik():.0f}", "c kalibre  r sifirla  q cikis"]
            hud.panel(kare, satirlar, baslik="VUCUT POZU")
            if uyari[0] and simdi - uyari[1] < 3.0:
                cv2.rectangle(kare, (0, yukseklik - 70), (genislik, yukseklik), hud.TURUNCU, -1)
                cv2.putText(kare, UYARILAR[uyari[0]], (30, yukseklik - 22), hud.FONT, 1.3, hud.BEYAZ, 3, cv2.LINE_AA)

            tus = app.goster(kare)
            if tus == ord("c"):
                durus.kalibre_et()
            elif tus == ord("r"):
                sayac = TekrarSayaci(egzersiz["asagi"], egzersiz["yukari"])


if __name__ == "__main__":
    main()
