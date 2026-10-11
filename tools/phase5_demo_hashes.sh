#!/bin/bash
# Usage: tools/phase5_demo_hashes.sh REPO_DIR OUT_DIR
# Runs the three paper demos (quick and slow) from the checkout in REPO_DIR, with REPO_DIR first on PYTHONPATH,
# and writes OUT_DIR/{quick,full}/<demo>_metrics.json, OUT_DIR/sha256.txt and OUT_DIR/timing.txt (slow wall times).
set -e
REPO="$1"; OUT="$2"
mkdir -p "$OUT/quick" "$OUT/full"
cd "$REPO"
export PYTHONPATH="$REPO"
: > "$OUT/timing.txt"
for demo in demo demo_prestructured demo_circuit; do
  nbdev-test --n-workers 0 "nbs/${demo}.ipynb" > /dev/null
  cp "results/${demo}/quick/metrics.json" "$OUT/quick/${demo}_metrics.json"
  s=$(python -c 'import time; print(time.time())')
  nbdev-test --n-workers 0 --flags slow "nbs/${demo}.ipynb" > /dev/null
  e=$(python -c 'import time; print(time.time())')
  python -c "print('${demo} slow wall_s', round($e - $s, 1))" >> "$OUT/timing.txt"
  cp "results/${demo}/full/metrics.json" "$OUT/full/${demo}_metrics.json"
done
(cd "$OUT" && shasum -a 256 quick/* full/* > sha256.txt)
cat "$OUT/timing.txt"
