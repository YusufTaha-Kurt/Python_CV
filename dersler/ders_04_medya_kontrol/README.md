# Ders 4: Medya ve Ses Kontrolü

**Amaç:** Ders 3'teki olay yoluna ilk gerçek "yetenekleri" bağlamak. Müzik ve video
klavyeye ya da fareye dokunmadan yönetilir.

## Jest sözlüğü

| Jest | Eylem |
|------|-------|
| L işareti (başparmak + işaret) | **Ses modu:** iki parmak arası mesafe = ses seviyesi |
| Avuç aç | Ses modundan çık (seviye olduğu yerde kalır) |
| Avuçla sağa / sola kaydır | Sonraki / önceki parça |
| Başparmak yukarı | Oynat / duraklat |
| Rock (işaret + serçe) | Sesi kapat / aç |

## Öğrenilenler

- **Sürekli ve ayrık kontrol:** Ses seviyesi sürekli bir değerdir ve her kare güncellenir.
  Oynat/duraklat ise ayrıktır ve olay olarak bir kez tetiklenir.
- **Ses modundan çıkış neden avuçla?** Yumrukla çıkılsaydı parmaklar kapanırken mesafe
  küçülür ve ses sıfıra düşerdi. Mod, orta/yüzük/serçe parmaklardan biri açılınca biter.
  Bu sırada başparmak ile işaret parmağı arası değişmez.
- **Windows Core Audio:** `pycaw` ile seviye doğrudan 0-100 arası ayarlanır. Ses tuşlarına
  basmaktan farklı olarak adım adım değil, istenen değere tek seferde gidilir. API'yi
  gereksiz çağırmamak için %1'den küçük değişiklikler yok sayılır.
- **Yetenek = abone:** `Yetenekler` sınıfı sadece olayları dinler. Yeni bir yetenek
  eklemek, görüntü döngüsüne dokunmadan yeni bir abone yazmak demektir.

## Çalıştırma

```bash
python dersler/ders_04_medya_kontrol/medya_kontrol.py
python dersler/ders_04_medya_kontrol/medya_kontrol.py --sadece-izle
```

## CV maddesi

> Jestle sistem sesi ve medya kontrolü geliştirdim (Windows Core Audio / pycaw). Bu
> yetenekleri olay tabanlı mimaride, görüntü katmanından bağımsız aboneler olarak tasarladım.
