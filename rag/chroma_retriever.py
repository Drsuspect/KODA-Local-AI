from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer


class ChromaRetriever:
    def __init__(
        self,
        chunks: list[dict],
        db_dir: str = "chroma_db",
        collection_name: str = "koda_docs",
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        reset_collection: bool = False,
    ):
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(exist_ok=True)

        self.collection_name = collection_name
        self.model = SentenceTransformer(model_name)

        self.client = chromadb.PersistentClient(path=str(self.db_dir))

        if reset_collection:
            try:
                self.client.delete_collection(name=self.collection_name)
                print("🧹 Eski ChromaDB collection silindi.")
            except Exception:
                print("ℹ️ Silinecek mevcut ChromaDB collection bulunamadı.")

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "KODA Secure LLM document memory"}
        )

        self._index_chunks(chunks)

    def _index_chunks(self, chunks: list[dict]):
        if not chunks:
            print("⚠️ İndekslenecek chunk bulunamadı.")
            return

        existing_count = self.collection.count()

        if existing_count > 0:
            print(f"🧠 ChromaDB hazır. Mevcut kayıt sayısı: {existing_count}")
            return

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            source = str(chunk.get("source", "unknown"))
            chunk_id = int(chunk.get("chunk_id", 0))
            text = str(chunk.get("text", "")).strip()

            if not text:
                continue

            ids.append(f"{source}::chunk_{chunk_id}")
            documents.append(text)
            metadatas.append({
                "source": source,
                "chunk_id": chunk_id,
            })

        if not documents:
            print("⚠️ Boş olmayan doküman/chunk bulunamadı.")
            return

        embeddings = self.model.encode(
            documents,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

        print(f"🧠 ChromaDB indeksleme tamamlandı. Yeni kayıt: {len(ids)}")

    def retrieve(self, query: str, top_k: int = 3, min_similarity: float = 0.10) -> str:
        result = self.retrieve_with_sources(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity
        )

        return result["context"]

    def retrieve_with_sources(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.10
    ) -> dict:
        query = query.strip()

        if not query:
            return {
                "context": "",
                "sources": []
            }

        if self.collection.count() == 0:
            return {
                "context": "",
                "sources": []
            }

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        context_parts = []
        sources = []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, distance in zip(documents, metadatas, distances):
            similarity = 1 / (1 + float(distance))

            if similarity < min_similarity:
                continue

            source = meta.get("source", "unknown")
            chunk_id = meta.get("chunk_id", "unknown")

            context_parts.append(
                f"[Kaynak: {source} | Chunk: {chunk_id} | Benzerlik: {similarity:.3f}]\n"
                f"{doc}"
            )

            sources.append({
                "source": source,
                "chunk_id": chunk_id,
                "similarity": round(similarity, 3)
            })

        return {
            "context": "\n\n---\n\n".join(context_parts),
            "sources": sources
        }