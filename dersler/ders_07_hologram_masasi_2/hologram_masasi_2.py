"""
Ders 7 - Hologram Masası II

Ders 6'nın üstüne:
    Pençe ile uzaktan çekme   Avucunu aç, sonra pençe yap (işaret, orta, yüzük kanca gibi
                              kıvrık, serçe düz, başparmakla arası geniş). Pençenin ağzıyla
                              uzaktaki bir nesneye nişan al. Nesne titremeye başlar; 2 saniye
                              sonra pençeyi hızla kapat: nesne eline uçar. Avucunu açınca bırakır.
    Alkış                     İki avuç dik, birbirine hızla yaklaşırsa masa toparlanır.
    İki 3D model              Reaktör ve küp (dokun: patlat / topla, tutup bekle: döndür)
    Piramit modu              --piramit ya da tarayıcıda p tuşu: Pepper's ghost hologramı için
                              sahneyi dört yöne çizer (ekranın ortasına ters plastik piramit koy).

Çalıştırma (depo kökünden):
    python dersler/ders_07_hologram_masasi_2/hologram_masasi_2.py
    python dersler/ders_07_hologram_masasi_2/hologram_masasi_2.py --piramit
"""

import os

from goru.cimdik import CimdikAyarlari
from goru.hologram import Masa
from goru.hologram_uygulama import argumanlar_ekle, calistir, icerik_yukle
from goru.olaylar import OlayYolu
from goru.uygulama import arguman_ayraci

KLASOR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(KLASOR))


def main():
    ayrac = argumanlar_ekle(arguman_ayraci("Hologram Masası II"))
    ayrac.add_argument("--piramit", action="store_true", help="Pepper's ghost piramit görünümüyle aç")
    args = ayrac.parse_args()

    yol = OlayYolu()
    yol.abone_ol(OlayYolu.HEPSI, lambda olay: print(f"[HOLOGRAM] {olay.ad} {olay.veri.get('etiket', '')}"))
    masa = Masa(
        ayarlar=CimdikAyarlari.yukle(os.path.join(KOK, "ayarlar", "cimdik.json")), pence=True, alkis=True, yol=yol
    )
    icerik = os.path.join(KLASOR, "icerik")
    icerik_yukle(masa, icerik)
    masa.model_ekle("reaktor", x=masa.w * 0.18, y=masa.h * 0.7)
    masa.model_ekle("kup", x=masa.w * 0.82, y=masa.h * 0.7, boyut=0.13)
    calistir(args, masa, "HOLOGRAM MASASI II", icerik_klasoru=icerik, piramit=args.piramit)


if __name__ == "__main__":
    main()
