# Referans Analizi: barehands (el ile hologram arayüzü)

**Kaynak:** [barehands](https://github.com/jaredrhod/barehands) (commit `eb23bed`, 2026-08-30),
Jared Rhodenizer. Tanıtım videosu: [youtube.com/watch?v=cV02finVi4o](https://www.youtube.com/watch?v=cV02finVi4o)
**Lisans:** AGPL-3.0

barehands tarayıcıda çalışan (MediaPipe JS + three.js) bir el arayüzü: notlar, görseller ve 3D
modeller kamera görüntüsünün üstünde cam kartlar olarak süzülür; elle tutulur, fırlatılır,
büyütülür, uzaktan çekilir. Ders 5-7 bu arayüzdeki tekniklerden esinlenir.

## Lisans kararı

AGPL kodu bu repoya **kopyalanmıyor**; kopyalansaydı tüm reponun AGPL olması gerekirdi.
Teknikler aşağıda belgelenip kendi kodumuzla (Python, piksel uzayında), kendi testlerimizle
yeniden yazılıyor. Fikirler telif konusu değildir, ama kaynak her zaman belirtilir.

## Önemli fark: koordinat uzayı

barehands ölçümlerini MediaPipe'ın **normalize** koordinatlarında (x ve y ayrı ayrı 0-1) yapar.
16:9 bir görüntüde bu uzay anizotropiktir: yatay mesafeler dikeye göre ~1.78 kat küçük görünür.
Biz ölçümleri **piksel** uzayında yaparız. Bu yüzden eşikler birebir kopyalanamaz; yön bağımlı
olanlar (avuç en-boy oranı gibi) dönüştürülür, diğerleri `ornekleyici` ile kendi elimize göre
ayarlanır. Hız eşikleri ekran pikseli yerine **el boyu / saniye** cinsindendir, böylece
kameraya uzaklıktan bağımsızdır.

## Öğrenilen jest teknikleri

| # | Teknik | Nasıl çalışıyor | Ders |
|---|--------|-----------------|------|
| 1 | Tespit ve takip güvenini ayırma | Yeni el bulmak için yüksek eşik (kalabalık arka planda hayalet el çıkmasın), var olan eli tutmak için düşük eşik (hızlı harekette bulanık el düşmesin) | 5 |
| 2 | Kontrast yasası (çimdik mi yumruk mu?) | Her parmak için `uç-bilek / kök-bilek` oranı. Gerçek çimdikte işaret kıvrılır, diğer üç parmak dışarıda kalır. Yumrukta hepsi kıvrıktır. Profil açısında başparmağın yüzük köküne uzaklığı ölçülür | 5 |
| 3 | İki kare onayı + EMA | İmza iki ardışık karede görülürse hemen, ya da üstel ortalaması eşiği geçerse çimdik başlar. Tek şanslı kare yetmez | 5 |
| 4 | Hıza duyarlı bırakma | El hızlıyken bırakma eşiği yükselir ve iki kare art arda açık görülmelidir. Bulanık parmaklar sahte bırakma üretmez | 5 |
| 5 | Doğum hızı kapısı | Çok hızlı hareket sırasında "doğan" çimdik hayalettir, bir şey kavrayamaz. El yavaşlarsa kendini iyileştirir | 5 |
| 6 | Deneme süresi | Yeni çimdik ilk 400 ms boyunca imzasını korumalı. 4 kare imzasız kalırsa sessizce düşer (eli yumruk yaparken geçilen sahte OK işareti) | 5 |
| 7 | İmkânsız geometri | Avuç uzunluğu / genişliği oranı gerçek bir elde olamayacak kadar büyükse takip modeli uyduruyordur, o el hiçbir şey tetikleyemez | 5 |
| 8 | Kıvrım = açı, mesafe değil | `(kök→PIP)·(DIP→uç)` birim vektör nokta çarpımı, 3D. Düz parmak ≈ +0.9, kanca < 0.35. Kameraya doğru uzanan parmakta mesafeler yalan söyler, açılar söylemez | 5, 7 |
| 9 | Kişiye özel eşik örnekleyici | Pozu birkaç saniye tut, her ölçüm için min/medyan/max çıkar, eşiği doğru ve yanlış dağılımların arasından kes | 5 |
| 10 | İmleç = başparmak/işaret orta noktası | Çimdikte iki uç birbirine doğru gelir, orta nokta sabit kalır | 5, 6 |
| 11 | Fırlatma | Son örneklerdeki tepe hız bırakma anında nesneye aktarılır, sürtünmeyle yavaşlar | 6 |
| 12 | İki el = ölçek | İki el aynı nesneyi tutarsa eller arası mesafe oranı = ölçek | 6 |
| 13 | Tut-bekle = döndür | Modeli tutup ~1 sn sabit beklemek döndürme moduna geçirir | 6 |
| 14 | Boş çimdikle patlatma | Hiçbir şeyi tutmayan çimdik yana sürüklenince son 3D modelin parçaları açılır / kapanır | 6 |
| 15 | Pençe ile çekme | Geçiş yasası (son 0.9 sn içinde açık el), pençe pozu birkaç kare tutulmalı, nişan = başparmak-işaret çizgisinin normali, dar koni, hedef 2 sn titrer, ağzın hızla kapanması nesneyi ele çeker | 7 |
| 16 | Alkış | İki avuç dik ve birbirine hızla yaklaşırsa masa toparlanır | 7 |
| 17 | Güvenli komut kanalı | Dışarıdan gelen komutlar izin listesiyle sınırlı, dosyalar sadece tek bir klasörden yüklenebilir | 6, 17 |
