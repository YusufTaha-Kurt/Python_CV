# Ders 10: Göz Kırpma ve Yorgunluk

**Amaç:** Gözlerin açık mı kapalı mı olduğunu güvenilir şekilde ölçmek; bununla hem
göz kırparak tıklamak hem de uzun süre bilgisayar başında kalınca yorgunluğu fark etmek.

## Göz Açıklık Oranı (EAR)

```
    p2   p3
p1          p4        EAR = (|p2 - p6| + |p3 - p5|) / (2 |p1 - p4|)
    p6   p5
```

Açık gözde ~0.30, kapalı gözde ~0.10 (Soukupová & Čech, 2016). Gerçek bir webcam videosunda
açık göz medyanı 0.30, kırpma anları 0.08-0.15 ölçüldü.

**Sabit eşik kullanılmaz.** Her gözün açık tabanı son ~10 saniyenin %70'lik diliminden sürekli
öğrenilir; kapanma eşiği tabanın %62'si, açılma eşiği %78'idir (histerezis). Testte açık göz
EAR'ı 0.20 olan bir kullanıcı da doğru çalışıyor (sabit 0.2 eşiği onda her kareyi "kapalı" sayardı).

**Göz indeksleri:** MediaPipe'ın göz noktaları (33 / 263 grupları) görüntü aynalansa da hep
görüntünün aynı tarafında kalır (Ders 9'da doğrulandı). Bu yüzden gözler "ekranda sol / sağ"
diye adlandırılır; aynalı görüntüde ekranın solundaki göz kullanıcının kendi sol gözüdür.

## Olaylar

| Olay | Koşul | Kullanım |
|------|-------|----------|
| `dogal` | İki göz < 0.35 sn kapalı | Kırpma hızı (dakikada) |
| `bilincli` | İki göz 0.35 - 1.5 sn kapalı | `--fare` ile **sol tık** |
| `goz_kirp_sol` / `goz_kirp_sag` | Tek göz 0.2 - 1 sn kapalı, diğeri hep açık | `--fare` ile sağdaki gözle **sağ tık** |
| `mikro_uyku` | İki göz 1.5 sn'dir kapalı | Kırmızı uyarı (+ `--alarm` ile ses) |

Doğal kırpmada bir göz bir kare önce kapanabilir; bu tek göz kırpma sayılmaz (diğer göz
kapanınca tek göz adayı iptal edilir).

## Yorgunluk

- **PERCLOS:** Son 1 dakikada gözlerin kapalı olduğu zamanın oranı. Sürücü yorgunluğu
  araştırmalarının standart ölçüsü; %15'i geçince "mola ver" uyarısı (30 sn'de bir).
- **Kırpma hızı** (dakikada) ve **esneme sayısı** (`jawOpen` ifade skoru 1.2 sn boyunca > 0.6).

## Çalıştırma

```bash
python dersler/ders_10_goz_kirpma/goz_kirpma.py                 # izleme ve uyarı
python dersler/ders_10_goz_kirpma/goz_kirpma.py --fare --alarm  # eller serbest fare + sesli uyarı
```

`--fare`: Ders 9'un başla imleciyle birleşir. Gözler kapanırken baş biraz oynadığı için göz
kapalıyken imleç dondurulur; böylece tık tam bakılan yere düşer.

## CV maddesi

> Kişiye uyarlanan eşiklerle göz kırpma sınıflandırması (doğal / bilinçli / tek göz / mikro
> uyku) yaptım; bunu baş pozuyla birleştirip tamamen eller serbest bir fare ve PERCLOS tabanlı
> bir yorgunluk izleyicisi geliştirdim.
