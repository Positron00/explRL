# Tasks: Phase 19

Status (2026-11-08): T1-T4 done (offline tests and the `train`-flagged step test pass; committed in bfe5e5b), including the review's alignment fixes (README, implementation notes in design-low-level). The user's decisions are in the README. **Before T5:** C1 (Phase 20: bridges, then Gate C1) and A2 (prompted screens, then Gate A2) must be built and run; they set A1's training world and arm 4's records. **A1 waits for Gate C1, and C1's main run waits for B3's fitted simulator** (Phase 20, P20-13, 2026-11-09), so A1 waits for B3 too. T5 then trains A1 in squads with bridges, once C1's code exists. Two handoffs were accepted on 2026-11-09: relay credit (Phase 20's P20-12, T5) and A2's record format (Phase 21's P21-11, T8).

Rules are as in Phases 16-18:

- notebook first, then export, with one notebook per test call;
- modules under 200 lines;
- offline tests without a GPU or `anthropic`;
- Phase 5-18 outputs and hashes unchanged;
- each frozen plan is pushed before its cell runs.

## T1. Squads and guards in RL rollouts (about half a day)
- **Files:** `nbs/colony_board.ipynb` (`dealSquads`, wiring into the text environment), `nbs/clue_roll.ipynb` if `rollout` needs the option passed through.
- **Done when:** `test_squads` passes. A recorded 16-agent rollout in squads of 4 shows four separate boards with the dealt liars and guards.
- **Status (2026-11-08): done.** `dealSquads` and squads, guards and Stage 4 keys in `rollout` (`boardFactory`); `test_squads` passes (colony_board, clue_roll).

## T2. Contest credit, the penalty, records and the answer halt (about 1.5 days)
- **Files:** `nbs/contest.ipynb` (new: `ContestLog`, `sharePenalty`, `Records`), `nbs/clueboard.ipynb` (`scheme='contest'`, penalty hook).
- **Done when:** AC-2, AC-3, AC-3b, AC-4 and AC-4b pass: `test_contest`, `test_watchers`, `test_credit_equal`, `test_penalty` and `test_records`.
- **Status (2026-11-08): done** (the answer halt is left to T3's trainer). `explRL/contest.py`, `scheme='contest'` in `clueboard`; the five tests pass in `nbs/contest.ipynb`.

## T3. Config, trainer hooks, plans and Colab cells (about 1 day)
- **Files:**
  - `nbs/rl19_grid.ipynb`: `RL19Config`, arms, `SPEED19`, `PILOT19_PLAN`, the `RL19_PLAN` skeleton, `contestSuite` (gate grid, held-out sizes and faults, arm 4's sequences, the best arm at 64 agents), `projectHours19`;
  - `nbs/rl17_train.ipynb`: threat mix, hooks, records, answer halt;
  - the Phase 19 section in `nbs/colab_clue_rl.ipynb`.
- **Done when:** `test_rl19_hash` passes. `test_rl19_step` passes on the Mac with the tiny model. The cells compile with Drive paths and assert the freezes.
- **Status (2026-11-08): done.** `explRL/rl19_grid.py` (config, hash, arms, plans unfrozen, `projectHours19`, `evalAdapter19`), `rl19_step.py` (threat mix, `playStep`, `RecordBook`, the answer halt), `rl19_suite.py` (`contestSuite`, sequences, `WARM_ANSWERS` and pilot cells), `contest_eval.py` (`enforceK`, Phase 19 columns), hooks in `trainRL17` and `trainRL19`; the Phase 19 section of `colab_clue_rl` (three cells). `test_rl19_hash`, AC-6 and the answer-halt half of AC-4 pass offline; `test_rl19_step` passes with `--flags train` (`.venv-train`, 8 agents in squads of 4). See the implementation notes in design-low-level.

## T4. Report and demo (about half a day)
- **Files:** `nbs/rl19_report.ipynb` (measures, tests, `figRL19`), `nbs/demo_rl19.ipynb`.
- **Done when:** `test_rl19_report` (AC-7) and the full suite pass.
- **Status (2026-11-08): done.** `explRL/rl19_measures.py`, `rl19_spec.py` (arm 4), `rl19_report.py` (`rl19Summaries`, `writeRL19`, `figRL19`), `rl19_synth.py` (`syntheticRows19`, the power check `powerPrimary`); `nbs/demo_rl19.ipynb` (quick, power and main). `test_rl19_report` and the full suite pass.
- **Review fixes (2026-11-08): done.** The waiting rate over answers (the plan's definition); cost without liars and H19-3 against the warm start without guards; regret with the threshold chosen per liar count and lifetime; time to contest over every contest; gullibility per honest agent-turn, suppression, error correlation, the share of lies on a guarded clue; the division of labour (Gorelick) apart from specialization; role persistence between consecutive boards; H19-6 secondary; `WARM_ANSWERS` per guard count; records keyed by liar count; `evalAdapter19`'s checkpoint; the strict watcher timing; the world field and the Colab cells' Gate C1 and stability checks.

## T5. Training in squads with bridges (FR-A9; once C1's code exists, about half a day)
- **Needs:** Phase 20's bridged rollouts (C1), built and tested.
- **What:**
  - wire the bridge options into `rollout` and `RL19Config.world`, and set `BRIDGES_READY`; when the world is 'bridges', add Phase 20's keys (`couple=0.25`, `bridges=1` or the configuration Gate C1 sets) to `BASE19['world']` and to `world19e`, so every cell of `contestSuite`, `pilotCells`, `warmCells` and the sequences is bridged, the damage reference included (Phase 20's handoff, design-low-level there);
  - `SPEED19` records a bridge's prompt tokens (`bridgePromptTokens`, Phase 20 FR-B6, as `longestBridge`) and relays per bridge turn; `WARM_ANSWERS` is measured in the bridged world;
  - make the evaluation measures relay-aware through `relaySource`: in `contestsOf`, `uncorrected`, `liarPosts`/`guardLies` and misreporting, a relayed liar value is the liar's and a relay is not an honest false post, so the measures agree with the reward (FR-A9); test on a hand-built bridged board;
  - put the bridged world's wiring and measures in a new module `rl19_bridge.py`, so `rl19_grid`, `rl19_suite`, `contest` and `contest_eval` stay under 200 lines (NFR-5; `rl19_grid` is at 197 and `rl19_suite` at 198);
  - log a bridge agent's longest prompt plus reply (`longestBridge`) in each step's metrics;
  - add the bridge options to `contestSuite`'s 64-agent cells, and contamination across squads to `contestColumns`;
  - relay credit (Phase 20's P20-12, accepted 2026-11-09; FR-A9): under `'credit'` and `'contest'`, a relayed clue's credit share is split equally between the bridge and the first true poster on the mirror, and `ContestLog` treats a relayed liar's value as the liar's, through `relaySource`;
  - record Gate C1 in `RL19_PLAN['gates']` as {passed, inertFired, userAcceptsBridges} and set the plans' `world` from it (`worldFor19`: 'bridges' if it passed and bridges are kept, 'squads' if it failed or the user declined inert bridges; P19-8); `bridge1` for every arm;
  - P19-9: coupled answers out of `waitAnswers` and exempt from `enforceK` (reported apart); the reference cells coupled and bridged; single-squad held-out cells unbridged; the 64-agent cells in squads of 8;
- **Done when:** `rl19Config` builds an arm in squads with bridges; a recorded 16-agent bridged rollout shows the bridges' relays and `longestBridge`; the AC-8 refusals are replaced by tests of the bridged world, P20-12's split and a paid contest against a relayed lie included; the full suite and `test_rl19_step` pass.
- **Status (2026-11-08): waiting for Phase 20.** Until then `rl19Config`, `speedConfig19`, `pilotConfig19`, `warmCells` and `contestSuite` refuse 'bridges' with an error naming Phase 20.

## T6. Speed check (Colab A, about 3 A100 hours: 6 steps at about 1,080 s, plus 120 warm-start boards)
- **What:**
  1. Freeze `SPEED19` (its world from Gate C1) and push.
  2. Run 3 steps of arm 2 in squads of 4 and of 8.
  3. Record the step times, the longest prompt and a bridge agent's, invalid replies, `WARM_ANSWERS` (with 4 guards and without) and compute units per A100 hour.
- **Then:**
  - `projectHours19` replaces the README's estimates.
  - **Report to the user the projected pilot and main-run hours in A100 hours and in Pro+ compute units, and wait.**

## T7. Squad-size pilot (Colab A and B, about 6.5 A100 hours)
- **What:**
  1. Freeze `PILOT19_PLAN` and push.
  2. Run the pilot cell: 2 runs × 10 steps, split between the accounts by claims.
  3. Evaluate on the held-out seeds 950-954.
  4. Apply the selection rule.
- **Done when:** the selection is recorded in the README with both gains.

## T8. Freeze and main runs (Colab A and B, about 260 A100 hours of training plus about 28 of evaluation)
- **What:**
  0. Before the freeze (Mac, about half a day): implement `records='a2'` in `Records.addBoard`/`line` (with Phase 21's `a2_seq.followed` if Phase 21 is built, else the same rule in `contest.py`: a followed contest is a correct answer on that subtask after the contest, at most one per subtask), extend `test_records`, and add `recordFormat` to `RL19_PLAN` and P20-12 and the bridge configuration to `DECISIONS19`.
  1. Set arm 4's records from Gate A2 (P19-5). If Gate A2 passed, also set the record format of A2's P21-11 (accepted 2026-11-09): `Records.line` lists, per board, the contests made and the correct answers that followed, beside the payoffs, so A1 tests the format that passed; `test_records` covers it. Confirm the world matches Gate C1. After the user decides the GPU budget (P19-6), check power (design-low-level, Statistics).
  2. Freeze `RL19_PLAN` and push.
  3. Run the main cell on both accounts.
  4. **Stability check:** the main cell trains the first 2 runs and stops, printing their halts (the answer halt included). If neither halted, set `STABLE19 = True` and rerun the cell; if either halted, stop and ask.
- **Done when:** 29 final adapters (halted runs reported) and `eval_p19/runs.csv`.

## T9. Analysis, Gate A1 and docs
- **What:**
  - `demo_rl19` full, and Gate A1 as frozen, with the kill criterion (arm 4's specialization at 16 agents);
  - results in the README, `REPORT.md` and the Research Plan (Gate A1, and what it means for C3 and C4);
  - the preprint and summary page only where a claim changes.
