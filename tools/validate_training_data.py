from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_REASONING = {
    "id", "subject", "question", "options",
    "correct_answer", "pedagogy", "source", "validation",
}
OPTION_KEYS = {"A", "B", "C", "D", "E"}

REQUIRED_ACCESSIBILITY = {
    "id", "content_type", "source_text", "accessible_text",
    "tts_text", "standards", "validation",
}

REQUIRED_VOICE = {
    "id", "canonical_text", "intent", "category",
    "audio_ref", "conditions", "split",
}

VALID_SPLITS = {None, "train", "dev", "benchmark"}


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
        if isinstance(value, dict) and not str(value.get("reason") or "").strip():
            errors.append(f"option {key} reason must not be empty")

    pedagogy = row.get("pedagogy") or {}
    for required in ("hint", "explain", "check_understanding"):
        if not str(pedagogy.get(required) or "").strip():
            errors.append(f"pedagogy missing/empty {required}")

    if row.get("split") not in VALID_SPLITS:
        errors.append("split must be train/dev/benchmark")

    return errors


def validate_accessibility(row: dict) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_ACCESSIBILITY - set(row)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
        return errors

    for field in ("source_text", "accessible_text", "tts_text"):
        if not str(row.get(field) or "").strip():
            errors.append(f"{field} must not be empty")

    standards = row.get("standards")
    if not isinstance(standards, list) or not standards:
        errors.append("standards must be a non-empty list")

    validation = row.get("validation") or {}
    if validation.get("status") not in {"draft", "reviewed", "verified"}:
        errors.append("validation.status must be draft/reviewed/verified")

    if row.get("split") not in VALID_SPLITS:
        errors.append("split must be train/dev/benchmark")

    return errors


def validate_voice(row: dict) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_VOICE - set(row)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
        return errors

    for field in ("canonical_text", "intent", "category", "audio_ref"):
        if not str(row.get(field) or "").strip():
            errors.append(f"{field} must not be empty")

    conditions = row.get("conditions")
    if not isinstance(conditions, dict):
        errors.append("conditions must be an object")
    else:
        noise = conditions.get("noise")
        if noise not in {"clean", "low", "medium", "high", "unknown"}:
            errors.append("conditions.noise invalid")

    if row.get("split") not in {"train", "dev", "benchmark"}:
        errors.append("split must be train/dev/benchmark")

    return errors


VALIDATORS = {
    "reasoning": validate_reasoning,
    "accessibility": validate_accessibility,
    "voice": validate_voice,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument(
        "--type",
        choices=sorted(VALIDATORS),
        default="reasoning",
    )
    args = parser.parse_args()

    path = Path(args.file)
    validator = VALIDATORS[args.type]
    failures = 0
    rows = 0
    ids: set[str] = set()

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

        row_id = str(row.get("id") or "").strip()
        errors = validator(row)

        if not row_id:
            errors.append("id must not be empty")
        elif row_id in ids:
            errors.append(f"duplicate id: {row_id}")
        else:
            ids.add(row_id)

        if errors:
            failures += 1
            print(f"{lineno}: " + "; ".join(errors))

    print(
        f"type={args.type} rows={rows} unique_ids={len(ids)} "
        f"failures={failures}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
