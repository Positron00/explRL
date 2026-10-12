# Running Phase 9 (safety and mechanism design)

Design, decisions and results: [README.md](README.md). Builds on Phase 8: [../phase8/RUN.md](../phase8/RUN.md).

## Prerequisites

Python 3.9+, dev install from the repo root:

```sh
pip install -e ".[dev]"
nbdev-export
```

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/adversary.ipynb` | liar, free-rider, saboteur and lead variants (AC-3) | ~2 s |
| `nbdev-test --n-workers 0 nbs/defence.ipynb` | trust update, sanctions (revoke and reinstate), spot checks, bridge to `CommBandit` (AC-4) | ~5 s |
| `nbdev-test --n-workers 0 nbs/safety_runs.ipynb` | bridge to `runHarness` on every channel, welfare, AUC, loss pairing, timing (AC-1, AC-5) | ~10 s |
| `nbdev-test --n-workers 0 nbs/safety_grid.ipynb` | grid sizes, distinct row keys, quick grids, CSV identical for 1 and 4 workers, `confirm` (AC-6) | ~5 s |
| `nbdev-test --n-workers 0 nbs/safety_report.ipynb` | summaries and report sections | ~3 s |
| `nbdev-test --n-workers 0 nbs/safety_figures.ipynb` | figures | ~3 s |
| `nbdev-test --n-workers 0 nbs/demo_safety.ipynb` | quick demo: every grid on pilot seeds (pipeline check) | ~2 s |
| `nbdev-test --n-workers 0` | full suite (quick) | ~1 min |

## Benchmark runs

The long modes need `--cell-timeout 0` (nbdev stops a cell after 600 s by default).

| Command | What it runs | Time (8 processes) |
|---------|--------------|--------------------|
| `nbdev-test --n-workers 0 --cell-timeout 0 --flags slow nbs/demo_safety.ipynb` | H3 (360 runs, seeds 300-329) | 59 s measured |
| `nbdev-test --n-workers 0 --cell-timeout 0 --flags sweeps nbs/demo_safety.ipynb` | attack (800), defence (1 200) and monitoring (480) grids, seeds 400-409 | 570 s measured |

**H3 is run once.** Rerunning `--flags slow` reproduces the same numbers (every cell is seeded), but the result that counts is the one recorded in [README.md](README.md) against the frozen `PREREG_H3` (hash `a44617201f88`, commit `cae6b3a`). Reports can be rebuilt from `runs.csv` without rerunning (`readCSV`, `lossRows`, `confirm`, `summaries`, `report`).

## Artifacts

Under `results/multiagent/safety/{quick,h3,full}/` (gitignored):

- `runs.csv`: one row per run: cell keys, configuration, honest and team welfare, monitoring cost, sanctions, detection AUC, discoveries and free-riding index.
- `metrics.json`: mode, `PREREG_H3`, its hash, git commit, deviations, seeds, `theta`, wall time, the H3 result (h3 and quick modes) and the summary tables.
- `report.md`: the H3 table and per-size losses, then (exploratory) attacks, defences, cost and benefit, monitoring, sanctions, detection, free riding, and a figure guide.
- Figures: `attack.png`, `team.png`, `defence.png`, `cost.png`, `monitor.png`, `detection.png`, `h3.png`.

## Regression

```sh
tools/phase5_demo_hashes.sh "$PWD" /tmp/explRL_p5     # paper demos: compare with results/multiagent/baseline_phase5
tools/phase6_demo_hashes.sh "$PWD" /tmp/explRL_p6     # demo_team: identical to results/multiagent/baseline_phase6
tools/phase8_baseline.sh "$PWD" /tmp/explRL_p8        # demo_harness and demo_bench quick: identical to results/multiagent/baseline_phase8
```

Run from a copy of the working tree if you keep editing notebooks meanwhile (every `nbdev-export` rewrites the modules).

## Related

- Phase 8 benchmark: [../phase8/RUN.md](../phase8/RUN.md)
- Phase 10 LLM agents: [../phase10/RUN.md](../phase10/RUN.md)
- Phase 7 harness: [../phase7/RUN.md](../phase7/RUN.md)
- Multi-agent plan: [../README.md](../README.md)
