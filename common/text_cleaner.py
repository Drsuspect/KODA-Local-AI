import re


ANSI_ESCAPE_PATTERN = re.compile(
    r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'
)

SOURCE_METADATA_PATTERN = re.compile(
    r'\s*\[Kaynak:[^\]\r\n]*\]\s*',
    re.IGNORECASE
)


def _is_multiple_choice_question(question: str) -> bool:
    if not question:
        return False

    labels = re.findall(
        r"(?im)(?:^|\n|\s)([A-E])\s*[\)\].:]\s+",
        question,
    )

    return len(set(labels)) >= 2


def _remove_spurious_option_prefix(text: str, question: str = "") -> str:
    if not text:
        return ""

    # Gercekten sikli bir soruysa cevap etiketine dokunma.
    if _is_multiple_choice_question(question):
        return text

    # Acik uclu sorularda LLM'nin kaynaktan taklit ettigi
    # "A:", "B)", "C." gibi gereksiz baslangic etiketlerini temizle.
    return re.sub(
        r"^\s*[A-E]\s*[\)\].:]\s*",
        "",
        text,
        count=1,
    )



def _strip_safe_markdown(text: str) -> str:
    """
    Remove presentation-only Markdown without touching
    arithmetic multiplication such as: 2 * 3.
    """

    if not text:
        return ""

    # Markdown headings:
    #   ## Baslik  -> Baslik
    text = re.sub(
        r"(?m)^\s{0,3}#{1,6}\s+",
        "",
        text,
    )

    # Markdown bullet:
    #   * Madde -> Madde
    text = re.sub(
        r"(?m)^\s*\*\s+",
        "",
        text,
    )

    # Unicode bullets.
    text = re.sub(
        r"(?m)^\s*[???]\s+",
        "",
        text,
    )

    # Markdown bold:
    #   **metin** -> metin
    text = re.sub(
        r"\*\*([^\n*]+?)\*\*",
        r"\1",
        text,
    )

    # Alternative Markdown bold:
    #   __metin__ -> metin
    text = re.sub(
        r"__([^\n_]+?)__",
        r"\1",
        text,
    )

    return text


def clean_llm_output(text: str, question: str = "") -> str:
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

    text = text.strip()

    # Presentation-only Markdown isaretlerini temizle.
    # Matematikteki tek '*' carpma operatorune dokunulmaz.
    text = _strip_safe_markdown(text)

    # Acik uclu sorulardaki sahte sik etiketini temizle.
    text = _remove_spurious_option_prefix(text, question)

    return text.strip()

