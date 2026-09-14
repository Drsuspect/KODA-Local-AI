from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MathResult:
    expression: str
    normalized_expression: str
    result: int | float
    accessible_answer: str


class MathEngine:
    """
    KODAAI Math Engine V0.1

    Supported:
    - addition
    - subtraction
    - multiplication
    - division
    - parentheses
    - normal arithmetic precedence

    Python eval() is deliberately NOT used.
    """

    _binary_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    _unary_operators = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def normalize(self, expression: str) -> str:
        value = expression.strip()

        # Unicode / spoken multiplication variants.
        value = value.replace("\u00d7", "*")
        value = value.replace("\u00f7", "/")

        # x or X is multiplication when it occurs between
        # numeric values or parenthesized arithmetic groups.
        value = re.sub(
            r"(?<=[\d)])\s*[xX]\s*(?=[\d(])",
            "*",
            value,
        )

        # Turkish spoken operators.
        replacements = (
            (r"\bcarpi\b", "*"),
            (r"\bçarpı\b", "*"),
            (r"\barti\b", "+"),
            (r"\bartı\b", "+"),
            (r"\beksi\b", "-"),
            (r"\bbolu\b", "/"),
            (r"\bbölü\b", "/"),
        )

        for pattern, replacement in replacements:
            value = re.sub(
                pattern,
                replacement,
                value,
                flags=re.IGNORECASE,
            )

        value = re.sub(r"\s+", " ", value).strip()

        return value

    def looks_like_expression(self, text: str) -> bool:
        normalized = self.normalize(text)

        return bool(
            re.fullmatch(
                r"[\d\s\.\,\+\-\*\/\(\)]+",
                normalized,
            )
            and re.search(r"[\+\-\*\/]", normalized)
        )

    def evaluate(self, expression: str) -> MathResult:
        normalized = self.normalize(expression)

        # Turkish decimal comma support.
        normalized = re.sub(
            r"(?<=\d),(?=\d)",
            ".",
            normalized,
        )

        if not re.fullmatch(
            r"[\d\s\.\+\-\*\/\(\)]+",
            normalized,
        ):
            raise ValueError(
                "Desteklenmeyen matematiksel ifade."
            )

        try:
            tree = ast.parse(normalized, mode="eval")
        except SyntaxError as exc:
            raise ValueError(
                "Matematiksel ifade çözümlenemedi."
            ) from exc

        result = self._evaluate_node(tree.body)

        if isinstance(result, float) and result.is_integer():
            result = int(result)

        return MathResult(
            expression=expression,
            normalized_expression=normalized,
            result=result,
            accessible_answer=self._accessible_result(result),
        )

    def _evaluate_node(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                raise ValueError("Geçersiz sayı.")

            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError("Geçersiz sabit.")

        if isinstance(node, ast.BinOp):
            operator_type = type(node.op)

            if operator_type not in self._binary_operators:
                raise ValueError(
                    "Desteklenmeyen matematik işlemi."
                )

            left = self._evaluate_node(node.left)
            right = self._evaluate_node(node.right)

            if operator_type is ast.Div and right == 0:
                raise ValueError("Sıfıra bölme yapılamaz.")

            return self._binary_operators[operator_type](
                left,
                right,
            )

        if isinstance(node, ast.UnaryOp):
            operator_type = type(node.op)

            if operator_type not in self._unary_operators:
                raise ValueError(
                    "Desteklenmeyen tekli işlem."
                )

            operand = self._evaluate_node(node.operand)

            return self._unary_operators[operator_type](
                operand
            )

        raise ValueError(
            "İfade güvenli matematik kapsamının dışında."
        )

    @staticmethod
    def _accessible_result(result: int | float) -> str:
        return f"Sonuç {result}."


if __name__ == "__main__":
    engine = MathEngine()

    tests = (
        ("6 x 2 + 6", 18),
        ("6 + 2 x 6", 18),
        ("(6 + 2) x 6", 48),
        ("20 / 4 + 3", 8),
        ("20 - 3 * 4", 8),
        ("-5 + 8", 3),
        ("7,5 + 2,5", 10),
    )

    failed = 0

    for expression, expected in tests:
        try:
            answer = engine.evaluate(expression)
            passed = answer.result == expected

            if not passed:
                failed += 1

            print(
                "PASS" if passed else "FAIL",
                "|",
                expression,
                "=>",
                answer.result,
                "| expected:",
                expected,
            )

        except Exception as exc:
            failed += 1
            print(
                "FAIL",
                "|",
                expression,
                "=>",
                repr(exc),
            )

    print()
    print(
        "MATH ENGINE V0.1:",
        "PASS" if failed == 0 else f"FAIL ({failed})"
    )
