# Tasks: Phase 16

Status (2026-10-17): T1-T3 done (offline; `rl16_grid` 60 lines, `rl16_report` 180; full suite green; the Colab batch cell and its subprocess code checked offline, not on a GPU). T4 done (`RL16_PLAN` frozen at `0d0b7dc`, hash `082b3b7c9a31`, pushed). Next: T5 on Colab.

Rules as Phase 15 (notebook first, export, one notebook per test call, modules under 200 lines, offline tests without `anthropic`, `torch` or a GPU; Phase 5-15 cached reruns byte-identical). Gates: no Phase 16 run before `RL16_PLAN` is frozen, committed and pushed; the full analysis only on all nine runs plus the warm start; no API calls.

## T1. Grid and plan
- **Files**: `nbs/rl16_grid.ipynb` (design-low-level: `rl16_grid`).
- **Tests**: AC-2, AC-3; `RL16_PLAN` content.
- **Done when**: tests pass; module under 200 lines. About 1.5 hours.

## T2. Statistics and report
- **Files**: `nbs/rl16_report.ipynb`.
- **Tests**: AC-4, AC-5 (refusal on incomplete rows).
- **Done when**: tests pass. About 2 hours.

## T3. Colab sections, demo, figure
- **Files**: `nbs/colab_clue_rl.ipynb` (the one-cell automatic batch, configuration cell, header, Pack list), new `nbs/demo_rl16.ipynb`, `tools/incentive_figure.py`.
- **Tests**: the quick demo; the Colab notebook's offline cells; the figure script on the existing rows.
- **Done when**: full suite passes. About 1 hour.

## T4. Freeze and push
- **What**: `RL16_PLAN['frozen'] = True`, export, commit, push; record the commit and `coopHash(RL16_PLAN)` in the README.
- **Done when**: the plan is on GitHub before the Colab session starts.

## T5. Runs, evaluation and packing (Colab, one automatic batch, about 20 GPU hours, about $26)
- **What**: set-up, configuration, then the single "Phase 16: runs, evaluation and pack in one session" cell; it trains, evaluates and packs with no manual step in between (after a disconnect: restart, set-up, configuration, the same cell). Then download `explRL_rl16.zip` from Google Drive.
- **Done when**: six adapters trained (or halted and reported), `eval_p16/runs.csv` with 6 x 15 rows, the zip on Drive.

## T6. Analysis
- **What**: unzip into `results/multiagent/rl/colab/`; `demo_rl16` full; results in the README.
- **Done when**: AC-6 for the analysis; every `RL16_PLAN` item reported.

## T7. Docs and preprints
- **What**: `REPORT.md` Phase 16 section; the preprint's RL section, abstract and contributions; the summary figure; the multi-agent plan's status; wording as the claim rules decide.
- **Done when**: docs updated; all checks pass.
