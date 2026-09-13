from pathlib import Path
import json
import re
import unicodedata
from collections import Counter

BASE = (
    Path(__file__).resolve().parent.parent
    / "01_KODA_Education_Platform"
    / "kodaai"
    / "data"
    / "output"
    / "license"
)

CURRICULUM = BASE / "curriculum"
READING = BASE / "reading"
QUIZ = BASE / "quiz"

OUT = Path("data/routing/knowledge_routing_index_v02.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

SUBJECT_IDS = {
    "turkce": 1,
    "matematik": 2,
    "tarih": 3,
    "cografya": 4,
    "vatandaslik": 5,
}

STOP = {
    "ve","veya","ile","icin","bu","bir","olarak","olan",
    "da","de","mi","mu","mı","mü","ne","nedir","nasil",
    "hangi","gibi","ders","soru","sorular","konu",
    "aciklar","eder","ayirt","yorumlar","degerlendirir","turkiye","turkiyenin","nin","ozellikleri","ozellik","genel","temel"
}

def normalize_text(text: str) -> str:
    text = str(text).lower()

    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    # Metinsel router için noktalama anlamsız
    text = re.sub(r"[^a-z0-9]+", " ", text)

    return " ".join(text.split())

def normalize_math(text: str) -> str:
    text = str(text).lower()

    # Unicode matematik sembollerini canonical hale getir
    replacements = {
        "": "*",
        "": "*",
        "": "/",
        "": "-",
        "": "-",
        "": "-",
        "＝": "=",
        "": "<=",
        "": ">=",
        "": "!=",
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    # boşlukları kaldır ama matematik operatörlerini koru
    text = re.sub(r"\s+", "", text)

    return text

def all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from all_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from all_strings(value)

def load_json(path: Path):
    try:
        return json.loads(
            path.read_text(encoding="utf-8-sig")
        )
    except Exception:
        return None

def lesson_prefix(lesson_code: str) -> str:
    m = re.match(r"(ders_\d+)", lesson_code)
    return m.group(1) if m else lesson_code

def find_sources(root: Path, subject: str, lesson_code: str):
    subject_dir = root / subject

    if not subject_dir.exists():
        return []

    prefix = lesson_prefix(lesson_code)
    prefix_norm = normalize_text(prefix)

    results = []

    for path in subject_dir.rglob("*.json"):
        stem_norm = normalize_text(path.stem)

        if prefix_norm in stem_norm:
            results.append(path)

    return sorted(set(results))

routes = []

for curriculum_file in sorted(CURRICULUM.rglob("ders_*.json")):
    data = load_json(curriculum_file)

    if not isinstance(data, dict):
        continue

    subject = data.get("subject")
    lesson_no = data.get("lesson_no")
    lesson_code = data.get("lesson_code")
    title = data.get("title")

    if not subject or not lesson_code:
        continue

    if lesson_no is None:
        m = re.match(r"ders_(\d+)", str(lesson_code))
        if m:
            lesson_no = int(m.group(1))
        else:
            continue

    subject_id = SUBJECT_IDS.get(subject)

    if subject_id is None:
        # Bilinmeyen subject'i şimdilik index dışı bırak
        continue

    route_key = f"{subject_id}.{int(lesson_no):02d}"

    reading_files = find_sources(
        READING,
        subject,
        lesson_code
    )

    quiz_files = find_sources(
        QUIZ,
        subject,
        lesson_code
    )

    texts = []
    texts.extend(all_strings(data))

    for source_file in reading_files + quiz_files:
        source_data = load_json(source_file)

        if source_data is not None:
            texts.extend(all_strings(source_data))

    token_counter = Counter()

    for text in texts:
        normalized = normalize_text(text)

        for token in normalized.split():
            if len(token) < 3:
                continue
            if token in STOP:
                continue
            if token.isdigit():
                continue

            token_counter[token] += 1

    keywords = [
        token
        for token, _ in token_counter.most_common(150)
    ]

    aliases = set()

    if title:
        aliases.add(title)
        aliases.add(normalize_text(title))

    aliases.add(lesson_code)
    aliases.add(normalize_text(lesson_code))

    blueprint = data.get("reading_blueprint") or {}

    if isinstance(blueprint, dict):
        segments = blueprint.get("segments", [])
    elif isinstance(blueprint, list):
        segments = blueprint
    else:
        segments = []

    for segment in segments:
        if not isinstance(segment, dict):
            continue

        segment_title = segment.get("title")

        if segment_title:
            aliases.add(segment_title)
            aliases.add(normalize_text(segment_title))

    achievements = []

    for item in data.get("achievements", []):
        text = item.get("text")

        if text:
            achievements.append(text)

    routes.append({
        "route_key": route_key,
        "subject_id": subject_id,
        "lesson_id": int(lesson_no),

        "subject": subject,
        "lesson_code": lesson_code,
        "title": title,

        "aliases": sorted(aliases),
        "aliases_normalized": sorted({
            normalize_text(x)
            for x in aliases
            if x
        }),

        "keywords": keywords,
        "achievements": achievements,

        "paths": {
            "curriculum": str(
                curriculum_file.relative_to(BASE)
            ).replace("\\", "/"),

            "reading": [
                str(p.relative_to(BASE)).replace("\\", "/")
                for p in reading_files
            ],

            "quiz": [
                str(p.relative_to(BASE)).replace("\\", "/")
                for p in quiz_files
            ],
        }
    })

index = {
    "schema": "kodaai.kri.v0.2",
    "education_level": "license",

    "subject_ids": SUBJECT_IDS,

    "normalization": {
        "text": "lowercase + tr ascii fold + punctuation removal",
        "math": "operator preserving canonical form"
    },

    "route_count": len(routes),
    "routes": routes,
}

OUT.write_text(
    json.dumps(
        index,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print("KRI v0.2 OLUSTURULDU")
print("Route sayisi:", len(routes))
print("Dosya:", OUT.resolve())

for row in routes[:15]:
    print(
        row["route_key"],
        "|",
        row["subject"],
        "|",
        row["lesson_code"],
        "| reading:",
        len(row["paths"]["reading"]),
        "| quiz:",
        len(row["paths"]["quiz"])
    )



