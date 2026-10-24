"""
Ders 17 - 7/24 Servis

Önceki derslerin yetenekleri tek kamera ve tek süreçte, arka planda, sürekli çalışır.
Ayarlar servis_ayarlari.json dosyasından okunur (hangi yetenekler açık, kamera, port...).

    kontrol     Ders 8: fare / medya / pencere modları (sol elle 1/2/3 parmak: mod)
    yorgunluk   Ders 10: göz kırpma, PERCLOS, esneme uyarıları
    durus       Ders 16: kambur oturma / eğik omuz uyarısı
    mimik       Ders 11: yüz ifadesi olayları (isteğe bağlı komutlar)
    kapi        Ders 14: kapı bekçisi; "sadece_sahip" ile diğer yetenekler sahip yokken durur
    nesne       Ders 15: nesne tespiti ve takibi

Kontrol paneli: http://127.0.0.1:8770/  (yetenekleri aç / kapat, olayları canlı izle)

Çalıştırma (depo kökünden):
    python dersler/ders_17_servis/servis.py
    python dersler/ders_17_servis/servis.py --onizleme --sadece-izle
    python dersler/ders_17_servis/servis.py --yetenekler kontrol,yorgunluk,durus
Konsol penceresi olmadan (arka planda) çalıştırmak için python yerine pythonw kullan.
"""

import argparse
import logging
import os
import time
from logging.handlers import RotatingFileHandler

from goru.olaylar import OlayYolu
from goru.servis import Servis, ayarlari_yukle

KLASOR = os.path.dirname(os.path.abspath(__file__))


def main():
    """Servisi komut satırından başlatır. Sıra: ayar dosyasını oku → komut satırı seçenekleriyle üzerine yaz →
    günlük dosyasını kur (döner, 1 MB x 3) → Servis'i çalıştır (Ctrl+C ile durur).

    Bu dosya sadece bir başlatıcıdır; asıl iş goru/servis.py ve goru/yetenekler.py içindedir.
    Başka bir uygulamaya eklemek için bu dosya gerekmez: `from goru.servis import Servis` yeter.
    """
    ayrac = argparse.ArgumentParser(description="Python CV 7/24 servis")
    ayrac.add_argument("--ayarlar", default=os.path.join(KLASOR, "servis_ayarlari.json"))
    ayrac.add_argument("--kaynak", help="Kamera indeksi ya da video / görsel dosyası")
    ayrac.add_argument("--yetenekler", help="Sadece bu yetenekleri aç (virgülle), örn. kontrol,yorgunluk")
    ayrac.add_argument("--port", type=int, help="HTTP portu (0: boş bir port)")
    ayrac.add_argument("--onizleme", action="store_true", help="Kamera önizleme penceresi aç")
    ayrac.add_argument("--sadece-izle", action="store_true", help="Fareye, klavyeye ve sese dokunma")
    ayrac.add_argument("--kare-limiti", type=int, help="Bu kadar kare işleyip çık (test için)")
    ayrac.add_argument("--pencere-yok", action="store_true", help="(Servis zaten penceresizdir; uyumluluk için)")
    ayrac.add_argument("--sessiz", action="store_true", help="Olayları konsola yazma")
    args = ayrac.parse_args()

    # Öncelik: komut satırı > ayar dosyası > varsayılanlar
    ayarlar = ayarlari_yukle(args.ayarlar)
    if args.kaynak is not None:
        ayarlar["kaynak"] = int(args.kaynak) if args.kaynak.isdigit() else args.kaynak
    if args.yetenekler is not None:
        secilen = {ad.strip() for ad in args.yetenekler.split(",") if ad.strip()}
        for ad, ayar in ayarlar["yetenekler"].items():
            ayar["acik"] = ad in secilen
    if args.port is not None:
        ayarlar["http"]["port"] = args.port
    ayarlar["onizleme"] = args.onizleme and not args.pencere_yok
    ayarlar["sadece_izle"] = args.sadece_izle or ayarlar.get("sadece_izle", False)

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

    servis = Servis(ayarlar)
    if not args.sessiz:
        servis.yol.abone_ol(OlayYolu.HEPSI, lambda o: print(f"[{time.strftime('%H:%M:%S')}] {o.ad} {o.veri}",
                                                            flush=True))
    try:
        servis.calistir(kare_limiti=args.kare_limiti)
    except KeyboardInterrupt:
        logging.info("Ctrl+C: servis kapatılıyor")


if __name__ == "__main__":
    main()
