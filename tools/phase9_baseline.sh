#!/bin/bash
# Usage: tools/phase9_baseline.sh REPO_DIR OUT_DIR
# Records, from the checkout in REPO_DIR (REPO_DIR first on PYTHONPATH), the Phase 8 baseline (demo_harness metrics
# and demo_bench quick runs.csv, via phase8_baseline.sh) and the hash of demo_safety's quick runs.csv.
set -e
REPO="$1"; OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
bash "$HERE/phase8_baseline.sh" "$REPO" "$OUT/p8" > /dev/null
cd "$REPO"
export PYTHONPATH="$REPO"
nbdev-test --n-workers 0 "nbs/demo_safety.ipynb" > /dev/null
mkdir -p "$OUT/safety"
cp "results/multiagent/safety/quick/runs.csv" "$OUT/safety/quick_runs.csv"
(cd "$OUT" && { cat p8/sha256.txt | sed 's#  #  p8/#'; shasum -a 256 safety/quick_runs.csv; } > sha256.txt)
cat "$OUT/sha256.txt"
