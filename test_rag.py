import json
import urllib.request
import time


API_URL = "http://127.0.0.1:8080/ask"


def ask(question: str) -> dict:
    payload = json.dumps(
        {
            "question": question,
            "user_role": "research",
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    print("API isteği gönderiliyor...")

    started = time.perf_counter()

    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    elapsed = (time.perf_counter() - started) * 1000

    print(f"API cevabı geldi: {elapsed:.0f} ms")
    return data


def main():
    result = ask(
        "Satürn gezegeninde 1842 yılında hangi yerel belediye başkanı görev yapıyordu?"
    )

    print("\n=== ANSWER ===")
    print(result.get("answer"))

    sources = result.get("sources", [])

    print("\n=== SOURCES ===")
    print(f"Kaynak sayısı: {len(sources)}")

    for source in sources:
        print(source)

    print("\n=== PROCESS STEPS ===")

    for step in result.get("process_steps", []):
        print(step)

    assert result.get("blocked") is False, \
        "Sorgu beklenmedik şekilde engellendi."

    assert result.get("used_context") is True, \
        "RAG context kullanılmadı."

    assert len(sources) > 0, \
        "Retriever kaynak döndürmedi."

    assert result.get("answer"), \
        "Cevap boş döndü."

    print("\nRAG SMOKE TEST: OK")


if __name__ == "__main__":
    main()
