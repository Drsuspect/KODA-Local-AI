import re


ANSI_ESCAPE_PATTERN = re.compile(
    r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'
)


def clean_llm_output(text: str) -> str:
    if not text:
        return ""

    # ANSI escape temizle
    text = ANSI_ESCAPE_PATTERN.sub('', text)

    # Fazla boşluk temizle
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Unicode normalize benzeri temizlik
    text = text.replace('\r', '')

    return text.strip()