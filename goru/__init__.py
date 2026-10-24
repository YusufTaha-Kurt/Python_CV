"""
goru - Bilgisayarlı görü ile bilgisayar kontrolü çekirdeği.

Her derste büyüyen, yeniden kullanılabilir modüller: kamera, el / yüz / vücut / nesne
takibi, jestler, filtreler, kimlik doğrulama ve 7/24 çalışabilen servis.

Başka bir uygulama bu paketi iki yoldan kullanabilir:
  * Doğrudan: `from goru.el import ElTakipci`
  * Servis olarak: `goru.servis.Servis` (olay yolu + yerel HTTP arayüzü, bkz. Ders 17)

Not: Bu dosya bilerek hafif tutuldu (cv2 / mediapipe içe aktarmaz).
Böylece filtreler ve jestler gibi saf matematik modülleri kamera ve
model olmadan test edilebilir.
"""

__version__ = "1.0.0"
