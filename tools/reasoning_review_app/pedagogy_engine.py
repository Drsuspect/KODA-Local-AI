from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

@dataclass
class Finding:
    severity: str
    code: str
    message: str
    field: str | None = None

    def to_dict(self):
        return asdict(self)


def _text(x: Any) -> str:
    return str(x or "").strip()


def analyze_record(record: dict[str, Any]) -> dict[str, Any]:
    findings: list[Finding] = []
    p = record.get("pedagogy") or {}
    options = record.get("options") or {}
    correct = _text(record.get("correct_answer"))

    hint = _text(p.get("hint"))
    explain = _text(p.get("explain"))
    simplify = _text(p.get("simplify"))
    example = _text(p.get("example"))
    check = _text(p.get("check_understanding"))

    if len(hint) < 20:
        findings.append(Finding("warn", "HINT_TOO_SHORT", "İpucu öğrenciyi düşünmeye yöneltecek kadar açıklayıcı olmayabilir.", "pedagogy.hint"))
    if re.search(r"(?i)\bcevap\s+[ABCDE]\b|\bdoğru\s+(seçenek|cevap)\s+[ABCDE]\b", hint):
        findings.append(Finding("fail", "HINT_REVEALS_ANSWER", "İpucu doğru cevabı doğrudan açıklıyor.", "pedagogy.hint"))
    if len(explain) < 45:
        findings.append(Finding("warn", "EXPLAIN_TOO_SHORT", "Ana açıklama gerekçeyi yeterince açmayabilir.", "pedagogy.explain"))
    if len(simplify) > 220:
        findings.append(Finding("warn", "SIMPLIFY_TOO_LONG", "Basitleştirilmiş açıklama kısa ve sesli kullanım dostu olmalı.", "pedagogy.simplify"))
    if not example:
        findings.append(Finding("warn", "EXAMPLE_MISSING", "Genellenebilir bir örnek eklenmesi öğrenme transferini güçlendirir.", "pedagogy.example"))
    if not check.endswith("?"):
        findings.append(Finding("warn", "CHECK_NOT_QUESTION", "Anlama kontrolü soru biçiminde olmalı.", "pedagogy.check_understanding"))

    wrong = [k for k in "ABCDE" if k != correct]
    for key in wrong:
        reason = _text((options.get(key) or {}).get("reason"))
        if len(reason) < 35:
            findings.append(Finding("warn", "WRONG_REASON_THIN", f"{key} seçeneğinin neden yanlış olduğu daha somut açıklanabilir.", f"options.{key}.reason"))
        if reason.casefold().startswith(("yanlıştır", "doğru değildir", f"{key.casefold()} değildir")):
            findings.append(Finding("warn", "WRONG_REASON_CIRCULAR", f"{key} gerekçesi sonucu tekrar ediyor olabilir; hatanın mekanizmasını açıklamalı.", f"options.{key}.reason"))

    q = _text(record.get("question"))
    if "Sesli okuma:" in q:
        if any(sym in explain for sym in ("√", "²", "³", "⁴", "⁻")):
            findings.append(Finding("warn", "TTS_SYMBOLS", "Açıklamada TTS için ayrıca sesli matematik biçimi gerekebilir.", "pedagogy.explain"))

    fail_count = sum(f.severity == "fail" for f in findings)
    warn_count = sum(f.severity == "warn" for f in findings)
    readiness = "blocked" if fail_count else ("review" if warn_count else "ready")

    return {
        "readiness": readiness,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "findings": [f.to_dict() for f in findings],
        "criteria": {
            "wrong_answer_reasoning": "Yanlış seçeneğin neden yanlış olduğunu mekanizma/kanıt üzerinden açıklar.",
            "hint": "Cevabı vermeden yönlendirir.",
            "explain": "Doğru cevabın gerekçesini açık ve izlenebilir biçimde verir.",
            "simplify": "Sesli kullanım için kısa ve anlaşılırdır.",
            "example": "Öğrenilen kuralı yeni örneğe taşır.",
            "check_understanding": "Aktif geri çağırma/mini kontrol sorusu içerir.",
            "accessibility": "TTS ve görme engelli kullanıcı bağlamında belirsiz görsel referanslardan kaçınır.",
        },
        "engine": "KODAAI Pedagogical Control Layer v0.1",
    }
