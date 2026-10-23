"""
Ders 4 - Medya ve Ses Kontrolü (OlayYolu'na ilk "yetenekleri" bağlamak)

Jest sözlüğü:
    L işareti (başparmak + işaret açık)  -> SES MODU: iki parmak arası mesafe = ses seviyesi
    Avuç aç                              -> ses modundan çık (seviye olduğu yerde kalır)
    Avuçla sağa / sola kaydır            -> sonraki / önceki parça
    Başparmak yukarı                     -> oynat / duraklat
    Rock (işaret + serçe)                -> sesi kapat / aç

Ders 3'ten farkı: Görüntü döngüsü yine sadece olay yayınlar. Medya işlemleri
OlayYolu'na abone olan ayrı fonksiyonlardır (Yetenekler sınıfı). JARVIS'e ileride
yeni bir yetenek eklemek, yeni bir abone yazmak kadar kolay olacak.

Çalıştırma (depo kökünden):
    python dersler/ders_04_medya_kontrol/medya_kontrol.py
"""

import argparse
import time

import cv2
import numpy as np

from jarvis_vision import hud
from jarvis_vision import jestler as j
from jarvis_vision.el import ElTakipci
from jarvis_vision.filtreler import OneEuroFiltre
from jarvis_vision.kamera import Kamera
from jarvis_vision.olaylar import OlayYolu
from jarvis_vision.ses import SesKontrol, medya_tusu

# Başparmak-işaret mesafesinin (el boyutuna oranla) ses seviyesine eşlendiği aralık
SES_MIN_ORAN, SES_MAX_ORAN = 0.25, 1.1


class Yetenekler:
    """OlayYolu'ndan gelen olayları gerçek eylemlere çeviren aboneler."""

    def __init__(self, ses, sadece_izle):
        self.ses = ses
        self.sadece_izle = sadece_izle
        self.ses_modu = False
        self.son_eylem = "-"

    def jest_degisti(self, olay):
        jest = olay.veri["jest"]
        if jest == j.Jest.L_ISARETI.value:
            self.ses_modu = True
            self._eylem("ses modu")
        elif jest == j.Jest.BASPARMAK_YUKARI.value:
            self._eylem("oynat/duraklat", lambda: medya_tusu("playpause"))
        elif jest == j.Jest.ROCK.value:
            self._eylem("sessiz ac/kapa", self.ses.sessiz_degistir)

    def kaydirma(self, olay):
        if olay.veri["yon"] == "sag":
            self._eylem("sonraki parca", lambda: medya_tusu("nexttrack"))
        else:
            self._eylem("onceki parca", lambda: medya_tusu("prevtrack"))

    def _eylem(self, ad, fonksiyon=None):
        self.son_eylem = ad
        print(f"[JARVIS] {ad}")
        if fonksiyon and not self.sadece_izle:
            fonksiyon()


def main():
    ayrac = argparse.ArgumentParser(description="JARVIS - Medya ve Ses Kontrolü")
    ayrac.add_argument("--kamera", type=int, default=0)
    ayrac.add_argument("--el", choices=["sag", "sol"], default="sag")
    ayrac.add_argument("--sadece-izle", action="store_true", help="Ses ve medya tuşlarına dokunma")
    args = ayrac.parse_args()

    ses = SesKontrol()
    yetenekler = Yetenekler(ses, args.sadece_izle)
    yol = OlayYolu()
    yol.abone_ol("jest.degisti", yetenekler.jest_degisti)
    yol.abone_ol("jest.kaydirma", yetenekler.kaydirma)

    jest_takip = j.JestKararlilastirici(sure=0.35)
    kaydirma = j.KaydirmaAlgilayici()
    ses_filtresi = OneEuroFiltre(min_kesim=0.8, beta=2.0)
    hedef_seviye = ses.seviye()
    fps = hud.FpsSayaci()

    with Kamera(args.kamera) as kamera, ElTakipci() as takipci:
        while True:
            kare = kamera.oku()
            if kare is None:
                break
            simdi = time.monotonic()
            el = next((e for e in takipci.isle(kare) if e.taraf == args.el), None)

            if el is None:
                yetenekler.ses_modu = False
                jest_takip.sifirla()
                kaydirma.sifirla()
                ses_filtresi.sifirla()
            else:
                n = el.noktalar
                hud.iskelet_ciz(kare, n)
                yeni_jest = jest_takip.guncelle(j.jest_tani(n), simdi)
                if yeni_jest is not None:
                    yol.yayinla("jest.degisti", el=args.el, jest=yeni_jest.value)

                if jest_takip.mevcut == j.Jest.AVUC:
                    yon = kaydirma.guncelle(n[j.ORTA_KOK], j.el_boyutu(n), simdi)
                    if yon:
                        yol.yayinla("jest.kaydirma", el=args.el, yon=yon)
                else:
                    kaydirma.sifirla()

                # --- SES MODU ---
                # Orta, yüzük veya serçe açılırsa moddan çık. İşaret parmağının durumuna bakılmaz:
                # başparmağa yaklaşırken bükülür ve "kapalı" görünebilir.
                _, _, orta, yuzuk, serce = j.parmak_durumlari(n)
                if yetenekler.ses_modu and (orta or yuzuk or serce):
                    yetenekler.ses_modu = False
                    ses_filtresi.sifirla()

                if yetenekler.ses_modu:
                    oran = j.cimdik_orani(n, j.BAS_UCU, j.ISARET_UCU)
                    ham_seviye = np.clip((oran - SES_MIN_ORAN) / (SES_MAX_ORAN - SES_MIN_ORAN), 0, 1)
                    yeni_seviye = float(ses_filtresi(ham_seviye, simdi))
                    # Her karede ses API'sini çağırmamak için %1'lik değişimleri bekle
                    if abs(yeni_seviye - hedef_seviye) > 0.01:
                        hedef_seviye = yeni_seviye
                        if not args.sadece_izle:
                            ses.seviye_ayarla(hedef_seviye)

                    p1 = tuple(int(v) for v in n[j.BAS_UCU, :2])
                    p2 = tuple(int(v) for v in n[j.ISARET_UCU, :2])
                    cv2.line(kare, p1, p2, hud.CAMGOBEGI, 3, cv2.LINE_AA)
                    orta_nokta = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
                    hud.reaktor_halkasi(kare, orta_nokta, hedef_seviye, yaricap=34)

            genislik = kare.shape[1]
            seviye = hedef_seviye if (yetenekler.ses_modu or not ses.destekleniyor) else ses.seviye()
            hud.cubuk(kare, (genislik - 70, 120), (35, 250), seviye, f"%{int(seviye * 100)}")
            hud.panel(
                kare,
                [
                    ("MOD: SES" if yetenekler.ses_modu else "MOD: JEST", hud.YESIL),
                    f"JEST: {jest_takip.mevcut.value}",
                    (f"EYLEM: {yetenekler.son_eylem}", hud.TURUNCU),
                    f"SES API: {'pycaw' if ses.destekleniyor else 'yok (medya tuslari)'}",
                    f"FPS: {fps.tik():.0f}",
                    "SADECE IZLEME" if args.sadece_izle else "Cikis: q",
                ],
                baslik="J.A.R.V.I.S. // MEDYA",
            )
            cv2.imshow("JARVIS - Medya Kontrolu", kare)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
