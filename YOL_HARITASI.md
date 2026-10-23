# Yol Haritası: Mark I'den JARVIS'e

Her faz bir "Mark" zırhıdır: bir öncekinin üstüne kurulur ve sonunda elde çalışan bir ürün kalır.
Her dersin sonunda `jarvis_vision` paketine en az bir yeniden kullanılabilir modül eklenir.

**İlke:** Görüntü katmanı sadece olay yayınlar, eylemi aboneler yapar. Böylece Faz 4'te
yapay zeka asistanı, mevcut hiçbir derse dokunmadan olay yoluna bağlanabilir.

**Referans:** Hologram masası ve ses/yüz tasarımı için jaredrhod'un açık kaynak JARVIS yığını
incelendi. Kod kopyalanmıyor, teknikler kendi kodumuzla yeniden yazılıyor:
[docs/referanslar/jaredrhod_jarvis_analizi.md](docs/referanslar/jaredrhod_jarvis_analizi.md)

---

## Faz 1: Mark I, Eller

| # | Ders | Durum | Pakete eklenen | Öğrenilen kavramlar |
|---|------|-------|----------------|---------------------|
| 1 | El kontrollü fare V1 | ✅ | - | El iskeleti (21 nokta), koordinat dönüşümü, PyAutoGUI |
| 2 | Fare V2: akışkanlık | ✅ | `kamera`, `el`, `filtreler`, `imlec`, `hud` | 1€ filtresi, thread'ler, gecikme analizi, histerezis |
| 3 | Jest merkezi ve olay yolu | ✅ | `jestler`, `olaylar` | Kural tabanlı sınıflandırma, kenar tetikleme, yayınla-abone ol |
| 4 | Medya ve ses kontrolü | ✅ | `ses` | Windows Core Audio (pycaw), sürekli ve ayrık kontrol |
| 5 | Güvenilir çimdik ve Fare V3 | ⏳ | `cimdik`, `ornekleyici` | Kontrast yasası, hayalet çimdik kapısı, hıza duyarlı bırakma, deneme süresi, 3D kıvrım açısı, kişiye özel eşik örnekleyici |
| 6 | Hologram masası I | ⏳ | `kopru` (WebSocket), `hologram/` | Python takipçisi → tarayıcı sahnesi (three.js), cam kartlar, tut-taşı, fırlatma fiziği, iki elle ölçekleme |
| 7 | Hologram masası II | ⏳ | `hologram/` | Pençe ile uzaktan çekme, alkışla temizleme, 3D model döndürme ve patlatma, JARVIS halkası (idle / listening / thinking / speaking) |
| 8 | Kaydırma, pencere yönetimi ve hava çizimi | ⏳ | `kisayollar`, `modlar` | İki parmakla scroll, masaüstü değiştirme, mod makinesi, parmakla tuval |

## Faz 2: Mark II, Yüz

| # | Ders | Öğrenilen kavramlar |
|---|------|---------------------|
| 9 | Yüz iskeleti ve baş pozu | Face Landmarker (478 nokta), `solvePnP` ile baş yönü, baş hareketiyle imleç |
| 10 | Göz kırpma ile tıklama | Göz açıklık oranı (EAR), yorgunluk ve uyuklama alarmı |
| 11 | Mimik komutları | 52 blendshape skoru: gülümseme, kaş kaldırma, ağız açma ile komut |

## Faz 3: Mark III, Kimlik (Kapı Bekçisi)

| # | Ders | Öğrenilen kavramlar |
|---|------|---------------------|
| 12 | Yüz tanıma | Yüz gömme vektörleri (embedding), kosinüs benzerliği, kayıt veritabanı |
| 13 | Canlılık testi | Fotoğrafla kandırmaya karşı "göz kırp, gülümse" doğrulaması (Faz 2 tekrar kullanılır) |
| 14 | "Hoş geldiniz efendim" | Yüzle kilit açma, kişiye özel jest ayarları |

## Faz 4: Mark IV, Ses ve Beyin (JARVIS çekirdeği)

| # | Ders | Öğrenilen kavramlar |
|---|------|---------------------|
| 15 | Bas-konuş ve konuşma tanıma | Tuşla açılan mikrofon, Türkçe konuşmayı yazıya çevirme (faster-whisper), "Jarvis" uyandırma kelimesi |
| 16 | Sesli yanıt | Türkçe metinden sese (Piper), cümle cümle akış, konuşurken araya girme, ses dalgası sinyali |
| 17 | Yapay zeka ajanı | Olay yolu = algı, `ses` / `imlec` / `medya` / hologram masası = araçlar. İzin listesi ve sesli onay. Kendi yapay zekan buraya takılır |
| 18 | Hafıza ve çok kipli soru-cevap | Markdown not kasası, "JARVIS, elimdeki ne?": kamera karesini görsel modele gönderme |

## Faz 5: Mark V, Dünya

| # | Ders | Öğrenilen kavramlar |
|---|------|---------------------|
| 19 | Nesne tespiti | YOLO ile nesne tanıma, nesneyle etkileşim |
| 20 | Vücut pozu | Pose Landmarker, tüm vücut jestleri, egzersiz sayacı |
| 21 | Tek uygulama | Tüm yetenekler eklenti olarak, sistem tepsisi, PyInstaller ile paketleme |

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
- [ ] Ders sonunda commit + push
