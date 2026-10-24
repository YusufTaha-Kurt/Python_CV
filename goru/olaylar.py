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
    ad: str  # örn. "jest.degisti", "jest.kaydirma", "el.kayboldu"
    veri: dict = field(default_factory=dict)
    zaman: float = field(default_factory=time.time)


class OlayYolu:
    HEPSI = "*"

    def __init__(self):
        self._aboneler = {}
        self._kilit = threading.Lock()

    def abone_ol(self, ad, fonksiyon):
        """`ad` adlı olaylar için fonksiyonu kaydeder. "*" tüm olayları dinler."""
        with self._kilit:
            self._aboneler.setdefault(ad, []).append(fonksiyon)

    def abonelikten_cik(self, ad, fonksiyon):
        with self._kilit:
            if fonksiyon in self._aboneler.get(ad, []):
                self._aboneler[ad].remove(fonksiyon)

    def yayinla(self, ad, **veri):
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
        self._dosya.close()
