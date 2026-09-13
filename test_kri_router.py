from pathlib import Path
import json
import re
import unicodedata
import time

INDEX_PATH = Path(
    "data/routing/knowledge_routing_index_v02.json"
)

data = json.loads(
    INDEX_PATH.read_text(encoding="utf-8")
)

routes = data["routes"]

def normalize_text(text: str) -> str:
    text = str(text).lower()

    table = str.maketrans({
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    })

    text = text.translate(table)

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())


def looks_like_math(text: str) -> bool:
    q = str(text).lower()

    # Güçlü matematik sembolleri
    strong = (
        "=",
        "+",
        "*",
        "/",
        "^",
        "<",
        ">",
        "%",
    )

    if any(x in q for x in strong) and any(
        ch.isdigit() for ch in q
    ):
        return True

    # Parantez + sayı/değişken kombinasyonu
    if (
        "(" in q
        and ")" in q
        and any(ch.isdigit() for ch in q)
    ):
        return True

    return False


def route_question(question: str):
    started = time.perf_counter()

    if looks_like_math(question):
        return {
            "route": "MATH",
            "route_ms": round(
                (time.perf_counter() - started) * 1000,
                3
            )
        }

    q = normalize_text(question)
    q_tokens = set(q.split())

    scored = []

    for route in routes:
        score = 0
        reasons = []

        # Tam / kısmi alias
        for alias in route["aliases_normalized"]:
            if not alias:
                continue

            if alias == q:
                score += 100
                reasons.append(
                    f"exact_alias:{alias}"
                )

            elif len(alias) >= 5 and alias in q:
                score += 30
                reasons.append(
                    f"alias:{alias}"
                )

        # Keyword örtüşmesi
        keyword_set = set(route["keywords"])
        overlap = q_tokens & keyword_set

        if overlap:
            token_score = len(overlap) * 5
            score += token_score
            reasons.append(
                "tokens:" + ",".join(sorted(overlap))
            )

        # Subject açıkça yazılmışsa
        subject = normalize_text(route["subject"])

        if subject in q_tokens:
            score += 15
            reasons.append(
                f"subject:{subject}"
            )

        # Başlık kelimelerine ek bonus
        title = normalize_text(
            route.get("title") or ""
        )

        title_tokens = set(title.split())
        title_overlap = q_tokens & title_tokens

        if title_overlap:
            score += len(title_overlap) * 15
            reasons.append(
                "title:" +
                ",".join(sorted(title_overlap))
            )

        if score > 0:
            scored.append({
                "score": score,
                "route_key": route["route_key"],
                "subject": route["subject"],
                "lesson_code": route["lesson_code"],
                "title": route["title"],
                "paths": route["paths"],
                "matched_tokens": sorted(overlap),
                "reasons": reasons,
            })

    scored.sort(
        key=lambda x: (
            x["score"],
            len(x["matched_tokens"])
        ),
        reverse=True
    )

    elapsed = round(
        (time.perf_counter() - started) * 1000,
        3
    )

    if not scored:
        return {
            "route": "GLOBAL_RAG",
            "score": 0,
            "route_ms": elapsed
        }

    best = scored[0]

    return {
        "route": "KRI",
        "route_ms": elapsed,
        **best,
        "alternatives": [
            {
                "route_key": x["route_key"],
                "title": x["title"],
                "score": x["score"]
            }
            for x in scored[1:4]
        ]
    }


tests = [
    "Orhun Yazıtlarının Türk tarihi açısından önemi nedir?",
    "Kut anlayışı nedir?",
    "İkili teşkilat nedir?",
    "Lozan Antlaşması neden önemlidir?",
    "Atatürk ilkeleri nelerdir?",
    "Türkiye'nin iklim özellikleri nelerdir?",
    "Sözcükte anlam nedir?",
    "Paragrafta anlam nedir?",
    "Rasyonel sayılar nedir?",
    "2*(x+3)=14",
]

for question in tests:
    print("\n" + "=" * 78)
    print("SORU :", question)

    result = route_question(question)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )

