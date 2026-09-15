from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from .algebra import AlgebraEngine
from .evaluator import MathEngine
from .intent_detector import MathIntentDetector
from .linear_system import LinearSystemEngine
from .percentage import PercentageEngine
from .ratio import RatioEngine


@dataclass(frozen=True)
class MathServiceResult:
    handled: bool
    expression: str | None = None
    classification: str | None = None
    result: int | float | None = None
    answer: str | None = None
    steps: tuple[str, ...] = ()
    verified: bool | None = None


class MathService:
    """
    KODAAI Math Service V0.11

    Routing order:
    1. Basic algebra equations
    2. Explicit arithmetic expressions
    3. Percentage word problems
    4. Ratio / proportion problems
    5. Otherwise leave the question for RAG/LLM
    """

    def __init__(self) -> None:
        self.algebra_engine = AlgebraEngine()
        self.detector = MathIntentDetector()
        self.engine = MathEngine()
        self.linear_system_engine = LinearSystemEngine()
        self.percentage_engine = PercentageEngine()
        self.ratio_engine = RatioEngine()

    @staticmethod
    def _normalize_fraction_text(
        value: str,
    ) -> str:
        """
        Turkce dogal dildeki basit kesir karsilastirma
        sorularini encoding-safe ASCII forma getirir.
        """

        text = (value or "").casefold()

        # Turkce buyuk I-dot (?) casefold sonrasi
        # "i + combining dot" uretebilir.
        # Once Unicode combining isaretlerini temizle.
        text = unicodedata.normalize(
            "NFKD",
            text,
        )

        text = "".join(
            ch
            for ch in text
            if not unicodedata.combining(ch)
        )

        table = str.maketrans({
            chr(0x0131): "i",
            chr(0x015f): "s",
            chr(0x011f): "g",
            chr(0x00fc): "u",
            chr(0x00f6): "o",
            chr(0x00e7): "c",
        })

        text = text.translate(table)

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        return text

    @staticmethod
    def _simple_number_value(
        value: str,
    ) -> int | None:
        """
        Basit Turkce sayi sozcuklerini ve rakamlari
        tamsayiya cevirir.

        Bu katman bilincli olarak kucuk ve deterministiktir.
        """

        token = (value or "").strip().casefold()

        if re.fullmatch(r"-?\d+", token):
            return int(token)

        numbers = {
            "sifir": 0,
            "bir": 1,
            "iki": 2,
            "uc": 3,
            "dort": 4,
            "bes": 5,
            "alti": 6,
            "yedi": 7,
            "sekiz": 8,
            "dokuz": 9,
            "on": 10,
            "onbir": 11,
            "oniki": 12,
            "onuc": 13,
            "ondort": 14,
            "onbes": 15,
            "onalti": 16,
            "onyedi": 17,
            "onsekiz": 18,
            "ondokuz": 19,
            "yirmi": 20,
        }

        compact = token.replace(" ", "")

        return numbers.get(compact)

    @classmethod
    def _handle_fraction_equivalence(
        cls,
        question: str,
    ) -> MathServiceResult | None:
        """
        Iki kesrin ayni sayiyi gosterip gostermedigini
        capraz carpimla deterministik olarak dogrular.

        Ornek:
            bir bolu iki ile iki bolu dort ayni sayi mi
            1/2 ile 2/4 esit mi
        """

        if not question or not question.strip():
            return None

        text = cls._normalize_fraction_text(
            question
        )

        relation_signal = (
            "ayni sayi" in text
            or "esdeger" in text
            or "esit mi" in text
            or "esit midir" in text
            or "esit olur" in text
        )

        if not relation_signal:
            return None

        values = None

        # --------------------------------------------------
        # Rakamla yazilmis kesir:
        # 1/2 ile 2/4
        # --------------------------------------------------

        match = re.search(
            r"(-?\d+)\s*/\s*(-?\d+)"
            r"\s+(?:ile|ve)\s+"
            r"(-?\d+)\s*/\s*(-?\d+)",
            text,
        )

        if match:
            values = tuple(
                int(item)
                for item in match.groups()
            )

        # --------------------------------------------------
        # Dogal dil / sesli kesir:
        # bir bolu iki ile iki bolu dort
        # --------------------------------------------------

        if values is None:
            number_token = (
                r"(?:-?\d+|"
                r"sifir|bir|iki|uc|dort|bes|alti|"
                r"yedi|sekiz|dokuz|on|on\s*bir|"
                r"on\s*iki|on\s*uc|on\s*dort|"
                r"on\s*bes|on\s*alti|on\s*yedi|"
                r"on\s*sekiz|on\s*dokuz|yirmi)"
            )

            match = re.search(
                rf"({number_token})\s+bolu\s+"
                rf"({number_token})\s+"
                rf"(?:ile|ve)\s+"
                rf"({number_token})\s+bolu\s+"
                rf"({number_token})",
                text,
            )

            if match:
                parsed = tuple(
                    cls._simple_number_value(item)
                    for item in match.groups()
                )

                if all(
                    item is not None
                    for item in parsed
                ):
                    values = parsed

        if values is None:
            return None

        a, b, c, d = values

        # --------------------------------------------------
        # Sifir payda korumasi
        # --------------------------------------------------

        if b == 0 or d == 0:
            return MathServiceResult(
                handled=True,
                expression=f"{a}/{b} ? {c}/{d}",
                classification="invalid_fraction",
                result=None,
                answer=(
                    "Paydas\u0131 s\u0131f\u0131r olan bir ifade "
                    "ge\u00e7erli bir kesir de\u011fildir."
                ),
                steps=(),
                verified=False,
            )

        # --------------------------------------------------
        # Deterministik capraz carpim
        # a/b == c/d  <=>  a*d == c*b
        # --------------------------------------------------

        left_cross = a * d
        right_cross = c * b

        equivalent = (
            left_cross == right_cross
        )

        if equivalent:
            answer = (
                f"Evet. {a} b\u00f6l\u00fc {b} ile "
                f"{c} b\u00f6l\u00fc {d} "
                f"ayn\u0131 say\u0131y\u0131 g\u00f6sterir."
            )
        else:
            answer = (
                f"Hay\u0131r. {a} b\u00f6l\u00fc {b} ile "
                f"{c} b\u00f6l\u00fc {d} "
                f"ayn\u0131 say\u0131y\u0131 g\u00f6stermez."
            )

        steps = (
            (
                f"\u00c7apraz \u00e7arp\u0131mlar\u0131 "
                f"kar\u015f\u0131la\u015ft\u0131r: "
                f"{a} \u00e7arp\u0131 {d} = {left_cross}."
            ),
            (
                f"{c} \u00e7arp\u0131 {b} = {right_cross}."
            ),
        )

        return MathServiceResult(
            handled=True,
            expression=f"{a}/{b} ? {c}/{d}",
            classification=(
                "equivalent_fractions"
                if equivalent
                else "non_equivalent_fractions"
            ),
            result=None,
            answer=answer,
            steps=steps,
            verified=True,
        )

    @classmethod
    def _handle_digit_fact_question(
        cls,
        question: str,
    ) -> MathServiceResult | None:

        if not question or not question.strip():
            return None

        text = cls._normalize_fraction_text(
            question
        )

        if "rakam" not in text:
            return None

        if "en kucuk rakam" in text:
            return MathServiceResult(
                handled=True,
                classification="smallest_digit",
                result=0,
                answer="En k\u00fc\u00e7\u00fck rakam s\u0131f\u0131rd\u0131r.",
                steps=(),
                verified=True,
            )

        if "en buyuk rakam" in text:
            return MathServiceResult(
                handled=True,
                classification="largest_digit",
                result=9,
                answer="En b\u00fcy\u00fck rakam dokuzdur.",
                steps=(),
                verified=True,
            )

        if (
            "rakamlarin sayisi" in text
            or "rakam sayisi kac" in text
            or "kac rakam" in text
            or "kac tane rakam" in text
        ):
            return MathServiceResult(
                handled=True,
                classification="digit_count",
                result=10,
                answer=(
                    "Toplam on rakam vard\u0131r: "
                    "s\u0131f\u0131rdan dokuza kadar."
                ),
                steps=(),
                verified=True,
            )

        return None

    @classmethod
    def _handle_rational_number_question(
        cls,
        question: str,
    ) -> MathServiceResult | None:
        """
        Rasyonel sayilarla ilgili kesin ve deterministik
        uyelik / temel kavram sorularini LLM'e birakmaz.

        Bu katman yalniz acik matematiksel kurallari kapsar.
        """
        if not question or not question.strip():
            return None

        text = cls._normalize_fraction_text(
            question
        )

        if "rasyonel" not in text:
            return None

        # --------------------------------------------------
        # Temel kavramsal kurallar
        # --------------------------------------------------

        if (
            "tam sayilar" in text
            and "rasyonel" in text
            and (
                "yazilabilir mi" in text
                or "yazilabilir midir" in text
                or "olabilir mi" in text
            )
        ):
            return MathServiceResult(
                handled=True,
                classification="integer_is_rational",
                result=None,
                answer=(
                    "Evet. Her tam say\u0131, paydas\u0131 bir olan "
                    "bir kesir bi\u00e7iminde yaz\u0131labildi\u011fi i\u00e7in "
                    "rasyonel say\u0131d\u0131r."
                ),
                steps=(
                    "Bir tam sayı n, n bölü bir biçiminde yazılabilir.",
                    "Payda sıfır olmadığı için bu ifade rasyoneldir.",
                ),
                verified=True,
            )

        if (
            "hem tam sayi hem rasyonel" in text
            or (
                "tam sayi" in text
                and "rasyonel sayi" in text
                and "olabilir mi" in text
            )
        ):
            return MathServiceResult(
                handled=True,
                classification="integer_and_rational",
                result=None,
                answer=(
                    "Evet. Bir say\u0131 hem tam say\u0131 hem de "
                    "rasyonel say\u0131 olabilir. \u00d6rne\u011fin \u00fc\u00e7, "
                    "\u00fc\u00e7 b\u00f6l\u00fc bir bi\u00e7iminde yaz\u0131labilir."
                ),
                steps=(),
                verified=True,
            )

        if (
            "rasyonel sayilar" in text
            and "sayi dogrusunda" in text
            and (
                "gosterilebilir mi" in text
                or "gosterilir mi" in text
            )
        ):
            return MathServiceResult(
                handled=True,
                classification="rational_number_line",
                result=None,
                answer=(
                    "Evet. Rasyonel say\u0131lar say\u0131 do\u011frusunda "
                    "g\u00f6sterilebilir."
                ),
                steps=(),
                verified=True,
            )

        if (
            "iki rasyonel sayi arasinda" in text
            and (
                "baska bir rasyonel" in text
                or "rasyonel sayi bulunabilir" in text
            )
        ):
            return MathServiceResult(
                handled=True,
                classification="rational_density",
                result=None,
                answer=(
                    "Evet. \u0130ki farkl\u0131 rasyonel say\u0131 aras\u0131nda "
                    "ba\u015fka bir rasyonel say\u0131 bulunabilir. "
                    "\u00d6rne\u011fin bu iki say\u0131n\u0131n aritmetik ortalamas\u0131 "
                    "da rasyonel bir say\u0131d\u0131r."
                ),
                steps=(),
                verified=True,
            )

        # --------------------------------------------------
        # Belirli bir sayinin rasyonel olup olmadigi
        # --------------------------------------------------

        membership_signal = (
            "rasyonel sayi midir" in text
            or "rasyonel sayi mi" in text
        )

        if not membership_signal:
            return None

        # Soru sonundaki kategori ifadesini kaldir.
        value_text = re.sub(
            r"\s+(?:bir\s+)?rasyonel\s+sayi\s+"
            r"(?:midir|mi)\b.*$",
            "",
            text,
        ).strip()

        # "eksi uc" gibi negatif tam sayilar.
        sign = 1

        if value_text.startswith("eksi "):
            sign = -1
            value_text = value_text[5:].strip()

        # Rakamla negatif deger: -3
        if re.fullmatch(r"-?\d+", value_text):
            value = int(value_text)

            return MathServiceResult(
                handled=True,
                expression=str(value),
                classification="rational_membership",
                result=None,
                answer=(
                    f"Evet. {value} bir rasyonel sayidir; "
                    f"cunku {value} bolu bir biciminde "
                    "yaz\u0131labilir."
                ),
                steps=(),
                verified=True,
            )

        # Sozcukle tam sayi: sifir, uc, eksi uc...
        integer_value = cls._simple_number_value(
            value_text
        )

        if integer_value is not None:
            integer_value *= sign

            if integer_value == 0:
                answer = (
                    "Evet. S\u0131f\u0131r bir rasyonel say\u0131d\u0131r; "
                    "\u00e7\u00fcnk\u00fc s\u0131f\u0131r b\u00f6l\u00fc bir bi\u00e7iminde "
                    "yaz\u0131labilir."
                )
            else:
                answer = (
                    "Evet. Bu tam say\u0131 bir rasyonel say\u0131d\u0131r; "
                    "\u00e7\u00fcnk\u00fc paydas\u0131 bir olan bir kesir "
                    "bi\u00e7iminde yaz\u0131labilir."
                )

            return MathServiceResult(
                handled=True,
                expression=str(integer_value),
                classification="rational_membership",
                result=None,
                answer=answer,
                steps=(),
                verified=True,
            )

        # Sozcukle veya rakamla tek kesir:
        # eksi bir bolu iki
        # 3 bolu 4
        # 3/4
        fraction_match = re.fullmatch(
            r"(.+?)\s+bolu\s+(.+)",
            value_text,
        )

        if fraction_match:
            numerator_text = (
                fraction_match.group(1).strip()
            )
            denominator_text = (
                fraction_match.group(2).strip()
            )

            numerator_sign = 1

            if numerator_text.startswith("eksi "):
                numerator_sign = -1
                numerator_text = (
                    numerator_text[5:].strip()
                )

            numerator = cls._simple_number_value(
                numerator_text
            )
            denominator = cls._simple_number_value(
                denominator_text
            )

            if (
                numerator is not None
                and denominator is not None
            ):
                numerator *= numerator_sign

                if denominator == 0:
                    return MathServiceResult(
                        handled=True,
                        classification="invalid_fraction",
                        result=None,
                        answer=(
                            "Hay\u0131r. Paydas\u0131 s\u0131f\u0131r olan bir ifade "
                            "rasyonel say\u0131 olarak tan\u0131ml\u0131 de\u011fildir."
                        ),
                        steps=(),
                        verified=False,
                    )

                return MathServiceResult(
                    handled=True,
                    expression=(
                        f"{numerator}/{denominator}"
                    ),
                    classification="rational_membership",
                    result=None,
                    answer=(
                        "Evet. Pay ve payda tam say\u0131d\u0131r ve "
                        "payda s\u0131f\u0131r olmad\u0131\u011f\u0131 i\u00e7in bu ifade "
                        "rasyonel say\u0131d\u0131r."
                    ),
                    steps=(),
                    verified=True,
                )

        slash_match = re.fullmatch(
            r"(-?\d+)\s*/\s*(-?\d+)",
            value_text,
        )

        if slash_match:
            numerator = int(
                slash_match.group(1)
            )
            denominator = int(
                slash_match.group(2)
            )

            if denominator == 0:
                return MathServiceResult(
                    handled=True,
                    classification="invalid_fraction",
                    result=None,
                    answer=(
                        "Hay\u0131r. Paydas\u0131 s\u0131f\u0131r olan bir ifade "
                        "rasyonel say\u0131 olarak tan\u0131ml\u0131 de\u011fildir."
                    ),
                    steps=(),
                    verified=False,
                )

            return MathServiceResult(
                handled=True,
                expression=(
                    f"{numerator}/{denominator}"
                ),
                classification="rational_membership",
                result=None,
                answer=(
                    "Evet. Pay ve payda tam say\u0131d\u0131r ve "
                    "payda s\u0131f\u0131r olmad\u0131\u011f\u0131 i\u00e7in bu ifade "
                    "rasyonel say\u0131d\u0131r."
                ),
                steps=(),
                verified=True,
            )

        return None

    @staticmethod
    def _normalize_natural_language_equation(
        question: str,
    ) -> str | None:
        """
        Turkce dogal dilde ifade edilen basit tek degiskenli
        denklemleri AlgebraEngine formatina donusturur.
        """

        if not question or not question.strip():
            return None

        text = question.strip()
        lowered = text.casefold()

        # "2x" gibi bitisik degiskenleri destekle.
        if "x" not in lowered:
            return None

        # Turkce karakterleri kaynak dosyaya yazmadan olustur.
        s = chr(0x015f)
        S = chr(0x015e)
        c = chr(0x00e7)
        C = chr(0x00c7)
        g = chr(0x011f)
        G = chr(0x011e)
        i_dotless = chr(0x0131)
        o_umlaut = chr(0x00f6)
        u_umlaut = chr(0x00fc)

        esittir = "e" + s + "ittir"
        esit = "e" + s + "it"
        arti = "art" + i_dotless
        carpi = c + "arp" + i_dotless
        bolu = "b" + o_umlaut + "l" + u_umlaut

        has_equals_word = (
            esittir in lowered
            or esit in lowered
            or "esittir" in lowered
            or "esit" in lowered
        )

        has_equals_symbol = "=" in text

        if not (has_equals_word or has_equals_symbol):
            return None

        normalized = text

        replacements = (
            (esittir, "="),
            (esit, "="),
            ("esittir", "="),
            ("esit", "="),
            (arti, "+"),
            ("arti", "+"),
            ("eksi", "-"),
            (carpi, "*"),
            ("carpi", "*"),
            (bolu, "/"),
            ("bolu", "/"),
        )

        for source, target in replacements:
            normalized = normalized.replace(source, target)

        # "ise" sonrasindaki soru kismini kaldir.
        normalized = re.split(
            r"\bise\b",
            normalized,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        normalized = normalized.strip(" ?.!,:;")

        if "=" not in normalized:
            return None

        left, right = normalized.split("=", 1)

        left = left.strip()
        right = right.strip()

        # Sesli / dogal dil denklem komutlarinda
        # esitligin sag tarafindan sonra gelen
        # soru-komut eklerini temizle.
        #
        # Ornek:
        #   2 carpi parantez icinde x arti 3
        #   esittir 14 denklemini coz
        #
        # -> 2*(x+3)=14
        right = re.sub(
            r"\s+"
            r"(?:"
            r"denklemini\s+(?:coz|\u00e7\u00f6z)"
            r"|denklemi\s+(?:coz|\u00e7\u00f6z)"
            r"|denklemini\s+(?:cozunuz|\u00e7\u00f6z\u00fcn\u00fcz)"
            r"|denklemi\s+(?:cozunuz|\u00e7\u00f6z\u00fcn\u00fcz)"
            r"|(?:coz|\u00e7\u00f6z)"
            r"|(?:cozunuz|\u00e7\u00f6z\u00fcn\u00fcz)"
            r")"
            r"\s*$",
            "",
            right,
            flags=re.IGNORECASE,
        ).strip()

        if not left or not right:
            return None

        allowed = r"[0-9xX+\-*/().\s]+"

        if not re.fullmatch(allowed, left):
            return None

        if not re.fullmatch(allowed, right):
            return None

        return f"{left} = {right}"

    @staticmethod
    def _detect_multivariable_single_equation(
        question: str,
    ) -> tuple[str, tuple[str, ...]] | None:
        """
        Tek denklemde birden fazla bilinmeyeni tespit eder.
        x, y ve z degiskenleri desteklenir.
        """

        if not question or not question.strip():
            return None

        value = question.strip().casefold()

        # Encoding-safe Turkce karakterler.
        s_char = chr(0x015f)
        i_dotless = chr(0x0131)
        c_char = chr(0x00e7)
        o_char = chr(0x00f6)
        u_char = chr(0x00fc)

        esittir = "e" + s_char + "ittir"
        esit = "e" + s_char + "it"
        arti = "art" + i_dotless
        carpi = c_char + "arp" + i_dotless
        bolu = "b" + o_char + "l" + u_char

        replacements = (
            (esittir, "="),
            (esit, "="),
            ("esittir", "="),
            ("esit", "="),
            (arti, "+"),
            ("arti", "+"),
            ("eksi", "-"),
            (carpi, "*"),
            ("carpi", "*"),
            (bolu, "/"),
            ("bolu", "/"),
        )

        for source, target in replacements:
            value = value.replace(source, target)

        # "ise ..." sonrasi soru metnidir.
        value = re.split(
            r"\bise\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        if value.count("=") != 1:
            return None

        # Denklem bolumunu soru cumlesinden ayir.
        match = re.search(
            r"([0-9xyz+\-*/().\s]+"
            r"="
            r"[0-9xyz+\-*/().\s]+)",
            value,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        equation = match.group(1).strip()

        variables = tuple(
            sorted(
                set(
                    re.findall(
                        r"[xyz]",
                        equation,
                        flags=re.IGNORECASE,
                    )
                )
            )
        )

        if len(variables) < 2:
            return None

        equation = re.sub(
            r"\s+",
            "",
            equation,
        )

        return equation, variables


    @staticmethod
    def _normalize_spoken_parentheses(
        question: str,
    ) -> str:
        """
        Turkce sesli matematikte:

            2 carpi parantez icinde x arti 3 esittir 14

        ifadesini:

            2 carpi (x arti 3) esittir 14

        bicimine getirir.
        """

        if not question:
            return question

        # --------------------------------------------------
        # 1. "parantez x arti 3 parantez esittir ..."
        #
        # Sesli kullanimda ayni "parantez" sozcugu hem
        # acilis hem kapanis icin kullanilabilir.
        # --------------------------------------------------
        paired_pattern = re.compile(
            r"\bparantez\s+"
            r"(.+?)"
            r"\s+parantez"
            r"(?=\s+(?:e\u015fittir|esittir|e\u015fit|esit)\b|\s*=)",
            flags=re.IGNORECASE,
        )

        normalized = paired_pattern.sub(
            lambda match: (
                "("
                + match.group(1).strip()
                + ")"
            ),
            question,
        )

        # --------------------------------------------------
        # 2. "parantez icinde x arti 3 esittir ..."
        # --------------------------------------------------
        inside_pattern = re.compile(
            r"\bparantez\s+i(?:\u00e7|c)inde\s+"
            r"(.+?)"
            r"(?=\s+(?:e\u015fittir|esittir|e\u015fit|esit)\b|\s*=)",
            flags=re.IGNORECASE,
        )

        normalized = inside_pattern.sub(
            lambda match: (
                "("
                + match.group(1).strip()
                + ")"
            ),
            normalized,
        )

        return normalized

    def handle(self, question: str) -> MathServiceResult:
        # 0. DIGIT FACTS
        digit_result = self._handle_digit_fact_question(
            question
        )

        if digit_result is not None:
            return digit_result

        # ---------------------------------------------------------
        # 0. RATIONAL NUMBER DETERMINISTIC KNOWLEDGE
        # ---------------------------------------------------------
        rational_result = (
            self._handle_rational_number_question(
                question
            )
        )

        if rational_result is not None:
            return rational_result

        # ---------------------------------------------------------
        # 0. FRACTION EQUIVALENCE
        # ---------------------------------------------------------
        fraction_result = (
            self._handle_fraction_equivalence(
                question
            )
        )

        if fraction_result is not None:
            return fraction_result

        # ---------------------------------------------------------
        # 1. 2x2 LINEAR SYSTEM
        # ---------------------------------------------------------
        system_result = self.linear_system_engine.solve(question)

        if system_result.handled:
            return MathServiceResult(
                handled=True,
                expression=None,
                classification=system_result.classification,
                result=None,
                answer=system_result.answer,
                steps=system_result.steps,
                verified=True if system_result.classification == "unique_solution" else None,
            )

        # ---------------------------------------------------------
        # 1. NATURAL LANGUAGE ALGEBRA NORMALIZATION
        # ---------------------------------------------------------
        spoken_question = (
            self._normalize_spoken_parentheses(
                question
            )
        )

        normalized_equation = (
            self._normalize_natural_language_equation(
                spoken_question
            )
        )

        algebra_question = (
            normalized_equation
            if normalized_equation
            else spoken_question
        )

        # ---------------------------------------------------------
        # 2. ALGEBRA
        #
        # Algebra must be checked before ordinary arithmetic.
        # Example:
        #
        #     x / 3 = 5
        #
        # contains "/" but is an equation, not a simple
        # arithmetic expression.
        # ---------------------------------------------------------
        algebra_result = self.algebra_engine.solve(
            algebra_question
        )

        if algebra_result.handled:
            return MathServiceResult(
                handled=True,
                expression=algebra_result.equation,
                classification=algebra_result.classification,
                result=algebra_result.solution,
                answer=algebra_result.answer,
                steps=algebra_result.steps,
                verified=algebra_result.verified,
            )

        multivariable = (
            self._detect_multivariable_single_equation(
                question
            )
        )

        if multivariable is not None:
            expression, variables = multivariable

            variable_names = " ve ".join(
                variables
            )

            answer = (
                "Bu denklemde "
                f"{variable_names} olmak \u00fczere iki veya daha fazla "
                "bilinmeyen vard\u0131r. Tek bir denklem, bilinmeyenlerin "
                "de\u011ferlerini ayr\u0131 ayr\u0131 belirlemek i\u00e7in "
                "yeterli de\u011fildir. Ek bir ba\u011f\u0131ms\u0131z "
                "denkleme ihtiya\u00e7 vard\u0131r."
            )

            return MathServiceResult(
                handled=True,
                expression=expression,
                classification="underdetermined",
                result=None,
                answer=answer,
                steps=(),
                verified=None,
            )

        # Unsupported algebra equations must not leak into
        # percentage or ratio/proportion routing.
        #
        # Example:
        #     2x+3=x+8
        #
        # Algebra V0.9 intentionally leaves x-on-both-sides
        # equations unsupported. Without this guard, RatioEngine
        # can interpret the numeric tokens as a proportion.
        normalized_question = (
            question.lower()
            .replace(" ", "")
        )

        if (
            "=" in normalized_question
            and "x" in normalized_question
        ):
            return MathServiceResult(
                handled=False
            )

        # ---------------------------------------------------------
        # 2. EXPLICIT ARITHMETIC
        # ---------------------------------------------------------
        intent = self.detector.detect(question)

        if intent.is_math and intent.expression:
            evaluation = self.engine.evaluate(
                intent.expression
            )

            return MathServiceResult(
                handled=True,
                expression=evaluation.normalized_expression,
                result=evaluation.result,
                answer=evaluation.accessible_answer,
            )

        # ---------------------------------------------------------
        # 3. PERCENTAGE
        # ---------------------------------------------------------
        percentage_result = self.percentage_engine.handle(
            question
        )

        if percentage_result.handled:
            return MathServiceResult(
                handled=True,
                expression=None,
                result=percentage_result.result,
                answer=percentage_result.answer,
            )

        # ---------------------------------------------------------
        # 4. RATIO / PROPORTION
        # ---------------------------------------------------------
        ratio_result = self.ratio_engine.handle(
            question
        )

        if ratio_result.handled:
            return MathServiceResult(
                handled=True,
                expression=None,
                result=ratio_result.result,
                answer=ratio_result.answer,
            )

        # ---------------------------------------------------------
        # 5. RAG / LLM
        # ---------------------------------------------------------
        return MathServiceResult(
            handled=False
        )


if __name__ == "__main__":
    service = MathService()

    tests = (
        # Algebra V0.8
        ("x+5=12", True, 7),
        ("x-4=9", True, 13),
        ("3x=18", True, 6),
        ("x/3=5", True, 15),
        ("2x+4=10", True, 3),
        ("3x-7=11", True, 6),

        # Existing arithmetic regression
        ("6 x 2 + 6", True, 18),
        ("6 x 2 + 6 işleminin sonucu nedir", True, 18),
        ("(6 + 2) x 6", True, 48),
        ("20 / 4 + 3 kaç eder", True, 8),

        # Existing percentage regression
        (
            "100 liralık kitap %20 indirimle kaç lira olur",
            True,
            80,
        ),
        (
            "Fiyatı 100 TL olan yumurtaya yüzde 20 indirim uygulanırsa fiyatı nedir",
            True,
            80,
        ),
        (
            "%20 indirim sonrası 100 liralık ürün ne kadar olur",
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

        # Must remain available to RAG / LLM
        ("Türkiye'nin başkenti neresidir", False, None),
        ("işlem önceliğini anlat", False, None),
    )

    failed = 0

    for question, expected_handled, expected_result in tests:
        try:
            output = service.handle(question)

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
                "=>",
                output,
            )

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
        "MATH SERVICE V0.8:",
        "PASS" if failed == 0
        else f"FAIL ({failed})"
    )