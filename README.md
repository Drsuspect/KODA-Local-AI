# KODAAI Lokal AI

**Lokal-first Türkçe yapay zekâ araştırması; erişilebilir, ses öncelikli eğitim için belgeye dayalı ve kontrollü yardım.**

> Durum: Beta / Ar-Ge - Research Preview v0.1

KODAAI Lokal AI, KODAAI erişilebilir teknoloji ve eğitim Ar-Ge ekosisteminin lokal yapay zekâ katmanıdır. Proje; lokal çalışan dil modelleri, RAG, kontrollü eğitim açıklamaları ve ses öncelikli erişilebilir etkileşimi araştırır.

## Temel Tasarım İlkesi

**Yapay zekâ uygulamayı yönetmez.**

Kimlik, navigasyon, ders, test, sınav ve erişilebilirlik akışları deterministik KODAAI uygulama katmanında kalır. Üretken model, sınırlandırılmış bir yardımcı olarak kullanılır.

## Güncel Araştırma Hattı

- Gemma 3 4B / Ollama lokal runtime
- multilingual MiniLM embeddings
- ChromaDB tabanlı RAG
- semantik + lexical/hybrid retrieval araştırması
- FastAPI
- Türkçe belgeye dayalı soru-cevap
- erişilebilir yanıt dönüşümü
- ses öncelikli web arayüzü
- kontrollü MathSpeak ve Reading/TTS erişilebilirlik katmanları

Model ağırlıkları bu repoda dağıtılmaz.

## Eğitim Kapsamı

Mevcut Beta/Ar-Ge bilgi deposu EKPSS lisans düzeyine yönelik Türkçe, Coğrafya, Matematik, Tarih ve Vatandaşlık içerikleriyle test edilmektedir. Gerçek eğitim corpus'u public repoya dahil edilmez.

## Erişilebilirlik

KODAAI'nin erişilebilirlik yaklaşımı yalnız UI seviyesinde değildir. Metin ve matematiksel ifadelerin sesli aktarımı için deterministik kurallar üzerinde çalışılır.

### KODAAI MathSpeak V1.0

Public standart özeti: `standards/math/README.md`

Production Math Engine, tam regression corpus'u ve gerçek eğitim verileri public değildir.

### KODAAI Reading / TTS Standardı V2.x

Public standart özeti: `standards/reading/README.md`

Soru önce yaklaşımı, üç noktanın boşluk/noktalama ayrımı, Roma rakamları, vurgu-duraklama ve görsel biçimlendirmelerin erişilebilir aktarımı gibi kurallar bu hatta ele alınır.

## Ses Öncelikli Web Arayüzü

`web/` altında güvenli public örnek arayüz bulunur. Örnek;

- Kapsamı Dinle,
- Konuşmayı Başlat,
- Durdur,
- klavye/Enter kontrolü,
- aria-live sistem durumu,
- soru ve yanıt transcript alanı

gibi erişilebilir etkileşimleri gösterir.

Public örnek production host, özel telemetry ayrıntıları, credential veya production corpus içermez.

## RAG Akışı

```text
Belgeler
   |
   v
Loader / Chunker
   |
   v
Multilingual Embeddings
   |
   v
ChromaDB
   |
   v
Retrieval
   |
   v
Gemma 3 4B / Ollama
   |
   v
Kontrollü Türkçe Yanıt
   |
   v
Erişilebilirlik Katmanı
```

## Public Repo Güvenlik Sınırı

Bu repoda paylaşılmayan production varlıkları şunları kapsar:

- gerçek Reading / Quiz / Exam corpus'u,
- Math Engine V1.0 production implementation,
- Reading production dönüştürme pipeline'ı,
- Chroma index ve embeddings,
- model ağırlıkları,
- telemetry ve audit verileri,
- kullanıcı/session/request kayıtları,
- MP3/TTS ve ham ses varlıkları,
- `.env`, token, credential ve production config,
- backup/archive çalışma kopyaları.

`.gitignore` bu varlıkların yaygın biçimlerini dışarıda tutar; commit öncesinde ayrıca Git durumu kontrol edilmelidir.

## Güvenlik

Bu repo aktif Ar-Ge çalışmasını temsil eder. Development yönetim/document endpointleri doğrudan public internete açılmamalıdır. Authentication, authorization, rate limiting ve production hardening ayrı deployment katmanında ele alınmalıdır.

Ayrıntılar için `SECURITY.md` dosyasına bakın.

## Repository Yapısı

```text
KODA-Local-AI/
|-- audit/                 # logger implementation; runtime logs excluded
|-- common/
|-- examples/              # safe public examples
|-- experiments/
|-- llm_core/
|-- rag/
|-- security/
|-- standards/
|   |-- math/
|   `-- reading/
|-- web/                   # safe public accessible UI example
|-- .env.example
|-- .gitignore
|-- api_server.py
|-- main.py
|-- ARCHITECTURE.md
|-- SECURITY.md
`-- requirements.txt
```

## Privacy

Lokal çalışma gizlilik açısından avantaj sağlar ancak tek başına güvenlik garantisi değildir. Production sistem güvenliği; API yapılandırması, işletim sistemi, doküman erişimi, loglama, izinler ve deployment mimarisinin tamamına bağlıdır.

## Proje

KODAAI; erişilebilir teknoloji, ses öncelikli sistemler, eğitim ve lokal yapay zekâ alanlarında Ar-Ge yürütür.

Project website: https://kodaai.com.tr

Designed and developed by Murat GUNEY LARRANAGA.

Copyright 2026 KODAAI / Murat GUNEY LARRANAGA.

## License and Usage

This repository is published for research, evaluation, and collaboration purposes. No license is currently granted for commercial use, redistribution, sublicensing, or incorporation into commercial products without prior written permission.

Collaboration and licensing: https://kodaai.com.tr
