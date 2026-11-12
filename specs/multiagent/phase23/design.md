# Design: Phase 23, bridges that carry evidence (C1b)

Status: draft v2 (aligned with requirements draft v2, 2026-11-11). One design file covers both levels, as the phase is small.

## Components

| Module (new unless marked) | Contents | Lines (est.) |
|---|---|---|
| `explRL/relay_board.py` (`nbs/relay_board.ipynb`) | `RELAY_KEYS`, `checkRelay`, `RelayBoardEnv(BridgeBoardEnv)` with `relaySenders`, `opened`, `roleBridges` and `falseValues` hook data, and `RelayView` | ~110 |
| `explRL/clue_colony.py` (changed) | `tally` merges `board.relaySenders(k, j)` when the board defines it; `_value` takes an optional source tag | +10 |
| `explRL/colony_trace.py` (changed) | `falseValues` adds `board.countedFalse()` when the board defines it | +3 |
| `explRL/relay_agents.py` (`nbs/relay_agents.ipynb`) | `BRIDGE_ROLE_RULE`, `EVIDENCE_RULE`, `WINDOW_RULE`, `relayRules`, the evidence display line, the pair line's marks (FR-B6), `RoleBridge`, `relayMembers` | ~130 |
| `explRL/relay_grid.py` | `C1B_ARMS`, `C1B_CELLS`, `C1B_CLEAN`, `PILOT23`, `c1bGrid`, `c1bEstimate`, `reusedCells23` | ~80 |
| `explRL/relay_plan.py` | `C1B_PILOT_PLAN`, `C1B_PLAN`, `pilotCheck23` | ~80 |
| `explRL/relay_mech.py` | `relayColumns`, `runC1bCell` (wraps `runC1Cell`), `reusedRows23` | ~120 |
| `explRL/relay_report.py` | `gateC1b`, `c1bSummaries`, `writeC1b`, `figC1b`, `syntheticRows23` | ~170 |
| `nbs/demo_c1b.ipynb` | stages quick, pilot, main1, main2, main; `mainReady23` | — |

`clue_colony.colonyRules` already appends `bridgeRules` (a lazy import, line 126). It appends `relayRules` after it, which returns '' on any board without a relay key.

## The evidence tally (FR-A2, FR-A3, P23-2)

```
RelayBoardEnv.opened(k)    -> any relayLog entry on k                       # evidence: the clue is opened by its first relay
RelayBoardEnv.relaySenders(k, j) -> {r: frozenset(mirror senders)}          # {} unless k coupled to i's squad and j == 1
    mt = mirrorTally(k).get(k, {}).get(1, [])                                # [] when the mirror has no posts
    if mirrorWindow or (evidence and opened(k)): return {r: s for r, s, _ in mt}
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
- **Rule agent:** `RoleBridge._relay` takes the leader of each mirror on its pair. It relays it only if the leader has at least `Q` senders, no other value has as many, and its own board does not show it as leading. Otherwise it waits. It never opens.

## Data flow

Same as C1: `runC1Cell` produces rows with `stage4Columns`, `bridgeColumns` and `contestColumns`, plus `relayColumns`. The output folders are:

- `results/multiagent/colony/c1bpilot/` for the pilot;
- `c1bmain1/` and `c1bmain2/` for the two seed batches;
- `c1b/` for the full grid, where `reused.csv` holds the replayed C1 cells.

As in C1, the main stage replays every new cell through the cache-only client before writing; a missing reply raises `CacheMiss` before any paid call.

## Measures (FR-D1)

| Column | Definition |
|---|---|
| `contamination` | `traceBoard`'s, with `falseValues` extended by `countedFalse` |
| `coupledContamination` | the same, over honest answers on coupled subtasks only |
| `arrivalConfirmed` | relays whose value had at least `Q` mirror senders at the relay's turn, / relays |
| `filterGain` | false share of the distinct mirror values on the bridge's pair when it relayed, minus `falseRelayShare` |
| `reRelays` | relays on a coupled subtask whose earlier relayed value no longer leads the mirror |
| `relaysUsedCorrect` | relays whose value entered a correct answer |
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
| `test_check_relay` | relay_board | FR-A6 |
| `test_evidence_tally` | relay_board | AC-2, AC-3, FR-A2, FR-A5 |
| `test_window` | relay_board | AC-4, FR-A3 |
| `test_counted_false` | relay_board | AC-10, FR-D1 (contamination) |
| `test_relay_rules` | relay_agents | AC-5, FR-A4, FR-B1-B4, FR-B6 |
| `test_role_bridge_numpy` | relay_agents | AC-6, FR-B5 |
| `test_relay_prompt_tokens` | relay_agents | NFR-4 |
| `test_relay_columns` | relay_mech | FR-D1 (columns) |
| `test_reused23` (slow) | relay_mech | AC-7, FR-C2 |
| `test_c1b_grid`, `test_c1b_plans` | relay_grid, relay_plan | FR-C1, FR-C3, FR-C4 |
| `test_main_ready23` | demo_c1b | AC-8, FR-C5 |
| `test_gate_c1b`, `test_write_c1b` | relay_report | AC-9, FR-D2-D4 |
| `tools/c1_regression.py` (extended to all 38 C1 boards), `tools/b3_run.py check` | — | NFR-1 |
