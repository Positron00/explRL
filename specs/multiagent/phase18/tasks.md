# Tasks: Phase 18

Status (2026-10-19): T1, T2, T3, T4 and T7 done (offline; full suite green; Part 0 run, `colony_predictions.json` written and to be committed before the pilot); AC-6 revised after measuring (README). `COLONY_PLAN` frozen at `fc01882` (hash `58e842277a3e`). T5 done (2026-10-20: pilot $0.84, Stage 1 $24.89; H18-1, 2, 4 supported, H18-3 not; go/no-go: stop, so T6 not run unless the user decides to deviate). Next: T10 docs; T8 after Phase 17's recipe is frozen.

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

## T7. Part B code (about 1.5 days; may start after T2)
- **Files**: `nbs/rl17_grid.ipynb`, `nbs/rl17_train.ipynb` (`world`, the `longest` metric), `nbs/rl17_update.ipynb` (`pairLengths`), `nbs/clue_roll.ipynb` (Phase 18 columns in `coopRows`); new `nbs/rl18_grid.ipynb`, `nbs/rl18_report.ipynb`, `nbs/demo_rl18.ipynb`; the two Colab cells in `nbs/colab_clue_rl.ipynb`.
- **Tests**: AC-9; Phase 17's hashes and trainer tests unchanged.

## T8. Part B runs (Colab, one or two Pro+ accounts; after T5 and Phase 17's frozen recipe)
- **What**: push; speed check on one account (it prints seconds per step, the proposed `maxLen` and the projected hours); report them to the user and wait for confirmation; freeze `RL18_PLAN` (steps, `maxLen`, hours), push; run "Phase 18 main" on both accounts (`HOST` set per account); the last account to finish evaluating writes `explRL_rl18.zip`.
- **Done when**: 13 final adapters (halted runs reported), `eval_p18/runs.csv`.

## T9. Part B analysis (Mac)
- **What**: unzip into `results/multiagent/rl/colab/`; `demo_rl18` (flag `train`); H18-B1 to H18-B4 (goal drift); results in the README.

## T10. Docs and preprints
- **What**: README results, `REPORT.md` Phase 18 section, the plan's status line, the summary page and the preprints where a claim changes (paper: trust and scale; paper2: the forecast).
- **Done when**: docs updated; all checks pass.
