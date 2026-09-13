import json
import time
import urllib.request
from pathlib import Path

API_URL = "http://127.0.0.1:8080/api/chat"

QUESTIONS = [
    "Ülkemizin iklim özellikleri nelerdir?",
    "Türkiye'nin iklim özellikleri nelerdir?",
    "Orhun Yazıtlarının Türk tarihi açısından önemi nedir?",
    "Orhun kitabelerini kim yazmıştır?",
    "Lozan Barış Antlaşmasının önemi nedir?",
    "Atatürk'ün Türk tarihi açısından önemi nedir?",
    "Rasyonel sayılar nedir?",
    "Kelimede anlam nedir?",
    "Paragraf soruları nasıl çözülür?",
    "2*(x+3)=14",
]

OUT = Path("data/routing/live_baseline_results.json")
OUT.parent.mkdir(parents=True, exist_ok=True)


def ask(question):
    payload = {
        "question": question,
        "user_role": "research"
    }

    data = json.dumps(
        payload,
        ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8"
        },
        method="POST"
    )

    started = time.perf_counter()

    with urllib.request.urlopen(req, timeout=180) as response:
        raw = response.read()

    elapsed_ms = (
        time.perf_counter() - started
    ) * 1000

    obj = json.loads(raw.decode("utf-8"))

    return elapsed_ms, obj


print("=" * 80)
print("KODAAI LIVE BASELINE TEST")
print("=" * 80)
print("API:", API_URL)

results = []

for no, question in enumerate(QUESTIONS, 1):

    print()
    print("=" * 80)
    print(f"TEST {no}")
    print("SORU:", question)

    try:
        elapsed_ms, obj = ask(question)

        answer = obj.get("answer")
        used_context = obj.get("used_context")
        blocked = obj.get("blocked")
        reason = obj.get("reason")
        sources = obj.get("sources") or []
        steps = obj.get("process_steps") or []

        print("SURE:", round(elapsed_ms, 2), "ms")
        print("CEVAP:", answer)
        print("USED_CONTEXT:", used_context)
        print("BLOCKED:", blocked)
        print("REASON:", reason)

        print("SOURCES:")

        if not sources:
            print("  - YOK")

        for source in sources:
            print(
                "  -",
                source.get("file_name"),
                "|",
                source.get("subject"),
                "| chunk:",
                source.get("chunk_id"),
                "| sim:",
                source.get("similarity")
            )

        print("PROCESS_STEPS:")

        for step in steps:
            print("  -", step)

        results.append({
            "question": question,
            "elapsed_ms": round(elapsed_ms, 2),
            "answer": answer,
            "used_context": used_context,
            "blocked": blocked,
            "reason": reason,
            "sources": sources,
            "process_steps": steps
        })

    except Exception as exc:
        print("HATA:", repr(exc))

        results.append({
            "question": question,
            "error": repr(exc)
        })


OUT.write_text(
    json.dumps(
        results,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print()
print("=" * 80)
print("TEST TAMAMLANDI")
print("SONUC DOSYASI:", OUT.resolve())
print("=" * 80)
