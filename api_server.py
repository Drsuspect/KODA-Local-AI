from pathlib import Path
from typing import Dict, Optional
import shutil

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel, Field

from llm_core.local_model import LocalLLM
from audit.audit_logger import AuditLogger
from security.prompt_guard import PromptGuard

from rag.document_loader import DocumentLoader
from rag.chunker import TextChunker
from rag.chroma_retriever import ChromaRetriever
from common.text_cleaner import clean_llm_output


APP_VERSION = "0.1.0"
DOCS_DIR = Path("data/documents")
DOCS_DIR.mkdir(exist_ok=True)

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".docx",
}


app = FastAPI(
    title="KODA Local AI API",
    version=APP_VERSION,
    description="Local-first experimental RAG-powered Turkish LLM runtime."
)


class AskRequest(BaseModel):
    question: str
    user_role: str = "research"


class SourceItem(BaseModel):
    source: str
    chunk_id: int | str
    similarity: float


class AskResponse(BaseModel):
    answer: str
    used_context: bool
    context: str | None = None
    sources: list[SourceItem] = Field(default_factory=list)
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
guard = PromptGuard()

loader = DocumentLoader(docs_dir=str(DOCS_DIR))
documents = loader.load_documents()

chunker = TextChunker(chunk_size=600, overlap=100)
chunks = chunker.chunk_documents(documents)

retriever = ChromaRetriever(chunks)

llm = LocalLLM(
    model_name="gemma3:4b",
    mode="offline"
)


def rebuild_retriever(reset_collection: bool = True):
    global documents, chunks, retriever

    loader = DocumentLoader(docs_dir=str(DOCS_DIR))
    documents = loader.load_documents()

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
        "system": "KODA Local AI",
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


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    question = request.question.strip()

    if not question:
        return AskResponse(
            answer="Soru boş olamaz.",
            used_context=False,
            sources=[]
        )

    safety_result = guard.check(question)

    if not safety_result["allowed"]:
        audit.log_blocked_query(
            question=question,
            reason=safety_result["reason"]
        )

        return AskResponse(
            answer="Sorgu güvenlik politikası nedeniyle engellendi.",
            used_context=False,
            sources=[],
            blocked=True,
            reason=safety_result["reason"]
        )

    retrieval_result = retriever.retrieve_with_sources(question)

    context = retrieval_result["context"]
    source_items = retrieval_result["sources"]

    raw_answer = llm.generate(
        question=question,
        context=context
    )

    answer = clean_llm_output(raw_answer)

    audit.log_interaction(
        question=question,
        response=answer,
        user_role=request.user_role
    )

    return AskResponse(
        answer=answer,
        used_context=bool(context),
        context=context if context else None,
        sources=source_items,
        blocked=False,
        reason=None
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
