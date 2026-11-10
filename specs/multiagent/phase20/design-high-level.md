# Design (high level): Phase 20

Part of [README.md](README.md); requirements are in [requirements.md](requirements.md), and details in [design-low-level.md](design-low-level.md).

## Components

| Component | New or changed | Role |
|---|---|---|
| `nbs/bridge_board.ipynb` -> `explRL/bridge_board.py` | new | `BRIDGE_KEYS`, `checkBridge`, `dealBridges`, `BridgeBoardEnv` (with `mirrors(i, every=None)`, `mirrorTally`, `bridgeOf`; coupled deal, mirrors, `mirrorLog`, `relayLog`, relay credit through `_creditTo` and an overridden `_reward`), `BridgeView` (with `crossClues()` and `pair`), `relaySource` |
| `nbs/bridge_agents.ipynb` -> `explRL/bridge_agents.py` | new | `COUPLE_RULE`, `MIRROR_RULE`, `BRIDGE_RULE`, `bridgeRules`, `bridgeLines` (prompt lines), `parseBridge` (mirror shares and relays), `onMirror`, `RuleBridge` (a mixin), `MirrorLiar`, `bridgeMembers`, `bridgePromptTokens` |
| `nbs/bridge_mech.ipynb` -> `explRL/bridge_mech.py` | new | `isPhase20`, `tokensByRole`, `bridgeColumns`, `c1Columns`, `runC1`, `runC1Cell` (as `runStage4Cell`; rows = `stage4Columns` + `bridgeColumns` + `contestColumns`, numpy and LLM; B3 reads its numpy rows), `reusedRows20`, `boardDol`, `tokPerSolved`, `coreMeasures` (requirements FR-D5, through Phase 19's `contest_eval.contestColumns`, `rl19_measures` (`index`, `ratio`, `lags`) and `rl19_spec.dolIndex`) |
| `nbs/bridge_grid.ipynb` -> `explRL/bridge_grid.py` | new | `ARMS20`, `C1_CELLS`, `C1_CLEAN`, `PILOT20`, `REUSED20`, `c1Cell`, `c1Grid`, `c1PilotGrid`, `reusedCells20`, `c1Estimate`, `c1Range`, `squadEvalSuite`, `reusedPartB`, `bridgeCheckCells`, `projectHours20` |
| `nbs/bridge_plan.ipynb` -> `explRL/bridge_plan.py` | new | `C1_PILOT_PLAN`, `C1_PLAN` (unfrozen until T8 and T9), `costRule20`, `pilotCheck20` |
| `nbs/bridge_report.ipynb` -> `explRL/bridge_report.py` | new | `planned20`, `gateC1`, `c1Summaries` (with cost without liars, H20-8), `partBSummaries` |
| `nbs/bridge_write.ipynb` -> `explRL/bridge_write.py` | new | `writeC1`, `figC1`, `syntheticRows20`, `syntheticPartB` |
| `tools/c1_regression.py` | new | T6's regression gate: every earlier live board (413) replayed through the cache-only client with every saved column equal (a miss raises), then the 16 reused cells through `reusedRows20` |
| `nbs/colony_board.ipynb` -> `explRL/colony_board.py` | changed (hook) | `squadView` returns `board.viewFor(i)` when the board has it |
| `nbs/clue_colony.ipynb` -> `explRL/clue_colony.py` | changed | `checkOptions` for the bridge keys; `colonyRules` appends the bridge sentences |
| `nbs/clue_text.ipynb` -> `explRL/clue_text.py` | changed (hook) | `observe` adds `bridgeLines`; `parse` defers mirror shares and relays to `parseBridge` |
| `nbs/clue_runs.ipynb` -> `explRL/clue_runs.py` | changed | `clueSetup` builds `BridgeBoardEnv` when a bridge key is set; `bridgeMembers` beside `stage4Members` |
| `nbs/clue_roll.ipynb` -> `explRL/clue_roll.py` | changed (hook) | `boardFactory` builds `BridgeBoardEnv`; `coopRows` adds `bridgeColumns` when `isPhase20` |
| `nbs/colab_clue_rl.ipynb` | changed | Section "Phase 20": part b and the 3B bridge check, one cell, resumable and claim-aware |
| `nbs/demo_c1.ipynb` | new | quick (fake client), then the live stages by `EXPLRL_C1_STAGE`: `pilot`, `main1` and `main2` (the two seed batches), `main` (the cached full grid, after both batches with invalid replies under 5%); part b (analysis of the Colab zip) |
| `nbs/llm_budget.ipynb` -> `explRL/llm_budget.py` | changed (shared with Phase 21, NFR-7) | `Budget` dates new ledger entries by UTC month and counts only the current month; `spentAll()` for reports |

Unchanged: `ClueBoardEnv`'s and `ColonyBoardEnv`'s deals and streams, every earlier rule string, `colony_trace`, the reward schemes at their defaults, and every Phase 5-19 hash.

## Data flow

```text
Mac: implement -> offline tests (coupling, isolation, bridges, relays, liars, relay credit, rollouts, adaptive-liar path)
Mac: regression gate (tools/c1_regression.py: every earlier live board replays from the cache-only client, every saved column
     equal; the reused cells with C1's columns; Phase 19's tests) -> push   [done 2026-11-10]
Mac: Budget counts by month (NFR-7; done once, by Phase 20 or 21, whichever is built first)
User: approves the pilot's estimated cost (P20-8)
Mac: freeze C1_PILOT_PLAN (hypotheses, gate, pilot checks, cost rule, cap $250 per month; the forecast comes after the pilot)
     -> push
Mac, live: pilot (seed 1890: coupled, bridge1, bridgeGuard at 64 agents; about $2) -> pilotCheck20 -> projection
     -> report to the user; stop and ask on any failed check
B3 (specified and built elsewhere): fitted simulator, with RuleBridge for bridges -> C1 waits here until it exists
Mac: refit B3's simulator on the pilot; commit the forecast; freeze C1_PLAN with its SHA-256 -> push
User: approves the pilot's projection of the main run (P20-8)
Mac, live: main (38 new boards: 23 with liars, seeds 1800-1807 and 1800-1804, and 15 clean, seeds 1800-1804;
     stages main1 and main2, the two seed batches; about $25-31)
Mac, $0: the full grid (new and reused cells) replays from the cache -> c1Summaries -> Gate C1
Colab (one account; claims): part b (9 models x 20 boards in squads of 4) + the 3B bridge check -> explRL_c1b.zip
Mac: partBSummaries; README results, REPORT.md, research plan's Gate C1 line; hand Gate C1 to Phase 19 and C3
```

Part b and the bridge check do not depend on part a or on B3, and can run on Colab as soon as T6 (the regression gate) has passed. The pilot waits only for the user's approval of its cost and for `C1_PILOT_PLAN`. The main run waits for B3, the forecast in `C1_PLAN` and the user's approval of the projection. A1 (Phase 19) waits for Gate C1, so it waits for B3 too.

## Key decisions

- **Mirrors keep squads isolated and make coupling real.** The cross clue's holders post it on their own board, on a line their squad cannot answer. Only a bridge carries a value across. Mirrors exist in every coupled arm, so `coupled` against `bridge1` isolates the bridges.
- **A bridge belongs to the receiving squad.** It never holds the clues it relays, so a relay is always a relay and never a direct post of its own clue. It still works in its own squad, so bridges cost no squad an agent.
- **A guarding bridge replaces a guard, not an "other".** The team keeps 16 liars, 16 guards and 32 others in every bridge arm, so `bridgeGuard` against `bridge1` changes only who bridges.
- **A bridge reads only the relayable part of the second board.** It reads its pair's mirror lines, not the neighbour's whole board. This keeps a 3B bridge inside the 3,072-token window, which A1 needs.
- **Relays are ordinary posts on the receiving board.** The counting display is unchanged and has no "relayed" label. The harness logs each relay's source, so measures and RL credit can follow it.
- **Liars can reach the mirrors.** Otherwise no false value could be relayed and H20-5 would be untestable.
- **Reuse the two reference arms.** Stage 4's `squads` and the 64-agent run's `colonyGuards` are on the same seeds and the same board. Reusing them saves $18.47 and gives the gate's lead 8 boards, which the plan's 5-board allowance for uncoupled squads would not.
- **Clean boards for the arms A1 may train in** (P20-14). `squads`, `coupled` and `bridge1` get 5 clean boards each, so cost without liars, the plan's core measure, is measured where A1 needs it. `colonyGuards` gets none: it is the gate's reference, and A1 will not train on one board of 64. The clean boards are descriptive and outside Gate C1. Stage 4 has no clean `squads` cell to reuse.
- **One board's code serves Claude and RL.** `BridgeBoardEnv` is built by `clueSetup` for Claude cells and by `boardFactory` for `rollout`, so A1, C3 and C4 use the board C1 tested.
- **The inert-bridge rule.** The plan's gate cannot tell bridges that help from coupling that costs little. The rule makes that case a question for the user, not a silent pass.

## Gates

1. **Regression gate** before any paid call: NFR-1 (`tools/c1_regression.py`) and the full suite. Passed 2026-11-10.
2. **Cost approval and the cap** (P20-8, P20-9): the user approves the pilot's estimated cost before the pilot. The cap is $250 per calendar month, counted by `Budget` per month (NFR-7). `C1_PILOT_PLAN` is frozen and pushed before the pilot, and the cell asserts it.
3. **Pilot checks** (P20-8): any failure stops and asks. After the pilot, the user approves its projection of the main run.
4. **B3 and `C1_PLAN`:** B3's fitted simulator is refit on the pilot (P20-13). `C1_PLAN` is frozen (with the forecast's SHA-256) and pushed before the main run, and the cell asserts it.
5. **Batch rule:** between batches, the only stops are 5% invalid replies and the cap. A batch is not analysed on its own.
6. **Gate C1 (plan: week 3):** parts (i) and (ii) as frozen.
   - Pass: squads with bridges become A1's and C3's training world, unless the inert-bridge rule fires (then stop and ask).
   - Fail: A1 uses squads without cross-squad subtasks, and C3 does not run.
7. **Part b** runs only after the regression gate. Its results are descriptive and gate nothing.
8. **Cost without liars** (H20-8, the clean boards) is descriptive and gates nothing. It is reported beside Gate C1 and handed to A1 with it.
