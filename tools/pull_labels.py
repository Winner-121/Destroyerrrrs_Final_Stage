"""Pull team labels from the Modal Dict into data/labels.csv (run locally with the Modal token)."""
import csv, sys
from pathlib import Path
import modal
ROOT = Path(__file__).resolve().parents[1]
d = modal.Dict.from_name("lsg-labels", create_if_missing=True)
labels = {k: v for k, v in d.items()}
rows = []
with open(ROOT / "data" / "labels.csv") as f:
    hdr = next(csv.reader(f))
    for r in csv.DictReader(f, fieldnames=hdr):
        if r["filename"].startswith("#"): continue
        L = labels.get(r["filename"])
        if L:
            r.update({"view": L.get("view", ""), "roll_label": "unclear" if L.get("valid") == "no" else L.get("roll_label", ""),
                      "side_overhang": "unclear" if L.get("valid") == "no" else L.get("side_overhang", ""),
                      "rear_overhang": "unclear" if L.get("valid") == "no" else L.get("rear_overhang", ""),
                      "over_height": "unclear" if L.get("valid") == "no" else L.get("over_height", ""),
                      "notes": (("not a truck; " if L.get("valid") == "no" else "") + L.get("notes", "") + f" [by {L.get('by','?')}]").strip()})
        rows.append(r)
with open(ROOT / "data" / "labels.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(rows)
print(f"{len(labels)} labels pulled, {sum(1 for r in rows if r['view'])} of {len(rows)} rows filled")
