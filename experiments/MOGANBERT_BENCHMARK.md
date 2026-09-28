# MoganBERT-Embed A/B Benchmark v1

Bu deney production RAG akisini degistirmez.

## Amac
KODAAI'nin mevcut embedding modeli `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` ile `moganai/MoganBERT-Embed` modelini ayni Turkce retrieval sorularinda karsilastirmak.

## Metrikler
- Recall@1 / @3 / @5
- MRR
- model yukleme suresi
- ortalama query embedding + retrieval suresi

## Calistirma
```powershell
python .\experiments\moganbert_embed_benchmark.py
```

Ilk calistirmada Hugging Face model dosyalari indirilecegi icin internet gerekir. Sonraki calistirmalar yerel cache'i kullanabilir.

## Kabul kurali
Challenger otomatik olarak production'a alinmaz. Gercek KODAAI corpus benchmark'i tamamlanmadan `rag/chroma_retriever.py` varsayilani degistirilmez.

Bu v1 smoke setidir. Sonraki adim Biyografi ve KODAAI corpusundan etiketli sorgularla daha buyuk benchmark setidir.
