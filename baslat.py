"""
Tüm dersleri tek yerden başlat.

    python baslat.py                 Menüden seç
    python baslat.py 5               Ders 5'i başlat
    python baslat.py 5 --sadece-izle Ders 5'i fareye dokunmadan başlat (ek argümanlar derse iletilir)
"""

import os
import subprocess
import sys

KOK = os.path.dirname(os.path.abspath(__file__))

# (numara, ad, betik, açıklama)
DERSLER = [
    ("1", "El Kontrollu Fare V1", "faz-1-mouse-kontrol/hand_tracking.py", "Ilk surum (arsiv)"),
    ("2", "Fare V2", "dersler/ders_02_fare_v2/fare_v2.py", "1 euro filtresi, 144 Hz imlec"),
    ("3", "Jest Merkezi", "dersler/ders_03_jest_merkezi/jest_merkezi.py", "7 jest + kaydirma, olay yolu"),
    ("4", "Medya ve Ses", "dersler/ders_04_medya_kontrol/medya_kontrol.py", "L isareti ses, jestle medya"),
    ("5", "Fare V3", "dersler/ders_05_guvenilir_cimdik/fare_v3.py", "Guvenilir OK cimdigi, esik ornekleyici"),
    ("6", "Hologram Masasi I", "dersler/ders_06_hologram_masasi/hologram_masasi.py", "Tarayicida 3D kartlar"),
    ("7", "Hologram Masasi II", "dersler/ders_07_hologram_masasi_2/hologram_masasi_2.py", "Pence, alkis, piramit"),
    ("8a", "Kontrol Merkezi", "dersler/ders_08_kontrol_merkezi/kontrol_merkezi.py", "Fare / medya / pencere modlari"),
    ("8b", "Hava Cizimi", "dersler/ders_08_kontrol_merkezi/hava_cizimi.py", "Parmakla cizim"),
    ("9", "Bas Pozu", "dersler/ders_09_bas_pozu/bas_fare.py", "Basla imlec, bakarak tiklama"),
    ("10", "Goz Kirpma", "dersler/ders_10_goz_kirpma/goz_kirpma.py", "Kirpma, yorgunluk (--fare)"),
    ("11", "Mimik Komutlari", "dersler/ders_11_mimik/mimik_komutlari.py", "Yuz ifadesiyle komut"),
    ("12", "Yuz Tanima", "dersler/ders_12_yuz_tanima/yuz_tanima.py", "--kaydet ISIM ile kaydol"),
    ("13", "Canlilik Testi", "dersler/ders_13_canlilik/canlilik_testi.py", "Fotografa karsi hareket sorgusu"),
    ("14", "Kapi Bekcisi", "dersler/ders_14_kapi_bekcisi/kapi_bekcisi.py", "Tanima + canlilik, kilit"),
    ("15", "Nesne Tespiti", "dersler/ders_15_nesne_tespiti/nesne_tespiti.py", "Nesne + ID takibi, isaret et"),
    ("16", "Vucut Pozu", "dersler/ders_16_vucut_pozu/vucut_pozu.py", "Egzersiz sayaci, durus bekcisi"),
    ("17", "7/24 Servis", "dersler/ders_17_servis/servis.py", "Hepsi bir arada, panel: 127.0.0.1:8770"),
]


def menu():
    print("\n  PYTHON CV DERSLERI\n")
    for numara, ad, _, aciklama in DERSLER:
        print(f"  {numara:>3}  {ad:<22} {aciklama}")
    print("\n  Ipucu: once '--sadece-izle' ile dene (fareye, klavyeye, sese dokunmaz). q: cikis")
    return input("\n  Ders numarasi: ").strip()


def main():
    secim, ek = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else (menu(), [])
    if secim.lower() in ("q", ""):
        return
    ders = next((d for d in DERSLER if d[0] == secim or d[0] == secim + "a"), None)
    if ders is None:
        print(f"Bilinmeyen ders: {secim}")
        sys.exit(1)
    if not ek and len(sys.argv) <= 1:
        ek = input("  Ek argumanlar (bos birak ya da orn. --sadece-izle): ").split()
    print(f"\n  >>> Ders {ders[0]}: {ders[1]}\n")
    ortam = dict(os.environ, PYTHONPATH=KOK + os.pathsep + os.environ.get("PYTHONPATH", ""))
    sys.exit(subprocess.call([sys.executable, os.path.join(KOK, ders[2]), *ek], cwd=KOK, env=ortam))


if __name__ == "__main__":
    main()
