from pathlib import Path
import json
import re
import unicodedata

PATH = Path("data/routing/routing_synonyms.json")

synonyms = json.loads(
    PATH.read_text(encoding="utf-8-sig")
)

def normalize(text):
    text = str(text).lower()

    table = str.maketrans({
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
        "â": "a",
        "î": "i",
        "û": "u"
    })

    text = text.translate(table)
    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())


# Uzun ifadeler önce eşleşsin.
lookup = []

for canonical, variants in synonyms.items():
    for variant in variants:
        lookup.append(
            (
                normalize(variant),
                canonical
            )
        )

lookup.sort(
    key=lambda x: len(x[0].split()),
    reverse=True
)


def canonicalize(text):
    normalized = normalize(text)

    matches = []

    for variant, canonical in lookup:
        pattern = r"\b" + re.escape(variant) + r"\b"

        if re.search(pattern, normalized):
            matches.append({
                "canonical": canonical,
                "matched": variant
            })

    # Aynı canonical birden fazla kez gelmesin.
    unique = []
    seen = set()

    for item in matches:
        if item["canonical"] in seen:
            continue

        seen.add(item["canonical"])
        unique.append(item)

    return {
        "original": text,
        "normalized": normalized,
        "canonical": [
            x["canonical"] for x in unique
        ],
        "matches": unique
    }


tests = [
    "Türkiye'nin iklim özellikleri nelerdir?",
    "Ülkemizin iklim özellikleri nelerdir?",
    "Bizim ülkede hava koşulları nasıldır?",
    "Göktürk Yazıtları neden önemlidir?",
    "Orhun kitabelerini kim yazmıştır?",
    "Kut anlayışı nedir?",
    "Lozan Barış Antlaşması neden önemlidir?",
    "Mustafa Kemal kimdir?",
    "Rasyonel sayılar nedir?",
    "Kelimede anlam nedir?",
    "Paragraf soruları nasıl çözülür?"
]

for question in tests:
    result = canonicalize(question)

    print("\n" + "=" * 72)
    print("SORU      :", result["original"])
    print("NORMALIZE :", result["normalized"])
    print("CANONICAL :", result["canonical"])

    for match in result["matches"]:
        print(
            "  ->",
            match["matched"],
            "=>",
            match["canonical"]
        )
