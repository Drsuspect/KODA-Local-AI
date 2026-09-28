"""KODAAI embedding A/B benchmark.

Production RAG koduna dokunmaz. Mevcut multilingual MiniLM ile
moganai/MoganBERT-Embed'i ayni Turkce retrieval setinde karsilastirir.

Calistirma:
    python experiments/moganbert_embed_benchmark.py
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

BASELINE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHALLENGER = "moganai/MoganBERT-Embed"
TOP_K = (1, 3, 5)

CORPUS = [
    ("ataturk_samsun", "Mustafa Kemal Atatürk 19 Mayıs 1919 tarihinde Samsun'a çıktı. Bu gelişme Milli Mücadele sürecinin başlangıcı kabul edilir."),
    ("ankara_baskent", "Ankara, 13 Ekim 1923 tarihinde Türkiye'nin başkenti ilan edildi."),
    ("tbmm_acilis", "Türkiye Büyük Millet Meclisi 23 Nisan 1920 tarihinde Ankara'da açıldı."),
    ("cumhuriyet", "Türkiye Cumhuriyeti 29 Ekim 1923 tarihinde ilan edildi."),
    ("sakarya", "Sakarya Meydan Muharebesi 23 Ağustos ile 13 Eylül 1921 tarihleri arasında gerçekleşti."),
    ("buyuk_taarruz", "Büyük Taarruz 26 Ağustos 1922 tarihinde başladı ve 30 Ağustos'ta Başkomutanlık Meydan Muharebesi kazanıldı."),
    ("lozan", "Lozan Barış Antlaşması 24 Temmuz 1923 tarihinde imzalandı."),
    ("saltanat", "Saltanat 1 Kasım 1922 tarihinde Türkiye Büyük Millet Meclisi kararıyla kaldırıldı."),
    ("istiklal_marsi", "İstiklal Marşı 12 Mart 1921 tarihinde Türkiye Büyük Millet Meclisi tarafından kabul edildi."),
    ("amasya", "Amasya Genelgesi 22 Haziran 1919 tarihinde yayımlandı ve Milli Mücadele'nin gerekçe, amaç ve yöntemini açıkladı."),
]

QUERIES = [
    ("Milli Mücadele'nin fiilen başlangıcı sayılan olay nedir?", "ataturk_samsun"),
    ("Türkiye'nin yönetim merkezinin Ankara olması ne zaman kararlaştırıldı?", "ankara_baskent"),
    ("Ulusal meclis Ankara'da hangi tarihte faaliyete geçti?", "tbmm_acilis"),
    ("Cumhuriyet yönetimine hangi tarihte geçildi?", "cumhuriyet"),
    ("1921'de yaklaşık üç hafta süren meydan savaşı hangisidir?", "sakarya"),
    ("30 Ağustos zaferine giden askeri harekat ne zaman başladı?", "buyuk_taarruz"),
    ("Yeni Türk devletinin uluslararası tanınmasında temel antlaşma hangisidir?", "lozan"),
    ("Osmanlı hanedanının siyasi egemenliğine hangi kararla son verildi?", "saltanat"),
    ("Mehmet Akif'in yazdığı milli marş ne zaman kabul edildi?", "istiklal_marsi"),
    ("Milli Mücadele'nin gerekçe amaç ve yöntemini açıklayan belge hangisidir?", "amasya"),
]


@dataclass
class Result:
    model: str
    load_seconds: float
    query_seconds: float
    recall: dict[int, float]
    mrr: float
    ranks: list[int | None]


def benchmark(model_name: str) -> Result:
    t0 = time.perf_counter()
    model = SentenceTransformer(model_name)
    load_seconds = time.perf_counter() - t0

    docs = [text for _, text in CORPUS]
    doc_ids = [doc_id for doc_id, _ in CORPUS]
    doc_emb = model.encode(docs, convert_to_numpy=True, normalize_embeddings=True)

    ranks: list[int | None] = []
    t1 = time.perf_counter()
    for query, expected in QUERIES:
        q = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        scores = np.dot(doc_emb, q)
        order = np.argsort(-scores)
        ranked_ids = [doc_ids[i] for i in order]
        ranks.append(ranked_ids.index(expected) + 1 if expected in ranked_ids else None)
    query_seconds = time.perf_counter() - t1

    recall = {
        k: sum(r is not None and r <= k for r in ranks) / len(ranks)
        for k in TOP_K
    }
    mrr = sum(0.0 if r is None else 1.0 / r for r in ranks) / len(ranks)
    return Result(model_name, load_seconds, query_seconds, recall, mrr, ranks)


def main() -> None:
    results = [benchmark(BASELINE), benchmark(CHALLENGER)]
    payload = []
    for r in results:
        row = {
            "model": r.model,
            "load_seconds": round(r.load_seconds, 3),
            "query_seconds_total": round(r.query_seconds, 3),
            "query_ms_avg": round(r.query_seconds * 1000 / len(QUERIES), 2),
            "recall_at_1": round(r.recall[1], 4),
            "recall_at_3": round(r.recall[3], 4),
            "recall_at_5": round(r.recall[5], 4),
            "mrr": round(r.mrr, 4),
            "ranks": r.ranks,
        }
        payload.append(row)
        print(json.dumps(row, ensure_ascii=False, indent=2))

    out = Path("experiments/moganbert_embed_benchmark_result.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSonuc yazildi: {out}")


if __name__ == "__main__":
    main()
