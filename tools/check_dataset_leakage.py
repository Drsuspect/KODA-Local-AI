from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").casefold().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s]", "", value, flags=re.UNICODE)
    return value


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        row["_source_file"] = str(path)
        row["_source_line"] = lineno
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check exact/normalized question leakage between JSONL datasets."
    )
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    seen_ids: dict[str, tuple[str, int]] = {}
    seen_questions: dict[str, tuple[str, int, str]] = {}
    failures = 0

    for file_name in args.files:
        path = Path(file_name)
        for row in load_jsonl(path):
            row_id = str(row.get("id") or "").strip()
            question = str(row.get("question") or "").strip()
            split = str(row.get("split") or "").strip()

            if row_id:
                if row_id in seen_ids:
                    prev_file, prev_line = seen_ids[row_id]
                    print(
                        f"DUPLICATE_ID {row_id}: "
                        f"{prev_file}:{prev_line} <-> "
                        f"{path}:{row['_source_line']}"
                    )
                    failures += 1
                else:
                    seen_ids[row_id] = (str(path), row["_source_line"])

            if question:
                key = normalize(question)
                if key in seen_questions:
                    prev_file, prev_line, prev_split = seen_questions[key]
                    print(
                        f"QUESTION_LEAKAGE split={prev_split}/{split}: "
                        f"{prev_file}:{prev_line} <-> "
                        f"{path}:{row['_source_line']}"
                    )
                    failures += 1
                else:
                    seen_questions[key] = (
                        str(path),
                        row["_source_line"],
                        split,
                    )

    print(
        f"files={len(args.files)} ids={len(seen_ids)} "
        f"questions={len(seen_questions)} failures={failures}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
