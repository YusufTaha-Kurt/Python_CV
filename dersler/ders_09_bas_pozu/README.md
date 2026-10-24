# Ders 9: Yüz İskeleti ve Baş Pozu

**Amaç:** Yüzün 478 noktasını ve başın uzaydaki yönünü (yaw / pitch / roll) bulmak, sonra
bununla ellere hiç ihtiyaç duymayan bir fare yapmak.

## Baş pozu: iki yöntem

| | Dönüşüm matrisi (varsayılan) | solvePnP (klasik) |
|---|---|---|
| Nasıl | MediaPipe kanonik 3D yüz modelini her kareye oturtur ve 4x4 dönüşüm matrisini verir | 6 yüz noktası (burun, çene, göz ve ağız köşeleri) genel bir 3D yüz modeliyle eşleştirilir, kamera pozu `cv2.solvePnP` ile çözülür |
| Kamera bilgisi | Gerekmez | Odak uzaklığı gerekir (kalibrasyon yoksa ~ görüntü genişliği varsayılır) |
| Ölçülen (örnek yüz) | yaw 6.6°, pitch -17.6°, roll -5.2° | yaw 9.3°, pitch **-35.2°**, roll -6.8° |

İki yöntem yaw ve roll'da aynı işareti ve benzer büyüklüğü verir. solvePnP'nin pitch'i
sistematik olarak büyüktür: genel 3D modelin burun derinliği gerçek yüze uymaz ve odak
uzaklığı tahminidir. Bu yüzden matris varsayılan, ve başla imleç her durumda **nötr poz
kalibrasyonu** kullanır: sapma sabit olduğu sürece kalibrasyonla sıfırlanır.

**Doğrulama:** Görüntü aynalanınca yaw ve roll işaret değiştirir; görüntü 15° saat yönüne
döndürülünce roll tam +15° değişir. `tests/test_yuz.py` ayrıca bilinen bir pozla
projekte edilmiş noktalardan solvePnP'nin 15°'lik yaw'u geri çözdüğünü test eder.

İşaret kuralı aynalanmış görüntüye göredir: `yaw > 0` yüz ekranın sağına dönük,
`pitch > 0` yukarı bakıyor, `roll > 0` baş ekranın sağına yatık.

## Başla imleç

```bash
python dersler/ders_09_bas_pozu/bas_fare.py --sadece-izle   # önce böyle dene
python dersler/ders_09_bas_pozu/bas_fare.py
```

1. İlk 1.5 sn ekranın ortasına bak (nötr poz kalibrasyonu, **c** ile tekrarlanır).
2. Başını sağa / sola / yukarı / aşağı çevir: ±18° yaw ve ±11° pitch tüm ekranı kaplar.
3. **Bakarak tıklama:** İmleci 1 sn bir yerde tut, tıklar. Bu, elini kullanamayanlar için
   klasik bir erişilebilirlik tekniğidir (dwell click). **t** ile aç / kapa.

Açılar 1€ filtresinden geçer, imleç Ders 2'deki 144 Hz sürücüyle akar.

## CV maddesi

> MediaPipe yüz iskeletinden baş pozunu iki yöntemle (dönüşüm matrisi ve solvePnP) hesaplayıp
> karşılaştırdım; PnP'nin genel yüz modelinden kaynaklanan pitch sapmasını ölçtüm ve nötr
> poz kalibrasyonuyla giderdim. Bununla eller serbest, bakarak tıklayan bir fare yaptım.
