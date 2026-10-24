# Ders 13: Canlılık Testi

**Amaç:** Yüz tanımayı bir fotoğrafla kandırmayı engellemek. Telefonda gösterilen bir
fotoğraf, Ders 12'nin tanıma sistemine göre "sen"sin.

## Nasıl çalışıyor?

Rastgele sırayla 3 hareket istenir. Her biri 6 saniye içinde yapılmalı:

| Görev | Başarı koşulu |
|-------|---------------|
| Göz kırp | Ders 10'un algılayıcısı doğal ya da bilinçli bir kırpma görür |
| Gülümse | Gülümseme skoru > 0.6 **ve** görev başladığından beri bir an < 0.3 olmuş |
| Ağzını aç | `jawOpen` > 0.5 **ve** görev boyunca bir an < 0.15 olmuş |
| Başını sola / sağa çevir | Yaw, görev başındaki açıya göre 15°'den fazla değişti |

**Her görev bir değişim ister, bir durum değil.** Gülümseyen bir fotoğraf "gülümse"
görevini geçemez: görev başında nötr olup sonra gülümsemek gerekir. Baş çevirme de mutlak
açıyla değil, görev başındaki açıya göre ölçülür; yana dönük bir fotoğraf geçemez.
Görevler rastgele sırada olduğu için önceden kaydedilmiş bir video da işe yaramaz.
Yüz 1 saniyeden uzun kaybolursa test başarısız olur.

## Testler

- Birim: Sabit dört yüz (nötr, **gülümseyen**, **ağzı açık**, **yana dönük**) beş farklı
  rastgele görev sırasıyla denenir; hepsi kalır. Hareket eden sentetik bir yüz 5 görevi de geçer.
- Uçtan uca: Gerçek bir yüz fotoğrafıyla çalıştırılınca sonuç **KALDI**.

## Çalıştırma

```bash
python dersler/ders_13_canlilik/canlilik_testi.py
python dersler/ders_13_canlilik/canlilik_testi.py --kaynak fotograf.jpg   # fotoğrafla dene
```

**Boşluk** yeni test başlatır.

## Sınırlar

Bu, "meydan okuma-yanıt" (challenge-response) türünde aktif bir testtir. Gerçek zamanlı
yüz canlandırma (deepfake) ya da 3D maske gibi gelişmiş saldırılara karşı tek başına yeterli
değildir; bunlar için derinlik kamerası (Windows Hello'nun kızılötesi kamerası gibi) ya da
pasif sahtecilik tespit modelleri gerekir.

## CV maddesi

> Yüz tanımaya karşı fotoğraf saldırılarını engelleyen, rastgele sıralı ve durum yerine
> değişim ölçen bir canlılık testi tasarladım; sabit fotoğraf varyasyonlarıyla (gülümseyen,
> yana dönük) testi geçemediğini doğruladım.
