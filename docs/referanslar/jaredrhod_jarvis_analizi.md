# Referans Analizi: jaredrhod JARVIS Yığını

**Kaynak video:** [My Iron Man Jarvis Interface](https://www.youtube.com/watch?v=cV02finVi4o), Jared Rhodenizer ([@jaredrhod](https://www.youtube.com/@jaredrhod))
**İncelenen sürümler (2026-08-30):**

| Repo | Rol | Commit | Lisans | Teknoloji |
|------|-----|--------|--------|-----------|
| [barehands](https://github.com/jaredrhod/barehands) | Eller (hologram masası) | `eb23bed` | AGPL-3.0 | Tarayıcı: MediaPipe JS + three.js, stdlib Python sunucu |
| [backtalk](https://github.com/jaredrhod/backtalk) | Ağız ve kulak (ses) | `84b3a6c` | AGPL-3.0 | faster-whisper, Kokoro TTS, Claude Agent SDK |
| [ai-visualizer](https://github.com/jaredrhod/ai-visualizer) | Yüz | `6921e1d` | AGPL-3.0 | Tarayıcı sayfaları, stdlib Python sunucu |
| [ai-memory-vault](https://github.com/jaredrhod/ai-memory-vault) | Zihin (hafıza) | `659bba9` | CC BY-SA 4.0 | Obsidian kasası + CLAUDE.md şablonları |

Yerel kopyalar: `goruntu_isleme/Referanslar/jaredrhod/` (bu reponun dışında tutuluyor).

## Lisans kararı

AGPL kodu bu repoya **kopyalanmıyor**. Kopyalansaydı tüm reponun AGPL olması gerekirdi.
Bunun yerine:

1. **Fikirler ve teknikler** aşağıda belgelenip kendi kodumuzla, kendi testlerimizle yeniden
   yazılıyor. Fikirler telif konusu değildir, ama kaynak her zaman belirtilir.
2. **Birlikte çalışabilirlik:** Onun bileşenleri ayrı süreç olarak, olduğu gibi çalıştırılabilir.
   `jarvis_vision` ise aynı dosya/HTTP protokolünü konuşur (bkz. "Sinyal yolu"). Ayrı
   programlar arasında protokol uyumu lisans bulaşması yaratmaz.

## Mimari: Zihin, ağız, yüz, eller

Bileşenler birbirini import etmez. Hepsi **küçük dosyalar ve localhost HTTP** ile konuşur.
Bizim `OlayYolu` + `olaylar.jsonl` tasarımımızla aynı felsefe: algı katmanı yayınlar, diğerleri dinler.

### Sinyal yolu (ses ↔ yüz)

```
.voice_state        idle | listening | thinking | speaking
.voice_waveform     {"ts": ..., "samples": [64 float]}   (konuşurken)
.voice_loading_pid  düşünme sesi çalarken var olur
.voice_alert        boş değilse yüz kırmızıya döner
```

### barehands protokolü

| Uç nokta | İş |
|----------|-----|
| `POST /state` | Takip sayfasının ~45 Hz kalp atışı. Yanıt, kuyruktaki komutları taşır (komut kanalı) |
| `POST /cmd` | Yapay zekadan masaya komut. İzin listesi: `add_img, add_card, clear, reset, hand, give, yank, hover, scroll_note, widget, explode, assemble, present` |
| `GET /orb` | Halkanın durumu: `state/state`, `state/mood.json`, `state/wave.json` dosyalarından |
| `GET /tree`, `/note` | Not klasörü (sadece `.md`, klasör dışına çıkış engelli) |

Güvenlik dersi: komutlar **izin listesiyle** sınırlı, medya dosyaları sadece `media/` klasöründen
yüklenebiliyor ("airlock"), yollar önce çözümlenip sonra klasör içinde mi diye kontrol ediliyor.
Bir yapay zekaya araç verirken aynı ilke bizde de uygulanacak (Ders 17).

Bayat durum koruması: `thinking` yazıp çöken bir süreç halkayı sonsuza kadar "düşünüyor"da
bırakmasın diye, dosya `state_timeout_s` saniyeden eskiyse `idle` sayılıyor.

## barehands'ten öğrenilen jest teknikleri

Haftalarca gerçek el üzerinde ayarlanmış eşikler. Bizdeki karşılıkları ve planlanan ders:

| # | Teknik | Nasıl çalışıyor | Bizde | Ders |
|---|--------|-----------------|-------|------|
| 1 | Tespit ve takip güvenini ayırma | Yeni el bulmak için 0.7 (kalabalık arka planda hayalet el çıkmasın), var olan eli tutmak için 0.5 (hızlı harekette bulanık el düşmesin) | 0.6 / 0.6 / 0.5 | 5 |
| 2 | Kontrast yasası (çimdik mi yumruk mu?) | Her parmak için `uç-bilek / kök-bilek` oranı. Gerçek çimdikte işaret kıvrılır, diğer üç parmak dışarıda kalır: `ort(orta, yüzük, serçe) - işaret > 0.18` ve `ort > 1.30`. Profil açısında başparmak ölçütü: `avuç en-boy < 2` ve `bas_ucu-yüzük_kökü / el > 0.95` | Yok (çimdik sırasında yumruk kontrolü kapatılıyor) | 5 |
| 3 | İki kare onayı + EMA | İmza iki ardışık karede görülürse hemen, ya da `ema = 0.7·ema + 0.3·imza` 0.55'i geçerse çimdik başlar. Tek şanslı kare yetmez | Histerezis var, onay yok | 5 |
| 4 | Hıza duyarlı bırakma | Hız 800 px/s üstündeyse bırakma eşiği 0.55'ten 0.70'e çıkar ve iki kare art arda açık görülmelidir. Bulanık parmaklar sahte bırakma üretmez | Yok | 5 |
| 5 | Doğum hızı kapısı | 900 px/s üstünde "doğan" çimdik hayalettir, bir şey kavrayamaz. El 500 px/s altına yavaşlarsa kendini iyileştirir | Yok | 5 |
| 6 | Deneme süresi | Yeni çimdik ilk 400 ms boyunca imzasını korumalı. 4 kare imzasız kalırsa sessizce düşer (eli yumruk yaparken geçilen sahte OK işareti) | Yok | 5 |
| 7 | İmkânsız geometri | `avuç uzunluğu / avuç genişliği > 6` ise takip modeli uyduruyordur, o el hiçbir şey tetikleyemez | Yok | 5 |
| 8 | Kıvrım = açı, mesafe değil | `(kök→PIP)·(DIP→uç)` birim vektör nokta çarpımı, 3D. Düz parmak ≈ +0.9, kanca < 0.35. Kameraya doğru uzanan parmakta mesafeler yalan söyler, açılar söylemez | Mesafe tabanlı | 5 |
| 9 | Kişiye özel eşik örnekleyici | Pozu 4 sn tut, her ölçüm için min/medyan/max yazdır, eşiği "kanyonun ortasından" kes | Yok | 5 |
| 10 | İmleç = başparmak/işaret orta noktası | Çimdikte iki uç birbirine doğru gelir, orta nokta sabit kalır | İşaret kökü (nokta 5) | 5 |
| 11 | Fırlatma | Son 10 örnekteki tepe hız, bırakma anında nesneye aktarılır, sürtünmeyle yavaşlar | Yok | 6 |
| 12 | İki el = ölçek | İki el aynı nesneyi tutarsa eller arası mesafe oranı = ölçek | Yok | 6 |
| 13 | Pençe ile çekme | Geçiş yasası (son 0.9 sn içinde açık el), 14 kare pençe pozu, nişan = başparmak-işaret çizgisinin normali, %25'lik dar koni, hedef 2 sn titrer, ağzın hızla kapanması (280 ms içinde 0.22 düşüş) nesneyi ele çeker | Yok | 7 |
| 14 | Alkış | İki avuç dik ve birbirine yaklaşıyorsa masayı temizler | Yok | 7 |
| 15 | Yapay zekanın gözü | `board-state` komutu masada ne olduğunu yazdırır, yapay zeka konuşmadan önce bakar | `olaylar.jsonl` | 17 |

## Ses ve yüz notları (Faz 4 için)

- **Konuşma tanıma:** faster-whisper (yerel, ücretsiz). Türkçe destekler.
- **Ses:** Kokoro **Türkçe desteklemiyor** (en, es, fr, hi, it, ja, pt, zh). Türkçe için Piper
  (`tr_TR` sesleri) ya da ElevenLabs düşünülmeli.
- **Bas-konuş:** Mikrofon sadece tuş basılıyken açık. Böylece hoparlörü duymaz, kulaklık gerekmez.
  Tuşa basmak konuşmayı keser.
- **Cümle cümle konuşma:** Yanıt üretilirken her cümle hazır olur olmaz seslendirilir, ilk ses ~1-2 sn.
- **Sesli izin:** Gerçek bir eylemden önce sesli onay ister. Sadece okuma işlemleri sormadan geçer.
- **Hafıza:** Notlar modelin dışında, Markdown klasöründe. Görev başına "hangi notları oku" listesi
  ("AI Priming").
