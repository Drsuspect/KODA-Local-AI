class TextChunker:
    def __init__(self, chunk_size: int = 600, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_documents(self, documents: list[dict]) -> list[dict]:
        chunks = []

        for doc in documents:
            text = doc["text"]
            source = doc["source"]

            start = 0
            chunk_id = 1

            while start < len(text):
                end = start + self.chunk_size
                chunk_text = text[start:end].strip()

                if chunk_text:
                    chunks.append({
                        "source": source,
                        "chunk_id": chunk_id,
                        "text": chunk_text
                    })

                chunk_id += 1
                start += self.chunk_size - self.overlap

        return chunks