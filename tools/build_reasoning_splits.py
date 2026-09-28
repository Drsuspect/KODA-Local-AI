from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        rows.append(row)
    return rows


def stable_key(row: dict, salt: str) -> str:
    raw = f"{salt}|{row.get('subject','')}|{row.get('id','')}|{row.get('question','')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def allocate(group: list[dict], train_ratio: float, dev_ratio: float) -> dict[str, list[dict]]:
    n = len(group)
    if n == 0:
        return {"train": [], "dev": [], "benchmark": []}

    train_n = round(n * train_ratio)
    dev_n = round(n * dev_ratio)

    if n >= 3:
        train_n = max(1, min(train_n, n - 2))
        dev_n = max(1, min(dev_n, n - train_n - 1))
    elif n == 2:
        train_n, dev_n = 1, 0
    else:
        train_n, dev_n = 1, 0

    bench_n = n - train_n - dev_n

    return {
        "train": group[:train_n],
        "dev": group[train_n:train_n + dev_n],
        "benchmark": group[train_n + dev_n:train_n + dev_n + bench_n],
    }


def write_jsonl(path: Path, rows: list[dict], split: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            item = dict(row)
            item["split"] = split
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out-dir", default="training_data/splits")
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--dev-ratio", type=float, default=0.15)
    parser.add_argument("--salt", default="KODAAI_REASONING_V1")
    args = parser.parse_args()

    if not (0 < args.train_ratio < 1):
        raise SystemExit("train-ratio must be between 0 and 1")
    if not (0 <= args.dev_ratio < 1):
        raise SystemExit("dev-ratio must be between 0 and 1")
    if args.train_ratio + args.dev_ratio >= 1:
        raise SystemExit("train-ratio + dev-ratio must be < 1")

    rows = load_jsonl(Path(args.input))
    by_subject: dict[str, list[dict]] = defaultdict(list)

    for row in rows:
        subject = str(row.get("subject") or "UNKNOWN").strip()
        by_subject[subject].append(row)

    final = {"train": [], "dev": [], "benchmark": []}

    for subject, group in sorted(by_subject.items()):
        group = sorted(group, key=lambda row: stable_key(row, args.salt))
        allocated = allocate(group, args.train_ratio, args.dev_ratio)
        for split, items in allocated.items():
            final[split].extend(items)

    out_dir = Path(args.out_dir)
    for split, items in final.items():
        items.sort(key=lambda row: (str(row.get("subject")), str(row.get("id"))))
        write_jsonl(out_dir / f"{split}.jsonl", items, split)

    print(" ".join(f"{split}={len(items)}" for split, items in final.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
