# Tasks: Phase 18

Status (2026-10-19): T1, T2, T3, T4 and T7 done (offline; full suite green; Part 0 run, `colony_predictions.json` written and to be committed before the pilot); AC-6 revised after measuring (README). `COLONY_PLAN` frozen at `fc01882` (hash `58e842277a3e`). T5 done (2026-10-20: pilot $0.84, Stage 1 $24.89; H18-1, 2, 4 supported, H18-3 not; go/no-go: stop). T6 replaced by a user-approved deviation, T6b, done 2026-10-20 ($32.73): guards held at 32 agents (+0.229, p 0.004) and helped against mistaken members and colluding liars. T6c (Stage 3) and T6d (guards at 64) done 2026-10-20/21. T6e (Stage 4, guards that scale) built and tested 2026-10-21 (full suite green; regression gate passed: 303 earlier live boards replay through the cache-only client with every saved column equal, and the live-flag cached reruns are byte-identical, $0); forecast committed at `1e9c53d`; `STAGE4_PLAN` frozen at `40cbaad` (hash `a441381ce078`). Pilot passed (2026-10-21, $2.38; projection $44.39, run). Stage 4 run in two seed batches and analysed (2026-10-21, $43.80): H18-13, H18-14, H18-15 all supported (Holm p 0.012); squads' advantage grows from 16 to 64 agents; forecast 4 right, 1 wrong, 1 no call. Next: T10 docs; T8 after Phase 17's recipe is frozen.

Rules as Phases 13-17: notebook first, `nbdev-clean` then `nbdev-export`, one notebook per test call, modules under 200 lines, offline tests without a network, key, `anthropic` or `torch`; Phase 5-17 cached reruns byte-identical and Phase 12-17 hashes unchanged. Gates: no Haiku cell before the Part 0 forecast is committed; no main cell before its plan is frozen and its hash recorded; Stage 2 only on a `go` verdict and a raised API cap; Part B only after Phase 17's recipe is frozen, Stage 1 is done and the user confirms the GPU hours.

## T1. Literature check (about half a day)
- **What**: verify the README's candidate references (stigmergy, quorum sensing, stop signals, response thresholds, polyandry, ant mills, Byzantine fault tolerance, emergent roles in MARL) and search for LLM work on quorum, contest or role rules on shared boards with faulty members; add a Phase 18 section to `../LITERATURE.md`; revise the README's novelty claims if needed.
- **Done when**: every cited paper checked on its own page; the "what is new" statement updated.

## T2. Board options and agents (about 1.5 days)
- **Files**: new `nbs/clue_colony.ipynb`, `nbs/colony_agents.ipynb`; small changes in `nbs/clue_text.ipynb`, `nbs/clue_fix.ipynb`, `nbs/clue_policy.ipynb`, `nbs/llm_agent.ipynb`, `nbs/clue_roll.ipynb`, `nbs/clue_runs.ipynb`.
- **Tests**: AC-2, AC-3 (colony, confirm, guard and threshold agents; colluding liars; mistaken members); Phase 11-17 byte-identical (the existing hash tests stay green).

## T3. Tracing, grids, plans, analysis, demo (about 2 days)
- **Files**: new `nbs/colony_trace.ipynb`, `nbs/colony_grid.ipynb`, `nbs/colony_report.ipynb`, `nbs/demo_colony.ipynb`.
- **Tests**: AC-4, AC-6 (tracing and goal drift), AC-7; the quick demo with the fake client.

## T4. Part 0: numpy screen and forecast (Mac, $0)
- **What**: `tools/colony_forecast.py` (done 2026-10-19: 10,080 cells, 10 minutes); run once; commit `colony_predictions.json` before any Haiku cell (AC-5); summarize the screen in the README (which rules and roles numpy favours; whether `colony+threshold` should replace `colony+guards` is **not** changed by the screen: Stage 1's arms are fixed in the README).

## T5. Freeze, pilot, Stage 1 (Mac, about $26)
- **What**: freeze `COLONY_PLAN` (before the pilot, so the cost rule is fixed first), commit and push, record the hash; pilot (AC-8; stop and ask if liars cost the plain board nothing); the cost rule; Stage 1 (176 cells); cached rerun; tracing; `colonySummaries`; `goNoGo`; score the forecast; results in the README.
- **Done when**: AC-8, AC-10 for `COLONY_PLAN`; the go/no-go verdict reported to the user.

## T6. Stage 2 (Mac, about $77-108; only on `go` and a raised cap)
- **What**: the user raises the cap; freeze `COLONY2_PLAN` with the chosen arm, commit and push; the Stage 2 cost rule; run; cached rerun; tracing; the trend test; rescore the forecast for H18-5.
- **Done when**: AC-10 for `COLONY2_PLAN`.

## T6b. Guards at 32 agents (deviation, 2026-10-20; Mac, about $35-45, cap $200)
- **Files**: new `nbs/colony32.ipynb` (`stage32Grid`, `COLONY32_PLAN`, `stage32Summaries`, `writeStage32`); a `stage32` section in `nbs/demo_colony.ipynb`.
- **What**: freeze `COLONY32_PLAN`, commit and push, record the hash; run (`EXPLRL_COLONY_STAGE=stage32`); cached rerun; results in the README.

## T6c. Stage 3: adaptive liars and unassigned guards (implemented and tested 2026-10-20; `COLONY3_PLAN` frozen at `351ce61`, hash `0c59fa10f2b0`; run 2026-10-20, $8.85 with the pilot: H18-10 supported, H18-11 not)
- **Files**: `nbs/clue_colony.ipynb` (`DECEIVER_RULE`, `VOLUNTEER_RULE`, `colonyRules`, `checkOptions`, `COLONY_OPTS`), `nbs/clue_text.ipynb` (`fault`, `volunteer`, the share exemption, slot-dependent rules), `nbs/clue_policy.ipynb` and `nbs/llm_agent.ipynb` (the slot whenever a slot-dependent option is set), `nbs/clue_runs.ipynb` and `nbs/colony_trace.ipynb` (Claude liar slots, call reservation), `nbs/clue_roll.ipynb` and `nbs/rl17_train.ipynb` (no scripted members for adaptive cells: `scriptedFaults`), `nbs/fix_grid.ipynb` (`cellCalls`), `nbs/colony_agents.ipynb` (`faultClass` refuses `adaptive`), `nbs/colony_grid.ipynb` (`colonyVolunteer`, fault `adaptive`), new `nbs/colony3.ipynb`, the `stage3pilot` and `stage3` sections of `nbs/demo_colony.ipynb`.
- **Tests**: AC-11.
- **What**: regression gate (Stage 1's and the 32-agent run's cached reruns byte-identical, hash tests green); freeze `COLONY3_PLAN`, commit and push, record the hash; pilot (`EXPLRL_COLONY_STAGE=stage3pilot`; compliance gate and cost rule; stop and ask if either fails); Stage 3 (`EXPLRL_COLONY_STAGE=stage3`), with the reused Stage 1 cells replayed from the cache for the new columns ($0); cached rerun; results in the README.
- **Done when**: AC-10 and AC-11 for `COLONY3_PLAN`.

## T6d. Guards at 64 agents (second deviation, lean; built 2026-10-20; `COLONY64_PLAN` frozen at `183da31`, hash `9764cd43e34c`; Mac, about $25-32 with the pilot, cap $250; **done 2026-10-21**: pilot passed, 16 boards run, $28.83 with the pilot, H18-12 supported, +0.165, p 0.004)
- **Files**: new `nbs/colony64.ipynb`; `stage64pilot` and `stage64` sections in `nbs/demo_colony.ipynb`.
- **Tests**: AC-12.
- **What**: freeze `COLONY64_PLAN`, commit and push, record the hash; pilot (`EXPLRL_COLONY_STAGE=stage64pilot`; invalid under 5%, cost rule $35; stop and ask if either fails); the 16 boards (`EXPLRL_COLONY_STAGE=stage64`); cached rerun; results in the README.

## T6e. Stage 4: guards that scale (planned 2026-10-21; plan [stage4.md](stage4.md); Mac, about $51 with the pilot, cost rule $60, cap $250)
- **Files**: new `nbs/colony_board.ipynb`, `nbs/colony_mech.ipynb`, `nbs/colony4.ipynb`, `nbs/colony4_report.ipynb`; small changes in `nbs/clue_runs.ipynb` (`clueSetup`, `stage4Members`), `nbs/clue_colony.ipynb` (failure label, `knownColony`, `FAIL_RULE`, `SQUAD_RULE`, `checkOptions`, `COLONY_OPTS`), `nbs/clue_text.ipynb` (`squadView` in `observe` and `parse`), `nbs/colony_trace.ipynb` (`stage4Members` in `replay`), `nbs/clue_roll.ipynb` (`rollout` refuses the Stage 4 keys); `tools/colony_forecast.py` (`stage4`, `score4`); `stage4pilot` and `stage4` sections in `nbs/demo_colony.ipynb`.
- **Tests**: AC-13; the full suite.
- **What**, in order:
  1. Build and test offline (AC-13).
  2. Regression gate: every earlier live cell replays through the cache-only client without a miss ($0); then the cached reruns of Stage 1, 32 agents, Stage 3 and 64 agents byte-identical; hash tests green.
  3. Run the numpy forecast (`colony_forecast.py stage4`), commit `colony4_predictions.json`.
  4. Freeze `STAGE4_PLAN` (with the forecast file's hash), commit and push, record the hash in [stage4.md](stage4.md).
  5. Pilot (`EXPLRL_COLONY_STAGE=stage4pilot`; `pilotCheck4` and `costRule4`; stop and ask if either fails, including the guard-contest gate and its triage fallback).
  6. Stage 4 (`EXPLRL_COLONY_STAGE=stage4`) with the reused references replayed from the cache ($0).
  7. Cached rerun; score the forecast (`score4`); results in [stage4.md](stage4.md) and the README.
- **Done when**: AC-10 and AC-13 for `STAGE4_PLAN`.

## T7. Part B code (about 1.5 days; may start after T2)
- **Files**: `nbs/rl17_grid.ipynb`, `nbs/rl17_train.ipynb` (`world`, the `longest` metric), `nbs/rl17_update.ipynb` (`pairLengths`), `nbs/clue_roll.ipynb` (Phase 18 columns in `coopRows`); new `nbs/rl18_grid.ipynb`, `nbs/rl18_report.ipynb`, `nbs/demo_rl18.ipynb`; the two Colab cells in `nbs/colab_clue_rl.ipynb`.
- **Tests**: AC-9; Phase 17's hashes and trainer tests unchanged.

## T8. Part B runs (Colab, one or two Pro+ accounts; after T5 and Phase 17's frozen recipe)
- **Part B lite** (`RL18_PLAN` v2, amended by the user 2026-10-21): 5 `c18team` runs of 30 steps, the lite evaluation.
- **What**: push; speed check on the first free account (it prints seconds per step, the proposed `maxLen` and the projected hours for 5 runs of 30 steps); a stability check of Phase 17's main runs once its zip arrives (no halts or collapse under the recipe); report both to the user and wait for confirmation; freeze `RL18_PLAN` (`maxLen`, hours, recipe), push; run "Phase 18 main" on both accounts (`HOST` set per account); the last account to finish evaluating writes `explRL_rl18.zip`.
- **Speed check done** (2026-10-22): 628 s per step, longest 2,163 tokens (`maxLen` 3,072), 0 cut, invalid 0.1-0.3%; 26 GPU hours for 5 runs of 30 steps. Phase 17 stability check failed (5 of 8 halted, 4 on one-step KL outliers); the user approved `FIX18` (KL cap 10, two-step KL halt, pre-halt checkpoint for halted runs) and confirmed the hours; `RL18_PLAN` frozen (2026-10-22). Next: "Phase 18 main" on both accounts.
- **Done when**: 5 final adapters (halted runs reported), `eval_p18/runs.csv`.

## T9. Part B analysis (Mac)
- **What**: unzip into `results/multiagent/rl/colab/`; `demo_rl18` (flag `train`); H18-B2 (primary), H18-B3, H18-B4 (goal drift) and the training trend; results in the README; a full Part B (H18-B1) only if specialization appears.

## T10. Docs and preprints
- **What**: README results, `REPORT.md` Phase 18 section, the plan's status line, the summary page and the preprints where a claim changes (paper: trust and scale; paper2: the forecast).
- **Done when**: docs updated; all checks pass.
