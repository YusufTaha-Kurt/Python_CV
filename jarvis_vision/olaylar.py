"""Olay yolu (event bus): JARVIS'in sinir sistemi.

Görüntü modülleri ne olduğunu YAYINLAR ("sağ elde yumruk yapıldı"), ne yapılacağını
bilmez. Fare, medya kontrolü ya da ileride yazılacak yapay zeka asistanı bu olaylara
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

    Dil modelleri ve diğer süreçler bu dosyayı satır satır okuyarak (tail -f gibi)
    görüntü olaylarını takip edebilir. JARVIS entegrasyonunun en basit köprüsü budur.
    """

    def __init__(self, dosya_yolu):
        self._dosya = open(dosya_yolu, "a", encoding="utf-8")

    def __call__(self, olay):
        self._dosya.write(json.dumps(asdict(olay), ensure_ascii=False) + "\n")
        self._dosya.flush()

    def kapat(self):
        self._dosya.close()
