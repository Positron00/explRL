# Running the speedup and follow-up work

Plan, decisions and results: [README.md](README.md). Builds on Phase 10: [../phase10/RUN.md](../phase10/RUN.md).

## Prerequisites

As Phase 10: `pip install -e ".[dev]"` and `nbdev-export`; for live runs also `pip install -e ".[llm]"` and an API key in the environment or the git-ignored `.env.local`.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/llm_budget.ipynb` | prices, `maxCallCost`, the shared budget | ~1 s |
| `nbdev-test --n-workers 0 nbs/llm_client.ipynb` | client, cache, cap floor, timing records, retry counter (AC-4 part) | ~2 s |
| `nbdev-test --n-workers 0 nbs/llm_sched.ipynb` | longest-first order, byte-identical outputs at 1, 8, 32 processes pooled and grid by grid (AC-1), cap fallback (AC-3), timing files (AC-4) | ~20 s |
| `nbdev-test --n-workers 0 nbs/team_time.ipynb` | team rates and totals on a hand-made ledger (AC-7), Phase 8-9 rows rebuilt exactly | ~3 s |
| `nbdev-test --n-workers 0 nbs/rounds.ipynb` | rounds with `d = 0` equal the event-driven loop; concurrency; thread-timing independence (AC-5) | ~5 s |
| `nbdev-test --n-workers 0 nbs/territory.ipynb` | home ranges, `TerritoryBandit` at `beta` 0 and `inf`, home share (AC-6) | ~3 s |
| `nbdev-test --n-workers 0 nbs/followup_grid.ipynb` | grid sizes and call counts, unique keys, the frozen rules | ~2 s |
| `nbdev-test --n-workers 0 nbs/followup_report.ipynb` | summaries, report and figures on fake runs | ~5 s |
| `nbdev-test --n-workers 0 nbs/demo_followup.ipynb` | quick: every follow-up path with the fake client, same outputs pooled and grid by grid | ~3 s |
| `nbdev-test --n-workers 0` | full suite | ~70 s |

## Workloads

| Command | What it runs | Measured |
|---------|--------------|----------|
| `nbdev-test --n-workers 0 --cell-timeout 0 --flags slow nbs/demo_followup.ipynb` | B-numpy: rounds and squads, N 8-64, 320 runs | 17 s |
| `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_followup.ipynb` | D1 pilot (360 calls), then the main workload (D2 and B-LLM; D1 main only if the pilot found a level) | pilot: 243 s, $0.18; main: see README |
| `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_llm.ipynb` | Phase 10 main mode through the new scheduler (from the cache: no request, about 10 s) | byte-identical at 1, 8, 32 processes |

Live workloads use `LLM_WORKERS = 32` processes (set in the demos), share Phase 10's cache and spend ledger (`results/multiagent/llm/`), refuse to start a workload that does not fit the $150 cap with its margin (falling back to grid-by-grid priority order), and keep a per-call floor so that runs in flight cannot pass the cap. `FOLLOWUP_PLAN` must be frozen (it is: commit `c64c868`, hash `b5bea39be001`) before any live call.

Team-rate reruns of Phases 8-9 (FR-C3, into `results/multiagent/{bench,safety}/teamrate/`, never touching the confirmatory folders): `runGrid(cells, run=teamRateCell)` over `teamRateGrids()`; the check compares every original column with the saved CSVs (0 mismatches on 2026-10-12).

## Artifacts

Under `results/multiagent/followup/{quick,numpy,pilot,full}/` (gitignored): `runs.csv`, `turns.jsonl`, `timing.jsonl` (one line per call: row key, model, task, seconds, retries, cached), `metrics.json` (plan, timing summary, grids done, refused runs, pooled or not), `report.md`, figures `hard.png`, `effort.png`, `rounds.png`, `team_total.png`. Phase 10's outputs gained the team-total and round/squad columns once (reference hashes in [../phase10/RUN.md](../phase10/RUN.md)); `results/multiagent/REPORT.md` (from `nbs/demo_multiagent.ipynb`) adds team totals and the follow-up results.

## Regression

```sh
tools/phase9_baseline.sh "$WORKTREE" /tmp/explRL_p9   # on a clean worktree: identical to results/multiagent/baseline_phase9
```

## Related

- Phase 10 run guide: [../phase10/RUN.md](../phase10/RUN.md)
- Multi-agent plan: [../README.md](../README.md)
- Demo notebook: [nbs/demo_followup.ipynb](../../../nbs/demo_followup.ipynb)
