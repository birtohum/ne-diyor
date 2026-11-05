# Ne Diyor?

Resmî yazıyı sade Türkçeye çevirir: kısaca ne diyor, senden ne istiyor, ne zamana kadar.

- **Site:** https://birtohum.github.io/ne-diyor/
- **Eklenti (Chrome / Edge):** [son sürüm](https://github.com/birtohum/ne-diyor/releases/latest). Zip'i aç, `chrome://extensions` → Geliştirici modu → “Paketlenmemiş öğe yükle” → `eklenti` klasörü. Sayfada metni seç, sağ tıkla, “Ne diyor?”.

## Nasıl çalışır

1. Tarayıcı, metindeki TC kimlik no, IBAN, cep telefonu ve e-postayı `[TC no]` gibi işaretlerle değiştirir. Sunucu aynı maskelemeyi bir kez daha yapar.
2. Sunucu (`sunucu/`) metni Meta Model API'ye (`muse-spark-1.3`, içeriği eğitimde kullanmayan ücretli katman) bir istemle gönderir: yalnızca metinde yazanı kullan, tarih/süre/tutarı aynen yaz, tavsiye verme.
3. **Sayı denetimi** (`cekirdek.denetle`): çıktıdaki her sayı asıl metinde aranır. Asıl metinde olmayan bir tarih, süre ya da tutar çıkarsa kullanıcıya kırmızı uyarıyla gösterilir. Modelin en tehlikeli hatası bu: “7 gün” yerine “15 gün” yazmak.

Metinler kaydedilmez. Kötüye kullanıma karşı IP başına günde 10, toplam günde 100 metin ve toplam harcama tavanı var (`NEDIYOR_*` ortam değişkenleri). Sunucu, Caddy arkasında `systemd` servisi olarak çalışıyor (`sunucu/ne-diyor.service`).

## Sınırlar

- Bir hukuk danışmanlığı değildir. Önemli kararlarda yazının aslı ve bir uzman esas alınmalı.
- Sayı denetimi uydurma sayıyı yakalar ama yanlış anlamayı (ör. “ceza uygulanır” yerine “uygulanmaz”) yakalamaz.
- Taranmış (resim) belgeler okunmaz; metin seçilebilir olmalı.
- Örnek yazı uydurmadır; gerçek bir kuruma ait değildir.

## Geliştirme

```bash
python -m unittest discover -s testler
cd sunucu && python sunucu.py     # 127.0.0.1:8791, META_MODEL_API_KEY gerekir
```

Lisans: MIT.
