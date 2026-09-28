# KODAAI Training Data v0.1

Bu alan KODAAI Local AI için kullanılacak doğrulanmış eğitim verisinin yapısını tanımlar.

## Veri havuzları

### 1. Educational Reasoning Corpus
Amaç: modeli yalnız doğru cevabı söyleyen bir chatbot yerine pedagojik olarak kontrollü tutor davranışına hazırlamak.

Her kayıt mümkün olduğunda şunları içerir:
- soru
- seçenekler
- doğru cevap
- her seçeneğin neden doğru/yanlış olduğu
- HINT
- EXPLAIN
- SIMPLIFY
- EXAMPLE
- CHECK_UNDERSTANDING
- kaynak
- doğrulama durumu

### 2. Accessibility Transformation Corpus
Ham içerik ile erişilebilir dönüşüm çiftleri:
- source_text
- accessible_text
- tts_text
- uygulanan Reading/MathSpeak kuralları
- kalite/doğrulama bilgisi

### 3. Voice Command Corpus
KODAAI'nin gerçek komut uzayını ölçmek ve ileride STT geliştirmek için manifest yapısı.

Kategoriler:
- auth
- voice model
- dashboard
- lesson selection
- reading control
- quiz
- exam
- global commands

## Veri ayırma politikası

Veri üç ayrı havuzda tutulur:

- train
- dev
- benchmark

Bir örnek benchmark setine girdikten sonra eğitim veya prompt tuning için kullanılmaz.

## Gizlilik

Gerçek kullanıcı adı, ses kaydı, session id, e-posta, telefon, IP veya production telemetry bu public repoya eklenmez.

Gerçek kullanıcı verisi gerekiyorsa:
1. açık amaç tanımlanır,
2. anonimleştirilir,
3. ayrı güvenli depoda tutulur,
4. public repoda yalnız şema/anonim örnek bulunur.

## İlk üretim hedefi

Educational Reasoning Corpus v0.1:
- 100 doğrulanmış EKPSS tipi soru
- 5 seçenek
- doğru cevap gerekçesi
- 4 yanlış seçenek gerekçesi
- en az HINT + EXPLAIN + CHECK_UNDERSTANDING
- kaynak/doğrulama alanları

Gerçek sınav soruları için telif ve kullanım hakları ayrıca doğrulanmalıdır. Public repoda sentetik/izinli örnekler tercih edilir.
