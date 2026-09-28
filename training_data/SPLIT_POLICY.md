# KODAAI Training / Dev / Benchmark Split Policy v1

Bu politika KODAAI Local AI veri setlerinde ölçüm sızıntısını (benchmark leakage) önlemek için zorunludur.

## 1. Amaç

Model, prompt, retriever veya eğitim verisi geliştirilirken kullanılan örneklerle performans ölçmek gerçek ilerlemeyi göstermez. Bu nedenle veri üç ayrı havuzda tutulur:

- **train**: model/prompt/RAG geliştirme için kullanılabilir.
- **dev**: geliştirme sırasında sınırlı hata analizi ve ayar seçimi için kullanılabilir.
- **benchmark**: yalnız final karşılaştırma/ölçüm için kullanılır; geliştirme girdisi değildir.

## 2. Minimum oranlar

İlk 100 kayıt için hedef:

- train: 70
- dev: 15
- benchmark: 15

Küçük seed setleri oranı temsil etmek zorunda değildir; ancak benchmark kayıtları ayrı dosyada tutulmalıdır.

## 3. Konu dengesi

Mümkün olduğunda her split içinde konu/branş dağılımı korunur.

Örnek:
- Türkçe
- Tarih
- Coğrafya
- Vatandaşlık
- Matematik
- Genel Yetenek / Genel Kültür

## 4. Sızıntı kuralları

Benchmark kaydı:
- train corpus'a kopyalanmaz,
- prompt örneği olarak kullanılmaz,
- few-shot örneği yapılmaz,
- RAG dokümanına gömülmez,
- insan hata analizi sırasında cevabı modele öğretecek şekilde tekrar kullanılmaz.

Aynı soru küçük sözcük değişiklikleriyle başka split'e taşınmaz.

## 5. Yakın kopya kontrolü

Exact duplicate yanında normalize edilmiş soru metni de kontrol edilir.

İleriki sürümde semantik benzerlik kontrolü eklenecektir.

## 6. Sürümleme

Benchmark içeriği değişirse benchmark sürümü artar.

Örnek:
- local_ai_v1
- local_ai_v1.1
- local_ai_v2

Model veya prompt değişmesi benchmark sürümünü değiştirmez.

## 7. Doğrulama kapısı

Bir benchmark kaydı:
- doğruluk kontrolü,
- kaynak/lisans kontrolü,
- erişilebilirlik kontrolü

tamamlanmadan benchmark havuzuna alınmaz.
