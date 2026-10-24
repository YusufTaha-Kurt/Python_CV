# Yol Haritası

Bu repo, bilgisayarlı görü ile bilgisayar kontrolünü **ders ders** öğreten ve sonunda tek bir
servis olarak 7/24 çalışabilen bir modül üretir. **17 dersin hepsi tamamlandı.** Asistan, ses ve hafıza gibi konular bu reponun
kapsamında değildir; buradaki `goru` paketi ayrı bir uygulamaya özellik olarak eklenmek üzere
tasarlanır (bkz. Ders 17).

**İlke:** Görüntü katmanı sadece olay yayınlar, eylemi aboneler yapar. Her ders `goru/` paketine
yeniden kullanılabilir bir modül ekler ve kamera gerektirmeyen kısımlar test edilir.

---

## Faz 1: Eller

| # | Ders | Pakete eklenen | Öğrenilen kavramlar |
|---|------|----------------|---------------------|
| 1 | El kontrollü fare V1 | - | El iskeleti (21 nokta), koordinat dönüşümü, PyAutoGUI |
| 2 | Fare V2: akışkanlık | `kamera`, `el`, `filtreler`, `imlec`, `hud` | 1€ filtresi, thread'ler, gecikme analizi, histerezis |
| 3 | Jest merkezi ve olay yolu | `jestler`, `olaylar` | Kural tabanlı sınıflandırma, kenar tetikleme, yayınla-abone ol |
| 4 | Medya ve ses kontrolü | `ses`, `medya` | Windows Core Audio (pycaw), sürekli ve ayrık kontrol |
| 5 | Güvenilir çimdik ve Fare V3 | `cimdik`, `fare`, `ornekleyici` | Yanlış tetiklemeye karşı katmanlı çimdik, tıklama durum makinesi, veriyle eşik ayarı |
| 6 | Hologram masası I | `hologram`, `web` | Python takip + tarayıcıda 3D sahne (three.js), MJPEG ve SSE ile canlı yayın, tut-taşı, fırlatma fiziği, iki elle ölçek |
| 7 | Hologram masası II | `hologram` | Pençe ile uzaktan çekme, alkış, 3D model döndürme ve patlatma, piramit (Pepper's ghost) modu |
| 8 | Kontrol merkezi ve hava çizimi | `kisayollar`, `modlar` | İki parmakla kaydırma, sanal masaüstü ve pencere yönetimi, mod makinesi, parmakla çizim |

## Faz 2: Yüz

| # | Ders | Pakete eklenen | Öğrenilen kavramlar |
|---|------|----------------|---------------------|
| 9 | Yüz iskeleti ve baş pozu | `yuz`, `bas_pozu` | Face Landmarker (478 nokta), `solvePnP` ile baş yönü, bakarak tıklama |
| 10 | Göz kırpma ve yorgunluk | `goz` | Göz açıklık oranı (EAR), uyarlanır eşik, göz kırparak tıklama, PERCLOS ile yorgunluk alarmı |
| 11 | Mimik komutları | `mimik` | 52 ifade skoru (blendshape), nötr yüz kalibrasyonu, ifadeyle komut |

## Faz 3: Kimlik (Kapı Bekçisi)

| # | Ders | Pakete eklenen | Öğrenilen kavramlar |
|---|------|----------------|---------------------|
| 12 | Yüz tanıma | `kimlik` | YuNet ile yüz bulma, SFace gömme vektörleri, kosinüs benzerliği, kayıt veritabanı |
| 13 | Canlılık testi | `canlilik` | Fotoğrafla kandırmaya karşı rastgele hareket sorgusu (göz kırp, gülümse, başını çevir) |
| 14 | Kapı bekçisi | `kapi` | Tanıma + canlılık durum makinesi, uzaklaşınca Windows'u kilitleme, yabancı kaydı |

## Faz 4: Dünya

| # | Ders | Pakete eklenen | Öğrenilen kavramlar |
|---|------|----------------|---------------------|
| 15 | Nesne tespiti | `nesne`, `takip` | EfficientDet, IoU ile nesne takibi, parmakla işaret edilen nesneyi bulma |
| 16 | Vücut pozu | `poz`, `egzersiz` | Pose Landmarker, eklem açıları, tekrar sayacı, duruş bekçisi |

## Faz 5: Entegrasyon

| # | Ders | Pakete eklenen | Öğrenilen kavramlar |
|---|------|----------------|---------------------|
| 17 | 7/24 servis | `servis` | Tek kamera + eklenti yetenekler, enerji tasarrufu, kamera kopmasına dayanıklılık, yerel HTTP arayüzü (SSE), başka uygulamalara entegrasyon |

---

## Her dersin şablonu

```
dersler/ders_NN_konu/
  konu.py        Çalıştırılabilir ders (depo kökünden çalışır)
  README.md      Amaç, kavramlar, jest sözlüğü, ayarlar, CV maddesi
```

Kontrol listesi:
- [ ] Yeni yeniden kullanılabilir mantık `goru/` altına
- [ ] Kamera gerektirmeyen kısımlar için `tests/` altında birim testi
- [ ] Uçtan uca test (`tests/test_uctan_uca.py`)
- [ ] `--kaynak`, `--pencere-yok`, `--kare-limiti`, `--sadece-izle` destekleniyor
- [ ] Kök README'deki ders tablosu ve `baslat.py` güncellendi
- [ ] Ders sonunda commit + push
