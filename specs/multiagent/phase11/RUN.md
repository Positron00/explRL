# Running Phase 11 (the clue board)

Plan, decisions and results: [README.md](README.md). Builds on Phase 10 and the follow-ups: [../phase10/RUN.md](../phase10/RUN.md), [../speedup/RUN.md](../speedup/RUN.md).

## Prerequisites

As Phase 10: `pip install -e ".[dev]"` and `nbdev-export`; for live runs also `pip install -e ".[llm]"` and an API key in the environment or the git-ignored `.env.local`.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/cluetask.ipynb` | clues: unique answer, every clue needed, feasible prime sets (AC-2) | ~1 s |
| `nbdev-test --n-workers 0 nbs/clueboard.ipynb` | dealing guarantee, actions, share and solve logs, false residues, reward schemes (AC-3) | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_agents.ipynb` | channels, `known`, rule agents and the liar (AC-4) | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_text.ipynb` | rules text, observation, parsing, posting (AC-5) | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_runs.ipynb` | metrics on hand-made runs, numpy and fake-client runs, determinism | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_grid.ipynb` | grid sizes and call counts, the frozen settings rule, `CLUE_PLAN` | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_train.ipynb` | batched episodes, exports round-trip, teacher solves (AC-7) | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_report.ipynb` | summaries on synthetic and fake runs, report and figures | ~1 s |
| `nbdev-test --n-workers 0 nbs/demo_clue.ipynb` | quick: every clue path with the fake client, identical at 1 and 8 processes, pooled and grid by grid; key scan (AC-6) | ~2 s |
| `nbdev-test --n-workers 0` | full suite (also passes without the `anthropic` package) | ~100 s |

## Workloads

| Command | What it runs | Measured |
|---------|--------------|----------|
| `nbdev-test --n-workers 0 --cell-timeout 0 --flags slow nbs/demo_clue.ipynb` | the numpy sweep (22 400 rule-agent runs) and the frozen settings rule | 242 s on 8 processes |
| `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_clue.ipynb` | pilot (540 calls), then the main workload (main, framing, liar and the 60 rule-agent cells; effort and scale only with `OPTIONAL = True`) | pilot: 378 s, $0.13; main: see README |

Live workloads use `LLM_WORKERS = 32` processes, share Phase 10's cache and spend ledger (`results/multiagent/llm/`) under the one $150 cap, and refuse a workload that does not fit the cap (grid by grid in priority order instead). The main section asserts that `CLUE_PLAN` is frozen (commit `20a60e8`, hash `050a825d7bae`); the pilot section asserts that `CLUE_SETTINGS` matches the sweep's choice. After the first live run, `metrics.json` and `timing.jsonl` are copied to `metrics_live.json` and `timing_live.jsonl`, so a later cached rerun cannot overwrite the live timing.

## Artifacts

Under `results/multiagent/clue/{quick,sweep,pilot,full}/` (gitignored): `runs.csv`, `turns.jsonl` (per turn: key, agent, time, observation, response, reward; the input of `clue_train.exportTrajectories`), `timing.jsonl`, `metrics.json` (plan, timing summary, grids done, refused runs), `report.md`, figures `clue_welfare.png`, `clue_info.png`, `clue_numpy.png`, `clue_arms.png`.

## Regression

```sh
tools/phase9_baseline.sh "$WORKTREE" /tmp/explRL_p9   # on a worktree of the code: identical to results/multiagent/baseline_phase9
```

Phase 10 and follow-up full workloads rerun from the response cache only (fake client on a miss, so no request can be made) give byte-identical `runs.csv` and `turns.jsonl` (checked 2026-10-12 against the T1 reference sha256: Phase 10 `377dea80...`, `3eed3aae...`; follow-up `9d5f59b8...`, `0bc69c9e...`).

## Related

- Multi-agent plan: [../README.md](../README.md)
- Demo notebook: [nbs/demo_clue.ipynb](../../../nbs/demo_clue.ipynb)
- Training package: [nbs/clue_train.ipynb](../../../nbs/clue_train.ipynb)
