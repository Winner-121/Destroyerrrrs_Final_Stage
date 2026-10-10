"""Team labelling tool, served by our own app. Labels persist in a Modal Dict when running on Modal,
or in data/labels_store.json locally. Pull them with tools/pull_labels.py."""
from __future__ import annotations

import csv, json, os, threading, time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parents[1]
SLUG = os.environ.get("LABEL_SLUG", "destroyerrrrs")
STORE_NAME = "lsg-labels"
router = APIRouter()
_lock = threading.Lock()


def _items():
    rows = []
    with open(ROOT / "data" / "labels.csv") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            fn = r["filename"]; folder = "night_rain" if fn.startswith("night_") else "test"
            if (ROOT / "data" / folder / fn).exists():
                rows.append({"f": fn, "g": fn.split("_")[0], "folder": folder})
    return rows


class Store:
    def __init__(self):
        self.kind = "file"; self.d = None
        try:
            import modal
            if os.environ.get("MODAL_IS_REMOTE") or os.environ.get("MODAL_TASK_ID"):
                self.d = modal.Dict.from_name(STORE_NAME, create_if_missing=True); self.kind = "modal"
        except Exception:
            pass
        self.path = ROOT / "data" / "labels_store.json"

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
            cur = self.all(); cur[key] = body; self.path.write_text(json.dumps(cur, indent=1))


STORE = Store()
ITEMS = _items()
FIELDS = ["view", "roll_label", "side_overhang", "rear_overhang", "over_height", "load_position", "valid"]


def _check(slug):
    if slug != SLUG:
        raise HTTPException(404)


@router.get("/label/{slug}", response_class=HTMLResponse)
def page(slug: str, request: Request):
    _check(slug)
    html = (ROOT / "app" / "templates" / "label.html").read_text()
    return html.replace("__ITEMS__", json.dumps([{"f": i["f"], "g": i["g"]} for i in ITEMS])).replace("__SLUG__", slug)


@router.get("/label/{slug}/img/{name}")
def img(slug: str, name: str):
    _check(slug)
    it = next((i for i in ITEMS if i["f"] == Path(name).name), None)
    if not it:
        raise HTTPException(404)
    return FileResponse(ROOT / "data" / it["folder"] / it["f"], media_type="image/jpeg")


@router.get("/label/{slug}/state")
def state(slug: str):
    _check(slug)
    return JSONResponse({"labels": STORE.all(), "store": STORE.kind})


@router.post("/label/{slug}/save")
async def save(slug: str, request: Request):
    _check(slug)
    body = await request.json()
    fn = body.get("filename", "")
    if not any(i["f"] == fn for i in ITEMS):
        raise HTTPException(400, "unknown filename")
    rec = {k: str(body.get(k, ""))[:40] for k in FIELDS}
    rec.update({"filename": fn, "notes": str(body.get("notes", ""))[:500], "by": str(body.get("by", ""))[:40], "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    if rec["valid"] != "no" and any(not rec[k] for k in FIELDS):
        raise HTTPException(400, "incomplete")
    STORE.put(fn, rec)
    return {"ok": True, "n": len(STORE.all())}
