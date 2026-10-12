#!/bin/bash
# Usage: tools/phase7_demo_hashes.sh REPO_DIR OUT_DIR
# Runs demo_harness quick and slow from the checkout in REPO_DIR, with REPO_DIR first on PYTHONPATH,
# and writes OUT_DIR/{quick,full}/metrics.json, OUT_DIR/sha256.txt and OUT_DIR/timing.txt (slow wall time).
set -e
REPO="$1"; OUT="$2"
mkdir -p "$OUT/quick" "$OUT/full"
cd "$REPO"
export PYTHONPATH="$REPO"
: > "$OUT/timing.txt"
nbdev-test --n-workers 0 "nbs/demo_harness.ipynb" > /dev/null
cp "results/multiagent/demo_harness/quick/metrics.json" "$OUT/quick/metrics.json"
s=$(python -c 'import time; print(time.time())')
nbdev-test --n-workers 0 --flags slow "nbs/demo_harness.ipynb" > /dev/null
e=$(python -c 'import time; print(time.time())')
python -c "print('demo_harness slow wall_s', round($e - $s, 1))" >> "$OUT/timing.txt"
cp "results/multiagent/demo_harness/full/metrics.json" "$OUT/full/metrics.json"
(cd "$OUT" && shasum -a 256 quick/* full/* > sha256.txt)
cat "$OUT/timing.txt"
