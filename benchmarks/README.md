# KODAAI Benchmark Framework v1

Bu klasör KODAAI Local AI değişikliklerini tekrar edilebilir ve ölçülebilir biçimde değerlendirmek için ayrılmıştır.

## Temel kural

**Training set != benchmark set.**

Benchmark örnekleri model eğitimi, prompt geliştirme veya RAG corpus genişletme sırasında kullanılmaz. Böylece bir model/prompt/retriever değişikliğinin gerçek etkisi aynı sabit test seti üzerinde karşılaştırılabilir.

## Benchmark aileleri

### 1. Local AI / RAG Benchmark
Ölçümler:
- answer correctness
- grounded / ungrounded answer
- refusal correctness
- route/process behavior
- source usage
- latency
- hallucination flag
- accessible speech compatibility

### 2. Turkish Voice / STT Benchmark
Ölçümler:
- command success rate
- word error rate (WER)
- character error rate (CER)
- EMPTY_STT rate
- latency
- critical command accuracy

Önerilen komut kategorileri:
- kimlik / ad-soyad
- dashboard komutları
- ders adları
- test ve sınav cevapları
- sayılar ve sınav seçimi
- global komutlar
- gürültülü / düşük ses / farklı mikrofon koşulları

### 3. Accessibility / TTS Benchmark
Ölçümler:
- Reading standardı kural uyumu
- MathSpeak kural uyumu
- boşluk/ellipsis ayrımı
- soru görevi önceleme
- Türkçe telaffuz
- anlam kaybı / answer leakage
- erişilebilir speech çıktısı

## Klasör politikası

- `benchmarks/`: sabit test verisi ve değerlendirme araçları
- `training_data/`: eğitim/RAG üretim verisi şemaları ve örnekleri
- Gerçek kullanıcı kayıtları, kişisel veriler ve production telemetry bu repoya commit edilmez.
- Benchmark değişikliği yeni bir benchmark sürümü gerektirir.
- Model değişikliği benchmark sürümünü değiştirmez.

## İlk hedef

`local_ai_v1` ile küçük fakat sabit bir smoke benchmark başlatılır. Sonraki aşamada 50-100, ardından 200+ doğrulanmış Türkçe eğitim sorusuna genişletilir.
