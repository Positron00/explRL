# Running Phase 8 (benchmark and eval suite)

Design, decisions and results: [README.md](README.md). Builds on Phase 7: [../phase7/RUN.md](../phase7/RUN.md).

## Prerequisites

Python 3.9+, dev install from the repo root:

```sh
pip install -e ".[dev]"
nbdev-export
```

## Tests

From the repo root (`.venv/bin` first on `PATH`):

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/bench_metrics.ipynb` | recovery, beliefs, goal spread, discoveries (and agreement with `Credit`), free riding, find, overlap and follow times (AC-3) | ~5 s |
| `nbdev-test --n-workers 0 nbs/bench_stats.ipynb` | bootstrap, sign-flip, Holm, effect size, scaling fit (AC-4) | ~2 s |
| `nbdev-test --n-workers 0 nbs/episodes.ipynb` | `LevelBandit`, `runEpisodes`, persistence arms (AC-6) | ~3 s |
| `nbdev-test --n-workers 0 nbs/bench_grid.ipynb` | grid sizes, quick grid, CSV identical for 1 and 4 workers, every runner path, `confirm` (AC-5, AC-7) | ~5 s |
| `nbdev-test --n-workers 0 nbs/bench_report.ipynb` | summaries and report sections | ~5 s |
| `nbdev-test --n-workers 0 nbs/bench_figures.ipynb` | figures | ~5 s |
| `nbdev-test --n-workers 0 nbs/demo_bench.ipynb` | quick demo: pilot seeds, budgets / 10, every path (pipeline check) | ~4 s |
| `nbdev-test --n-workers 0` | full suite (quick) | ~40 s |

## Benchmark runs

The long modes need `--cell-timeout 0`: nbdev stops any cell after 600 s by default, and the sweeps cell takes longer.

| Command | What it runs | Time (8 processes) |
|---------|--------------|--------------------|
| `nbdev-test --n-workers 0 --cell-timeout 0 --flags slow nbs/demo_bench.ipynb` | main grid (1 680 runs, confirmatory seeds 100-129) and the pre-registered tests | 280 s measured |
| `nbdev-test --n-workers 0 --cell-timeout 0 --flags sweeps nbs/demo_bench.ipynb` | side sweeps (1 350 runs) and study B (160 sequences of 12 episodes), seeds 200-209 | 690 s measured |

**The confirmatory run is done once.** Rerunning `--flags slow` reproduces the same numbers (every cell is seeded), but the result that counts is the one recorded in [README.md](README.md) against the frozen `PREREG` (hash `8a59293847ae`, commit `e98e238`). A report can be rebuilt from `runs.csv` without rerunning anything (`readCSV`, `confirm`, `report`).

## Artifacts

Under `results/multiagent/bench/{quick,full,sweeps}/` (gitignored):

- `runs.csv`: one row per run (one per episode for study B): cell keys, configuration, Phase 7 metrics and Phase 8 metrics.
- `metrics.json`: mode, `PREREG`, its hash, git commit, wall time, confirmatory results, scaling slopes, side-sweep table, team-optimal `cUCB`, study B summary.
- `report.md`: run settings and seeds, confirmatory table, per-size estimates, scaling slopes, side sweeps, circuit teams, studies A and B (all but the confirmatory table labelled exploratory), figure guide.
- Figures: `scaling.png`, `confirmatory.png`, `recovery.png`, `beliefs.png`, `secondary.png`, `sweeps.png`, `studyB.png`.

## Regression

```sh
tools/phase5_demo_hashes.sh "$PWD" /tmp/explRL_p5     # paper demos: compare with results/multiagent/baseline_phase5
tools/phase6_demo_hashes.sh "$PWD" /tmp/explRL_p6     # demo_team: identical to results/multiagent/baseline_phase6
tools/phase7_demo_hashes.sh "$PWD" /tmp/explRL_p7     # demo_harness: differs from baseline_phase7 only in IFD fields
```

Run from a copy of the working tree if you keep editing notebooks meanwhile (every `nbdev-export` rewrites the modules).

## Related

- Phase 7 harness: [../phase7/RUN.md](../phase7/RUN.md)
- Phase 9 safety: [../phase9/RUN.md](../phase9/RUN.md)
- Phase 6 team world: [../phase6/RUN.md](../phase6/RUN.md)
- Multi-agent plan: [../README.md](../README.md)
