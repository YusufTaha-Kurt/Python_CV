"""
Ders 11 - Mimik Komutları

Yüz ifadeleriyle bilgisayara komut ver. İlk 2 saniye ifadesiz dur: nötr yüzün ölçülür.

    Gülümse            Ekran görüntüsü al (ekran_goruntuleri/ klasörüne)
    Kaşlarını kaldır   Yukarı kaydır
    Kaşlarını çat      Aşağı kaydır
    Ağzını aç          Oynat / duraklat
    Dudak büz          Sesi kapat / aç
    Yanak şişir        (sadece gösterilir, kendi eylemini ekleyebilirsin)

Tuşlar:  n nötr yüzü yeniden ölç   q çıkış

Çalıştırma (depo kökünden):
    python dersler/ders_11_mimik/mimik_komutlari.py --sadece-izle   # önce böyle dene
    python dersler/ders_11_mimik/mimik_komutlari.py
"""

import os
import time

import cv2

from goru import hud
from goru.el import ElTakipci
from goru.fare import PyAutoGuiFare
from goru.mimik import IFADELER, MimikAlgilayici, el_yuzu_kapatiyor
from goru.ses import medya_tusu
from goru.uygulama import Uygulama, arguman_ayraci
from goru.yuz import YuzTakipci, yuz_ciz

KLASOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ekran_goruntuleri")


def ekran_goruntusu():
    import pyautogui

    os.makedirs(KLASOR, exist_ok=True)
    yol = os.path.join(KLASOR, time.strftime("ekran_%Y%m%d_%H%M%S.png"))
    pyautogui.screenshot(yol)
    print(f"[MIMIK] kaydedildi: {yol}")


def eylemler():
    fare = PyAutoGuiFare()
    return {
        "gulumseme": ("ekran goruntusu", ekran_goruntusu),
        "kas_kaldirma": ("yukari kaydir", lambda: fare.kaydir(600)),
        "kas_catma": ("asagi kaydir", lambda: fare.kaydir(-600)),
        "agiz_acma": ("oynat/duraklat", lambda: medya_tusu("playpause")),
        "dudak_buzme": ("sessiz ac/kapa", lambda: medya_tusu("volumemute")),
    }


def main():
    args = arguman_ayraci("Mimik Komutları").parse_args()
    mimik = MimikAlgilayici()
    mimik.kalibre_et()
    eylem_tablosu = {ifade: (ad, None) for ifade, (ad, _) in eylemler().items()} if args.sadece_izle else eylemler()
    son = "-"
    fps = hud.FpsSayaci()

    app = Uygulama(args, "Mimik Komutlari")
    engel = False
    with YuzTakipci() as takipci, ElTakipci() as el_takipci:
        for kare, simdi in app.kareler():
            yuzler = takipci.isle(kare, simdi)
            if yuzler:
                # El yüzün üstündeyse model görmediği ağzı / kaşları uydurur: komutları duraklat
                engel = el_yuzu_kapatiyor(yuzler[0], el_takipci.isle(kare, simdi))
                yuz_ciz(kare, yuzler[0], hud.TURUNCU if engel else hud.CAMGOBEGI)
                for ifade in mimik.guncelle(yuzler[0].ifadeler, simdi, engel=engel):
                    ad, fonksiyon = eylem_tablosu.get(ifade, ("-", None))
                    son = f"{ifade} -> {ad}"
                    print(f"[MIMIK] {son}")
                    if fonksiyon:
                        fonksiyon()

            # İfade çubukları: eşik çizgisiyle
            x0, y0 = 15, kare.shape[0] - 30 * len(IFADELER) - 15
            for i, ifade in enumerate(IFADELER):
                y = y0 + 30 * i
                skor = mimik.skorlar[ifade]
                renk = hud.YESIL if ifade in mimik.aktif else hud.CAMGOBEGI
                cv2.rectangle(kare, (x0 + 150, y), (x0 + 150 + int(250 * skor), y + 20), renk, -1)
                cv2.rectangle(kare, (x0 + 150, y), (x0 + 400, y + 20), (90, 90, 90), 1)
                xe = x0 + 150 + int(250 * mimik.esik)
                cv2.line(kare, (xe, y - 3), (xe, y + 23), hud.KIRMIZI, 2)
                cv2.putText(kare, ifade, (x0, y + 16), hud.FONT, 0.5, hud.BEYAZ, 1, cv2.LINE_AA)

            satirlar = [("YUZ YOK", hud.TURUNCU)] if not yuzler else []
            if yuzler and engel:
                satirlar.append(("EL YUZDE: komutlar duraklatildi", hud.TURUNCU))
            if mimik.kalibre_ediliyor:
                satirlar.append((f"NOTR YUZ OLCULUYOR: ifadesiz dur %{int(mimik.kalibrasyon_ilerlemesi(simdi) * 100)}",
                                 hud.TURUNCU))
            satirlar += [(f"SON: {son}", hud.YESIL), f"FPS: {fps.tik():.0f}",
                         "SADECE IZLEME" if args.sadece_izle else "n notr yuz  q cikis"]
            hud.panel(kare, satirlar, baslik="MIMIK KOMUTLARI")
            if app.goster(kare) == ord("n"):
                mimik.kalibre_et()


if __name__ == "__main__":
    main()
