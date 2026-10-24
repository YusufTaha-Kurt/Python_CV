"""Ders 16: Eklem açıları, egzersiz tekrar sayacı, duruş bekçisi ve vücut jestleri.

Bu modül sadece numpy kullanır; girdi `.noktalar` (33, 3) ve `.gorunurluk` (33,) alanları
olan bir poz nesnesidir (goru.poz.Poz). Böylece sentetik pozlarla test edilebilir.
"""

import math
import statistics

import numpy as np

# MediaPipe vücut noktaları ("sol" = kişinin kendi solu)
BURUN = 0
SOL_OMUZ, SAG_OMUZ = 11, 12
SOL_DIRSEK, SAG_DIRSEK = 13, 14
SOL_BILEK, SAG_BILEK = 15, 16
SOL_KALCA, SAG_KALCA = 23, 24
SOL_DIZ, SAG_DIZ = 25, 26
SOL_AYAK, SAG_AYAK = 27, 28

EGZERSIZLER = {
    # eklem üçlüleri (her iki taraf), aşağı ve yukarı eşik açıları (derece)
    "squat": {"ad": "Squat", "eklemler": [(SOL_KALCA, SOL_DIZ, SOL_AYAK), (SAG_KALCA, SAG_DIZ, SAG_AYAK)],
              "asagi": 100, "yukari": 160},
    "biceps": {"ad": "Biceps curl", "eklemler": [(SOL_OMUZ, SOL_DIRSEK, SOL_BILEK), (SAG_OMUZ, SAG_DIRSEK, SAG_BILEK)],
               "asagi": 50, "yukari": 150},
    "sinav": {"ad": "Sinav", "eklemler": [(SOL_OMUZ, SOL_DIRSEK, SOL_BILEK), (SAG_OMUZ, SAG_DIRSEK, SAG_BILEK)],
              "asagi": 90, "yukari": 155},
}


def aci(a, b, c):
    """b noktasındaki açı (derece, 0-180)."""
    v1, v2 = np.asarray(a[:2], float) - b[:2], np.asarray(c[:2], float) - b[:2]
    kos = np.dot(v1, v2) / max(np.linalg.norm(v1) * np.linalg.norm(v2), 1e-9)
    return math.degrees(math.acos(float(np.clip(kos, -1, 1))))


def egzersiz_acisi(poz, egzersiz, gorunurluk_esigi=0.5):
    """Daha iyi görünen taraftaki eklem açısı; iki taraf da görünmüyorsa None."""
    en_iyi = None
    for a, b, c in EGZERSIZLER[egzersiz]["eklemler"]:
        gorunurluk = float(min(poz.gorunurluk[a], poz.gorunurluk[b], poz.gorunurluk[c]))
        if gorunurluk >= gorunurluk_esigi and (en_iyi is None or gorunurluk > en_iyi[0]):
            en_iyi = (gorunurluk, aci(poz.noktalar[a], poz.noktalar[b], poz.noktalar[c]))
    return en_iyi[1] if en_iyi else None


class TekrarSayaci:
    """Açı `asagi`nın altına inip sonra `yukari`nın üstüne çıkınca bir tekrar sayılır.

    İki ayrı eşik (histerezis) sayesinde tek bir eşik etrafındaki titreme çift sayılmaz.
    """

    def __init__(self, asagi, yukari):
        self.asagi, self.yukari = asagi, yukari
        self.faz = "yukari"
        self.sayi = 0

    def guncelle(self, aci_):
        if aci_ is None:
            return False
        if self.faz == "yukari" and aci_ < self.asagi:
            self.faz = "asagi"
        elif self.faz == "asagi" and aci_ > self.yukari:
            self.faz = "yukari"
            self.sayi += 1
            return True
        return False


class DurusBekcisi:
    """Önden bakan bir webcam için duruş izleme.

    Önden bakınca boynun öne eğilmesi doğrudan görünmez, ama kambur oturunca baş omuzlara
    yaklaşır. Ölçü: (omuz ortası y - burun y) / omuz genişliği. Önce dik oturuş kalibre
    edilir; oran bunun `esik` katının altına `uyari_suresi` boyunca inerse uyarılır.
    Omuz çizgisinin yataydan sapması da ayrıca izlenir (yana yaslanma).
    """

    def __init__(self, kalibrasyon_suresi=3.0, esik=0.8, egim_esigi=8.0, uyari_suresi=10.0, uyari_araligi=60.0):
        self.kalibrasyon_suresi = kalibrasyon_suresi
        self.esik = esik
        self.egim_esigi = egim_esigi
        self.uyari_suresi = uyari_suresi
        self.uyari_araligi = uyari_araligi
        self.taban = None
        self.oran = None
        self.egim = 0.0
        self._kalibrasyon = []
        self._kal_baslangic = None
        self._baslangic = {"kambur": None, "egik_omuz": None}
        self._son_uyari = {"kambur": -math.inf, "egik_omuz": -math.inf}

    def kalibre_et(self):
        self.taban, self._kalibrasyon, self._kal_baslangic = None, [], None

    def kalibrasyon_ilerlemesi(self, zaman):
        if self.taban is not None:
            return 1.0
        return 0.0 if self._kal_baslangic is None else min(1.0, (zaman - self._kal_baslangic) / self.kalibrasyon_suresi)

    def durum(self):
        """Şu an kambur / eğik mi (uyarı süresi beklenmeden)."""
        return {
            "kambur": self.taban is not None and self.oran is not None and self.oran < self.taban * self.esik,
            "egik_omuz": abs(self.egim) > self.egim_esigi,
        }

    def guncelle(self, poz, zaman):
        n, g = poz.noktalar, poz.gorunurluk
        if min(g[BURUN], g[SOL_OMUZ], g[SAG_OMUZ]) < 0.5:
            return []
        sol, sag = n[SOL_OMUZ, :2], n[SAG_OMUZ, :2]
        genislik = max(float(np.linalg.norm(sol - sag)), 1e-6)
        self.oran = ((sol[1] + sag[1]) / 2 - n[BURUN, 1]) / genislik
        dx, dy = sag[0] - sol[0], sag[1] - sol[1]
        self.egim = math.degrees(math.atan2(dy, abs(dx)))  # Yatay omuz çizgisi: 0°

        if self.taban is None:
            if self._kal_baslangic is None:
                self._kal_baslangic = zaman
            self._kalibrasyon.append(self.oran)
            if zaman - self._kal_baslangic >= self.kalibrasyon_suresi:
                self.taban = statistics.median(self._kalibrasyon)
            return []

        uyarilar = []
        for ad, kotu in self.durum().items():
            if not kotu:
                self._baslangic[ad] = None
                continue
            self._baslangic[ad] = self._baslangic[ad] if self._baslangic[ad] is not None else zaman
            if zaman - self._baslangic[ad] >= self.uyari_suresi and zaman - self._son_uyari[ad] > self.uyari_araligi:
                self._son_uyari[ad] = zaman
                uyarilar.append(ad)
        return uyarilar


class VucutJestleri:
    """Tüm vücutla jestler: eller yukarı, T pozu. Jest `sure` boyunca tutulunca bir kez bildirilir."""

    def __init__(self, sure=0.5):
        self.sure = sure
        self.mevcut = None
        self._aday, self._aday_zamani = None, 0.0

    @staticmethod
    def tani(poz):
        n, g = poz.noktalar, poz.gorunurluk
        if min(g[SOL_BILEK], g[SAG_BILEK], g[SOL_OMUZ], g[SAG_OMUZ]) < 0.5:
            return None
        omuz_gen = float(np.linalg.norm(n[SOL_OMUZ, :2] - n[SAG_OMUZ, :2]))
        if n[SOL_BILEK, 1] < n[BURUN, 1] and n[SAG_BILEK, 1] < n[BURUN, 1]:
            return "eller_yukari"
        omuz_y = (n[SOL_OMUZ, 1] + n[SAG_OMUZ, 1]) / 2
        bilekler_yatay = all(abs(n[b, 1] - omuz_y) < 0.35 * omuz_gen for b in (SOL_BILEK, SAG_BILEK))
        if bilekler_yatay and abs(n[SOL_BILEK, 0] - n[SAG_BILEK, 0]) > 2.5 * omuz_gen:
            return "t_pozu"
        return None

    def guncelle(self, poz, zaman):
        jest = self.tani(poz)
        if jest != self._aday:
            self._aday, self._aday_zamani = jest, zaman
        if self._aday != self.mevcut and zaman - self._aday_zamani >= self.sure:
            self.mevcut = self._aday
            return self.mevcut
        return None
