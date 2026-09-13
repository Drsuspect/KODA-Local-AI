from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from services.morphology_service import MorphologyService

ROOT = Path(__file__).resolve().parent.parent

SYNONYMS_PATH = (
    ROOT / "data" / "routing" / "routing_synonyms.json"
)

ROUTE_MAP_PATH = (
    ROOT / "data" / "routing" / "canonical_route_map.json"
)

KRI_PATH = (
    ROOT / "data" / "routing" / "knowledge_routing_index_v02.json"
)


def normalize_text(text: str) -> str:
    text = str(text).lower()

    table = str.maketrans({
        "\u0131": "i",
        "\u011f": "g",
        "\u00fc": "u",
        "\u015f": "s",
        "\u00f6": "o",
        "\u00e7": "c",
        "\u00e2": "a",
        "\u00ee": "i",
        "\u00fb": "u",
    })

    text = text.translate(table)

    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())


class RoutingLanguageService:

    def __init__(self):
        self.morph = MorphologyService()

        self.synonyms = json.loads(
            SYNONYMS_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        self.route_map = json.loads(
            ROUTE_MAP_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        self.kri = json.loads(
            KRI_PATH.read_text(
                encoding="utf-8-sig"
            )
        )

        self.routes_by_key = {
            route["route_key"]: route
            for route in self.kri["routes"]
        }

        self.lookup = []

        for canonical, variants in self.synonyms.items():
            for variant in variants:
                self.lookup.append(
                    (
                        normalize_text(variant),
                        canonical
                    )
                )

        self.lookup.sort(
            key=lambda x: len(x[0].split()),
            reverse=True
        )

    def canonicalize_text(self, text: str):
        normalized = normalize_text(text)

        found = []

        for variant, canonical in self.lookup:
            pattern = (
                r"\b"
                + re.escape(variant)
                + r"\b"
            )

            if re.search(pattern, normalized):
                if canonical not in found:
                    found.append(canonical)

        return found

    def analyse(self, question: str):
        morph_items = self.morph.analyse_text(
            question
        )

        lemmas = [
            item["lemma"]
            for item in morph_items
        ]

        lemma_text = " ".join(lemmas)

        canonical = []

        for source_text in (
            question,
            lemma_text
        ):
            for item in self.canonicalize_text(
                source_text
            ):
                if item not in canonical:
                    canonical.append(item)

        route_keys = []

        for item in canonical:
            route_key = self.route_map.get(item)

            if (
                route_key
                and route_key not in route_keys
            ):
                route_keys.append(route_key)

        routes = []

        for route_key in route_keys:
            route = self.routes_by_key.get(
                route_key
            )

            if route:
                routes.append({
                    "route_key": route_key,
                    "subject": route.get("subject"),
                    "lesson_code": route.get("lesson_code"),
                    "title": route.get("title"),
                    "paths": route.get("paths"),
                })

        return {
            "question": question,
            "lemmas": lemmas,
            "lemma_text": lemma_text,
            "canonical": canonical,
            "route_keys": route_keys,
            "routes": routes,
            "morphology": morph_items,
        }

    def close(self):
        self.morph.close()
