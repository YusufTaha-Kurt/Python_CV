# Ders 8: Kontrol Merkezi ve Hava Çizimi

**Amaç:** Önceki derslerde ayrı ayrı yazılan yetenekleri tek uygulamada birleştirmek ve
aralarında el hareketiyle geçiş yapmak. Ayrıca OpenCV Ders 3'te yarım kalan paint
uygulamasını elle çalışır hale getirmek.

## Kontrol Merkezi

```bash
python dersler/ders_08_kontrol_merkezi/kontrol_merkezi.py
python dersler/ders_08_kontrol_merkezi/kontrol_merkezi.py --sadece-izle
```

**İki elin iki görevi var:** kontrol eli (varsayılan sağ) işi yapar, diğer el modu seçer.
Mod eli 1, 2 ya da 3 düz parmak gösterip 0.6 sn tutarsa o moda geçilir. Yumruk ve açık
avuç modu değiştirmez; dinlenen bir el yanlışlıkla mod değiştirmesin diye. Pencerede
**1 / 2 / 3** tuşları da çalışır.

| Mod | Kontrol eli |
|-----|-------------|
| **1 FARE** | Ders 5: OK çimdiği tık / çift tık / sürükle, başparmak + orta parmak sağ tık |
| **2 MEDYA** | Ders 4: L işareti ses seviyesi, başparmak yukarı oynat/duraklat, avuçla parça değiştir, rock sessiz |
| **3 PENCERE** | Zafer + yukarı / aşağı: sayfayı kaydır · avuçla sola / sağa: sanal masaüstü değiştir · başparmak yukarı: pencereyi büyüt · rock: küçült · L işareti: Alt+Tab |

Her modda kontrol eliyle **yumruk (0.5 sn)** uyku modunu açar / kapatır.

### Nasıl birleşti?

Her yetenek pakette kendi sınıfında yaşıyor ve **aynı olay yolunu** dinliyor:

```
JestYayincisi --jest.degisti / jest.kaydirma--> OlayYolu --> MedyaKontrol   (aktif: MEDYA modunda)
                                                         --> PencereKontrol (aktif: PENCERE modunda)
                                                         --> uyku modu
ElFaresi.isle()  <- sadece FARE modunda her kare
ModSecici        <- mod eli
```

Mod değişince yeteneğin `aktif` bayrağı değişir; jest algılama koduna dokunulmaz. Fare
modundan çıkarken basılı tuş bırakılır (`ElFaresi.sifirla`).

### Kaydırma

Zafer pozundayken elin dikey hareketi (el boyuna oranla) fare tekerleği birimlerine çevrilir.
Hareket 1€ filtresinden geçer, küçük titremeler ölü bölgede yutulur ve kaydırma tek tek
çentik yerine 10'ar birimlik adımlarla gönderilir: modern uygulamalarda pürüzsüz kayar.
Yön dokunmatik ekran gibidir: elini aşağı indirince içerik de aşağı iner.

## Hava Çizimi

```bash
python dersler/ders_08_kontrol_merkezi/hava_cizimi.py
```

| Hareket | Sonuç |
|---------|-------|
| Sadece işaret parmağı düz | Çiz |
| İşaret + orta (zafer) | Kalemi kaldır ve gezin; parmağı üstteki palete götürerek renk / silgi seç |
| Açık avuç (0.8 sn) | Tuvali temizle |

Tuşlar: **s** kaydet (`cizimler/`), **+ / -** kalınlık, **c** temizle.

"Düz parmak" için uç-bilek mesafesi yetmez: kanca gibi kıvrılmış bir parmağın ucu da
bileğe uzak kalabilir (Ders 7'de testlerle bulundu). `jestler.duz_parmak_sayisi` ayrıca
parmağın kıvrım açısına bakar.

## Bu derste bulunan hata

Testler, Ders 4'ten beri var olan bir hatayı yakaladı: `OlayYolu.yayinla(ad, **veri)`
imzası yüzünden `yayinla("medya.eylem", ad=...)` çağrısı `TypeError` veriyordu. Olay
yolu abonelerin hatalarını yakalayıp sadece yazdırdığı için uygulama çökmedi, ama medya
tuşu hiç basılmıyordu. Düzeltme: olay adı artık sadece konumla verilebiliyor
(`def yayinla(self, ad, /, **veri)`) ve bunun için bir regresyon testi var.

## CV maddesi

> Jest tabanlı yetenekleri (fare, medya, pencere yönetimi) olay yolu üzerinden haberleşen
> bağımsız modüller olarak tek bir uygulamada birleştirdim; iki elli bir mod seçici ve
> dokunmatik hissi veren pürüzsüz kaydırma ekledim. Birim testleri, olay yolunun sessizce
> yuttuğu eski bir hatayı ortaya çıkardı.
