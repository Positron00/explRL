# Running Phase 13 (from diagnosis to fixes)

Plan, decisions and results: [README.md](README.md). Builds on Phase 12: [../phase12/RUN.md](../phase12/RUN.md).

Status 2026-10-15: code done (T1-T4, T8 and the evaluation code of T10); `RL13_PLAN` frozen at `962c4e1` (hash `3e50a4002c7b`); the live runs are next (T5 pilots on the Mac, the five Track B runs on Colab).

## Prerequisites

As Phase 12: the project environment `.venv` for offline tests and Track A (with the `[llm]` extra and the API key in the git-ignored `.env.local` for live runs); `.venv-train` for model work on the Mac; Colab (A100) for Track B, which installs the package from GitHub, so push first.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command; none needs a network, a key, `anthropic` or `torch`:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/clue_fix.ipynb` | the four clue-board options: defaults byte-identical (hashed against the pre-change code), schema, `ask`, `table`, `record`, `check`, hints (AC-2) | ~2 s |
| `nbdev-test --n-workers 0 nbs/clue_roll.ipynb` | rollout rows and turn logs equal `runClue`'s with each option on, with and without a liar | ~3 s |
| `nbdev-test --n-workers 0 nbs/hidden_profile.ipynb` | the vote: fact totals over 1 000 seeds, `lone`, scripted teams, `factsFirst`, the table, parsing, shuffling (AC-3) | ~3 s |
| `nbdev-test --n-workers 0 nbs/profile_runs.ipynb` | `runProfile` end to end with the fake client; a cached rerun byte-identical with no calls | ~3 s |
| `nbdev-test --n-workers 0 nbs/fix_grid.ipynb` | grid sizes and call estimates; baseline cells send the same requests as Phase 11's (cache reuse) | ~2 s |
| `nbdev-test --n-workers 0 nbs/fix_report.ipynb` | gap closed, loss recovered, no-liar cost, Holm, on synthetic rows; `fixLogMetrics` on hand-made logs (AC-5) | ~2 s |
| `nbdev-test --n-workers 0 nbs/rl_adv.ipynb` | turn-level advantages, rewards-to-go with late credit, the training-only wrong-answer penalty (AC-4) | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_rl.ipynb` | Phase 12 configuration hashes unchanged; the roll-back guard with stubs (AC-4) | ~1 s |
| `nbdev-test --n-workers 0 nbs/coop_grid.ipynb` | `RL13_PLAN` arms and runs; `RL_PLAN` hash unchanged | ~1 s |
| `nbdev-test --n-workers 0 nbs/demo_fix.ipynb` | quick: every arm and the vote with the fake client, identical at 1 and 8 processes | ~10 s |
| `nbdev-test --n-workers 0` | full suite | ~75 s |

From the training environment, `nbdev-test --n-workers 0 --flags train nbs/clue_rl.ipynb` runs two RL steps with turn-level advantages and the penalty on the tiny model, a forced jump rolled back, two roll-backs in a row halting, and resume (under a minute).

## Runs, in order

| Step | Where | Command | Cost |
|------|-------|---------|------|
| T5 pilots | Mac | re-check prices; `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --flags llm nbs/demo_fix.ipynb` (the pilot section runs; the main section stops until `FIX_PLAN` is frozen); check the AC-6 bands it prints | measured: $0.65, AC-6 passed |
| T6 freeze | Mac | set the pilot-informed settings and `FIX_PLAN['frozen'] = True` in `nbs/fix_grid.ipynb`, export, commit; record the commit and `coopHash(FIX_PLAN)` in the README | done: `f01ad81`, hash `79abfb531cdd` |
| T7 Track A main | Mac | the same command with `--cell-timeout 0` (main section; the pilot replays from the cache); then the cached-rerun section | about $9 |
| T8 freeze | Mac | `RL13_PLAN['frozen'] = True` in `nbs/coop_grid.ipynb`, export, commit, push | done: `962c4e1`, hash `3e50a4002c7b` |
| T9 RL runs | Colab, one session per run (restart first) | open [colab_clue_rl](https://colab.research.google.com/github/Positron00/explRL/blob/main/nbs/colab_clue_rl.ipynb); set-up; configuration with `ARM` and `SEED` (`credit` 2, `indpen` 1 and 2, `credturn` 1 and 2); the "Phase 13 RL run" section (resumes after a disconnect); or all five in one session with "Phase 13: all five runs in one session" (each run in its own process, finished runs skipped, resumes after a disconnect; queue the evaluation and Pack after it) | about 3 GPU hours each |
| T10 evaluation | Colab, then Mac | the "Phase 13 evaluation" section, then Pack; download and `unzip -o` into `results/multiagent/rl/colab/`; on the Mac from `.venv-train`: `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags train nbs/demo_rl.ipynb` (its Phase 13 cell picks the best arm and runs its cross-play) | about 2 GPU hours; API under $1 |

API spend goes through the Phase 10 client and ledger under the $150 API cap; GPU spend under its own $150 cap.

## Artifacts

- `results/multiagent/fix/{quick,pilot,full}/` and `results/multiagent/profile/{quick,pilot,full}/`: `runs.csv`, `turns/`, `report.md`, `fix.png`, metrics and timing (`_live` copies after the live runs).
- `results/multiagent/rl/colab/runs_p13/<arm>_s<seed>/`, `results/multiagent/rl/colab/eval_p13/`, `results/multiagent/rl/eval_p13/` (merged rows and the report).

## Regression

Phase 11 (`clue/full`) and Phase 12 Track A (`coop/full`) workloads rerun from the response cache give byte-identical `runs.csv` and `turns.jsonl`, and the Phase 12 evaluation's cached rerun gives byte-identical rows and turn logs with no API spend (checked 2026-10-15 after the Phase 13 code; reference hashes in the README, T1).
