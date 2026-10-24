# Ders 16: Vücut Pozu

**Amaç:** Tüm vücudu izlemek: egzersiz tekrarlarını saymak, masa başında duruşu
gözetlemek ve tüm vücutla jest yapmak.

MediaPipe **Pose Landmarker** (lite model, 5.8 MB) her kare 33 vücut noktası ve her nokta
için bir görünürlük skoru verir.

## Egzersiz sayacı

| Egzersiz | Eklem | Aşağı | Yukarı |
|----------|-------|-------|--------|
| `squat` | Kalça - diz - ayak bileği | < 100° | > 160° |
| `biceps` | Omuz - dirsek - bilek | < 50° | > 150° |
| `sinav` | Omuz - dirsek - bilek | < 90° | > 155° |

- Açı, **daha iyi görünen taraftan** ölçülür (görünürlük < 0.5 olan eklemler kullanılmaz).
- **Histerezis:** Tekrar, açı alt eşiğin altına inip sonra üst eşiğin üstüne çıkınca sayılır.
  Tek bir eşik etrafındaki titreme çift saymaz (testli).

## Duruş bekçisi

Masa başındaki webcam kişiyi **önden** görür; boynun öne eğilmesi doğrudan görünmez. Ama
kambur oturunca baş omuzlara yaklaşır:

```
oran = (omuz ortası y - burun y) / omuz genişliği
```

İlk 3 saniyede dik oturuş kalibre edilir. Oran tabanın %80'inin altına **10 saniye boyunca**
inerse "dik otur" uyarısı verilir (dakikada en fazla bir kez). Omuz çizgisi yataydan 8°'den
fazla saparsa (yana yaslanma) ayrıca uyarılır. 7/24 serviste (Ders 17) bu bir yetenek olarak çalışır.

## Vücut jestleri

- **Eller yukarı:** İki bilek de burnun üstünde.
- **T pozu:** Bilekler omuz hizasında ve aralarındaki mesafe omuz genişliğinin 2.5 katından fazla.

Jest 0.5 sn tutulunca bir kez bildirilir (`vucut.jest` olayı).

## Çalıştırma

```bash
python dersler/ders_16_vucut_pozu/vucut_pozu.py
python dersler/ders_16_vucut_pozu/vucut_pozu.py --egzersiz biceps --alarm
```

**c** duruşu yeniden kalibre eder, **r** sayacı sıfırlar.

## CV maddesi

> Vücut pozundan eklem açısıyla histerezisli egzersiz tekrar sayacı ve önden bakan bir
> webcam için kalibrasyonlu bir duruş bekçisi geliştirdim.
