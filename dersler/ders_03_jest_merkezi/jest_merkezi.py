"""
Ders 3 - Jest Merkezi ve Olay Yolu (JARVIS'in sinir sistemi)

İki eli aynı anda izler, statik jestleri (yumruk, avuç, zafer, L, rock, başparmak yukarı)
ve dinamik jestleri (sağa/sola kaydırma) tanır. Tanınan her şeyi OlayYolu'na yayınlar.

Bu dersin asıl fikri: Görüntü kodu "ne yapılacağını" bilmez, sadece "ne olduğunu" söyler.
Olaylar olaylar.jsonl dosyasına da yazılır. İleride JARVIS (yapay zeka) bu dosyayı ya da
OlayYolu'nu dinleyerek "Efendim, başparmağınızı kaldırdınız." diyebilecek.

Çalıştırma (depo kökünden):
    python dersler/ders_03_jest_merkezi/jest_merkezi.py
"""

import argparse
import os
import time

import cv2

from jarvis_vision import hud
from jarvis_vision import jestler as j
from jarvis_vision.el import ElTakipci
from jarvis_vision.kamera import Kamera
from jarvis_vision.olaylar import JsonlKaydedici, OlayYolu

KAYIT_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "olaylar.jsonl")


class ElDurumu:
    """Her el (sağ/sol) için ayrı kararlılaştırıcı ve kaydırma algılayıcı tutulur."""

    def __init__(self):
        self.jest = j.JestKararlilastirici(sure=0.3)
        self.kaydirma = j.KaydirmaAlgilayici()
        self.goruluyor = False


def konsola_yaz(olay):
    print(f"[{time.strftime('%H:%M:%S')}] {olay.ad:<16} {olay.veri}")


def main():
    ayrac = argparse.ArgumentParser(description="JARVIS - Jest Merkezi")
    ayrac.add_argument("--kamera", type=int, default=0)
    args = ayrac.parse_args()

    yol = OlayYolu()
    kaydedici = JsonlKaydedici(KAYIT_DOSYASI)
    yol.abone_ol(OlayYolu.HEPSI, konsola_yaz)
    yol.abone_ol(OlayYolu.HEPSI, kaydedici)

    durumlar = {"sag": ElDurumu(), "sol": ElDurumu()}
    son_olay = "-"
    fps = hud.FpsSayaci()

    with Kamera(args.kamera) as kamera, ElTakipci(max_el=2) as takipci:
        while True:
            kare = kamera.oku()
            if kare is None:
                break
            simdi = time.monotonic()
            eller = {e.taraf: e for e in takipci.isle(kare)}

            for taraf, durum in durumlar.items():
                el = eller.get(taraf)
                if el is None:
                    if durum.goruluyor:
                        durum.goruluyor = False
                        durum.jest.sifirla()
                        durum.kaydirma.sifirla()
                        son_olay = yol.yayinla("el.kayboldu", el=taraf).ad
                    continue

                n = el.noktalar
                if not durum.goruluyor:
                    durum.goruluyor = True
                    son_olay = yol.yayinla("el.goruldu", el=taraf).ad

                parmaklar = j.parmak_durumlari(n)
                yeni_jest = durum.jest.guncelle(j.jest_tani(n), simdi)
                if yeni_jest is not None:
                    yol.yayinla("jest.degisti", el=taraf, jest=yeni_jest.value, parmak_sayisi=sum(parmaklar))
                    son_olay = f"{taraf}: {yeni_jest.value}"

                # Kaydırma sadece açık avuçla yapılır; böylece fare hareketi kaydırma sanılmaz
                if durum.jest.mevcut == j.Jest.AVUC:
                    yon = durum.kaydirma.guncelle(n[j.ORTA_KOK], j.el_boyutu(n), simdi)
                    if yon:
                        yol.yayinla("jest.kaydirma", el=taraf, yon=yon)
                        son_olay = f"{taraf}: kaydirma {yon}"
                else:
                    durum.kaydirma.sifirla()

                # Görselleştirme: iskelet, açık parmak uçları ve elin üstünde jest adı
                hud.iskelet_ciz(kare, n, hud.CAMGOBEGI if taraf == "sag" else hud.TURUNCU)
                for acik, uc in zip(parmaklar, (j.BAS_UCU, j.ISARET_UCU, j.ORTA_UCU, j.YUZUK_UCU, j.SERCE_UCU)):
                    if acik:
                        cv2.circle(kare, tuple(int(v) for v in n[uc, :2]), 9, hud.YESIL, 2, cv2.LINE_AA)
                x, y = int(n[:, 0].min()), int(n[:, 1].min()) - 15
                etiket = f"{taraf.upper()} | {durum.jest.mevcut.value} | {sum(parmaklar)} parmak"
                cv2.putText(kare, etiket, (x, max(y, 20)), hud.FONT, 0.6, hud.BEYAZ, 2, cv2.LINE_AA)

            hud.panel(
                kare,
                [
                    f"SAG EL: {durumlar['sag'].jest.mevcut.value if 'sag' in eller else '-'}",
                    f"SOL EL: {durumlar['sol'].jest.mevcut.value if 'sol' in eller else '-'}",
                    (f"SON OLAY: {son_olay}", hud.YESIL),
                    f"FPS: {fps.tik():.0f}",
                    "Cikis: q",
                ],
                baslik="J.A.R.V.I.S. // JEST MERKEZI",
            )
            cv2.imshow("JARVIS - Jest Merkezi", kare)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    kaydedici.kapat()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
