import json
from pathlib import Path
from datetime import datetime


class AuditLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.audit_file = self.log_dir / "audit_log.jsonl"
        self.blocked_file = self.log_dir / "blocked_queries.jsonl"

    def log_interaction(self, question: str, response: str, user_role: str = "unknown"):
        record = {
            "timestamp": self._now(),
            "event_type": "interaction",
            "user_role": user_role,
            "question": question,
            "response": response
        }

        self._write_jsonl(self.audit_file, record)

    def log_blocked_query(self, question: str, reason: str):
        record = {
            "timestamp": self._now(),
            "event_type": "blocked_query",
            "question": question,
            "reason": reason
        }

        self._write_jsonl(self.blocked_file, record)

    def read_interactions(self, limit: int = 50) -> list[dict]:
        return self._read_jsonl(self.audit_file, limit=limit)

    def read_blocked_queries(self, limit: int = 50) -> list[dict]:
        return self._read_jsonl(self.blocked_file, limit=limit)

    def _write_jsonl(self, path: Path, record: dict):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path, limit: int = 50) -> list[dict]:
        if not path.exists():
            return []

        records = []

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return records[-limit:]

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")