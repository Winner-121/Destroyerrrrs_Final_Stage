"""Controlled roll accuracy test on real photos (no rig needed).

Protocol, declared: take side-view photos the team labelled as level, rotate each by a known angle
about the image centre and crop 15 % of the border (so no border artefacts add edges). The rotation
is the ground truth. Two things are measured on every rotated image through the production stages:

1. Instrument error: the body-vertical reading against the image vertical must move by the rotation.
   This is the accuracy of the roll instrument itself.
2. Camera-tilt cancellation: rotating a photo tilts the camera, not the truck. When scene verticals
   are found, the reported body roll must stay near the base value, not follow the rotation.

Usage:  .venv/bin/python eval/run_tilt_eval.py [max_base_images]   -> eval/out/tilt_eval.json
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.run import get_detector                      # noqa: E402
from pipeline.geometry import measure                      # noqa: E402

ANGLES = [-12, -8, -5, -3, 3, 5, 8, 12]
MAX_SIDE = 1280


def rotate_crop(img, deg, margin=0.15):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    rot = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    m = int(min(h, w) * margin)
    return rot[m:h - m, m:w - m]


def read(fn):
    img = cv2.imread(str(fn))
    h, w = img.shape[:2]
    s = MAX_SIDE / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return img


def reading(img):
    det = get_detector()(img)
    M = measure(det, img.shape, img)
    return M


def main():
    mx = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    bases = []
    with open(ROOT / "data" / "labels.csv") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            if r["view"] == "side" and r["roll_label"] == "ok":
                p = ROOT / "data" / ("night_rain" if r["filename"].startswith("night_") else "test") / r["filename"]
                if p.exists():
                    bases.append(p)
    bases = bases[:mx]
    print(f"{len(bases)} level side-view photos labelled by the team; angles {ANGLES}")

    rows, inst_err, cancel_err, sign_ok = [], [], [], []
    t0 = time.time()
    for p in bases:
        img = read(p)
        M0 = reading(img)
        if M0.body_vs_camera_deg is None:
            print(f"  skip {p.name}: no body verticals on the base image")
            continue
        for a in ANGLES:
            M = reading(rotate_crop(img, a))
            if M.body_vs_camera_deg is None:
                rows.append({"file": p.name, "angle": a, "instrument": None})
                continue
            # image rotated by +a (counter-clockwise on screen) tilts the body verticals by -a
            delta = M.body_vs_camera_deg - M0.body_vs_camera_deg
            err = abs(abs(delta) - abs(a))
            inst_err.append(err)
            sign_ok.append(np.sign(delta) == -np.sign(a))
            row = {"file": p.name, "angle": a, "instrument": round(delta, 2), "instrument_err": round(err, 2),
                   "reference": M.roll_reference, "reported_roll": None if M.roll_deg is None else round(M.roll_deg, 2)}
            if M.roll_reference == "scene verticals" and M0.roll_deg is not None and M.roll_deg is not None:
                c = abs(M.roll_deg - M0.roll_deg)
                cancel_err.append(c)
                row["cancel_err"] = round(c, 2)
            rows.append(row)
        print(f"  {p.name[:50]:50s} done, {len(inst_err)} readings so far, {time.time()-t0:.0f}s")

    per_angle = {}
    for a in ANGLES:
        e = [r["instrument_err"] for r in rows if r["angle"] == a and r.get("instrument_err") is not None]
        per_angle[a] = {"n": len(e), "mae": round(float(np.mean(e)), 2) if e else None}
    out = {
        "protocol": "level side-view photos rotated by known angles and cropped 15 %, 1280 px max side",
        "base_images": len(bases),
        "readings": len(inst_err),
        "instrument_mae_deg": round(float(np.mean(inst_err)), 2) if inst_err else None,
        "instrument_median_deg": round(float(np.median(inst_err)), 2) if inst_err else None,
        "sign_agreement": round(float(np.mean(sign_ok)), 3) if sign_ok else None,
        "per_angle": per_angle,
        "camera_tilt_cancel": {
            "n": len(cancel_err),
            "mae_deg": round(float(np.mean(cancel_err)), 2) if cancel_err else None,
            "within_2deg": round(float(np.mean([c <= 2 for c in cancel_err])), 3) if cancel_err else None,
        },
        "no_reading": sum(1 for r in rows if r["instrument"] is None),
        "rows": rows,
    }
    (ROOT / "eval" / "out").mkdir(parents=True, exist_ok=True)
    (ROOT / "eval" / "out" / "tilt_eval.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
