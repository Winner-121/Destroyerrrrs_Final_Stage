"""Run the full pipeline on one image and print the result. Used as a first health check."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
from pipeline.run import analyse

p = sys.argv[1]
img = cv2.imread(p)
assert img is not None, f"cannot read {p}"
r = analyse(img)
out = Path("eval/out"); out.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(out / ("smoke_" + Path(p).name)), r.pop("image"))
print(json.dumps(r, indent=2, default=str))
