# KODAAI Reasoning Review + Grammar + Pedagogy v0.1

Bu araç `training_data/wrong_answer_reasoning_v0_1/ekpss_100_draft.jsonl` kayıtlarını insan/domain incelemesine hazırlar.

## Amaç

- soru ve A-E gerekçelerini tek ekranda incelemek,
- her yanlış seçenek için "neden yanlış?" gerekçesini düzenlemek,
- TDK/MEB kaynaklarına hızlı erişmek,
- kural tabanlı Türkçe dilbilgisi kontrolü çalıştırmak,
- pedagojik kalite ve erişilebilirlik uyarıları üretmek,
- `draft -> reviewed -> verified` akışını kontrollü yürütmek,
- her kaydetmede otomatik JSONL yedeği almak.

## Çalıştırma

Repo kökünde:

```powershell
.\tools\reasoning_review_app\run_review.ps1
```

Tarayıcı:

`http://127.0.0.1:8091`

Varsayılan olarak yalnız localhost'a bağlanır. İnternete/public porta açmayın.

## Verified kuralı

`verified` için:
- reviewer adı zorunlu,
- dilbilgisi katmanında blocking `fail` olmamalı,
- pedagojik katmanda `blocked` olmamalı.

Motorun `pass` üretmesi insan doğrulamasının yerine geçmez.

## Kaynak hiyerarşisi

1. TDK Yazım Kılavuzu / TDK resmî sayfaları
2. MEB / Özel Eğitim resmî öğretim materyalleri
3. Zemberek-NLP yalnız yardımcı morfolojik analiz aracı

Dış kaynaktan alınan kural/metin eğitim corpus'una otomatik kopyalanmaz; yalnız kanıt/referans olarak kullanılır.
