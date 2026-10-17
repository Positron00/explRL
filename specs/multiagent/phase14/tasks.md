# Tasks: Phase 14

Status (2026-10-17): T1, T2 and T4 done (offline; full suite green; the numpy forecast run and committed before any Part B LLM cell). Next: T3 (freeze `TRUST_PLAN`, Part A live), then T5.

Rules as Phase 13 (notebook first, export, one notebook per test call, modules under 200 lines, offline tests without `anthropic` or `torch`; Phase 5-13 cached reruns byte-identical). Gates: no Part A main run before `TRUST_PLAN` is frozen; no Part B LLM cell (the pilot included) before the numpy forecast is committed; no Part B main run before `SCALE_PLAN` is frozen; API under the $150 cap.

## T1. The two new settings
- **Files**: `nbs/clue_fix.ipynb`, `nbs/clue_text.ipynb` (design: the two new settings).
- **Tests**: AC-2: private record on hand-made boards; public check reaches every agent and their known clues; Phase 13 defaults byte-identical (the existing hash tests stay green); rollout rows and turn logs equal `runClue`'s with each new setting.

## T2. Grids, plans, analysis, demo
- **Files**: `nbs/fix_grid.ipynb` (two `FIX_ARMS` entries; `fixCell` takes a number of liars), new `nbs/scale_grid.ipynb`, new `nbs/scale_report.ipynb`, new `nbs/demo_trust.ipynb`.
- **Tests**: AC-3 (sizes, liar counts, reused cells); summaries on synthetic rows with known publicity and cost effects; the quick demo with the fake client.

## T3. Part A main run (live, about $2)
- **What**: freeze `TRUST_PLAN`, commit; run; cached rerun; results in the README.
- **Done when**: AC-6 for `TRUST_PLAN`.

## T4. Numpy forecast
- **What**: `tools/scale_forecast.py run`; run once; commit output and predicted signs (AC-5), before T5's pilot.

## T5. Part B pilot, freeze, main (live, up to $40)
- **What**: pilot at N = 32 (AC-4: invalid under 5%, enforced again before the main run), apply the cost rule (cut N = 32 to 3 seeds, or stop and ask), freeze `SCALE_PLAN`, commit; main run; cached rerun; score the forecast (`tools/scale_forecast.py score`); results.
- **Done when**: AC-4, AC-5, AC-6.

## T6. Docs and preprints
- **What**: README results, `REPORT.md` Phase 14 section, the multi-agent plan's status, and the preprints where a claim changes (paper: the trust and communication-cost sections; paper2: the scaling forecast).
- **Done when**: docs updated; all checks pass.
