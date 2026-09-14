from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class RatioProblem:
    intent: str
    known_quantity: float
    known_value: float
    target_quantity: float | None = None
    target_value: float | None = None
    quantity_unit: str | None = None
    value_unit: str | None = None


class RatioNormalizer:
    """
    KODAAI Ratio / Proportion Normalizer V0.6

    Supported intents:
    - direct_proportion
    - inverse_proportion
    - direct_proportion_reverse
    - inverse_proportion_reverse
    """

    INVERSE_MARKERS = (
        "isci",
        "makine",
        "musluk",
        "hiz",
        "sure",
        "gunde",
        "saatte",
    )

    QUANTITY_QUESTION_MARKERS = (
        "kac kalem",
        "kac kitap",
        "kac urun",
        "kac yumurta",
        "kac isci",
        "kac makine",
        "kac musluk",
        "kac tane",
        "kac adet",
    )

    def normalize_text(self, text: str) -> str:
        value = text.casefold()

        value = value.translate(
            str.maketrans({
                "\u0131": "i",
                "\u011f": "g",
                "\u00fc": "u",
                "\u015f": "s",
                "\u00f6": "o",
                "\u00e7": "c",
            })
        )

        value = unicodedata.normalize("NFKD", value)

        value = "".join(
            char
            for char in value
            if not unicodedata.combining(char)
        )

        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _to_number(raw: str) -> float | int:
        number = float(raw.replace(",", "."))

        if number.is_integer():
            return int(number)

        return number

    def _extract_numbers(
        self,
        normalized: str,
    ) -> list[float | int]:
        return [
            self._to_number(match.group(0))
            for match in re.finditer(
                r"\d+(?:[.,]\d+)?",
                normalized,
            )
        ]

    def _is_inverse(
        self,
        normalized: str,
    ) -> bool:
        return any(
            marker in normalized
            for marker in self.INVERSE_MARKERS
        )

    def _asks_for_quantity(
        self,
        normalized: str,
    ) -> bool:
        return any(
            marker in normalized
            for marker in self.QUANTITY_QUESTION_MARKERS
        )

    def _detect_intent(
        self,
        normalized: str,
    ) -> str:
        inverse = self._is_inverse(normalized)
        reverse = self._asks_for_quantity(normalized)

        if inverse and reverse:
            return "inverse_proportion_reverse"

        if inverse:
            return "inverse_proportion"

        if reverse:
            return "direct_proportion_reverse"

        return "direct_proportion"

    def _extract_quantity_unit(
        self,
        normalized: str,
    ) -> str | None:
        patterns = (
            (r"\bkalem\b", "kalem"),
            (r"\bkitap\b", "kitap"),
            (r"\burun\b", "ürün"),
            (r"\byumurta\b", "yumurta"),
            (r"\bisci\b", "işçi"),
            (r"\bmakine\b", "makine"),
            (r"\bmusluk\b", "musluk"),
        )

        for pattern, unit in patterns:
            if re.search(pattern, normalized):
                return unit

        return None

    def _extract_value_unit(
        self,
        normalized: str,
    ) -> str | None:
        patterns = (
            (r"\btl\b", "TL"),
            (r"\blira\b", "TL"),
            (r"\bgunde\b", "gün"),
            (r"\bgun\b", "gün"),
            (r"\bsaatte\b", "saat"),
            (r"\bsaat\b", "saat"),
            (r"\bdakika\b", "dakika"),
        )

        for pattern, unit in patterns:
            if re.search(pattern, normalized):
                return unit

        return None

    def detect(
        self,
        text: str,
    ) -> RatioProblem | None:
        if not text or not text.strip():
            return None

        normalized = self.normalize_text(text)

        # Algebra ifadeleri oran-oranti motoruna dusmemeli.
        #
        # Ornek:
        #   2x + 6 = 10
        #   2 carpi (x + 3) esittir 14
        #   x + y = 10
        #
        # Aksi halde yalnizca sayilari gorup sahte bir
        # direct_proportion sonucu uretebilir.
        has_algebra_variable = bool(
            re.search(
                r"(?<![a-z])[xyz](?![a-z])",
                normalized,
            )
        )

        has_equation_marker = (
            "=" in normalized
            or "esittir" in normalized
            or " esit " in f" {normalized} "
            or "denklem" in normalized
        )

        if has_algebra_variable or has_equation_marker:
            return None

        numbers = self._extract_numbers(normalized)

        if len(numbers) != 3:
            return None

        intent = self._detect_intent(normalized)

        known_quantity = numbers[0]
        known_value = numbers[1]

        if known_quantity == 0:
            return None

        quantity_unit = self._extract_quantity_unit(normalized)
        value_unit = self._extract_value_unit(normalized)

        if intent in (
            "direct_proportion_reverse",
            "inverse_proportion_reverse",
        ):
            target_value = numbers[2]

            if known_value == 0 or target_value == 0:
                return None

            return RatioProblem(
                intent=intent,
                known_quantity=known_quantity,
                known_value=known_value,
                target_value=target_value,
                quantity_unit=quantity_unit,
                value_unit=value_unit,
            )

        target_quantity = numbers[2]

        if target_quantity == 0:
            return None

        return RatioProblem(
            intent=intent,
            known_quantity=known_quantity,
            known_value=known_value,
            target_quantity=target_quantity,
            quantity_unit=quantity_unit,
            value_unit=value_unit,
        )


if __name__ == "__main__":
    normalizer = RatioNormalizer()

    tests = (
        (
            "3 kalem 30 TL ise 5 kalem kaç TL",
            "direct_proportion",
            5,
            None,
        ),
        (
            "4 işçi işi 12 günde bitiriyorsa 6 işçi kaç günde bitirir",
            "inverse_proportion",
            6,
            None,
        ),
        (
            "5 kalem 50 TL ise 30 TL'ye kaç kalem alınır",
            "direct_proportion_reverse",
            None,
            30,
        ),
        (
            "4 kitap 200 TL ise 500 TL'ye kaç kitap alınır",
            "direct_proportion_reverse",
            None,
            500,
        ),
        (
            "6 işçi işi 8 günde bitiriyorsa aynı işi 12 günde kaç işçi bitirir",
            "inverse_proportion_reverse",
            None,
            12,
        ),
        (
            "3 makine işi 20 saatte yapıyorsa aynı işi 12 saatte kaç makine yapar",
            "inverse_proportion_reverse",
            None,
            12,
        ),
    )

    failed = 0

    for (
        question,
        expected_intent,
        expected_target_quantity,
        expected_target_value,
    ) in tests:

        result = normalizer.detect(question)

        passed = (
            result is not None
            and result.intent == expected_intent
            and result.target_quantity == expected_target_quantity
            and result.target_value == expected_target_value
        )

        if not passed:
            failed += 1

        print(
            "PASS" if passed else "FAIL",
            "|",
            question,
        )
        print("   =>", result)

    print()

    print(
        "RATIO NORMALIZER V0.6 REVERSE:",
        "PASS" if failed == 0
        else f"FAIL ({failed})"
    )
