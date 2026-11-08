"""
Tüm dersleri tek yerden başlat.

    python baslat.py                 Menüden seç
    python baslat.py 5               Ders 5'i başlat
    python baslat.py 5 --sadece-izle Ders 5'i fareye dokunmadan başlat (ek argümanlar derse iletilir)
    python baslat.py 12              Yüz tanıma alt menüsü (kaydol, yeniden kaydol, tanı, listele, sil)

Dersler iki gruptadır. Temel dersler günlük kullanıma yöneliktir. Ekstra dersler teknik olarak
öğreticidir ama herkesin günlük ihtiyacı değildir (baş ve yüz ifadesiyle kontrol, tarayıcıda
hologram masası, göz kırparak tıklama). Kodları ve README'leri yerinde durur.
"""

import os
import subprocess
import sys

KOK = os.path.dirname(os.path.abspath(__file__))

# (numara, ad, betik, açıklama, ekstra mı, varsayılan argümanlar)
DERSLER = [
    ("1", "El Kontrollu Fare V1", "dersler/ders_01_fare_v1/fare_v1.py", "Ilk surum: cimdikle tik, yumrukla uyku", False, []),
    ("2", "Fare V2", "dersler/ders_02_fare_v2/fare_v2.py", "1 euro filtresi, 144 Hz imlec", False, []),
    ("3", "Jest Merkezi", "dersler/ders_03_jest_merkezi/jest_merkezi.py", "7 jest + kaydirma, olay yolu", False, []),
    ("4", "Medya ve Ses", "dersler/ders_04_medya_kontrol/medya_kontrol.py", "L isareti ses, jestle medya", False, []),
    ("5", "Fare V3", "dersler/ders_05_guvenilir_cimdik/fare_v3.py", "Guvenilir OK cimdigi, esik ornekleyici", False, []),
    ("6", "Hologram Masasi I", "dersler/ders_06_hologram_masasi/hologram_masasi.py", "Tarayicida 3D kartlar", True, []),
    ("7", "Hologram Masasi II", "dersler/ders_07_hologram_masasi_2/hologram_masasi_2.py", "Pence, alkis, piramit", True, []),
    ("8a", "Kontrol Merkezi", "dersler/ders_08_kontrol_merkezi/kontrol_merkezi.py", "Fare / medya / pencere modlari", False, []),
    ("8b", "Hava Cizimi", "dersler/ders_08_kontrol_merkezi/hava_cizimi.py", "Parmakla cizim", False, []),
    ("9", "Bas Pozu", "dersler/ders_09_bas_pozu/bas_fare.py", "Basla imlec, bakarak tiklama", True, []),
    ("10", "Yorgunluk", "dersler/ders_10_goz_kirpma/goz_kirpma.py", "Kirpma hizi, PERCLOS, mola uyarisi", False, []),
    ("10f", "Goz Kirpma Faresi", "dersler/ders_10_goz_kirpma/goz_kirpma.py", "Basla imlec + goz kirparak tik", True, ["--fare"]),
    ("11", "Mimik Komutlari", "dersler/ders_11_mimik/mimik_komutlari.py", "Yuz ifadesiyle komut", True, []),
    ("12", "Yuz Tanima", "dersler/ders_12_yuz_tanima/yuz_tanima.py", "Kaydol / tani (alt menu)", False, []),
    ("13", "Canlilik Testi", "dersler/ders_13_canlilik/canlilik_testi.py", "Fotografa karsi hareket sorgusu", False, []),
    ("14", "Kapi Bekcisi", "dersler/ders_14_kapi_bekcisi/kapi_bekcisi.py", "Tanima + canlilik, kilit", False, []),
    ("15", "Nesne Tespiti", "dersler/ders_15_nesne_tespiti/nesne_tespiti.py", "Nesne + ID takibi, isaret et", False, []),
    ("16", "Vucut Pozu", "dersler/ders_16_vucut_pozu/vucut_pozu.py", "Egzersiz sayaci, durus bekcisi", False, []),
    ("17", "7/24 Servis", "dersler/ders_17_servis/servis.py", "Hepsi bir arada, panel: 127.0.0.1:8770", False, []),
]


def girdi(soru):
    """Kullanıcıdan satır okur; bazı terminallerin başa eklediği görünmez BOM karakterini atar."""
    return input(soru).strip().lstrip(chr(0xFEFF))


def menu():
    """Dersleri temel ve ekstra diye iki grupta listeler, seçilen numarayı döndürür."""
    print("\n  PYTHON CV DERSLERI\n\n  TEMEL")
    for numara, ad, _, aciklama, ekstra, _ in DERSLER:
        if not ekstra:
            print(f"  {numara:>4}  {ad:<22} {aciklama}")
    print("\n  EKSTRA (ogretici, gundelik kullanim icin degil)")
    for numara, ad, _, aciklama, ekstra, _ in DERSLER:
        if ekstra:
            print(f"  {numara:>4}  {ad:<22} {aciklama}")
    print("\n  Ipucu: once '--sadece-izle' ile dene (fareye, klavyeye, sese dokunmaz). q: cikis")
    return girdi("\n  Ders numarasi: ")


def yuz_tanima_menusu():
    """Ders 12'nin komutlarını seçenek olarak sunar; derse verilecek argümanları döndürür."""
    print("\n  YUZ TANIMA\n")
    print("     1  Tani            Kameradaki yuzu kayitli kisilerle karsilastir")
    print("     2  Kaydol          Yeni kisi kaydet ya da kayitli kisiye ornek ekle")
    print("     3  Yeniden kaydol  Eski kaydi silip bastan kaydol")
    print("     4  Listele         Kayitli kisileri goster")
    print("     5  Sil             Bir kisinin kaydini sil")
    secim = girdi("\n  Secim (bos: 1): ") or "1"
    if secim in ("2", "3", "5"):
        isim = girdi("  Isim: ")
        if not isim:
            print("Isim bos olamaz.")
            sys.exit(1)
        return [{"2": "--kaydet", "3": "--yeniden", "5": "--sil"}[secim], isim]
    return ["--listele"] if secim == "4" else []


def main():
    menuden = len(sys.argv) <= 1
    secim, ek = (menu(), []) if menuden else (sys.argv[1], sys.argv[2:])
    if secim.lower() in ("q", ""):
        return
    ders = next((d for d in DERSLER if d[0] == secim.lower() or d[0] == secim + "a"), None)
    if ders is None:
        print(f"Bilinmeyen ders: {secim}")
        sys.exit(1)
    numara, ad, betik, _, _, varsayilan = ders
    if numara == "12" and not ek:
        ek = yuz_tanima_menusu()
    elif menuden:
        ek = girdi("  Ek argumanlar (bos birak ya da orn. --sadece-izle): ").split()
    print(f"\n  >>> Ders {numara}: {ad}\n")
    ortam = dict(os.environ, PYTHONPATH=KOK + os.pathsep + os.environ.get("PYTHONPATH", ""))
    sys.exit(subprocess.call([sys.executable, os.path.join(KOK, betik), *varsayilan, *ek], cwd=KOK, env=ortam))


if __name__ == "__main__":
    main()
