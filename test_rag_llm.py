from rag.document_loader import DocumentLoader
from rag.chunker import TextChunker
from rag.chroma_retriever import ChromaRetriever
from llm_core.local_model import LocalLLM


QUESTION = "KODA'nın kurucusu kimdir?"


docs = DocumentLoader("docs").load_documents()
chunks = TextChunker().chunk_documents(docs)

retriever = ChromaRetriever(
    chunks,
    reset_collection=True
)

retrieval = retriever.retrieve_with_sources(
    QUESTION,
    top_k=3
)

context = retrieval["context"]

print("=== RETRIEVED CONTEXT ===")
print(context)
print()

if not context.strip():
    print("HATA: Soruyla ilgili context bulunamadı.")
    raise SystemExit(1)

prompt = f"""
Sen KODA Secure LLM Core içinde çalışan yerel bir asistansın.

Aşağıdaki KAYNAK metne dayanarak soruyu cevapla.

Kurallar:
- Sadece verilen kaynakta bulunan bilgilere dayan.
- Kaynakta olmayan bilgi ekleme.
- Tahmin yapma.
- Cevabı kısa, açık ve Türkçe ver.
- Eğer cevap kaynakta yoksa sadece:
  "Bu bilgi verilen kaynaklarda bulunmuyor."
  yaz.

KAYNAK:
{context}

SORU:
{QUESTION}

CEVAP:
""".strip()

model = LocalLLM(
    model_name="gemma3:4b",
    mode="offline"
)

answer = model.generate(prompt)

print("=== KODA LOCAL RAG ANSWER ===")
print(answer)
print()

print("=== SOURCES ===")
for source in retrieval["sources"]:
    print(source)

