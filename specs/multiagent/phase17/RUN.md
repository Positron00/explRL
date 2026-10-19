# Running Phase 17 (RL that makes larger teams pay off)

Plan, decisions and results: [README.md](README.md). Builds on Phase 16: [../phase16/RUN.md](../phase16/RUN.md).

Status 2026-10-18: T1-T3 implemented and tested; nothing run; step 0 waits for Phase 16.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/rl17_grid.ipynb` | evaluation grid, configuration hashes, plans, claiming (AC-2, AC-4) | ~5 s |
| `nbdev-test --n-workers 0 nbs/rl17_update.ipynb` | board groups, clipped loss (offline parts of AC-3) | ~3 s |
| `nbdev-test --n-workers 0 nbs/rl17_train.ipynb` | imports (the loop needs `train`) | ~3 s |
| `nbdev-test --n-workers 0 --flags train nbs/rl17_train.ipynb` | FR-B4 equivalence with a tiny model (`.venv-train`: `PATH=.venv-train/bin:$PATH`), and a mixed step with liars and clipped passes | ~25 s |
| `nbdev-test --n-workers 0 nbs/rl17_report.ipynb` | exact tests, Holm, curves (AC-6) | ~10 s |
| `nbdev-test --n-workers 0 nbs/demo_rl17.ipynb` | quick: synthetic end to end | ~5 s |
| `nbdev-test --n-workers 0` | full suite | ~100 s |

## Runs, in order

| Step | Where | Command | Compute |
|------|-------|---------|---------|
| T4 step 0 | Colab (A100 or L4), after Phase 16; one or two accounts (models claimed one at a time) | set-up, configuration, "Phase 17 step 0" (models not yet on Drive are skipped; rerun to add them); download `explRL_rl17s0.zip` | about 8 A100 hours |
| T5 freeze | Mac | `PILOT17_PLAN['frozen'] = True`, commit, push | none |
| T5 pilot (v2) | Colab (A100 or G4), one or two accounts (run the cell on both; they split `p17a`-`p17c` by claims; about 34 hours of wall time with two); writes `runs_p17pilot2/` and `explRL_rl17pilot2.zip` (v1: `runs_p17pilot/`) | set-up, configuration, "Phase 17 pilot"; download `explRL_rl17pilot.zip`; on the Mac: selection and the projected main-run hours, for the user to confirm | about 50 A100 hours |
| T6 freeze | Mac | after the user confirms the projected hours: the chosen recipe and cost levers into `RL17_PLAN`, `frozen = True`, commit, push | none |
| T6 main | Colab (A100), one or two accounts | on each: set-up, configuration (`HOST` set, different per account), "Phase 17 main"; when all runs are final, the account that wins the evaluation claim evaluates and writes `explRL_rl17.zip` (rerun the cell on any account after the last run finishes). To move a run to another account: stop the first runtime, add the run to `TAKEOVER` on the other, rerun the cell | about 850 A100 hours at four passes per batch (about a third at one) |
| T7 analysis | Mac | unzip into `results/multiagent/rl/colab/`; `nbdev-test --n-workers 0 --cell-timeout 0 --flags train nbs/demo_rl17.ipynb` | none |

**Background and long runs:** turn on background execution (Pro+), so the cells continue with the browser closed. Colab ends a session after about 24 hours; a main run takes days, so each run checkpoints every step: when a session ends, restart, run set-up and configuration, then the same cell again (finished runs and evaluated models are skipped; the run in progress resumes from its last step).

**Second account set-up:** share `MyDrive/explRL_rl` from the first account (Editor); on the second, "Add shortcut to Drive" at the top of My Drive, named `explRL_rl`, so the path is identical (the configuration hash includes the model path).

## Artifacts

- Colab (Drive): `eval_p17s0/`, `runs_p17pilot/`, `runs_p17/<arm>_s<seed>/` (with `claim.json`), `eval_p17/`; zips `explRL_rl17s0.zip`, `explRL_rl17pilot.zip`, `explRL_rl17.zip`.
- Mac: `results/multiagent/rl/colab/...` (the unzipped outputs); `results/multiagent/rl/quick_p17/` (synthetic), `eval_p17s0/` (step-0 report and curves), `pilot_p17/selection.json` (choice, recipe, projected hours), `eval_p17/{report.md, rl17.png, summary.json}`.
