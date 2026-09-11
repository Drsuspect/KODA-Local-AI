from pathlib import Path
import re


class TextChunker:
    def __init__(self, chunk_size: int = 600, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def _extract_metadata(self, source: str) -> dict:
        path = Path(source)
        parts = path.parts

        content_type = "unknown"
        subject = "unknown"

        if "license" in parts:
            license_index = parts.index("license")
            relative = parts[license_index + 1:]

            if relative:
                content_type = relative[0]

            if content_type in ("reading", "quiz") and len(relative) >= 2:
                subject = relative[1]

        return {
            "file_name": path.name,
            "file_type": path.suffix.lower().lstrip("."),
            "content_type": content_type,
            "subject": subject,
        }

    def _find_chunk_end(self, text: str, start: int) -> int:
        hard_end = min(start + self.chunk_size, len(text))

        if hard_end >= len(text):
            return len(text)

        search_start = start + int(self.chunk_size * 0.55)
        window = text[search_start:hard_end]

        boundaries = [
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
        ]

        best = -1
        best_len = 0

        for boundary in boundaries:
            pos = window.rfind(boundary)

            if pos > best:
                best = pos
                best_len = len(boundary)

        if best >= 0:
            return search_start + best + best_len

        return hard_end

    def _find_next_start(self, text: str, start: int, end: int) -> int:
        if end >= len(text):
            return len(text)

        overlap_start = max(start + 1, end - self.overlap)
        window = text[overlap_start:end]

        boundaries = [
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
        ]

        best = -1
        best_len = 0

        for boundary in boundaries:
            pos = window.find(boundary)

            if pos >= 0 and (best == -1 or pos < best):
                best = pos
                best_len = len(boundary)

        if best >= 0:
            return overlap_start + best + best_len

        return end

    def _find_active_title(self, text: str, start: int) -> str | None:
        prefix = text[:start]

        matches = list(
            re.finditer(
                r"(?m)^\s*title:\s*(.+?)\s*$",
                prefix
            )
        )

        if not matches:
            return None

        title = matches[-1].group(1).strip()

        return title or None

    def chunk_documents(self, documents: list[dict]) -> list[dict]:
        chunks = []

        for doc in documents:
            text = doc["text"]
            source = doc["source"]

            metadata = self._extract_metadata(source)

            start = 0
            chunk_id = 1

            while start < len(text):
                end = self._find_chunk_end(text, start)
                chunk_text = text[start:end].strip()

                active_title = self._find_active_title(
                    text,
                    start
                )

                has_title = re.search(
                    r"(?m)^\s*title:\s*",
                    chunk_text
                )

                if (
                    chunk_text
                    and active_title
                    and not has_title
                ):
                    chunk_text = (
                        f"title: {active_title}\n"
                        f"{chunk_text}"
                    )

                if chunk_text:
                    chunks.append({
                        "source": source,
                        "file_name": metadata["file_name"],
                        "file_type": metadata["file_type"],
                        "content_type": metadata["content_type"],
                        "subject": metadata["subject"],
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                    })

                if end >= len(text):
                    break

                next_start = self._find_next_start(
                    text,
                    start,
                    end
                )

                if next_start <= start:
                    next_start = end

                start = next_start
                chunk_id += 1

        return chunks
