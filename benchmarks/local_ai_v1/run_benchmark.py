from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path
from urllib import request, error


def load_cases(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def post_ask(base_url: str, api_key: str | None, question: str) -> tuple[dict, float]:
    payload = json.dumps({
        "question": question,
        "user_role": "research",
        "client_request_id": f"benchmark-{time.time_ns()}",
    }, ensure_ascii=False).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-KODAAI-API-Key"] = api_key

    req = request.Request(
        base_url.rstrip("/") + "/ask",
        data=payload,
        headers=headers,
        method="POST",
    )

    started = time.perf_counter()
    with request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed_ms = (time.perf_counter() - started) * 1000
    return data, elapsed_ms


def infer_route(response: dict) -> str | None:
    for step in response.get("process_steps") or []:
        text = str(step)
        for route in ("MATH", "RAG_NO_ANSWER", "RAG", "LLM", "BLOCKED", "DIRECT_KNOWLEDGE"):
            if route in text:
                return route
    return response.get("route")


def score_case(case: dict, response: dict) -> dict:
    answer = str(response.get("answer") or "")
    answer_lower = answer.casefold()
    contains_ok = all(
        str(token).casefold() in answer_lower
        for token in case.get("expected_answer_contains") or []
    )

    refusal_markers = (
        "bulunmuyor",
        "bulunamadı",
        "bulunamadi",
        "verilen kaynak",
        "yeterli bilgi yok",
    )
    refused = any(m in answer_lower for m in refusal_markers)

    expected_route = case.get("expected_route")
    actual_route = infer_route(response)
    route_ok = expected_route is None or expected_route == actual_route

    must_refuse = bool(case.get("must_refuse"))
    refusal_ok = refused if must_refuse else True

    return {
        "contains_ok": contains_ok,
        "route_ok": route_ok,
        "refusal_ok": refusal_ok,
        "passed": contains_ok and route_ok and refusal_ok,
        "actual_route": actual_route,
        "answer": answer,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument(
        "--cases",
        default=str(Path(__file__).with_name("questions.jsonl")),
    )
    parser.add_argument("--out", default="benchmark_report.json")
    args = parser.parse_args()

    api_key = os.environ.get("KODAAI_API_KEY")
    cases = load_cases(Path(args.cases))
    results = []

    for case in cases:
        try:
            response, elapsed_ms = post_ask(args.url, api_key, case["question"])
            score = score_case(case, response)
            score.update({
                "id": case["id"],
                "elapsed_ms": round(elapsed_ms, 2),
                "error": None,
            })
        except (error.URLError, TimeoutError, json.JSONDecodeError, Exception) as exc:
            score = {
                "id": case.get("id"),
                "passed": False,
                "elapsed_ms": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        results.append(score)

    latencies = [r["elapsed_ms"] for r in results if r.get("elapsed_ms") is not None]
    passed = sum(1 for r in results if r.get("passed"))

    report = {
        "benchmark": "KODAAI Local AI v1",
        "case_count": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 4) if results else 0.0,
        "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else None,
        "latency_ms_p50": round(statistics.median(latencies), 2) if latencies else None,
        "results": results,
    }

    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
