from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import time
import threading
import os
import re
import unicodedata
from datetime import datetime
from typing import Dict, Optional
import shutil

from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from llm_core.local_model import LocalLLM, GenerationCancelled
from audit.audit_logger import AuditLogger
from audit.telemetry_logger import TelemetryLogger
from security.prompt_guard import PromptGuard

from rag.document_loader import DocumentLoader
from rag.chunker import TextChunker
from rag.chroma_retriever import ChromaRetriever
from common.text_cleaner import clean_llm_output
from common.accessibility_formatter import to_accessible_speech
from services.routing_language_service import RoutingLanguageService
from services.direct_knowledge_service import DirectKnowledgeService
from services.direct_answer_composer import compose_direct_answer


load_dotenv(override=True)

APP_VERSION = "0.1.0"
DOCS_DIR = Path("data/documents")
CONTENT_GAP_FILE = Path(__file__).resolve().parent / "logs" / "content_gap.jsonl"

EDUCATION_DOCS_DIR = (
    Path(__file__).resolve().parent.parent
    / "01_KODA_Education_Platform"
    / "kodaai"
    / "data"
    / "output"
    / "license"
)
DOCS_DIR.mkdir(exist_ok=True)

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
    ".json",
}


app = FastAPI(
    title="KODA Local AI API",
    version=APP_VERSION,
    description="Local-first experimental RAG-powered Turkish LLM runtime.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

WEB_DIR = Path(__file__).resolve().parent / "web"

app.mount(
    "/static",
    StaticFiles(directory=WEB_DIR),
    name="static",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def local_ai_ui():
    return FileResponse(WEB_DIR / "index.html")

@app.middleware("http")
async def telemetry_exception_middleware(request, call_next):
    started_at = time.perf_counter()

    try:
        return await call_next(request)

    except Exception as exc:
        if request.url.path == "/ask":
            telemetry.log_request(
                request_id=telemetry.new_request_id(),
                route="ERROR",
                duration_ms=(time.perf_counter() - started_at) * 1000,
                source_count=0,
                used_context=False,
                success=False,
                blocked=False,
                subject=None,
                accessibility_layer="NONE",
                error=type(exc).__name__,
            )

        raise



class AskRequest(BaseModel):
    question: str
    user_role: str = "research"
    session_id: str | None = None
    client_request_id: str | None = None


class StopTelemetryRequest(BaseModel):
    request_id: str
    session_id: str | None = None
    stop_after_ms: float | None = None


class SourceItem(BaseModel):
    file_name: str
    content_type: str | None = None
    subject: str | None = None
    chunk_id: int | str
    similarity: float


class AskResponse(BaseModel):
    answer: str
    answer_speech: str | None = None
    used_context: bool
    sources: list[SourceItem] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list)
    blocked: bool = False
    reason: str | None = None


class TutorExplainRequest(BaseModel):
    lesson_code: str
    question_id: str
    user_message: str

    question: str
    options: Dict[str, str]
    correct_answer: str

    passage: Optional[str] = None
    explanation_hint: Optional[str] = None
    user_answer: Optional[str] = None
    user_role: str = "student"


class TutorExplainResponse(BaseModel):
    answer: str
    lesson_code: str
    question_id: str
    used_passage: bool
    blocked: bool = False
    reason: str | None = None


audit = AuditLogger()
telemetry = TelemetryLogger()
guard = PromptGuard()
routing_language = RoutingLanguageService()
direct_knowledge = DirectKnowledgeService()

_active_generations_lock = threading.Lock()
_active_generations = {}


def begin_generation(session_id: str | None):
    if not session_id:
        return threading.Event()

    with _active_generations_lock:
        previous = _active_generations.get(session_id)

        if previous is not None:
            previous.set()

        current = threading.Event()
        _active_generations[session_id] = current

        return current


def cancel_generation(session_id: str | None):
    if not session_id:
        return False

    with _active_generations_lock:
        current = _active_generations.get(session_id)

        if current is None:
            return False

        current.set()
        return True


def finish_generation(
    session_id: str | None,
    cancel_event
):
    if not session_id:
        return

    with _active_generations_lock:
        current = _active_generations.get(session_id)

        if current is cancel_event:
            _active_generations.pop(session_id, None)


loader = DocumentLoader(docs_dir=str(DOCS_DIR))
documents = loader.load_documents()

for education_subdir in ("reading", "quiz", "exam"):
    education_loader = DocumentLoader(
        docs_dir=str(EDUCATION_DOCS_DIR / education_subdir)
    )
    documents += education_loader.load_documents()

chunker = TextChunker(chunk_size=600, overlap=100)
chunks = chunker.chunk_documents(documents)

retriever = ChromaRetriever([])

llm = LocalLLM(
    model_name="gemma3:4b",
    mode="offline"
)


SUBJECT_KEYWORDS = {
    "cografya": (
        "coğrafya",
        "doğu anadolu",
        "batı anadolu",
        "iç anadolu",
        "marmara",
        "ege bölgesi",
        "akdeniz bölgesi",
        "karadeniz bölgesi",
        "güneydoğu anadolu",
        "iklim",
        "masif",
        "jeoloji",
        "jeolojik",
        "jeomorfoloji",
        "jeomorfolojik",
        "kayaç",
        "tektonik",
        "yeryüzü şekilleri",
        "nüfus",
        "yerleşme",
        "göç",
    ),
    "tarih": (
        "tarih",
        "osmanlı",
        "selçuklu",
        "atatürk",
        "kurtuluş savaşı",
        "milli mücadele",
        "inkılap",
        "birinci dünya savaşı",
        "ikinci dünya savaşı",
        "ii. dünya savaşı",
        "i. dünya savaşı",
        "i dünya savaşı",
        "ii dünya savaşı",
    ),
    "matematik": (
        "matematik",
        "denklem",
        "kesir",
        "yüzde",
        "oran",
        "orantı",
        "üslü",
        "köklü",
        "geometri",
        "fonksiyon",
        "eşitsizlik",
        "olasılık",
        "ifade",
        "işlem",
        "denklem",
        "eşitlik",
        "eşitsizlik",
    ),
    "turkce": (
        "türkçe",
        "paragraf",
        "sözcük",
        "cümle",
        "fiilimsi",
        "anlatım bozukluğu",
        "noktalama",
        "yazım",
    ),
    "vatandaslik": (
        "vatandaşlık",
        "anayasa",
        "tbmm",
        "hukuk",
        "yargı",
        "yasama",
        "yürütme",
        "seçim",
        "siyasi parti",
    ),
}



def log_content_gap(
    *,
    question: str,
    subject: str | None,
    topic_guess: str | None,
    retrieval_score: float,
    matched_sources: int,
    request_id: str | None = None,
    session_id: str | None = None,
) -> bool:
    """
    Append one curriculum content-gap event to logs/content_gap.jsonl.

    This logger is deliberately fail-safe: telemetry/logging must never
    break the user's /ask request path.
    """
    if not subject or subject not in SUBJECT_KEYWORDS:
        return False

    record = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "event": "CONTENT_GAP",
        "question": question,
        "subject": subject,
        "topic_guess": topic_guess or "",
        "curriculum_scope": True,
        "retrieval_score": round(float(retrieval_score), 3),
        "matched_sources": int(matched_sources),
        "status": "PENDING_REVIEW",
        "request_id": request_id,
        "session_id": session_id,
    }

    try:
        CONTENT_GAP_FILE.parent.mkdir(parents=True, exist_ok=True)

        with CONTENT_GAP_FILE.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

        return True

    except Exception:
        # Content-gap logging is observational only.
        # Never interrupt the answer pipeline because the log could not be written.
        return False

def detect_subject(question: str) -> str | None:
    # Turkish-aware, ASCII-stable normalization.
    # PowerShell/clipboard encoding differences must not affect routing.
    normalized = question.casefold().replace(chr(775), "")

    normalized = normalized.translate(
        str.maketrans({
            ord(chr(231)): "c",   # c-cedilla
            ord(chr(287)): "g",   # g-breve
            ord(chr(305)): "i",   # dotless i
            ord(chr(246)): "o",   # o-diaeresis
            ord(chr(351)): "s",   # s-cedilla
            ord(chr(252)): "u",   # u-diaeresis
        })
    )

    # 1. Explicit mathematical symbols
    math_symbols = (
        "=", "+", "-", "*", "<", ">", "%",
        chr(215),
        chr(247),
        chr(8804),
        chr(8805),
        chr(8730),
        chr(178),
        chr(179),
    )

    if any(symbol in question for symbol in math_symbols):
        return "matematik"

    if re.search(r"\b\d+\s*/\s*\d+\b", question):
        return "matematik"

    # 2. High-confidence curriculum expressions.
    # Patterns are deliberately ASCII after normalization.
    strong_patterns = {
        "turkce": (
            "gercek anlam",
            "mecaz anlam",
            "es anlam",
            "zit anlam",
            "yakin anlam",
            "terim anlam",
            "paragraf",
            "sozcuk",
            "kelime",
            "baglam",
            "ana dusunce",
            "ana fikir",
            "yardimci dusunce",
            "cikarim",
        ),
        "matematik": (
            "rasyonel sayi",
            "rasyonel",
            "dogal sayi",
            "tam sayi",
            "sayi kumeleri",
            "rakam",
            "basamak",
            "bolu",
        ),
        "tarih": (
            "orhun",
            "gokturk",
            "islamiyet oncesi turk",
            "islamiyet oncesindeki devlet",
            "ilk turk devlet",
            "eski turk",
            "kurultay",
            "kut anlayisi",
            "hukumdar",
        ),
        "cografya": (
            "iklim",
            "cografya",
            "yer sekilleri",
            "yeryuzu sekilleri",
            "denizlerin iklime",
            "karasal iklim",
        ),
    }

    scores = {}

    for subject, patterns in strong_patterns.items():
        score = sum(
            3 for pattern in patterns
            if pattern in normalized
        )
        if score:
            scores[subject] = scores.get(subject, 0) + score

    # Generic number concepts, but not every occurrence of "sayi".
    if re.search(
        r"\b("
        r"sayi\s+nedir"
        r"|sayi\s+ile"
        r"|bir\s+sayi\b"
        r"|sayilar\b"
        r"|sayilarin\b"
        r"|sayinin\b"
        r")",
        normalized,
    ):
        scores["matematik"] = scores.get("matematik", 0) + 3

    # 3. Existing SUBJECT_KEYWORDS remain useful as secondary evidence.
    for subject, keywords in SUBJECT_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            k = keyword.casefold().replace(chr(775), "")
            k = k.translate(
                str.maketrans({
                    ord(chr(231)): "c",
                    ord(chr(287)): "g",
                    ord(chr(305)): "i",
                    ord(chr(246)): "o",
                    ord(chr(351)): "s",
                    ord(chr(252)): "u",
                })
            )

            # Too generic for mathematics.
            if subject == "matematik" and k == "ifade":
                continue

            if k in normalized:
                score += 1

        if score:
            scores[subject] = scores.get(subject, 0) + score

    if not scores:
        return None

    ranked = sorted(
        scores.items(),
        key=lambda item: (-item[1], item[0])
    )

    best_subject, best_score = ranked[0]

    if len(ranked) > 1 and ranked[1][1] == best_score:
        return None

    return best_subject


def _normalize_answerability_text(text: str) -> list[str]:
    text = text.casefold()

    turkish_map = str.maketrans({
        "\u0131": "i",
        "\u011f": "g",
        "\u00fc": "u",
        "\u015f": "s",
        "\u00f6": "o",
        "\u00e7": "c",
    })
    text = text.translate(turkish_map)

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )

    return re.findall(r"[a-z0-9]+", text)


def is_context_answerable(question: str, context: str) -> tuple[bool, float]:
    if not context.strip():
        return False, 0.0

    stop_words = {
        "ve", "veya", "ile", "bir", "bu", "su",
        "nedir", "nelerdir", "neler", "hangileri", "hangileridir", "say", "acikla", "anlat",
        "hakkinda", "icin", "olan", "olarak",
        "mi", "midir", "dir",
        "nin", "nın", "nun", "nün",
        "ni", "nı", "nu", "nü", "deki", "daki", "teki", "taki",
    }

    question_words = [
        word
        for word in _normalize_answerability_text(question)
        if len(word) > 2 and word not in stop_words
    ]

    if not question_words:
        return True, 1.0

    context_words = set(_normalize_answerability_text(context))

    def supported(word: str) -> bool:
        if word in context_words:
            return True

        if len(word) >= 5:
            prefix = word[:5]
            return any(
                len(candidate) >= 5 and candidate.startswith(prefix)
                for candidate in context_words
            )

        return False

    matched = sum(1 for word in question_words if supported(word))
    coverage = matched / len(question_words)

    return coverage >= 0.50, round(coverage, 3)


def has_required_answer_evidence(question: str, context: str) -> tuple[bool, str]:
    """
    Soru yalnızca konu benzerliği değil, belirli bir bilgi türü istiyorsa
    bağlamın o bilgi türünü gerçekten içerip içermediğini kontrol eder.
    """

    q_words = _normalize_answerability_text(question)
    c_words = _normalize_answerability_text(context)

    q_text = " ".join(q_words)
    c_text = " ".join(c_words)

    # ORHUN TARGETED EVIDENCE GUARD
    if "orhun" in q_text:

        if "dili" in q_text:
            language_markers = (
                "gokturkce",
                "kokturkce",
                "eski turkce",
                "orhun turkcesi",
            )

            if not any(
                marker in c_text
                for marker in language_markers
            ):
                return (
                    False,
                    "orhun_language_missing_explicit_evidence",
                )

        if "yansit" in q_text:
            reflection_markers = (
                "yansitir",
                "yansitmistir",
                "yansitan",
                "yansitmakta",
            )

            if not any(
                marker in c_text
                for marker in reflection_markers
            ):
                return (
                    False,
                    "orhun_reflection_missing_explicit_evidence",
                )

    # Görev / yetki / işlev soruları
    duty_intent = any(
        token in q_text
        for token in (
            "gorev",
            "gorevleri",
            "yetki",
            "yetkileri",
            "islev",
            "islevi",
            "ne ise yarar",
        )
    )

    if duty_intent:
        duty_evidence_patterns = (
            r"\bgorevi\b",
            r"\bgorevleri\b",
            r"\bgorevidir\b",
            r"\bgorevleridir\b",
            r"\byetkisi\b",
            r"\byetkileri\b",
            r"\bsorumludur\b",
            r"\byukumludur\b",
            r"\binceler\b",
            r"\barastirir\b",
            r"\bdenetler\b",
            r"\bdegerlendirir\b",
            r"\bsonuclandirir\b",
            r"\btavsiyede\s+bulunur\b",
            r"\bkarar\s+verir\b",
            r"\byerine\s+getirir\b",
            r"\bbasvuru(?:yu|lari|lar)?\s+(?:inceler|degerlendirir|sonuclandirir)\b",
        )

        if not any(
            re.search(pattern, c_text)
            for pattern in duty_evidence_patterns
        ):
            return False, "DUTY_EVIDENCE_MISSING"

        # --------------------------------------------------
        # DUTY SUBJECT LINK GUARD
        #
        # "X'in gorevleri nelerdir?" sorusunda baglam,
        # gorev/yetki bilgisini ayni ana ozneye baglamali.
        #
        # Ornek:
        #   "Belediye encumeninin gorevleri..." ifadesi
        #   "Belediyenin gorevleri..." sorusuna tek basina
        #   yeterli evidence sayilmaz.
        # --------------------------------------------------
        duty_stop_words = {
            "gorev",
            "gorevleri",
            "yetki",
            "yetkileri",
            "islev",
            "islevi",
            "nelerdir",
            "nedir",
            "ne",
            "ise",
            "yarar",
        }

        subject_tokens = [
            token
            for token in q_words
            if (
                len(token) > 2
                and token not in duty_stop_words
            )
        ]

        if subject_tokens:
            subject_linked = False

            raw_sentences = re.split(
                r"(?<=[.!?])\s+|\n+",
                context,
            )

            for raw_sentence in raw_sentences:
                sentence_words = (
                    _normalize_answerability_text(
                        raw_sentence
                    )
                )

                if not sentence_words:
                    continue

                sentence_text = " ".join(
                    sentence_words
                )

                has_duty_marker = any(
                    re.search(
                        pattern,
                        sentence_text,
                    )
                    for pattern in duty_evidence_patterns
                )

                if not has_duty_marker:
                    continue

                subject_hit = any(
                    (
                        token in sentence_words
                        or (
                            len(token) >= 5
                            and any(
                                word.startswith(token[:5])
                                for word in sentence_words
                            )
                        )
                    )
                    for token in subject_tokens
                )

                if not subject_hit:
                    continue

                if any(
                    marker in sentence_text
                    for marker in (
                        "belediye encumeni",
                        "belediye meclisi",
                        "belediye baskani",
                    )
                ):
                    continue

                # Bir kurumun organini tanimlayan cumle,
                # kurumun kendi gorevlerini aciklayan evidence
                # olarak kullanilamaz.
                #
                # Ornek:
                #   "Belediyenin danisma ve yurutme gorevleri
                #    bulunan organidir."
                #
                # Bu, belediyenin gorevlerini degil bir belediye
                # organinin niteligini anlatir.
                if (
                    "organidir" in sentence_text
                    or "organdir" in sentence_text
                ):
                    continue

                subject_linked = True
                break

            if not subject_linked:
                return False, "DUTY_SUBJECT_EVIDENCE_MISSING"

    # --------------------------------------------------
    # DEFINITION EVIDENCE GATE
    # --------------------------------------------------
    strong_definition_intent = (
        "ne demektir" in q_text
        or "ne anlama gelir" in q_text
        or "anlami nedir" in q_text
    )

    semantic_nedir_intent = (
        q_text.endswith(" nedir")
        and any(
            token in q_words
            for token in (
                "anlam",
                "anlamli",
                "sozcuk",
                "dusunce",
                "kavram",
                "terim",
            )
        )
    )

    definition_intent = (
        strong_definition_intent
        or semantic_nedir_intent
    )

    if definition_intent:
        definition_stop_words = {
            "ne",
            "nedir",
            "demektir",
            "anlama",
            "gelir",
            "anlami",
            "paragrafta",
            "paragraf",
            "bir",
            "bu",
        }

        concept_tokens = [
            token
            for token in q_words
            if (
                len(token) > 2
                and token
                not in definition_stop_words
            )
        ]

        raw_sentences = re.split(
            r"(?<=[.!?])\s+|\n+",
            context,
        )

        definition_patterns = (
            r"\bdenir\b",
            r"\bifade\s+eder\b",
            r"\banlamina\s+gelir\b",
            r"\banlamindadir\b",
            r"\bolarak\s+tanimlanir\b",
            r"\btanimlanir\b",
            r"\bkabul\s+edilir\b",
        )

        definition_found = False

        for raw_sentence in raw_sentences:
            sentence_words = (
                _normalize_answerability_text(
                    raw_sentence
                )
            )

            if not sentence_words:
                continue

            sentence_text = " ".join(
                sentence_words
            )

            def token_supported(token: str) -> bool:
                if token in sentence_words:
                    return True

                if len(token) >= 5:
                    prefix = token[:5]

                    return any(
                        len(candidate) >= 5
                        and candidate.startswith(prefix)
                        for candidate in sentence_words
                    )

                return False

            concept_hits = sum(
                1
                for token in concept_tokens
                if token_supported(token)
            )

            if not concept_tokens:
                continue

            required_hits = (
                len(concept_tokens)
                if len(concept_tokens) <= 3
                else max(
                    2,
                    int(
                        len(concept_tokens)
                        * 0.75
                    ),
                )
            )

            if concept_hits < required_hits:
                continue

            if any(
                re.search(
                    pattern,
                    sentence_text,
                )
                for pattern
                in definition_patterns
            ):
                definition_found = True
                break

        if not definition_found:
            return (
                False,
                "DEFINITION_EVIDENCE_MISSING",
            )

    # Zaman soruları
    time_intent = any(
        token in q_text
        for token in (
            "ne zaman",
            "hangi yil",
            "hangi tarihte",
            "kac yil",
        )
    )

    if time_intent:
        if not re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", c_text):
            return False, "TIME_EVIDENCE_MISSING"

    # Neden / sebep soruları
    reason_intent = any(
        token in q_text
        for token in (
            "neden",
            "nicin",
            "sebebi",
            "sebep",
        )
    )

    if reason_intent:
        reason_markers = (
            "cunku",
            "nedeni",
            "sebebi",
            "sonuc",
            "dolayi",
            "amac",
        )

        if not any(marker in c_text for marker in reason_markers):
            return False, "REASON_EVIDENCE_MISSING"

    return True, "OK"


def rebuild_retriever(reset_collection: bool = True):
    global documents, chunks, retriever

    loader = DocumentLoader(docs_dir=str(DOCS_DIR))
    documents = loader.load_documents()

    for education_subdir in ("reading", "quiz", "exam"):
        education_loader = DocumentLoader(
            docs_dir=str(EDUCATION_DOCS_DIR / education_subdir)
        )
        documents += education_loader.load_documents()

    chunker = TextChunker(chunk_size=600, overlap=100)
    chunks = chunker.chunk_documents(documents)

    retriever = ChromaRetriever(
        chunks,
        reset_collection=reset_collection
    )

    return {
        "documents": len(documents),
        "chunks": len(chunks)
    }


def build_tutor_prompt(req: TutorExplainRequest) -> str:
    options_text = "\n".join(
        f"{key}) {value}" for key, value in req.options.items()
    )

    passage_text = req.passage or "Bu soru için ders anlatımı metni verilmedi."
    hint_text = req.explanation_hint or "Ek açıklama ipucu verilmedi."
    user_answer_text = req.user_answer or "Öğrenci cevabı belirtilmedi."

    return f"""
Sen KODA AI Tutor'sun.

Görevin:
- Öğrenciye Türkçe, sade, sabırlı ve öğretici cevap vermek.
- Cevabı doğrudan ezberletmek yerine mantığını anlatmak.
- Görme engelli kullanıcıya uygun şekilde konuşur gibi açıklamak.
- Gereksiz uzun konuşmamak.
- Matematikte adımları net söylemek.
- Eğer öğrenci "neden" diye soruyorsa sebebi anlat.
- Eğer öğrenci yanlış cevap verdiyse, doğru cevabı ve nedenini açıkla.
- Eğer öğrenci anlamadığını söylüyorsa daha basit örnek ver.
- Soru, şıklar ve doğru cevap dışına gereksiz bilgi ekleme.
- Ders anlatımı varsa öncelikle ona dayan.
- Bilmediğin şeyi uydurma.

Ders kodu:
{req.lesson_code}

Soru ID:
{req.question_id}

Soru:
{req.question}

Şıklar:
{options_text}

Doğru cevap:
{req.correct_answer}

Öğrencinin cevabı:
{user_answer_text}

Öğrencinin mesajı:
{req.user_message}

Ders anlatımı / passage:
{passage_text}

Mevcut açıklama ipucu:
{hint_text}

Cevap formatı:
- Önce kısa cevap ver.
- Sonra mantığını 2-4 cümleyle açıkla.
- Gerekirse küçük bir örnek ver.
- Sonunda öğrenciyi devam etmeye teşvik et.
""".strip()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "system": "KODAAI Local AI",
        "version": APP_VERSION,
        "documents": len(documents),
        "chunks": len(chunks),
        "mode": "offline"
    }


@app.get("/sources")
def sources():
    return {
        "documents": [
            {
                "source": doc.get("source"),
                "file_name": doc.get("file_name"),
                "file_type": doc.get("file_type"),
                "text_length": len(doc.get("text", ""))
            }
            for doc in documents
        ],
        "document_count": len(documents),
        "chunk_count": len(chunks)
    }


@app.post("/telemetry/stop")
def telemetry_stop(request: StopTelemetryRequest):
    cancel_generation(request.session_id)

    telemetry.log_stop(
        request_id=request.request_id,
        stop_after_ms=request.stop_after_ms,
        session_id=request.session_id,
    )

    return {"status": "logged"}


@app.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    x_kodaai_api_key: str | None = Header(
        default=None,
        alias="X-KODAAI-API-Key",
    ),
):
    expected_key = os.getenv("KODAAI_API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured.",
        )

    if x_kodaai_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized.",
        )
    request_id = request.client_request_id or telemetry.new_request_id()
    started_at = time.perf_counter()

    question = request.question.strip()

    if not question:
        telemetry.log_request(
            request_id=request_id,
            question=question,
            route="INVALID_REQUEST",
            duration_ms=(time.perf_counter() - started_at) * 1000,
            source_count=0,
            used_context=False,
            success=False,
            blocked=False,
            session_id=request.session_id,
            subject=None,
            accessibility_layer="NONE",
            error="empty_question",
        )

        return AskResponse(
            answer="Soru boş olamaz.",
            used_context=False,
            sources=[]
        )

    process_steps = [
        "Soru alındı",
        "Güvenlik kontrolü yapılıyor"
    ]

    safety_result = guard.check(question)

    if not safety_result["allowed"]:
        audit.log_blocked_query(
            question=question,
            reason=safety_result["reason"]
        )

        telemetry.log_request(
            request_id=request_id,
            question=question,
            route="BLOCKED",
            duration_ms=(time.perf_counter() - started_at) * 1000,
            source_count=0,
            used_context=False,
            success=True,
            blocked=True,
            session_id=request.session_id,
        )

        return AskResponse(
            answer="Sorgu güvenlik politikası nedeniyle engellendi.",
            used_context=False,
            sources=[],
            blocked=True,
            reason=safety_result["reason"]
        )

    process_steps.append("KODAAI bilgi kaynakları taranıyor")

    # KODAAI Math Engine
    # Explicit arithmetic expressions are solved deterministically
    # before RAG/LLM retrieval. Non-math questions continue normally.
    from math_engine.service import MathService

    math_result = MathService().handle(question)

    if math_result.handled:
        process_steps.append(
            "Matematiksel ifade KODAAI Math Engine tarafından çözüldü"
        )

        if math_result.steps:
            process_steps.extend(
                math_result.steps
            )

        if math_result.verified is True:
            process_steps.append(
                "Çözüm matematiksel olarak doğrulandı"
            )

        math_answer = math_result.answer or ""

        process_steps.append(
            "Reading / MathSpeak erişilebilirlik katmanı uygulanıyor"
        )

        math_answer_speech = to_accessible_speech(
            math_answer
        )

        process_steps.append(
            "Yanıt hazır"
        )

        telemetry.log_request(
            request_id=request_id,
            question=question,
            route="MATH",
            duration_ms=(time.perf_counter() - started_at) * 1000,
            source_count=0,
            used_context=False,
            success=True,
            blocked=False,
            session_id=request.session_id,
            subject="matematik",
            accessibility_layer="READING_MATHSPEAK",
        )

        audit.log_interaction(
            question=question,
            response=math_answer,
            user_role=request.user_role
        )

        return AskResponse(
            answer=math_answer,
            answer_speech=math_answer_speech,
            used_context=False,
            sources=[],
            process_steps=process_steps
        )

    # ------------------------------------------------------
    # KODAAI Direct Knowledge Layer
    # Deterministic indexed knowledge lookup before RAG/LLM.
    # ------------------------------------------------------

    direct_result = direct_knowledge.search(
        question,
        limit=3,
    )

    direct_answerable = bool(
        direct_result.get("answerable")
    )

    direct_confidence = float(
        direct_result.get(
            "direct_confidence"
        ) or 0.0
    )

    direct_passage = direct_result.get(
        "best_passage"
    )

    if (
        direct_answerable
        and direct_confidence >= 0.90
        and direct_passage
    ):
        direct_passage_text = str(
            direct_passage.get("text") or ""
        ).strip()

        direct_answer = compose_direct_answer(
            question=question,
            passage=direct_passage_text,
            intent=str(
                direct_result.get("intent") or "fact"
            ),
        )

        if direct_answer:
            process_steps.append(
                "Direct Knowledge e\u015fle\u015fmesi: "
                + str(
                    direct_result.get(
                        "route_key"
                    )
                )
            )

            process_steps.append(
                "Direct Knowledge g\u00fcven skoru: "
                + f"{direct_confidence:.3f}"
            )

            process_steps.append(
                "Yerel indeks \u00fczerinden do\u011frudan yan\u0131tland\u0131"
            )

            process_steps.append(
                "Reading / MathSpeak eri\u015filebilirlik katman\u0131 uygulan\u0131yor"
            )

            direct_answer_speech = (
                to_accessible_speech(
                    direct_answer
                )
            )

            process_steps.append(
                "Yan\u0131t haz\u0131r"
            )

            direct_file = str(
                direct_passage.get(
                    "file_path"
                ) or ""
            )

            direct_sources = [
                {
                    "file_name": (
                        Path(direct_file).name
                        if direct_file
                        else ""
                    ),
                    "content_type": direct_passage.get(
                        "content_type"
                    ),
                    "subject": direct_passage.get(
                        "subject"
                    ),
                    "chunk_id": "direct",
                    "similarity": direct_confidence,
                }
            ]

            telemetry.log_request(
                request_id=request_id,
            question=question,
                route="DIRECT_KNOWLEDGE",
                duration_ms=(
                    time.perf_counter()
                    - started_at
                ) * 1000,
                source_count=1,
                used_context=True,
                success=True,
                blocked=False,
                session_id=request.session_id,
                subject=direct_result.get(
                    "subject"
                ),
                accessibility_layer="READING_MATHSPEAK",
            )

            audit.log_interaction(
                question=question,
                response=direct_answer,
                user_role=request.user_role
            )

            return AskResponse(
                answer=direct_answer,
                answer_speech=direct_answer_speech,
                used_context=True,
                sources=direct_sources,
                process_steps=process_steps,
            )

    subject = detect_subject(question)

    # KODAAI Language Layer
    # morphology -> canonical -> KRI route hint
    route_analysis = routing_language.analyse(question)

    route_items = route_analysis.get("routes", [])

    preferred_files = set()
    routing_subject = subject

    if len(route_items) == 1:
        route_item = route_items[0]

        route_subject = route_item.get("subject")

        if route_subject:
            routing_subject = route_subject

        route_paths = route_item.get("paths") or {}

        for group in ("reading", "quiz"):
            for route_path in route_paths.get(group, []) or []:
                preferred_files.add(
                    Path(route_path).name
                )

        process_steps.append(
            "KRI yönlendirmesi: "
            + str(route_item.get("route_key"))
            + "  "
            + str(route_item.get("title"))
        )

    retrieval_result = retriever.retrieve_with_sources(
        question,
        subject=routing_subject,
        preferred_files=preferred_files,
    )

    subject = routing_subject

    context = retrieval_result["context"]
    source_items = retrieval_result["sources"]

    public_sources = []

    for item in source_items:
        source_path = item.get("source", "")

        public_sources.append(
            {
                "file_name": Path(source_path).name if source_path else "",
                "content_type": item.get("content_type"),
                "subject": item.get("subject"),
                "chunk_id": item.get("chunk_id"),
                "similarity": item.get("similarity"),
            }
        )

    process_steps.append(
        f"{len(source_items)} kaynak bulundu"
        if source_items
        else "?lgili kaynak bulunamad?"
    )

    answerability_queries = [question]

    lemma_query = str(
        route_analysis.get("lemma_text") or ""
    ).strip()

    if (
        lemma_query
        and lemma_query.casefold() != question.casefold()
    ):
        answerability_queries.append(lemma_query)

    canonical_terms = [
        str(item).replace("_", " ").strip()
        for item in (route_analysis.get("canonical") or [])
        if str(item).strip()
    ]

    # KRI tek ve kesin bir route verdi?inde canonical kavramlar
    # answerability i?in g?venli ek sinyal olarak kullan?labilir.
    if len(route_items) == 1 and canonical_terms:
        answerability_queries.append(
            " ".join(canonical_terms)
        )

        route_title = str(
            route_items[0].get("title") or ""
        ).strip()

        if route_title:
            answerability_queries.append(
                route_title
            )

    chunk_scores = []
    primary_scores = []
    auxiliary_scores = []

    if context:
        for chunk in context.split("\n\n---\n\n"):
            _, primary_coverage = is_context_answerable(
                question,
                chunk,
            )

            evidence_ok, evidence_reason = has_required_answer_evidence(
                question,
                chunk,
            )

            effective_primary_coverage = (
                primary_coverage
                if evidence_ok
                else 0.0
            )

            aux_coverages = []

            for answerability_query in answerability_queries:
                if (
                    answerability_query.strip().casefold()
                    == question.strip().casefold()
                ):
                    continue

                _, aux_coverage = is_context_answerable(
                    answerability_query,
                    chunk,
                )
                aux_coverages.append(aux_coverage)

            best_aux = (
                max(aux_coverages)
                if aux_coverages
                else 0.0
            )

            primary_scores.append(effective_primary_coverage)
            auxiliary_scores.append(best_aux)

            combined_score = (
                effective_primary_coverage * 0.85
                + best_aux * 0.15
            )

            chunk_scores.append(combined_score)

    best_primary_coverage = (
        max(primary_scores)
        if primary_scores
        else 0.0
    )

    best_auxiliary_coverage = (
        max(auxiliary_scores)
        if auxiliary_scores
        else 0.0
    )

    best_coverage = (
        max(chunk_scores)
        if chunk_scores
        else 0.0
    )

    process_steps.append(
        f"Kaynak yeterlilik skoru: {best_coverage:.3f}"
    )
    process_steps.append(
        f"Ana soru kapsama skoru: {best_primary_coverage:.3f}"
    )
    process_steps.append(
        f"Yardimci sorgu kapsama skoru: {best_auxiliary_coverage:.3f}"
    )

    if best_primary_coverage < 0.60 or best_coverage < 0.60:
        telemetry_route = "RAG_NO_ANSWER"
        process_steps.append(
            "Kaynak yeterliliği yetersiz"
        )

        topic_guess = ""

        if len(route_items) == 1:
            topic_guess = str(
                route_items[0].get("title") or ""
            ).strip()

        if not topic_guess and canonical_terms:
            topic_guess = ", ".join(canonical_terms[:3])

        gap_logged = log_content_gap(
            question=question,
            subject=subject,
            topic_guess=topic_guess,
            retrieval_score=best_coverage,
            matched_sources=len(source_items),
            request_id=request_id,
            session_id=request.session_id,
        )

        if gap_logged:
            process_steps.append(
                "Müfredat içi içerik açığı inceleme kuyruğuna kaydedildi"
            )

        answer = (
            "Mevcut bilgi kaynaklarımda bu soruyu "
            "yeterli doğrulukta yanıtlayacak bilgi bulunamadı."
        )
    else:
        telemetry_route = "LLM"
        process_steps.append(
            "Yerel yapay zekâ yanıtı oluşturuyor"
        )

        cancel_event = begin_generation(
            request.session_id
        )

        try:
            raw_answer = llm.generate(
                question=question,
                context=context,
                cancel_event=cancel_event
            )

        except GenerationCancelled:
            telemetry.log_request(
                request_id=request_id,
            question=question,
                route="CANCELLED",
                duration_ms=(
                    time.perf_counter() - started_at
                ) * 1000,
                source_count=len(source_items),
                used_context=bool(context),
                success=True,
                blocked=False,
                session_id=request.session_id,
                subject=subject,
                accessibility_layer="NONE",
            )

            return AskResponse(
                answer="Yan?t durduruldu.",
                answer_speech=None,
                used_context=False,
                sources=[],
                process_steps=[
                    "Yan?t kullan?c? taraf?ndan durduruldu"
                ],
                blocked=False,
                reason=None
            )

        finally:
            finish_generation(
                request.session_id,
                cancel_event
            )

        answer = clean_llm_output(
            raw_answer,
            question=question
        )

    process_steps.append(
        "Reading / MathSpeak erişilebilirlik katmanı uygulanıyor"
    )

    answer_speech = to_accessible_speech(answer)

    process_steps.append("Yanıt hazır")

    telemetry.log_request(
        request_id=request_id,
            question=question,
        route=telemetry_route,
        duration_ms=(time.perf_counter() - started_at) * 1000,
        source_count=len(source_items),
        used_context=bool(context),
        success=True,
        blocked=False,
        session_id=request.session_id,
        subject=subject,
        accessibility_layer="READING_MATHSPEAK",
    )

    audit.log_interaction(
        question=question,
        response=answer,
        user_role=request.user_role
    )

    return AskResponse(
        answer=answer,
        answer_speech=answer_speech,
        used_context=bool(context),
        sources=public_sources,
        process_steps=process_steps,
        blocked=False,
        reason=None
    )


@app.post("/api/chat", response_model=AskResponse, include_in_schema=False)
def public_chat(request: AskRequest):
    internal_key = os.getenv("KODAAI_API_KEY")

    if not internal_key:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured.",
        )

    return ask(
        request,
        x_kodaai_api_key=internal_key,
    )


@app.post("/tutor/explain", response_model=TutorExplainResponse)
def tutor_explain(req: TutorExplainRequest):
    safety_result = guard.check(req.user_message)

    if not safety_result["allowed"]:
        audit.log_blocked_query(
            question=req.user_message,
            reason=safety_result["reason"]
        )

        return TutorExplainResponse(
            answer="Bu istek güvenlik politikası nedeniyle yanıtlanamaz.",
            lesson_code=req.lesson_code,
            question_id=req.question_id,
            used_passage=bool(req.passage),
            blocked=True,
            reason=safety_result["reason"]
        )

    prompt = build_tutor_prompt(req)

    raw_answer = llm.generate(
        question=prompt,
        context=""
    )

    answer = clean_llm_output(raw_answer)

    audit.log_interaction(
        question=f"[TUTOR] {req.lesson_code}/{req.question_id}: {req.user_message}",
        response=answer,
        user_role=req.user_role
    )

    return TutorExplainResponse(
        answer=answer,
        lesson_code=req.lesson_code,
        question_id=req.question_id,
        used_passage=bool(req.passage),
        blocked=False,
        reason=None
    )


@app.post("/reindex")
def reindex():
    stats = rebuild_retriever(reset_collection=True)

    return {
        "status": "reindexed",
        "documents": stats["documents"],
        "chunks": stats["chunks"]
    }


@app.get("/audit/interactions")
def audit_interactions(limit: int = 50):
    items = audit.read_interactions(limit=limit)

    return {
        "count": len(items),
        "items": items
    }


@app.get("/audit/blocked")
def audit_blocked(limit: int = 50):
    items = audit.read_blocked_queries(limit=limit)

    return {
        "count": len(items),
        "items": items
    }


@app.get("/documents")
def list_documents():
    files = []

    for file_path in DOCS_DIR.glob("*"):
        if file_path.is_file():
            files.append({
                "file_name": file_path.name,
                "extension": file_path.suffix.lower(),
                "size_bytes": file_path.stat().st_size
            })

    return {
        "count": len(files),
        "documents": files
    }


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        return {
            "status": "error",
            "message": "Dosya adı boş olamaz."
        }

    file_name = Path(file.filename).name
    extension = Path(file_name).suffix.lower()

    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        return {
            "status": "error",
            "message": f"Desteklenmeyen dosya tipi: {extension}",
            "allowed_extensions": sorted(ALLOWED_DOCUMENT_EXTENSIONS)
        }

    target_path = DOCS_DIR / file_name

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "uploaded",
        "file_name": file_name,
        "path": str(target_path),
        "message": "Dosya yüklendi. Bilgi havuzuna almak için /reindex çalıştır."
    }


@app.delete("/documents/{file_name}")
def delete_document(file_name: str):
    safe_name = Path(file_name).name
    target_path = DOCS_DIR / safe_name

    if not target_path.exists():
        return {
            "status": "error",
            "message": "Dosya bulunamadı.",
            "file_name": safe_name
        }

    if not target_path.is_file():
        return {
            "status": "error",
            "message": "Hedef bir dosya değil.",
            "file_name": safe_name
        }

    target_path.unlink()

    return {
        "status": "deleted",
        "file_name": safe_name,
        "message": "Dosya silindi. ChromaDB güncellemesi için /reindex çalıştır."
    }







































