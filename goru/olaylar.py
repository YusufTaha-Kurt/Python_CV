"""Olay yolu (event bus): modüller arası haberleşme ve dış uygulamalara entegrasyon arayüzü.

Görüntü modülleri ne olduğunu YAYINLAR ("sağ elde yumruk yapıldı"), ne yapılacağını
bilmez. Fare, medya kontrolü ya da bu paketi kullanan başka bir uygulama bu olaylara
ABONE olur. Böylece yeni bir yetenek eklemek için görüntü koduna dokunmak gerekmez.
"""

import json
import threading
import time
from dataclasses import asdict, dataclass, field


@dataclass
class Olay:
    """Yayınlanan tek bir olay: ne olduğu (`ad`), ayrıntıları (`veri`) ve ne zaman (`zaman`, epoch sn)."""

    ad: str  # örn. "jest.degisti", "jest.kaydirma", "el.kayboldu"
    veri: dict = field(default_factory=dict)
    zaman: float = field(default_factory=time.time)


class OlayYolu:
    """Basit yayınla / abone ol (publish-subscribe) mekanizması. Thread güvenlidir.

        yol = OlayYolu()
        yol.abone_ol("jest.degisti", lambda olay: print(olay.veri))
        yol.yayinla("jest.degisti", el="sag", jest="yumruk")
    """

    HEPSI = "*"  # abone_ol("*", ...) ile her olay dinlenir (günlükleme, HTTP akışı için)

    def __init__(self):
        self._aboneler = {}
        self._kilit = threading.Lock()

    def abone_ol(self, ad, fonksiyon):
        """`ad` adlı olaylar için fonksiyonu kaydeder. "*" tüm olayları dinler."""
        with self._kilit:
            self._aboneler.setdefault(ad, []).append(fonksiyon)

    def abonelikten_cik(self, ad, fonksiyon):
        """`abone_ol` ile kaydedilmiş fonksiyonu kaldırır."""
        with self._kilit:
            if fonksiyon in self._aboneler.get(ad, []):
                self._aboneler[ad].remove(fonksiyon)

    def yayinla(self, ad, /, **veri):
        """Olayı bütün abonelerine sırayla iletir ve Olay nesnesini döndürür."""
        # "/" sayesinde ad sadece konumla verilir; veri içinde "ad" adlı bir alan da kullanılabilir
        olay = Olay(ad, veri)
        with self._kilit:
            dinleyiciler = self._aboneler.get(ad, []) + self._aboneler.get(self.HEPSI, [])
        for fonksiyon in dinleyiciler:
            try:
                fonksiyon(olay)
            except Exception as hata:
                # Bir abonenin hatası görüntü döngüsünü çökertmemeli
                print(f"[OlayYolu] '{ad}' işlenirken hata: {hata}")
        return olay


class JsonlKaydedici:
    """Her olayı bir satır JSON olarak dosyaya yazar.

    Başka süreçler (başka bir dilde yazılmış olsalar bile) bu dosyayı satır satır okuyarak
    görüntü olaylarını takip edebilir. Ayrı süreçler arası en basit entegrasyon yolu budur.
    """

    def __init__(self, dosya_yolu):
        self._dosya = open(dosya_yolu, "a", encoding="utf-8")
        self._kilit = threading.Lock()

    def __call__(self, olay):
        with self._kilit:
            self._dosya.write(json.dumps(asdict(olay), ensure_ascii=False) + "\n")
            self._dosya.flush()

    def kapat(self):
        """Dosyayı kapatır."""
        self._dosya.close()
