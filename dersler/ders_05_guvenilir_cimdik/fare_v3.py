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

from goru import hud
from goru import jestler as j
from goru.cimdik import CimdikAyarlari
from goru.el import ElTakipci
from goru.fare import ElFaresi, PyAutoGuiFare, SahteFare
from goru.imlec import ImlecSurucu
from goru.ornekleyici import Ornekleyici, cimdik_ayari_oner
from goru.uygulama import Uygulama, arguman_ayraci

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VARSAYILAN_AYARLAR = os.path.join(KOK, "ayarlar", "cimdik.json")


def olcum_yaz(kare, cimdik, konum):
    x, y = int(konum[0]) + 40, int(konum[1]) - 60
    satirlar = [f"{ad}: {deger:.2f}" for ad, deger in cimdik.olcum.items()]
    satirlar += [f"hiz: {cimdik.hiz:.1f} el/sn", f"imza: {'EVET' if cimdik.imza else 'hayir'}"]
    for i, satir in enumerate(satirlar):
        cv2.putText(kare, satir, (x, y + 20 * i), hud.FONT, 0.5, hud.BEYAZ, 1, cv2.LINE_AA)


def cimdik_ciz(kare, cimdik, renk, hata_ayiklama):
    if cimdik.nokta is None:
        return
    dolum = 1 - (cimdik.olcum["oran"] - cimdik.ayar.baslama) / (1.0 - cimdik.ayar.baslama)
    halka = hud.YESIL if cimdik.kavrayabilir else (hud.TURUNCU if cimdik.hayalet else renk)
    hud.reaktor_halkasi(kare, cimdik.nokta, dolum, renk=halka)
    # İmza göstergesi: yeşil = OK işareti görülüyor, kırmızı = görülmüyor
    nokta = tuple(int(v) for v in cimdik.nokta)
    cv2.circle(kare, nokta, 5, hud.YESIL if cimdik.imza else hud.KIRMIZI, -1, cv2.LINE_AA)
    if hata_ayiklama:
        olcum_yaz(kare, cimdik, cimdik.nokta)


def main():
    ayrac = arguman_ayraci("Güvenilir Çimdik ve Fare V3")
    ayrac.add_argument("--el", choices=["sag", "sol"], default="sag", help="Fareyi yönetecek el")
    ayrac.add_argument("--imlec", choices=["orta", "kok"], default="orta", help="İmleç noktası")
    ayrac.add_argument("--ayarlar", default=VARSAYILAN_AYARLAR, help="Çimdik eşikleri (JSON)")
    args = ayrac.parse_args()

    ayar = CimdikAyarlari.yukle(args.ayarlar)
    surucu = None if args.sadece_izle else ImlecSurucu()
    fare = SahteFare(yazdir=True) if args.sadece_izle else PyAutoGuiFare()
    faresi = ElFaresi(fare, ayar, surucu=surucu, imlec_noktasi=args.imlec)
    jest_takip = j.JestKararlilastirici(sure=0.5)
    ornekleyici = Ornekleyici(sure=4.0)
    fps = hud.FpsSayaci()
    if surucu:
        surucu.baslat()

    uyku_modu_aktif = False
    hata_ayiklama = False
    mesaj = ""

    app = Uygulama(args, "Fare V3")
    with ElTakipci() as takipci:
        for kare, simdi in app.kareler():
            yukseklik, genislik = kare.shape[:2]
            el = next((e for e in takipci.isle(kare, simdi) if e.taraf == args.el), None)

            if not uyku_modu_aktif:
                faresi.isle(el, simdi, (genislik, yukseklik))
            if el is None:
                jest_takip.sifirla()
            else:
                n = el.noktalar
                # Uyku modu: çimdik sırasında jestlere bakılmaz
                if not faresi.cimdik_aktif and jest_takip.guncelle(j.jest_tani(n), simdi) == j.Jest.YUMRUK:
                    uyku_modu_aktif = not uyku_modu_aktif
                    faresi.sifirla()

                if ornekleyici.kayitta and faresi.sol.olcum and ornekleyici.ekle(faresi.sol.olcum, simdi):
                    etiket = next(reversed(ornekleyici.ornekler))
                    mesaj = f"'{etiket}' orneklendi"
                    print(f"[ORNEKLEYICI] {etiket}: " + ", ".join(
                        f"{ad} {mn:.2f}/{md:.2f}/{mx:.2f}" for ad, (mn, md, mx) in ornekleyici.ozet(etiket).items()
                    ))

                renk = hud.TURUNCU if uyku_modu_aktif else hud.CAMGOBEGI
                hud.iskelet_ciz(kare, n, renk)
                if not uyku_modu_aktif:
                    cimdik_ciz(kare, faresi.sol, renk, hata_ayiklama)

            if faresi.kutu:
                x1, y1, x2, y2 = faresi.kutu
                cv2.rectangle(kare, (x1, y1), (x2, y2), hud.CAMGOBEGI, 1, cv2.LINE_AA)
            if uyku_modu_aktif:
                mod = ("MOD: UYKU (uyanmak icin yumruk)", hud.TURUNCU)
            else:
                mod = (f"MOD: AKTIF  |  TUS: {faresi.makine.durum.upper()}", hud.YESIL)
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
                faresi.ayar_degistir(ayar)
                mesaj = "esikler kaydedildi"
                print("[ORNEKLEYICI] Yeni eşikler:", *rapor, f"-> {args.ayarlar}", sep="\n  ")

    faresi.sifirla()
    if surucu:
        surucu.durdur()


if __name__ == "__main__":
    main()
