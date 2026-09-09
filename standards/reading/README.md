# KODAAI Reading / TTS Erişilebilirlik Standardı V2.x

## Amaç

Bu standart, Türkçe eğitim metinlerinin özellikle görme engelli ve ses öncelikli kullanıcılar için anlam kaybı oluşturmadan hazırlanması ve seslendirilmesi için KODAAI tarafından geliştirilen kamuya açık erişilebilirlik yaklaşımını açıklar.

Bu dizin gerçek ders JSON'larını, MP3/TTS varlıklarını veya production dönüştürme pipeline'ını içermez.

## Temel Kurallar

### 1. Soru önce

Paragraf veya uzun metin içeren sorularda kullanıcı önce neyi aradığını bilmelidir. Bu nedenle soru kökü/paragrafın amacı, uygun olduğu durumda paragraf metninden önce seslendirilir.

### 2. Üç nokta: boşluk ile noktalama ayrımı

Üç nokta tek bir davranış değildir.

- Boşluk/doldurulacak alan görevi taşıyan `...`, `. . .` veya `…` ifadesi açık biçimde **“nokta nokta nokta”** olarak seslendirilir.
- Normal noktalama veya eksilti görevi taşıyan üç nokta ise metnin doğal duraklama ve cümle akışına göre ele alınır.

### 3. Roma rakamları

`I`, `(I)`, `II`, `(II)` gibi yapılar bağlama göre doğru Türkçe karşılığıyla okunur. Yanında sıra bildiren nokta bulunmadığında otomatik olarak “birinci, ikinci” biçimine çevrilmez; gerekli durumda “bir, iki, üç” olarak okunur.

### 4. Vurgu, boşluk ve duraklama

TTS metni yalnızca kelime dönüşümü değildir. Kelimeler arasındaki boşluk, vurgu ve anlamlı duraklamalar ses üretiminden önce bilinçli biçimde düzenlenir. Erişilebilirlik dönüşümü, hedef ses dosyasında kullanıcının gerçekten duyacağı anlamı dikkate alır.

### 5. Altı çizili ifadeler

Altı çizili veya görsel biçimlendirmeyle işaretlenmiş gerçek metin kaybolmaz. Görsel işaretin soru açısından anlamı varsa, ilgili gerçek ifade erişilebilir metinde korunur ve gerektiğinde açıklanır.

### 6. Deterministik erişilebilirlik

Erişilebilirlik kuralları üretken modelin serbest yorumuna bırakılmaz. KODAAI'nin deterministik uygulama ve içerik katmanı, temel okuma ve seslendirme davranışında yetkilidir.

## Reading ile Quiz Ayrımı

Ders anlatımı ve konu testi aynı içerik türü değildir. Reading içeriği öğretim ve açıklama akışını; quiz/test içeriği ise soru, seçenek, doğru cevap ve geri bildirim akışını temsil eder. Public standart bu ayrımı korur; gerçek production eğitim corpus'u paylaşılmaz.

## Public / Private Sınırı

Public:
- erişilebilirlik kuralları,
- standardın gerekçesi,
- güvenli ve genel örnekler.

Private / production:
- gerçek ders/quiz/exam JSON'ları,
- production dönüştürme kodları,
- MP3/TTS varlıkları,
- öğrenci/kullanıcı verileri,
- regression ve içerik corpus'larının tamamı.

## Durum

V2.x hattı yaşayan bir erişilebilirlik standardıdır. Yeni Türkçe içerikler ve gerçek kullanıcı testleriyle kurallar gözden geçirilebilir; ancak değişiklikler kontrollü ve sürümlenmiş biçimde yapılmalıdır.
