# KODAAI Educational Reasoning Corpus v0.1 - 100 Kayıt Planı

## Hedef

İlk üretim hedefi 100 doğrulanmış, özgün/izinli Türkçe eğitim sorusudur.

Bu sürüm bir model eğitme iddiasından önce veri üretim ve kalite hattını doğrular.

## Branş hedefi

İlk 100 kayıt için önerilen dağılım:

| Branş | Kayıt |
|---|---:|
| Türkçe | 20 |
| Matematik | 20 |
| Tarih | 15 |
| Coğrafya | 15 |
| Vatandaşlık | 15 |
| Genel Yetenek / Mantık | 10 |
| Genel Kültür / bilgi okuryazarlığı | 5 |
| **Toplam** | **100** |

Bu dağılım sonraki curriculum analiziyle değiştirilebilir; değişiklik manifestte sürümlenir.

## Her kayıt için zorunlu alanlar

- soru
- A-E seçenekleri
- tek doğru cevap
- doğru seçeneğin gerekçesi
- dört yanlış seçeneğin ayrı ayrı neden yanlış olduğu
- HINT
- EXPLAIN
- CHECK_UNDERSTANDING
- kaynak/reference
- lisans/kullanım durumu
- validation status
- split

Tercihen:
- SIMPLIFY
- EXAMPLE
- topic
- difficulty

## Batch üretimi

100 kayıt tek seferde üretilmez.

Önerilen kontrollü sıra:

1. Batch A: 20 kayıt — veri hattı ve validator doğrulama
2. Batch B: +20 — konu/branş dengesi
3. Batch C: +20 — pedagojik kalite incelemesi
4. Batch D: +20 — erişilebilirlik incelemesi
5. Batch E: +20 — final 100 ve split mühürleme

Her batch:
- validator
- leakage checker
- insan/domain review
- erişilebilirlik review

aşamalarından geçmeden sonraki batch'e ilerlemez.

## Split hedefi

100 kayıt tamamlandığında:

- train: 70
- dev: 15
- benchmark: 15

Benchmark soruları eğitim, prompt örneği ve RAG corpus'tan ayrı tutulur.

## Kalite hedefleri

- schema validity: %100
- duplicate ID: 0
- exact/normalized question leakage: 0
- tek doğru cevap bütünlüğü: %100
- boş reason alanı: 0
- boş pedagogy required alanı: 0
- source/reference coverage: %100
- doğrulanmamış kaydın production kullanımı: 0

## İlk başarı ölçütü

v0.1 başarılı sayılırsa:
1. 100 kayıt validator'dan hatasız geçer,
2. split leakage kontrolü sıfır hata verir,
3. en az 15 benchmark kaydı geliştirme sürecinden ayrı tutulur,
4. corpus, mevcut Local AI üzerinde Tutor davranış deneyine girdi sağlayabilir.
