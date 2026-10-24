"""
Ders 12 - Yüz Tanıma

YuNet ile yüzleri bulur, SFace ile her yüzü 128 sayılık bir vektöre çevirir ve kayıtlı
kişilerle kosinüs benzerliğine göre eşleştirir.

Kullanım (depo kökünden):
    python dersler/ders_12_yuz_tanima/yuz_tanima.py --kaydet Yusuf   # kendini kaydet
    python dersler/ders_12_yuz_tanima/yuz_tanima.py                  # tanı
    python dersler/ders_12_yuz_tanima/yuz_tanima.py --listele
    python dersler/ders_12_yuz_tanima/yuz_tanima.py --sil Yusuf

Kayıt sırasında başını yavaşça sağa, sola, yukarı, aşağı çevir: birbirine çok benzeyen
örnekler atlanır, farklı açılardan 12 örnek toplanır.

Gizlilik: Yüz vektörleri sadece bu bilgisayarda, depo kökündeki kimlikler/ klasöründe tutulur
(.gitignore'da, GitHub'a yüklenmez).
"""

import os

import cv2

from goru import hud
from goru.kimlik import VARSAYILAN_ESIK, KayitToplayici, KimlikVeritabani, YuzTanima
from goru.uygulama import Uygulama, arguman_ayraci

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KIMLIK_KLASORU = os.path.join(KOK, "kimlikler")
EN_AZ_ORNEK = 3


def yuz_ciz(kare, satir, renk, etiket):
    x, y, g, h = (int(v) for v in satir[:4])
    cv2.rectangle(kare, (x, y), (x + g, y + h), renk, 2, cv2.LINE_AA)
    for i in range(5):  # Gözler, burun, ağız köşeleri: hizalama bu noktalarla yapılır
        cv2.circle(kare, (int(satir[4 + 2 * i]), int(satir[5 + 2 * i])), 3, renk, -1, cv2.LINE_AA)
    cv2.rectangle(kare, (x, y - 28), (x + max(g, 12 * len(etiket)), y), renk, -1)
    cv2.putText(kare, etiket, (x + 5, y - 8), hud.FONT, 0.6, (20, 20, 20), 2, cv2.LINE_AA)


def main():
    ayrac = arguman_ayraci("Yüz Tanıma")
    ayrac.add_argument("--kaydet", metavar="ISIM", help="Bu isimle yeni kişi kaydet (ya da örnek ekle)")
    ayrac.add_argument("--sil", metavar="ISIM", help="Kişiyi sil")
    ayrac.add_argument("--listele", action="store_true", help="Kayıtlı kişileri listele")
    ayrac.add_argument("--esik", type=float, default=VARSAYILAN_ESIK, help="Kosinüs benzerliği eşiği")
    ayrac.add_argument("--kimlikler", default=KIMLIK_KLASORU, help="Kimlik veritabanı klasörü")
    args = ayrac.parse_args()

    veritabani = KimlikVeritabani(args.kimlikler, esik=args.esik)
    if args.listele:
        for isim in veritabani.isimler:
            print(f"{isim}: {len(veritabani.kisiler[isim])} örnek")
        print(f"Toplam {len(veritabani.isimler)} kişi ({args.kimlikler})")
        return
    if args.sil:
        veritabani.sil(args.sil)
        print(f"Silindi: {args.sil}")
        return

    tanima = YuzTanima()
    toplayici = KayitToplayici() if args.kaydet else None
    fps = hud.FpsSayaci()
    app = Uygulama(args, "Yuz Tanima")
    for kare, _ in app.kareler():
        yuzler = tanima.bul(kare)
        for i, satir in enumerate(yuzler[:5]):
            gomme = tanima.gomme(kare, satir)
            if toplayici is not None:
                if i == 0 and toplayici.dene(gomme, satir):
                    print(f"[KAYIT] örnek {len(toplayici.ornekler)}/{toplayici.hedef}")
                yuz_ciz(kare, satir, hud.TURUNCU, f"KAYIT {len(toplayici.ornekler)}/{toplayici.hedef}" if i == 0 else "")
            else:
                isim, benzerlik = veritabani.tani(gomme)
                if app.kare_no % 30 == 1:  # Konsolu boğmamak için saniyede bir
                    print(f"[TANIMA] {isim or 'taninmadi'} ({benzerlik:.2f})")
                yuz_ciz(kare, satir, hud.YESIL if isim else hud.KIRMIZI, f"{isim or 'TANINMADI'} {benzerlik:.2f}")

        if toplayici is not None:
            satirlar = [(f"KAYIT: {args.kaydet}", hud.TURUNCU),
                        f"Ornek: {len(toplayici.ornekler)} / {toplayici.hedef}",
                        "Basini yavasca saga, sola, yukari, asagi cevir"]
        else:
            satirlar = [(f"Kayitli kisi: {len(veritabani.isimler)}", hud.YESIL), f"Esik: {veritabani.esik:.2f}"]
            if not veritabani.isimler:
                satirlar.append(("Once kaydol: --kaydet ISIM", hud.TURUNCU))
        satirlar += [f"Yuz: {len(yuzler)}   FPS: {fps.tik():.0f}", "q: cikis"]
        hud.panel(kare, satirlar, baslik="YUZ TANIMA")
        app.goster(kare)
        if toplayici is not None and toplayici.tamam:
            app.cik()

    if toplayici is not None:
        if len(toplayici.ornekler) >= EN_AZ_ORNEK:
            isim = veritabani.ekle(args.kaydet, toplayici.ornekler)
            print(f"[KAYIT] {isim} kaydedildi: {len(toplayici.ornekler)} örnek -> {args.kimlikler}")
        else:
            print(f"[KAYIT] Yetersiz örnek ({len(toplayici.ornekler)}, en az {EN_AZ_ORNEK}). Kayıt yapılmadı.")


if __name__ == "__main__":
    main()
