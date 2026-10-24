"""
Ders 15 - Nesne Tespiti ve Takibi

EfficientDet-Lite0 (COCO'nun 80 sınıfı: insan, fincan, telefon, kitap, şişe, ...) ile
nesneleri bulur, IoU takipçisiyle her birine kalıcı bir ID verir ve parmağınla işaret
ettiğin nesneyi söyler.

    Bir nesneyi işaret et (sadece işaret parmağı açık)   O nesne vurgulanır ve adı yazılır

Olaylar: nesne.goruldu, nesne.kayboldu, nesne.isaretlendi

Çalıştırma (depo kökünden):
    python dersler/ders_15_nesne_tespiti/nesne_tespiti.py
    python dersler/ders_15_nesne_tespiti/nesne_tespiti.py --siniflar cup,bottle,cell phone,book
"""

import time
from collections import Counter

import cv2

from goru import hud
from goru import jestler as j
from goru.el import ElTakipci
from goru.nesne import TURKCE, NesneDedektoru, isaret_edilen
from goru.olaylar import OlayYolu
from goru.takip import IoUTakipci
from goru.uygulama import Uygulama, arguman_ayraci

PALET = [(255, 200, 0), (80, 220, 80), (0, 165, 255), (230, 120, 255), (0, 220, 255), (255, 120, 120)]


def main():
    """Ders akışı (her karede): nesneleri bul → IoUTakipci kalıcı ID verir (yeni / kaybolan nesneler olay olur)
    → işaret parmağı açıksa gösterdiği nesneyi bul → kutuları ve adları çiz."""
    ayrac = arguman_ayraci("Nesne Tespiti ve Takibi")
    ayrac.add_argument("--siniflar", help="Sadece bu COCO sınıfları (virgülle), örn. cup,bottle,cell phone")
    ayrac.add_argument("--esik", type=float, default=0.4, help="Tespit güven eşiği")
    args = ayrac.parse_args()
    izinli = [s.strip() for s in args.siniflar.split(",")] if args.siniflar else None

    yol = OlayYolu()
    yol.abone_ol(OlayYolu.HEPSI, lambda o: print(f"[{time.strftime('%H:%M:%S')}] {o.ad} {o.veri}"))
    takipci = IoUTakipci()
    isaretli = None
    fps = hud.FpsSayaci()

    app = Uygulama(args, "Nesne Tespiti")
    with NesneDedektoru(skor_esigi=args.esik, izinli=izinli) as dedektor, ElTakipci(max_el=1) as el_takipci:
        for kare, simdi in app.kareler():
            # Dedektör her kareyi bağımsız görür; takipçi aynı nesneye aynı ID'yi verir
            izler = takipci.guncelle(dedektor.isle(kare, simdi))
            for iz in takipci.yeni:
                yol.yayinla("nesne.goruldu", id=iz.id, nesne=TURKCE.get(iz.etiket, iz.etiket))
            for iz in takipci.biten:
                yol.yayinla("nesne.kayboldu", id=iz.id, nesne=TURKCE.get(iz.etiket, iz.etiket))

            # Parmakla işaret: sadece işaret parmağı açıkken
            eller = el_takipci.isle(kare, simdi)
            hedef = None
            if eller and j.jest_tani(eller[0].noktalar) == j.Jest.ISARET:
                n = eller[0].noktalar
                hedef = isaret_edilen(n, {iz.id: iz.kutu for iz in izler})
                kok, uc = n[j.ISARET_KOK, :2], n[j.ISARET_UCU, :2]
                cv2.line(kare, tuple(int(v) for v in uc), tuple(int(v) for v in uc + 4 * (uc - kok)),
                         hud.TURUNCU, 2, cv2.LINE_AA)
            if hedef is not None and hedef != isaretli:
                iz = next(iz for iz in izler if iz.id == hedef)
                yol.yayinla("nesne.isaretlendi", id=iz.id, nesne=TURKCE.get(iz.etiket, iz.etiket))
            isaretli = hedef

            for iz in izler:
                x0, y0, x1, y1 = (int(v) for v in iz.kutu)
                renk = hud.YESIL if iz.id == hedef else PALET[iz.id % len(PALET)]
                cv2.rectangle(kare, (x0, y0), (x1, y1), renk, 4 if iz.id == hedef else 2, cv2.LINE_AA)
                etiket = f"#{iz.id} {TURKCE.get(iz.etiket, iz.etiket)} {iz.skor:.2f}"
                cv2.rectangle(kare, (x0, y0 - 24), (x0 + 11 * len(etiket), y0), renk, -1)
                cv2.putText(kare, etiket, (x0 + 4, y0 - 7), hud.FONT, 0.55, (20, 20, 20), 2, cv2.LINE_AA)
            if hedef is not None:
                iz = next(iz for iz in izler if iz.id == hedef)
                cv2.putText(kare, TURKCE.get(iz.etiket, iz.etiket).upper(), (30, kare.shape[0] - 30), hud.FONT, 1.6,
                            hud.YESIL, 4, cv2.LINE_AA)

            sayim = Counter(TURKCE.get(iz.etiket, iz.etiket) for iz in izler)
            satirlar = [f"{ad}: {adet}" for ad, adet in sayim.most_common(6)] or ["nesne yok"]
            satirlar += [f"FPS: {fps.tik():.0f}", "isaret parmagiyla goster  q: cikis"]
            hud.panel(kare, satirlar, baslik="NESNE TESPITI")
            app.goster(kare)


if __name__ == "__main__":
    main()
