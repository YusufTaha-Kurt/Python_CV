"""
Ders 6 - Hologram Masası I

Kamera görüntüsünün üstünde cam kartlar ve bir 3D model süzülür. Elle:
    OK çimdiği ile tut          Taşı
    Kısa çimdik (dokun)         Kartı aç / kapat, modeli patlat / topla
    Tutup hızla bırak           Fırlat (sürtünmeyle yavaşlar, kenarlardan seker)
    İki elle aynı nesneyi tut   Büyüt / küçült
    Modeli tutup 1 sn bekle     Döndürme modu: elini oynatarak döndür
    Boş çimdikle yana sürükle   Modelin parçalarını aç / kapat

Mimari: El takibi ve tüm etkileşim mantığı Python'da (goru/hologram.py), tarayıcı sadece
çizer (goru/hologram_web/). Video MJPEG, sahne durumu SSE ile yerel sunucudan akar.

Kartlar icerik/ klasöründeki .md dosyalarından gelir; oraya görsel de bırakabilirsin.

Çalıştırma (depo kökünden):
    python dersler/ders_06_hologram_masasi/hologram_masasi.py
"""

import os

from goru.cimdik import CimdikAyarlari
from goru.hologram import Masa
from goru.hologram_uygulama import argumanlar_ekle, calistir, icerik_yukle
from goru.uygulama import arguman_ayraci

KLASOR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(KLASOR))


def main():
    """Masayı kurar: kartlar icerik/ klasöründeki .md dosyalarından gelir, bir 3D reaktör modeli eklenir.
    Asıl döngü goru/hologram_uygulama.py içindeki `calistir`dadır (Ders 7 ile ortak)."""
    args = argumanlar_ekle(arguman_ayraci("Hologram Masası I")).parse_args()
    masa = Masa(ayarlar=CimdikAyarlari.yukle(os.path.join(KOK, "ayarlar", "cimdik.json")))
    icerik = os.path.join(KLASOR, "icerik")
    icerik_yukle(masa, icerik)
    masa.model_ekle("reaktor", x=masa.w * 0.82, y=masa.h * 0.68)
    calistir(args, masa, "HOLOGRAM MASASI I", icerik_klasoru=icerik)


if __name__ == "__main__":
    main()
