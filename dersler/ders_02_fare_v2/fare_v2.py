"""
Ders 2 - El Kontrollü Fare V2 (Akışkanlık Güncellemesi)

V1'e göre:
  * PyAutoGUI'nin her çağrıda 0.1 sn uyuması kapatıldı (asıl takılma sebebi)
  * İmleç ayrı thread'de 144 Hz akıyor (kamera 30 FPS olsa bile)
  * Sabit yumuşatma yerine hıza duyarlı 1€ filtresi
  * Kamera okuma thread'li, MediaPipe VIDEO (takip) modunda
  * Tıklama eşiği el boyutuna oranlı + histerezisli
  * İmleç başparmak yerine işaret parmağı kökünden alınıyor: çimdik yaparken kaymıyor
  * Tıklama/çift tık/sürükleme mantığı işletim sistemine bırakıldı (çimdik = sol tuş basılı)
  * Başparmak + orta parmak çimdiği = sağ tık
  * Yumruk = uyku modu (kenar tetiklemeli, tutarken aç/kapa yapmaz)

Çalıştırma (depo kökünden):
    python dersler/ders_02_fare_v2/fare_v2.py
    python dersler/ders_02_fare_v2/fare_v2.py --sadece-izle   # fareyi oynatmadan dene
    python dersler/ders_02_fare_v2/fare_v2.py --kaynak kayit.mp4   # kamera yerine video
"""

import math

import cv2
import numpy as np
import pyautogui

from goru import hud
from goru import jestler as j
from goru.el import ElTakipci
from goru.filtreler import OneEuroFiltre
from goru.imlec import ImlecSurucu
from goru.uygulama import Uygulama, arguman_ayraci

# --- Ayarlar ---
KUTU_ORANI = 0.18  # Sanal çalışma alanının kamera kenarlarına uzaklığı (kare boyutuna oranla)
IMLEC_NOKTASI = j.ISARET_KOK  # Çimdik yaparken en az kıpırdayan nokta
FILTRE_MIN_KESIM = 0.6  # Düşür -> dururken daha az titreme
FILTRE_BETA = 6.0  # Artır -> hızlı harekette daha az gecikme
SURUKLEME_ESIGI = 0.025  # Çimdikteyken imlecin serbest kalması için gereken hareket (ekran genişliğine oranla)
CIFT_TIK_PENCERESI = 0.3  # Bıraktıktan sonra imlecin donuk kalacağı süre (çift tık aynı noktaya düşsün)


def argumanlar():
    """Ortak seçeneklere (--kaynak, --sadece-izle...) bu derse özel `--el` seçeneğini ekler."""
    ayrac = arguman_ayraci("El Kontrollü Fare V2")
    ayrac.add_argument("--el", choices=["sag", "sol"], default="sag", help="Fareyi yönetecek el")
    return ayrac.parse_args()


def main():
    """Ders akışı (her karede): el bul → yumruksa uyku modunu çevir → imleci hedefle →
    çimdikle tuşa bas / bırak → sağ tık → ekrana geri bildirim çiz."""
    args = argumanlar()
    ekran_genisligi, ekran_yuksekligi = pyautogui.size()
    surukleme_esigi_px = SURUKLEME_ESIGI * ekran_genisligi

    filtre = OneEuroFiltre(min_kesim=FILTRE_MIN_KESIM, beta=FILTRE_BETA)
    sol_tik = j.CimdikAlgilayici(baslama=0.25, birakma=0.38)  # Başparmak + işaret
    sag_tik = j.CimdikAlgilayici(baslama=0.25, birakma=0.38)  # Başparmak + orta
    jest_takip = j.JestKararlilastirici(sure=0.4)
    fps = hud.FpsSayaci()
    surucu = ImlecSurucu()
    if not args.sadece_izle:
        surucu.baslat()

    uyku_modu_aktif = False
    basili_tutuluyor_mu = False
    kilit_noktasi = None
    birakma_zamani = 0.0
    jest = j.Jest.BILINMIYOR

    def fare_birak():
        """Basılı fare tuşunu bırakır ve imleç / çimdik durumunu sıfırlar (el kaybolunca ya da uykuya geçince)."""
        nonlocal basili_tutuluyor_mu
        if basili_tutuluyor_mu and not args.sadece_izle:
            pyautogui.mouseUp(_pause=False)
        basili_tutuluyor_mu = False
        surucu.dondur(False)
        sol_tik.sifirla()
        sag_tik.sifirla()

    app = Uygulama(args, "Fare V2")
    with ElTakipci() as takipci:
        for kare, simdi in app.kareler():
            yukseklik, genislik = kare.shape[:2]
            kx1, ky1 = int(genislik * KUTU_ORANI), int(yukseklik * KUTU_ORANI)
            kx2, ky2 = genislik - kx1, yukseklik - ky1
            cv2.rectangle(kare, (kx1, ky1), (kx2, ky2), hud.CAMGOBEGI, 1, cv2.LINE_AA)

            el = next((e for e in takipci.isle(kare, simdi) if e.taraf == args.el), None)

            if el is None:
                # El kaybolduysa basılı tuş takılı kalmasın; filtre de sıfırlansın ki
                # el geri geldiğinde eski konumdan "çekilme" olmasın
                fare_birak()
                filtre.sifirla()
                jest_takip.sifirla()
            else:
                n = el.noktalar
                hud.iskelet_ciz(kare, n, hud.TURUNCU if uyku_modu_aktif else hud.CAMGOBEGI)

                # --- 1. UYKU MODU (kenar tetiklemeli yumruk) ---
                # Çimdik sırasında parmaklar kıvrık olduğundan yumruk sanılabilir; o anda jestleri yok say
                if not sol_tik.aktif and not sag_tik.aktif:
                    yeni_jest = jest_takip.guncelle(j.jest_tani(n), simdi)
                    jest = jest_takip.mevcut
                    if yeni_jest == j.Jest.YUMRUK:
                        uyku_modu_aktif = not uyku_modu_aktif
                        fare_birak()

                if not uyku_modu_aktif:
                    # --- 2. İMLEÇ: kutu içi konumu ekrana oranla, 1€ filtresinden geçir ---
                    x, y = n[IMLEC_NOKTASI, :2]
                    nx = np.clip((x - kx1) / (kx2 - kx1), 0, 1)
                    ny = np.clip((y - ky1) / (ky2 - ky1), 0, 1)
                    fx, fy = filtre((nx, ny), simdi)
                    hedef = (fx * (ekran_genisligi - 1), fy * (ekran_yuksekligi - 1))
                    surucu.hedef_ayarla(*hedef)

                    # --- 3. SOL TUŞ: çimdik = basılı, bırakmak = tuşu bırak ---
                    # Tek tık, çift tık ve sürüklemeyi işletim sistemi kendisi ayırt eder.
                    sol_oran = j.cimdik_orani(n, j.BAS_UCU, j.ISARET_UCU)
                    durum = sol_tik.guncelle(sol_oran)
                    if durum == "basladi" and not sag_tik.aktif:
                        if not surucu.donmus:
                            surucu.dondur(True)
                            kilit_noktasi = hedef
                        if not args.sadece_izle:
                            pyautogui.mouseDown(_pause=False)
                        basili_tutuluyor_mu = True
                    elif durum == "bitti" and basili_tutuluyor_mu:
                        if not args.sadece_izle:
                            pyautogui.mouseUp(_pause=False)
                        basili_tutuluyor_mu = False
                        birakma_zamani = simdi

                    # Donuk imleç: el belirgin hareket ederse sürükleme başlar,
                    # tuş bırakılıp çift tık penceresi geçerse serbest kalır
                    if surucu.donmus and kilit_noktasi is not None:
                        uzaklasti = math.dist(hedef, kilit_noktasi) > surukleme_esigi_px
                        pencere_bitti = not basili_tutuluyor_mu and simdi - birakma_zamani > CIFT_TIK_PENCERESI
                        if uzaklasti or pencere_bitti:
                            surucu.dondur(False)

                    # --- 4. SAĞ TIK: başparmak + orta parmak ---
                    sag_oran = j.cimdik_orani(n, j.BAS_UCU, j.ORTA_UCU)
                    if sag_tik.guncelle(sag_oran) == "basladi" and not sol_tik.aktif and not args.sadece_izle:
                        pyautogui.rightClick(_pause=False)

                    # --- 5. Görsel geri bildirim ---
                    # Halka, parmaklar yaklaştıkça dolar; tam dolduğunda tıklama olur
                    dolum = 1 - (sol_oran - sol_tik.baslama) / (1.0 - sol_tik.baslama)
                    renk = hud.YESIL if sol_tik.aktif else hud.CAMGOBEGI
                    hud.reaktor_halkasi(kare, n[j.ISARET_UCU], dolum, renk=renk)
                    cv2.circle(kare, tuple(int(v) for v in n[IMLEC_NOKTASI, :2]), 7, hud.KIRMIZI, -1, cv2.LINE_AA)

            if uyku_modu_aktif:
                mod = ("MOD: UYKU (uyanmak icin yumruk)", hud.TURUNCU)
            elif basili_tutuluyor_mu:
                mod = ("MOD: BASILI / SURUKLE", hud.YESIL)
            else:
                mod = ("MOD: AKTIF", hud.YESIL)
            hud.panel(
                kare,
                [
                    mod,
                    f"EL: {args.el.upper()} {'(goruldu)' if el else '(yok)'}",
                    f"JEST: {jest.value}",
                    f"FPS: {fps.tik():.0f}",
                    ("SADECE IZLEME" if args.sadece_izle else "Cikis: q", hud.BEYAZ),
                ],
                baslik="FARE v2",
            )
            app.goster(kare)

    fare_birak()
    surucu.durdur()


if __name__ == "__main__":
    main()
