"""Gate inspection journal: one record per inspection, no images, no filenames of uploads.

Makes the result a ticket the dispatcher can quote and gives the shift a running count of
GO / WARN / NO-GO. Persists in a Modal Dict on Modal, or in data/journal_store.json locally.
Only measured numbers are stored; the photo is discarded after the response.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE_NAME = "lsg-journal"
_lock = threading.RLock()


class Store:
    def __init__(self):
        self.kind = "file"; self.d = None
        try:
            import modal
            if os.environ.get("MODAL_IS_REMOTE") or os.environ.get("MODAL_TASK_ID"):
                self.d = modal.Dict.from_name(STORE_NAME, create_if_missing=True); self.kind = "modal"
        except Exception:
            pass
        self.path = ROOT / "data" / "journal_store.json"

    def all(self) -> dict:
        if self.kind == "modal":
            return {k: v for k, v in self.d.items()}
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return {}

    def put(self, key: str, body: dict):
        if self.kind == "modal":
            self.d[key] = body; return
        with _lock:
            cur = self.all(); cur[key] = body
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(cur, indent=1))


STORE = Store()


def _today() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def record(result: dict, source: str) -> str:
    """Store one inspection and return its ticket id. `source` is 'upload' or 'example:<name>'."""
    now = dt.datetime.now(dt.timezone.utc)
    day = now.strftime("%Y%m%d")
    with _lock:
        n = sum(1 for k in STORE.all() if k.startswith(f"LSG-{day}-")) + 1
        ticket = f"LSG-{day}-{n:04d}"
        values = {c["name"]: {"status": c["status"], "value": c["value"]} for c in result.get("checks", [])}
        STORE.put(ticket, {
            "ticket": ticket, "ts": now.isoformat(timespec="seconds"), "verdict": result["verdict"],
            "checks": values, "view": result.get("view"), "scale": result.get("scale_source"),
            "latency_ms": result.get("timings_ms", {}).get("total"), "source": source,
        })
    return ticket


def recent(limit: int = 20) -> list[dict]:
    rows = sorted(STORE.all().values(), key=lambda r: r["ts"], reverse=True)
    return rows[:limit]


def stats(day: str | None = None) -> dict:
    day = day or _today()
    counts = {"GO": 0, "WARN": 0, "NO-GO": 0, "CANNOT ASSESS": 0}
    for r in STORE.all().values():
        if r["ts"].startswith(day):
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    total = sum(counts.values())
    return {"day": day, **counts, "total": total, "held": counts["NO-GO"] + counts["WARN"]}
