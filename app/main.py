"""Load Safety Gate — web app. Upload a photo of a loaded truck -> GO / NO-GO."""
from __future__ import annotations

import base64
import io
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageOps

from pipeline.run import analyse, get_detector
from app.label import router as label_router

ROOT = Path(__file__).parent
app = FastAPI(title="Load Safety Gate")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.include_router(label_router)
templates = Jinja2Templates(directory=ROOT / "templates")
EXAMPLES = sorted((ROOT / "static" / "examples").glob("*.jpg")) if (ROOT / "static" / "examples").exists() else []


@app.on_event("startup")
def _warm():
    get_detector()


def _read_image(data: bytes) -> np.ndarray:
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im).convert("RGB")      # phone photos carry rotation in EXIF
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def _to_b64(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf.tobytes()).decode()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"examples": [p.name for p in EXAMPLES]})


@app.post("/analyse")
async def analyse_upload(file: UploadFile = File(...)):
    img = _read_image(await file.read())
    return _respond(img)


@app.get("/analyse/example/{name}")
def analyse_example(name: str):
    p = ROOT / "static" / "examples" / Path(name).name
    if not p.exists():
        return JSONResponse({"error": "no such example"}, status_code=404)
    return _respond(cv2.imread(str(p)))


@app.get("/health")
def health():
    return {"ok": True, "device": get_detector().device}


def _respond(img):
    r = analyse(img)
    r["image_b64"] = _to_b64(r.pop("image"))
    return JSONResponse(r)
