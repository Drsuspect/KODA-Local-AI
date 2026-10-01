from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

OFFICIAL_SOURCES = {
    "TDK_YAZIM_2026": {
        "label": "TDK Yazım Kılavuzu (2026 baskısı esaslı çevrim içi sürüm)",
        "url": "https://yazim.tdk.gov.tr/",
        "authority": "official",
    },
    "TDK_SESLER": {
        "label": "TDK - Sesler ve Ses Uyumları",
        "url": "https://yazim.tdk.gov.tr/content/02-sesler-ve-ses-uyumlari.html",
        "authority": "official",
    },
    "TDK_UNLU_DUSMESI": {
        "label": "TDK - Ünlü Düşmesi",
        "url": "https://tdk.gov.tr/icerik/yazim-kurallari/unlu-dusmesi/",
        "authority": "official",
    },
    "TDK_BUYUK_UNLU": {
        "label": "TDK - Büyük Ünlü Uyumu",
        "url": "https://tdk.gov.tr/icerik/yazim-kurallari/buyuk-unlu-uyumu/",
        "authority": "official",
    },
    "TDK_KUCUK_UNLU": {
        "label": "TDK - Küçük Ünlü Uyumu",
        "url": "https://tdk.gov.tr/icerik/yazim-kurallari/kucuk-unlu-uyumu/",
        "authority": "official",
    },
    "TDK_UNSUZ_UYUMU": {
        "label": "TDK - Ünsüz Uyumu",
        "url": "https://tdk.gov.tr/icerik/yazim-kurallari/unsuz-uyumu/",
        "authority": "official",
    },
    "MEB_EKPSS_SES": {
        "label": "MEB Özel Eğitim - EKPSS Türkçe / Ses Bilgisi",
        "url": "https://orgm.meb.gov.tr/ekpssmebozel/content/magazines/pdf/turkce2.pdf",
        "authority": "official",
    },
    "MEB_GORME_DILBILGISI": {
        "label": "MEB Özel Eğitim - Görme / Dil Bilgisi hedefleri",
        "url": "https://orgm.meb.gov.tr/meb_iys_dosyalar/2025_03/13111054_21130034_gorme.pdf",
        "authority": "official",
    },
    "ZEMBEREK": {
        "label": "Zemberek-NLP - Türkçe biçimbilim ve çözümleme (yardımcı teknik kaynak)",
        "url": "https://github.com/ahmetaa/zemberek-nlp",
        "authority": "community-tool",
    },
}

PHONOLOGY_LEXICON = {
    "ayrıntı": {
        "event": "ünlü düşmesi",
        "analysis": "ayır- + -ıntı -> ayrıntı",
        "sources": ["MEB_EKPSS_SES", "TDK_UNLU_DUSMESI"],
        "confidence": "medium",
        "note": "Türetim çözümlemesi uzman incelemesiyle doğrulanmalıdır.",
    },
    "yalnız": {
        "event": "ünlü düşmesi",
        "analysis": "yalın + -ız -> yalnız",
        "sources": ["MEB_EKPSS_SES", "TDK_UNLU_DUSMESI"],
        "confidence": "medium",
        "note": "Tarihsel/türetimsel çözümleme uzman incelemesiyle doğrulanmalıdır.",
    },
}

@dataclass
class Finding:
    severity: str
    code: str
    message: str
    field: str | None = None
    evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _has_shallow_reason(text: str) -> bool:
    t = text.casefold().strip(" .")
    shallow = {
        "yanlıştır", "doğru değildir", "bu seçenek yanlıştır",
        "işlem sonucu bu değildir", "bağlama uymaz",
    }
    return t in shallow or len(t) < 28


def relevant_sources(record: dict[str, Any]) -> list[dict[str, Any]]:
    q = (_norm(record.get("question")) + " " + _norm(record.get("topic"))).casefold()
    keys = ["TDK_YAZIM_2026"]
    if any(x in q for x in ("ses olayı", "ünlü", "ünsüz", "ses bilgisi")):
        keys += ["MEB_EKPSS_SES", "TDK_SESLER", "TDK_UNLU_DUSMESI", "TDK_UNSUZ_UYUMU"]
    if any(x in q for x in ("sözcük tür", "sıfat", "zamir", "zarf", "edat", "bağlaç")):
        keys += ["MEB_GORME_DILBILGISI", "ZEMBEREK"]
    seen = set()
    result = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            result.append({"id": key, **OFFICIAL_SOURCES[key]})
    return result


def analyze_record(record: dict[str, Any]) -> dict[str, Any]:
    findings: list[Finding] = []
    options = record.get("options") or {}
    correct = _norm(record.get("correct_answer"))

    if set(options) != set("ABCDE"):
        findings.append(Finding("fail", "OPTION_SET", "Seçenekler tam olarak A-E olmalı.", "options"))

    for key in "ABCDE":
        opt = options.get(key) or {}
        reason = _norm(opt.get("reason"))
        if "PENDING_" in reason:
            findings.append(Finding("fail", "PENDING_REASON", f"{key} gerekçesi tamamlanmamış.", f"options.{key}.reason"))
        elif _has_shallow_reason(reason):
            findings.append(Finding("warn", "SHALLOW_REASON", f"{key} gerekçesi pedagojik olarak yüzeysel olabilir.", f"options.{key}.reason"))
        if key == correct and opt.get("is_correct") is not True:
            findings.append(Finding("fail", "CORRECT_FLAG", f"{key} doğru cevap ama is_correct=true değil.", f"options.{key}.is_correct"))
        if key != correct and opt.get("is_correct") is True:
            findings.append(Finding("fail", "WRONG_FLAG", f"{key} yanlış seçenek ama is_correct=true.", f"options.{key}.is_correct"))

    blob = " ".join([
        _norm(record.get("question")),
        *[_norm((options.get(k) or {}).get("reason")) for k in "ABCDE"],
        _norm((record.get("pedagogy") or {}).get("explain")),
    ]).casefold()

    evidence = []
    for word, item in PHONOLOGY_LEXICON.items():
        if word in blob:
            ev = {"word": word, **item}
            ev["source_details"] = [{"id": s, **OFFICIAL_SOURCES[s]} for s in item["sources"]]
            evidence.append(ev)

    if "ses olayı" in blob and not any(term in blob for term in (
        "ünlü düşmesi", "ünsüz yumuşaması", "ünsüz benzeşmesi",
        "ünlü daralması", "ses türemesi", "kaynaşma", "ulama"
    )):
        findings.append(Finding(
            "warn", "PHONOLOGY_TERM_MISSING",
            "Ses olayı sorusunda gerekçede olayın adı açıkça belirtilmemiş olabilir.",
            "options/pedagogy",
        ))

    status = "pass"
    if any(f.severity == "fail" for f in findings):
        status = "fail"
    elif findings:
        status = "warn"

    return {
        "status": status,
        "findings": [f.to_dict() for f in findings],
        "evidence": evidence,
        "sources": relevant_sources(record),
        "engine": "KODAAI Turkish Grammar Engine v0.1",
        "limitations": [
            "Bu motor kural/kanıt katmanıdır; tam Türkçe biçimbilim çözümleyicisi değildir.",
            "TDK/MEB kaynakları normatif doğrulama için önceliklidir.",
            "Zemberek yalnız yardımcı morfolojik analiz katmanı olarak planlanmıştır.",
            "verified durumuna geçiş için insan/domain incelemesi zorunludur.",
        ],
    }
