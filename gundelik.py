"""
Gündelik kullanım başlatıcısı.

Derslerden günlük hayatta kullanılanları tek bir arka plan servisinde başlatır ve kontrol
panelini tarayıcıda açar. Ayrıntılar: GUNDELIK.md

    python gundelik.py                  Başlat (konsol açık kalır, Ctrl+C ile kapanır)
    python gundelik.py --sadece-izle    Fareye, klavyeye, sese dokunmadan dene
    python gundelik.py --onizleme       Kamera önizleme penceresi de açılsın
    Gundelik.bat                        Çift tıkla: konsolsuz başlar, panelden kapatılır

Açık yetenekler gundelik_ayarlari.json dosyasından okunur. Servis zaten çalışıyorsa ikinci
kopya açılmaz, yalnız panel açılır (kamerayı iki program aynı anda kullanamaz).
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
import webbrowser
from logging.handlers import RotatingFileHandler

KOK = os.path.dirname(os.path.abspath(__file__))
AYAR_DOSYASI = os.path.join(KOK, "gundelik_ayarlari.json")


def konsolsuz_ciktiyi_yonlendir(klasor):
    """pythonw ile konsolsuz çalışırken çıktı bir dosyaya gitsin (hata olursa okunabilsin)."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    os.makedirs(klasor, exist_ok=True)
    dosya = open(os.path.join(klasor, "gundelik_konsol.txt"), "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = dosya
    try:  # MediaPipe gibi C kütüphanelerinin doğrudan yazdıkları da aynı dosyaya
        os.dup2(dosya.fileno(), 1)
        os.dup2(dosya.fileno(), 2)
    except OSError:
        pass


def mesaj_kutusu(metin):
    """Konsolsuz çalışırken hatayı kullanıcıya göstermenin tek yolu (Windows)."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, metin, "Python CV Gündelik", 0x10)


def zaten_calisiyor(port):
    """Bu portta çalışan bir servis var mı? (Kontrol panelinin durum adresine sorar.)"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/durum.json", timeout=0.5) as yanit:
            return "yetenekler" in json.loads(yanit.read())
    except Exception:
        return False


def main():
    ayrac = argparse.ArgumentParser(description="Python CV gündelik kullanım")
    ayrac.add_argument("--ayarlar", default=AYAR_DOSYASI, help="Ayar dosyası")
    ayrac.add_argument("--sadece-izle", action="store_true", help="Fareye, klavyeye ve sese dokunma")
    ayrac.add_argument("--onizleme", action="store_true", help="Kamera önizleme penceresi aç")
    ayrac.add_argument("--panel-acma", action="store_true", help="Kontrol panelini tarayıcıda açma")
    ayrac.add_argument("--kaynak", help="Kamera indeksi ya da video dosyası (varsayılan: ayar dosyasındaki)")
    ayrac.add_argument("--port", type=int, help="Panel portu (varsayılan: ayar dosyasındaki, 8770)")
    args = ayrac.parse_args()

    sys.path.insert(0, KOK)
    from goru.olaylar import OlayYolu
    from goru.servis import Servis, ayarlari_yukle

    ayarlar = ayarlari_yukle(args.ayarlar)
    ayarlar["sadece_izle"] = args.sadece_izle or ayarlar.get("sadece_izle", False)
    ayarlar["onizleme"] = args.onizleme
    if args.kaynak is not None:
        ayarlar["kaynak"] = int(args.kaynak) if args.kaynak.isdigit() else args.kaynak
    if args.port is not None:
        ayarlar["http"]["port"] = args.port
    konsolsuz_ciktiyi_yonlendir(ayarlar["kayit_klasoru"])

    port = ayarlar["http"]["port"]
    panel = f"http://127.0.0.1:{port}/"
    if zaten_calisiyor(port):
        print(f"Servis zaten çalışıyor, panel açılıyor: {panel}")
        if not args.panel_acma:
            webbrowser.open(panel)
        return

    os.makedirs(ayarlar["kayit_klasoru"], exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(os.path.join(ayarlar["kayit_klasoru"], "servis.log"), maxBytes=1_000_000,
                                backupCount=3, encoding="utf-8"),
        ],
    )

    acik = [ad for ad, ayar in ayarlar["yetenekler"].items() if ayar.get("acik")]
    print(f"Gündelik kullanım başlıyor: {', '.join(acik)}")
    print("Kamera ve modeller hazırlanıyor...")
    servis = Servis(ayarlar)
    servis.yol.abone_ol(OlayYolu.HEPSI, lambda o: print(f"[{time.strftime('%H:%M:%S')}] {o.ad} {o.veri}", flush=True))
    servis.baslat()

    hazir = False
    try:
        while not servis.bekle(0.5):
            if not hazir and servis.kare_no > 0 and servis.url:
                hazir = True  # İlk kare işlendi: kamera ve modeller çalışıyor
                print(f"Hazır. Kontrol paneli: {servis.url}  (kapatmak için panelde 'Servisi kapat' ya da Ctrl+C)",
                      flush=True)
                if not args.panel_acma:
                    webbrowser.open(servis.url)
    except KeyboardInterrupt:
        print("Kapatılıyor...")
        servis.durdur()
    if servis.kare_no == 0:
        metin = ("Kamera açılamadı ya da hiç görüntü gelmedi. Kamera başka bir programda açık olabilir.\n\n"
                 f"Ayrıntı: {os.path.join(ayarlar['kayit_klasoru'], 'servis.log')}")
        print(metin)
        if sys.stdin is None or not sys.stdin.isatty():
            mesaj_kutusu(metin)
        sys.exit(1)


if __name__ == "__main__":
    main()
