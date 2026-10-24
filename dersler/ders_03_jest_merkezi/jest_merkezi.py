"""
Ders 3 - Jest Merkezi ve Olay Yolu

İki eli aynı anda izler, statik jestleri (yumruk, avuç, zafer, L, rock, başparmak yukarı)
ve dinamik jestleri (sağa/sola kaydırma) tanır. Tanınan her şeyi OlayYolu'na yayınlar
(goru.jestler.JestYayincisi).

Bu dersin asıl fikri: Görüntü kodu "ne yapılacağını" bilmez, sadece "ne olduğunu" söyler.
Olaylar olaylar.jsonl dosyasına da yazılır. Bu paketi kullanan başka bir uygulama bu
dosyayı ya da OlayYolu'nu dinleyerek jestlere tepki verebilir.

Çalıştırma (depo kökünden):
    python dersler/ders_03_jest_merkezi/jest_merkezi.py
"""

import os
import time

import cv2

from goru import hud
from goru import jestler as j
from goru.el import ElTakipci
from goru.olaylar import JsonlKaydedici, OlayYolu
from goru.uygulama import Uygulama, arguman_ayraci

KAYIT_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "olaylar.jsonl")
PARMAK_UCLARI = (j.BAS_UCU, j.ISARET_UCU, j.ORTA_UCU, j.YUZUK_UCU, j.SERCE_UCU)


def main():
    """Ders akışı: el bul → JestYayincisi jestleri olay yoluna yayınlar → aboneler olayı yazdırır / dosyaya kaydeder.

    Bu derste jestlere tepki veren hiçbir "eylem" yoktur; amaç mimariyi göstermek:
    görüntü kodu sadece ne olduğunu söyler, kimin ne yapacağını abone olanlar belirler.
    """
    args = arguman_ayraci("Jest Merkezi").parse_args()

    # Olay yolu: her şey buradan geçer. İki abone: konsol ve JSONL dosyası ("*" = tüm olaylar).
    yol = OlayYolu()
    kaydedici = JsonlKaydedici(KAYIT_DOSYASI)
    son_olay = ["-"]

    def konsola_yaz(olay):
        """Her olayı saat damgasıyla konsola yazar, ekran panelindeki "son olay" için saklar."""
        print(f"[{time.strftime('%H:%M:%S')}] {olay.ad:<16} {olay.veri}")
        son_olay[0] = f"{olay.ad} {olay.veri.get('jest') or olay.veri.get('yon') or ''}"

    yol.abone_ol(OlayYolu.HEPSI, konsola_yaz)
    yol.abone_ol(OlayYolu.HEPSI, kaydedici)
    yayinci = j.JestYayincisi(yol)
    fps = hud.FpsSayaci()

    app = Uygulama(args, "Jest Merkezi")
    with ElTakipci(max_el=2) as takipci:
        for kare, simdi in app.kareler():
            eller = takipci.isle(kare, simdi)  # 1) elleri bul
            yayinci.guncelle(eller, simdi)  # 2) jestleri tanı, değişince olay yayınla

            # 3) Görselleştirme: iskelet, açık parmak uçları ve elin üstünde jest adı
            for el in eller:
                n = el.noktalar
                parmaklar = j.parmak_durumlari(n)
                hud.iskelet_ciz(kare, n, hud.CAMGOBEGI if el.taraf == "sag" else hud.TURUNCU)
                for acik, uc in zip(parmaklar, PARMAK_UCLARI):
                    if acik:
                        cv2.circle(kare, tuple(int(v) for v in n[uc, :2]), 9, hud.YESIL, 2, cv2.LINE_AA)
                x, y = int(n[:, 0].min()), int(n[:, 1].min()) - 15
                etiket = f"{el.taraf.upper()} | {yayinci.jest(el.taraf).value} | {sum(parmaklar)} parmak"
                cv2.putText(kare, etiket, (x, max(y, 20)), hud.FONT, 0.6, hud.BEYAZ, 2, cv2.LINE_AA)

            hud.panel(
                kare,
                [
                    f"SAG EL: {yayinci.jest('sag').value}",
                    f"SOL EL: {yayinci.jest('sol').value}",
                    (f"SON OLAY: {son_olay[0]}", hud.YESIL),
                    f"FPS: {fps.tik():.0f}",
                    "Cikis: q",
                ],
                baslik="JEST MERKEZI",
            )
            app.goster(kare)

    kaydedici.kapat()


if __name__ == "__main__":
    main()
