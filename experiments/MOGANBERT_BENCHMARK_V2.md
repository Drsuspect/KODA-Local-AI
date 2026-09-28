# KODAAI MoganBERT Benchmark V2

Bu deney production RAG koduna dokunmadan MiniLM ve MoganBERT-Embed'i ayni gercek corpus ve ayni gold soru seti uzerinde karsilastirir.

## Veri formati

- `biography_corpus.jsonl`: her satir `id`, `text`, istege bagli `source`.
- `biography_gold.jsonl`: her satir `query` ve corpus'taki dogru `expected_id`.
- Karar testi icin en az 50, tercihen 100 gold soru kullanin.
- Kolay dogrudan sorularla birlikte isim/ifade birebir gecmeyen semantik ve paraphrase sorular ekleyin.

## Calistirma

```powershell
python .\experiments\moganbert_benchmark_v2.py --corpus .\experiments\data\biography_corpus.jsonl --gold .\experiments\data\biography_gold.jsonl
```

## Izolasyon

Her model icin ayri Chroma dizini ve collection olusturulur. MiniLM index'i Mogan embedding'leriyle yeniden kullanilmaz. Production `rag/chroma_retriever.py` degistirilmez.

## Metrikler

Recall@1/3/5, MRR, model yukleme suresi, indexleme suresi, ortalama/p50/p95 sorgu gecikmesi ve rank-1 olmayan sorgular kaydedilir.
