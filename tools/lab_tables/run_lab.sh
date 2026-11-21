#!/bin/sh
# Re-measure the device table scales and refit the scale model. Run from the repo root.
# 1) render tables_images in the 3 themes with table logging  2) measure device scale per table by template matching
# 3) fit/evaluate the scale model (fit_scale_model.py prints the best pad/cap and per-table errors).
set -e
W=tools/lab_tables/work; mkdir -p $W
run() { TH=$1; SZ=$2; P=$3; X0=$4; R=$5
  rm -f $W/log_$TH.jsonl
  KR_TBL_LOG=$W/log_$TH.jsonl PYTHONPATH=. python3 -m kindle_render epub exam/tables_images_exam/kindle_tables_images_exam.epub $W/out_$TH \
    --pages 200 --size26 $SZ --x0 $X0 --right $R --pitch $P --top 168 --page-bottom 2203 >/dev/null
  python3 tools/lab_tables/measure_scale.py $TH
}
run Standard 2880 68 79 1001
run Compact 2496 53 39 1041
run Large 3200 82 131 949
python3 tools/lab_tables/fit_scale_model.py
