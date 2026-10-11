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
      ──► annotated image + checklist + inspection ticket   (app/)
      ──► shift journal: ticket, time, verdict, values      (app/journal.py, Modal Dict; no image stored)
```

- **Body roll** = angle of the body's vertical edges against scene verticals (poles, walls) in the same image, or against
  the image vertical with reduced confidence when no scene vertical is found. Left and right body edges converge in opposite
  directions under perspective, so their mean cancels it. Camera roll cancels when a scene vertical exists.
- **Overhang** = cargo box extent beyond the body edge at cargo height. Rear overhang in a side view, side overhang in a rear view.
  In a rear view with the load stacked above the body, the load width comes from the truck mask above the vehicle box.
- **Height** = highest point of anything resting on the truck (cargo boxes, truck mask, any detection whose bottom sits inside the truck box) to ground, scaled by the wheel diameter or the body width.
- **Load lean (experimental)** = for a load stacked above the body in a rear view, the mean angle of the stack's two side
  edges against the image vertical (averaging both edges cancels perspective), plus whether the stack is wider at the top
  than at the body. No regulation covers stack lean and the labelled test set gave it no support, so it is shown as an
  observation and does not change the verdict (see Evaluation).
- Low-confidence or missing inputs produce `CANNOT ASSESS` or a skipped check, never a guess.

Models are pretrained and untrained by us (Ultralytics YOLO-World v2 and YOLOv8s-seg, AGPL-3.0).
Our own work is the pipeline, the geometry, the decision rules, the evaluation set and the app.

## Run locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 7860       # web app, same code as the deployed version, http://localhost:7860
python -m pipeline.run path/to/truck.jpg out.jpg    # command line: verdict as JSON, annotated image to out.jpg
python eval/smoke_test.py path/to/truck.jpg         # first health check
```

## Deployment

Modal (serverless CPU container, one instance kept warm) deployed from this repository by GitHub Actions on every push to `main`
(`.github/workflows/deploy.yml`, `modal_app.py`). Secrets: `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`.
Hugging Face Spaces was the first choice but compute Spaces require a paid plan on the team's account.

Public URL: https://amir-kuldashev--load-safety-gate-web.modal.run

## Decision thresholds (local regulation)

Uzbekistan, Cabinet of Ministers Decree No. 342 of 26 Dec 2011, Annex 2 (via [Uzavtoyul](https://gov.uz/ru/uzavtoyul/sections/view/48313)):
a vehicle, loaded or empty, is oversized when height exceeds **4.0 m**, width exceeds **2.55 m** (2.6 m for refrigerated bodies),
or cargo protrudes more than **2 m** beyond the rear of the body. Beyond these limits a special permit and escort rules apply.
The decision layer uses exactly these values (`pipeline/config.yaml`); roll thresholds (4 degrees warn, 7 degrees fail) are
engineering choices, not regulation, and are stated as such.

## Real conditions, as required by the brief

- **Where inference runs:** one CPU container on Modal, 2 cores, 4 GiB, kept warm; no GPU. The same code runs on a laptop or a
  small edge box with `uvicorn`, the Dockerfile builds the identical image for self-hosting.
- **Speed:** 0.2 s per image measured on the deployed container, about 0.3 s end to end on a phone over 4G.
- **Cost:** below $0.001 of compute per inspection, about $90 per month for the always-warm server, one server serves many gates.
- **Night:** the truck is found on 97 % of the 41 night photos, the most robust stage; edges are noisier so roll confidence
  drops and the check is skipped more often. Measured, see Evaluation.
- **Rain:** not measured. The licensed set holds only two rain photos, too few to report a number.
- **Local vehicles and plates:** the set is international Commons photos with a handful of CIS and Uzbek trucks, so numbers for
  local fleets are not yet measured; month one of the pilot collects them at the gate. Plates and faces are found with an
  open-vocabulary prompt and pixelated before storage or display, on every image, whatever the plate format.

## Cost model

| Item | Value | Basis |
|---|---|---|
| Inference time | ~0.19 s per image, CPU | measured on Modal, 2 cores |
| Compute per inspection | < $0.001 | 0.19 s x ($0.094 core-hour + $0.032 memory-hour) / 3600 |
| One always-warm server | ~$90 / month | Modal, 2 cores + 4 GiB, 24/7; serves many gates |
| Camera per gate | $100 to $300 | fixed IP camera and mount, one-off |
| Hardware alternative | ~$150 one-off | the same model runs on a small edge box (CPU), no cloud |

## Evaluation

```bash
python tools/fetch_commons.py   # download licensed Commons photos, append data/SOURCES.csv
python tools/hit_rate.py        # detector hit rate per subset on data/raw -> eval/out/hit_rate.json
# team labelling: open <deployed url>/label/<slug> ; labels persist in a Modal Dict
python tools/pull_labels.py     # pull team labels into data/labels.csv
python eval/run_eval.py         # precision/recall per check, night subset, latency -> eval/out/metrics.json
python eval/run_tilt_eval.py    # controlled roll accuracy on rotated level photos -> eval/out/tilt_eval.json
```

Deck: `deck/LoadSafetyGate_deck.pptx` (built by `deck/build_deck.js`), PDF alongside.

Results on the 101 test images labelled by the team (19 of 120 were marked not a truck or left unlabelled). Regenerated from `eval/out/metrics.json`:

| Check | Precision | Recall | tp / fp / fn |
|---|---|---|---|
| Tilted body | 0.40 | 0.18 | 2/3/9 |
| Rear overhang | 0.00 | 0.00 | 0/1/7 |
| Side overhang | n/a | 0.00 | 0/0/6 |
| Over height | 0.57 | 0.24 | 4/3/13 |
| Clean trucks with no false alarm | 39 of 44 | | specificity 89% |

Reading: 61 of the 101 labelled photos are three-quarter views and 16 are rear or front views. The measurement stages only
report when a side or rear view gives them a scale object, so on this uncontrolled set they are deliberately conservative:
clean trucks are rarely flagged (89% specificity) but only 6 of 41 labelled positive checks were caught. Verdicts on the set: 55 GO, 7 WARN, 9 NO-GO, 31 CANNOT ASSESS.
Roll and height are reported on side and rear views (rear views take scale from the 2.55 m body width); three-quarter views are gated to CANNOT ASSESS.
The detector stages are robust (truck found on 86 to 97 percent of real truck photos, night included). The measurement stages
need the controlled geometry of a fixed gate camera, which is the product configuration. Mean latency 0.20 s per image on CPU.

### Load lean, experimental and not counted

The team labelled the stack position on all 120 photos: 50 straight, 2 leaning, 36 with no stacked load, 32 unclear. The
measurement only runs on a rear view with the load above the body, which is 2 of the 101 photos. Both leaning stacks are
side or three-quarter views, where it cannot run, and the one rear-view reading disagreed with the human label (the stack
read 10 degrees right, the labeller called it straight). Result: 0 of 2 caught, 1 disagreement. The reading is therefore
shown on the result page in brackets as an observation and never changes the verdict. It stays in the code because the
geometry is sound and the gate camera will give the rear view it needs; it needs its own test set before it counts.

### Roll instrument accuracy, controlled test

No tilt rig was available, so the protocol is declared synthetic: the 7 side-view photos the team labelled as level and on
which the body edges are found are rotated by -12, -8, -5, -3, +3, +5, +8, +12 degrees about the image centre and cropped by
15 percent so no border edge is introduced. The rotation is the ground truth. Regenerated from `eval/out/tilt_eval.json`:

| Quantity | Value |
|---|---|
| Readings | 56 (7 photos x 8 angles) |
| Mean absolute error of the body-angle reading | 1.63 deg |
| Median absolute error | 0.74 deg |
| Sign of the tilt correct | 93% |
| Error at 3 to 8 degrees | 0.96 to 1.83 deg |
| Error at 12 degrees | 2.0 and 3.41 deg |

Rotating a photo tilts the camera, not the truck. When scene verticals were found (4 of 56 rotated images) the
reported body roll moved by 2.94 degrees on average while the camera was tilted by up to 8 degrees, which is the
camera-roll cancellation working, with a small sample. Without scene verticals the reading follows the camera, and the
confidence is reduced accordingly.

### Known failure cases
- Front-only or three-quarter views: body edges are foreshortened, roll confidence is reduced.
- No wheels or body edge visible: no scale, overhang and height are skipped.
- Wheels hidden by shadow, tanks or skirts: the circle finder can lock onto a toolbox or a wheel arch. A tall load then reads
  as 8 m or more; any height above 8 m is reported in brackets as an unreliable scale, not as a measurement.
- A tall load makes the COCO truck mask nearly square; the vehicle-only box from the open-vocabulary detector is used for the
  view, the wheel search and the body width, and the full mask for the load top.
- Dark trucks at night: mask boundary noisy, roll may be reported with low confidence.
- Cargo that matches the body colour is sometimes merged into the truck mask, hiding overhang.
- The open-vocabulary "cargo" prompt misses the load on 37 of 101 labelled photos, which is the main cause of
  CANNOT ASSESS. A mask-based alternative was tested (cargo = mask extent above the wheel band, body = mask extent in
  the wheel band): on side views the two labelled rear-overhang positives read 0 and 55 cm while clean trucks read 0 to
  1,200 cm, so it was rejected rather than shipped. The fix is a calibrated gate camera, not a looser detector.

## Data sources and licences

All images are listed in `data/SOURCES.csv` with URL, licence and attribution.
No faces or plates are stored unblurred. No customer or personal data is used.

| Source | Licence | Use |
|---|---|---|
| Wikimedia Commons, CC BY-SA 4.0 | 137 images | test set and hit rate |
| Wikimedia Commons, CC BY-SA 3.0 | 33 images | test set and hit rate |
| Wikimedia Commons, CC BY-SA 2.0 | 31 images | test set and hit rate |
| Wikimedia Commons, CC BY 2.0 | 28 images | test set and hit rate |
| Wikimedia Commons, Public domain | 22 images | test set and hit rate |
| Wikimedia Commons, CC0 | 17 images | test set and hit rate |
| Wikimedia Commons, CC BY 4.0 | 13 images | test set and hit rate |
| Wikimedia Commons, CC BY 3.0 | 10 images | test set and hit rate |
| Wikimedia Commons, CC BY-SA 3.0 de | 4 images | test set and hit rate |
| Wikimedia Commons, CC BY-SA 3.0 it | 2 images | test set and hit rate |
| Wikimedia Commons, CC BY-SA 3.0 au | 2 images | test set and hit rate |
| Wikimedia Commons, CC BY 2.5 | 1 images | test set and hit rate |
| Wikimedia Commons, CC BY 2.1 jp | 1 images | test set and hit rate |
| Rotated copies of team-labelled level Commons photos | same licence as the source image | roll accuracy, declared synthetic |
| Ultralytics YOLO-World v2, YOLOv8s-seg weights | AGPL-3.0 | detection |

All 301 photos come from Wikimedia Commons categories (car_carrier 70, overloaded 60, flatbed 55, oversized 45, night 41, semi 30), fetched by
`tools/fetch_commons.py`, which records URL, licence and author per file. Six of them are served as demo examples with their
attribution in `app/static/examples/ATTRIBUTION.json`. No photo was taken by the team and no partner or customer data is used.

## Libraries
Ultralytics, OpenCV, NumPy, FastAPI, Uvicorn, Pillow, PyYAML. Built during the final by the team with LLM coding assistance.
