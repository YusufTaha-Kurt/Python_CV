# Yol Haritası: Mark I'den JARVIS'e

Her faz bir "Mark" zırhıdır: bir öncekinin üstüne kurulur ve sonunda elde çalışan bir ürün kalır.
Her dersin sonunda `jarvis_vision` paketine en az bir yeniden kullanılabilir modül eklenir.

**İlke:** Görüntü katmanı sadece olay yayınlar, eylemi aboneler yapar. Böylece Faz 4'te
yapay zeka asistanı, mevcut hiçbir derse dokunmadan olay yoluna bağlanabilir.

---

## Faz 1: Mark I, Eller

| # | Ders | Durum | Pakete eklenen | Öğrenilen kavramlar |
|---|------|-------|----------------|---------------------|
| 1 | El kontrollü fare V1 | ✅ | - | El iskeleti (21 nokta), koordinat dönüşümü, PyAutoGUI |
| 2 | Fare V2: akışkanlık | ✅ | `kamera`, `el`, `filtreler`, `imlec`, `hud` | 1€ filtresi, thread'ler, gecikme analizi, histerezis |
| 3 | Jest merkezi ve olay yolu | ✅ | `jestler`, `olaylar` | Kural tabanlı sınıflandırma, kenar tetikleme, yayınla-abone ol |
| 4 | Medya ve ses kontrolü | ✅ | `ses` | Windows Core Audio (pycaw), sürekli ve ayrık kontrol |
| 5 | Kaydırma ve pencere yönetimi | ⏳ | `kisayollar`, `modlar` | İki parmakla scroll, masaüstü değiştirme (Win+Ctrl+Ok), mod makinesi (fare / medya / sunum) |
| 6 | Hava çizimi ve holografik menü | ⏳ | `hud` (radyal menü) | Parmakla tuval (OpenCV Ders 3 paint'in el versiyonu), Stark tarzı radyal menü, çimdikle seçim |

## Faz 2: Mark II, Yüz

| # | Ders | Öğrenilen kavramlar |
|---|------|---------------------|
| 7 | Yüz iskeleti ve baş pozu | Face Landmarker (478 nokta), `solvePnP` ile baş yönü, baş hareketiyle imleç |
| 8 | Göz kırpma ile tıklama | Göz açıklık oranı (EAR), yorgunluk ve uyuklama alarmı |
| 9 | Mimik komutları | 52 blendshape skoru: gülümseme, kaş kaldırma, ağız açma ile komut |

## Faz 3: Mark III, Kimlik (Kapı Bekçisi)

| # | Ders | Öğrenilen kavramlar |
|---|------|---------------------|
| 10 | Yüz tanıma | Yüz gömme vektörleri (embedding), kosinüs benzerliği, kayıt veritabanı |
| 11 | Canlılık testi | Fotoğrafla kandırmaya karşı "göz kırp, gülümse" doğrulaması (Faz 2 tekrar kullanılır) |
| 12 | "Hoş geldiniz efendim" | Yüzle kilit açma, kişiye özel jest ayarları |

## Faz 4: Mark IV, Ses ve Beyin (JARVIS çekirdeği)

| # | Ders | Öğrenilen kavramlar |
|---|------|---------------------|
| 13 | Uyandırma kelimesi ve konuşma tanıma | "Jarvis" anahtar kelimesi, Türkçe konuşmayı yazıya çevirme (Whisper) |
| 14 | Sesli yanıt | Türkçe metinden sese (TTS) |
| 15 | Yapay zeka ajanı | Olay yolu = algı, `ses` / `imlec` / `medya` = araçlar. Dil modeline araç kullanımı (tool use) ile bağlanır. Kendi yapay zekan buraya takılır. |
| 16 | Çok kipli soru-cevap | "JARVIS, elimdeki ne?": kamera karesini görsel modele gönderme |

## Faz 5: Mark V, Dünya

| # | Ders | Öğrenilen kavramlar |
|---|------|---------------------|
| 17 | Nesne tespiti | YOLO ile nesne tanıma, nesneyle etkileşim |
| 18 | Vücut pozu | Pose Landmarker, tüm vücut jestleri, egzersiz sayacı |
| 19 | Tek uygulama | Tüm yetenekler eklenti olarak, sistem tepsisi, PyInstaller ile paketleme |

---

## Her dersin şablonu

```
dersler/ders_NN_konu/
  konu.py        Çalıştırılabilir ders (depo kökünden çalışır)
  README.md      Amaç, kavramlar, jest sözlüğü, ayarlar, CV maddesi
```

Kontrol listesi:
- [ ] Yeni yeniden kullanılabilir mantık `jarvis_vision/` altına
- [ ] Kamera gerektirmeyen kısımlar için `tests/` altında test
- [ ] `--sadece-izle` bayrağı (sisteme dokunmadan denemek için)
- [ ] Kök README'deki ders tablosu güncellendi
- [ ] Demo GIF kaydedildi (`docs/`)
