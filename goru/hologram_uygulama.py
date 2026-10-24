"""Hologram masası çalıştırıcısı (Ders 6 ve 7 ortak).

Kamera -> el takibi -> Masa (Python) -> CanliYayin -> tarayıcı (three.js)
"""

import os
import webbrowser

import cv2

from . import hud
from .el import ElTakipci
from .uygulama import Uygulama
from .web import CanliYayin

WEB_KLASORU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hologram_web")
GORSEL_UZANTILARI = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def argumanlar_ekle(ayrac):
    ayrac.add_argument("--port", type=int, default=8765, help="Yerel sunucu portu (0: boş bir port seç)")
    ayrac.add_argument("--tarayici-acma", action="store_true", help="Tarayıcıyı otomatik açma")
    return ayrac


def icerik_yukle(masa, klasor):
    """Klasördeki .md dosyalarını kart, görselleri görsel kartı olarak masaya koyar.

    Görseller sadece bu klasörden yüklenebilir (tarayıcı /icerik/... adresinden ister).
    """
    if not klasor or not os.path.isdir(klasor):
        return
    masa.notlari_yukle(klasor)
    for ad in sorted(os.listdir(klasor)):
        if ad.lower().endswith(GORSEL_UZANTILARI):
            masa.gorsel_ekle(f"/icerik/{ad}", baslik=os.path.splitext(ad)[0])


def calistir(args, masa, baslik, icerik_klasoru=None, piramit=False):
    ek = {"icerik": icerik_klasoru} if icerik_klasoru else {}
    yayin = CanliYayin(WEB_KLASORU, port=args.port, ek_klasorler=ek, izinli_komutlar={"kart_ekle", "toparla"})
    url = yayin.baslat() + ("?piramit=1" if piramit else "")
    print(f"Hologram masası: {url}  (kapatmak için önizleme penceresinde q ya da Ctrl+C)")
    if not args.tarayici_acma:
        webbrowser.open(url)

    fps = hud.FpsSayaci()
    app = Uygulama(args, baslik)
    try:
        with ElTakipci() as takipci:
            for kare, simdi in app.kareler():
                yukseklik, genislik = kare.shape[:2]
                masa.boyutla(genislik, yukseklik)
                eller = takipci.isle(kare, simdi)
                masa.guncelle(eller, simdi)
                for komut in yayin.komutlari_al():
                    masa.komut(komut)
                yayin.kare_yayinla(kare)
                durum = masa.durum()
                durum["fps"] = round(fps.tik())
                yayin.durum_yayinla(durum)

                if not args.pencere_yok:
                    onizleme = cv2.resize(kare, (640, int(640 * yukseklik / genislik)))
                    oran = 640 / genislik
                    for el in eller:
                        hud.iskelet_ciz(onizleme, el.noktalar * oran)
                    hud.panel(onizleme, [f"Tarayici: {url}", f"FPS: {durum['fps']}", "q: cikis"], baslik=baslik)
                    app.goster(onizleme)
    except KeyboardInterrupt:
        pass
    finally:
        yayin.durdur()
