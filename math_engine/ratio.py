from __future__ import annotations

from dataclasses import dataclass

from .ratio_normalizer import (
    RatioNormalizer,
    RatioProblem,
)


@dataclass(frozen=True)
class RatioResult:
    handled: bool
    intent: str | None = None
    known_quantity: float | int | None = None
    known_value: float | int | None = None
    target_quantity: float | int | None = None
    result: float | int | None = None
    quantity_unit: str | None = None
    value_unit: str | None = None
    answer: str | None = None


class RatioEngine:
    """
    KODAAI Ratio / Proportion Engine V0.6

    Supported:
    - direct_proportion
    - inverse_proportion
    """

    def __init__(self) -> None:
        self.normalizer = RatioNormalizer()

    def handle(self, text: str) -> RatioResult:
        problem = self.normalizer.detect(text)

        if problem is None:
            return RatioResult(
                handled=False
            )

        result = self._calculate(problem)

        if result is None:
            return RatioResult(
                handled=False
            )

        return RatioResult(
            handled=True,
            intent=problem.intent,
            known_quantity=problem.known_quantity,
            known_value=problem.known_value,
            target_quantity=problem.target_quantity,
            result=result,
            quantity_unit=problem.quantity_unit,
            value_unit=problem.value_unit,
            answer=self._build_answer(
                problem,
                result,
            ),
        )

    def _calculate(
        self,
        problem: RatioProblem,
    ) -> float | int | None:
        known_quantity = float(
            problem.known_quantity
        )

        known_value = float(
            problem.known_value
        )

        if known_quantity == 0:
            return None

        if problem.intent == "direct_proportion":
            if problem.target_quantity is None:
                return None

            target_quantity = float(
                problem.target_quantity
            )

            if target_quantity == 0:
                return None

            result = (
                known_value
                * target_quantity
                / known_quantity
            )

        elif problem.intent == "inverse_proportion":
            if problem.target_quantity is None:
                return None

            target_quantity = float(
                problem.target_quantity
            )

            if target_quantity == 0:
                return None

            result = (
                known_quantity
                * known_value
                / target_quantity
            )

        elif problem.intent == "direct_proportion_reverse":
            if problem.target_value is None:
                return None

            target_value = float(
                problem.target_value
            )

            if known_value == 0:
                return None

            result = (
                known_quantity
                * target_value
                / known_value
            )

        elif problem.intent == "inverse_proportion_reverse":
            if problem.target_value is None:
                return None

            target_value = float(
                problem.target_value
            )

            if target_value == 0:
                return None

            result = (
                known_quantity
                * known_value
                / target_value
            )

        else:
            return None

        return self._clean_number(result)

    @staticmethod
    def _clean_number(
        value: float,
    ) -> float | int:
        rounded = round(value, 10)

        if float(rounded).is_integer():
            return int(rounded)

        return rounded

    def _build_answer(
        self,
        problem: RatioProblem,
        value: float | int,
    ) -> str:
        if problem.intent in (
            "direct_proportion_reverse",
            "inverse_proportion_reverse",
        ):
            quantity_unit = (
                f" {problem.quantity_unit}"
                if problem.quantity_unit
                else ""
            )

            return (
                f"Sonuç {value}{quantity_unit}."
            )

        value_unit = (
            f" {problem.value_unit}"
            if problem.value_unit
            else ""
        )

        return (
            f"Sonuç {value}{value_unit}."
        )

if __name__ == "__main__":
    engine = RatioEngine()

    tests = (
        (
            "3 kalem 30 TL ise 5 kalem kaç TL",
            True,
            50,
        ),
        (
            "4 kitap 200 lira ise 10 kitap kaç liradır",
            True,
            500,
        ),
        (
            "12 yumurta 60 TL ise 6 yumurta kaç TL",
            True,
            30,
        ),
        (
            "4 işçi işi 12 günde bitiriyorsa 6 işçi kaç günde bitirir",
            True,
            8,
        ),
        (
            "3 makine işi 20 saatte yapıyorsa 5 makine kaç saatte yapar",
            True,
            12,
        ),
        (
            "Türkiye'nin başkenti neresidir",
            False,
            None,
        ),
    )

    failed = 0

    for question, expected_handled, expected_result in tests:
        try:
            output = engine.handle(question)

            passed = (
                output.handled == expected_handled
                and output.result == expected_result
            )

            if not passed:
                failed += 1

            print(
                "PASS" if passed else "FAIL",
                "|",
                question,
            )
            print("   =>", output)

        except Exception as exc:
            failed += 1

            print(
                "FAIL",
                "|",
                question,
                "=>",
                repr(exc),
            )

    print()

    print(
        "RATIO ENGINE V0.6:",
        "PASS" if failed == 0
        else f"FAIL ({failed})"
    )
