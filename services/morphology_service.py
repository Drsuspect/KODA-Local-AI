from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DB = (
    ROOT
    / "data"
    / "language"
    / "kodaai"
    / "morph_lookup.sqlite"
)

_APOSTROPHES = {
    "\u2019": "'",
    "\u2018": "'",
    "\u02bc": "'",
    "`": "'",
    "\u00b4": "'",
}

class MorphologyService:

    def __init__(self, db_path=None):
        self.db_path = Path(db_path or DEFAULT_DB)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Morphology DB not found: {self.db_path}"
            )

        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row

    @staticmethod
    def normalize_apostrophe(text: str) -> str:
        value = str(text).strip()

        for old, new in _APOSTROPHES.items():
            value = value.replace(old, new)

        return value

    @staticmethod
    def strip_edge_punctuation(token: str) -> str:
        return token.strip(
            " \t\r\n"
            ".,;:!?()[]{}"
            "\"\u201c\u201d"
        )

    @classmethod
    def proper_noun_fallback(cls, token: str):
        token = cls.normalize_apostrophe(token)

        if "'" not in token:
            return None

        root, suffix = token.split("'", 1)

        if not root or not suffix:
            return None

        if not root[0].isupper():
            return None

        return root

    def lookup(self, surface: str, limit: int = 20):
        surface = self.normalize_apostrophe(surface)

        rows = self.conn.execute(
            """
            SELECT lemma, pos, tags, source
            FROM morph
            WHERE surface = ?
            LIMIT ?
            """,
            (surface, limit)
        ).fetchall()

        return [dict(row) for row in rows]

    def analyse_token(self, token: str):
        original = token

        token = self.strip_edge_punctuation(
            self.normalize_apostrophe(token)
        )

        rows = self.lookup(token)

        if not rows and token:
            lowered = token.lower()

            if lowered != token:
                rows = self.lookup(lowered)

        if rows:
            return {
                "original": original,
                "surface": token,
                "lemma": rows[0]["lemma"],
                "analyses": rows,
                "method": "morph_db",
            }

        proper_root = self.proper_noun_fallback(token)

        if proper_root:
            return {
                "original": original,
                "surface": token,
                "lemma": proper_root,
                "analyses": [],
                "method": "proper_noun_fallback",
            }

        return {
            "original": original,
            "surface": token,
            "lemma": token,
            "analyses": [],
            "method": "identity",
        }

    def analyse_text(self, text: str):
        tokens = re.findall(
            r"[0-9A-Za-z\u00c7\u011e\u0130\u00d6\u015e\u00dc"
            r"\u00e7\u011f\u0131\u00f6\u015f\u00fc"
            r"\u00c2\u00ce\u00db\u00e2\u00ee\u00fb"
            r"'\u2019]+",
            text
        )

        return [
            self.analyse_token(token)
            for token in tokens
        ]

    def lemmatize_text(self, text: str):
        return [
            item["lemma"]
            for item in self.analyse_text(text)
        ]

    def close(self):
        self.conn.close()

