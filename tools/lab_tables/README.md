# tools/lab_tables: table experiments toolkit
Run everything from the repo root. Work files go to `tools/lab_tables/work/` (git-ignore it).
- `score_tables.py ENGINEDIR TAG`: renders tables_images in Standard / Compact / Large, compares with `exam/tables_images_exam/theme_*`, prints pages, exact pages, diff pixels per theme and the total (this is the metric used by the reviewer).
- `sweep.py KR_X=a,b KR_Y=c,d`: grid sweep of the experiment env hooks (see below).
- `run_lab.sh`: re-measures the device scale of every table (template matching, +/-0.01) and prints the scale-model fit. Needs numpy and opencv-python (`pip install opencv-python-headless`).
- `fit_scale_model.py`, `features.py`: scale-model fit / per-table features from the measurements.
Experiment env hooks inside `kindle_render/page.py` (documented, to be turned into named config fields once settled): `KR_PAD` (column pad, em), `KR_CAP` (cap for scale and widths, em), `KR_CAPW` (separate cap for widths), `KR_LP0` / `KR_LPM` (left cell padding of first / other columns, em), `KR_RPF` (row pad factor, default 0.28), `KR_TBL_SCALE` (force a scale), `KR_TBL_LOG=path` (append one JSON line per table).
