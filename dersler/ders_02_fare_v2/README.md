# Ders 2: El Kontrollü Fare V2 (Akışkanlık)

**Amaç:** Ders 1'deki fareyi gerçekten günlük kullanılabilir hale getirmek. Takılmayı,
titremeyi ve yanlış tıklamaları ölçüp kök nedenlerini düzeltmek.

## Hata ayıklama hikâyesi: V1 neden takılıyordu?

1. **Asıl suçlu: PyAutoGUI.** `pyautogui.PAUSE` varsayılan olarak `0.1`'dir. Her `moveTo`
   ve `click` çağrısından sonra program 100 ms uyur. Döngü her karede `moveTo` çağırdığı
   için kamera 30 FPS verse bile sistem en fazla ~10 FPS çalışıyordu.
   Çözüm: `pyautogui.PAUSE = 0` ([imlec.py](../../jarvis_vision/imlec.py)).
2. **Kamera ve monitör hızı uyuşmuyor.** İmleç sadece kare geldiğinde (30 Hz) hareket
   edince 144 Hz monitörde basamaklı görünür. Çözüm: `ImlecSurucu` imleci ayrı bir
   thread'de 144 Hz'de hedefe doğru akıtır.
3. **Sabit yumuşatma ikilemi.** Faktör büyükse imleç hantal, küçükse titrek oluyordu.
   Çözüm: **1€ filtresi**. Bu filtre el yavaşken güçlü yumuşatma, hızlıyken az yumuşatma
   uygular ([filtreler.py](../../jarvis_vision/filtreler.py)).
4. **Tıklarken imleç kayıyordu.** İmleç başparmak ucundan alınıyordu ama çimdik yaparken
   başparmak hareket eder. Çözüm: imleç işaret parmağı kökünden (nokta 5) alınıyor ve
   çimdik başladığı anda imleç donduruluyor.
5. **Mesafeye bağlı tıklama.** Sabit 25 px eşiği, el kameradan uzaklaşınca hiç
   tetiklenmiyordu. Çözüm: mesafe el boyutuna bölünüyor ve **histerezis** uygulanıyor
   (başlama < 0.25, bırakma > 0.38).
6. **Uyku modu titriyordu.** Yumruk tutuldukça her saniye aç/kapa oluyordu. Çözüm:
   `JestKararlilastirici` ile kenar tetikleme. Jest sadece *değiştiğinde* bir kez sayılır.

## Ölçümler

| | V1 | V2 |
|---|---|---|
| Dururken titreme (std) | 0.0016 | 0.0008 |
| 1 ekran/sn harekette gecikme | %3.3 ekran | %1.7 ekran |
| İmleç güncelleme | ≤10 Hz | 144 Hz |

Kaynak: `tests/test_filtreler.py::test_v1_yumusatmasindan_hem_stabil_hem_hizli`

## Tıklama tasarımı: işi işletim sistemine bırak

V1 tek tık, çift tık ve sürüklemeyi zamanlayıcılarla kendisi ayırt etmeye çalışıyordu.
V2'de çimdik doğrudan **sol tuşu basılı tutmak** demek:

| Hareket | Sonuç |
|---------|-------|
| Kısa çimdik | Tek tık |
| İki hızlı çimdik | Çift tık (imleç 0.3 sn donuk kalır, ikinci tık aynı noktaya düşer) |
| Çimdik + elini hareket ettir | Sürükle-bırak |
| Başparmak + orta parmak çimdiği | Sağ tık |
| Yumruk (0.4 sn) | Uyku modu aç/kapa |

## Çalıştırma

```bash
python dersler/ders_02_fare_v2/fare_v2.py
python dersler/ders_02_fare_v2/fare_v2.py --sadece-izle   # fareyi oynatmadan dene
python dersler/ders_02_fare_v2/fare_v2.py --el sol --kamera 1
```

Ayarlar dosyanın başındadır: `FILTRE_MIN_KESIM` (dururken titreme), `FILTRE_BETA`
(hızlı harekette gecikme), `KUTU_ORANI` (çalışma alanı), `SURUKLEME_ESIGI`.

> Sağ/sol el ters algılanıyorsa `jarvis_vision/el.py` içindeki `AYNALI_TARAF` eşlemesini değiştir.

## CV maddesi

> MediaPipe tabanlı el kontrollü farede gecikmenin kök nedenini (PyAutoGUI'nin çağrı başına
> 100 ms bekleme süresi) tespit edip giderdim. 1€ filtresi ve 144 Hz'lik ayrı imleç thread'i
> ile titremeyi ve gecikmeyi yarıya indirdim.
