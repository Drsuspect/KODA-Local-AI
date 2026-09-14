from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class PercentageProblem:
    intent: str
    base_value: float
    rate: float
    unit: str | None = None
    object_name: str | None = None


class PercentageNormalizer:
    """
    KODAAI Percentage Problem Normalizer V0.5

    Supported intents:
    - percentage_discount
    - percentage_increase
    - percentage_of
    - reverse_percentage_discount
    - reverse_percentage_increase
    """

    DISCOUNT_MARKERS = (
        "indirim",
        "indirimli",
        "iskonto",
        "iskontolu",
        "dusur",
        "duser",
        "dusunce",
        "azalir",
        "azaltilir",
        "ucuz",
        "ucuza",
    )

    INCREASE_MARKERS = (
        "zam",
        "zamli",
        "artis",
        "artirilir",
        "artar",
        "artarsa",
        "arttiginda",
        "arttigi",
        "artmis",
        "yukselir",
        "yukseltilir",
        "yukseldiginde",
    )

    REVERSE_MARKERS = (
        "eski fiyat",
        "ilk fiyat",
        "onceki fiyat",
        "baslangic fiyat",
        "baslangic deger",
        "indirimsiz fiyat",
        "zamsiz fiyat",
        "%100 fiyat",
        "yuzde 100 fiyat",
        "tam fiyat",
    )

    UNIT_PATTERNS = (
        (r"\btl\b", "TL"),
        (r"\blira\b", "TL"),
        (r"\bliralik\b", "TL"),
        (r"\bliraya\b", "TL"),
        (r"\bliradan\b", "TL"),
        (r"\bbirim\b", "birim"),
        (r"\bbirimlik\b", "birim"),
    )

    def normalize_text(self, text: str) -> str:
        value = text.casefold()

        turkish_map = str.maketrans({
            "\u0131": "i",
            "\u011f": "g",
            "\u00fc": "u",
            "\u015f": "s",
            "\u00f6": "o",
            "\u00e7": "c",
        })

        value = value.translate(turkish_map)

        value = unicodedata.normalize("NFKD", value)
        value = "".join(
            char
            for char in value
            if not unicodedata.combining(char)
        )

        value = re.sub(r"\s+", " ", value).strip()

        return value

    def _to_number(self, raw: str) -> float:
        value = raw.replace(",", ".")
        result = float(value)

        if result.is_integer():
            return int(result)

        return result

    def _extract_percentage_values(
        self,
        normalized: str
    ) -> list[tuple[float, tuple[int, int]]]:
        matches: list[tuple[float, tuple[int, int]]] = []

        patterns = (
            r"%\s*(\d+(?:[.,]\d+)?)",
            r"\byuzde\s+(\d+(?:[.,]\d+)?)",
        )

        occupied: list[tuple[int, int]] = []

        for pattern in patterns:
            for match in re.finditer(pattern, normalized):
                span = match.span()

                if any(
                    not (
                        span[1] <= other[0]
                        or span[0] >= other[1]
                    )
                    for other in occupied
                ):
                    continue

                occupied.append(span)

                matches.append(
                    (
                        self._to_number(match.group(1)),
                        span,
                    )
                )

        matches.sort(
            key=lambda item: item[1][0]
        )

        return matches

    def _extract_rate(
        self,
        normalized: str
    ) -> tuple[float | None, tuple[int, int] | None]:
        percentages = self._extract_percentage_values(
            normalized
        )

        if not percentages:
            return None, None

        for value, span in percentages:
            if value != 100:
                return value, span

        return percentages[0]

    def _extract_base_value(
        self,
        normalized: str,
        percentage_spans: list[tuple[int, int]],
    ) -> float | None:
        working = normalized

        for start, end in sorted(
            percentage_spans,
            reverse=True
        ):
            working = (
                working[:start]
                + " "
                + working[end:]
            )

        number_matches = list(
            re.finditer(
                r"\d+(?:[.,]\d+)?",
                working
            )
        )

        if not number_matches:
            return None

        return self._to_number(
            number_matches[0].group(0)
        )

    def _detect_unit(
        self,
        normalized: str
    ) -> str | None:
        for pattern, unit in self.UNIT_PATTERNS:
            if re.search(pattern, normalized):
                return unit

        return None

    def _has_reverse_marker(
        self,
        normalized: str
    ) -> bool:
        return any(
            marker in normalized
            for marker in self.REVERSE_MARKERS
        )

    def _detect_intent(
        self,
        normalized: str
    ) -> str | None:
        has_discount = any(
            marker in normalized
            for marker in self.DISCOUNT_MARKERS
        )

        has_increase = any(
            marker in normalized
            for marker in self.INCREASE_MARKERS
        )

        reverse_requested = self._has_reverse_marker(
            normalized
        )

        if has_increase and reverse_requested:
            return "reverse_percentage_increase"

        if has_discount and reverse_requested:
            return "reverse_percentage_discount"

        if has_discount:
            return "percentage_discount"

        if has_increase:
            return "percentage_increase"

        rate_exists = bool(
            re.search(
                r"(?:%\s*\d|\byuzde\s+\d)",
                normalized
            )
        )

        if rate_exists:
            return "percentage_of"

        return None

    def _extract_object(
        self,
        normalized: str
    ) -> str | None:
        candidates = (
            r"\burunun\b",
            r"\burun\b",
            r"\bkitabin\b",
            r"\bkitap\b",
            r"\byumurtanin\b",
            r"\byumurta\b",
            r"\bbiletin\b",
            r"\bbilet\b",
            r"\btelefonun\b",
            r"\btelefon\b",
        )

        object_map = {
            "urunun": "ürün",
            "urun": "ürün",
            "kitabin": "kitap",
            "kitap": "kitap",
            "yumurtanin": "yumurta",
            "yumurta": "yumurta",
            "biletin": "bilet",
            "bilet": "bilet",
            "telefonun": "telefon",
            "telefon": "telefon",
        }

        for pattern in candidates:
            match = re.search(pattern, normalized)

            if match:
                return object_map.get(
                    match.group(0)
                )

        return None

    def detect(
        self,
        text: str
    ) -> PercentageProblem | None:
        if not text or not text.strip():
            return None

        normalized = self.normalize_text(text)

        percentages = self._extract_percentage_values(
            normalized
        )

        if not percentages:
            return None

        rate, _ = self._extract_rate(
            normalized
        )

        if rate is None:
            return None

        percentage_spans = [
            span
            for _, span in percentages
        ]

        base_value = self._extract_base_value(
            normalized,
            percentage_spans,
        )

        if base_value is None:
            return None

        intent = self._detect_intent(
            normalized
        )

        if intent is None:
            return None

        if rate < 0 or rate > 10000:
            return None

        return PercentageProblem(
            intent=intent,
            base_value=base_value,
            rate=rate,
            unit=self._detect_unit(normalized),
            object_name=self._extract_object(normalized),
        )


if __name__ == "__main__":
    normalizer = PercentageNormalizer()

    tests = (
        (
            "100 liralık kitap %20 indirimle kaç lira olur",
            "percentage_discount",
            100,
            20,
        ),
        (
            "Fiyatı 100 TL olan yumurtaya yüzde 20 indirim uygulanırsa fiyatı nedir",
            "percentage_discount",
            100,
            20,
        ),
        (
            "100 birimlik bir ürünün %20 indirimli fiyatı kaçtır",
            "percentage_discount",
            100,
            20,
        ),
        (
            "%20 indirim sonrası 100 liralık ürün ne kadar olur",
            "percentage_discount",
            100,
            20,
        ),
        (
            "100 TL'den yüzde 20 düşerse kaç TL kalır",
            "percentage_discount",
            100,
            20,
        ),
        (
            "100 lira olan kitabın indirimli fiyatı nedir, indirim oranı %20",
            "percentage_discount",
            100,
            20,
        ),
        (
            "100 liraya %20 zam yapılırsa kaç lira olur",
            "percentage_increase",
            100,
            20,
        ),
        (
            "Fiyatı 100 TL olan ürüne yüzde 20 zam gelirse yeni fiyat nedir",
            "percentage_increase",
            100,
            20,
        ),
        (
            "200'ün %15'i kaçtır",
            "percentage_of",
            200,
            15,
        ),
        (
            "200 sayısının yüzde 15'i nedir",
            "percentage_of",
            200,
            15,
        ),
        (
            "fiyatı %15 arttığında 230 TL olan ürünün %100 fiyatı nedir",
            "reverse_percentage_increase",
            230,
            15,
        ),
        (
            "%20 indirimden sonra 80 TL olan ürünün eski fiyatı nedir",
            "reverse_percentage_discount",
            80,
            20,
        ),
    )

    failed = 0

    for (
        question,
        expected_intent,
        expected_base,
        expected_rate,
    ) in tests:
        result = normalizer.detect(question)

        passed = (
            result is not None
            and result.intent == expected_intent
            and result.base_value == expected_base
            and result.rate == expected_rate
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
        "PERCENTAGE NORMALIZER V0.5:",
        "PASS" if failed == 0
        else f"FAIL ({failed})"
    )
