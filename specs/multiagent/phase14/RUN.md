# Running Phase 14 (trust information and team-size scaling)

Plan, decisions and results: [README.md](README.md). Builds on Phase 13: [../phase13/RUN.md](../phase13/RUN.md).

Status 2026-10-17: code done (T1, T2) and the numpy forecast frozen (T4); the live runs are next (T3, T5).

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command; none needs a network, a key, `anthropic` or `torch`:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/clue_fix.ipynb` | the private record and the public check; Phase 13 option values byte-identical (hash over rules, schema, rows and logs) (AC-2) | ~3 s |
| `nbdev-test --n-workers 0 nbs/clue_roll.ipynb` | rollout rows and turn logs equal `runClue`'s with `record='private'` and `check='public'`, with and without a liar | ~3 s |
| `nbdev-test --n-workers 0 nbs/scale_grid.ipynb` | grid sizes, liar counts (N // 4), shared seeds, cached cells, call estimates, the cost rule (AC-3) | ~2 s |
| `nbdev-test --n-workers 0 nbs/scale_report.ipynb` | loss recovered, the publicity and cost effects and their difference, per-N effects, on synthetic rows; Phase 13's numbers reproduced | ~3 s |
| `nbdev-test --n-workers 0 nbs/demo_trust.ipynb` | quick: both parts with the fake client, identical at 1 and 8 processes | ~15 s |
| `nbdev-test --n-workers 0` | full suite | ~80 s |

## Runs, in order

| Step | Where | Command | Cost |
|------|-------|---------|------|
| T4 numpy forecast | Mac | `python tools/scale_forecast.py run $PWD` (14 s, byte-identical on rerun); commit `specs/multiagent/phase14/scale_predictions.json` | done 2026-10-17 (`ec1bcb3`) |
| T3 freeze | Mac | `TRUST_PLAN['frozen'] = True` in `nbs/scale_grid.ipynb`, export, commit; record the commit and `coopHash(TRUST_PLAN)` in the README | none |
| T3 Part A and T5 pilot | Mac | `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_trust.ipynb`: runs Part A's main run and then the Part B pilot (allowed: the forecast is committed); the Part B main section stops until `SCALE_PLAN` is frozen. The pilot prints the invalid rate at N = 32, tokens and cost per call, the projected main cost and the cost rule's verdict | about $1.70 + $1-2 |
| T5 freeze | Mac | if the pilot's invalid rate is under 5% and the verdict is `run` or `cut`: `SCALE_PLAN['frozen'] = True`, export, commit; record the commit, hash and verdict in the README (a `stop` verdict: ask) | none |
| T5 main and reruns | Mac | the same command: Part B main (only the cells the cost rule allows; it re-checks the pilot's band), then the cached reruns of both parts (byte-identical, free); then `python tools/scale_forecast.py score $PWD results/multiagent/scale/full/runs.csv` | up to $40 |

## Artifacts

- `results/multiagent/trust/{quick,full}/`: `runs.csv`, `turns.jsonl`, `timing.jsonl`, `metrics.json` (and `_live` copies), `report.md`, `trust.png`.
- `results/multiagent/scale/{quick,pilot,full}/`: the same files, `scale.png`.
- `results/multiagent/forecast/scale_numpy.json`, `scale_score.json`; `specs/multiagent/phase14/scale_predictions.json`.
