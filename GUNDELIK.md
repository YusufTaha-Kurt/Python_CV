# Gündelik Kullanım

Derslerin hepsi öğrenme yolu olarak depoda durur. Bu sayfa yalnız günlük hayatta kullanılan
kısmı anlatır. Tek bir başlatıcı arka planda çalışır, fareyi, medyayı ve pencereleri elle
yönetir, yorgunluğu izler.

## Başlatma

| Yol | Ne olur |
|-----|---------|
| `Gundelik.bat` dosyasına çift tıklamak | Konsol penceresi açılmaz. Hazır olunca kontrol paneli tarayıcıda açılır. |
| `python gundelik.py` | Konsol açık kalır, olaylar orada akar. Ctrl+C ile kapanır. |
| `python gundelik.py --sadece-izle` | Fareye, klavyeye ve sese dokunmaz. İlk denemede önerilir. |
| `python gundelik.py --onizleme` | Kamera görüntüsü ve el iskeleti ayrı bir pencerede görünür. |
| `python baslat.py g` | Ders menüsünden aynı başlatıcı |

Kamerayı aynı anda yalnız bir program kullanabilir. Açık kalan bir dersi önce kapatınız.
Başlatıcı ikinci kez çalıştırılırsa yeni kopya açılmaz, yalnız panel açılır.

## Kapatma

Kontrol panelinde (`http://127.0.0.1:8770/`) **Servisi kapat** düğmesine basınız. Konsolla
başlatıldıysa Ctrl+C de kapatır. Yalnız ara vermek için **Duraklat** yeterlidir.

## Ne yapar

İki el iki ayrı iş yapar. Sağ el işi yapar, sol el modu seçer. Sol elle 1, 2 ya da 3 parmak
gösterip 0.6 saniye tutunca o moda geçilir.

| Mod | Sağ elle |
|-----|----------|
| **1 Fare** | OK çimdiği tık, iki hızlı çimdik çift tık, çimdikle sürükle, başparmak + orta parmak sağ tık |
| **2 Medya** | L işareti ses seviyesi, onay oynat / duraklat, avuçla sağa / sola sonraki / önceki parça, bozkurt sessiz |
| **3 Pencere** | Kardeşlik + yukarı / aşağı sayfayı kaydırır, avuçla sağa / sola sanal masaüstü değişir, onay büyütür, bozkurt küçültür, L işareti Alt+Tab |

Her modda sağ elle **yumruk** uyku modunu açar ve kapatır. Uykudayken hiçbir hareket bir
şey yapmaz.

**Yorgunluk** arka planda izlenir. Son bir dakikada gözlerin kapalı kaldığı zaman %15'i geçerse
mola uyarısı verilir. Gözler 3 dakika kapalı kalırsa uyku uyarısı verilir. Uyarılar panelde
ve olay listesinde görünür. Ses için ayarlarda `"alarm": true` yapınız.

15 saniye kimse görünmezse servis bekleme moduna geçer ve saniyede 2 kare işler. Biri görününce
tam hıza döner.

## Ayarlar

Ayarlar [`gundelik_ayarlari.json`](gundelik_ayarlari.json) dosyasındadır. Değişiklik bir
sonraki başlatmada geçerli olur.

| Ayar | Anlamı |
|------|--------|
| `kontrol.el` | İşi yapan el, `"sag"` ya da `"sol"`. Diğer el mod seçer. |
| `yorgunluk.alarm` | Uyarıda bip sesi |
| `yorgunluk.mikro_uyku_dakika` | Gözler bu kadar dakika kapalı kalınca uyarı |
| `yorgunluk.perclos_esigi` | Mola uyarısı için gözlerin kapalı kalma oranı (0.15 = %15) |
| `kaynak` | Kamera numarası. Harici kamera için `1` deneyebilirsiniz. |
| `http.port` | Kontrol panelinin portu |

Kapalı yetenekler panelden de açılabilir. Panelden açılan yetenek yalnız o oturum için açık kalır.

## Bilgisayar açılınca kendiliğinden başlatma

1. Win+R tuşlarına basınız, `shell:startup` yazıp Enter'a basınız.
2. Açılan klasöre `Gundelik.bat` dosyasının kısayolunu sürükleyiniz (Alt ile sürüklemek kısayol oluşturur).

Kaldırmak için kısayolu o klasörden silmeniz yeterlidir.

## Sorun giderme

| Belirti | Çözüm |
|---------|-------|
| Çift tıkladım, hiçbir şey olmadı | Kamera ve modellerin hazırlanması birkaç saniye sürer. Hata olursa bir uyarı penceresi çıkar. |
| "Kamera açılamadı" uyarısı | Kamera başka bir programda açık. Açık dersi ya da görüntülü görüşmeyi kapatınız. |
| Çimdik kaçıyor ya da kendiliğinden tıklıyor | Ders 5'teki örnekleyiciyle eşiği kendi elinize göre çıkarabilirsiniz. `python baslat.py 5 --sadece-izle` ile açıp **p** (4 sn OK çimdiği), **y** (4 sn yumruk) ve **k** (kaydet) tuşlarına sırayla basınız. Gündelik kullanım bu ayarı kendiliğinden okur. |
| Ne olduğunu görmek istiyorum | `servis_kayitlari/servis.log` ve `servis_kayitlari/gundelik_konsol.txt` dosyalarına bakınız. |

## Gündelik kullanıma girmeyenler

Bunlar depoda ders olarak durur, menüden (`python baslat.py`) ayrıca açılabilir.

| Ders | Neden dışarıda |
|------|----------------|
| 6, 7 Hologram masası | Tarayıcıda çalışır. Tutma noktası ile görüntü tam örtüşmez, akış hızı düşüktür. |
| 9 Baş pozu | Başla imleç, elini kullanamayanlar için erişilebilirlik aracıdır. |
| 10f Göz kırparak tıklama | Gözlükle ve kısık gözle güvenilir değildir. |
| 11 Mimik | Çalışır ama yüz ifadesiyle komut gündelik ihtiyaç değildir. |
| 12, 13, 14 Yüz tanıma, canlılık, kapı bekçisi | Ders olarak durur. Kapı bekçisi ayarlarda `"kapi": {"acik": true}` ile açılabilir. Önce `python baslat.py 12` ile kaydolmak gerekir. |
| 15 Nesne tespiti | Gündelik ihtiyaç değildir. |
| 16 Vücut pozu | Gündelik ihtiyaç değildir. Duruş uyarısı ayarlarda `"durus"` ile açılabilir. |
