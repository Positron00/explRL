# Plan: Phase 22, a better cheap screen (B3)

Status: **week-1 fit and retrospective done 2026-11-11 (fit health ok; H22-2 fails, fitted 7 of 11 against the unfitted 9); C1's forecast committed (T6). C1 scored 2026-11-11 (`c1_score.json`): of 8 items, 6 conclusive; fitted, prior-only, unfitted and every-design-helps 4 right and 2 wrong each, pilot-only 5 and 1. Next: A2's forecast.** Earlier: built and tested offline 2026-11-11 (T1-T3). The user accepted P22-1 to P22-15 as proposed and decided P22-16 to P22-20 after a review of the specs, and P22-21 on 2026-11-11 (table below). Where the code differs from the designs, design-low-level's "As built" section says so. This phase is experiment B3 of the Stage 1 research plan (project B, "evaluate how teams of Claudes behave as they grow"). It makes no API calls and uses no GPU: numpy on the Mac, on cached rows and on the pilots that other experiments pay for.

**Order relative to the plan.** The plan runs B3 over weeks 1-16. The fit and a retrospective check come in week 1. Then each Claude experiment gets a forecast refit on its own pilot and frozen before its main run:

- **C1 (Phase 20) waits for B3** (the user, 2026-11-09, P20-13). C1's main run cannot start until B3's simulator exists and has been refit on C1's pilot. There is no fallback to the unfitted rule agents. A1 (Phase 19) waits for Gate C1, so it waits for B3 too. So B3's week-1 work is on the critical path.
- **A2 (Phase 21) is exempt** (P21-8). Rule agents read no rules or records, so the simulator cannot represent A2's arms. A2 freezes the every-design-helps and pilot-only forecasts. B3 supplies those two forecasters; the fitted and unfitted lines read "not represented", which is not a deviation (Phase 21's P21-8 carries the same note).
- **C2 and C4 part b** are not specified yet. B3 gives them a generic entry point and lists what each must supply (P22-15).

B3's own result, its gate, is read when the last of these experiments has been scored (plan: week 16).

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the frozen plan, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Components, data flow, key decisions, gates |
| [design-low-level.md](design-low-level.md) | The two behaviours, fit cells and folds, the fit and refit, the four forecasters, effect lists, scoring, runtime derivation, tests |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |

## Why

The companion preprint (`paper2/`, "What Cheap Rule-Agent Worlds Predict About Teams of Language-Model Agents") scored three frozen numpy forecasts of the defences against Claude Haiku teams. Over the three, **11 calls were conclusive** (the Haiku 95% interval excluded 0):

| Forecast (frozen file) | Conclusive calls | Right | Wrong | No call |
|---|---|---|---|---|
| Stage 1, 8 and 16 agents (`colony_predictions.json`) | H18-1, H18-2, H18-3, H18-4 | 3 | 1: H18-4, guards predicted to cost more than they protect | 2 (H18-6, colony against confirm) |
| Stage 4, 16 to 64 agents (`colony4_predictions.json`) | H18-13, H18-14, H18-15, `did_guardDeal`, `did_squads` | 4 | 1: H18-13, guard copies predicted to hurt at 64 | 1 (`did_failFlag`) |
| Stage 4b, 32 agents (`colony4b_predictions.json`) | H18-17, H18-18 | 2 | 0 | 1 (H18-16) |
| **All** | **11** | **9** | **2** | **4** |

A forecaster that says every tested design helps (sign + on every effect) is right on 10 of the 11. Its one miss is H18-3: the counting board cost output on boards without liars (`paper2/make_assets.py`, `DefenceNaiveRight`). So the simulation's 9 shows agreement on direction more than screening power.

The preprint traced the misses to two things Claude teams do that the rule agents do not:

- **Claude teams keep their output without liars as teams grow.** On Phase 14's plain board, rule teams' pooled share without liars fell from 0.51 to 0.36 (8 to 32 agents), Haiku's from 0.41 to 0.34. The numpy forecast predicted a change of -0.156; Haiku's was -0.065 [-0.081, -0.048]. With less to lose, rule teams lost less to liars as they grew (-0.134), while Haiku teams lost more (+0.076 [0.013, 0.137]) (Phase 15). The same gap shows on the counting board: rule agents' clean pooled share fell 0.383, 0.342, 0.302 at 8, 16 and 32 agents, while Claude's was 0.363 and 0.361 at 8 and 16.
- **Claude agents build on values the counting board has not confirmed.** Rule agents use a posted value only when two agents posted it or they hold it. So only 0.15 of their honest answers on the counting board were built on a lie (0.06 with guards), against 0.60 for Claude (0.31 with guards). In the simulation, guards had little left to protect, which is why it called H18-4 wrong.

The plan's B3 card asks to give the rule agents these two behaviours as parameters, fit them to the cached runs, refit them on each experiment's pilot, and test whether the fitted simulator calls more effects right than the unfitted simulator, the pilot alone and the every-design-helps forecaster.

## Questions and hypotheses

| ID | Hypothesis | Role |
|---|---|---|
| H22-1 | Pooled over the Claude experiments it forecasts (C1, C2, C4 part b), the fitted simulator calls more effects right than each of the unfitted simulator, the pilot-only forecaster and the every-design-helps forecaster | Primary (Gate B3), a frozen counting rule (P22-10) |
| H22-2 | Retrospective, on paper2's 11 conclusive calls: the fitted simulator, fit without the scored study's cells, gets more right than the unfitted simulator's 9 | Week-1 check, not a gate (P22-11) |
| H22-3 | The fit moves the simulator toward Claude on cells it did not see: its held-out error on the fit targets is below the unfitted simulator's in at least 2 of 3 folds | Fit check (P22-11) |
| H22-4 | The pilot refit adds to the cached-run fit: the refit forecast calls more right than the prior-only forecast | Descriptive |

Each can fail. H22-1 fails if the fitted simulator ties or trails any alternative, which is likely against every-design-helps when most tested designs help. H22-2 fails if the two behaviours do not turn the two wrong calls (H18-4, H18-13) right, or turn a right call wrong. H22-3 fails if the knobs cannot reach Claude's measures within their ranges.

**The retrospective check is not a clean test.** The two behaviours were named by looking at these misses, so even with the scored study's cells held out, H22-2 is a check that the fit does what it was built to do. The forward score (H22-1) is the test.

## Design summary

- **Two behaviours as parameters** (P22-2), each 0 by default, so default runs are today's rule agents draw for draw:
  - `trustOne` (building on unconfirmed values): the probability that a counting-board agent counts a leading value posted by fewer than q agents as known. Decided once per agent, clue and value.
  - a behaviour-1 knob (keeping output as teams grow), chosen in week 1 from three frozen candidates by held-out error: `spread` (open the subtask fewest teammates have open), `shareAll` (share a held clue even when no teammate has its subtask open) or `guess` (the existing guess rate). `spread` is the default on ties.
- **Fit** (P22-3, P22-4). Targets are mechanism measures only, never the scored contrasts: clean pooled share on 15 cached clean cells, and the share of honest answers built on a lie (`contamination`) on 17 cached counting-board cells with scripted liars. A grid search minimizes the standardized squared error of cell means, with 30 simulator seeds (3000-3029, as Phase 18's forecasts).
- **Leakage** (P22-5). The retrospective check fits three times, each time leaving out every cell that enters the scored study's contrasts (leave one study out). A forward forecast's fit leaves out the cached cells the experiment reuses as arms (for C1: Stage 4's `squads` and the 64-agent run's `colonyGuards`, both at 64).
- **Pilot refit** (P22-6). A pilot has 1-3 boards. The refit is a penalized fit on the grid: the pilot's measures, weighted by the cached boards' spread, plus a Gaussian penalty pulling each parameter toward the cached-run fit, with a width from a bootstrap over cached boards (at least 0.1, two fine steps for `guess`). A parameter the pilot has no measure for stays at the cached-run fit. Only the two behaviours are refit.
- **Four forecasters** (P22-7), each giving a sign per planned effect:
  - **fitted:** the refit simulator; + or - when its 95% interval over 30 seeds excludes 0, else 0;
  - **unfitted:** today's rule agents, same rule;
  - **pilot-only:** the sign of the effect computed from the pilot's boards, with arms the pilot lacks taken from cached Claude rows that existed before the experiment; every-design-helps' sign if neither exists (P22-17);
  - **every-design-helps:** the sign meaning "the design is better than its reference" on every effect.
  - A fifth line, the cached-run fit without the pilot refit (**prior-only**), is reported for H22-4 and is not in the gate.
- **Effects** (P22-8). Each experiment lists its planned effects as signed linear combinations of arm means (contrasts and margins alike), oriented so + means the design does better. C1 has 8 (H20-1 to H20-5, with H20-5's two measures, and H20-8's two clean contrasts). A2 has 4, which no simulator represents.
- **Files and hashes** (P22-13). Each experiment's forecast is one JSON file in its own spec folder (C1: `specs/multiagent/phase20/c1_predictions.json`). Its SHA-256 goes into the experiment's frozen plan before the main run, as Phase 18 did for `colony4_predictions.json`.
- **Scoring** (P22-9). Paper2's rule: a forecast is right when the Claude 95% bootstrap interval over boards excludes 0 on the predicted side; wrong when it excludes 0 and the forecast had the other sign or 0; not scored when the interval spans 0. The gate counts items both simulators represent (the common set); items they do not represent (A2's) are counted for the other two forecasters in a secondary count.
- **Gate B3** (P22-10). The fitted simulator's right count on the common set must exceed each alternative's, pooled over experiments, with at least 8 conclusive items; else the gate is not read. Exact McNemar tests on the items where two forecasters differ are reported beside it, not gating. With so few calls, B3 reports counts, not calibration.
- **If the fitted simulator does not beat every-design-helps,** B3 reports that. No experiment changes: forecasts never gate experiments.

## Cost

**$0 of API calls and 0 GPU hours**, as the plan says. B3 reads cached rows and the pilot rows that C1, C2 and C4 part b pay for.

**Laptop time** (8 worker processes on the Mac), scaled from Stage 4's numpy forecast, 1,050 boards at 8-128 agents in 2 minutes (about 8.75 boards a second; Part 0's 10,080 boards at 4-128 agents took 10 minutes):

| Step | Boards | Time |
|---|---|---|
| Week-1 fit, coarse grid (3 candidate knobs × 6 × 6 values, 96 distinct points, 960 boards each) | about 92,000 | about 2.9 hours |
| Week-1 fit, fine grid for the chosen knob (11 × 11, 85 new points) | about 82,000 | about 2.6 hours |
| Default check (reproduces cached numpy rows) and the retrospective forecasts (3 folds × fitted and pilot-refit settings) | about 10,000 | about 20-30 minutes |
| C1 forecast: pilot refit (11 values of `trustOne` × 3 pilot cells × 30 seeds) and three forecasts (9 cells × 30 seeds each) | about 1,800 boards at 64 agents | under 30 minutes at an assumed 2 seconds per 64-agent board |

A 1-seed timing probe replaces these estimates before the fit (T4). **Engineering:** about 3 days (T1-T3), plus about 1.5 days for T5-T9 spread over the weeks their inputs arrive (tasks).

## Decisions (the user, 2026-11-10)

All fifteen were accepted as proposed by the user on 2026-11-10. In P22-6 the user chose no relay fit; in P22-15 C4 part b's spec chooses between the stand-in liar and marking the adaptive arms not represented. P22-8 and P22-12 are carried into Phase 20 (its FR-A4, FR-C4 and the `C1_PLAN` forecast row).

| ID | Question | Proposal |
|---|---|---|
| P22-1 | Role of B3's forecasts | Forecasts never gate or change any experiment. Each is frozen in the experiment's plan before its main run and scored after it. A2 stays exempt from the fitted forecast (P21-8). |
| P22-2 | The two behaviours as parameters | `trustOne` in [0, 1] for building on unconfirmed values, applied to counting-board agents (`ColonyAgent` and its subclasses, `RuleBridge`). For keeping output, three frozen candidates: `spread` in [0, 1], `shareAll` in [0, 1], and the existing `guess` in [0, 0.5]. Week 1 keeps the candidate with the lowest summed held-out error over the three folds; ties go to `spread`. All default to 0 (`guess` to the cell's own value). The draws of `trustOne`, `spread` and `shareAll` come from a separate generator (`guess` keeps `RuleAgent`'s existing draw), created only when a parameter is not at its default, so default runs consume no new draws and reproduce today's rows and hashes. Alternative: fit all three candidates together (more freedom, harder to read). |
| P22-3 | What "fitted to explRL's cached runs" fits on | Clean pooled share on 15 clean cells (Phase 14's plain board at 8, 16 and 32; Stage 1's four arms at 8 and 16; the 32-agent run's two arms; Stage 4's two clean arms at 16), and `contamination` on 17 counting-board cells with independent scripted liars (Stage 1, the 32- and 64-agent runs, Stage 4, Stage 4b). Left out: arms rule agents cannot play (`record`, Stage 3's volunteers, Claude liars), other faults (mistaken members, colluding liars; reported as held-out checks), the `confirm` arm's liar boards (no counting display), and plain-board liar boards (no knob changes them). |
| P22-4 | Fit method | Grid search. Loss: the sum over cells of ((simulated mean − Claude mean) / Claude standard error)², with the standard error floored at 0.01. Coarse grid at steps of 0.2 for each candidate with `trustOne` (`guess`: 0.1, over [0, 0.5]), then a 0.1 grid for the chosen candidate (`guess`: 0.05). 30 simulator seeds, 3000-3029. The parameters' spread comes from 200 bootstrap resamples of Claude boards within cells, on the same grid (no new simulation). Alternative: a smooth optimizer (Nelder-Mead); the grid is cheaper to audit. |
| P22-5 | Leakage | Fit only mechanism measures (clean pooled share, contamination), never on a cell whose outcome is scored; some scored effects use the same measures on other cells (H18-2, H18-3, C1-7, C1-8). For the retrospective check, leave one study out: the Stage 1 fold drops all Stage 1 cells; the Stage 4 fold drops Stage 4's cells, the 64-agent `colonyGuards` cell and Stage 1's 16-agent `colonyGuards` liar cell (its references); the Stage 4b fold drops Stage 4b's cells and the 32-agent `colonyGuards` liar cell. For a forward forecast, drop the cached cells the experiment reuses as arms. Caveat stated in the report: folds may use later studies' cells, the behaviours were chosen after seeing the misses, and the keep-output knob is chosen on the same folds that H22-3 and the retrospective score (P22-18). |
| P22-6 | Refit on a pilot of 1-3 boards | A penalized fit on the grid: J(θ) = Σ over pilot measures ((sim − pilot) / s)² + Σ over parameters ((θ − θ0) / τ)². θ0 is the cached-run fit; τ is its bootstrap standard deviation, at least 0.1; s is the cached Claude boards' per-board standard deviation of that measure over √(pilot boards). Parameters with no pilot measure keep θ0 (C1's pilot has no clean board, so the behaviour-1 knob keeps θ0). Experiment-specific rates (C1's relays and mirror posts) are measured and reported beside the forecast, not fitted. Alternative: also fit a relay probability for `RuleBridge` on C1's pilot. |
| P22-7 | The four forecasters | As the design summary: fitted and unfitted signed by the 95% interval over 30 seeds; pilot-only by the sign of its point estimate (no interval exists for one board), 0 when not computable; every-design-helps by each effect's declared `naive` sign. Prior-only is reported, not gated. |
| P22-8 | What counts as a planned effect, and C1's and A2's lists | Every tested contrast or margin in the experiment's frozen plan, written as a signed linear combination of arm means on one measure. Per-arm descriptive levels are not effects. **C1:** H20-1, H20-2, H20-3, H20-4, H20-5 (false-relay share and honest pooled share), H20-8 (clean `bridge1` − `squads` and clean `squads` − `coupled`): 8 effects, all represented. H20-6 (3B part b) and H20-7 (per-arm contamination) are not forecast. **A2:** H21-1, H21-2, H21-3 at 8 and at 32: 4 effects, none represented by a simulator. **Orientation for every-design-helps:** a design (a defence, structure, record or bridge) beats its reference on every measure, clean boards included, and a handicap (coupling, a stronger liar) hurts. So it says + on all 8 C1 effects, including H20-4, whose hypothesis expects the opposite. |
| P22-9 | Scoring | Paper2's rule (above), with each Claude interval from the experiment's own `bootSeeds` estimate (2,000 resamples). A predicted 0 on a conclusive outcome is wrong. Primary count: the common set. Secondary count: all items, with an unrepresented item a 0 for both simulators. |
| P22-10 | Gate B3 | Read when the last forecast experiment is scored. Passes if, on the common set pooled over experiments, the fitted simulator's right count is strictly above each of the other three, with at least 8 conclusive items. Fewer than 8: "too few calls to read". Exact two-sided McNemar p for fitted against each alternative, reported, not gating. If it fails against every-design-helps: report it, record it in the plan's Stage 2 decision and in paper2's workflow paragraph; no experiment changes. |
| P22-11 | Week-1 retrospective check | Score all four forecasters on paper2's 11 calls (the 4 no-calls listed), with the fitted simulator fit per fold and refit on that study's own pilot (seed 1890: Stage 1's 4 boards at 16 agents, Stage 4's 3, Stage 4b's 3). Report to the user before C1's forecast. Not a gate. **Stop and ask** only on fit health: a parameter at the top of its range (P22-21), or H22-3 failing (held-out error not below the unfitted simulator's in at least 2 of 3 folds). Phase 14's two team-size calls are scored the same way in a fourth fold, as a secondary check. |
| P22-12 | Mirror posts by rule agents (a gap in Phase 20) | Phase 20's FR-A4 says honest rule agents ignore mirrors. Then, in the simulator, only liars post on mirrors and every `RuleBridge` relay is a lie. Proposal: amend Phase 20 so honest rule agents post a held cross clue on its mirror when its leading value there is missing, different or unconfirmed (`ColonyAgent`'s rule), before C1's forecast. This is structure, not a fitted behaviour, so the unfitted simulator gets it too. Alternative: B3 adds it in its own wrapper and leaves Phase 20 unchanged; C3's imitation data would then still lack it. |
| P22-13 | Files, hashes and freezes | `B3_PLAN` (fit cells, folds, grid, loss, candidates, selection rule, refit rule, forecasters, scoring and gate rules) frozen with `coopHash` and pushed before the week-1 fit. Each forecast in the experiment's spec folder (`c1_predictions.json`, `a2_predictions.json`, ...), committed, its SHA-256 and commit in the experiment's frozen plan before the main run. Scores beside each forecast (`c1_score.json`) and pooled in `results/multiagent/b3/score.json`. |
| P22-14 | Timing | Week 1: agents, forecasters, fit and the retrospective check. B3 does not need to be ready before C1's pilot, only before C1's main run. C1's forecast needs B3's fit, Phase 20's bridge board, `RuleBridge` and mirror posts (P22-12), and C1's pilot rows. A2 uses B3's every-design-helps and pilot-only functions if they exist at A2's freeze, else writes them by hand by B3's rule. C2 and C4 part b follow their pilots. B3's scoring ends with the last of them (plan: weeks 14-16). |
| P22-15 | What C2 and C4 part b must supply | Each spec supplies an effect list, a numpy cell builder and its pilot rows. **C2** also needs rule agents that read a public record: a `RecordReader` that discounts senders whose posted values went into wrong answers (the failed-answer record) or whose values were false (the oracle record), and liars that launder by posting true values first. The instruction-only arm cannot be represented and is marked so. **C4 part b**'s prompted Claude liars cannot be represented by scripted liars. Its spec chooses either a stand-in (a liar that lies on clues no guard holds and avoids contested clues) or marks the adaptive arms not represented. |
| P22-16 | Pilot-only and the reused reference cells | **Decided by the user, 2026-11-10** (spec review). Pilot-only may read Claude rows that existed before the experiment, including the cells the experiment reuses as reference arms (NFR-6 reworded). This favours pilot-only; the report says so. |
| P22-17 | Pilot-only's missing arms | **Decided by the user, 2026-11-10.** Where pilot-only cannot compute an effect (an arm in neither the pilot nor the prior rows), it takes every-design-helps' sign, marked `fallback`, instead of a 0 that would always score wrong. Beside the gate: fitted against pilot-only on the items pilot-only computes. |
| P22-18 | Knob selection and H22-3 | **Decided by the user, 2026-11-10.** Keep `chooseKnob` on the three folds; state that H22-3 and the retrospective are scored on the folds that chose the knob, and report both for all three candidates (no new simulation). |
| P22-19 | Every-design-helps on C1-7 and the margins | **Decided by the user, 2026-11-10.** Keep + on all 8 C1 effects (P22-8) and state both conventions in the forecast file's `note`: C1-7 combines a handicap and a design; the margins' + is a size claim. |
| P22-20 | Relays in the simulator (Phase 20's P20-17) | **Decided by the user, 2026-11-10.** At θ_default honest rule agents never build on a relay (one sender, below `Q` = 2), so the unfitted simulator calls no bridge benefit for honest agents on C1-1 to C1-5. `trustOne` applies to relayed values like any other value with fewer than `Q` senders, so the fitted simulator's bridge effects come from the fit. In the unfitted simulator relays feed scripted liars' coupled solves instead (liars trust single posts): honest coupled solves are 0 at θ_default (numpy `bridge1`, seed 1890: 32 coupled solves, all by liars). The report states both. |
| P22-21 | Which range bounds stop the fit (P22-11) | **Decided by the user, 2026-11-11, before `B3_PLAN` was frozen.** Only a knob fitted to the top of its range (trustOne, spread or shareAll 1.0; guess 0.5) is a bound hit that stops the week-1 fit to ask: the range may be too narrow. A knob fitted to 0 means that behaviour does not help; `fitHealth` reports it (`atZero`) and the run continues. A 2-seed smoke run had put the keep-output knob at 0 in most fits. |

## Relation to the other experiments

- **C1 (Phase 20).** C1's main run waits for B3 (P20-13). B3 needs from Phase 20: `BridgeBoardEnv` with a numpy runner, `RuleBridge` and `bridgeMembers` (FR-B4), and the mirror posts of P22-12. C1's pilot is seed 1890: `coupled`, `bridge1` and `bridgeGuard` at 64 agents with liars. B3 writes `c1_predictions.json` and Phase 20's T9 puts its SHA-256 into `C1_PLAN`. Phase 20's `C1_PLAN` names the 8 effects (its FR-C4, amended 2026-11-10).
- **A2 (Phase 21).** Exempt (P21-8). B3's every-design-helps and pilot-only forecasters give A2's two frozen forecasts. A2's pilot (team 2190, own records only; one drop-only board at 32 agents) lets pilot-only compute H21-2 and H21-3 at 32 only; for the other two it takes every-design-helps' sign (P22-17). A2's fitted line reads "not represented", which is not a deviation.
- **A1 (Phase 19).** Waits for Gate C1, so for B3. B3 does not forecast A1: its effects are trained 3B policies, which rule agents do not represent.
- **C2, C4 part b.** Forecast through B3's entry point once their specs exist (P22-15).
- **B1.** B3's fit targets are B1 measures (contamination, clean pooled share), read from cached rows as B1's eval does.
- **paper2.** B3 is the preprint's first future direction ("hybrid simulations"). Its retrospective check and Gate B3 change the preprint only where a claim changes. The committed prediction and score files of Phases 13-18 are never rewritten.
