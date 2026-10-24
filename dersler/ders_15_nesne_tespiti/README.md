# Ders 15: Nesne Tespiti ve Takibi

**Amaç:** Kameradaki nesneleri bulmak, her birine kalıcı bir kimlik vermek ve parmakla
gösterilen nesneyi anlamak.

## Tespit

MediaPipe Object Detector + **EfficientDet-Lite0** (COCO'nun 80 sınıfı: insan, fincan,
şişe, telefon, kitap, dizüstü, makas, ...). Model 7 MB, CPU'da gerçek zamanlı çalışır.
`--siniflar cup,bottle,cell phone` ile sadece istenen sınıflar aranır.

## Takip: dedektör "kim kimdir" bilmez

Dedektör her kareyi bağımsız işler; önceki karedeki fincanın bu karedeki hangi kutu
olduğunu bilmez. `IoUTakipci` (SORT'un sadeleştirilmiş hali) her nesneye kalıcı bir ID verir:

1. **Tahmin:** Her iz son hızıyla bir kare ileri taşınır.
2. **Eşleştirme:** Aynı sınıftaki iz-tespit çiftleri IoU'ya (kesişim / birleşim) göre açgözlü eşleştirilir.
3. **Yaşatma:** Dedektör bir nesneyi birkaç kare kaçırırsa iz tahminle ilerletilir; nesne
   geri gelince ID değişmez (testli: 5 kare kayıp sonrası aynı ID).
4. **Kesinleşme:** Yeni iz ancak 3 kare üst üste görülünce gösterilir; tek karelik sahte
   tespitler elenir.

Gerçek bir webcam videosunda kişi 10 saniye boyunca aynı ID ile takip edildi; kapüşon ipi
kısa bir süre "kravat" sanıldı, kayboluşu `nesne.kayboldu` olayıyla bildirildi.

## Parmakla işaret

Sadece işaret parmağı açıkken (`Jest.ISARET`):
1. Parmak ucu bir kutunun içindeyse o nesne (birden çoksa en küçüğü).
2. Değilse işaret parmağının kökünden ucuna uzanan **ışının** ilk çarptığı kutu
   (ışın-kutu kesişimi, "slab" yöntemi).

## Olaylar

`nesne.goruldu`, `nesne.kayboldu`, `nesne.isaretlendi` (hepsi `id` ve Türkçe `nesne` adıyla).

## Çalıştırma

```bash
python dersler/ders_15_nesne_tespiti/nesne_tespiti.py
python dersler/ders_15_nesne_tespiti/nesne_tespiti.py --siniflar cup,bottle,cell phone,book --esik 0.5
```

## CV maddesi

> EfficientDet ile nesne tespitini, sabit hız modelli IoU tabanlı çoklu nesne takibiyle
> (SORT benzeri) birleştirdim; el iskeletinden ışın izleyerek kullanıcının parmağıyla gösterdiği
> nesneyi buldum.
