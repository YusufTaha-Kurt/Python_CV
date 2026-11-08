# Ders 1: El Kontrollü Fare V1

**Amaç:** Standart bir web kamerasıyla fareyi sadece el hareketleriyle yönetmek. Bu ilk
çalışan sürüm. Ders 2 bu sürümün sorunlarını ölçüp tek tek düzeltir.

## Ne yapar?

| Hareket | Sonuç |
|---------|-------|
| Başparmağı mor kutu içinde gezdirmek | İmleç ekranda aynı oranda gezer |
| Başparmak + işaret ucu birleşir | Tek tık |
| 0.45 sn içinde ikinci çimdik | Basılı tut / sürükle (çok kısa tutulursa çift tık) |
| Yumruk | Uyku modu aç / kapa |

## Nasıl çalışır?

1. **El iskeleti.** MediaPipe her karede elin 21 noktasını verir ([goru/el.py](../../goru/el.py)).
   Kullanılanlar: başparmak ucu (4), işaret ucu (8) ve yumruk testi için bilek (0) ile parmak boğumları.
2. **Sanal çalışma alanı.** Kameranın kenarlarından 100 px içerideki kutu bütün ekrana oranlanır.
   Böylece ekranın köşelerine ulaşmak için kolu uzatmak gerekmez.
3. **Yumuşatma.** İmleç her karede hedefe kalan yolun yarısı kadar gider:
   `yeni = onceki + (hedef - onceki) / 2`
4. **Tıklama.** İki parmak ucu arasındaki mesafe 25 pikselin altına inince tıklanır.
5. **Uyku modu.** Dört parmağın ucu bileğe, alt boğumundan daha yakınsa el yumruktur.

## Bilinen sorunlar (Ders 2'de çözülüyor)

Fare mantığı bilerek ilk yazıldığı gibi bırakıldı. Kamera, el takibi ve ekran çizimi ise
diğer derslerle aynı `goru` altyapısından gelir. Yani iki ders aynı görüntüyü aynı şekilde
işler, fark sadece fare mantığındadır.

> İlk sürümde PyAutoGUI her çağrıdan sonra 0.1 sn uyuyordu ve program ~10 FPS'e sabitleniyordu.
> Bu bekleme artık kapalı, ders kameranın verebildiği en yüksek hızda çalışır. Sorunun nasıl
> bulunduğu Ders 2'de anlatılıyor.

| Sorun | Ders 2'deki çözüm |
|-------|-------------------|
| İmleç sadece kare geldiğinde (≤30 Hz) hareket ediyor, 144 Hz monitörde basamaklı | Ayrı thread'de 144 Hz imleç sürücüsü |
| Sabit yumuşatma: ya hantal ya titrek | Hıza duyarlı 1€ filtresi |
| İmleç başparmak ucundan alınıyor, çimdikte kayıyor | İşaret parmağı kökü + çimdikte imleci dondurma |
| Sabit 25 px eşik, el uzaklaşınca tıklamıyor | El boyutuna oranlı eşik + histerezis |
| Tek / çift tık zamanlayıcılarla elle ayırt ediliyor | Çimdik = sol tuş basılı, gerisini işletim sistemi ayırt eder |
| Yumruk tutuldukça uyku modu her saniye aç / kapa | Kenar tetikleme: jest sadece değiştiğinde sayılır |

## Çalıştırma

```bash
python baslat.py 1 --sadece-izle                          # fareye dokunmadan dene
python dersler/ders_01_fare_v1/fare_v1.py
python dersler/ders_01_fare_v1/fare_v1.py --el sol --kaynak 1
```

Ayarlar dosyanın başındadır: `KUTU_KENAR_BOSLUGU`, `YUMUSATMA_FAKTORU`, `TIKLAMA_ESIGI_PX`.
