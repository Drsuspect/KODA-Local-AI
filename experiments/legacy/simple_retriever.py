class SimpleRetriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks

    def retrieve(self, query: str, top_k: int = 3) -> str:
        query_words = set(query.lower().split())
        scored_chunks = []

        for chunk in self.chunks:
            chunk_words = set(chunk["text"].lower().split())
            score = len(query_words.intersection(chunk_words))

            if score > 0:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        selected = scored_chunks[:top_k]

        if not selected:
            return ""

        context_parts = []

        for score, chunk in selected:
            context_parts.append(
                f"[Kaynak: {chunk['source']} | Chunk: {chunk['chunk_id']}]\n"
                f"{chunk['text']}"
            )

        return "\n\n---\n\n".join(context_parts)