# Load Safety Gate

One photo of a loaded truck at the depot gate → **GO / WARN / NO-GO** with three measured checks:
body roll, cargo overhang, and height. Plates and people are pixelated before anything is stored or shown.

Track: Computer Vision (automotive business and road safety). Mode: Startup. Customer: fleet owners and freight
terminals. Partner angle: car-carrier trucks delivering to Toyota Royal Motors and BYD Royal Motors.

## How it works

```
photo ──► YOLO-World (open-vocabulary boxes: truck, trailer, cargo, wheel, plate, person)
      ──► YOLOv8-seg (COCO truck mask)
      ──► privacy stage: pixelate plates and people         (pipeline/privacy.py)
      ──► geometry: roll, overhang, height, all relative     (pipeline/geometry.py)
          to objects in the same image, scaled by trailer
          width 2.55 m or wheel diameter 1.05 m
      ──► decision layer: road-code thresholds → verdict     (pipeline/decision.py, pipeline/config.yaml)
      ──► annotated image + checklist                       (app/)
```

- **Body roll** = angle between the body top edge (RANSAC fit on the truck mask) and the wheel contact line.
  Camera roll cancels because both lines are in the same image.
- **Overhang** = cargo box extent beyond the body edge at cargo height. Rear overhang in a side view, side overhang in a rear view.
- **Height** = cargo top to ground, scaled by the wheel diameter.
- Low-confidence or missing inputs produce `CANNOT ASSESS` or a skipped check, never a guess.

Models are pretrained and untrained by us (Ultralytics YOLO-World v2 and YOLOv8s-seg, AGPL-3.0).
Our own work is the pipeline, the geometry, the decision rules, the evaluation set and the app.

## Run locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python app.py                      # Gradio UI, same as the deployed Space, http://localhost:7860
# or the FastAPI variant: uvicorn app.main:app --port 7860
# CLI: python -m pipeline.run path/to/truck.jpg out.jpg
```

## Deployment

Modal (serverless CPU container, one instance kept warm) deployed from this repository by GitHub Actions on every push to `main`
(`.github/workflows/deploy.yml`, `modal_app.py`). Secrets: `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`.
Hugging Face Spaces was the first choice but compute Spaces require a paid plan on the team's account.

Public URL: _to be filled_

## Evaluation

```bash
python eval/run_eval.py      # reads data/labels.csv, writes eval/out/metrics.json
```

Metrics table: _filled from eval/out/metrics.json before submission_

| Check | Precision | Recall | n |
|---|---|---|---|
| Tilted body | | | |
| Rear overhang | | | |
| Side overhang | | | |
| Over height | | | |
| Night / rain subset | | | |

Roll MAE on rig photos with known angle: _ degrees. Mean latency: _ ms (CPU). Cost per inspection: _ USD.

### Known failure cases
- Front-only or three-quarter views: body edges are foreshortened, roll confidence is reduced.
- No wheels or body edge visible: no scale, overhang and height are skipped.
- Dark trucks at night: mask boundary noisy, roll may be reported with low confidence.
- Cargo that matches the body colour is sometimes merged into the truck mask, hiding overhang.

## Data sources and licences

All images are listed in `data/SOURCES.csv` with URL, licence and attribution.
No faces or plates are stored unblurred. No customer or personal data is used.

| Source | Licence | Use |
|---|---|---|
| Open Images V7 (truck class) | CC BY 4.0 annotations, CC BY 2.0 images | test set |
| Pexels / Unsplash | Pexels License / Unsplash License | test set, night and rain |
| Own photos (toy-truck rig at known tilt) | team, CC BY 4.0 | roll accuracy |
| Ultralytics YOLO-World v2, YOLOv8s-seg weights | AGPL-3.0 | detection |

## Libraries
Ultralytics, OpenCV, NumPy, FastAPI, Uvicorn, Pillow, PyYAML. Built during the final by the team with LLM coding assistance.
