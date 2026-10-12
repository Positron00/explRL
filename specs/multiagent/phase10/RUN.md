# Running Phase 10 (language-model agents, Claude API)

Design, decisions and results: [README.md](README.md). Builds on Phase 9: [../phase9/RUN.md](../phase9/RUN.md).

## Prerequisites

Python 3.9+, dev install from the repo root:

```sh
pip install -e ".[dev]"
nbdev-export
```

The normal tests and the quick demo need nothing else: no `anthropic` package, no network, no credentials. Live runs also need the optional SDK and an API key:

```sh
pip install -e ".[llm]"                      # the anthropic SDK
# then either export ANTHROPIC_API_KEY in your shell, or put it in the git-ignored .env.local at the repo root:
#   ANTHROPIC_API_KEY=sk-ant-...
```

`.env.local` is ignored by git (`.gitignore`); the live client copies it into the environment only if the variable is not already set, and never logs, caches or writes the key. Note that a repo inside a synced folder (Dropbox) syncs `.env.local` too.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/llm_client.ipynb` | request shape, response cache (first writer wins, charge of the call made), budget and run reservation, `.env.local` loader, imports without `anthropic`, no key-like strings (AC-2) | ~2 s |
| `nbdev-test --n-workers 0 nbs/llm_fake.ipynb` | `FakeClient` scripts; `fakeReply` gives parseable actions for both tasks and beliefs | ~2 s |
| `nbdev-test --n-workers 0 nbs/taskboard.ipynb` | puzzles and checker, schedule, scoring, penalties, reward schemes, social optimum (AC-4) | ~2 s |
| `nbdev-test --n-workers 0 nbs/board_agents.ipynb` | claim board, lead, numpy board agent; channels cut duplicate work | ~3 s |
| `nbdev-test --n-workers 0 nbs/llm_env.ipynb` | text foraging: rules, observation, parsing, same ledger as direct moves, channels (AC-3) | ~2 s |
| `nbdev-test --n-workers 0 nbs/llm_board.ipynb` | text board: rules, observation, parsing, claims | ~2 s |
| `nbdev-test --n-workers 0 nbs/llm_agent.ipynb` | members, turn budgets, memory settings, append-only prompts, beliefs, liars (AC-5) | ~3 s |
| `nbdev-test --n-workers 0 nbs/llm_runs.ipynb` | runs, rows, persistence, equal budget, reservation, cached rerun identical | ~3 s |
| `nbdev-test --n-workers 0 nbs/llm_compare.ipynb` | numpy runs, Spearman, `compareNumpy` recovers a known rho (AC-6) | ~5 s |
| `nbdev-test --n-workers 0 nbs/llm_grid.ipynb` | grid sizes and call counts, seeds, 5 s stays, plan hash, quick grid (AC-6) | ~2 s |
| `nbdev-test --n-workers 0 nbs/llm_report.ipynb` | summaries and report provenance | ~3 s |
| `nbdev-test --n-workers 0 nbs/llm_figures.ipynb` | figures | ~3 s |
| `nbdev-test --n-workers 0 nbs/demo_llm.ipynb` | quick demo with the fake client: every grid, all artifacts, under 30 s, same CSV for 1 and 8 workers, no key-like strings (AC-6) | ~3 s |
| `nbdev-test --n-workers 0 nbs/demo_multiagent.ipynb` | the plan's write-up from saved results (skips if they are missing) | ~3 s |
| `nbdev-test --n-workers 0` | full suite | ~1 min |

## Live runs

Live sections make API calls only with `EXPLRL_LLM_LIVE=1`; every request is checked against the $150 cap (`CAP` in the demo; shared ledger `results/multiagent/llm/spend.jsonl`) and cached (`results/multiagent/llm/cache/`). The long modes need `--cell-timeout 0`.

| Command | What it runs | Measured |
|---------|--------------|----------|
| `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm_pilot nbs/demo_llm.ipynb` | the pilot (stage 1, then stages 1 and 2) | round 2: 695 calls, $1.04, about 15 min |
| `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_llm.ipynb` | main, Sonnet, equal-budget, liar, framing, memory and persistence grids, then the numpy cells | 47 988 calls (45 809 live), $31.94 charged, 10.6 h (8 processes) |

**Reruns are free and exact only with the cache.** With `results/multiagent/llm/cache/` present, rerunning either mode sends no request (the ledger does not grow), takes about 10 s for the full mode, and writes byte-identical `runs.csv` and `turns.jsonl` (AC-9, checked twice). Without the cache, live reruns differ (these models take no sampling parameters). The cache (about 50 000 small JSON files) is gitignored; keep a copy to reproduce the results. The results recorded in [README.md](README.md) are against the frozen `ANALYSIS_PLAN` (hash `83df7591d1de`, commit `ce9d661`).

**Reference outputs (AC-9).** On 2026-10-12 the full outputs were regenerated once from the cache with the team-total columns and the round/squad config columns of the [speedup plan](../speedup/README.md) (no request; every earlier column value-identical; `turns.jsonl` unchanged). Reference sha256: `runs.csv` `377dea800560a7955f1211b2a7e9cef6bc31f041807966944226916029735d3d`, `turns.jsonl` `3eed3aae5eac1596f2c9152a366d2dd3c6e6cda10cc99a04366680e53ae11a01`. The file before that change is kept as `full/runs_before_teamrate.csv` (`runs.csv` sha256 then: `da2fe8623b0978a9c1f04e6bb09ef16e2073d90924f536941a5e41c76842de46`).

## Artifacts

Under `results/multiagent/llm/{quick,pilot,pilot_probe,full}/` (gitignored):

- `runs.csv`: one row per run (per episode in the persistence arm): cell keys, configuration, welfare, honest welfare, task metrics, invalid actions, refusals, `max_tokens` stops, report and exploration shares, calls, tokens and cost.
- `turns.jsonl`: one line per API call: row key, episode, agent, time, observation, response text, parsed action, validity, reward, report, exploration flag, stop reason, refusal, usage and cost.
- `metrics.json`: mode, the analysis plan and its hash, git commit, models, effort, prices with their date, cap, cost, total spend, calls and cache hits, wall time, grids done, the estimate per grid and the summary tables. `full/metrics_live.json` and `full/report_live.md` keep the live run's own record (cache hits 2 173, wall time 38 136 s).
- `report.md`: provenance, then the main table, harness benefit per model, model-size contrast, numpy vs LLM, equal budget, arms, and the interface, token and cost table.
- Figures: `welfare.png`, `model_size.png`, `tokens.png`, `numpy_vs_llm.png`, `arms.png`.

## Regression

```sh
tools/phase9_baseline.sh "$WORKTREE" /tmp/explRL_p9   # Phase 8 baselines and demo_safety quick: identical to results/multiagent/baseline_phase9
```

Run it on a clean worktree (`git worktree add --detach <dir> HEAD`): every `nbdev-export` rewrites the modules' cell-id comments.

## Related

- Phase 9 run guide: [../phase9/RUN.md](../phase9/RUN.md)
- Multi-agent plan: [../README.md](../README.md)
- Demo notebook: [nbs/demo_llm.ipynb](../../../nbs/demo_llm.ipynb)
- The plan's write-up (Phases 8-10, from saved results, no rerun): `nbdev-test --n-workers 0 nbs/demo_multiagent.ipynb` writes [results/multiagent/REPORT.md](../../../results/multiagent/REPORT.md) and `results/multiagent/report/*.png` (it skips if the saved results are missing)
