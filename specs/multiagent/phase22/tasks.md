# Tasks: Phase 22

Status (2026-11-11): T1-T3 built and tested offline (with T6's tests and `tools/b3_run.py` for T4-T6 and T9); T4 step 1 (the regression gate) passed; `B3_PLAN` not yet frozen. Decisions P22-1 to P22-20 made by the user on 2026-11-10. B3 makes no API calls and uses no GPU. **C1's main run waits for T6** (P20-13), and A1 waits for Gate C1, so T1-T6 are on the critical path. **T6 also needs Phase 20's T1-T2** (the bridge board, `RuleBridge`, `bridgeMembers`, mirror posts as P22-12) **and C1's pilot rows** (Phase 20's T8). A2 does not wait for B3 (P21-8); T2 gives A2 its two forecasters early.

Order: T1 and T2 first (T2's naive and pilot-only parts before A2's T5 freeze), then T3, T4 and T5 in week 1. T6 once its Phase 20 inputs exist. T7 alongside A2. T8 when C2's and C4's specs exist. T9 after each main run, and the gate at the end.

Rules are as in Phases 16-21:

- notebook first, then `nbdev-export` and `nbdev-clean`, with one notebook per test call;
- new notebooks go into `nbs/sidebar.yml`;
- modules stay under 200 lines;
- offline tests run without the network, `anthropic`, a key or a GPU;
- Phase 5-21 outputs and hashes stay unchanged, and so do the committed Phase 13-18 prediction and score files;
- each frozen plan and each forecast is pushed before it is used;
- multiprocess runs only from `tools/b3_run.py`, a script with a `__main__` guard (macOS spawn).

## T1. Behaviours as parameters (about 1 day)
- **Files:** `nbs/b3_agents.ipynb` (new: `B3_KNOBS`, `B3Params`, `b3Rng`, the `TrustOne`, `Spread` and `ShareAll` mixins, `b3Members`).
- **What:** the two behaviours of P22-2 (all three behaviour-1 candidates), with their own random generator, made only for non-default knobs.
- **Done when:**
  - `test_b3_defaults` (AC-2) and `test_b3_behaviours` (AC-3) pass;
  - the `slow` regression passes: θ_default reruns of Part 0's Stage 1 cells and Stage 4's forecast cells equal `colony/forecast/runs.csv` and `forecast4/runs.csv` row for row;
  - `test_b3_hashes` and the full suite pass.
- **Status (2026-11-11): done.** `b3_agents` (140 lines). `test_b3_defaults`, `test_b3_behaviours`, `test_b3_mirror` and the `slow` regression pass. A one-line guard in `RuleAgent.choose` and `ViewAgent.choose` (a guess waits when no answer is consistent with the known clues) fixes a crash that `guess` > 0 met on liar boards; unreachable at guess 0, so no earlier output changes.

## T2. Effects, forecasters and files (about 1 day)
- **Files:** `nbs/b3_forecast.ipynb` (new: `Effect`, `estimate`, `forecastSim`, `forecastPilot`, `forecastNaive`, `forecastExperiment`, `writeForecast`, `scoreExperiment`), `nbs/b3_effects.ipynb` (new: `C1_EFFECTS`, `A2_EFFECTS`, `RETRO_EFFECTS`, `c1Forecast`, `a2Forecast`).
- **First:** `forecastNaive`, `forecastPilot`, `writeForecast`, `A2_EFFECTS` and `a2Forecast`, so A2 can freeze its two forecasts with them (T7).
- **Done when:** `test_b3_forecasters` (AC-7), `test_b3_files` (AC-9) and `test_b3_retro_counts` (AC-8: 9 and 10 of 11, item by item, from the saved score files) pass.
- **Status (2026-11-11): done.** `b3_forecast` (199 lines) and `b3_effects` (162). `test_b3_forecasters`, `test_b3_files` (the writeForecast and scoreExperiment parts) and `test_b3_retro_counts` pass: the unfitted line is right on 9 of 11 and every-design-helps on 10, item by item from the saved files; each study's frozen estimate rule reproduces its saved predictions to 1e-12. `test_b3_c1` (AC-10) is here too.

## T3. The fit and `B3_PLAN` (about 1 day)
- **Files:** `nbs/b3_fit.ipynb` (new: `FIT_CELLS`, `FOLDS`, `claudeTargets`, `simCell`, `gridSim`, `loss`, `fit`, `heldOut`, `chooseKnob`, `bootTau`, `refit`, `fitHealth`), `nbs/b3_report.ipynb` (new: `B3_PLAN` unfrozen, `retrospective`, `poolScores`, `gateB3`, `writeB3`, `figB3`, `syntheticB3`), `tools/b3_run.py` (new), `nbs/demo_b3.ipynb` (new: `quick`, `fit`, `forecast`).
- **Done when:**
  - `test_b3_fit` (AC-5) and `test_b3_refit` (AC-6) pass;
  - `claudeTargets` reads the 15 clean and 17 liar cells with the means of design-low-level's tables;
  - `demo_b3` quick runs end to end on a tiny grid and synthetic rows.
- **Status (2026-11-11): done.** Split to stay under 200 lines: `b3_cells` (93: `FIT_CELLS`, `FOLDS`, `REUSED`, grids, `thetaKey`, `claudeTargets`), `b3_fit` (149: `simCell`, `gridSim`, `loss`, `fit`, `heldOut`, `chooseKnob`, `bootTau`, `refit`, `pilotScale`, `fitHealth`), `b3_plan` (59: `B3_PLAN`), `b3_retro` (100: `retrospective`), `b3_report` (165: `poolScores`, `gateB3`, `retroMarkdown`, `writeB3`, `figB3`, `syntheticB3`); `b3Replay` is in `b3_agents`. `claudeTargets` reads the 32 cells with the tables' means (to 3 decimals). `demo_b3` quick runs end to end; `tools/b3_run.py` has check, probe, grid, fit, retro, forecast C1 and score C1.

## T4. Freeze and the week-1 fit (Mac, about 6 hours of laptop time, $0)
- **What:**
  1. Run the regression gate (T1's checks and the full suite).
  2. Freeze `B3_PLAN` (`coopHash`), commit and push. Record the commit and hash in the README.
  3. Run a 1-seed timing probe on the slowest fit cell (64 agents) and update the runtime estimate.
  4. `tools/b3_run.py grid`: the coarse grid for the three candidates; `chooseKnob`; the fine grid for the winner.
  5. `fit` per fold and on all cells; `bootTau`; `fitHealth`.
- **Then:** if a parameter sits at the top of its range (P22-21), or H22-3 fails (held-out loss not below θ_default's in at least 2 of 3 folds), **stop and ask** before T6 (P22-11).
- **Done when:** `results/multiagent/b3/fit.json` holds the chosen knob, θ0 per fold and on all cells, τ, held-out losses beside θ_default's, and the fit-health verdict; the grid cache is complete.
- **Status (2026-11-11): steps 1-3 done; `B3_PLAN` frozen, hash `3490efe9aa41` (pinned in `test_b3_plan`), to be pushed before step 4.** `tools/b3_run.py check`: 840 Part 0 and 630 Stage 4 forecast boards at θ_default (30 seeds) equal their saved rows, 0 differ; full suite passes. Probe: 0.6-1.0 s per 64-agent board with knobs set; 234.7 s per grid point on 8 workers, so the coarse grid about 0.8 hours and the fine grid about 0.7. Next: freeze and push `B3_PLAN` (needs the user's go-ahead to push), then grid and fit.

## T5. Retrospective check on paper2's calls (Mac, under 1 hour, $0)
- **What:** `tools/b3_run.py retro`: per fold, θ0 without the fold, refit on that study's pilot (seed 1890), each study's frozen forecast rule, and the scores of all four forecasters and prior-only against the saved Haiku results. The `P14` fold scores Phase 14's two team-size calls for the two simulators.
- **Done when:**
  - `results/multiagent/b3/retro.json` and `retro.md` give, for the 11 conclusive calls, the right, wrong and no-call counts per forecaster, item by item (unfitted 9, every-design-helps 10, as paper2), with H22-2's verdict and the in-sample caveat;
  - the error and collude faults are reported as held-out checks;
  - the plain-board liar misfit is stated.
- **Then:** report the retrospective and the fit to the user. Nothing waits on the score.

## T6. C1's forecast (Mac, under 1 hour, $0)
- **Needs:**
  - T4 (fit health passed, or the user decided);
  - Phase 20's T1-T2: `BridgeBoardEnv` that runs with the numpy runner, `RuleBridge`, `bridgeMembers`, and mirror posts by honest rule agents (P22-12, Phase 20's FR-A4), and `runC1Cell`'s numpy rows with `bridgeColumns`;
  - C1's pilot rows (Phase 20's T8: `coupled`, `bridge1`, `bridgeGuard` at 64 agents, seed 1890).
- **What:**
  1. `test_b3_mirror` (AC-4) and `test_b3_c1` (AC-10).
  2. `tools/b3_run.py forecast C1`: θ0 without C1's reused cells (Stage 4's `squads` at 64 and the 64-agent `colonyGuards`); refit `trustOne` on the pilot's contamination; the five lines for `C1_EFFECTS`; simulated against observed relays and mirror posts.
  3. Commit and push `specs/multiagent/phase20/c1_predictions.json`. Hand its SHA-256 and commit to Phase 20's T9 for `C1_PLAN`.
- **Done when:** `C1_PLAN` can be frozen with the forecast's SHA-256, and a rerun of T6 at the same commit gives the same bytes.

## T7. A2's two forecasts (alongside Phase 21's T5)
- **What:** after A2's pilot, `a2Forecast(pilotRows)` writes `specs/multiagent/phase21/a2_predictions.json`: every-design-helps on `A2-1` to `A2-4`; pilot-only on `A2-2` (team 2190) and `A2-4` (drop-only seed 990 against Phase 14's originals 900-904), 0 on the others; fitted and unfitted "not represented".
- **If T2 is not built by then:** A2 writes the same two lines by hand by B3's rules, and T7 later checks them with `forecastNaive` and `forecastPilot` and reports any difference.
- **Done when:** the file's SHA-256 is in `A2_PLAN`'s second frozen version before A2's main run.

## T8. C2 and C4 part b (when their specs and pilots exist)
- **What:** check that each spec supplies its effect list (with `naive` and `represented`), a numpy `cellFn`, `pilotMap` and `reused` (P22-15). C2 adds rule agents that read the failed-answer and oracle records, and laundering liars. C4 part b chooses a liar stand-in or marks the adaptive arms not represented. Then `tools/b3_run.py forecast <exp>` after each pilot, and the file's SHA-256 into that experiment's frozen plan.
- **Done when:** each forecast is committed and pushed before its main run.

## T9. Scoring and Gate B3 (after each main run; the gate at the end, plan: week 16)
- **What:**
  1. After each experiment's report: `tools/b3_run.py score <exp>` with the experiment's estimates and intervals (for C1, `c1Summaries`), writing `<exp>_score.json` beside its forecast.
  2. After the last one: `poolScores`, `gateB3` (H22-1, with McNemar beside it; H22-4), `writeB3` and `figB3`.
- **Done when:**
  - `results/multiagent/b3/report.md` gives the counts per forecaster and experiment, pooled, on the common set and on all items, and Gate B3's verdict by the frozen counting rule (or "too few calls to read" below 8 conclusive items);
  - the result is in this README, `results/multiagent/REPORT.md` and the research plan's B3 line;
  - if the fitted simulator does not beat every-design-helps, that is reported plainly and recorded for the Stage 2 decision, and no experiment changes;
  - paper2 changes only where a claim changes.
