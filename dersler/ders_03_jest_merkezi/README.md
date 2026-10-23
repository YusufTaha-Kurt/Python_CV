# Ders 3: Jest Merkezi ve Olay Yolu

**Amaç:** JARVIS'in sinir sistemini kurmak. İki el aynı anda izlenir, jestler tanınır ve
her şey bir **olay** olarak yayınlanır. Görüntü kodu ne yapılacağını bilmez, sadece ne
olduğunu söyler.

## Jest sözlüğü

| Jest | Parmaklar (baş, işaret, orta, yüzük, serçe) |
|------|-----|
| `yumruk` | hepsi kapalı |
| `avuc` | hepsi açık |
| `isaret` | sadece işaret |
| `l_isareti` | başparmak + işaret |
| `zafer` | işaret + orta |
| `rock` | işaret + serçe |
| `basparmak_yukari` | sadece başparmak, uç bileğin üstünde |
| `kaydirma` (dinamik) | açık avuçla hızlı yatay hareket |

## Nasıl çalışıyor?

- **Parmak açık mı?** Parmak ucu bileğe orta boğumdan daha uzaksa parmak açıktır. Sadece
  mesafe karşılaştırıldığı için el döndürülse de çalışır (testlerde -60° ile +90° arası doğrulandı).
- **Kararlılık:** Jest 0.3 sn kesintisiz görülmeden kabul edilmez. Tek karelik yanlış
  tanımalar böylece elenir.
- **Kaydırma:** Son 0.35 sn içinde el, el boyutunun 1.6 katından fazla yatay yol aldıysa
  ve dikey sapma küçükse kaydırma sayılır. Eşik el boyutuna oranlı olduğundan kameraya
  uzaklıktan bağımsızdır.

## Olaylar

| Olay | Veri |
|------|------|
| `el.goruldu` / `el.kayboldu` | `el` |
| `jest.degisti` | `el`, `jest`, `parmak_sayisi` |
| `jest.kaydirma` | `el`, `yon` (`sag` / `sol`) |

Her olay `olaylar.jsonl` dosyasına bir satır JSON olarak eklenir:

```json
{"ad": "jest.degisti", "veri": {"el": "sag", "jest": "zafer", "parmak_sayisi": 2}, "zaman": 1761245112.4}
```

**JARVIS entegrasyonu:** Kendi yapay zekan ister `OlayYolu`'na abone olur (aynı süreç),
ister bu dosyayı satır satır okur (ayrı süreç). İkisi de görüntü koduna dokunmadan çalışır.

```python
from jarvis_vision.olaylar import OlayYolu

yol = OlayYolu()
yol.abone_ol("jest.degisti", lambda olay: print("Efendim,", olay.veri["jest"], "yaptınız."))
```

## Çalıştırma

```bash
python dersler/ders_03_jest_merkezi/jest_merkezi.py
```

## CV maddesi

> Kural tabanlı, dönme ve ölçek değişmez el jesti sınıflandırıcısı ve yayınla-abone ol
> mimarisinde olay yolu tasarladım. Bu yapı görüntü katmanını eylem katmanından ayırarak
> yapay zeka asistanı entegrasyonuna hazır hale getirir.
