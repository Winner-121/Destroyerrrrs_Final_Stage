# Load Safety Gate — build plan (10 working hours, 3 people)

Product: one photo of a loaded truck at the depot gate -> GO / NO-GO with an
annotated image and three measured checks: body roll, side/rear overhang,
height. Mode: Startup (fleet / terminal is the customer). Partner angle to
mention: car-carrier trucks delivering to Toyota / BYD Royal Motors.

Hard rules (from REQUIREMENTS.txt):
- No personal data. Plates and faces blurred at ingest, before storage.
- No faked demo. Every number on screen comes from the live pipeline.
- Every data source listed with its licence in README.
- Deploy frontend + backend from this repo. Freeze commit at the deadline.
- Prototype must accept a jury photo from a phone and return a result.

Scope that is frozen: three checks, one pretrained zero-shot detector
(YOLO-World or equivalent), OpenCV geometry, threshold decision layer,
web app on Modal (HF Spaces refused: compute Spaces need PRO on the team account).
LIVE: https://amir-kuldashev--load-safety-gate-web.modal.run  (CPU, ~170 ms/image warm, one container kept warm)
Fine-tuning is optional (hour 7+).

Legend: [C] Claude does it   [H] a human must do it   [C+H] Claude drafts, human verifies/decides


## Phase 0 — Setup (hour 0–1)

[C]  Create repo layout: app/, pipeline/, data/, eval/, docs/, README.md, .gitignore.
[C]  Write requirements.txt, Dockerfile / HF Space config, GitHub Actions deploy workflow.
[C]  Write pipeline/config.yaml with class prompts and decision thresholds
     (initial values; trailer width 2.55 m used as scale).
[H]  DONE: GitHub repo, Modal account, first deploy. TODO: add GitHub Actions secrets
     MODAL_TOKEN_ID / MODAL_TOKEN_SECRET (commands given in chat) so pushes redeploy automatically.
[H]  Decide the team name and the first-slide mode ("Startup").
[C+H] Regulation thresholds for width, height, rear overhang: Claude drafts
     from public road-code sources; a human confirms the local values.


## Phase 1 — Detector and privacy stage (hour 1–3)

[C]  Privacy stage: plate/face detection + pixelation, runs first on every image.
[C]  Zero-shot detector wrapper: prompts truck, trailer body, cargo, wheel ->
     boxes/masks, with a CPU latency log.
[C]  Debug visualiser that draws detections, for quick human checks.
[H]  Collect 150 real truck photos from CC-licensed sources only
     (Open Images, Pexels, Unsplash, Roboflow Universe with stated licence,
     own photos). YouTube frames are not allowed. Log each source and licence
     in data/SOURCES.csv as you go.
[H]  Shoot or find at least 15 night / rain / low-light photos for the
     conditions subset.
[C]  Kill-point check at hour 3: report detector hit rate on the collected
     photos. If trailer + wheels are missed on most images, drop the height
     check (human decides).


## Phase 2 — Geometry and decision layer (hour 3–7)

[C]  Body roll: angle between the wheel-contact line and the trailer top edge,
     camera roll cancels; output degrees + confidence.
[C]  Overhang: cargo extent beyond trailer body, as fraction of body width,
     converted to cm with the 2.55 m standard; side and rear.
[C]  Height: cargo top vs trailer body top, scaled by body height / wheel
     diameter; flagged as low-confidence when scale objects are missing.
[C]  Decision layer: thresholds -> GO / NO-GO, checklist text, annotated image
     with the measured lines drawn on it.
[C]  Known-failure-case handling: no truck found, front-only view, truck too
     small in frame -> explicit "cannot assess" instead of a guess.
[H]  Label the test set (80–100 photos): for each image mark roll (ok /
     tilted, approximate degrees if visible), side overhang (yes/no),
     rear overhang (yes/no), over-height (yes/no). Claude provides the
     labelling sheet template; a human fills it, because this is the
     ground truth the jury will ask about.
[H]  Toy-truck tilt rig (optional): photos at known angles 0/3/5/8/12 deg for
     the roll-accuracy table. Record the real angle per photo.


## Phase 3 — Evaluation (hour 5–8, overlaps phase 2)

[C]  eval/run_eval.py: precision / recall per check, MAE of roll on the rig
     subset, latency per image on the deployed CPU, cost per inspection.
[C]  Separate numbers for the night / rain subset.
[C]  Failure-case gallery (worst 10 images with reason) for the deck.
[H]  Review the metrics. Any check without a measured number is removed from
     the deck, not estimated.
[C]  Optional (hour 7+, only if everything above is green): fine-tune YOLO-n
     on the labelled set and re-run eval; keep whichever model scores higher.


## Phase 4 — App and deployment (hour 3–8, Person C)

[C]  Web app: phone-friendly upload page, result page with annotated image,
     checklist, GO / NO-GO, latency shown. Example images button that runs
     the real pipeline (not cached results).
[C]  Deploy workflow: push to main -> build -> HF Space. Deployment history
     visible in Actions.
[H]  Hour 6: open the public link on two different phones, upload a fresh
     photo of a truck, confirm a result comes back. Report problems to Claude.
[H]  Hour 8: record a backup video of the full demo flow on a phone.


## Phase 5 — Deck, README, submission (hour 7–10)

[C]  README: what it is, how to run locally, how it is deployed, architecture
     diagram, data sources with licences (from data/SOURCES.csv), metrics
     table, known failure cases, cost model.
[C]  Deck draft (PDF or pptx), 7-minute split: problem & user 1 min, live
     demo 2 min, technology 2 min, budget & ROI 1.5 min, next steps 0.5 min.
     Every number sourced from eval output.
[C+H] Budget and ROI slide: Claude builds the model; a human supplies or
     confirms the assumptions (fleet size, rollover/fine/cargo-loss figures,
     salaries, hosting price). Every assumption is written on the slide.
[H]  Decide who presents which part. Rehearse twice with a timer; stop at 7:00.
[H]  Prepare answers for: "relative to what is the tilt measured?",
     "what happens at night?", "what breaks it?", "who pays and why now?".
[H]  Freeze: final commit, redeploy that commit, submit prototype link, deck
     and repo link on the team dashboard. Do not push after the deadline.


## Kill points (human decides, Claude reports)

Hour 3  Detector weak on trailers/wheels     -> drop height, keep roll + overhang
Hour 7  Fine-tune not started                -> skip it, ship pretrained + own eval
Hour 8  Feature not working                  -> remove it from app and deck
Hour 8  No new features after this point


## Must not slip

1. Public link works from a phone with a new photo by hour 6.
2. Every number on the deck comes from eval/ output.
3. data/SOURCES.csv complete with licences before submission.
4. Plates blurred in every stored and displayed image.
