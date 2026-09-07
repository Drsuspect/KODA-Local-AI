import numpy as np
from sentence_transformers import SentenceTransformer


class VectorRetriever:
    def __init__(self, chunks: list[dict], model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.chunks = chunks
        self.model = SentenceTransformer(model_name)

        self.chunk_texts = [chunk["text"] for chunk in chunks]

        if self.chunk_texts:
            self.chunk_embeddings = self.model.encode(
                self.chunk_texts,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
        else:
            self.chunk_embeddings = np.array([])

    def retrieve(self, query: str, top_k: int = 3) -> str:
        if not self.chunks or self.chunk_embeddings.size == 0:
            return ""

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )[0]

        scores = np.dot(self.chunk_embeddings, query_embedding)

        top_indices = np.argsort(scores)[::-1][:top_k]

        context_parts = []

        for idx in top_indices:
            score = float(scores[idx])
            chunk = self.chunks[idx]

            if score < 0.25:
                continue

            context_parts.append(
                f"[Kaynak: {chunk['source']} | Chunk: {chunk['chunk_id']} | Skor: {score:.3f}]\n"
                f"{chunk['text']}"
            )

        return "\n\n---\n\n".join(context_parts)