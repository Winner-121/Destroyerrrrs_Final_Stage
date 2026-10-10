# Labelling guide (human task)

Put images in `data/test/` (normal conditions), `data/night_rain/` (low light, rain, fog),
`data/rig/` (toy-truck rig at known angles). Add one row per image to `data/labels.csv`
and one row per image to `data/SOURCES.csv`.

## labels.csv columns
- filename: exact file name.
- view: side | rear | three_quarter | other.
- roll_label: ok if the body looks level relative to the wheels; tilted if it visibly leans.
- roll_deg_true: only for rig photos, the angle you set on the board. Leave blank otherwise.
- side_overhang: yes if cargo sticks out past the body sides (seen from rear / three-quarter); no; unclear.
- rear_overhang: yes if cargo sticks out past the back of the trailer (seen from side); no; unclear.
- over_height: yes if cargo is clearly taller than a normal box trailer / would hit a 4 m bridge; no; unclear.
- notes: anything odd (night, rain, partial truck, front-only view).

"unclear" rows are skipped in that metric, so use it honestly rather than guessing.

## SOURCES.csv columns
- filename, source_url, dataset_or_site (Open Images / Pexels / Unsplash / Roboflow name / own photo),
  licence (e.g. CC BY 2.0, Pexels License, Unsplash License, CC BY 4.0), attribution (author if the licence requires it),
  subset (test / night_rain / rig / raw), notes.

Allowed sources: Open Images, COCO, Roboflow Universe datasets with a stated licence, Pexels, Unsplash, own photos.
Not allowed: YouTube frames, Google Images results, anything without a stated licence.
Plates and people are blurred automatically by the pipeline, but prefer images without visible people.
