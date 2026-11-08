"""
Ders 12 - Yüz Tanıma

YuNet ile yüzleri bulur, SFace ile her yüzü 128 sayılık bir vektöre çevirir ve kayıtlı
kişilerle kosinüs benzerliğine göre eşleştirir.

Kullanım (depo kökünden). En kolayı menüden: python baslat.py 12
    python dersler/ders_12_yuz_tanima/yuz_tanima.py --kaydet Yusuf      # kaydol ya da örnek ekle
    python dersler/ders_12_yuz_tanima/yuz_tanima.py --yeniden Yusuf     # eski kaydı silip baştan kaydol
    python dersler/ders_12_yuz_tanima/yuz_tanima.py                     # tanı
    python dersler/ders_12_yuz_tanima/yuz_tanima.py --listele           # kayıtlı kişiler
    python dersler/ders_12_yuz_tanima/yuz_tanima.py --sil Yusuf         # kaydı sil

Kayıt adım adım yönlendirilir: düz bak, sola, sağa, yukarı, aşağı. Ekranda o an ne
yapılacağı yazar. Bir açı 8 saniyede yakalanamazsa açıya bakılmadan örnek alınır.

Gizlilik: Yüz vektörleri sadece bu bilgisayarda, depo kökündeki kimlikler/ klasöründe tutulur
(.gitignore'da, GitHub'a yüklenmez).
"""

import os

import cv2

from goru import hud
from goru.kimlik import VARSAYILAN_ESIK, KimlikVeritabani, YonluKayit, YuzTanima
from goru.uygulama import Uygulama, arguman_ayraci

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KIMLIK_KLASORU = os.path.join(KOK, "kimlikler")
EN_AZ_ORNEK = 3
OKLAR = {"sol": "<<<", "sag": ">>>", "yukari": "^^^", "asagi": "vvv", "orta": "( )"}


def yuz_ciz(kare, satir, renk, etiket):
    """YuNet yüz satırını çizer: kutu, 5 hizalama noktası ve üstte etiket."""
    x, y, g, h = (int(v) for v in satir[:4])
    cv2.rectangle(kare, (x, y), (x + g, y + h), renk, 2, cv2.LINE_AA)
    for i in range(5):  # Gözler, burun, ağız köşeleri: hizalama bu noktalarla yapılır
        cv2.circle(kare, (int(satir[4 + 2 * i]), int(satir[5 + 2 * i])), 3, renk, -1, cv2.LINE_AA)
    if etiket:
        cv2.rectangle(kare, (x, y - 28), (x + max(g, 12 * len(etiket)), y), renk, -1)
        cv2.putText(kare, etiket, (x + 5, y - 8), hud.FONT, 0.6, (20, 20, 20), 2, cv2.LINE_AA)


def kayit_yonergesi(kare, kayit, zaman):
    """Ekranın ortasına büyük harflerle o adımda ne yapılacağını yazar."""
    if kayit.tamam:
        return
    ad = kayit.adimlar[kayit.adim][0]
    metin = f"{OKLAR[ad]}  {kayit.komut}  {OKLAR[ad]}"
    (g, _), _ = cv2.getTextSize(metin, hud.FONT, 1.0, 2)
    x, y = (kare.shape[1] - g) // 2, kare.shape[0] - 60
    cv2.rectangle(kare, (x - 16, y - 40), (x + g + 16, y + 18), (20, 20, 20), -1)
    cv2.putText(kare, metin, (x, y), hud.FONT, 1.0, hud.TURUNCU, 2, cv2.LINE_AA)
    kalan = kayit.kalan_sure(zaman)
    if ad != "orta" and kalan < kayit.adim_suresi:
        not_ = "Aci yakalanamadi, yine de ornek aliniyor" if kalan == 0 else f"{kalan:.0f} sn"
        cv2.putText(kare, not_, (x, y + 45), hud.FONT, 0.6, hud.BEYAZ, 1, cv2.LINE_AA)


def main():
    """İki kullanım: (1) `--kaydet İSİM` ile adım adım farklı açılardan örnek toplayıp kaydol,
    (2) seçenek yoksa kameradaki yüzleri kayıtlı kişilerle karşılaştırıp tanı.
    `--listele`, `--sil` ve `--yeniden` veritabanını yönetir. Hepsi yerel `kimlikler/` klasöründe tutulur."""
    ayrac = arguman_ayraci("Yüz Tanıma")
    ayrac.add_argument("--kaydet", metavar="ISIM", help="Bu isimle kaydol (kayıtlıysa örnek ekler)")
    ayrac.add_argument("--yeniden", metavar="ISIM", help="Eski kaydı silip bu isimle baştan kaydol")
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
    if args.yeniden:
        if args.yeniden in veritabani.isimler:
            veritabani.sil(args.yeniden)
            print(f"[KAYIT] {args.yeniden} için eski kayıt silindi, baştan kaydediliyor.")
        args.kaydet = args.yeniden

    tanima = YuzTanima()
    kayit = YonluKayit() if args.kaydet else None
    fps = hud.FpsSayaci()
    app = Uygulama(args, "Yuz Tanima")
    for kare, simdi in app.kareler():
        yuzler = tanima.bul(kare)  # 1) yüzleri bul (en büyük önce)
        for i, satir in enumerate(yuzler[:5]):
            gomme = tanima.gomme(kare, satir)  # 2) her yüzü 128 sayılık vektöre çevir
            # 3) Kayıt modunda örnek topla, tanıma modunda veritabanıyla karşılaştır
            if kayit is not None:
                if i == 0 and kayit.dene(gomme, satir, simdi):
                    print(f"[KAYIT] örnek {len(kayit.ornekler)}/{kayit.hedef} ({kayit.komut})")
                yuz_ciz(kare, satir, hud.TURUNCU, f"KAYIT {len(kayit.ornekler)}/{kayit.hedef}" if i == 0 else "")
            else:
                isim, benzerlik = veritabani.tani(gomme)
                if app.kare_no % 30 == 1:  # Konsolu boğmamak için saniyede bir
                    print(f"[TANIMA] {isim or 'taninmadi'} ({benzerlik:.2f})")
                yuz_ciz(kare, satir, hud.YESIL if isim else hud.KIRMIZI, f"{isim or 'TANINMADI'} {benzerlik:.2f}")

        if kayit is not None:
            satirlar = [(f"KAYIT: {args.kaydet}", hud.TURUNCU),
                        f"Adim {min(kayit.adim + 1, len(kayit.adimlar))}/{len(kayit.adimlar)}"
                        f"   Ornek {len(kayit.ornekler)}/{kayit.hedef}"]
            if not yuzler:
                satirlar.append(("Yuz bulunamadi: kameraya yaklas", hud.KIRMIZI))
            kayit_yonergesi(kare, kayit, simdi)
        else:
            satirlar = [(f"Kayitli kisi: {len(veritabani.isimler)}", hud.YESIL), f"Esik: {veritabani.esik:.2f}"]
            if not veritabani.isimler:
                satirlar.append(("Once kaydol: python baslat.py 12", hud.TURUNCU))
        satirlar += [f"Yuz: {len(yuzler)}   FPS: {fps.tik():.0f}", "q: cikis"]
        hud.panel(kare, satirlar, baslik="YUZ TANIMA")
        app.goster(kare)
        if kayit is not None and kayit.tamam:
            app.cik()

    if kayit is not None:
        if len(kayit.ornekler) >= EN_AZ_ORNEK:
            isim = veritabani.ekle(args.kaydet, kayit.ornekler)
            print(f"[KAYIT] {isim} kaydedildi: {len(kayit.ornekler)} örnek -> {args.kimlikler}")
        else:
            print(f"[KAYIT] Yetersiz örnek ({len(kayit.ornekler)}, en az {EN_AZ_ORNEK}). Kayıt yapılmadı.")


if __name__ == "__main__":
    main()
