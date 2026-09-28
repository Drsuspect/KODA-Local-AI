from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_REASONING = {
    "id", "subject", "question", "options",
    "correct_answer", "pedagogy", "source", "validation",
}
OPTION_KEYS = {"A", "B", "C", "D", "E"}


def validate_reasoning(row: dict) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_REASONING - set(row)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
        return errors

    options = row.get("options")
    if not isinstance(options, dict) or set(options) != OPTION_KEYS:
        errors.append("options must contain exactly A,B,C,D,E")
        return errors

    correct = row.get("correct_answer")
    if correct not in OPTION_KEYS:
        errors.append("correct_answer must be A-E")

    true_options = [
        key for key, value in options.items()
        if isinstance(value, dict) and value.get("is_correct") is True
    ]
    if true_options != [correct]:
        errors.append(
            f"is_correct mismatch: expected only {correct}, got {true_options}"
        )

    for key, value in options.items():
        if not isinstance(value, dict):
            errors.append(f"option {key} must be object")
            continue
        for required in ("text", "is_correct", "reason"):
            if required not in value:
                errors.append(f"option {key} missing {required}")

    pedagogy = row.get("pedagogy") or {}
    for required in ("hint", "explain", "check_understanding"):
        if not str(pedagogy.get(required) or "").strip():
            errors.append(f"pedagogy missing/empty {required}")

    split = row.get("split")
    if split not in (None, "train", "dev", "benchmark"):
        errors.append("split must be train/dev/benchmark")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument(
        "--type",
        choices=["reasoning"],
        default="reasoning",
    )
    args = parser.parse_args()

    path = Path(args.file)
    failures = 0
    rows = 0

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        rows += 1
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            failures += 1
            print(f"{lineno}: invalid JSON: {exc}")
            continue

        errors = validate_reasoning(row)
        if errors:
            failures += 1
            print(f"{lineno}: " + "; ".join(errors))

    print(f"rows={rows} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
