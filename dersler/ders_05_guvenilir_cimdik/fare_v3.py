"""
Ders 5 - Güvenilir Çimdik ve Fare V3

Fare V2'nin üstüne:
  * Çimdik artık "OK işareti" ile yapılır: işaret parmağı başparmağa değer, diğer üç parmak
    dışarıda kalır. Yumruk, kenetlenmiş eller ve yüze dokunan el tık üretmez.
  * Yedi katmanlı GuvenilirCimdik (goru/cimdik.py) ve tıklama durum makinesi (goru/fare.py)
  * İmleç başparmak ile işaret ucunun orta noktasından alınır (çimdikte en sabit nokta)
  * Kişiye özel eşik örnekleyici: kendi elinle eşikleri ayarla

Jestler:
    OK çimdiği (kısa)          Sol tık         (iki kez hızlı: çift tık)
    OK çimdiği (basılı tut)    Sol tuş basılı  (elini hareket ettirerek sürükle)
    Başparmak + orta parmak    Sağ tık
    Yumruk (0.5 sn)            Uyku modu aç / kapa

Tuşlar:
    d   Hata ayıklama ekranı (çimdik ölçümleri)
    p   "Doğru çimdik" pozunu 4 sn örnekle (OK çimdiği yap ve bekle)
    y   "Yumruk" pozunu 4 sn örnekle (başparmağın işaretin üstünde yumruk yap)
    k   Örneklerden önerilen eşikleri ayarlar/cimdik.json dosyasına kaydet

Çalıştırma (depo kökünden):
    python dersler/ders_05_guvenilir_cimdik/fare_v3.py
    python dersler/ders_05_guvenilir_cimdik/fare_v3.py --sadece-izle
"""

import os

import cv2
import numpy as np
import pyautogui

from goru import hud
from goru import jestler as j
from goru.cimdik import CimdikAyarlari, GuvenilirCimdik
from goru.el import ElTakipci
from goru.fare import PyAutoGuiFare, SahteFare, TiklamaMakinesi
from goru.filtreler import OneEuroFiltre
from goru.imlec import ImlecSurucu
from goru.ornekleyici import Ornekleyici, cimdik_ayari_oner
from goru.uygulama import Uygulama, arguman_ayraci

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VARSAYILAN_AYARLAR = os.path.join(KOK, "ayarlar", "cimdik.json")

# --- Ayarlar ---
KUTU_ORANI = 0.18  # Sanal çalışma alanının kamera kenarlarına uzaklığı (kare boyutuna oranla)
FILTRE_MIN_KESIM = 0.6  # Düşür -> dururken daha az titreme
FILTRE_BETA = 6.0  # Artır -> hızlı harekette daha az gecikme
SURUKLEME_ESIGI = 0.025  # Çimdikteyken sürüklemenin başlaması için gereken hareket (ekran genişliğine oranla)


def imlec_noktasi(noktalar, tur):
    if tur == "kok":
        return noktalar[j.ISARET_KOK, :2]
    return (noktalar[j.BAS_UCU, :2] + noktalar[j.ISARET_UCU, :2]) / 2


def olcum_yaz(kare, cimdik, konum):
    x, y = int(konum[0]) + 40, int(konum[1]) - 60
    satirlar = [f"{ad}: {deger:.2f}" for ad, deger in cimdik.olcum.items()]
    satirlar += [f"hiz: {cimdik.hiz:.1f} el/sn", f"imza: {'EVET' if cimdik.imza else 'hayir'}"]
    for i, satir in enumerate(satirlar):
        cv2.putText(kare, satir, (x, y + 20 * i), hud.FONT, 0.5, hud.BEYAZ, 1, cv2.LINE_AA)


def main():
    ayrac = arguman_ayraci("Güvenilir Çimdik ve Fare V3")
    ayrac.add_argument("--el", choices=["sag", "sol"], default="sag", help="Fareyi yönetecek el")
    ayrac.add_argument("--imlec", choices=["orta", "kok"], default="orta", help="İmleç noktası")
    ayrac.add_argument("--ayarlar", default=VARSAYILAN_AYARLAR, help="Çimdik eşikleri (JSON)")
    args = ayrac.parse_args()

    ayar = CimdikAyarlari.yukle(args.ayarlar)
    ekran_genisligi, ekran_yuksekligi = pyautogui.size()
    fare = SahteFare(yazdir=True) if args.sadece_izle else PyAutoGuiFare()
    makine = TiklamaMakinesi(fare, SURUKLEME_ESIGI * ekran_genisligi)
    sol_cimdik = GuvenilirCimdik(j.ISARET_UCU, ayar)
    sag_cimdik = GuvenilirCimdik(j.ORTA_UCU, ayar)
    jest_takip = j.JestKararlilastirici(sure=0.5)
    filtre = OneEuroFiltre(min_kesim=FILTRE_MIN_KESIM, beta=FILTRE_BETA)
    ornekleyici = Ornekleyici(sure=4.0)
    fps = hud.FpsSayaci()
    surucu = ImlecSurucu()
    if not args.sadece_izle:
        surucu.baslat()

    uyku_modu_aktif = False
    hata_ayiklama = False
    mesaj = ""

    def sifirla():
        makine.sifirla()
        sol_cimdik.sifirla()
        sag_cimdik.sifirla()
        surucu.dondur(False)

    app = Uygulama(args, "Fare V3")
    with ElTakipci() as takipci:
        for kare, simdi in app.kareler():
            yukseklik, genislik = kare.shape[:2]
            kx1, ky1 = int(genislik * KUTU_ORANI), int(yukseklik * KUTU_ORANI)
            kx2, ky2 = genislik - kx1, yukseklik - ky1
            cv2.rectangle(kare, (kx1, ky1), (kx2, ky2), hud.CAMGOBEGI, 1, cv2.LINE_AA)

            el = next((e for e in takipci.isle(kare, simdi) if e.taraf == args.el), None)
            if el is None:
                sifirla()
                filtre.sifirla()
                jest_takip.sifirla()
            else:
                n = el.noktalar
                olay = sol_cimdik.guncelle(n, simdi)
                sag_olay = sag_cimdik.guncelle(n, simdi)

                # Uyku modu: çimdik sırasında jestlere bakılmaz
                if not sol_cimdik.aktif and not sag_cimdik.aktif:
                    if jest_takip.guncelle(j.jest_tani(n), simdi) == j.Jest.YUMRUK:
                        uyku_modu_aktif = not uyku_modu_aktif
                        sifirla()

                if ornekleyici.kayitta and ornekleyici.ekle(sol_cimdik.olcum, simdi):
                    etiket = next(reversed(ornekleyici.ornekler))
                    mesaj = f"'{etiket}' orneklendi"
                    print(f"[ORNEKLEYICI] {etiket}: " + ", ".join(
                        f"{ad} {mn:.2f}/{md:.2f}/{mx:.2f}" for ad, (mn, md, mx) in ornekleyici.ozet(etiket).items()
                    ))

                if not uyku_modu_aktif:
                    x, y = imlec_noktasi(n, args.imlec)
                    nx = np.clip((x - kx1) / (kx2 - kx1), 0, 1)
                    ny = np.clip((y - ky1) / (ky2 - ky1), 0, 1)
                    fx, fy = filtre((nx, ny), simdi)
                    hedef = (fx * (ekran_genisligi - 1), fy * (ekran_yuksekligi - 1))
                    surucu.dondur(makine.guncelle(olay, sol_cimdik.kavrayabilir, hedef, simdi))
                    surucu.hedef_ayarla(*hedef)
                    if sag_olay == "basladi" and sag_cimdik.kavrayabilir and makine.durum == makine.BOS:
                        fare.sag_tikla()

                # --- Görsel geri bildirim ---
                renk = hud.TURUNCU if uyku_modu_aktif else hud.CAMGOBEGI
                hud.iskelet_ciz(kare, n, renk)
                if sol_cimdik.nokta is not None:
                    oran = sol_cimdik.olcum["oran"]
                    dolum = 1 - (oran - ayar.baslama) / (1.0 - ayar.baslama)
                    halka_rengi = hud.YESIL if sol_cimdik.kavrayabilir else (hud.TURUNCU if sol_cimdik.hayalet else renk)
                    hud.reaktor_halkasi(kare, sol_cimdik.nokta, dolum, renk=halka_rengi)
                    # İmza göstergesi: yeşil = OK işareti görülüyor, kırmızı = görülmüyor
                    nokta = tuple(int(v) for v in sol_cimdik.nokta)
                    cv2.circle(kare, nokta, 5, hud.YESIL if sol_cimdik.imza else hud.KIRMIZI, -1, cv2.LINE_AA)
                    if hata_ayiklama:
                        olcum_yaz(kare, sol_cimdik, sol_cimdik.nokta)

            if uyku_modu_aktif:
                mod = ("MOD: UYKU (uyanmak icin yumruk)", hud.TURUNCU)
            else:
                mod = (f"MOD: AKTIF  |  TUS: {makine.durum.upper()}", hud.YESIL)
            satirlar = [
                mod,
                f"EL: {args.el.upper()} {'(goruldu)' if el else '(yok)'}",
                f"JEST: {jest_takip.mevcut.value}",
                f"FPS: {fps.tik():.0f}",
            ]
            if ornekleyici.kayitta:
                satirlar.append((f"ORNEKLENIYOR '{ornekleyici.etiket}': {ornekleyici.kalan(simdi):.1f} sn", hud.TURUNCU))
            elif mesaj:
                satirlar.append((mesaj, hud.YESIL))
            satirlar.append("d: olcumler  p/y: ornekle  k: kaydet  q: cikis")
            hud.panel(kare, satirlar, baslik="FARE v3 // GUVENILIR CIMDIK")

            tus = app.goster(kare)
            if tus == ord("d"):
                hata_ayiklama = not hata_ayiklama
            elif tus in (ord("p"), ord("y")):
                ornekleyici.baslat("cimdik" if tus == ord("p") else "yumruk", simdi)
            elif tus == ord("k"):
                ayar, rapor = cimdik_ayari_oner(ornekleyici, ayar)
                ayar.kaydet(args.ayarlar)
                sol_cimdik.ayar = sag_cimdik.ayar = ayar
                mesaj = "esikler kaydedildi"
                print("[ORNEKLEYICI] Yeni eşikler:", *rapor, f"-> {args.ayarlar}", sep="\n  ")

    sifirla()
    surucu.durdur()


if __name__ == "__main__":
    main()
