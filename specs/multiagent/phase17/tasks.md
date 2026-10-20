# Tasks: Phase 17

Status (2026-10-18): T1-T3 done (offline and `train`-flagged tests pass: `rl17_grid` 150 lines, `rl17_update` 85, `rl17_train` 141, `rl17_report` 166; the full suite passes). `PILOT17_PLAN` frozen at `626bead` (hash `f4b4bd036996`). Next: T5 (pilot) on a second account now; T4 (step 0) after Phase 16.

Rules as Phase 16 (notebook first, export, one notebook per test call, modules under 200 lines, offline tests without `anthropic` or a GPU; Phase 5-16 outputs and hashes unchanged). Gates: step 0 complete only after Phase 16 (the pilot may run in parallel on another account); `PILOT17_PLAN` frozen and pushed before the pilot; `RL17_PLAN` frozen and pushed before the main runs; evaluation only when all main runs are final; no API calls.

## T1. Evaluation grid, step 0 (about half a day)
- **Files**: `nbs/rl17_grid.ipynb` (suite, step-0 model list), the step-0 Colab cell.
- **Done when**: AC-2; the cell's subprocess code compiles with Drive paths.

## T2. Constrained replies and the new trainer (about 1.5 days)
- **Files**: `nbs/local_policy.ipynb` (`guided`), `nbs/rl17_update.ipynb`, `nbs/rl17_train.ipynb`, `RL17Config` in `rl17_grid`.
- **Done when**: AC-3 (offline parts; the `train`-flagged equivalence run on the Mac with a tiny model); Phase 12-16 hashes unchanged.

## T3. Plans, claiming, Colab cells, analysis (about 1 day)
- **Files**: `PILOT17_PLAN`, `RL17_PLAN`, `claim`, `projectHours` in `rl17_grid`; pilot and main cells; `nbs/rl17_report.ipynb` (with `figRL17`), `nbs/demo_rl17.ipynb`.
- **Done when**: AC-4, AC-6 (synthetic); full suite passes.

## T4. Step 0 (Colab, about 8 A100 hours; an L4 works) - done 2026-10-19 (about 16 hours on account B; README)
- **What**: push; run the step-0 cell (models not yet on Drive are skipped; rerun after Phase 16 to add them; the zip is written when all 15 are done); unzip; baseline curves on the Mac (descriptive).

## T5. Pilot (Colab, about 50 A100 hours; may run before or alongside T4; one or two accounts split the runs by claims)
- **v1 (2026-10-19)**: ran; found the key-order flaw of constrained decoding (README); the user chose to re-pilot with the model's own key order (`PILOT17_PLAN` v2, `runs_p17pilot2/`).
- **v2 (2026-10-19)**: ran; every recipe halted on KL; diagnosed on the Mac (README: a log-probability sink on schema-fixed and near-certain tokens, and cut 8-agent prompts); the user approved the fix (`FIX17`) and pilot v3 (`runs_p17pilot3/`). Implemented and tested (`valueMask`, `tokenTerm`, `cutCount`, the `cut` rule).
- **v3 (2026-10-20)**: ran; `p17a` chosen (stable, KL about 0.01); the four-pass recipes halted again; projected main runs about 405 A100 hours; the user chose a shorter main run instead (T6).
- **What**: freeze `PILOT17_PLAN`, push; run the pilot cell; apply the selection rule; `projectHours` from the measured step times replaces the README's estimates; **report the projected main-run hours to the user and wait for confirmation**.

## T6. Freeze and main runs (Colab; amended 2026-10-20: `r17mix` only, 8 seeds, 60 steps, about 86 A100 hours plus evaluation; one or two accounts)
- **What**: after the user's confirmation, freeze `RL17_PLAN` with the chosen recipe and cost levers, push; run the main cell on each account (`HOST` set per account); when all runs are final, the account that wins the evaluation claim evaluates and writes the zip.
- **Done when**: 8 final adapters (halted runs reported), `eval_p17/runs.csv`.

## T7. Analysis and docs
- **What**: `demo_rl17` full; README results; `REPORT.md`; preprint; summary figure and page; wording as `RL17_PLAN`'s families and claim rules decide.
