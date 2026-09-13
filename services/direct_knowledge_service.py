from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from pathlib import Path

from services.routing_language_service import (
    RoutingLanguageService
)

from common.turkish_text import (
    normalize_for_search as _normalize_for_search,
)


ROOT = Path(__file__).resolve().parent.parent

DB_PATH = (
    ROOT
    / "data"
    / "routing"
    / "knowledge_index.sqlite"
)


STOP_WORDS = {
    "ve",
    "veya",
    "ile",
    "bir",
    "bu",
    "su",
    "nedir",
    "nelerdir",
    "neler",
    "hangileri",
    "hangileridir",
    "icin",
    "olan",
    "olarak",
    "mi",
    "midir",
    "dir",
    "kim",
    "nasil",
}


def normalize_text(text: str) -> str:
    """
    Compatibility wrapper.

    Turkish normalization is owned exclusively by
    common.turkish_text.
    """
    return _normalize_for_search(text)


INTENT_MARKERS = {
    "person": (
        "kim",
        "kimdir",
        "kimdi",
        "kim yazdi",
        "kim yazmistir",
    ),
    "date": (
        "ne zaman",
        "hangi tarihte",
        "tarihi nedir",
        "tarihinde",
    ),
    "location": (
        "nerede",
        "neresidir",
        "hangi yerde",
    ),
    "importance": (
        "onemi",
        "neden onemli",
        "neden onemlidir",
    ),
    "reason": (
        "neden",
        "ni?in",
        "nicin",
        "sebebi",
        "sebebi nedir",
    ),
    "method": (
        "nasil",
        "nasil yapilir",
        "nasil cozulur",
    ),
    "list": (
        "nelerdir",
        "neler",
        "hangileri",
        "hangileridir",
    ),
    "definition": (
        "nedir",
        "ne demektir",
        "ne anlama gelir",
    ),
}


def detect_direct_intent(question: str) -> str:
    normalized = normalize_text(question)

    # Daha spesifik intentler once kontrol edilir.
    order = (
        "person",
        "date",
        "location",
        "importance",
        "reason",
        "method",
        "list",
        "definition",
    )

    for intent in order:
        for marker in INTENT_MARKERS[intent]:
            if normalize_text(marker) in normalized:
                return intent

    return "fact"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def passage_intent_score(
    intent: str,
    text: str,
    query_tokens: list[str] | None = None,
) -> float:
    normalized = normalize_text(text)

    if not normalized:
        return 0.0

    query_tokens = [
        normalize_text(token)
        for token in (query_tokens or [])
        if len(normalize_text(token)) >= 4
    ]

    sentences = [
        normalize_text(part)
        for part in re.split(r"[.!?;\n]+", text)
        if part.strip()
    ]

    def sentence_has_topic(sentence: str) -> bool:
        if not query_tokens:
            return True

        hits = sum(
            1
            for token in query_tokens
            if token in sentence
        )

        return hits >= 1

    if intent == "definition":
        markers = (
            " denir",
            " olarak tanimlanir",
            " ifade eder",
            " anlamina gelir",
            " biciminde yazilabilen",
            " kabul edilir",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "person":
        # Kisi sorusunda konu ve kisi-iliski ifadesi
        # AYNI cumlede bulunmak zorunda.
        relation_markers = (
            " tarafindan yazildi",
            " tarafindan yazilmistir",
            " yazdi",
            " yazmistir",
            " kaleme aldi",
            " kaleme almistir",
            " hazirladi",
            " hazirlamistir",
            " kurdu",
            " kurmustur",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(
                    sentence,
                    relation_markers
                )
            ):
                return 1.0

        return 0.0

    elif intent == "date":
        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and re.search(
                    r"\b(1[0-9]{3}|20[0-9]{2})\b",
                    sentence
                )
            ):
                return 1.0

    elif intent == "location":
        markers = (
            " bulunur",
            " bulunmaktadir",
            " yer alir",
            " bolgesinde",
            " ilinde",
            " ilcesinde",
            " kiyisinda",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "importance":
        markers = (
            " onemli",
            " onemlidir",
            " onemi",
            " en onemli",
            " taninir",
            " taninmistir",
            " kabul edilir",
            " kaldirilir",
            " kaldirilmistir",
            " sona erer",
            " sona ermistir",
            " saglar",
            " saglamistir",
            " sonucunda",
            " kaynaklarindandir",
            " uluslararasi alanda",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "reason":
        markers = (
            " cunku",
            " nedeniyle",
            " sebebi",
            " sonucunda",
            " dolayisiyla",
            " yol acar",
            " yol acmistir",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "method":
        markers = (
            " once",
            " sonra",
            " uygulanir",
            " yapilir",
            " cozulur",
            " belirlenir",
            " dikkate alinir",
            " kontrol edilir",
        )

        for sentence in sentences:
            if (
                sentence_has_topic(sentence)
                and _contains_any(sentence, markers)
            ):
                return 1.0

    elif intent == "list":
        # Klasik virgullu / noktali virgul ile yazilan liste.
        for sentence in sentences:
            if not sentence_has_topic(sentence):
                continue

            if (
                sentence.count(",") >= 2
                or sentence.count(";") >= 2
            ):
                return 1.0

        # Dogal dilde liste her zaman tek cumlede yazilmaz.
        # Ornek:
        # "Karadeniz iklimi ... Akdeniz iklimi ...
        #  Ic kesimlerde karasal iklim ..."
        #
        # Route zaten kesin oldugu icin, ayni passage icinde
        # birden fazla aciklayici cumle varsa guclu liste
        # sinyali kabul ediyoruz.
        informative_sentences = [
            sentence
            for sentence in sentences
            if len(sentence.split()) >= 5
        ]

        topic_hits = sum(
            1
            for token in query_tokens
            if token in normalized
        )

        if (
            len(informative_sentences) >= 3
            and topic_hits >= 1
        ):
            return 1.0

    else:
        return 0.5

    return 0.0


class DirectKnowledgeService:

    def __init__(self):

        if not DB_PATH.exists():
            raise FileNotFoundError(
                f"Knowledge index yok: "
                f"{DB_PATH}"
            )

        self.conn = sqlite3.connect(
            str(DB_PATH),
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

        self.routing = (
            RoutingLanguageService()
        )

    def _query_tokens(
        self,
        route_analysis: dict
    ) -> list[str]:

        parts = []

        parts.append(
            route_analysis.get(
                "lemma_text",
                ""
            )
        )

        for item in (
            route_analysis.get(
                "canonical",
                []
            )
        ):
            parts.append(
                str(item).replace(
                    "_",
                    " "
                )
            )

        text = normalize_text(
            " ".join(parts)
        )

        tokens = []

        for token in text.split():

            if (
                len(token) > 2
                and token not in STOP_WORDS
                and token not in tokens
            ):
                tokens.append(token)

        return tokens

    def search(
        self,
        question: str,
        limit: int = 5
    ) -> dict:

        started = time.perf_counter()

        route_started = time.perf_counter()

        route = self.routing.analyse(
            question
        )

        route_ms = (
            time.perf_counter()
            - route_started
        ) * 1000

        routes = route.get(
            "routes",
            []
        )

        if len(routes) != 1:
            return {
                "route": "NO_SINGLE_ROUTE",
                "route_ms": round(
                    route_ms,
                    3
                ),
                "total_ms": round(
                    (
                        time.perf_counter()
                        - started
                    ) * 1000,
                    3
                ),
                "route_analysis": route,
                "results": [],
            }

        route_item = routes[0]
        route_key = route_item[
            "route_key"
        ]

        tokens = self._query_tokens(
            route
        )

        if not tokens:
            return {
                "route": "NO_QUERY_TOKENS",
                "route_key": route_key,
                "results": [],
            }

        fts_query = " OR ".join(
            f'"{token}"'
            for token in tokens
        )

        sql_started = time.perf_counter()

        rows = self.conn.execute(
            """
            SELECT
                p.id,
                p.route_key,
                p.subject,
                p.lesson_code,
                p.route_title,
                p.content_type,
                p.file_path,
                p.json_path,
                p.text,
                bm25(passages_fts) AS rank
            FROM passages_fts
            JOIN passages p
                ON p.id = passages_fts.passage_id
            WHERE passages_fts MATCH ?
              AND passages_fts.route_key = ?
            ORDER BY rank
            LIMIT ?
            """,
            (
                fts_query,
                route_key,
                max(limit * 8, 20),
            )
        ).fetchall()

        sql_ms = (
            time.perf_counter()
            - sql_started
        ) * 1000

        results = [
            dict(row)
            for row in rows
        ]

        # FTS bazi "nasil / neden / nelerdir" sorularinda
        # route icindeki faydali segmentleri token eslesmesi
        # olmadigi icin kacirabilir.
        #
        # Aday havuzu zayifsa ayni route'un reading
        # segmentlerini de kontrollu sekilde ekle.
        if len(results) < 10:
            existing_ids = {
                int(item["id"])
                for item in results
                if item.get("id") is not None
            }

            route_rows = self.conn.execute(
                """
                SELECT
                    id,
                    route_key,
                    subject,
                    lesson_code,
                    route_title,
                    content_type,
                    file_path,
                    json_path,
                    text,
                    0.0 AS rank
                FROM passages
                WHERE route_key = ?
                  AND content_type = 'reading'
                  AND json_path LIKE '$.segments[%'
                LIMIT 40
                """,
                (route_key,)
            ).fetchall()

            for row in route_rows:
                item = dict(row)

                if int(item["id"]) in existing_ids:
                    continue

                results.append(item)
                existing_ids.add(
                    int(item["id"])
                )

        def passage_quality(item: dict) -> float:
            score = 0.0

            content_type = str(
                item.get("content_type") or ""
            )

            json_path = str(
                item.get("json_path") or ""
            )

            text_value = str(
                item.get("text") or ""
            ).strip()

            text_len = len(text_value)

            # Reading i?eriklerini tercih et.
            if content_type == "reading":
                score += 2.0

            # Quiz sadece do?rudan soru-cevap gerekiyorsa de?erlidir.
            if content_type == "quiz":
                score -= 1.5

            # Root kay?tlar? ?o?unlukla yaln?z ba?l?kt?r.
            if json_path == "$":
                score -= 3.0

            # Ger?ek segment passage'lar?n? kuvvetle ?ne ??kar.
            if json_path.startswith("$.segments["):
                score += 3.0

            # ?ok k?sa i?erikler genellikle title / label kay?tlar?d?r.
            if text_len < 80:
                score -= 2.0
            elif text_len >= 180:
                score += 1.0
            elif text_len >= 350:
                score += 1.5

            normalized = normalize_text(text_value)

            # Tan?m / a??klama t?r? pasajlara k???k bonus.
            definition_markers = (
                "denir",
                "ifade eder",
                "anlamina gelir",
                "biciminde",
                "kabul edilir",
                "amac",
                "onemi",
                "ozelligi",
            )

            marker_hits = sum(
                1
                for marker in definition_markers
                if marker in normalized
            )

            score += min(
                marker_hits * 0.35,
                1.40
            )

            # FTS bm25 d???k / daha negatif ise daha iyi.
            # Bunu tamamen yok etmiyoruz, sadece kalite ile dengeliyoruz.
            rank = item.get("rank")

            if isinstance(rank, (int, float)):
                score += min(
                    abs(float(rank)) * 0.08,
                    1.50
                )

            return round(score, 4)

        for item in results:
            item["quality_score"] = passage_quality(
                item
            )

        results.sort(
            key=lambda item: item["quality_score"],
            reverse=True
        )

        intent = detect_direct_intent(question)

        # Intent-aware candidate evaluation
        #
        # FTS ve quality rerank adaylari getirir.
        # Son karar tek basina quality_score ile degil,
        # passage'in soru niyetini gercekten karsilayip
        # karsilamadigina gore verilir.
        evaluated_results = []

        for item in results:
            quality = float(
                item.get("quality_score") or 0.0
            )

            intent_score = passage_intent_score(
                intent,
                str(item.get("text") or ""),
                tokens,
            )

            quality_component = max(
                0.0,
                min(quality / 7.0, 1.0)
            )

            route_component = 1.0

            confidence = (
                route_component * 0.25
                + quality_component * 0.35
                + intent_score * 0.40
            )

            confidence = round(
                max(
                    0.0,
                    min(confidence, 1.0)
                ),
                3
            )

            item["intent_score"] = intent_score
            item["direct_confidence"] = confidence

            # Intent karsilayan passage'lari yukariya cek.
            #
            # Once intent_score,
            # sonra confidence,
            # sonra quality_score.
            selection_score = (
                intent_score * 10.0
                + confidence * 2.0
                + quality_component
            )

            item["selection_score"] = round(
                selection_score,
                4
            )

            evaluated_results.append(item)

        evaluated_results.sort(
            key=lambda item: (
                item.get("selection_score", 0.0),
                item.get("quality_score", 0.0),
            ),
            reverse=True
        )

        results = evaluated_results[:limit]

        best_item = (
            evaluated_results[0]
            if evaluated_results
            else None
        )

        direct_confidence = 0.0
        answerable = False

        if best_item is not None:
            intent_score = float(
                best_item.get("intent_score") or 0.0
            )

            direct_confidence = float(
                best_item.get(
                    "direct_confidence"
                ) or 0.0
            )

            strict_intents = {
                "person",
                "date",
                "location",
            }

            if intent in strict_intents:
                answerable = (
                    intent_score >= 1.0
                    and direct_confidence >= 0.70
                )
            else:
                answerable = (
                    intent_score >= 1.0
                    and direct_confidence >= 0.72
                )

        total_ms = (
            time.perf_counter()
            - started
        ) * 1000

        return {
            "route": "DIRECT_KNOWLEDGE",
            "route_key": route_key,
            "subject": route_item.get(
                "subject"
            ),
            "lesson_code": route_item.get(
                "lesson_code"
            ),
            "title": route_item.get(
                "title"
            ),
            "tokens": tokens,
            "route_ms": round(
                route_ms,
                3
            ),
            "sql_ms": round(
                sql_ms,
                3
            ),
            "total_ms": round(
                total_ms,
                3
            ),
            "intent": intent,
            "direct_confidence": direct_confidence,
            "answerable": answerable,
            "best_passage": best_item,
            "results": results,
        }

    def close(self):

        self.routing.close()
        self.conn.close()
