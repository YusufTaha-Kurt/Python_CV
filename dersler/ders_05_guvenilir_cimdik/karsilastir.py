"""
Ders 5 - V2 ile V3 çimdik algılayıcısını bir video üzerinde karşılaştırır.

Kendine ait bir video kaydet (bilinçli olarak çimdik YAPMADIĞIN, yumruk yaptığın, yüzüne
dokunduğun, ellerini kenetlediğin bir video), sonra iki algılayıcının kaç tık ürettiğine bak.
Böyle bir videoda her tık bir yanlış alarmdır.

    python dersler/ders_05_guvenilir_cimdik/karsilastir.py --kaynak kayit.mp4
"""

from goru import jestler as j
from goru.cimdik import GuvenilirCimdik
from goru.el import ElTakipci
from goru.fare import SahteFare, TiklamaMakinesi
from goru.uygulama import Uygulama, arguman_ayraci


class V2Cimdik:
    """Ders 2'deki algılayıcı: sadece parmak uçları arası mesafe + histerezis."""

    def __init__(self):
        self.ic = j.CimdikAlgilayici(baslama=0.25, birakma=0.38)

    def guncelle(self, noktalar, zaman):
        """GuvenilirCimdik ile aynı arayüz: "basladi" / "bitti" / None döndürür."""
        return self.ic.guncelle(j.cimdik_orani(noktalar))


def main():
    """Aynı video üzerinde eski (V2) ve yeni (V3) çimdik algılayıcıyı yarıştırır; kaç sahte tık ürettiklerini sayar.

    Gerçek bir kayıtla çalıştır: python karsilastir.py --kaynak kayit.mp4
    """
    ayrac = arguman_ayraci("V2 / V3 çimdik karşılaştırması")
    args = ayrac.parse_args()
    args.pencere_yok = True

    sonuclar = {"V2": {}, "V3": {}}
    app = Uygulama(args, "karsilastir")
    with ElTakipci() as takipci:
        for kare, simdi in app.kareler():
            for el in takipci.isle(kare, simdi):
                for surum, sinif in (("V2", V2Cimdik), ("V3", GuvenilirCimdik)):
                    if el.taraf not in sonuclar[surum]:
                        sonuclar[surum][el.taraf] = (sinif(), TiklamaMakinesi(SahteFare(), 40), [0])
                    cimdik, makine, baslangic = sonuclar[surum][el.taraf]
                    olay = cimdik.guncelle(el.noktalar, simdi)
                    baslangic[0] += olay == "basladi"
                    kavrayabilir = getattr(cimdik, "kavrayabilir", True)
                    makine.guncelle(olay, kavrayabilir, tuple(el.noktalar[j.ISARET_KOK, :2]), simdi)

    print(f"{app.kare_no} kare işlendi.")
    for surum, eller in sonuclar.items():
        baslangic = sum(b[0] for _, _, b in eller.values())
        eylemler = [e for _, makine, _ in eller.values() for e in makine.fare.eylemler]
        print(
            f"{surum}: {baslangic} çimdik başlangıcı -> {eylemler.count('tikla')} tık, "
            f"{eylemler.count('bas')} basılı tutma"
        )


if __name__ == "__main__":
    main()
