"""
Ders 4 - Medya ve Ses Kontrolü (OlayYolu'na ilk "yetenekleri" bağlamak)

Jest sözlüğü:
    L işareti (başparmak + işaret açık)  -> SES MODU: iki parmak arası mesafe = ses seviyesi
    Avuç aç                              -> ses modundan çık (seviye olduğu yerde kalır)
    Avuçla sağa / sola kaydır            -> sonraki / önceki parça
    Başparmak yukarı                     -> oynat / duraklat
    Rock (işaret + serçe)                -> sesi kapat / aç

Ders 3'ten farkı: Görüntü döngüsü yine sadece olay yayınlar (JestYayincisi). Medya
işlemleri bu olaylara abone olan ayrı bir sınıftır (goru.medya.MedyaKontrol). Yeni bir
yetenek eklemek, yeni bir abone yazmak kadar kolaydır.

Çalıştırma (depo kökünden):
    python dersler/ders_04_medya_kontrol/medya_kontrol.py
"""

import cv2

from goru import hud
from goru import jestler as j
from goru.el import ElTakipci
from goru.medya import MedyaKontrol
from goru.olaylar import OlayYolu
from goru.uygulama import Uygulama, arguman_ayraci


def main():
    """Ders akışı: JestYayincisi jest olaylarını yayınlar → MedyaKontrol bu olaylara abone olup
    medya tuşlarına basar; ses seviyesi gibi SÜREKLİ kontroller ise her karede `isle()` ile güncellenir."""
    ayrac = arguman_ayraci("Medya ve Ses Kontrolü")
    ayrac.add_argument("--el", choices=["sag", "sol"], default="sag")
    args = ayrac.parse_args()

    yol = OlayYolu()
    # medya.eylem olayını sadece konsola yazıyoruz; başka bir uygulama da aynı olaya abone olabilir
    yol.abone_ol("medya.eylem", lambda olay: print(f"[MEDYA] {olay.veri['eylem']}"))
    yayinci = j.JestYayincisi(yol, sure=0.35)
    medya = MedyaKontrol(yol, el=args.el, sadece_izle=args.sadece_izle)
    fps = hud.FpsSayaci()

    app = Uygulama(args, "Medya Kontrolu")
    with ElTakipci() as takipci:
        for kare, simdi in app.kareler():
            eller = [e for e in takipci.isle(kare, simdi) if e.taraf == args.el]
            el = eller[0] if eller else None
            yayinci.guncelle(eller, simdi)  # Önce olaylar (ses modu buradan açılır)
            medya.isle(el, simdi)  # Sonra sürekli kontrol

            if el is not None:
                n = el.noktalar
                hud.iskelet_ciz(kare, n)
                if medya.ses_modu:
                    p1 = tuple(int(v) for v in n[j.BAS_UCU, :2])
                    p2 = tuple(int(v) for v in n[j.ISARET_UCU, :2])
                    cv2.line(kare, p1, p2, hud.CAMGOBEGI, 3, cv2.LINE_AA)
                    orta_nokta = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
                    hud.reaktor_halkasi(kare, orta_nokta, medya.seviye, yaricap=34)

            genislik = kare.shape[1]
            seviye = medya.gosterilen_seviye()
            hud.cubuk(kare, (genislik - 70, 120), (35, 250), seviye, f"%{int(seviye * 100)}")
            hud.panel(
                kare,
                [
                    ("MOD: SES" if medya.ses_modu else "MOD: JEST", hud.YESIL),
                    f"JEST: {yayinci.jest(args.el).value}",
                    (f"EYLEM: {medya.son_eylem}", hud.TURUNCU),
                    f"SES API: {'pycaw' if medya.ses.destekleniyor else 'yok (medya tuslari)'}",
                    f"FPS: {fps.tik():.0f}",
                    "SADECE IZLEME" if args.sadece_izle else "Cikis: q",
                ],
                baslik="MEDYA",
            )
            app.goster(kare)


if __name__ == "__main__":
    main()
