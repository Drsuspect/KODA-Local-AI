from pathlib import Path
import json
import pymupdf
from docx import Document


class DocumentLoader:
    def __init__(self, docs_dir: str = "docs"):
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(exist_ok=True)

    def load_documents(self) -> list[dict]:
        documents = []

        for file_path in self.docs_dir.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix.lower()

                try:
                    if suffix == ".txt":
                        text = self._load_txt(file_path)

                    elif suffix == ".pdf":
                        text = self._load_pdf(file_path)

                    elif suffix == ".docx":
                        text = self._load_docx(file_path)

                    elif suffix == ".json":
                        text = self._load_json(file_path)

                    else:
                        continue

                    if text.strip():
                        documents.append({
                            "source": str(file_path),
                            "file_name": file_path.name,
                            "file_type": suffix.replace(".", ""),
                            "text": text
                        })

                except Exception as e:
                    print(f"Doküman okunamadı: {file_path} | Hata: {e}")

        return documents

    def _load_txt(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8-sig", errors="ignore")

    def _load_pdf(self, file_path: Path) -> str:
        text_parts = []

        with pymupdf.open(file_path) as pdf:
            for page_no, page in enumerate(pdf, start=1):
                page_text = page.get_text("text")

                if page_text.strip():
                    text_parts.append(
                        f"\n[Sayfa {page_no}]\n{page_text}"
                    )

        return "\n".join(text_parts)

    def _load_docx(self, file_path: Path) -> str:
        doc = Document(file_path)
        paragraphs = []

        for para in doc.paragraphs:
            text = para.text.strip()

            if text:
                paragraphs.append(text)

        return "\n".join(paragraphs)

    def _load_json(self, file_path: Path) -> str:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        return self._json_to_text(data)

    def _json_to_text(self, data, prefix="") -> str:
        lines = []

        if isinstance(data, dict):
            for key, value in data.items():
                label = f"{prefix}{key}"

                if isinstance(value, (dict, list)):
                    lines.append(f"{label}:")
                    lines.append(self._json_to_text(value, prefix="  "))
                else:
                    lines.append(f"{label}: {value}")

        elif isinstance(data, list):
            for index, item in enumerate(data, start=1):
                lines.append(f"{prefix}Kayıt {index}:")
                lines.append(self._json_to_text(item, prefix="  "))

        else:
            lines.append(f"{prefix}{data}")

        return "\n".join(lines)

