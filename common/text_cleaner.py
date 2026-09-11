import re


ANSI_ESCAPE_PATTERN = re.compile(
    r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'
)

SOURCE_METADATA_PATTERN = re.compile(
    r'\s*\[Kaynak:[^\]\r\n]*\]\s*',
    re.IGNORECASE
)


def clean_llm_output(text: str) -> str:
    if not text:
        return ""

    # Remove ANSI escape sequences.
    text = ANSI_ESCAPE_PATTERN.sub("", text)

    # Remove retrieval/source metadata accidentally echoed by the LLM.
    # Example:
    # [Kaynak: /path/to/file.json | Tur: reading | Chunk: 12 | Benzerlik: 0.629]
    text = SOURCE_METADATA_PATTERN.sub(" ", text)

    # Normalize line endings.
    text = text.replace("\r", "")

    # Collapse excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse repeated horizontal whitespace without destroying newlines.
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()

