# Ders 12: Yüz Tanıma

**Amaç:** Kameradaki kişinin kim olduğunu bulmak.

## Nasıl çalışıyor?

1. **YuNet** (OpenCV Zoo, MIT) yüzü ve 5 noktasını (gözler, burun, ağız köşeleri) bulur.
2. Yüz bu noktalara göre **hizalanır** (göz çizgisi yatay, standart boyut).
3. **SFace** (OpenCV Zoo, Apache 2.0) hizalanmış yüzü 128 sayılık bir **gömme vektörüne** çevirir.
4. Vektör birim uzunluğa normalize edilir ve kayıtlı kişilerin örnekleriyle **kosinüs
   benzerliği** (iç çarpım) hesaplanır. Her kişinin en benzer örneği alınır.

İkisi de OpenCV'nin içinde (`cv2.FaceDetectorYN`, `cv2.FaceRecognizerSF`); ek paket gerekmez.

## Ölçümler

| Karşılaştırma | Kosinüs benzerliği |
|---------------|--------------------|
| Aynı kişi: aynalı / karanlık / küçültülmüş / 10° döndürülmüş | 0.95 - 0.97 |
| Aynı kişi, gerçek webcam videosunun farklı kareleri (eller yüzde, farklı açılar) | en düşük 0.58 |
| Farklı kişiler | 0.01 - 0.24 |

SFace'in önerdiği eşik 0.363'tür. Kapı bekçisinde yanlış kabul daha pahalı olduğu için
**0.40** kullanılıyor (`--esik` ile değiştirilebilir); iki dağılım arasında yine geniş bir boşluk var.

## Kayıt: çeşitlilik

Birbirinin aynısı 12 örnek, tek bir örnekten daha iyi değildir. `KayitToplayici` yeni bir
örneği ancak mevcutların hepsine benzerliği 0.93'ün altındaysa ekler. Kayıt sırasında başını
yavaşça çevirdikçe farklı açılar birikir. Küçük (< 80 px) ve düşük güvenli yüzler atlanır.

## Kullanım

```bash
python dersler/ders_12_yuz_tanima/yuz_tanima.py --kaydet Yusuf   # kayıt
python dersler/ders_12_yuz_tanima/yuz_tanima.py                  # tanıma
python dersler/ders_12_yuz_tanima/yuz_tanima.py --listele
python dersler/ders_12_yuz_tanima/yuz_tanima.py --sil Yusuf
```

## Gizlilik

Yüz vektörleri **biyometrik veridir**. Sadece bu bilgisayarda, depo kökündeki `kimlikler/`
klasöründe `.npy` dosyaları olarak tutulur; klasör `.gitignore`'dadır. İsimler dosya adına
çevrilirken temizlenir (`../` gibi kaçışlar engellenir, testli).

## Testler

`tests/test_uctan_uca.py`, tek bir fotoğrafın döndürülmüş / ölçeklenmiş hallerinden oluşan
bir videoyla gerçek modellerle kayıt yapar, aynı kişiyi tanır ve başka bir kişiyi reddeder.

## CV maddesi

> OpenCV YuNet + SFace ile yüz tanıma sistemi kurdum; benzerlik dağılımlarını ölçerek eşiği
> güvenlik için ayarladım, kayıt sırasında çeşitlilik zorunlu örnek toplama ve yerel,
> gizlilik odaklı bir kimlik veritabanı tasarladım.
