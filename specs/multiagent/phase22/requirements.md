# Requirements: Phase 22, a better cheap screen

Part of [README.md](README.md) (plan and decisions P22-1 to P22-20, decided by the user on 2026-11-10). It builds on these modules:

- `clue_agents` (`RuleAgent`, `ClueLiar`, `known`, `candidates`) and `colony_agents` (`ViewAgent`, `ConfirmAgent`, `ColonyAgent`, `GuardAgent`, `memberClass`, `faultMembers`);
- `clue_colony` (`Q`, `tally`, `leading`), `colony_grid` (`colonyCell`, `part0Grid`, `PART0_SEEDS`, `COLONY_PLAN`), `colony4` (`ARMS4`), `colony4b` (`HYP4B`), `clue_grid` (`CLUE_SETTINGS`, `clueCell`);
- `colony_trace` (`runColonyCell`), `colony_mech` (`runStage4Cell`), `clue_runs` (`runClueNumpy`), `colony_report` (`bootSeeds`, `colonySummaries`, `trendSlopes`), `colony4_report` (`diffs`, `HYP4`, `stage4Summaries`);
- `tools/colony_forecast.py` (`estimates`, `predict4`, `stage4b`, the sign rule) and `tools/scale_forecast.py` (`change`, `perN`);
- from Phase 20 (built 2026-11-10): `bridge_board` (`BridgeBoardEnv`), `bridge_agents` (`RuleBridge`, `bridgeMembers`), `bridge_grid` (`ARMS20`, `c1Cell`, `c1PilotGrid`), `bridge_plan` (`C1_PLAN`), `bridge_report` (`c1Summaries`), `bridge_mech` (`c1Columns`, `runC1Cell`);
- from Phase 21 (specified, not built): `a2_grid` (`A2_PLAN`), `a2_report` (`a2Summaries`);
- `bench_grid` (`readCSV`, `writeCSV`), `coop_grid` (`coopHash`).

## Terms

Terms are as in Phases 18-21, paper2 and the research plan. In addition:

- **Behaviour 1, keeping output:** Claude teams keep more of their pooled share without liars as they grow than rule teams do.
- **Behaviour 2, building on unconfirmed values:** Claude agents on the counting board answer with values fewer than q agents posted.
- **`trustOne`:** the probability that a counting-board agent counts a leading value with fewer than q senders as known. It is drawn once per (agent, subtask, clue, value) and kept for the board.
- **Behaviour-1 knob:** one of three frozen candidates, chosen in week 1 (P22-2):
  - `spread`: when an agent opens a subtask, with this probability it opens the live subtask that the fewest teammates have open (ties: most known clues, then value, then at random) instead of the top-ranked one;
  - `shareAll`: with this probability per turn, an agent shares a held clue not yet posted for any open subtask, not only one a teammate has open;
  - `guess`: the existing `RuleAgent` guess rate.
- **θ:** the parameter vector (`trustOne`, the behaviour-1 knob). **θ_default:** all 0 (`guess` at the cell's value), today's rule agents. **θ0:** the cached-run fit. **θ_pilot:** the refit on an experiment's pilot.
- **Fit cell:** a cached Claude cell (arm, fault, N, study) whose cell mean is a fit target.
- **Fold:** a set of fit cells left out of a fit (P22-5).
- **Effect:** one planned contrast or margin of an experiment, written as Σ c_a × mean(arm a) on one measure, fault and team size, oriented so + means the design does better (P22-8).
- **Represented:** an effect whose arms the simulator can play. Rule agents read no rule text, records or offers, and cannot stand in for Claude liars or trained 3B policies.
- **Forecast sign:** for a simulator, + or − when the 95% bootstrap interval over its 30 seeds excludes 0, else 0. For pilot-only, the sign of the point estimate; every-design-helps' sign when it is not computable (P22-17). For every-design-helps, the effect's declared `naive` sign.
- **Conclusive:** the Claude estimate's 95% bootstrap interval over boards excludes 0.
- **Right, wrong, no call:** right when conclusive and the forecast has its sign; wrong when conclusive and the forecast has the other sign or 0; no call when not conclusive (paper2's rule).
- **Common set:** the effects that both simulators represent. Gate B3 counts these.
- **Prior-only:** the simulator at θ0, without the pilot refit (descriptive).

## Functional requirements

### Part A: rule-agent behaviours

- **FR-A1** `B3_KNOBS = ('trustOne', 'spread', 'shareAll', 'guess')` with ranges [0, 1], [0, 1], [0, 1] and [0, 0.5]. `B3Params` holds one value each; at θ_default nothing changes.
- **FR-A2** `b3Members(world, members, seed)` wraps honest numpy members with the behaviours set in `world['b3']`, after `stage4Members` and `bridgeMembers` have built them:
  - `trustOne` applies to counting-board agents (`ColonyAgent`, `GuardAgent`, `ThresholdGuard`, `RuleBridge`): in `knownFor`, a leading value with fewer than q senders counts as known when the agent's draw for that (k, j, value) is below `trustOne`;
  - `spread` retargets the base agent's open, as defined in Terms, for `RuleAgent` (the `plain` arms and Phase 14's board) and `ViewAgent` alike. It does not re-implement `choose`, which would bypass `RuleBridge.choose`'s relays and `GuardAgent`'s and `ThresholdGuard`'s `choose`: `act = super().choose(b, t)`; if `act` is an open and the b3 draw < `spread`, it is retargeted to the least-crowded live subtask (ties as in Terms);
  - `shareAll` makes the share policy 'always' on that turn (it sets `share='always'` around `_shareable(self, b, kn, t, *a)`, since `GuardAgent` calls `_shareable(b, None, t, ks)`), for `RuleAgent` and `ViewAgent` alike;
  - `guess` passes to `RuleAgent`'s existing argument.

  Liars and mistaken members are not changed.
- **FR-A3** `trustOne`, `spread` and `shareAll` draw from `np.random.default_rng([seed, 22, slot])` (`guess` keeps `RuleAgent`'s existing draw), made only when `world['b3']` sets a non-default value. Without `world['b3']`, cells, configuration hashes, random streams and rows are those of today.
- **FR-A4** Mirror posts (P22-12): honest rule agents in squad s + 1 post a held cross clue on its mirror when its leading value there is missing, different or unconfirmed. Built in Phase 20 (its FR-A4, amended 2026-11-10); B3 tests it (AC-4).

### Part B: the fit

- **FR-B1** `FIT_CELLS`: the 15 clean cells (target `pooledShare`) and 17 counting-board liar cells (target `contamination`) of design-low-level, with their study, arm, fault, N and Claude seeds. `claudeTargets(rows)` returns each cell's mean, standard error (floored at 0.01) and board count from the cached `runs.csv` files.
- **FR-B2** `simCell(cell, theta, seeds)`: the numpy counterpart of a fit cell, built by `colonyCell(..., 'numpy')`, by `bridge_grid.c1Cell(study, arm, seed, fault, runner='numpy')` for C1's cells (`colonyCell` has no bridge arms unless `arms=ARMS20`), or by `clueCell` for Phase 14's plain board, with `world['b3'] = theta`, on seeds 3000-3029, run by `b3Replay(cfg, seed)`: `colony_trace.replay`'s numpy branch with members built by `stage4Members` (which applies Phase 20's `bridgeMembers`) and then `b3Members`, and rows `stage4Columns`, or on bridge boards `bridge_mech.c1Columns(cfg, rp)` (as `runC1Cell`'s numpy rows: `stage4Columns` + `bridgeColumns` with the replay's answers + `contestColumns`; not `stage4Columns` + `bridgeColumns` alone, since `crossContamination` needs `rp.answers`). At θ_default `b3Replay` equals `replay` (a regression test). It returns the cell mean of the target.
- **FR-B3** `gridSim(cells, grid)` simulates every grid point once and caches the cell means on disk (`results/multiagent/b3/grid/*.csv`), so folds, bootstraps and refits reuse them.
- **FR-B4** `fit(cells, sims, drop=())`: the grid point minimizing the loss of P22-4 over `cells` minus `drop`. `FOLDS`: `S1`, `S4`, `S4b` and the secondary `P14` (P22-5, P22-11). `heldOut(fold)`: the fold's loss at its own fit, on the cells it left out, beside θ_default's loss on the same cells.
- **FR-B5** `chooseKnob(sims)`: for each candidate, the summed held-out loss over `S1`, `S4` and `S4b` on the coarse grid; the lowest wins, ties to `spread` (P22-2). The fine grid then runs for that candidate only.
- **FR-B6** `bootTau(cells, sims, n=200)`: the standard deviation of the fitted θ over resamples of Claude boards within cells, floored at 0.1.
- **FR-B7** `refit(theta0, tau, pilotTargets, sims)`: the penalized fit of P22-6. `pilotTargets` maps each pilot measure to its simulated cell, pilot value and s. Parameters with no pilot measure keep θ0.
- **FR-B8** `fitHealth(fits)`: flags any parameter at a range bound, and H22-3 (reported for all three keep-output candidates, not only the chosen one, since `chooseKnob` picked it on the same folds; P22-18) (held-out loss below θ_default's in at least 2 of 3 folds).

### Part C: forecasters and the entry point

- **FR-C1** `Effect(id, hyp, measure, fault, N, terms, naive, represented=True, note='')`, with `terms` a tuple of (coefficient, arm). `estimate(rows, effect)` returns the per-seed values of Σ c × arm and their mean, for rows levelled `'<arm>|<fault>'`. An experiment may pass its own `estimateFn` (A2 does).
- **FR-C2** `C1_EFFECTS` and `A2_EFFECTS` as design-low-level (P22-8). `RETRO_EFFECTS`: paper2's 15 scored items (11 conclusive, 4 no calls) and Phase 14's 2 team-size calls, with each study's frozen estimate rule.
- **FR-C3** Forecasters:
  - `forecastSim(effects, cellFn, theta, seeds)`: runs every represented effect's arms through `cellFn` and signs each effect by the 95% interval over seeds (`bootSeeds`, 2,000 resamples);
  - `forecastPilot(effects, pilotRows, priorRows, estimateFn)`: the point estimate from pilot rows, filling arms the pilot lacks from `priorRows`, the cached Claude rows that existed before the experiment; when an arm is in neither, every-design-helps' sign for that effect, marked `fallback` (P22-17);
  - `forecastNaive(effects)`: each effect's `naive` sign.
- **FR-C4** The entry point `forecastExperiment(exp, effects, cellFn, pilotRows, priorRows, pilotMap, reused, estimateFn=estimate)`:
  1. fits θ0 on `FIT_CELLS` minus `reused` (the cached cells the experiment reuses as arms);
  2. refits it on the pilot through `pilotMap` (pilot measure to parameter target);
  3. returns the five lines (fitted, prior-only, unfitted, pilot-only, every-design-helps) per effect, with θ_default, θ0, θ_pilot, τ, seeds and the code commit.

  Unrepresented effects get only the pilot-only and every-design-helps lines.
- **FR-C5** `writeForecast(f, path)` writes sorted-key JSON with a trailing newline and returns its SHA-256. A rerun at the same commit gives the same bytes.
- **FR-C6** `c1Forecast()`: `forecastExperiment('C1', C1_EFFECTS, ...)` with Phase 20's numpy cells at 64 agents (`ARMS20`, `bridgeMembers`, `RuleBridge`); pilot rows from the `runs.csv` that Phase 20's T8 writes (its folder is Phase 20's choice); `reused` = Stage 4's `squads|independent` at 64 and the 64-agent run's `colonyGuards|independent`; `pilotMap` = `contamination` on each pilot board (arm-matched) to `trustOne`. It writes `specs/multiagent/phase20/c1_predictions.json`.
- **FR-C6b** `c1Forecast`'s file carries a `note` (P22-19): every-design-helps says + on all 8 C1 effects as decided (P22-8); for C1-7 (clean `bridge1` − `squads`) that is a convention, since `bridge1` combines a handicap (coupling) with a design (the bridge), and for the margins (C1-2 to C1-4) + is a size claim ("keeps more than half"), not "beats its reference".
- **FR-C7** `a2Forecast(pilotRows)`: every-design-helps and pilot-only lines for `A2_EFFECTS`, through `a2Summaries`' per-team estimates; fitted and unfitted marked "not represented". It writes `specs/multiagent/phase21/a2_predictions.json`.

### Part D: scoring, the retrospective check and the gate

- **FR-D1** `scoreExperiment(predPath, observed)`: `observed` maps effect id to (estimate, ci) from the experiment's own report. It writes `<exp>_score.json` beside the forecast: per item and forecaster, right, wrong or no call; per forecaster, the counts on the common set and on all items.
- **FR-D2** `retrospective()`: for each fold, fit θ0 without the fold, refit on that study's pilot (seed 1890), forecast with each study's frozen estimate rule, and score all four forecasters (and prior-only) against the saved Haiku results (`colony_score.json`, `colony4_score.json`, `stage4b/metrics.json`; Phase 14's `scale_score.json` for the `P14` fold). The unfitted line must reproduce paper2's 9 of 11 and every-design-helps its 10 of 11. Writes `results/multiagent/b3/retro.json` and `retro.md`.
- **FR-D3** `poolScores(paths)` and `gateB3(pooled, plan)`: H22-1 by P22-10's counting rule; the exact McNemar p of fitted against each alternative; H22-4 (fitted against prior-only), descriptive. `gateB3` refuses to report while any experiment listed in `B3_PLAN['experiments']` has a frozen forecast but no score.
- **FR-D4** `writeB3` (`results/multiagent/b3/report.md`, `score.json`) and `figB3` (`b3.png`: right, wrong and no-call counts per forecaster, per experiment and pooled; the retrospective beside). `syntheticB3` builds fit, forecast and score files with known counts for the offline tests of `writeB3`, `figB3` and `gateB3`. Beside C1's forecast the report notes P22-20: in the unfitted simulator relays feed scripted liars' coupled solves (liars trust single posts), and honest coupled solves are 0 at θ_default.
- **FR-D5** `B3_PLAN`, frozen with `coopHash` and pushed before the week-1 fit. It holds:
  - the knobs, ranges, defaults and the candidate-selection rule;
  - `FIT_CELLS`, `FOLDS`, the loss, the grids and the seeds;
  - the refit rule, the forecasters and the sign rules;
  - the scoring rule, the common set, the gate's counting rule and its minimum of 8;
  - the experiments it will forecast (C1, C2, C4 part b; A2 for the two non-simulator lines);
  - `exploratory=True`.
- **FR-D6** `demo_b3` with three stages behind `EXPLRL_B3_STAGE`: `quick` (tiny grid, synthetic Claude rows, a fake experiment), `fit` (the week-1 fit and the retrospective check) and `forecast` (one experiment's forecast, by name).

## Quality requirements

- **NFR-1** Phase 5-21 reference outputs and configuration hashes are unchanged. At θ_default, the simulator reproduces the cached numpy rows of `results/multiagent/colony/forecast/runs.csv` and `forecast4/runs.csv` for every cell it reruns, column for column. The committed prediction and score files of Phases 13-18 (`forecast/predictions.json`, `scale_predictions.json`, `colony_predictions.json`, `colony4_predictions.json`, `colony4b_predictions.json` and their scores) are never rewritten, and their SHA-256 are unchanged. `paper2/make_assets.py` regenerates `numbers.tex` byte-identically.
- **NFR-2** Offline only: no network, no key, no GPU, no `anthropic`. B3 makes no API calls. It reads Claude rows from `runs.csv` files and never replays the response cache.
- **NFR-3** Seeds are fixed (simulator seeds 3000-3029). The fit, the grid cache and every forecast are byte-identical on rerun at the same commit.
- **NFR-4** Each module stays under 200 lines. `colony_agents` (198 lines), `clue_agents` (199), `colony_trace` (199) and Phase 20's modules take no B3 code. The behaviours live in a new module that wraps members, as `stage4Members` does.
- **NFR-5** Notebook first: each module is written in its notebook and exported with `nbdev-export`, then `nbdev-clean`. New notebooks are added to `nbs/sidebar.yml`. Multiprocess runs go through `tools/b3_run.py`, a script with a `__main__` guard (macOS spawn).
- **NFR-6** The simulators never see the Claude rows of a cell they predict or compare against: not in the fit (P22-5), not in the refit (only the experiment's pilot). Pilot-only is "the pilot plus what was already known": it may read Claude rows that existed before the experiment, including the cached cells the experiment reuses as reference arms. This favours pilot-only and makes Gate B3 harder for the fitted simulator; the report says so (P22-16).
- **NFR-7** Each forecast file is committed and pushed, and its SHA-256 recorded in the experiment's frozen plan, before that experiment's main run. `B3_PLAN` is pushed before the week-1 fit.

## Acceptance criteria

- **AC-1** Regression: NFR-1, and the full suite passes.
- **AC-2** Defaults: with `world['b3']` absent or all default, a numpy cell at 8, 16, 32 and 64 agents (plain, counting board, guards, squads) gives rows and turn logs equal to today's, and no extra random draw is made.
- **AC-3** Behaviours, on hand-built boards:
  - `trustOne=1` makes a one-sender leading value known, and `trustOne=0` does not; the decision is the same on every turn of the board;
  - `spread=1` opens the subtask with the fewest openers;
  - `shareAll=1` shares a held clue whose subtask nobody has open;
  - each works on a `plain` cell (`RuleAgent`) and a Phase 14 cell as well as on counting-board agents;
  - each changes only the members FR-A2 names.
- **AC-4** Mirror posts (P22-12): on a 16-agent bridge board, an honest holder in s + 1 posts its cross clue on the mirror, and a `RuleBridge` in s relays it. With `spread` = 1 a `RuleBridge` still relays.
- **AC-5** Fit: on synthetic Claude targets made by the simulator at a known θ, the grid fit recovers it within one grid step. Each fold drops exactly the cells listed in design-low-level. `chooseKnob` follows the frozen rule. `bootTau` returns 0.1 on identical resamples; `fitHealth` flags a planted bound hit and a planted H22-3 failure; a second `gridSim` call makes no new boards; `b3Replay` at θ_default equals `replay`.
- **AC-6** Refit: with a pilot equal to θ0's simulation, θ_pilot equals θ0. With no pilot measure for a parameter, that parameter keeps θ0. With a large τ, θ_pilot approaches the pilot-only fit.
- **AC-7** Forecasters: on a fake experiment with known effects, each forecaster gives the signs of FR-C3. Pilot-only gives every-design-helps' sign, marked `fallback`, for an effect with an arm absent from both the pilot and the prior rows. An unrepresented effect has only two lines. `a2Forecast` writes 4 items with two lines each.
- **AC-8** Retrospective: the unfitted line reproduces paper2's 9 right of 11 and every-design-helps its 10 of 11, item by item (`DefenceRight`, `DefenceNaiveRight`).
- **AC-9** Files: `writeForecast` is byte-identical on rerun; `scoreExperiment` follows paper2's rule on hand-made cases (a predicted 0 on a conclusive outcome is wrong); `gateB3` applies the counting rule, the minimum of 8 and the refusal of FR-D3; `b3_run.py grid` refuses an unfrozen `B3_PLAN`; `writeB3` and `figB3` run on `syntheticB3`.
- **AC-10** C1's entry point: with Phase 20's code and a fake pilot, `c1Forecast` writes a file with 8 effects and five lines each, and its SHA-256 can be placed in `C1_PLAN`.

## Out of scope

- Calibration and stated confidences: B3 reports counts (the plan). Forecasting every effect with a confidence is paper2's second future direction, not this phase.
- Forecasting trained 3B policies (A1, C3, C4 part a) and Phase 20's part b.
- Behaviours beyond the two the plan names: ignoring a coordinator, herding in text foraging, re-posting held clues (Phase 15's `repost` variant, the nearest rule-agent analogue of A2's drop-only prompt).
- Representing rule text, records, offers or Claude liars with rule agents. C2's record readers and C4's liar stand-in belong to those specs (P22-15).
- Changing any frozen forecast, score or plan of Phases 13-21.
