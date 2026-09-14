from __future__ import annotations

import re
from dataclasses import dataclass

from .evaluator import MathEngine


@dataclass(frozen=True)
class MathIntent:
    is_math: bool
    expression: str | None = None


class MathIntentDetector:
    """
    KODAAI Math Engine - deterministic expression detector.

    Only explicit arithmetic expressions are captured.
    Explanatory/lesson questions remain available to RAG.
    """

    def __init__(self) -> None:
        self.engine = MathEngine()

    def detect(self, text: str) -> MathIntent:
        if not text or not text.strip():
            return MathIntent(False)

        value = text.strip()

        # Find an explicit arithmetic expression beginning with a number
        # or an opening parenthesis.
        candidates = re.findall(
            r"(?:\(\s*)?-?\d+(?:[.,]\d+)?"
            r"(?:\s*(?:[xX*+\-/×÷]|\bçarpı\b|\bcarpi\b|\bartı\b|\barti\b|\beksi\b|\bbölü\b|\bbolu\b)"
            r"\s*(?:\(\s*)?-?\d+(?:[.,]\d+)?\s*\)?)+",
            value,
            flags=re.IGNORECASE,
        )

        for candidate in candidates:
            candidate = candidate.strip()

            if self.engine.looks_like_expression(candidate):
                return MathIntent(
                    is_math=True,
                    expression=candidate,
                )

        return MathIntent(False)


if __name__ == "__main__":
    detector = MathIntentDetector()

    tests = (
        ("6 x 2 + 6", True),
        ("6 x 2 + 6 işleminin sonucu nedir", True),
        ("6 x 2 + 6 işleminin sonucu ne olur", True),
        ("20 / 4 + 3 kaç eder", True),
        ("Türkiye'nin başkenti neresidir", False),
        ("işlem önceliğini anlat", False),
        ("yüzde hesabı nasıl yapılır", False),
    )

    failed = 0

    for question, expected in tests:
        result = detector.detect(question)
        passed = result.is_math == expected

        if not passed:
            failed += 1

        print(
            "PASS" if passed else "FAIL",
            "|",
            question,
            "=>",
            result,
        )

    print()
    print(
        "MATH INTENT V0.2:",
        "PASS" if failed == 0 else f"FAIL ({failed})"
    )
