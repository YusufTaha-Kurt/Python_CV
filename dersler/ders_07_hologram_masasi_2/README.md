# Ders 7: Hologram Masası II

**Amaç:** Ders 6'nın masasına uzaktan etkileşim ve iki elli jestler eklemek, ileride
yapılacak fiziksel hologram için piramit görünümü hazırlamak.

## Pençe ile uzaktan çekme

1. Avucunu aç.
2. **Pençe yap:** işaret, orta ve yüzük parmakları kanca gibi kıvır, serçe düz kalsın,
   başparmakla işaret arası geniş olsun.
3. Pençenin ağzıyla uzaktaki bir nesneye **nişan al**. Nesne titremeye başlar ve titreme artar.
4. **2 saniye** sonra pençeyi hızla kapat: nesne eline uçar.
5. Avucunu açınca bırakırsın (hızla açarsan fırlatırsın).

### Neden bu kadar kural?

Pençe, gevşek duran bir elin doğal şekline çok benzer. Sahte tetiklemeyi önleyen kurallar:

| Kural | Neyi engeller |
|-------|---------------|
| **Geçiş yasası:** Pençe son 0.9 sn içinde açık bir elden oluşmalı | Masada gevşekçe duran kıvrık el |
| **Kıvrım açıyla ölçülür:** `(kök→PIP)·(DIP→uç)` 3D nokta çarpımı | Kameraya doğru uzanan düz parmakların kısa görünüp "kıvrık" sanılması |
| **Açık el = düz parmaklar:** uzunluk VE düzlük | Kanca gibi kıvrık parmak ucu bileğe uzak kaldığı için "açık" sanılması (testlerle bulundu) |
| **Poz 14 kare tutulmalı**, giriş eşikleri sıkı / korunma eşikleri gevşek | Bir anlık şans eseri poz, poz sınırında titreme |
| **Dar nişan konisi:** ileri mesafenin %25'i kadar sapma | Yanlış nesneye kilitlenme |
| **2 sn gerilim kuralı:** erken kapanırsa çekmez | Kazara çekme |
| **Kapanma = çöküş hızı:** ağız ya çok kapalı ya da son 280 ms'de hızla kapandı | Yavaşça kapanan elin çekme sanılması |

Nişan yönü elin kendisinden hesaplanır: başparmak-işaret çizgisinin normali, avuçtan dışarı doğru.

## Alkış

İki avucunu dik tut (parmaklar yukarı) ve hızla birbirine yaklaştır. Son 0.6 sn içinde
eller arası mesafe el boyunun 3 katından 1.3 katının altına inmişse masa toparlanır.

## Piramit modu (Pepper's ghost)

Tarayıcıda **p** tuşu ya da `--piramit`. Sahne ortadaki boş karenin etrafına dört kez,
alt kenarları merkeze bakacak şekilde çizilir. Ekranın ortasına ters çevrilmiş şeffaf bir
piramit (asetat ya da CD kutusundan kesilebilir) koyunca nesneler piramidin içinde havada
süzülüyormuş gibi görünür. Kamera görüntüsü bu modda gizlenir (arka plan siyah olmalı).

## Çalıştırma

```bash
python dersler/ders_07_hologram_masasi_2/hologram_masasi_2.py
python dersler/ders_07_hologram_masasi_2/hologram_masasi_2.py --piramit
```

Olaylar (`hologram.tutuldu`, `hologram.firlatildi`, `hologram.cekildi`, `hologram.alkis`, ...)
terminale yazılır ve `OlayYolu` üzerinden başka modüllere iletilebilir.

## Testler

`tests/test_hologram.py` pençenin tüm akışını sentetik bir pençe eliyle sınar: açık el, pençe,
nişan, gerilim, kapanma, ele uçma, avucu açıp bırakma. Ayrıca erken kapanan pençenin
çekmediği, açık elden gelmeyen pençenin kurulmadığı ve alkışın masayı toparladığı test edilir.

## CV maddesi

> Hologram arayüzüne uzaktan nesne çekme jesti ekledim: 3D parmak kıvrım açıları, geçiş
> yasası ve dar nişan konisiyle sahte tetiklemeyi önleyen bir durum makinesi. Fiziksel
> Pepper's ghost piramidi için dört yönlü görüntüleme modu hazırladım.
