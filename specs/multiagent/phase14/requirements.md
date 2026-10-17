# Requirements: Phase 14, publicity of trust information and team-size scaling

Part of [README.md](README.md) (plan and decisions P14-1 to P14-5). Builds on Phase 13 (the clue-board options in `clue_fix`, `fix_grid`, `fix_report`, `demo_fix`) and its forecast method (`tools/rl_forecast.py`, `tools/forecast_score.py`).

Terms: as Phase 13 ([../phase13/requirements.md](../phase13/requirements.md)); in addition:

- **Public / private:** whether a piece of trust information (a track record, a check result) is shown to every agent or only to the agent it belongs to.
- **Free / costly:** whether obtaining it takes the agent's turn.
- **Publicity effect:** in loss recovered, the mean over the public arms (`record`, `verifyPublic`) minus the mean over the private arms (`recordPrivate`, `verify`), paired on seed. **Cost effect:** the free arms (`record`, `recordPrivate`) minus the costly ones (`verify`, `verifyPublic`).
- **Liar share:** the fraction of agents that are scripted liars (a quarter in Part B).

## Functional requirements

### Part A: two new settings of the existing options
- **FR-A1** `record` takes `False`, `True` (Phase 13: public) or `'private'` (no aliases, so equal configurations give equal cells): with `'private'`, the track record shown to agent i next to a post by agent a counts only a's shares for subtasks that agent i solved. Rules sentence: "Each shared clue shows how many of its sender's earlier shares were true, counted over subtasks you solved yourself."
- **FR-A2** `check` takes `False`, `True` (Phase 13: private) or `'public'`: with `'public'`, a check's result goes to every agent: each agent's next observation carries `Checked by agent 2: T3 x mod 7 = 4 (from agent 1) is false.` (the checker's own line as Phase 13), and every agent's known clues apply the result as the checker's do in Phase 13. Rules sentence: "'check' a clue on the board (target = its subtask, clue = its text): next turn every teammate and you learn whether it is true; checking takes your turn." `clue_agents` is unchanged: `known` already takes a checked set, and the environment passes the shared one.
- **FR-A3** Defaults unchanged: Phase 13's `record=True` and `check=True` give byte-identical rules, observations, schema and rows (their cached reruns stay identical).
- **FR-A4** `FIX_ARMS` gains `recordPrivate = dict(record='private')` and `verifyPublic = dict(check='public')`; `trustGrid()` (study `trustA`): the two new arms at N 4, with one liar and without, seeds 900-909; `trustGrid()` and the plans live in a new `scale_grid` module (`fix_grid` would pass 200 lines); `trustSummaries` in a new `scale_report` module adds the publicity and cost effects and their difference.

### Part B: the team-size sweep
- **FR-B1** `scaleGrid()` (study `scaleB`): blackboard, N in (8, 16, 32), seeds 900-904, 40 turns; clean cells for `baseline` and `request`; cells with `nLiar = N // 4` for `baseline` and `record`. `scalePilotGrid()`: N = 32, `baseline`, clean and with liars, seed 900.
- **FR-B2** The cost rule: if the pilot's measured cost per call projects the main grid above $40, N = 32 runs seeds 900-902 only; if that still projects above $40, stop and ask. The rule is in the plan before the pilot.
- **FR-B3** `scaleSummaries` (in `scale_report`): per N, the request board's gap closed (as A1) and the record's loss recovered (as A2), and the baseline's pooled share and honest loss; per arm, the trend across N.

### Part C: the numpy forecast
- **FR-C1** `tools/scale_forecast.py run`: the Phase 11 rule agents (blackboard, share policy as Phase 11's numpy cells) at N in (4, 8, 16, 32, 64), clean and with a quarter liars, 20 seeds; output per N: pooled share (clean), honest loss (welfareHonest clean minus with liars); predicted signs of the N 8 -> 32 changes with bootstrap intervals over seeds.
- **FR-C2** The forecast's output and predicted signs are committed before any Part B LLM cell runs (the pilot included); `tools/scale_forecast.py score <runs.csv>` scores them against the Haiku baseline cells: each side's change is the mean at N = 32 minus the mean at N = 8 with a bootstrap interval resampling seeds within each N (unpaired: boards differ by N); signs and agreement as the Phase 13 rule.

### Part D: report and docs
- **FR-D1** New `demo_trust`: quick (fake client), Part A main, Part B pilot and main, cached reruns (`llm`); report and figure per part.
- **FR-D2** Results in this README, `REPORT.md` (a Phase 14 section) and the preprints where they change a claim.

## Analysis plans (frozen before the main runs; exploratory)

`TRUST_PLAN` (Part A): loss recovered for `recordPrivate` and `verifyPublic` against `baseline` (as Phase 13 A2, Holm over the two); the publicity effect and the cost effect with bootstrap CIs over seeds, and their difference (H14-1, H14-2); each arm's no-liar cost; mechanism: checks, checks found false, and the mean number of checked shares behind each private record.

`SCALE_PLAN` (Part B): per N, `request`'s pooled-share gap closed and `record`'s loss recovered, paired on seed (H14-3, H14-4; Holm over the three N within each arm); the baseline's pooled share and honest loss per N; the numpy forecast's score (H14-5).

## Quality requirements

- **NFR-1** Phase 5-13 reference outputs unchanged (cached reruns byte-identical), including Phase 13's `record` and `verify` cells.
- **NFR-2** Offline tests need no network, key, `anthropic` or `torch`.
- **NFR-3** API spend under the $150 cap ($60.73 spent); Part A about $2, Part B up to $40.
- **NFR-4** Seeds fixed; replies cached; reruns byte-identical.
- **NFR-5** Each module under 200 lines (`clue_agents` is at 199: new logic goes in `clue_fix`).

## Acceptance criteria

- **AC-1** Regression: NFR-1; the full suite passes.
- **AC-2** New settings: the private record counts only the viewer's own solved subtasks (hand-made boards); a public check's line reaches every agent's next observation and every agent's known clues drop a false clue; defaults byte-identical; rollout rows and turn logs equal `runClue`'s with each new setting.
- **AC-3** Grids: sizes, liar counts (N // 4), shared seeds, Phase 13 cells reused where identical.
- **AC-4** Pilot: invalid replies under 5% at N = 32; tokens and cost per call measured; the cost rule applied as written.
- **AC-5** Forecast committed before Part B's LLM cells; scored with the frozen rule.
- **AC-6** Every `TRUST_PLAN` and `SCALE_PLAN` item reported, labelled exploratory; cached reruns byte-identical and free.

## Out of scope

LLM liars; N = 64 with LLM agents; RL at larger scale (separate: more seeds on Colab); other channels than the blackboard in Part B.
