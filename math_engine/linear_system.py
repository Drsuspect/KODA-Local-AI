from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class LinearSystemResult:
    handled: bool
    classification: str | None = None
    x: Fraction | None = None
    y: Fraction | None = None
    answer: str | None = None
    steps: tuple[str, ...] = ()


class LinearSystemEngine:
    """
    Deterministic 2x2 linear system solver.

    Supported form examples:
        x + y = 10 ve x - y = 2
        2x + 3y = 12 ve x - y = 1
    """

    def solve(self, text: str) -> LinearSystemResult:
        equations = self._extract_two_equations(text)

        if equations is None:
            return LinearSystemResult(handled=False)

        first, second = equations

        parsed1 = self._parse_equation(first)
        parsed2 = self._parse_equation(second)

        if parsed1 is None or parsed2 is None:
            return LinearSystemResult(handled=False)

        a1, b1, c1 = parsed1
        a2, b2, c2 = parsed2

        det = a1 * b2 - a2 * b1

        if det != 0:
            x = Fraction(c1 * b2 - c2 * b1, det)
            y = Fraction(a1 * c2 - a2 * c1, det)

            x_text = self._fmt(x)
            y_text = self._fmt(y)

            return LinearSystemResult(
                handled=True,
                classification="unique_solution",
                x=x,
                y=y,
                answer=f"x = {x_text}, y = {y_text}",
                steps=(
                    f"Birinci denklem: {first}",
                    f"\u0130kinci denklem: {second}",
                    "Denklem sistemi determinant y\u00f6ntemiyle \u00e7\u00f6z\u00fcld\u00fc.",
                    f"x = {x_text}",
                    f"y = {y_text}",
                ),
            )

        same_x = a1 * c2 == a2 * c1
        same_y = b1 * c2 == b2 * c1

        if same_x and same_y:
            return LinearSystemResult(
                handled=True,
                classification="infinite_solutions",
                answer=(
                    "Bu iki denklem birbirine ba\u011f\u0131ml\u0131d\u0131r. "
                    "Sistem sonsuz say\u0131da \u00e7\u00f6z\u00fcm i\u00e7erir."
                ),
            )

        return LinearSystemResult(
            handled=True,
            classification="no_solution",
            answer=(
                "Bu iki denklem birbiriyle \u00e7eli\u015fkilidir. "
                "Sistemin \u00e7\u00f6z\u00fcm\u00fc yoktur."
            ),
        )

    def _extract_two_equations(
        self,
        text: str,
    ) -> tuple[str, str] | None:
        if not text or not text.strip():
            return None

        value = text.casefold()

        s = chr(0x015f)
        i_dotless = chr(0x0131)

        value = value.replace("e" + s + "ittir", "=")
        value = value.replace("esittir", "=")
        value = value.replace("art" + i_dotless, "+")
        value = value.replace("arti", "+")
        value = value.replace("eksi", "-")

        value = re.split(
            r"\bise\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        parts = re.split(
            r"\bve\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )

        if len(parts) != 2:
            return None

        first = parts[0].strip(" ,;")
        second = parts[1].strip(" ,;")

        if first.count("=") != 1 or second.count("=") != 1:
            return None

        return first, second

    def _parse_equation(
        self,
        equation: str,
    ) -> tuple[int, int, int] | None:
        compact = equation.replace(" ", "")

        if "=" not in compact:
            return None

        left, right = compact.split("=", 1)

        if not re.fullmatch(r"[0-9xy+\-]*", left):
            return None

        if not re.fullmatch(r"-?\d+", right):
            return None

        a, b = self._parse_side(left)

        if a is None or b is None:
            return None

        return a, b, int(right)

    def _parse_side(
        self,
        side: str,
    ) -> tuple[int | None, int | None]:
        normalized = side

        if normalized and normalized[0] not in "+-":
            normalized = "+" + normalized

        tokens = re.findall(r"[+-][^+-]+", normalized)

        a = 0
        b = 0

        for token in tokens:
            sign = -1 if token[0] == "-" else 1
            body = token[1:]

            if body.endswith("x"):
                coeff = body[:-1]
                coeff_value = 1 if coeff == "" else int(coeff)
                a += sign * coeff_value

            elif body.endswith("y"):
                coeff = body[:-1]
                coeff_value = 1 if coeff == "" else int(coeff)
                b += sign * coeff_value

            else:
                return None, None

        return a, b

    @staticmethod
    def _fmt(value: Fraction) -> str:
        if value.denominator == 1:
            return str(value.numerator)

        return f"{value.numerator}/{value.denominator}"
