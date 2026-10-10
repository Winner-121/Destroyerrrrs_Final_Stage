# Defence deck outline — 7 minutes, numbers only from eval/out/metrics.json

1. Title (0:00–0:15). Team, "Mode: Startup", one line: photo at the gate → GO / NO-GO.
2. Problem and user (0:15–1:00). Rollover, lost cargo, fines; checked by eye or not at all today.
   User: gate operator / dispatcher. Payer: fleet owner or terminal. Partner angle: car-carriers into Royal Motors yards.
3. Live demo (1:00–3:00). Open the public URL on a phone. Jury photo first, then one example.
   Point at: blurred plate, the two green lines (roll), red overhang line, verdict banner, latency.
4. Architecture (3:00–3:45). Pipeline diagram: detector → mask → privacy → geometry → thresholds.
   "Relative to what?" slide: both lines live in the same image, camera roll cancels. Scale = 2.55 m body / 1.05 m wheel.
5. Quality (3:45–4:30). Metrics table per check, night/rain row, roll MAE on the rig, latency and cost per inspection
   on CPU. Failure-case gallery with three images and why.
6. Replication test (4:30–5:00). What a weekend team gets: a detector. What they do not get: the geometry,
   the road-code decision layer, the labelled evaluation set, the gate-camera product shape.
7. Budget and ROI (5:00–6:30). Pilot cost (people, hosting, cameras, labelling) vs avoided losses.
   Every assumption printed on the slide. Payback period.
8. Next steps (6:30–7:00). Fixed calibrated gate camera, 10-s video mode, fine-tuned detector, open-door / loose-strap classes,
   integration with the weighbridge software.

Backup: recorded demo video on the presenter's phone and laptop.
