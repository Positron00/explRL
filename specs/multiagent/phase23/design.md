# Design: Phase 23, bridges that carry evidence (C1b)

Status: v4 (2026-11-11: T1-T5 done, aligned with requirements v4 by the alignment check below; `C1B_PILOT_PLAN` frozen). One design file covers both levels, as the phase is small.

## Components

| Module (new unless marked) | Contents | Lines (est.) |
|---|---|---|
| `explRL/relay_board.py` (`nbs/relay_board.ipynb`) | `RELAY_KEYS`, `checkRelay`, `relayKw`, `boardClass`, `RelayBoardEnv(BridgeBoardEnv)` with `relayOpened`, `relayTally`, `relaySenders`, `countedFalse`, `roleBridges`, and the hook targets `withShown` and `pairVals` | ~100 |
| `explRL/clue_colony.py` (changed) | `tally` merges `board.relaySenders(k, j)` when the board defines it; `_value` takes an optional source tag | +10 |
| `explRL/colony_trace.py` (changed) | `falseValues(board, shown=False)`: with `shown`, `board.withShown(posted)` when the board defines it (one line) | +0 |
| `explRL/relay_agents.py` (`nbs/relay_agents.ipynb`) | `BRIDGE_ROLE_RULE`, `EVIDENCE_RULE`, `WINDOW_RULE`, `relayRules`, the evidence display line, the pair line's marks (FR-B6), `RoleBridge`, `relayMembers` | ~130 |
| `explRL/relay_grid.py` | `ARMS23`, `NEW23`, `C1B_CELLS`, `C1B_CLEAN`, `PILOT23`, `REUSED23`, `PER_BOARD23`, `ALLOW23`, `arm23`, `c1bCell`, `c1bGrid`, `c1bPilotGrid`, `reusedCells23`, `c1bRange` | ~65 |
| `explRL/relay_plan.py` | `C1B_PILOT_PLAN`, `C1B_PLAN`, `pilotCheck23` | ~80 |
| `explRL/relay_mech.py` | `relayColumns`, `c1bColumns` (`c1Columns` plus `relayColumns`), `runC1b`, `runC1bCell` (Claude through `runLLMCell`, numpy through `replay`), `reusedRows23` | ~90 |
| `explRL/relay_report.py` | `gateC1b`, `c1bSummaries`, `writeC1b`, `figC1b`, `syntheticRows23` | ~170 |
| `nbs/demo_c1b.ipynb` | stages quick, pilot, main1, main2, main; `mainReady23` | — |

`clue_colony.colonyRules` already appends `bridgeRules` (a lazy import, line 126). It appends `relayRules` after it, which returns '' on any board without a relay key.

## The evidence tally (FR-A2, FR-A3, P23-2)

```
RelayBoardEnv.relayOpened(k) -> any relayLog entry on k                      # evidence: the clue is opened by its first relay
RelayBoardEnv.relaySenders(k, j) -> {r: frozenset(mirror senders)}          # {} unless k coupled to i's squad and j == 1
    mt = mirrorTally(k).get(k, {}).get(1, [])                                # [] when the mirror has no posts
    if mirrorWindow or (evidence and relayOpened(k)): return {r: s for r, s, _ in mt}
    return {}
```

`clue_colony.tally(channel, board)` works per open k.

1. It builds `vals` from the channel, as today.
2. For each `(r, s)` in `board.relaySenders(k, 1)`, it sets the senders of `vals[(1, r)]` to `s` plus any channel senders of r other than the board's bridges.
   - A bridge's own post therefore never counts (AC-2).
   - A liar in the receiving squad who posts r still counts as one of that squad's senders.
3. The newest time is the latest of the mirror and channel posts.
4. Sorting is unchanged: most senders, then newest.

Agent ids from squad s2 never collide with squad s's, so the counts are of real, distinct people. The receiving squad cannot see who they are, only how many and from which squad (FR-A5). Only the coupled clue (j = 1) on squad s's own coupled subtasks is affected. Every uncoupled subtask and every earlier board is unchanged (AC-1, NFR-1).

**Why the whole tally, live (P23-2).** Mirror posts are never withdrawn, so a count can only rise. What lets the receiving squad recover from a relayed lie is the true holders' later posts. With the whole tally shown, those posts appear downstream and contest the lie without a second relay (AC-3).

**Contamination (FR-D1).** `RelayBoardEnv.countedFalse()` returns `{(k, 1, r): (t0, ...)}` for every false mirror value that `relaySenders` exposed to a receiving board, where t0 is when it was first exposed. `colony_trace.falseValues` adds these, so `contaminatedBy` counts an honest answer that used one. On C1's boards the method does not exist, so nothing changes.

## The dedicated bridge (FR-A4, FR-B1, FR-B5, FR-B6, P23-3, P23-4)

- **Slot:** `dealBridges` is unchanged (the first honest non-guard slot per squad). `bridgeRole` marks those slots in `roleBridges`.
- **Board:** nothing is enforced, as for guards. `ColonyBoardEnv` uses `guardSet` only for the deal; "Do not open subtasks" is in the prompt.
- **Prompt:** `BRIDGE_RULE`, then `BRIDGE_ROLE_RULE`. The pair line marks confirmed, unconfirmed and contested values (FR-B6). Without these marks the rule could not be followed from the text.
- **Rule agent:** `RoleBridge._roleRelay` takes the leader of each mirror on its pair. It relays it only if the leader has at least `Q` senders, no other value has as many, its own board does not show it as leading, and it has not already relayed that value on that subtask. Otherwise it shares a held clue as a guard does (mirrors first), else it waits. It never opens.

## Data flow

As C1: `runC1bCell` produces rows with `c1Columns` (`stage4Columns`, `bridgeColumns`, `contestColumns`) plus `relayColumns`. The output folders are:

- `results/multiagent/colony/c1bpilot/` for the pilot;
- `c1bmain1/` and `c1bmain2/` for the two seed batches;
- `c1bquick/` for the quick stage (fake client, synthetic rows);
- `c1bmain/` for the full grid, where `reused.csv` holds the replayed C1 cells (`c1b/` is C1's part b).

As in C1, the main stage replays every new cell through the cache-only client before writing; a missing reply raises `CacheMiss` before any paid call.

## Measures (FR-D1)

| Column | Definition |
|---|---|
| `contamination` | `traceBoard`'s, with `falseValues` extended by `countedFalse` |
| `coupledContamination` | the same, over honest answers on coupled subtasks only |
| `arrivalConfirmed` | relays whose value had at least `Q` mirror senders at the relay's turn, / relays |
| `filterGain` | per relay, the false share of the distinct values on that subtask's mirror visible to the bridge when it relayed, averaged over relays, minus the false share of the relayed values |
| `reRelays` | relays of the mirror's leader on a coupled subtask whose earlier relayed value no longer leads the mirror |
| `roleBreaks` | a dedicated bridge's opens (its rule says never) |
| `truthConfirmable` | mirrors that ever had a confirmed true value, / mirrors |
| `liarConfirmed` | mirrors with a false value posted by two liars, / mirrors |

The report shows each arm's honest pooled share and contamination side by side (FR-D4), so effectiveness and safety are read together.

## Statistics (FR-D2, FR-D3)

- **Gate part (i):** paired per seed (1800-1807), d = `bridgeFix` − `bridge1` in honest pooled share. One-sided exact sign-flip (256 flips), α 0.05.
- **Gate part (ii):** the same pairs, in contamination. 2,000 paired bootstrap means; the 95th percentile must be below 0.05.
  - **Spread in C1:** per-board sd of contamination is 0.036-0.089 by arm, and the sd of paired differences between bridge arms is 0.038-0.074.
  - **What the bar does:** with 8 pairs the one-sided bound sits about 0.025 above the mean difference. A design as safe as `bridge1` passes about 95% of the time, and one that is truly 0.05 worse about 5%.
- **Secondary tests:** seeds 1800-1804, uncorrected one-sided sign-flip (smallest p 1/32), bootstrap intervals.
  - H23-3's ratio is computed as in C1's `c1Summaries`.
  - H23-5's main effects are the mean of the two cell differences at each level of the other factor.
- **Power and ceiling:**
  - **Spread:** `bridge1`'s per-board sd is about 0.02 in honest pooled share, so 8 pairs detect a gain of about 0.03 in part (i).
  - **Ceiling:** a confirmed true value is available on only about 52% of mirrors (README), and coupling cost 0.092 on these seeds. So even a perfect bridge can probably win back only about half of that, roughly 0.05, which is also H23-3's bar. The secondary tests report `truthConfirmable` beside H23-3.

## Cost derivation

From `results/multiagent/colony/c1/runs.csv`:

- **Per-board costs:** boards with liars $0.646 (`bridge2`), $0.651 (`bridge1`), $0.665 (`coupled`), $0.684 (`bridgeGuard`); clean $0.609 (`bridge1`), $0.620 (`coupled`).
- **Calls:** a dedicated bridge makes as many calls as a solver (one per turn).
- **Allowance:** the role and evidence sentences and the marks add about 80-120 input tokens per prompt, against about 860 today. On a squad board output is about 69% of the cost, so the allowance is 1.15x.

See README's table: $23.7-27.3.

## Failure handling

- **Pilot:** its checks (P23-9) stop and ask before the main run.
- **Cache:** a missing reply in the main stage raises before any paid call.
- **Invalid replies:** at 5% in batch 1, batch 2 does not start (as in C1).
- **Budget:** `Budget` stops the run at the monthly cap.

## Tests (by notebook)

| Test | Notebook | Covers |
|---|---|---|
| `test_relay_off` | relay_board | AC-1, FR-A1 |
| `test_relay_off_replay` | relay_mech | AC-1b, FR-A1 |
| `test_check_relay` | relay_board | FR-A6 |
| `test_evidence_tally` | relay_board | AC-2, AC-3, FR-A2, FR-A5 |
| `test_window` | relay_board | AC-4, FR-A3 |
| `test_counted_false` | relay_board | AC-10, FR-D1 (contamination) |
| `test_relay_rules` | relay_agents | AC-5 (the rule), FR-A4, FR-B1-B4, FR-B6; `test_relay_columns` has AC-5's `roleBreaks` |
| `test_role_bridge_numpy` | relay_agents | AC-6, FR-B5 |
| `test_relay_prompt_tokens` | relay_agents | NFR-4 |
| `test_relay_columns` | relay_mech | FR-D1 (columns) |
| `test_reused23` (slow) | relay_mech | AC-7, FR-C2 |
| `test_c1b_grid`, `test_c1b_plans` | relay_grid, relay_plan | FR-C1, FR-C3, FR-C4 |
| `test_main_ready23` | demo_c1b | AC-8, FR-C5 |
| `test_gate_c1b`, `test_write_c1b` | relay_report | AC-9, FR-D2-D4 |
| `tools/c1_regression.py` (extended to all 38 C1 boards), `tools/b3_run.py check` | — | NFR-1 |

## Build notes (2026-11-11): deviations and review fixes

- **Names.** `opened(k)` is `relayOpened(k)` (ColonyBoardEnv already has `opened`). `tally` merges `relayTally(k)`, `[(r, mirror senders, newest)]`, so the mirror's times carry over; `relaySenders(k, j)` stays as `{r: senders}`. No `RelayView`: `BridgeView` delegates to the board. `relay_write.py` holds `writeC1b`, `figC1b` and `syntheticRows23` (NFR-2, as C1's `bridge_write`). `relaysUsedCorrect` is not added: C1's `relaysUsed` counts exactly that. `boardClass` and `relayKw` pick the board in `clueSetup` and `boardFactory`.
- **Bridge posts.** On a shown clue, a bridge's channel post of a value on the mirror is dropped (its mirror senders count instead); a bridge post of any other value still counts.
- **Dedicated bridge (review A, B).** The deal gives a bridge clues like any slot, so the role's rule now ends by sharing held clues before waiting (FR-B1's added clause). `RoleBridge` relays a given value on a subtask at most once, so a value two receiving-squad liars outvote cannot hold it on one subtask.
- **False values (review C).** `falseValues(board, shown=False)`; only contamination (with `traceBoard`'s reach) and `coupledContamination` read the shown lies, so `lieTiming` and the posted-lie trace stay comparable with C1's arms.
- **Display (review).** A relayed value also posted in the receiving squad reads `(1 agent in squad 3 and 1 in your squad, relayed, confirmed)`, so the count never contradicts the label.
- **Seeds (review G).** H23-3's `truthConfirmable` and H23-8's per-arm values are on seeds 1800-1804, as the plan says. H23-4 is over the 8 `bridgeFix` boards (the plan's reading; FR-D3 said "bridge boards").
- **Pilot.** Mirror posts are checked per board as well as in total (a window board must show something). The token bar compares the measured mean, so `<= 1560` passes (P23-9 stops above it). Offline, `test_relay_prompt_tokens` scales the estimate from C1's `bridge1` (estimate 1,453, measured mean 1,002): the dedicated bridge's estimate is about 1.11x, projecting about 1,150. The main-run cost ceiling is $28.
- **Cost.** `c1bRange` gives $23.65-27.20 (README's $27.3 sums rounded rows).
- **Alignment check (2026-11-11, after T5; an independent review, each finding checked against the code).**
  - NFR-2: the hooks had pushed `colony_trace` (204), `bridge_agents` (203) and `clue_roll` (200) to the limit or over it. The logic moved to `RelayBoardEnv.withShown` and `pairVals` and `relay_agents.markedVals`; `relayMembers` is now called by `colony_board.stage4Members` after `bridgeMembers`. Rows are unchanged (regression rerun).
  - `pilotCheck23`: one relay confirmed out of 49 (or 98, 103, ...) relays gave 0.999... and would have stopped the pilot falsely; the product is rounded. Tested.
  - `gateC1b` passes its `nboot` to the bound (the run uses 2,000 either way).
  - Specs: robustness is part (i) only; FR-A2's merge and bridge-post rule; the grid's names; filter gain's definition; H23-4 on the 8 `bridgeFix` boards (also in the report's heading); H23-5's interaction and H23-7's extra contrasts written into FR-D3; NFR-4's "at most"; the $28 ceiling in README and FR-C4.
  - Tests: `test_relay_off_replay` (AC-1b: a whole numpy run through `RelayBoardEnv` equals `BridgeBoardEnv`'s); the dedicated bridge's sharing of held clues is now asserted unconditionally (a true clue it holds).
  - Batches: `main1` is seeds 1800-1803 (24 boards) and `main2` 1804-1807 (9 boards), because the 5-seed arms end at 1804.
  - Pilot plan: frozen with the user's approval of the estimate and the all-bridge-arms relay check recorded; its hash is pinned in `test_c1b_plans`.
