"""Evaluate the pipeline on data/test using data/labels.csv.

Outputs eval/out/metrics.json and eval/out/per_image.csv, plus annotated images.
Metrics: precision/recall per check (tilted, side_overhang, rear_overhang, over_height),
MAE of roll in degrees on rig photos with roll_deg_true, mean latency, cost per inspection.
"""
import csv, json, sys, time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.run import analyse  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "out"; OUT.mkdir(exist_ok=True, parents=True)
IMG_DIRS = [ROOT / "data" / "test", ROOT / "data" / "night_rain", ROOT / "data" / "rig"]
CPU_COST_PER_HOUR = 0.03   # HF Spaces CPU basic tier, USD; edit if different


def load_labels():
    rows = {}
    with open(ROOT / "data" / "labels.csv") as f:
        for r in csv.DictReader(l for l in f if not l.startswith("#")):
            rows[r["filename"]] = r
    return rows


def pr(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    return {"precision": p, "recall": r, "tp": tp, "fp": fp, "fn": fn}


def main():
    labels = load_labels()
    per = []
    counts = {k: [0, 0, 0] for k in ["tilted", "side_overhang", "rear_overhang", "over_height", "load_leaning"]}
    counts_night = {k: [0, 0, 0] for k in counts}
    roll_err, lat = [], []
    clean_n = clean_ok = 0
    for d in IMG_DIRS:
        for p in sorted(d.glob("*.jp*g")) + sorted(d.glob("*.png")):
            lab = labels.get(p.name)
            if not lab or not lab.get("view"):
                continue          # not labelled yet
            img = cv2.imread(str(p))
            t0 = time.perf_counter(); r = analyse(img); lat.append(time.perf_counter() - t0)
            cv2.imwrite(str(OUT / p.name), r.pop("image"))
            ch = {c["name"]: c for c in r["checks"]}
            pred = {
                "tilted": ch.get("Body roll", {}).get("status") in ("warn", "fail"),
                "side_overhang": ch.get("Side overhang", {}).get("status") == "fail",
                "rear_overhang": ch.get("Rear overhang", {}).get("status") in ("warn", "fail"),
                "over_height": ch.get("Height", {}).get("status") == "fail",
                "load_leaning": ch.get("Load lean", {}).get("status") in ("warn", "fail"),   # informational check never fires
            }
            truth = {
                "tilted": lab["roll_label"] == "tilted",
                "side_overhang": lab["side_overhang"] == "yes",
                "rear_overhang": lab["rear_overhang"] == "yes",
                "over_height": lab["over_height"] == "yes",
                "load_leaning": lab.get("load_position") == "leaning",
            }
            tgt = counts_night if d.name == "night_rain" else counts
            for k in counts:
                if lab.get({"tilted": "roll_label", "side_overhang": "side_overhang", "rear_overhang": "rear_overhang",
                            "over_height": "over_height", "load_leaning": "load_position"}[k], "") in ("unclear", ""):
                    continue          # unclear, or not labelled for this question
                if pred[k] and truth[k]: tgt[k][0] += 1
                elif pred[k] and not truth[k]: tgt[k][1] += 1
                elif not pred[k] and truth[k]: tgt[k][2] += 1
            if all(truth[k] is False for k in truth) and all(lab.get(c) != "unclear" for c in ("roll_label", "side_overhang", "rear_overhang", "over_height")):
                clean_n += 1; clean_ok += int(not any(pred.values()))
            if lab.get("roll_deg_true"):
                v = ch.get("Body roll", {}).get("value", "")
                try:
                    roll_err.append(abs(float(v.split("°")[0]) - abs(float(lab["roll_deg_true"]))))
                except ValueError:
                    pass
            per.append({"filename": p.name, "subset": d.name, "verdict": r["verdict"], **{f"pred_{k}": pred[k] for k in pred},
                        **{f"true_{k}": truth[k] for k in truth}, "latency_s": round(lat[-1], 3), "notes": "; ".join(r["notes"])})
    mean_lat = sum(lat) / len(lat) if lat else None
    metrics = {
        "n_images": len(per),
        "per_check": {k: pr(*v) for k, v in counts.items()},
        "night_rain": {k: pr(*v) for k, v in counts_night.items()},
        "clean_images": clean_n, "clean_no_false_alarm": clean_ok,
        "false_alarm_rate_on_clean": (1 - clean_ok / clean_n) if clean_n else None,
        "roll_mae_deg": sum(roll_err) / len(roll_err) if roll_err else None,
        "roll_n": len(roll_err),
        "mean_latency_s": mean_lat,
        "cost_per_inspection_usd": (mean_lat / 3600 * CPU_COST_PER_HOUR) if mean_lat else None,
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    with open(OUT / "per_image.csv", "w", newline="") as f:
        if per:
            w = csv.DictWriter(f, fieldnames=per[0].keys()); w.writeheader(); w.writerows(per)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
