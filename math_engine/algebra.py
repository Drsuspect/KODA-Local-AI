from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class AlgebraResult:
    handled: bool
    equation: str | None = None
    variable: str | None = None
    classification: str | None = None
    solution: int | float | None = None
    steps: tuple[str, ...] = ()
    verified: bool = False
    answer: str | None = None


class AlgebraEngine:
    """
    KODAAI Basic Algebra Engine V0.13

    Supported:
    - x + b = c
    - x - b = c
    - ax = c
    - x / a = c
    - ax + b = c
    - ax - b = c
    - b + x = c
    - c = ax + b
    - x / a + b = c
    - negative coefficients and results
    - spaces and explicit multiplication

    Still out of scope:
    - x on both sides
    - parentheses
    - powers
    - absolute value
    - inequalities
    - multiple variables
    """

    _NUMBER = r"[+-]?\d+(?:\.\d+)?"
    _UNSIGNED_NUMBER = r"\d+(?:\.\d+)?"

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = text.strip().lower()

        normalized = (
            normalized
            .replace("\u00d7", "*")
            .replace("\u00f7", "/")
            .replace(",", ".")
            .replace(" ", "")
        )

        return normalized

    @staticmethod
    def _number(value: str) -> Fraction:
        return Fraction(value)

    @staticmethod
    def _turkish_dative_suffix(number_text: str) -> str:
        clean = number_text.lstrip("+-")

        if not clean:
            return "'e"

        integer_part = clean.split(".")[0]
        trimmed = integer_part.rstrip("0")

        last_digit = (
            trimmed[-1]
            if trimmed
            else "0"
        )

        suffix_map = {
            "0": "'a",
            "1": "'e",
            "2": "'ye",
            "3": "'e",
            "4": "'e",
            "5": "'e",
            "6": "'ya",
            "7": "'ye",
            "8": "'e",
            "9": "'a",
        }

        return suffix_map.get(last_digit, "'e")

    @staticmethod
    def _display_number(value: Fraction) -> str:
        if value.denominator == 1:
            return str(value.numerator)

        decimal_value = float(value)

        return (
            f"{decimal_value:.10f}"
            .rstrip("0")
            .rstrip(".")
        )

    @classmethod
    def _parse_side(
        cls,
        expression: str,
    ) -> tuple[Fraction, Fraction] | None:
        """
        Convert one equation side into:

            a*x + b

        Examples:
            12       -> (0, 12)
            x        -> (1, 0)
            3x       -> (3, 0)
            2x+4     -> (2, 4)
            x-5      -> (1, -5)
            x/3      -> (1/3, 0)
            x/4+2    -> (1/4, 2)
            5+x      -> (1, 5)
            5-2x     -> (-2, 5)
        """

        # V0.12: one distributive parenthesized term.
        #
        # Supported examples:
        #
        #     2(x+3)
        #     3(x-2)
        #     2(x+4)+3
        #     3(x-1)+2
        #
        # Convert:
        #
        #     k(x+b)+c
        #
        # into:
        #
        #     k*x + (k*b+c)
        #
        # Nested or multiple parenthesized terms remain
        # intentionally out of scope.
        match = re.fullmatch(
            rf"({cls._NUMBER})"
            rf"\*?"
            rf"\("
            rf"x"
            rf"([+-]{cls._UNSIGNED_NUMBER})?"
            rf"\)"
            rf"([+-]{cls._UNSIGNED_NUMBER})?",
            expression,
        )

        if match:
            multiplier = cls._number(
                match.group(1)
            )

            inner_constant = (
                cls._number(match.group(2))
                if match.group(2)
                else Fraction(0)
            )

            outer_constant = (
                cls._number(match.group(3))
                if match.group(3)
                else Fraction(0)
            )

            coefficient = multiplier

            constant = (
                multiplier * inner_constant
                + outer_constant
            )

            return coefficient, constant

        # Numeric constant.
        if re.fullmatch(
            cls._NUMBER,
            expression,
        ):
            return (
                Fraction(0),
                cls._number(expression),
            )

        # x / divisor, optionally followed by +/- constant.
        match = re.fullmatch(
            rf"x/({cls._NUMBER})"
            rf"([+-]{cls._UNSIGNED_NUMBER})?",
            expression,
        )

        if match:
            divisor = cls._number(
                match.group(1)
            )

            if divisor == 0:
                return None

            constant = (
                cls._number(match.group(2))
                if match.group(2)
                else Fraction(0)
            )

            return (
                Fraction(1) / divisor,
                constant,
            )

        # ax optionally followed by +/- constant.
        match = re.fullmatch(
            rf"([+-]?(?:{cls._UNSIGNED_NUMBER})?)"
            rf"\*?x"
            rf"([+-]{cls._UNSIGNED_NUMBER})?",
            expression,
        )

        if match:
            coefficient_text = match.group(1)
            constant_text = match.group(2)

            if coefficient_text in ("", "+"):
                coefficient = Fraction(1)
            elif coefficient_text == "-":
                coefficient = Fraction(-1)
            else:
                coefficient = cls._number(
                    coefficient_text
                )

            constant = (
                cls._number(constant_text)
                if constant_text
                else Fraction(0)
            )

            return coefficient, constant

        # Constant first:
        # 5+x, 5-x, 5+2x, 5-2x
        match = re.fullmatch(
            rf"({cls._NUMBER})"
            rf"([+-])"
            rf"({cls._UNSIGNED_NUMBER})?"
            rf"\*?x",
            expression,
        )

        if match:
            constant = cls._number(
                match.group(1)
            )

            operator = match.group(2)
            coefficient_text = match.group(3)

            coefficient = (
                cls._number(coefficient_text)
                if coefficient_text
                else Fraction(1)
            )

            if operator == "-":
                coefficient = -coefficient

            return coefficient, constant

        return None

    @staticmethod
    def _verify(
        left_a: Fraction,
        left_b: Fraction,
        right_a: Fraction,
        right_b: Fraction,
        solution: Fraction,
    ) -> bool:
        left_value = (
            left_a * solution
            + left_b
        )

        right_value = (
            right_a * solution
            + right_b
        )

        return left_value == right_value

    @classmethod
    def solve(cls, text: str) -> AlgebraResult:
        equation = cls._normalize(text)

        if equation.count("=") != 1:
            return AlgebraResult(
                handled=False
            )

        left_text, right_text = equation.split(
            "=",
            1,
        )

        left_parsed = cls._parse_side(
            left_text
        )

        right_parsed = cls._parse_side(
            right_text
        )

        if (
            left_parsed is None
            or right_parsed is None
        ):
            return AlgebraResult(
                handled=False
            )

        left_a, left_b = left_parsed
        right_a, right_b = right_parsed

        # V0.13 hardening:
        # A parsed zero coefficient does not always mean that
        # the original equation contained no variable.
        #
        # Examples:
        #
        #     0x+5=5
        #     0(x+3)=0
        #
        # Both contain x semantically, even though their parsed
        # x coefficient becomes zero.
        has_variable_symbol = (
            "x" in left_text
            or "x" in right_text
        )

        if (
            left_a == 0
            and right_a == 0
            and not has_variable_symbol
        ):
            return AlgebraResult(
                handled=False
            )

        steps: list[str] = []

        # V0.13: zero-coefficient equations that still contained
        # a variable symbol reduce to a constant identity or
        # contradiction.
        if (
            left_a == 0
            and right_a == 0
            and has_variable_symbol
        ):
            left_constant = cls._display_number(
                left_b
            )
            right_constant = cls._display_number(
                right_b
            )

            steps.append(
                f"{left_constant} = "
                f"{right_constant} elde edilir."
            )

            if left_b == right_b:
                steps.append(
                    "E\u015fitlik her x de\u011feri "
                    "i\u00e7in do\u011frudur."
                )

                return AlgebraResult(
                    handled=True,
                    equation=equation,
                    variable="x",
                    classification="infinite_solutions",
                    solution=None,
                    steps=tuple(steps),
                    verified=True,
                    answer=(
                        "Bu denklemin sonsuz say\u0131da "
                        "\u00e7\u00f6z\u00fcm\u00fc vard\u0131r."
                    ),
                )

            steps.append(
                "Bu e\u015fitlik do\u011fru de\u011fildir."
            )

            return AlgebraResult(
                handled=True,
                equation=equation,
                variable="x",
                classification="no_solution",
                solution=None,
                steps=tuple(steps),
                verified=True,
                answer=(
                    "Bu denklemin \u00e7\u00f6z\u00fcm\u00fc yoktur."
                ),
            )

        # V0.10: linear variable terms on both sides.
        #
        #     a1*x + b1 = a2*x + b2
        #
        # Move the right-side x term to the left:
        #
        #     (a1 - a2)*x + b1 = b2
        #
        # Original coefficients remain unchanged and are used
        # later by _verify().
        if (
            left_a != 0
            and right_a != 0
        ):
            variable_text = left_text

            a = left_a - right_a
            b = left_b
            c = right_b

            if a == 0:
                right_term = (
                    "x"
                    if abs(right_a) == 1
                    else f"{cls._display_number(abs(right_a))}x"
                )

                if right_a > 0:
                    steps.append(
                        f"Her iki taraftan "
                        f"{right_term} "
                        f"\u00e7\u0131kar."
                    )
                else:
                    steps.append(
                        f"Her iki tarafa "
                        f"{right_term} "
                        f"ekle."
                    )

                left_constant = cls._display_number(
                    left_b
                )
                right_constant = cls._display_number(
                    right_b
                )

                if left_b == right_b:
                    steps.append(
                        f"{left_constant} = "
                        f"{right_constant} elde edilir."
                    )
                    steps.append(
                        "E\u015fitlik her x de\u011feri "
                        "i\u00e7in do\u011frudur."
                    )

                    return AlgebraResult(
                        handled=True,
                        equation=equation,
                        variable="x",
                        classification="infinite_solutions",
                        solution=None,
                        steps=tuple(steps),
                        verified=True,
                        answer=(
                            "Bu denklemin sonsuz say\u0131da "
                            "\u00e7\u00f6z\u00fcm\u00fc vard\u0131r."
                        ),
                    )

                steps.append(
                    f"{left_constant} = "
                    f"{right_constant} elde edilir."
                )
                steps.append(
                    "Bu e\u015fitlik do\u011fru de\u011fildir."
                )

                return AlgebraResult(
                    handled=True,
                    equation=equation,
                    variable="x",
                    classification="no_solution",
                    solution=None,
                    steps=tuple(steps),
                    verified=True,
                    answer=(
                        "Bu denklemin \u00e7\u00f6z\u00fcm\u00fc "
                        "yoktur."
                    ),
                )

            right_term = (
                "x"
                if abs(right_a) == 1
                else f"{cls._display_number(abs(right_a))}x"
            )

            if right_a > 0:
                steps.append(
                    f"Her iki taraftan "
                    f"{right_term} "
                    f"\u00e7\u0131kar."
                )
            else:
                steps.append(
                    f"Her iki tarafa "
                    f"{right_term} "
                    f"ekle."
                )

        # Normalize internally so the variable
        # expression is on the left.
        elif left_a == 0:
            variable_text = right_text

            a = right_a
            b = right_b
            c = left_b

            steps.append(
                "Denklemin taraflar\u0131n\u0131 yer de\u011fi\u015ftir."
            )
        else:
            variable_text = left_text

            a = left_a
            b = left_b
            c = right_b

        if a == 0:
            return AlgebraResult(
                handled=False
            )

        current_right = c

        if b != 0:
            if b > 0:
                steps.append(
                    f"Her iki taraftan "
                    f"{cls._display_number(b)} "
                    f"\u00e7\u0131kar."
                )
            else:
                steps.append(
                    f"Her iki tarafa "
                    f"{cls._display_number(-b)} "
                    f"ekle."
                )

            current_right = c - b

            if a != 1:
                steps.append(
                    f"{cls._display_number(a)}x = "
                    f"{cls._display_number(current_right)}"
                )

        if a != 1:
            division_match = re.match(
                rf"^x/({cls._NUMBER})",
                variable_text,
            )

            if division_match:
                divisor_text = (
                    division_match.group(1)
                )

                steps.append(
                    f"Her iki taraf\u0131 "
                    f"{divisor_text} ile "
                    f"\u00e7arp."
                )
            else:
                divisor_text = (
                    cls._display_number(a)
                )

                suffix = (
                    cls._turkish_dative_suffix(
                        divisor_text
                    )
                )

                steps.append(
                    f"Her iki taraf\u0131 "
                    f"{divisor_text}{suffix} "
                    f"b\u00f6l."
                )

        solution = current_right / a

        solution_text = cls._display_number(
            solution
        )

        steps.append(
            f"x = {solution_text}"
        )

        verified = cls._verify(
            left_a=left_a,
            left_b=left_b,
            right_a=right_a,
            right_b=right_b,
            solution=solution,
        )

        numeric_solution: int | float

        if solution.denominator == 1:
            numeric_solution = (
                solution.numerator
            )
        else:
            numeric_solution = float(
                solution
            )

        return AlgebraResult(
            handled=True,
            equation=equation,
            variable="x",
            classification="unique_solution",
            solution=numeric_solution,
            steps=tuple(steps),
            verified=verified,
            answer=f"x = {solution_text}",
        )


if __name__ == "__main__":
    tests = (
        ("x+5=12", 7),
        ("x-4=9", 13),
        ("3x=18", 6),
        ("x/3=5", 15),
        ("2x+4=10", 3),
        ("3x-7=11", 6),
        ("5+x=12", 7),
        ("10=2x+4", 3),
        ("3*x=18", 6),
        ("-2x+4=10", -3),
        ("2x-5=-11", -3),
        ("x/4+2=5", 12),
        ("-x+5=2", 3),
        ("-3x=12", -4),
    )

    failed = 0

    for equation, expected in tests:
        result = AlgebraEngine.solve(
            equation
        )

        passed = (
            result.handled
            and result.solution == expected
            and result.verified
        )

        if not passed:
            failed += 1

        print(
            "PASS" if passed else "FAIL",
            "|",
            equation,
            "=>",
            result,
        )

    print()

    print(
        "ALGEBRA ENGINE V0.9:",
        "PASS"
        if failed == 0
        else f"FAIL ({failed})"
    )
