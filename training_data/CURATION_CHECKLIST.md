# Educational Reasoning Corpus v0.1 - Curation Checklist

Bu kontrol listesi her yeni batch için uygulanır.

## Kaynak ve telif
- Soru proje tarafından özgün üretilmiş, izinli veya kullanım hakkı doğrulanmış mı?
- Kaynak/reference alanı dolu mu?
- Lisans/kullanım durumu biliniyor mu?
- Gerçek sınav sorusu ise public repoya koymadan önce kullanım hakkı doğrulandı mı?

## Doğruluk
- Tek bir doğru seçenek var mı?
- `correct_answer` ile `is_correct=true` aynı seçeneği gösteriyor mu?
- Her yanlış seçeneğin gerekçesi gerçekten o seçeneğe özgü mü?
- Doğru seçenek gerekçesi soruyu tekrar etmekten fazlasını sağlıyor mu?

## Pedagoji
- Hint cevabı doğrudan ele vermiyor mu?
- Explain kavramı açıklıyor mu?
- Simplify daha basit dil kullanıyor mu?
- Example yeni fakat aynı kavramı destekleyen bir örnek mi?
- Check-understanding yeni bir mikro ölçüm sağlıyor mu?

## Erişilebilirlik
- Cümleler sesli okununca anlaşılır mı?
- Görsel konum, renk, şekil veya biçim bilgisine bağımlı ifade var mı?
- Matematiksel içerik MathSpeak kurallarına dönüştürülebilir mi?
- Cevap açıklaması seçenek harfi kadar seçenek metnini de anlamlandırıyor mu?

## Veri kalitesi
- ID benzersiz mi?
- Subject/topic normalize mı?
- split doğru mu?
- JSONL satırı validator'dan geçiyor mu?
- Aynı soru train ve benchmark içinde tekrar etmiyor mu?

## Yayın kapısı
Bir kayıt ancak doğruluk + telif + erişilebilirlik kontrolleri tamamlandıktan sonra `validation.status=verified` olabilir.
