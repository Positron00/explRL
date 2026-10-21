# Running Phase 18 (colony rules for large Claude teams)

Plan, decisions and results: [README.md](README.md). Builds on Phases 14 ([../phase14/RUN.md](../phase14/RUN.md)) and 17 ([../phase17/RUN.md](../phase17/RUN.md)).

Status 2026-10-19: implemented and tested; Part 0 run (10 minutes, $0); nothing live run.

## Where things run

- **Part 0 and Part A: the Mac only.** Part A calls Claude Haiku; the API key lives in the git-ignored `.env.local` and never goes to Colab, so these runs cannot be split across Colab accounts. They run in parallel processes on the Mac instead (`runWorkload`, 8 workers by default), with the response cache and the spend ledger as in Phases 13-15.
- **Part B: Colab, one or two Pro+ accounts**, sharing `MyDrive/explRL_rl` exactly as Phase 17 (see "Second account set-up" there): runs and evaluation models are claimed per account.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/clue_colony.ipynb` | tally, labels, known clues, rule sentences, option checks (AC-2) | ~3 s |
| `nbdev-test --n-workers 0 nbs/colony_agents.ipynb` | colony and confirm rule agents, guards, threshold guards, colluding liars, mistaken members (AC-3) | ~5 s |
| `nbdev-test --n-workers 0 nbs/clue_text.ipynb` (and `clue_fix`, `clue_roll`) | defaults byte-identical; rows and logs equal `runClue`'s with each option | ~10 s |
| `nbdev-test --n-workers 0 nbs/colony_trace.ipynb` | contamination, reach, suppression, relay, goal drift (AC-6) | ~5 s |
| `nbdev-test --n-workers 0 nbs/colony_grid.ipynb` | grids (Stage 1: 176 cells), cost rules, go/no-go (AC-4) | ~3 s |
| `nbdev-test --n-workers 0 nbs/colony_report.ipynb` | exact tests, Holm, trend on synthetic rows (AC-7) | ~10 s |
| `nbdev-test --n-workers 0 nbs/demo_colony.ipynb` | quick: fake client end to end | ~20 s |
| `nbdev-test --n-workers 0 nbs/rl18_grid.ipynb` (and `rl18_report`, `demo_rl18`) | Part B arms, suite, claims, specialization index (AC-9) | ~10 s |
| `nbdev-test --n-workers 0 --flags train nbs/rl17_train.ipynb` | `.venv-train`: Phase 17's tests plus a tiny-model step on a colony board | ~40 s |
| `nbdev-test --n-workers 0` | full suite | ~120 s |

## Runs, in order

| Step | Where | Command | Cost |
|------|-------|---------|------|
| T4 forecast | Mac | `python tools/colony_forecast.py run $PWD` (10,080 numpy cells, minutes); commit `specs/multiagent/phase18/colony_predictions.json` | $0 |
| AC-6 tracing check | Mac | `nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_colony.ipynb` without `EXPLRL_LLM_LIVE`: only the tracing check runs (Phase 14's cached replies), the live sections print skipped | $0 |
| T5 freeze | Mac | `COLONY_PLAN['frozen'] = True` in `nbs/colony_grid.ipynb`, export, commit, push; record the commit and `coopHash(COLONY_PLAN)` in the README | none |
| T5 pilot | Mac | `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_colony.ipynb`: runs the pilot, prints the invalid rate, cost per call, the plain board's honest loss and the cost rule's verdict; Stage 1 is skipped (`EXPLRL_COLONY_STAGE` defaults to `pilot`) until the verdict is recorded in the README | about $1 |
| T5 Stage 1 | Mac | the same command with `EXPLRL_COLONY_STAGE=stage1`: Stage 1 (176 cells, or the seeds the verdict allows), cached rerun, tracing, analysis, go/no-go; then `python tools/colony_forecast.py score $PWD results/multiagent/colony/stage1/runs.csv` | about $25 |
| T6 Stage 2 | Mac | only on `go`, after the user raises the cap: `COLONY2_PLAN` frozen (arm, `capRaised`), commit, push; the same command with `EXPLRL_COLONY_STAGE=stage2` runs Stage 2 | about $77-108 |
| T6b guards at 32 (deviation) | Mac | `COLONY32_PLAN` frozen, committed and pushed; then `EXPLRL_LLM_LIVE=1 EXPLRL_COLONY_STAGE=stage32 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_colony.ipynb` (cap $200 for this run) | about $35-45 |
| T6c regression gate | Mac | `nbdev-test --n-workers 0` (hash tests) and `EXPLRL_LLM_LIVE=1 EXPLRL_COLONY_STAGE=pilot nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_colony.ipynb` (cached reruns of the pilot, Stage 1 and the 32-agent run, byte-identical, free) | none |
| T6c freeze | Mac | `COLONY3_PLAN['frozen'] = True` in `nbs/colony3.ipynb`, export, commit, push; record the commit and `coopHash(COLONY3_PLAN)` in [stage3.md](stage3.md) | none |
| T6c pilot | Mac | `EXPLRL_LLM_LIVE=1 EXPLRL_COLONY_STAGE=stage3pilot nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_colony.ipynb`: prints the compliance gate (liar false posts per turn, refusals, invalid) and the cost rule's verdict | about $0.50 |
| T6c Stage 3 | Mac | the same command with `EXPLRL_COLONY_STAGE=stage3` (runs only if the pilot passed both gates) | about $11 |
| T6d freeze | Mac | `COLONY64_PLAN['frozen'] = True` in `nbs/colony64.ipynb`, export, commit, push; record the hash | none |
| T6d pilot | Mac | `EXPLRL_LLM_LIVE=1 EXPLRL_COLONY_STAGE=stage64pilot nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_colony.ipynb`: one 64-agent board, about 3 hours; prints the invalid share, cost per call and the cost rule verdict | about $1.50-2 |
| T6d guards at 64 | Mac | the same command with `EXPLRL_COLONY_STAGE=stage64` (runs only if the pilot passed): 16 boards in parallel, about 3-3.5 hours | about $23-30 |
| T8 Part B speed check | Colab, one account | after `RL17_PLAN` is frozen and Stage 1 is done: push; set-up, configuration, "Phase 18 speed check"; it prints seconds per step, the proposed `maxLen` and the projected hours: paste them back on the Mac | about 1 GPU hour |
| T8 Part B freeze | Mac | after the user confirms: `RL18_PLAN` (`steps`, `maxLen`, `projectedHours`, `userConfirmed`, `frozen`), commit, push | none |
| T8 Part B main | Colab, one or two accounts | on each: set-up, configuration (`HOST` different per account), "Phase 18 main"; rerun the cell on any account after the last run finishes, so the evaluation (models claimed one at a time) and the pack complete; download `explRL_rl18.zip` | from the speed check, plus about 14 GPU hours of evaluation (shared) |
| T9 analysis | Mac | unzip into `results/multiagent/rl/colab/`; `nbdev-test --n-workers 0 --cell-timeout 0 --flags train nbs/demo_rl18.ipynb` | none |

**Long runs (Part B):** background execution on; Colab ends a session after about 24 hours; runs checkpoint every step, so restart, run set-up and configuration, then the same cell (finished runs and evaluated models are skipped; the run in progress resumes). To move a run between accounts: stop the first runtime, put the run's name in `TAKEOVER` on the other account, rerun the cell. After any error: Runtime -> Restart session first (a failed cell keeps GPU memory).

**Wall time (Part A):** a 64-agent board plays 2,560 turns in order (about 2-3 hours); Stage 2's boards run in parallel processes within the API rate limit, so Stage 2 takes about a day on the Mac.

## Artifacts

- Mac: `results/multiagent/colony/{forecast,quick,pilot,stage1,stage2}/` (`runs.csv`, `turns.jsonl`, `trace.jsonl`, `trace_summary.json`, `report.md`, `colony.png`, `metrics.json`); `specs/multiagent/phase18/colony_predictions.json`, `colony_score.json`.
- Colab (Drive): `speed_p18/`, `runs_p18/<arm>_s<seed>/` (with `claim.json`), `eval_p18/` (per-model CSVs, `claims/`, `runs.csv`); `explRL_rl18.zip`.
- Mac (Part B): `results/multiagent/rl/colab/{runs_p18,eval_p18}/`, `results/multiagent/rl/eval_p18/{report.md, rl18.png, summary.json}`.
