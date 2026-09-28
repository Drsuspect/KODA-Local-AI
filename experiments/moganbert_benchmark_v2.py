"""KODAAI MoganBERT Benchmark V2 - real corpus A/B retrieval test.

Production RAG koduna dokunmaz. Ayni corpus ve gold soru setini iki AYRI
Chroma indexinde MiniLM ve MoganBERT-Embed ile karsilastirir.

Corpus JSONL:
  {"id":"bio_001","text":"...","source":"..."}
Gold JSONL:
  {"query":"...","expected_id":"bio_001"}

Calistirma:
  python experiments/moganbert_benchmark_v2.py \
    --corpus experiments/data/biography_corpus.jsonl \
    --gold experiments/data/biography_gold.jsonl
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASELINE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHALLENGER = "moganai/MoganBERT-Embed"
TOP_K = (1, 3, 5)


@dataclass
class ModelResult:
    model: str
    collection: str
    corpus_count: int
    query_count: int
    load_seconds: float
    index_seconds: float
    query_ms_avg: float
    query_ms_p50: float
    query_ms_p95: float
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    ranks: list[int | None]
    failures: list[dict]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Dosya bulunamadi: {path}")
    rows = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no} gecersiz JSON: {exc}") from exc
    return rows


def validate(corpus: list[dict], gold: list[dict]) -> None:
    ids = []
    for i, row in enumerate(corpus, 1):
        if not row.get("id") or not str(row.get("text", "")).strip():
            raise ValueError(f"Corpus satir {i}: id ve text zorunlu")
        ids.append(str(row["id"]))
    if len(ids) != len(set(ids)):
        raise ValueError("Corpus id degerleri benzersiz olmali")

    known = set(ids)
    for i, row in enumerate(gold, 1):
        if not str(row.get("query", "")).strip() or not row.get("expected_id"):
            raise ValueError(f"Gold satir {i}: query ve expected_id zorunlu")
        if str(row["expected_id"]) not in known:
            raise ValueError(
                f"Gold satir {i}: expected_id corpus'ta yok: {row['expected_id']}"
            )


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def run_model(
    model_name: str,
    label: str,
    corpus: list[dict],
    gold: list[dict],
    work_dir: Path,
) -> ModelResult:
    # Her model kendi embedding uzayina ve kendi Chroma dizinine sahiptir.
    db_dir = work_dir / label
    if db_dir.exists():
        shutil.rmtree(db_dir)
    db_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    model = SentenceTransformer(model_name)
    load_seconds = time.perf_counter() - t0

    client = chromadb.PersistentClient(path=str(db_dir))
    collection_name = f"koda_bio_{label}"
    collection = client.create_collection(
        name=collection_name,
        metadata={"benchmark": "KODAAI MoganBERT V2", "model": model_name},
    )

    ids = [str(row["id"]) for row in corpus]
    documents = [str(row["text"]) for row in corpus]
    metadatas = [
        {"source": str(row.get("source", "")), "gold_id": str(row["id"])}
        for row in corpus
    ]

    t1 = time.perf_counter()
    embeddings = model.encode(
        documents,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    index_seconds = time.perf_counter() - t1

    ranks: list[int | None] = []
    latencies_ms: list[float] = []
    failures: list[dict] = []
    max_results = min(max(TOP_K), len(corpus))

    for item in gold:
        query = str(item["query"])
        expected = str(item["expected_id"])

        q0 = time.perf_counter()
        q_emb = model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        ).tolist()
        result = collection.query(
            query_embeddings=q_emb,
            n_results=max_results,
            include=["distances"],
        )
        latencies_ms.append((time.perf_counter() - q0) * 1000)

        ranked_ids = result.get("ids", [[]])[0]
        rank = ranked_ids.index(expected) + 1 if expected in ranked_ids else None
        ranks.append(rank)
        if rank != 1:
            failures.append(
                {
                    "query": query,
                    "expected_id": expected,
                    "rank": rank,
                    "top_ids": ranked_ids,
                }
            )

    recalls = {
        k: sum(rank is not None and rank <= k for rank in ranks) / len(ranks)
        for k in TOP_K
    }
    mrr = sum(0.0 if rank is None else 1.0 / rank for rank in ranks) / len(ranks)

    return ModelResult(
        model=model_name,
        collection=collection_name,
        corpus_count=len(corpus),
        query_count=len(gold),
        load_seconds=round(load_seconds, 3),
        index_seconds=round(index_seconds, 3),
        query_ms_avg=round(statistics.mean(latencies_ms), 2),
        query_ms_p50=round(percentile(latencies_ms, 0.50), 2),
        query_ms_p95=round(percentile(latencies_ms, 0.95), 2),
        recall_at_1=round(recalls[1], 4),
        recall_at_3=round(recalls[3], 4),
        recall_at_5=round(recalls[5], 4),
        mrr=round(mrr, 4),
        ranks=ranks,
        failures=failures,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("experiments/.benchmark_chroma_v2"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/moganbert_benchmark_v2_result.json"),
    )
    args = parser.parse_args()

    corpus = load_jsonl(args.corpus)
    gold = load_jsonl(args.gold)
    validate(corpus, gold)

    print(f"Corpus: {len(corpus)} kayit | Gold soru: {len(gold)}")
    if len(gold) < 50:
        print("UYARI: Karar benchmark'i icin en az 50 gold soru oneriliyor.")

    results = [
        run_model(BASELINE, "minilm", corpus, gold, args.work_dir),
        run_model(CHALLENGER, "moganbert", corpus, gold, args.work_dir),
    ]

    payload = {
        "benchmark": "KODAAI MoganBERT Benchmark V2",
        "corpus_file": str(args.corpus),
        "gold_file": str(args.gold),
        "note": "Production retriever degistirilmedi; model indexleri ayridir.",
        "results": [asdict(result) for result in results],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for result in results:
        print("\n" + json.dumps(asdict(result), ensure_ascii=False, indent=2))
    print(f"\nSonuc yazildi: {args.output}")


if __name__ == "__main__":
    main()
