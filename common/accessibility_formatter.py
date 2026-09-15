import re


TR = {
    "c": chr(231),
    "g": chr(287),
    "i": chr(305),
    "o": chr(246),
    "s": chr(351),
    "u": chr(252),
    "C": chr(199),
    "G": chr(286),
    "I": chr(304),
    "O": chr(214),
    "S": chr(350),
    "U": chr(220),
}

C = TR["c"]
G = TR["g"]
I_DOTLESS = TR["i"]
O = TR["o"]
S = TR["s"]
U = TR["u"]

ROMAN_CARDINALS = {
    "I": "bir",
    "II": "iki",
    "III": U + C,
    "IV": "d" + O + "rt",
    "V": "be" + S,
    "VI": "alt" + I_DOTLESS,
    "VII": "yedi",
    "VIII": "sekiz",
    "IX": "dokuz",
    "X": "on",
}

ROMAN_ORDINALS = {
    "I": "birinci",
    "II": "ikinci",
    "III": U + C + U + "n" + C + U,
    "IV": "d" + O + "rd" + U + "nc" + U,
    "V": "be" + S + "inci",
    "VI": "alt" + I_DOTLESS + "nc" + I_DOTLESS,
    "VII": "yedinci",
    "VIII": "sekizinci",
    "IX": "dokuzuncu",
    "X": "onuncu",
}


def _number_to_tr(n: str) -> str:
    try:
        value = int(n)
    except ValueError:
        return n

    ones = [
        "s" + I_DOTLESS + "f" + I_DOTLESS + "r",
        "bir",
        "iki",
        U + C,
        "d" + O + "rt",
        "be" + S,
        "alt" + I_DOTLESS,
        "yedi",
        "sekiz",
        "dokuz",
    ]

    tens = [
        "",
        "on",
        "yirmi",
        "otuz",
        "k" + I_DOTLESS + "rk",
        "elli",
        "altm" + I_DOTLESS + S,
        "yetmi" + S,
        "seksen",
        "doksan",
    ]

    if 0 <= value < 10:
        return ones[value]

    if 10 <= value < 100:
        t = value // 10
        o = value % 10
        return tens[t] if o == 0 else f"{tens[t]} {ones[o]}"

    return n


def _replace_percent(text: str) -> str:
    def repl(match):
        return "y" + U + "zde " + _number_to_tr(match.group(1))

    return re.sub(r"%\s*(\d{1,2})\b", repl, text)


def _replace_decimal(text: str) -> str:
    def repl(match):
        left = _number_to_tr(match.group(1))
        right = _number_to_tr(match.group(2))
        return f"{left} virg{U}l {right}"

    return re.sub(r"\b(\d{1,2}),(\d{1,2})\b", repl, text)


def _replace_simple_fraction(text: str) -> str:
    common = {
        ("1", "2"): "ikide bir",
        ("1", "3"): U + C + "te bir",
        ("2", "3"): U + C + "te iki",
        ("1", "4"): "d" + O + "rtte bir",
        ("3", "4"): "d" + O + "rtte " + U + C,
    }

    def repl(match):
        num = match.group(1)
        den = match.group(2)
        return common.get(
            (num, den),
            f"pay {_number_to_tr(num)}, payda {_number_to_tr(den)}",
        )

    return re.sub(
        r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])",
        repl,
        text,
    )


def _replace_superscripts(text: str) -> str:
    superscript_map = {
        "0": "s" + I_DOTLESS + "f" + I_DOTLESS + "r",
        "1": "bir",
        "2": "iki",
        "3": U + C,
        "4": "d" + O + "rt",
        "5": "be" + S,
        "6": "alt" + I_DOTLESS,
        "7": "yedi",
        "8": "sekiz",
        "9": "dokuz",
    }

    def repl(match):
        variable = match.group(1)
        exponent = match.group(2)
        return f"{variable} {superscript_map.get(exponent, exponent)}"

    text = re.sub(
        r"([A-Za-z])(?:\^)(\d)",
        repl,
        text,
    )

    return text


def _replace_square_root(text: str) -> str:
    def repl(match):
        value = match.group(1)
        return f"karek" + U + "k {value}"

    text = re.sub(
        r"sqrt\s*\(\s*([^()]+)\s*\)",
        repl,
        text,
        flags=re.IGNORECASE,
    )

    text = text.replace(
        chr(8730),
        "karek" + U + "k",
    )

    return text


def _replace_inequalities(text: str) -> str:
    replacements = (
        (">=", " b" + U + "y" + U + "k veya e" + S + "ittir "),
        ("<=", " k" + U + C + U + "k veya e" + S + "ittir "),
        (">", " b" + U + "y" + U + "kt" + U + "r "),
        ("<", " k" + U + C + U + "kt" + U + "r "),
    )

    for source, target in replacements:
        text = text.replace(source, target)

    return text


def _replace_roman_numerals(text: str) -> str:
    """
    Roma rakamlarini yalnizca BUYUK HARF ile yazildiklarinda
    donusturur.

    Kucuk x/i gibi matematik degiskenleri ve Turkce kelimeler
    kesinlikle Roma rakami olarak yorumlanmaz.

    Ornek:
        I. D?nya -> bir. D?nya
        II. D?nya -> iki. D?nya
        x = 2 -> x = 2
        2x + 6 -> 2x + 6
    """

    def repl_parenthesized(match):
        value = match.group(1)
        return ROMAN_CARDINALS.get(value, match.group(0))

    def repl_plain(match):
        value = match.group(0)
        return ROMAN_CARDINALS.get(value, value)

    # Parantezli Roma rakamlari.
    text = re.sub(
        r"\(\s*(VIII|VII|VI|IV|IX|III|II|I|V|X)\s*\)",
        repl_parenthesized,
        text,
    )

    # Nokta ile kullanilan Roma rakamlari:
    # I. / II. / III. gibi.
    text = re.sub(
        r"(?<![A-Za-z????????????])"
        r"(VIII|VII|VI|IV|IX|III|II|I|V|X)"
        r"(?=\.)",
        repl_plain,
        text,
    )

    return text

def _replace_implicit_multiplication(text: str) -> str:
    def repl(match):
        number = _number_to_tr(match.group(1))
        variable = match.group(2)
        return f"{number} {variable}"

    return re.sub(
        r"\b(\d{1,2})([A-Za-z])\b",
        repl,
        text,
    )


def _replace_operators(text: str) -> str:
    text = re.sub(
        r"\s+/\s+",
        " b" + U + "l" + U,
        text,
    )

    replacements = (
        (chr(215), " " + C + "arp" + I_DOTLESS + " "),
        ("*", " " + C + "arp" + I_DOTLESS + " "),
        (chr(247), " b" + U + "l" + U + " "),
        ("+", " art" + I_DOTLESS + " "),
        (chr(8722), " eksi "),
        ("-", " eksi "),
        ("=", " e" + S + "ittir "),
    )

    for source, target in replacements:
        text = text.replace(source, target)

    return text


def _replace_standalone_integers(text: str) -> str:
    def repl(match):
        return _number_to_tr(match.group(0))

    return re.sub(
        r"(?<![A-Za-z0-9/])\d{1,2}(?![A-Za-z0-9/])",
        repl,
        text,
    )


def _remove_leading_option_label(text: str) -> str:
    patterns = (
        r"^\s*[A-E]\s*[\)\].:\-]\s*",
        r"^\s*[A-E]\s+(?=[A-Z" + C + G + I_DOTLESS + O + S + U + r"][a-z" + C + G + I_DOTLESS + O + S + U + r"])",
    )

    result = text

    for pattern in patterns:
        cleaned = re.sub(
            pattern,
            "",
            result,
            count=1,
        )

        if cleaned != result:
            return cleaned

    return result


def to_accessible_speech(text: str) -> str:
    if not text:
        return ""

    result = _remove_leading_option_label(text)

    # SAFE MARKDOWN CLEANUP
    # Sunum isaretlerini kaldir; matematikteki tek '*' operatorunu koru.
    result = re.sub(
        r"(?m)^\s{0,3}#{1,6}\s+",
        "",
        result,
    )

    result = re.sub(
        r"\*\*([^\n*]+?)\*\*",
        r"\1",
        result,
    )

    result = re.sub(
        r"__([^\n_]+?)__",
        r"\1",
        result,
    )

    result = re.sub(
        r"(?m)^\s*[???]\s+",
        "",
        result,
    )

    result = re.sub(
        r"(?m)^\s*\*\s+",
        "",
        result,
    )

    result = re.sub(
        r"(?<=[.!?;:])\s+\*\s+",
        " ",
        result,
    )

    result = _replace_percent(result)
    result = _replace_decimal(result)
    result = _replace_simple_fraction(result)
    result = _replace_superscripts(result)
    result = _replace_square_root(result)
    result = _replace_inequalities(result)
    result = _replace_implicit_multiplication(result)
    result = _replace_operators(result)
    result = _replace_roman_numerals(result)
    result = _replace_standalone_integers(result)

    result = re.sub(r"\s+", " ", result).strip()

    return result
