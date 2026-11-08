"""
Ders 1 - El Kontrollü Fare V1

İlk çalışan sürüm: el iskeleti, başparmakla imleç, başparmak + işaret çimdiğiyle tıklama,
yumrukla uyku modu.

Kamera, el takibi ve ekran çizimi diğer derslerle aynı ortak `goru` altyapısından gelir.
Böylece Ders 2 ile aynı görüntüyü işler ve fark sadece fare mantığında kalır. Fare mantığı
bilerek V1'deki gibi bırakıldı, Ders 2 bu hataları tek tek ölçüp düzeltir:
  * Sabit yumuşatma faktörü (ya hantal ya titrek)
  * İmleç başparmak ucundan alınır (çimdik yaparken kayar)
  * Sabit 25 piksel tıklama eşiği (el uzaklaşınca tetiklenmez)
  * Tek / çift tık ve sürükleme zamanlayıcılarla elle ayırt edilir
  * Yumruk tutuldukça uyku modu her saniye aç / kapa olur
  * İmleç kamera hızında (≤30 Hz) güncellenir, 144 Hz monitörde basamaklı görünür

Çalıştırma (depo kökünden):
    python baslat.py 1 --sadece-izle
    python dersler/ders_01_fare_v1/fare_v1.py --sadece-izle   # fareyi oynatmadan dene
    python dersler/ders_01_fare_v1/fare_v1.py --kaynak kayit.mp4
"""

import math
import time

import cv2
import pyautogui

from goru import hud
from goru import jestler as j
from goru.el import ElTakipci
from goru.uygulama import Uygulama, arguman_ayraci

# --- Ayarlar (V1'deki değerler) ---
KUTU_KENAR_BOSLUGU = 100  # Sanal çalışma alanının kamera kenarlarına uzaklığı (piksel)
YUMUSATMA_FAKTORU = 2  # Arttıkça imleç daha hantal ama pürüzsüz hareket eder
TIKLAMA_ESIGI_PX = 25  # Başparmak ile işaret ucu bu kadar yaklaşınca tıklanır
CIFT_TIK_TOLERANSI = 0.45  # İki tık arası bundan kısaysa ikinci tık "basılı tut" olur
KISA_TEMAS = 0.25  # Basılı tutma bundan kısa sürdüyse sürükleme değil çift tıktır
YUMRUK_BEKLEMESI = 1.0  # Uyku modunun tekrar değişebilmesi için geçmesi gereken süre (sn)


def argumanlar():
    """Ortak seçeneklere (--kaynak, --sadece-izle...) bu derse özel `--el` seçeneğini ekler."""
    ayrac = arguman_ayraci("El Kontrollü Fare V1")
    ayrac.add_argument("--el", choices=["sag", "sol"], default="sag", help="Fareyi yönetecek el")
    return ayrac.parse_args()


def yumruk_mu(n):
    """V1 yumruk testi: dört parmağın ucu bileğe, alt boğumundan daha yakınsa el kapalıdır."""
    def bilek_mesafesi(i):
        return math.dist(n[i, :2], n[j.BILEK, :2])

    return all(bilek_mesafesi(uc) < bilek_mesafesi(uc - 2) for uc in (8, 12, 16, 20))


def main():
    """Ders akışı (her karede): el bul → yumruksa uyku modunu çevir → başparmağı ekrana oranla →
    sabit faktörle yumuşat → çimdik mesafesine göre tıkla / basılı tut / bırak."""
    args = argumanlar()
    ekran_genisligi, ekran_yuksekligi = pyautogui.size()
    pyautogui.FAILSAFE = False  # Fare köşeye gidince program durmasın
    # PyAutoGUI varsayılan olarak her çağrıdan sonra 0.1 sn uyur: döngü ~10 FPS'e sabitlenir.
    # Bu ders de kameranın verdiği en yüksek hızda çalışsın diye kapatıldı (kök neden Ders 2'de).
    pyautogui.PAUSE = 0

    fps = hud.FpsSayaci()
    onceki_fare_x, onceki_fare_y = ekran_genisligi / 2, ekran_yuksekligi / 2
    son_tiklama_zamani = 0.0
    temas_baslangic_zamani = 0.0
    tiklama_durumu = False
    basili_tutuluyor_mu = False
    uyku_modu_aktif = False
    son_yumruk_zamani = 0.0
    mesaj = ""

    def fare(islem):
        """`--sadece-izle` açıkken fareye hiç dokunmaz."""
        if not args.sadece_izle:
            islem()

    app = Uygulama(args, "Fare V1")
    with ElTakipci() as takipci:
        for kare, simdi in app.kareler():
            yukseklik, genislik = kare.shape[:2]
            min_x, max_x = KUTU_KENAR_BOSLUGU, genislik - KUTU_KENAR_BOSLUGU
            min_y, max_y = KUTU_KENAR_BOSLUGU, yukseklik - KUTU_KENAR_BOSLUGU
            cv2.rectangle(kare, (min_x, min_y), (max_x, max_y), (255, 0, 255), 2)

            el = next((e for e in takipci.isle(kare, simdi) if e.taraf == args.el), None)
            mesaj = ""

            if el is not None:
                n = el.noktalar
                hud.iskelet_ciz(kare, n, hud.TURUNCU if uyku_modu_aktif else hud.CAMGOBEGI)

                # --- 1. UYKU MODU: yumruk her YUMRUK_BEKLEMESI saniyede bir durumu çevirir ---
                if yumruk_mu(n) and simdi - son_yumruk_zamani > YUMRUK_BEKLEMESI:
                    uyku_modu_aktif = not uyku_modu_aktif
                    son_yumruk_zamani = simdi

                if not uyku_modu_aktif:
                    x1, y1 = (int(v) for v in n[j.ISARET_UCU, :2])
                    x2, y2 = (int(v) for v in n[j.BAS_UCU, :2])

                    # --- 2. İMLEÇ: kutu içindeki başparmak konumunu bütün ekrana oranla ---
                    sinirli_x = max(min_x, min(x2, max_x))
                    sinirli_y = max(min_y, min(y2, max_y))
                    hedef_x = (sinirli_x - min_x) / (max_x - min_x) * ekran_genisligi
                    hedef_y = (sinirli_y - min_y) / (max_y - min_y) * ekran_yuksekligi

                    # Sabit yumuşatma: her karede hedefe kalan yolun 1/faktörü kadar git
                    fare_x = onceki_fare_x + (hedef_x - onceki_fare_x) / YUMUSATMA_FAKTORU
                    fare_y = onceki_fare_y + (hedef_y - onceki_fare_y) / YUMUSATMA_FAKTORU
                    fare(lambda: pyautogui.moveTo(int(fare_x), int(fare_y)))
                    onceki_fare_x, onceki_fare_y = fare_x, fare_y

                    cv2.circle(kare, (x1, y1), 12, hud.KIRMIZI, -1, cv2.LINE_AA)  # İşaret
                    cv2.circle(kare, (x2, y2), 12, (255, 0, 0), -1, cv2.LINE_AA)  # Başparmak
                    cv2.line(kare, (x1, y1), (x2, y2), hud.YESIL, 3, cv2.LINE_AA)

                    # --- 3. TIKLAMA: sabit piksel eşiği ---
                    if math.hypot(x2 - x1, y2 - y1) < TIKLAMA_ESIGI_PX:
                        cv2.circle(kare, (x1, y1), 15, hud.YESIL, -1, cv2.LINE_AA)
                        su_an = time.time()
                        if not tiklama_durumu:  # Parmaklar ilk kez birleşti
                            temas_baslangic_zamani = su_an
                            if su_an - son_tiklama_zamani < CIFT_TIK_TOLERANSI:
                                fare(pyautogui.mouseDown)
                                basili_tutuluyor_mu = True
                            else:
                                fare(pyautogui.click)
                                son_tiklama_zamani = su_an
                        tiklama_durumu = True
                        mesaj = "BASILI TUTULUYOR (SURUKLE)" if basili_tutuluyor_mu else "TIKLANDI"
                    elif tiklama_durumu:  # Parmaklar ayrıldı
                        if basili_tutuluyor_mu:
                            fare(pyautogui.mouseUp)
                            basili_tutuluyor_mu = False
                            # İkinci temas çok kısaysa bu bir sürükleme değil, çift tıktır
                            if time.time() - temas_baslangic_zamani < KISA_TEMAS:
                                fare(pyautogui.click)
                        tiklama_durumu = False

            if uyku_modu_aktif:
                mod = ("MOD: UYKU (uyanmak icin yumruk)", hud.TURUNCU)
            elif mesaj:
                mod = (f"MOD: {mesaj}", hud.YESIL)
            else:
                mod = ("MOD: AKTIF", hud.YESIL)
            hud.panel(
                kare,
                [
                    mod,
                    f"EL: {args.el.upper()} {'(goruldu)' if el else '(yok)'}",
                    f"FPS: {fps.tik():.0f}",
                    ("SADECE IZLEME" if args.sadece_izle else "Cikis: q", hud.BEYAZ),
                ],
                baslik="FARE v1",
            )
            app.goster(kare)

    if basili_tutuluyor_mu:
        fare(pyautogui.mouseUp)


if __name__ == "__main__":
    main()
