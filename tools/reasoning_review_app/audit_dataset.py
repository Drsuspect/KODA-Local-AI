from __future__ import annotations

import argparse
import json
from pathlib import Path

from grammar_engine import analyze_record as grammar_analyze
from pedagogy_engine import analyze_record as pedagogy_analyze


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    path = Path(args.file)
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if args.limit:
        rows = rows[:args.limit]

    blocked = 0
    warnings = 0
    for row in rows:
        g = grammar_analyze(row)
        p = pedagogy_analyze(row)
        if g["status"] == "fail" or p["readiness"] == "blocked":
            blocked += 1
        if g["status"] == "warn" or p["readiness"] == "review":
            warnings += 1
        print(json.dumps({
            "id": row.get("id"),
            "grammar": g["status"],
            "pedagogy": p["readiness"],
            "grammar_findings": len(g["findings"]),
            "pedagogy_findings": len(p["findings"]),
        }, ensure_ascii=False))

    print(f"rows={len(rows)} blocked={blocked} warnings={warnings}")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
