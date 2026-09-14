from __future__ import annotations

from dataclasses import dataclass

from .percentage_normalizer import (
    PercentageNormalizer,
    PercentageProblem,
)


@dataclass(frozen=True)
class PercentageResult:
    handled: bool
    intent: str | None = None
    base_value: float | int | None = None
    rate: float | int | None = None
    result: float | int | None = None
    unit: str | None = None
    object_name: str | None = None
    answer: str | None = None


class PercentageEngine:
    """
    KODAAI Percentage Engine V0.5

    Supported:
    - percentage_discount
    - percentage_increase
    - percentage_of
    - reverse_percentage_discount
    - reverse_percentage_increase
    """

    def __init__(self) -> None:
        self.normalizer = PercentageNormalizer()

    def handle(self, text: str) -> PercentageResult:
        problem = self.normalizer.detect(text)

        if problem is None:
            return PercentageResult(
                handled=False
            )

        value = self._calculate(problem)

        if value is None:
            return PercentageResult(
                handled=False
            )

        answer = self._build_answer(
            problem,
            value,
        )

        return PercentageResult(
            handled=True,
            intent=problem.intent,
            base_value=problem.base_value,
            rate=problem.rate,
            result=value,
            unit=problem.unit,
            object_name=problem.object_name,
            answer=answer,
        )

    def _calculate(
        self,
        problem: PercentageProblem,
    ) -> float | int | None:
        base = float(problem.base_value)
        rate = float(problem.rate)

        if problem.intent == "percentage_discount":
            result = base * (1 - rate / 100)

        elif problem.intent == "percentage_increase":
            result = base * (1 + rate / 100)

        elif problem.intent == "percentage_of":
            result = base * rate / 100

        elif problem.intent == "reverse_percentage_increase":
            denominator = 1 + rate / 100

            if denominator == 0:
                return None

            result = base / denominator

        elif problem.intent == "reverse_percentage_discount":
            denominator = 1 - rate / 100

            if denominator <= 0:
                return None

            result = base / denominator

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
        problem: PercentageProblem,
        value: float | int,
    ) -> str:
        unit = (
            f" {problem.unit}"
            if problem.unit
            else ""
        )

        if problem.intent == "percentage_discount":
            if problem.object_name:
                return (
                    f"{problem.object_name.capitalize()} için "
                    f"yüzde {problem.rate} indirimli değer "
                    f"{value}{unit}."
                )

            return (
                f"Yüzde {problem.rate} indirim sonrası "
                f"değer {value}{unit}."
            )

        if problem.intent == "percentage_increase":
            if problem.object_name:
                return (
                    f"{problem.object_name.capitalize()} için "
                    f"yüzde {problem.rate} artış sonrası "
                    f"değer {value}{unit}."
                )

            return (
                f"Yüzde {problem.rate} artış sonrası "
                f"değer {value}{unit}."
            )

        if problem.intent == "percentage_of":
            return (
                f"{problem.base_value} değerinin "
                f"yüzde {problem.rate} kadarı "
                f"{value}{unit}."
            )

        if problem.intent == "reverse_percentage_increase":
            return (
                f"Yüzde {problem.rate} artıştan önceki "
                f"değer {value}{unit}."
            )

        if problem.intent == "reverse_percentage_discount":
            return (
                f"Yüzde {problem.rate} indirimden önceki "
                f"değer {value}{unit}."
            )

        return f"Sonuç {value}{unit}."


if __name__ == "__main__":
    engine = PercentageEngine()

    tests = (
        (
            "100 liralık kitap %20 indirimle kaç lira olur",
            True,
            80,
        ),
        (
            "100 liraya %20 zam yapılırsa kaç lira olur",
            True,
            120,
        ),
        (
            "200'ün %15'i kaçtır",
            True,
            30,
        ),
        (
            "fiyatı %15 arttığında 230 TL olan ürünün %100 fiyatı nedir",
            True,
            200,
        ),
        (
            "%20 indirimden sonra 80 TL olan ürünün eski fiyatı nedir",
            True,
            100,
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
        "PERCENTAGE ENGINE V0.5:",
        "PASS" if failed == 0
        else f"FAIL ({failed})"
    )
