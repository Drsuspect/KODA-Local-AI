import json
import uuid
from datetime import datetime
from pathlib import Path


class TelemetryLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.telemetry_file = self.log_dir / "telemetry.jsonl"

    def new_request_id(self) -> str:
        return str(uuid.uuid4())

    def log_request(
        self,
        request_id: str,
        route: str,
        duration_ms: float,
        source_count: int = 0,
        used_context: bool = False,
        success: bool = True,
        blocked: bool = False,
        session_id: str | None = None,
        subject: str | None = None,
        accessibility_layer: str = "NONE",
        error: str | None = None,
        question: str | None = None,
    ):
        question_text = (
            " ".join(str(question or "").split())[:500]
            if question is not None
            else None
        )

        record = {
            "timestamp": self._now(),
            "event_type": "request_completed",
            "request_id": request_id,
            "session_id": session_id,
            "route": route,
            "subject": subject,
            "question": question_text,
            "accessibility_layer": accessibility_layer,
            "duration_ms": round(duration_ms, 2),
            "source_count": source_count,
            "used_context": used_context,
            "success": success,
            "blocked": blocked,
            "error": error,
        }

        self._write_jsonl(record)

    def log_stop(
        self,
        request_id: str,
        stop_after_ms: float | None = None,
        session_id: str | None = None,
    ):
        record = {
            "timestamp": self._now(),
            "event_type": "answer_stopped",
            "request_id": request_id,
            "session_id": session_id,
            "stop_after_ms": (
                round(stop_after_ms, 2)
                if stop_after_ms is not None
                else None
            ),
        }

        self._write_jsonl(record)

    def read_events(self, limit: int = 50) -> list[dict]:
        if not self.telemetry_file.exists():
            return []

        records = []

        with self.telemetry_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return records[-limit:]

    def _write_jsonl(self, record: dict):
        with self.telemetry_file.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(record, ensure_ascii=False)
                + "\n"
            )

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")
