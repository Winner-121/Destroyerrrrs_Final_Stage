"""Detector hit rate on data/raw/*: how often we find a truck mask, >=2 wheels, cargo, a scale.
Writes eval/out/hit_rate.json, eval/out/hit_rate.csv and annotated images under eval/out/raw/<subset>/.
Usage: python tools/hit_rate.py [max_per_subset]
"""
import csv, json, sys, time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
from pipeline.run import analyse

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; OUT = ROOT / "eval" / "out" / "raw"
cap = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
agg = defaultdict(lambda: defaultdict(int)); rows = []; lat = []
for sub in sorted(p for p in RAW.iterdir() if p.is_dir()):
    files = sorted(sub.glob("*.jpg"))[:cap]
    (OUT / sub.name).mkdir(parents=True, exist_ok=True)
    for p in files:
        img = cv2.imread(str(p))
        if img is None:
            continue
        t = time.perf_counter(); r = analyse(img); lat.append(time.perf_counter() - t)
        cv2.imwrite(str(OUT / sub.name / p.name), r.pop("image"), [cv2.IMWRITE_JPEG_QUALITY, 70])
        labels = [d["label"] for d in r["detections"]]
        ch = {c["name"]: c["status"] for c in r["checks"]}
        a = agg[sub.name]; a["n"] += 1
        a["truck"] += "no truck found" not in r["notes"] and "truck too small in frame" not in r["notes"]
        a["wheels>=2"] += labels.count("wheel") >= 2
        a["cargo"] += any(l in ("cargo", "car", "container", "tarpaulin") for l in labels)
        a["scale"] += r["scale_source"] != "none"
        a["view_side"] += r["view"] == "side"; a["view_rear"] += r["view"] == "rear"
        a["roll_reported"] += ch.get("Body roll") in ("pass", "warn", "fail")
        a["overhang_reported"] += ch.get("Rear overhang", ch.get("Side overhang")) in ("pass", "warn", "fail")
        a["height_reported"] += ch.get("Height") in ("pass", "fail")
        a["verdict_" + r["verdict"]] += 1
        rows.append({"subset": sub.name, "file": p.name, "verdict": r["verdict"], "view": r["view"], "scale": r["scale_source"],
                     **{f"check_{k}": v for k, v in ch.items()}, "notes": "; ".join(r["notes"])})
summary = {s: {k: (round(v / a["n"], 2) if k != "n" and not k.startswith("verdict_") else v) for k, v in a.items()} for s, a in agg.items()}
summary["_mean_latency_s"] = round(sum(lat) / len(lat), 3) if lat else None
(ROOT / "eval" / "out" / "hit_rate.json").write_text(json.dumps(summary, indent=1))
with open(ROOT / "eval" / "out" / "hit_rate.csv", "w", newline="") as f:
    keys = sorted({k for r in rows for k in r}); w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
print(json.dumps(summary, indent=1))
