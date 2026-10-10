"""End-to-end: image -> privacy blur -> detect -> measure -> decide -> annotated image."""
from __future__ import annotations

import time
from dataclasses import asdict

import cv2
import numpy as np

from .decision import Decision, decide
from .detect import Detector, Detections
from .geometry import Measurements, measure
from .privacy import pixelate

_det: Detector | None = None

COL = {"pass": (40, 170, 60), "warn": (0, 170, 255), "fail": (40, 40, 230), "skip": (140, 140, 140)}


def get_detector() -> Detector:
    global _det
    if _det is None:
        _det = Detector()
    return _det


def annotate(img: np.ndarray, det: Detections, M: Measurements, D: Decision) -> np.ndarray:
    out = img.copy()
    if det.truck_mask is not None:
        overlay = out.copy()
        overlay[det.truck_mask > 0] = (0.6 * overlay[det.truck_mask > 0] + 0.4 * np.array([255, 200, 0])).astype(np.uint8)
        out = overlay
    for b in det.boxes:
        c = (255, 120, 0) if b.label == "wheel" else (0, 200, 255)
        cv2.rectangle(out, b.xyxy[:2], b.xyxy[2:], c, 2)
        cv2.putText(out, f"{b.label} {b.conf:.2f}", (b.xyxy[0], max(12, b.xyxy[1] - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1)
    if M.top_line:
        cv2.line(out, M.top_line.as_int()[:2], M.top_line.as_int()[2:], (0, 255, 0), 3)
    if M.bottom_line:
        cv2.line(out, M.bottom_line.as_int()[:2], M.bottom_line.as_int()[2:], (0, 255, 0), 3)
    if M.overhang_px:
        xb, xc, y = M.overhang_px
        cv2.line(out, (int(xb), int(y)), (int(xc), int(y)), (0, 0, 255), 4)
    if M.height_px:
        x, yt, yg = M.height_px
        cv2.line(out, (x, yt), (x, yg), (255, 0, 255), 3)
    # verdict banner
    col = {"GO": COL["pass"], "WARN": COL["warn"], "NO-GO": COL["fail"]}.get(D.verdict, COL["skip"])
    cv2.rectangle(out, (0, 0), (out.shape[1], 44), col, -1)
    cv2.putText(out, D.verdict, (12, 32), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
    y = 70
    for c in D.checks:
        cv2.putText(out, f"{c.name}: {c.value} [{c.status}]", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, COL[c.status], 2)
        y += 26
    return out


def analyse(img_bgr: np.ndarray, max_side: int = 1280) -> dict:
    t0 = time.perf_counter()
    h, w = img_bgr.shape[:2]
    s = max_side / max(h, w)
    if s < 1:
        img_bgr = cv2.resize(img_bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    det = get_detector()(img_bgr)
    safe = pixelate(img_bgr, det.privacy_boxes)      # from here on only the blurred image exists
    M = measure(det, safe.shape)
    D = decide(M)
    vis = annotate(safe, det, M, D)
    total = (time.perf_counter() - t0) * 1000
    return {
        "verdict": D.verdict,
        "checks": [asdict(c) for c in D.checks],
        "notes": D.notes,
        "view": M.view,
        "scale_source": M.scale_source,
        "privacy_regions_blurred": len(det.privacy_boxes),
        "detections": [{"label": b.label, "conf": round(b.conf, 3), "xyxy": b.xyxy} for b in det.boxes],
        "timings_ms": {**{k: round(v, 1) for k, v in det.timings_ms.items()}, "total": round(total, 1)},
        "device": get_detector().device,
        "image": vis,
    }


if __name__ == "__main__":
    import json, sys
    img = cv2.imread(sys.argv[1])
    r = analyse(img)
    out = sys.argv[2] if len(sys.argv) > 2 else "out.jpg"
    cv2.imwrite(out, r.pop("image"))
    print(json.dumps(r, indent=2))
