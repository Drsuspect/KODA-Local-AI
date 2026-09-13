from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent

KRI_PATH = (
    ROOT
    / "data"
    / "routing"
    / "knowledge_routing_index_v02.json"
)

DB_PATH = (
    ROOT
    / "data"
    / "routing"
    / "knowledge_index.sqlite"
)

EDU_ROOT = (
    ROOT.parent
    / "01_KODA_Education_Platform"
    / "kodaai"
    / "data"
    / "output"
    / "license"
)


TEXT_KEYS = {
    "title",
    "text",
    "tts_text",
    "content",
    "summary",
    "description",
    "definition",
    "explanation",
    "question",
    "answer",
    "correct_answer",
    "passage",
}


def normalize_text(text: str) -> str:
    text = str(text).casefold()

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

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return " ".join(text.split())


def collect_text(value) -> list[str]:
    parts = []

    if isinstance(value, str):
        value = value.strip()
        if value:
            parts.append(value)

    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                item = item.strip()
                if item:
                    parts.append(item)

    return parts


def walk_json(
    node,
    json_path="$"
):
    if isinstance(node, dict):

        parts = []

        for key, value in node.items():

            if key in TEXT_KEYS:
                parts.extend(
                    collect_text(value)
                )

        if parts:
            text = "\n".join(
                dict.fromkeys(parts)
            ).strip()

            if len(text) >= 20:
                yield json_path, text

        for key, value in node.items():

            if isinstance(value, (dict, list)):
                yield from walk_json(
                    value,
                    f"{json_path}.{key}"
                )

    elif isinstance(node, list):

        for index, item in enumerate(node):

            if isinstance(item, (dict, list)):
                yield from walk_json(
                    item,
                    f"{json_path}[{index}]"
                )


def main():

    kri = json.loads(
        KRI_PATH.read_text(
            encoding="utf-8-sig"
        )
    )

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        "PRAGMA journal_mode=WAL"
    )
    conn.execute(
        "PRAGMA synchronous=NORMAL"
    )
    conn.execute(
        "PRAGMA temp_store=MEMORY"
    )

    conn.executescript(
        """
        CREATE TABLE routes (
            route_key TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            lesson_code TEXT NOT NULL,
            title TEXT,
            curriculum_path TEXT
        );

        CREATE TABLE passages (
            id INTEGER PRIMARY KEY,
            route_key TEXT NOT NULL,
            subject TEXT NOT NULL,
            lesson_code TEXT NOT NULL,
            route_title TEXT,
            content_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            json_path TEXT NOT NULL,
            text TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            text_hash TEXT NOT NULL
        );

        CREATE INDEX idx_passages_route
        ON passages(route_key);

        CREATE INDEX idx_passages_lesson
        ON passages(lesson_code);

        CREATE INDEX idx_passages_type
        ON passages(content_type);

        CREATE UNIQUE INDEX idx_passages_unique
        ON passages(
            route_key,
            file_path,
            json_path,
            text_hash
        );

        CREATE VIRTUAL TABLE passages_fts
        USING fts5(
            normalized_text,
            route_key UNINDEXED,
            passage_id UNINDEXED
        );
        """
    )

    passage_count = 0
    file_count = 0

    for route in kri["routes"]:

        route_key = route["route_key"]
        subject = route["subject"]
        lesson_code = route["lesson_code"]
        title = route.get("title")

        paths = route.get("paths") or {}

        conn.execute(
            """
            INSERT INTO routes(
                route_key,
                subject,
                lesson_code,
                title,
                curriculum_path
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                route_key,
                subject,
                lesson_code,
                title,
                paths.get("curriculum"),
            )
        )

        for content_type in (
            "reading",
            "quiz",
        ):

            for relative_path in (
                paths.get(content_type) or []
            ):

                file_path = (
                    EDU_ROOT
                    / relative_path
                )

                if not file_path.exists():
                    print(
                        "DOSYA YOK:",
                        file_path
                    )
                    continue

                try:
                    data = json.loads(
                        file_path.read_text(
                            encoding="utf-8-sig"
                        )
                    )
                except Exception as exc:
                    print(
                        "JSON HATA:",
                        file_path,
                        repr(exc)
                    )
                    continue

                file_count += 1

                for json_path, text in walk_json(
                    data
                ):

                    normalized = normalize_text(
                        text
                    )

                    if len(normalized) < 10:
                        continue

                    text_hash = hashlib.sha1(
                        text.encode("utf-8")
                    ).hexdigest()

                    cur = conn.execute(
                        """
                        INSERT OR IGNORE INTO passages(
                            route_key,
                            subject,
                            lesson_code,
                            route_title,
                            content_type,
                            file_path,
                            json_path,
                            text,
                            normalized_text,
                            text_hash
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            route_key,
                            subject,
                            lesson_code,
                            title,
                            content_type,
                            str(file_path),
                            json_path,
                            text,
                            normalized,
                            text_hash,
                        )
                    )

                    if cur.rowcount == 0:
                        continue

                    passage_id = cur.lastrowid

                    conn.execute(
                        """
                        INSERT INTO passages_fts(
                            normalized_text,
                            route_key,
                            passage_id
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            normalized,
                            route_key,
                            passage_id,
                        )
                    )

                    passage_count += 1

    conn.commit()

    size_mb = (
        DB_PATH.stat().st_size
        / 1024
        / 1024
    )

    print()
    print("DIRECT KNOWLEDGE INDEX HAZIR")
    print("============================")
    print("Route :", len(kri["routes"]))
    print("Dosya :", file_count)
    print("Passage:", passage_count)
    print(
        "DB MB :",
        round(size_mb, 2)
    )
    print(
        "DB    :",
        DB_PATH
    )

    conn.close()


if __name__ == "__main__":
    main()
