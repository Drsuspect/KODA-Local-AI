from __future__ import annotations

import re
import unicodedata


TURKISH_ASCII_MAP = {
    ord("\u0131"): "i",
    ord("\u011f"): "g",
    ord("\u00fc"): "u",
    ord("\u015f"): "s",
    ord("\u00f6"): "o",
    ord("\u00e7"): "c",
}


def ascii_fold_tr(text: str) -> str:
    text = str(text).casefold()
    text = text.translate(TURKISH_ASCII_MAP)

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    return "".join(
        ch
        for ch in text
        if not unicodedata.combining(ch)
    )


def normalize_turkish_text(text: str) -> str:
    text = ascii_fold_tr(text)

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def normalize_for_search(text: str) -> str:
    return normalize_turkish_text(text)


def tokenize_tr(text: str) -> list[str]:
    normalized = normalize_for_search(text)

    if not normalized:
        return []

    return normalized.split()
