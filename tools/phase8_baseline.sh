#!/bin/bash
# Usage: tools/phase8_baseline.sh REPO_DIR OUT_DIR
# Records, from the checkout in REPO_DIR (REPO_DIR first on PYTHONPATH), the demo_harness metrics.json hashes
# (quick and full, via phase7_demo_hashes.sh) and the hash of demo_bench's quick runs.csv, in OUT_DIR/sha256.txt.
set -e
REPO="$1"; OUT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
bash "$HERE/phase7_demo_hashes.sh" "$REPO" "$OUT/harness" > /dev/null
cd "$REPO"
export PYTHONPATH="$REPO"
nbdev-test --n-workers 0 "nbs/demo_bench.ipynb" > /dev/null
mkdir -p "$OUT/bench"
cp "results/multiagent/bench/quick/runs.csv" "$OUT/bench/quick_runs.csv"
(cd "$OUT" && shasum -a 256 harness/quick/metrics.json harness/full/metrics.json bench/quick_runs.csv > sha256.txt)
cat "$OUT/sha256.txt"
