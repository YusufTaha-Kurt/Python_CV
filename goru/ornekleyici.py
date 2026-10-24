"""Ders 5: Kişiye özel eşik örnekleyici.

Eşikler bir başkasının eline göre ayarlanmışsa sizin elinizde yanlış çalışabilir. Bu modül
bir pozu birkaç saniye boyunca örnekler, her ölçümün dağılımını çıkarır ve "doğru" ile
"yanlış" pozları en iyi ayıran eşiği önerir.
"""

import statistics


class Ornekleyici:
    def __init__(self, sure=4.0):
        self.sure = sure
        self.etiket = None
        self.ornekler = {}  # etiket -> {ölçüm adı: [değerler]}
        self._baslangic = 0.0

    @property
    def kayitta(self):
        return self.etiket is not None

    def baslat(self, etiket, zaman):
        self.etiket = etiket
        self._baslangic = zaman
        self.ornekler[etiket] = {}

    def kalan(self, zaman):
        return max(0.0, self.sure - (zaman - self._baslangic)) if self.kayitta else 0.0

    def ekle(self, olcum, zaman):
        """Kayıttaysa ölçümü ekler. Süre dolduğunda True döndürür."""
        if not self.kayitta:
            return False
        for ad, deger in olcum.items():
            self.ornekler[self.etiket].setdefault(ad, []).append(float(deger))
        if zaman - self._baslangic >= self.sure:
            self.etiket = None
            return True
        return False

    def ozet(self, etiket):
        """{ölçüm: (min, medyan, max)}"""
        return {
            ad: (min(degerler), statistics.median(degerler), max(degerler))
            for ad, degerler in self.ornekler.get(etiket, {}).items()
        }


def esik_oner(dogru, yanlis):
    """İki değer listesini ayıran eşiği önerir.

    Dağılımlar ayrıksa eşik, aralarındaki boşluğun ("kanyonun") tam ortasından kesilir.
    Örtüşüyorlarsa uç değerler yerine %10 / %90 dilimleri kullanılır ve `ayrik` False döner.
    Dönüş: {"esik", "yon" (">" doğru değerler eşiğin üstünde demek), "ayrik"}
    """
    if not dogru or not yanlis:
        return None
    dogru_ust = statistics.median(dogru) > statistics.median(yanlis)
    d, y = sorted(dogru), sorted(yanlis)
    if dogru_ust:
        alt, ust = d[0], y[-1]
        ayrik = alt > ust
        if not ayrik:
            alt, ust = _dilim(d, 0.10), _dilim(y, 0.90)
    else:
        alt, ust = y[0], d[-1]
        ayrik = alt > ust
        if not ayrik:
            alt, ust = _dilim(y, 0.10), _dilim(d, 0.90)
    return {"esik": (alt + ust) / 2, "yon": ">" if dogru_ust else "<", "ayrik": ayrik}


def _dilim(sirali, oran):
    return sirali[min(len(sirali) - 1, int(oran * len(sirali)))]


def cimdik_ayari_oner(ornekleyici, ayarlar, dogru="cimdik", yanlis="yumruk"):
    """Örneklenen doğru çimdik ve yumruk pozlarından yeni CimdikAyarlari önerir.

    Dönüş: (yeni_ayarlar, rapor satırları)
    """
    from dataclasses import replace

    d, y = ornekleyici.ornekler.get(dogru, {}), ornekleyici.ornekler.get(yanlis, {})
    rapor, degisiklik = [], {}
    for ad, alan in (("kontrast", "kontrast"), ("arka", "arka_kemer")):
        oneri = esik_oner(d.get(ad, []), y.get(ad, []))
        if oneri and oneri["yon"] == ">":
            degisiklik[alan] = round(oneri["esik"], 3)
            rapor.append(f"{alan}: {getattr(ayarlar, alan):.2f} -> {oneri['esik']:.2f} ({'ayrik' if oneri['ayrik'] else 'ORTUSUYOR'})")
    if d.get("oran"):
        # Çimdik başlama eşiği: doğru çimdikteki en büyük aralığın biraz üstü
        yeni = min(0.45, max(0.20, max(d["oran"]) * 1.25))
        degisiklik["baslama"] = round(yeni, 3)
        rapor.append(f"baslama: {ayarlar.baslama:.2f} -> {yeni:.2f}")
    return replace(ayarlar, **degisiklik), rapor
