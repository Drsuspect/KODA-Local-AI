from rag.document_loader import DocumentLoader
from rag.chunker import TextChunker
from rag.chroma_retriever import ChromaRetriever

docs = DocumentLoader("docs").load_documents()
chunks = TextChunker().chunk_documents(docs)

r = ChromaRetriever(
    chunks,
    reset_collection=True
)

result = r.retrieve_with_sources(
    "KODA temel yaklaşımı nedir?",
    top_k=3
)

print("--- CONTEXT ---")
print(result["context"])

print("--- SOURCES ---")
print(result["sources"])
