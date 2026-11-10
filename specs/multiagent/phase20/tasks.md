# Tasks: Phase 20

Status (2026-11-10): specified, decisions made 2026-11-09, amended by Phase 22's P22-12 and P22-8 on 2026-11-10, not built. The user decided P20-1 to P20-14 (README) on 2026-11-09 and P20-15 to P20-16 on 2026-11-10; P20-14 adds 15 clean boards. **Before T8**, `Budget` counts by month (T0), and the user approves the pilot's estimated cost (P20-8). **Before T9**, B3's fitted simulator exists (P20-13); T9 and T10 wait for it. **After T10**, Gate C1 goes to Phase 19: it sets A1's training world (the user, 2026-11-08), so A1 also waits for B3.

Order: T0-T6, then T7 (part b and the bridge check) at any time after T6, and T8 (the pilot) at any time after T6. T9 and T10 wait for B3. T11 follows T10.

Rules are as in Phases 16-19:

- notebook first, then export, with one notebook per test call;
- `nbdev-clean` after creating or editing a notebook;
- new notebooks added to `nbs/sidebar.yml`;
- modules under 200 lines;
- offline tests without a GPU or `anthropic`;
- Phase 5-19 outputs and hashes unchanged;
- each frozen plan is pushed before its cell runs;
- no paid call before T8.

## T0. Monthly ledger (shared with Phase 21; about 2 hours)
- **Who:** whichever of Phases 20 and 21 is built first does it; the other reuses it.
- **Files:** `nbs/llm_budget.ipynb` -> `explRL/llm_budget.py` (`Budget`).
- **What:** each new ledger entry carries `month` (UTC `'YYYY-MM'`). `spent()` counts only the current month's entries; undated legacy entries count as earlier months. `spentAll()` gives the all-time total, for reports.
- **Done when:** NFR-7's tests pass (a month boundary and legacy entries), the full suite passes, and on the real ledger (491,301 undated entries, $233.18) `spent()` is $0 in November 2026 and `spentAll()` is $233.18.
- **Status (2026-11-10): done.** `Budget(cap, ledger, month=thisMonth)`; new entries carry `month`; `spent()` counts the current UTC month (legacy lines without `"month"` are skipped before parsing), `spentAll()` every entry; `test_budget_month` in `nbs/llm_budget.ipynb`. On the real ledger: `spent()` $0.00 for 2026-11, `spentAll()` $233.18, `remaining()` $250.00. Full suite passes. Phase 21 reuses it.

## T1. The bridge board (about 1.5 days)
- **Files:** `nbs/bridge_board.ipynb` (new: `dealBridges`, `BridgeBoardEnv`, `BridgeView`, `relaySource`), the hook in `nbs/colony_board.ipynb` (`squadView`).
- **Done when:** AC-2, AC-3, AC-4 (the board's half) and AC-6 pass: `test_couple`, `test_mirror_isolation`, `test_deal_bridges`, `test_relay_credit`. Phase 18's and 19's `colony_board`, `clueboard` and `contest` tests still pass.
- **Status (2026-11-10): done.** `explRL/bridge_board.py` (187 lines: `BRIDGE_KEYS`, `dealBridges`, `checkBridge`, `BridgeBoardEnv`, `BridgeView`, `relaySource`) and the `squadView` hook (`colony_board` stays at 190). Notes: relay credit overrides `_reward` in `BridgeBoardEnv` (`_creditTo` returns `(agent, divisor)` pairs; equal to `clueboard`'s without relays), since `clueboard` is at 197 lines; `mirrors(i, every=None)` gives liar slots all mirrors (P20-5) and holders only theirs (P20-16); `BridgeView.crossClues()`. Prompt-level AC-3, parsing and numpy posters are T2's.

## T2. Prompts, parsing, rule agents and rollouts (about 1.5 days)
- **Files:**
  - `nbs/bridge_agents.ipynb` (new: the three rules, `bridgeLines`, `parseBridge`, `RuleBridge`, `bridgeMembers` (with honest rule agents' mirror posts, P22-12), `MirrorLiar`, `bridgePromptTokens`), the `stage4Members` hook in `colony_board`;
  - hooks in `nbs/clue_colony.ipynb`, `nbs/clue_text.ipynb`, `nbs/clue_runs.ipynb` and `nbs/clue_roll.ipynb`.
- **Done when:**
  - `test_relay`, `test_bridge_liars`, `test_bridge_prompts` and `test_rollout_bridges` pass (AC-4, AC-5, AC-7);
  - a recorded 64-agent fake-client board shows mirror lines, bridge lines and relays in the turn log;
  - a 16-agent rollout in squads of 4 with bridges reports its longest prompt per role.
- **Status (2026-11-10): done.** `explRL/bridge_agents.py` (198 lines) and the hooks (`colony_board` 191, `clue_colony` 150, `clue_text` 196, `clue_runs` 107, `clue_roll` 197; `colony_trace`, `clue_agents`, `colony_agents` and `clueboard` unchanged). Pre-Phase-20 prompts, rows and numpy rows hashed before and after: unchanged. A 64-agent numpy board at seed 1890: 260 mirror posts (66 false, all liars'), 92 relays; the channel holds only same-squad posts. Notes: `RuleBridge` is a mixin on every honest numpy member (only bridges relay; all make P22-12 mirror posts); `bridgePromptTokens(cfg, seeds, tok=None, policy=None)`; `MIRROR_RULE` goes to every agent on a coupled board (design-low-level). The `coopRows` hook and `test_c1_numpy` are T3's.

## T3. Measures (about half a day)
- **Files:** `nbs/bridge_mech.ipynb` (new: `bridgeColumns`, `isPhase20`, and the core measures of FR-D5 through Phase 19's `contest_eval.contestColumns`, `rl19_measures.ratio` and `lags`, and `rl19_spec.dolIndex`).
- **Done when:** every measure in design-low-level's table is checked on a hand-built board with known relays, false relays, mirror posts and a contaminated answer, and `test_c1_measures` (AC-11) passes. The bridge columns appear in `coopRows` and in Claude rows only for bridge worlds; `contestColumns` is added to every C1 row, clean and reused rows included.
- **Status (2026-11-10): done.** `explRL/bridge_mech.py` (162 lines: `isPhase20`, `tokensByRole`, `bridgeColumns`, `c1Columns`, `runC1`, `runC1Cell`, `reusedRows20`, `boardDol`, `tokPerSolved`, `coreMeasures`) and the `coopRows` hook (`clue_roll` 199). `runC1Cell` and `reusedRows20` add the bridge columns (zeros or NaN without bridges) and `contestColumns` to every C1 row; `coopRows` adds bridge columns only for bridge worlds. Tests: `test_c1_measures`, `test_c1_numpy`, `test_c1_rows`. In the numpy simulator honest rule agents never use a relay: a relayed value has one sender, below `Q` = 2, and `RuleBridge` relays a clue only while the board lacks it (seed 1890, 64 agents: 92 relays, 0 honest coupled solves). The user decided on 2026-11-10 to leave this as is: it matches what honest agents see, and B3's fitted `trustOne` decides whether relays are used (Phase 22).

## T4. Grid, plans, cost rule and the Colab cell (about 1 day)
- **Files:**
  - `nbs/bridge_grid.ipynb` (new: `ARMS20`, the grids with `C1_CLEAN` (P20-14), `reusedCells20`, `c1Estimate`, `costRule20`, `pilotCheck20`, `C1_PILOT_PLAN` and `C1_PLAN` unfrozen, `squadEvalSuite`, `reusedPartB`, `bridgeCheckCells`, `projectHours20`);
  - the "Phase 20" section of `nbs/colab_clue_rl.ipynb`.
- **Done when:**
  - `test_c1_grid` (38 new cells, 15 of them clean; AC-10) and `test_c1_hashes` pass;
  - `reusedPartB` finds 180 one-board rows (9 models × 20) whose configuration matches the new cells apart from `squads`;
  - the Colab cell compiles with Drive paths and claims models.
- **Status (2026-11-10): done.** Split to stay under 200 lines: `explRL/bridge_grid.py` (158: arms, grids, `C1_CLEAN`, `reusedCells20`, `c1Estimate`, `squadEvalSuite`, `reusedPartB`, `bridgeCheckCells`, `projectHours20`) and `explRL/bridge_plan.py` (95: `C1_PILOT_PLAN`, `C1_PLAN` unfrozen with a B3 forecast placeholder, `costRule20` always 'ask', `pilotCheck20`). 38 new cells (15 clean), 3 pilot, 16 reused; main $25.28-30.63, pilot $1.76-2.21, total $27.05-32.83; part b 5.04 + check 0.52 A100 h. `reusedPartB` finds the 180 rows. `test_c1_hashes`: 26 plan, 5 grid and 2 RL config hashes unchanged. The Colab "Phase 20" cell (part b and the bridge check, levels `warm|bridge8` and `warm|bridge4`, prompt lengths to `check_c1/prompts.json`) compiles and dry-runs with stubs. `c1Estimate` prices arms the pilot lacks at the pilot's highest cost per call.

## T5. Report and demo (about half a day)
- **Files:** `nbs/bridge_report.ipynb` (new: `c1Summaries`, `gateC1`, `partBSummaries`, `writeC1`, `figC1`, `syntheticRows20`), `nbs/demo_c1.ipynb` (new: quick, pilot, main, part b).
- **Done when:** `test_c1_report` (AC-9) passes, and `demo_c1` quick runs end to end with the fake client and writes a report and `c1.png` from synthetic rows.
- **Status (2026-11-10): done.** Split to stay under 200 lines: `explRL/bridge_report.py` (156: `planned20`, `gateC1`, `c1Summaries`, `partBSummaries`) and `explRL/bridge_write.py` (165: `writeC1`, `figC1`, `syntheticRows20`, `syntheticPartB`); `nbs/demo_c1.ipynb` (stages by `EXPLRL_C1_STAGE`: `pilot`, `main1`, `main2`, `main`; live cells flagged `llm`; part b flagged `train`). `test_c1_report` recovers every planted effect. Judgement calls: H20-3 needs a positive coupling cost as well as win-back above 0.5; H20-4 also reports a one-sided p. The live stages have not run.

## T6. Regression gate ($0)
- **What:**
  1. Replay every earlier live board through the cache-only client, so a miss raises and nothing is spent: Phase 18's pilot, Stage 1, 32 agents, Stage 3 and its pilot, 64 agents and its pilot, Stage 4 and its pilot, Stage 4b.
  2. Only then run the live-flag cached reruns.
  3. Run the full suite and Phase 19's tests.
- **Done when:** every saved column is equal, the cached reruns are byte-identical, and the full suite passes (AC-1). The reused cells (`reusedCells20`) replay with C1's columns added and every earlier column unchanged.

## T7. Part b and the 3B bridge check (Colab, one account, about 5.5 A100 hours)
- **What:**
  1. Run the "Phase 20" cell: `squadEvalSuite` (180 boards; the warm start and the final `r17mix` adapters as published, P20-10) and `bridgeCheckCells` (10 boards), resumable per model.
  2. Pack `explRL_c1b.zip`.
  3. On the Mac, run `demo_c1` part b: `partBSummaries` with `reusedPartB`.
- **Then:** report H20-6 and P20-11's relay rate and longest prompt to the user. This can run any time after T6, before or alongside T8-T10.
- **Done when:** 190 rows, and `results/multiagent/colony/c1b/report.md`.

## T8. Freeze and pilot (Mac, live, about $2)
- **What:**
  1. T0 is done. Report the pilot's estimated cost (about $2) to the user and wait for approval (P20-8).
  2. Freeze `C1_PILOT_PLAN` (with `cap=250.0` and its `capNote`, P20-9) and push.
  3. Run the pilot: `coupled`, `bridge1` and `bridgeGuard` at 64 agents, seed 1890.
  4. `pilotCheck20` and the cost rule. Rows go to `results/multiagent/colony/c1pilot/runs.csv`, with `contamination` and the bridge columns (B3 reads them). Copy `metrics.json` and `timing.jsonl` to `*_live` before any cached rerun.
- **Then:** report the checks, the cost per call by arm and the projection of the main run (38 boards; the clean boards at 2,560 calls each) beside the $35 ceiling to the user, and wait for approval (P20-8). **Stop and ask** on any failed check. The pilot has no clean board (P20-14).

## T9. Forecast refit and C1_PLAN
- **Needs:** B3's fitted simulator, specified and built (P20-13). It models bridges with `RuleBridge` (T2). If B3 is not ready, C1 waits here; there is no fallback.
- **What:**
  1. B3's T6 (`tools/b3_run.py forecast C1`, `c1Forecast()`) refits on the pilot, writes, commits and pushes `c1_predictions.json` (P20-13).
  2. Freeze `C1_PLAN` with its SHA-256, the pilot's verdict and projection (with the user's approval in `C1_PLAN['projection']['approved']`, which `demo_c1`'s main stage asserts), and push.
- **Done when:** `C1_PLAN['frozen']` is true and its content is `C1_PILOT_PLAN`'s plus the forecast, the verdict and the projection.

## T10. Main run and Gate C1 (Mac, live, about $25-31; then $0)
- **Needs:** T9, and the user's approval of the pilot's projection (P20-8).
- **What:**
  1. Run the 38 new boards (23 with liars, 15 clean) in one or two seed batches, about 3.5-5 hours. Between batches, stop only at 5% invalid replies or the cap.
  2. Run the full grid, new and reused cells, from the cache at $0.
  3. `c1Summaries`, `writeC1` and `figC1`.
- **Done when:**
  - `results/multiagent/colony/c1/report.md` reports Gate C1 (parts i and ii, with robustness), H20-3 to H20-5, H20-7, the inert-bridge flag and H20-8 (cost without liars per arm, with the `coupled` − `squads` and `bridge1` − `squads` clean contrasts), as frozen;
  - it reports the core measures per arm (FR-D5);
  - the forecast is scored;
  - spend is recorded on the ledger.

## T11. Gate C1 handoff and docs
- **What:**
  - Write the results in this phase's README, `results/multiagent/REPORT.md` and the research plan's Gate C1 line.
  - **Gate C1 passes**, and the inert-bridge rule does not fire or the user accepts bridges: Phase 19's README records squads with bridges as A1's training world, with C1's cost without liars (H20-8) beside it. Phase 19 then takes its bridged step (design-low-level, "Handoff to Phase 19"), and C3 stays eligible.
  - **Gate C1 fails:** Phase 19 records the fallback, squads without cross-squad subtasks, and C3 does not run.
  - Write the C4 part b world (`bridge1` with `fault='adaptive'`) into C4's spec when it is drafted.
  - Change the preprint and summary page only where a claim changes.
