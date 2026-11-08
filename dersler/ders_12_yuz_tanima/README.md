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

## Kayıt: adım adım farklı açılar

Birbirinin aynısı 12 örnek, tek bir örnekten daha iyi değildir. Tanıma, kayıtta görülmüş
açılara yakın açılarda güvenilirdir. Kayıt bu yüzden beş adımda yönlendirilir (`YonluKayit`).

| Adım | Ekranda yazan | Örnek |
|------|---------------|-------|
| 1 | Kameraya düz bak | 3 |
| 2 | Başını yavaşça SOLA çevir | 2 |
| 3 | Başını yavaşça SAĞA çevir | 2 |
| 4 | Başını hafifçe YUKARI kaldır | 2 |
| 5 | Başını hafifçe AŞAĞI indir | 2 |

Baş yönü YuNet'in 5 noktasından kabaca hesaplanır. Burnun iki gözün ortasından yana kayması
yatay, göz çizgisi ile ağız arasındaki yeri dikey yönü verir. İlk adımdaki düz bakış taban
alınır. Sonraki adımlarda örnek ancak baş istenen yöne yeterince döndüğünde alınır.

Bir açı 8 saniyede yakalanamazsa (kamera açısı, gözlük) o adımda açıya bakılmadan örnek alınır.
Kayıt hiçbir adımda takılı kalmaz. Küçük (80 px altı) yüzler ve birebir aynı kareler atlanır.

İlk sürümde yön söylenmiyordu. Birbirine benzeyen kareler sessizce atlandığı için kayıt
ilerlemiyor ve neyin yanlış gittiği anlaşılmıyordu.

## Kullanım

En kolayı menüden.

```bash
python baslat.py 12
```

| Seçim | Komut | Ne yapar |
|-------|-------|----------|
| 1 Tanı | *(seçeneksiz)* | Kameradaki yüzü kayıtlı kişilerle karşılaştırır |
| 2 Kaydol | `--kaydet İSİM` | Yeni kişi kaydeder. İsim kayıtlıysa eski örneklere yenilerini ekler. |
| 3 Yeniden kaydol | `--yeniden İSİM` | Eski kaydı silip baştan kaydeder |
| 4 Listele | `--listele` | Kayıtlı kişileri ve örnek sayılarını gösterir |
| 5 Sil | `--sil İSİM` | Kişinin kaydını siler |

Kaydın sonucu beğenilmezse (tanıma eşiğe yakın kalıyorsa) "Yeniden kaydol" ile baştan
yapılabilir. Farklı ışıkta "Kaydol" ile örnek eklemek de tanımayı güçlendirir.

```bash
python dersler/ders_12_yuz_tanima/yuz_tanima.py --kaydet Yusuf
python dersler/ders_12_yuz_tanima/yuz_tanima.py --yeniden Yusuf
python dersler/ders_12_yuz_tanima/yuz_tanima.py
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
