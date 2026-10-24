# Ders 11: Mimik Komutları

**Amaç:** Yüz ifadeleriyle bilgisayara komut vermek ve bunu gerçek hayatta yanlış
tetiklenmeyecek kadar sağlam yapmak.

## İfadeler

MediaPipe yüz modeli her kare 52 ifade skoru (blendshape, 0-1) verir. Bunlardan altı üst
düzey ifade oluşturulur:

| İfade | Blendshape'ler | Eylem |
|-------|----------------|-------|
| Gülümseme | `mouthSmileLeft`, `mouthSmileRight` | Ekran görüntüsü (`ekran_goruntuleri/`) |
| Kaş kaldırma | `browInnerUp`, `browOuterUpLeft/Right` | Yukarı kaydır |
| Kaş çatma | `browDownLeft/Right` | Aşağı kaydır |
| Ağız açma | `jawOpen` | Oynat / duraklat |
| Dudak büzme | `mouthPucker` | Sesi kapat / aç |
| Yanak şişirme | `cheekPuff` | (sadece gösterilir) |

Bir ifade 0.4 sn boyunca eşiği (0.5) aşınca **bir kez** tetiklenir ve skor 0.3'ün altına
inene kadar tekrar tetiklenmez.

## Gerçek veride bulunan sorunlar ve çözümleri

Bilinçli ifade içermeyen 10 saniyelik gerçek bir webcam videosunda (kişi kapüşonunu, gözlüğünü
düzeltiyor, yüzüne dokunuyor) ilk sürüm **3 kez** "dudak büzme" komutu tetikledi.

| Sorun | Çözüm | Sonuç |
|-------|-------|-------|
| Kalibrasyonun ilk 2 saniyesinde el yüzdeydi, nötr taban kirlendi (dudak büzme medyanı 0.34 çıktı) | **Uyarlanır taban:** İnsanlar zamanlarının çoğunu nötr yüzle geçirir; son 30 sn'nin %30'luk dilimi nötr yüzü iyi tahmin eder. Taban buna doğru sürekli düzeltilir | 3 → 2 |
| El yüzü kapattığında model görmediği ağzı "uyduruyor" | **El kapısı:** El noktalarının %30'u yüz kutusundaysa yeni komut tetiklenmez | 2 → 1 |
| Dikkat toplarken kasıtsız dudak büzme | Bu ifadeye özel daha yüksek eşik (0.7) ve daha uzun tutma (0.6 sn) | Kalan 1 tetiklenme gerçek bir dudak büzme |

## Çalıştırma

```bash
python dersler/ders_11_mimik/mimik_komutlari.py --sadece-izle   # önce böyle dene
python dersler/ders_11_mimik/mimik_komutlari.py
```

İlk 2 saniye ifadesiz dur (nötr yüz ölçülür, **n** ile tekrarlanır). Ekrandaki çubuklar her
ifadenin skorunu ve kırmızı çizgi eşiği gösterir. El yüzündeyken yüz turuncu çizilir ve
komutlar duraklar.

## CV maddesi

> Yüz ifadesi skorlarını kişinin nötr yüzüne göre ölçekleyen, kendini sürekli düzelten bir
> taban ve el-yüz örtüşmesi kapısıyla ifade tabanlı komut sistemi geliştirdim; gerçek videoda
> kasıtsız komutları 3'ten 1'e indirdim.
