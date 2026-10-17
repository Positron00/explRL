# Design: Phase 14 (high and low level)

Phase 14 is small, so one design document covers both levels.

## Components

| Module | New / changed | Contents |
|---|---|---|
| `nbs/clue_fix.ipynb` -> `explRL/clue_fix.py` | changed | `trackRecord(a, board, viewer=None)` (with `viewer`: only subtasks the viewer solved); the public check: the result line for every agent and a shared checked set; the two rules sentences |
| `nbs/clue_text.ipynb` -> `explRL/clue_text.py` | changed | `record` and `check` accept `'public'` / `'private'` (booleans keep Phase 13 behaviour); `known(...)` gets the shared checked set under a public check |
| `nbs/fix_grid.ipynb` -> `explRL/fix_grid.py` | changed (or a new `trust_grid` if it would pass 200 lines) | `FIX_ARMS` gains `recordPrivate`, `verifyPublic`; `trustGrid`, `scaleGrid`, `scalePilotGrid`, `TRUST_PLAN`, `SCALE_PLAN` |
| `nbs/fix_report.ipynb` or new `nbs/scale_report.ipynb` | changed / new | `trustSummaries` (publicity and cost effects), `scaleSummaries` (per-N effects and trends) |
| `tools/scale_forecast.py` | new | the numpy forecast of the baseline trends with N |
| `nbs/demo_trust.ipynb` | new | quick (fake client); Part A main; Part B pilot and main; cached reruns (`llm`) |
| `nbs/demo_multiagent.ipynb` | changed | a Phase 14 section in `REPORT.md` |

## The two new settings (`clue_fix`, `clue_text`)

**Private record.** `trackRecord(a, board, viewer)` = (true, checked) over a's shares (`board.shareLog`) for subtasks with `solvedBy == viewer`. `fixBoard` passes the viewing agent when `env.record == 'private'`. The rules sentence says "counted over subtasks you solved yourself". `record=True` keeps the Phase 13 sentence and counts (byte-identical).

**Public check.** With `env.check == 'public'`, a valid check stores its result in a shared dict `env.checkedAll[(k, j, r)] = ok` and queues the line `Checked by agent {i}: T{k} x mod {p} = {r} (from agent {src}) is {true|false}.` for every agent's next observation (the checker gets its Phase 13 line instead). `known(i, ...)` for every agent uses `checkedAll` (merged with nothing else; private checks do not exist in this arm). Checks cost the checker's turn as in Phase 13.

Both keep the Phase 13 schema rules: `check` adds `'check'` to the action enum whether private or public.

## Grids and plans (`fix_grid`)

```python
FIX_ARMS.update(recordPrivate=dict(record='private'), verifyPublic=dict(check='public'))
def trustGrid(seeds=FIX_SEEDS)        # study 'trustA': the 2 new arms x {clean, liar} x N 4 x seeds 900-909
def scaleGrid(seeds=range(900, 905))  # study 'scaleB': N in (8, 16, 32); clean: baseline, request; nLiar = N // 4: baseline, record
def scalePilotGrid()                  # N 32, baseline, clean and liar, seed 900
TRUST_PLAN, SCALE_PLAN                # frozen before their main runs (hashes recorded in the README)
```

Part A's `record`, `verify` and `baseline` rows come from Phase 13 (`results/multiagent/fix/full/runs.csv`), joined by seed. Part B's N = 8 clean `baseline` and `request` cells equal Phase 13's (same request keys, so cached).

## Analysis

- `trustSummaries(rows13, rows14)`: per arm, loss recovered (`lossRecovered`, as Phase 13) and no-liar cost. Publicity effect = (LR(`record`) + LR(`verifyPublic`)) / 2 - (LR(`recordPrivate`) + LR(`verify`)) / 2, each LR computed from the arms' mean honest losses; its CI by bootstrap over seeds, resampling the same seeds for every arm. Cost effect = (LR(`record`) + LR(`recordPrivate`)) / 2 - (LR(`verify`) + LR(`verifyPublic`)) / 2, likewise. Holm over the two new arms' tests against the baseline.
- `scaleSummaries(rows)`: per N, `gapClosed` for `request` (pooled share, ceiling 1) and `lossRecovered` for `record`; Holm over N within each arm; the baseline's pooled share and honest loss per N.
- Forecast scoring: the numpy sign of (N 32 minus N 8) for clean pooled share and honest loss, against the Haiku baseline's sign (bootstrap over seeds), as `tools/forecast_score.py`'s rule.

## The numpy forecast (`tools/scale_forecast.py`)

`runClueNumpy` (Phase 11) with `clueCell`-style configs: blackboard, N in (4, 8, 16, 32, 64), `nLiar` 0 and N // 4, 40 turns, seeds 2000-2019 (not the LLM seeds; the forecast is about trends, not boards). Writes `results/multiagent/forecast/scale_numpy.json` and `specs/multiagent/phase14/scale_predictions.json`.
