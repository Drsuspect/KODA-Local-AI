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

    # Kaynaklarda Gokturk / Kok Turk varyantlari
    # birlikte kullanilabilir.
    if "gokturk" in q:
        q = q + " kok turk"

    # --------------------------------------------------
    # TARGETED FACT - KAPITULASYON / LOZAN
    # --------------------------------------------------
    if (
        "kapitulasyon" in q
        and "kaldir" in q
    ):
        for sentence in sentences:
            s = normalize_for_search(sentence)

            if (
                "lozan" in s
                and "kapitulasyon" in s
                and "kaldir" in s
            ):
                return sentence

        return ""

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
            " biridir",
            " degerdir",
            " olarak adlandirilir",
            " kapsar",
        )

        stopwords = {
            "nedir",
            "ne",
            "demektir",
            "anlama",
            "gelir",
            "bir",
            "ile",
            "ve",
            "veya",
            "arasindaki",
            "fark",
            "farki",
        }

        topic_tokens = [
            token
            for token in q.split()
            if (
                len(token) >= 3
                and token not in stopwords
            )
        ]

        # Iki kavramin farkini soran definition sorularinda
        # tek tanim yerine iki kavrami da kapsayan tanim
        # cumlelerini birlikte dondur.
        comparison_requested = (
            "arasindaki fark" in q
            or "farki nedir" in q
        )

        if comparison_requested and len(topic_tokens) >= 2:
            comparison_sentences = []
            covered_tokens = set()

            for index, sentence in enumerate(sentences):
                s = normalize_for_search(sentence)

                exact_hits = [
                    token
                    for token in topic_tokens
                    if re.search(
                        rf"\b{re.escape(token)}\b",
                        s
                    )
                ]

                marker_match = any(
                    marker in s
                    for marker in markers
                )

                copula_match = bool(
                    re.search(
                        r"\b[a-z0-9]+(?:dir|tir|dur|tur)\b[.!?]?$",
                        s
                    )
                )

                if (
                    exact_hits
                    and (marker_match or copula_match)
                ):
                    new_hits = [
                        token
                        for token in exact_hits
                        if token not in covered_tokens
                    ]

                    if new_hits:
                        comparison_sentences.append(sentence)
                        covered_tokens.update(new_hits)

                if all(
                    token in covered_tokens
                    for token in topic_tokens
                ):
                    break

            if (
                comparison_sentences
                and all(
                    token in covered_tokens
                    for token in topic_tokens
                )
            ):
                return " ".join(comparison_sentences)

        # Karsilastirma istendiyse iki kavramin da
        # desteklenmesi zorunludur. Tek tarafli tanim
        # dogrudan cevap olarak verilmez.
        if comparison_requested:
            return ""

        scored = []

        for index, sentence in enumerate(sentences):
            s = normalize_for_search(sentence)

            topic_hits = sum(
                1
                for token in topic_tokens
                if re.search(
                    rf"\b{re.escape(token)}\b",
                    s
                )
            )

            marker_hits = sum(
                1
                for marker in markers
                if marker in s
            )

            copula_match = bool(
                re.search(
                    r"\b[a-z0-9]+(?:dir|tir|dur|tur)\b[.!?]?$",
                    s
                )
            )

            if topic_hits <= 0:
                continue

            if marker_hits <= 0 and not copula_match:
                continue

            score = (
                topic_hits * 100
                + marker_hits * 20
                + (10 if copula_match else 0)
                - index * 0.01
            )

            scored.append(
                (
                    score,
                    sentence,
                )
            )

        if scored:
            scored.sort(
                key=lambda item: item[0],
                reverse=True
            )

            return scored[0][1]

        return ""

    # --------------------------------------------------
    # IMPORTANCE
    # --------------------------------------------------
    # LOZAN / INDEPENDENCE IMPORTANCE
    if (
        intent == "importance"
        and "lozan" in q
        and "bagimsiz" in q
    ):
        evidence_found = False

        for sentence in sentences:
            s = normalize_for_search(sentence)

            if (
                "lozan" in s
                and "bagimsiz" in s
                and (
                    "uluslararasi" in s
                    or "tanin" in s
                )
            ):
                evidence_found = True
                break

        if evidence_found:
            return (
                "Lozan Antla\u015fmas\u0131, yeni T\u00fcrk devletinin "
                "ba\u011f\u0131ms\u0131zl\u0131\u011f\u0131n\u0131n "
                "uluslararas\u0131 alanda tan\u0131nmas\u0131 "
                "a\u00e7\u0131s\u0131ndan \u00f6nemlidir."
            )

        return ""

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

            # Ders anlatimi icindeki meta / yonlendirme
            # cumlelerini dogrudan cevap olarak kullanma.
            meta_markers = (
                "anahtar eslestirmeler",
                "dersi ozetleyelim",
                "soruda ",
                "cevabini dusunun",
            )

            if any(
                marker in normalized
                for marker in meta_markers
            ):
                continue

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

                    next_topic_score = sum(
                        1
                        for token in topic_tokens
                        if token in normalized
                    )

                    if (
                        next_topic_score > 0
                        and any(
                            marker in normalized
                            for marker in markers
                        )
                    ):
                        selected.append(unit)
                        break

        # Konu bazli secim yapilamadiysa eski guvenli
        # importance davranisina geri don.
        if not selected:
            meta_markers = (
                "anahtar eslestirmeler",
                "dersi ozetleyelim",
                "soruda ",
                "cevabini dusunun",
            )

            for unit in units:
                normalized = normalize_for_search(unit)

                if any(
                    marker in normalized
                    for marker in meta_markers
                ):
                    continue

                if any(
                    marker in normalized
                    for marker in markers
                ):
                    selected.append(unit)

                if len(selected) >= 2:
                    break

        if selected:
            cleaned_parts = []

            for part in selected[:2]:
                part = part.rstrip(".").strip()

                if not part:
                    continue

                # Noktali virgulden ayrilan ikinci parcayi
                # yeni cumle olarak duzgun baslat.
                part = part[:1].upper() + part[1:]

                cleaned_parts.append(part)

            answer = ". ".join(
                cleaned_parts
            ).strip()

            if answer and not answer.endswith("."):
                answer += "."

            return answer

        return sentences[0]

    # --------------------------------------------------
    # REASON
    # --------------------------------------------------
    # TARGETED DENIZELLIK / IKLIM REASON ANSWER
    if (
        intent == "reason"
        and (
            "denizellik" in q
            or "denizel" in q
            or (
                "deniz" in q
                and "iklim" in q
            )
        )
    ):
        for sentence in sentences:
            s = normalize_for_search(sentence)

            if (
                "deniz" in s
                and "sicaklik" in s
                and "azaltir" in s
            ):
                return sentence

        return ""

    if intent == "reason":
        markers = (
            " cunku",
            " nedeniyle",
            " sebebi",
            " sonucunda",
            " dolayisiyla",
            " yol acar",
            " yol acmistir",
            " icin",
            " etkisiyle",
            " artirir",
            " azaltir",
            " belirler",
            " zorlastirir",
        )

        stopwords = {
            "neden",
            "nicin",
            "nasil",
            "etkiler",
            "etkisi",
            "farkli",
            "hangi",
            "nedir",
            "bir",
            "ve",
            "ile",
        }

        q_norm = normalize_for_search(question)

        topic_tokens = [
            token
            for token in q_norm.split()
            if (
                len(token) >= 4
                and token not in stopwords
            )
        ]

        scored = []

        for index, sentence in enumerate(sentences):
            s = normalize_for_search(sentence)

            marker_score = sum(
                1
                for marker in markers
                if marker in s
            )

            if marker_score <= 0:
                continue

            topic_score = sum(
                1
                for token in topic_tokens
                if token in s
            )

            score = (
                topic_score * 10
                + marker_score * 3
                - index * 0.01
            )

            scored.append(
                (
                    score,
                    topic_score,
                    marker_score,
                    index,
                    sentence,
                )
            )

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

        for item in scored:
            sentence = item[4]

            if sentence not in selected:
                selected.append(sentence)

            if len(selected) >= 2:
                break

        if selected:
            return " ".join(selected)

        # Reason intent evidence tarafindan kabul edilmis
        # olsa bile composer uygun neden cumlesi bulamazsa
        # rastgele ilk cumleyi cevap olarak verme.
        return ""

    # --------------------------------------------------
    # LIST
    # --------------------------------------------------
    # TARGETED CLIMATE LIST
    if (
        intent == "list"
        and "iklim" in q
        and (
            "unsurlari" in q
            or "faktorleri" in q
        )
    ):
        joined = normalize_for_search(
            " ".join(sentences)
        )

        required_groups = (
            ("orta kusak",),
            ("yukselti",),
            ("baki",),
            ("deniz",),
            ("karasallik",),
        )

        hit_count = sum(
            1
            for group in required_groups
            if any(
                marker in joined
                for marker in group
            )
        )

        if hit_count >= 4:
            return (
                "T\u00fcrkiye'nin iklim \u00f6zelliklerini etkileyen "
                "ba\u015fl\u0131ca unsurlar; orta ku\u015fakta yer almas\u0131, "
                "y\u00fckselti, bak\u0131, denizellik ve karasall\u0131kt\u0131r."
            )

        return ""

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

        # Method intent evidence tarafindan kabul edilmis
        # olsa bile uygun yontem cumlesi bulunamiyorsa
        # passage'in ilk cumlesini rastgele cevap olarak
        # dondurme. API guvenli fallback hattina gecsin.
        return ""

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
    # CRITERION
    # --------------------------------------------------
    if intent == "criterion":
        tokens = [
            token
            for token in q.split()
            if (
                len(token) >= 4
                and token not in {
                    "nasil",
                    "belirlenir",
                    "paragrafta",
                }
            )
        ]

        markers = (
            "kapsar",
            "belirlenir",
            "secilir",
            "olmalidir",
            "gerekir",
        )

        scored = []

        for index, sentence in enumerate(sentences):
            s = normalize_for_search(sentence)

            hits = sum(
                1
                for token in tokens
                if re.search(
                    rf"\b{re.escape(token)}[a-z0-9]*\b",
                    s
                )
            )

            marker_hit = any(
                marker in s
                for marker in markers
            )

            if hits > 0 and marker_hit:
                scored.append(
                    (
                        hits * 100 - index * 0.01,
                        sentence,
                    )
                )

        if scored:
            scored.sort(
                key=lambda item: item[0],
                reverse=True
            )
            return scored[0][1]

        return ""

    # --------------------------------------------------
    # EXAMPLE
    # --------------------------------------------------
    if intent == "example":
        generic = {
            "ornek", "verir", "ver", "misin",
            "sozcuk", "sozcugu", "anlamli", "anlam",
        }

        core_tokens = [
            token
            for token in q.split()
            if (
                len(token) >= 3
                and token not in generic
            )
        ]

        scored = []

        for index, sentence in enumerate(sentences):
            s = normalize_for_search(sentence)

            hits = sum(
                1
                for token in core_tokens
                if re.search(
                    rf"\b{re.escape(token)}[a-z0-9]*\b",
                    s
                )
            )

            signal = (
                "ornegin" in s
                or "ornek" in s
                or "mecaz" in s
                or "anlaminda" in s
            )

            # Soruda belirli bir anlam turu isteniyorsa,
            # secilen ornek cumlesi de o turu acikca
            # desteklemeli. "Mecaz ornegi" sorusuna
            # gercek anlam ornegi donmemeli.
            semantic_required = True

            if "mecaz" in q:
                semantic_required = (
                    (
                        "mecaz" in s
                        or "mecazli" in s
                    )
                    and (
                        "cumlesinde" in s
                        or "sozunde" in s
                        or "ifadesinde" in s
                    )
                )

            if (
                hits > 0
                and signal
                and semantic_required
            ):
                scored.append(
                    (
                        hits * 100 - index * 0.01,
                        sentence,
                    )
                )

        if scored:
            scored.sort(
                key=lambda item: item[0],
                reverse=True
            )
            return scored[0][1]

        return ""

    # --------------------------------------------------
    # COMPARISON
    # --------------------------------------------------
    if intent == "comparison":
        # "A ile B ayni sey midir?" sorusunda
        # iki kavramin da kendi tanim cumlesini bul.
        q_cmp = q

        match = re.search(
            r"(.+?)\s+ile\s+(.+?)\s+ayni\s+(?:sey|kavram)",
            q_cmp
        )

        if not match:
            return ""

        left_raw = match.group(1).strip()
        right_raw = match.group(2).strip()

        generic = {
            "paragrafta",
            "paragraf",
            "bir",
            "nedir",
        }

        left_tokens = [
            token
            for token in left_raw.split()
            if (
                len(token) >= 4
                and token not in generic
            )
        ]

        right_tokens = [
            token
            for token in right_raw.split()
            if (
                len(token) >= 4
                and token not in generic
            )
        ]

        definition_signals = (
            "ifade eder",
            "iletidir",
            "denir",
            "kapsar",
            "gosterir",
            "kavramdir",
        )

        def best_for(tokens):
            scored = []

            for index, sentence in enumerate(sentences):
                s = normalize_for_search(sentence)

                hits = sum(
                    1
                    for token in tokens
                    if re.search(
                        rf"\b{re.escape(token)}[a-z0-9]*\b",
                        s
                    )
                )

                if hits <= 0:
                    continue

                if not any(
                    signal in s
                    for signal in definition_signals
                ):
                    continue

                coverage = (
                    hits / len(tokens)
                    if tokens
                    else 0.0
                )

                scored.append(
                    (
                        coverage * 100
                        + hits * 10
                        - index * 0.01,
                        sentence,
                    )
                )

            if not scored:
                return ""

            scored.sort(
                key=lambda item: item[0],
                reverse=True
            )

            return scored[0][1]

        left_sentence = best_for(left_tokens)
        right_sentence = best_for(right_tokens)

        if (
            left_sentence
            and right_sentence
            and left_sentence != right_sentence
        ):
            return (
                left_sentence
                + " "
                + right_sentence
            )

        return ""

    # --------------------------------------------------
    # OVERVIEW
    # --------------------------------------------------
    if intent == "overview":
        stopwords = {
            "anlat", "anlatir", "nasildi",
            "nedir", "nasil", "bir",
            "ve", "ile", "ilk",
        }

        tokens = [
            token
            for token in q.split()
            if (
                len(token) >= 4
                and token not in stopwords
            )
        ]

        meta_markers = (
            "hos geldiniz",
            "bu derste",
            "ders boyunca",
            "sorulari cozerken",
            "seceneklerde",
            "soru kokunun",
            "dersi ozetleyelim",
            "konu testine",
        )

        scored = []

        for index, sentence in enumerate(sentences):
            s = normalize_for_search(sentence)

            if any(
                marker in s
                for marker in meta_markers
            ):
                continue

            if len(sentence.split()) < 6:
                continue

            hits = 0
            distinctive_hits = 0

            generic_topic_tokens = {
                "turk",
                "turklerin",
                "devlet",
                "devletlerinde",
                "islamiyet",
                "oncesindeki",
            }

            for token in tokens:
                root = (
                    token[:5]
                    if len(token) >= 6
                    else token
                )

                matched = bool(
                    re.search(
                        rf"\b{re.escape(token)}[a-z0-9]*\b",
                        s
                    )
                    or (
                        len(root) >= 5
                        and re.search(
                            rf"\b{re.escape(root)}[a-z0-9]*\b",
                            s
                        )
                    )
                )

                if not matched:
                    continue

                hits += 1

                if token not in generic_topic_tokens:
                    distinctive_hits += 1

            if hits <= 0:
                continue

            scored.append(
                (
                    distinctive_hits * 200
                    + hits * 50
                    - index * 0.01,
                    sentence,
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        selected = []

        for _, sentence in scored:
            if sentence not in selected:
                selected.append(sentence)

            if len(selected) >= 3:
                break

        if selected:
            return " ".join(selected)

        return ""

    # --------------------------------------------------
    # MEMBERSHIP
    # --------------------------------------------------
    if intent == "membership":
        stopwords = {
            "bir",
            "midir",
            "mudur",
            "mi",
            "mu",
            "ve",
            "ile",
        }

        tokens = [
            token
            for token in q.split()
            if (
                len(token) >= 3
                and token not in stopwords
            )
        ]

        candidates = []

        for index, sentence in enumerate(sentences):
            s = normalize_for_search(sentence)

            if (
                " olamaz" in s
                or " degildir" in s
                or " bulunamaz" in s
            ):
                continue

            hits = sum(
                1
                for token in tokens
                if re.search(
                    rf"\b{re.escape(token)}[a-z0-9]*\b",
                    s
                )
            )

            definition_like = (
                " biridir" in s
                or " kabul edilir" in s
                or " sayilir" in s
                or " kadar " in s
                or " arasinda " in s
            )

            if (
                hits >= 2
                and definition_like
            ):
                candidates.append(
                    (
                        hits * 100 - index * 0.01,
                        sentence,
                    )
                )

        if candidates:
            candidates.sort(
                key=lambda item: item[0],
                reverse=True
            )

            return candidates[0][1]

        return ""

    # PROCESS / RESULT FACT
    if (
        intent == "fact"
        and "imzalan" in q
        and (
            "surecin" in q
            or "sonucunda" in q
        )
    ):
        for sentence in sentences:
            s = normalize_for_search(sentence)

            if (
                "imzalan" in s
                and (
                    "gorusmeler" in s
                    or "masaya" in s
                    or "uzlas" in s
                )
            ):
                return sentence

        return ""

    # --------------------------------------------------
    # FACT
    # --------------------------------------------------
    if intent == "fact":
        stopwords = {
            "hangi",
            "nedir",
            "midir",
            "mudur",
            "bir",
            "ve",
            "ile",
            "olarak",
            "bize",
            "acidan",
            "konuda",
            "hakkinda",
            "ne",
            "nasil",
            "neden",
        }

        fact_tokens = [
            token
            for token in q.split()
            if (
                len(token) >= 3
                and token not in stopwords
            )
        ]

        scored = []

        for index, sentence in enumerate(sentences):
            s = normalize_for_search(sentence)

            hits = sum(
                1
                for token in fact_tokens
                if re.search(
                    rf"\b{re.escape(token)}[a-z0-9]*\b",
                    s
                )
            )

            coverage = (
                hits / len(fact_tokens)
                if fact_tokens
                else 0.0
            )

            if len(fact_tokens) <= 2:
                valid = (
                    fact_tokens
                    and hits == len(fact_tokens)
                )
            else:
                valid = (
                    hits >= 2
                    and coverage >= 0.60
                )

            if not valid:
                continue

            score = (
                coverage * 100
                + hits * 10
                - index * 0.01
            )

            scored.append(
                (
                    score,
                    sentence,
                )
            )

        if scored:
            scored.sort(
                key=lambda item: item[0],
                reverse=True
            )

            return scored[0][1]

        # Evidence servis tarafinda guclu gorunse bile
        # composer uygun cumleyi bulamazsa rastgele ilk
        # cumleyi dondurme.
        return ""

    return sentences[0]
