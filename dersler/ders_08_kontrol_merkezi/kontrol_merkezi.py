"""
Ders 8 - Kontrol Merkezi

Önceki derslerin yetenekleri tek uygulamada, modlar halinde:

    Mod 1  FARE      Ders 5: OK çimdiği tık / sürükle, başparmak + orta sağ tık
    Mod 2  MEDYA     Ders 4: L işareti ses, başparmak yukarı oynat, avuçla parça değiştir
    Mod 3  PENCERE   Zafer + yukarı / aşağı kaydır, avuçla sanal masaüstü değiştir,
                     başparmak yukarı büyüt, rock küçült, L işareti Alt+Tab

Mod seçimi: Diğer elinle (varsayılan sol) 1, 2 ya da 3 parmak göster ve 0.6 sn tut.
            Ya da pencerede 1 / 2 / 3 tuşları.
Her modda: Kontrol elinle yumruk (0.5 sn) uyku modunu açar / kapatır.

Çalıştırma (depo kökünden):
    python dersler/ders_08_kontrol_merkezi/kontrol_merkezi.py
    python dersler/ders_08_kontrol_merkezi/kontrol_merkezi.py --sadece-izle
"""

import os

import cv2

from goru import hud
from goru import jestler as j
from goru.cimdik import CimdikAyarlari
from goru.el import ElTakipci
from goru.fare import ElFaresi, PyAutoGuiFare, SahteFare
from goru.imlec import ImlecSurucu
from goru.kisayollar import PencereKontrol, PyAutoGuiKlavye, SahteKlavye
from goru.medya import MedyaKontrol
from goru.modlar import ModSecici
from goru.olaylar import OlayYolu
from goru.uygulama import Uygulama, arguman_ayraci

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODLAR = ["FARE", "MEDYA", "PENCERE"]


def mod_sekmeleri(kare, secili, uyku):
    x = kare.shape[1] - 3 * 130 - 15
    for i, mod in enumerate(MODLAR):
        renk = hud.TURUNCU if uyku else (hud.YESIL if mod == secili else (110, 110, 110))
        cv2.rectangle(kare, (x + i * 130, 15), (x + i * 130 + 120, 55), renk, -1 if mod == secili else 2)
        cv2.putText(kare, f"{i + 1} {mod}", (x + i * 130 + 10, 43), hud.FONT, 0.6,
                    (20, 20, 20) if mod == secili else renk, 2, cv2.LINE_AA)


def main():
    ayrac = arguman_ayraci("Kontrol Merkezi")
    ayrac.add_argument("--el", choices=["sag", "sol"], default="sag", help="Kontrol eli")
    args = ayrac.parse_args()
    mod_eli = "sol" if args.el == "sag" else "sag"

    yol = OlayYolu()

    def konsola_yaz(olay):
        if olay.ad.split(".")[0] in ("medya", "pencere", "mod"):
            print(f"[{olay.ad}] {olay.veri}")

    yol.abone_ol(OlayYolu.HEPSI, konsola_yaz)
    yayinci = j.JestYayincisi(yol)
    surucu = None if args.sadece_izle else ImlecSurucu()
    fare = SahteFare(yazdir=True) if args.sadece_izle else PyAutoGuiFare()
    klavye = SahteKlavye(yazdir=True) if args.sadece_izle else PyAutoGuiKlavye()
    faresi = ElFaresi(fare, CimdikAyarlari.yukle(os.path.join(KOK, "ayarlar", "cimdik.json")), surucu=surucu)
    medya = MedyaKontrol(yol, el=args.el, sadece_izle=args.sadece_izle)
    pencere = PencereKontrol(yol, el=args.el, klavye=klavye, fare=fare)
    secici = ModSecici(MODLAR, yol=yol)
    durum = {"uyku": False}
    fps = hud.FpsSayaci()
    if surucu:
        surucu.baslat()

    def yumruk(olay):
        # Fare modunda çimdik sırasında parmaklar kıvrık olabilir: o an yumruk sayılmaz
        if olay.veri.get("el") == args.el and olay.veri["jest"] == "yumruk" and not faresi.cimdik_aktif:
            durum["uyku"] = not durum["uyku"]
            faresi.sifirla()

    yol.abone_ol("jest.degisti", yumruk)

    app = Uygulama(args, "Kontrol Merkezi")
    with ElTakipci(max_el=2) as takipci:
        for kare, simdi in app.kareler():
            yukseklik, genislik = kare.shape[:2]
            eller = takipci.isle(kare, simdi)
            kontrol = next((e for e in eller if e.taraf == args.el), None)
            secen = next((e for e in eller if e.taraf == mod_eli), None)

            onceki_mod = secici.mod
            secici.guncelle(secen, simdi)
            yayinci.guncelle(eller, simdi)
            if secici.mod != onceki_mod and onceki_mod == "FARE":
                faresi.sifirla()

            uyku = durum["uyku"]
            medya.aktif = secici.mod == "MEDYA" and not uyku
            pencere.aktif = secici.mod == "PENCERE" and not uyku
            if not uyku and secici.mod == "FARE":
                faresi.isle(kontrol, simdi, (genislik, yukseklik))
            medya.isle(kontrol, simdi)
            pencere.isle(kontrol, yayinci.jest(args.el), simdi)

            # --- Görselleştirme ---
            for el in eller:
                hud.iskelet_ciz(kare, el.noktalar, hud.CAMGOBEGI if el.taraf == args.el else hud.TURUNCU)
            if kontrol is not None and secici.mod == "FARE" and faresi.sol.nokta is not None and not uyku:
                hud.reaktor_halkasi(kare, faresi.sol.nokta, 1 - faresi.sol.olcum["oran"],
                                    renk=hud.YESIL if faresi.sol.kavrayabilir else hud.CAMGOBEGI)
            if medya.ses_modu:
                hud.cubuk(kare, (genislik - 70, 120), (35, 250), medya.seviye, f"%{int(medya.seviye * 100)}")
            mod_sekmeleri(kare, secici.mod, uyku)
            son_eylem = {"FARE": faresi.makine.durum, "MEDYA": medya.son_eylem, "PENCERE": pencere.son_eylem}
            hud.panel(
                kare,
                [
                    ("UYKU (uyanmak icin yumruk)" if uyku else f"MOD: {secici.mod}", hud.TURUNCU if uyku else hud.YESIL),
                    f"KONTROL ELI: {args.el.upper()} {'(goruldu)' if kontrol else '(yok)'}",
                    f"JEST: {yayinci.jest(args.el).value}",
                    (f"SON: {son_eylem[secici.mod]}" + ("  [KAYDIRIYOR]" if pencere.kaydiriyor else ""), hud.TURUNCU),
                    f"FPS: {fps.tik():.0f}",
                    f"mod: {mod_eli} elle 1/2/3 parmak ya da 1/2/3 tusu",
                ],
                baslik="KONTROL MERKEZI",
            )
            tus = app.goster(kare)
            if tus in (ord("1"), ord("2"), ord("3")):
                if secici.mod == "FARE":
                    faresi.sifirla()
                secici.sec(MODLAR[tus - ord("1")])

    faresi.sifirla()
    if surucu:
        surucu.durdur()


if __name__ == "__main__":
    main()
