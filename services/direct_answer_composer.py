from __future__ import annotations

import re

from common.turkish_text import normalize_for_search


def split_sentences(text: str) -> list[str]:
    text = str(text or "").strip()

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def strip_heading(text: str) -> str:
    lines = [
        line.strip()
        for line in str(text or "").splitlines()
        if line.strip()
    ]

    if not lines:
        return ""

    if len(lines) == 1:
        return lines[0]

    first = lines[0]

    # Kisa baslik satirlarini at.
    if (
        len(first) <= 80
        and not first.endswith((".", "?", "!"))
    ):
        return " ".join(lines[1:]).strip()

    return " ".join(lines).strip()


def compose_direct_answer(
    question: str,
    passage: str,
    intent: str,
) -> str:
    text = strip_heading(passage)

    if not text:
        return ""

    sentences = split_sentences(text)

    if not sentences:
        return text

    q = normalize_for_search(question)

    # --------------------------------------------------
    # DEFINITION
    # --------------------------------------------------
    if intent == "definition":
        markers = (
            " denir",
            " yazilabilen",
            " ifade eder",
            " anlamina gelir",
            " tanimlanir",
            " kabul edilir",
        )

        for sentence in sentences:
            s = normalize_for_search(sentence)

            if any(
                marker in s
                for marker in markers
            ):
                return sentence

        return sentences[0]

    # --------------------------------------------------
    # IMPORTANCE
    # --------------------------------------------------
    if intent == "importance":
        markers = (
            " taninir",
            " taninmistir",
            " kaldirilir",
            " kaldirilmistir",
            " onemli",
            " kaynaklarindandir",
            " sona erer",
            " saglar",
            " sonucunda",
        )

        # Noktali virgul iceren uzun cumleleri
        # anlamli alt parcalara ayir.
        units = []

        for sentence in sentences:
            parts = [
                part.strip(" ;:")
                for part in sentence.split(";")
                if part.strip(" ;:")
            ]

            units.extend(parts)

        q_norm = normalize_for_search(question)

        # Genel soru kelimelerini konu tespitinden cikar.
        stopwords = {
            "nedir",
            "nelerdir",
            "onemi",
            "acisindan",
            "neden",
            "ni?in",
            "nicin",
            "hangi",
            "nasil",
            "baris",
            "antlasmasinin",
            "antlasmasi",
        }

        topic_tokens = [
            token
            for token in q_norm.split()
            if (
                len(token) >= 4
                and token not in stopwords
            )
        ]

        scored = []

        for index, unit in enumerate(units):
            normalized = normalize_for_search(unit)

            marker_score = sum(
                1
                for marker in markers
                if marker in normalized
            )

            topic_score = sum(
                1
                for token in topic_tokens
                if token in normalized
            )

            score = (
                topic_score * 10
                + marker_score * 3
            )

            scored.append(
                (
                    score,
                    topic_score,
                    marker_score,
                    index,
                    unit,
                )
            )

        # Once soru konusu ile eslesen parca.
        scored.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
                -item[3],
            ),
            reverse=True,
        )

        selected = []

        if scored:
            best = scored[0]

            if (
                best[1] > 0
                and best[2] > 0
            ):
                selected.append(best[4])

                # Ana konu parcasi secildikten sonra,
                # ayni baglamdaki bir sonraki anlamli
                # importance parcasi da alinabilir.
                start_index = best[3] + 1

                for unit in units[start_index:]:
                    normalized = normalize_for_search(unit)

                    if any(
                        marker in normalized
                        for marker in markers
                    ):
                        selected.append(unit)
                        break

        # Konu bazli secim yapilamadiysa eski guvenli
        # importance davranisina geri don.
        if not selected:
            for unit in units:
                normalized = normalize_for_search(unit)

                if any(
                    marker in normalized
                    for marker in markers
                ):
                    selected.append(unit)

                if len(selected) >= 2:
                    break

        if selected:
            answer = ". ".join(
                part.rstrip(".")
                for part in selected[:2]
            ).strip()

            if answer and not answer.endswith("."):
                answer += "."

            return answer

        return sentences[0]

    # --------------------------------------------------
    # LIST
    # --------------------------------------------------
    if intent == "list":
        selected = []

        for sentence in sentences:
            if len(sentence.split()) >= 4:
                selected.append(sentence)

            if len(selected) >= 3:
                break

        if selected:
            return " ".join(selected)

        return sentences[0]

    # --------------------------------------------------
    # METHOD
    # --------------------------------------------------
    if intent == "method":
        markers = (
            " once",
            " sonra",
            " okuyun",
            " belirleyin",
            " izleyin",
            " kontrol edin",
            " dikkate alin",
        )

        selected = []

        for sentence in sentences:
            s = normalize_for_search(sentence)

            if any(
                marker in s
                for marker in markers
            ):
                selected.append(sentence)

            if len(selected) >= 2:
                break

        if selected:
            return " ".join(selected)

        return sentences[0]

    # --------------------------------------------------
    # PERSON / DATE / LOCATION
    # --------------------------------------------------
    if intent in {
        "person",
        "date",
        "location",
    }:
        return sentences[0]

    # --------------------------------------------------
    # FACT
    # --------------------------------------------------
    return sentences[0]
