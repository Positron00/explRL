# Design: Phase 25, confirm the mirror window (C1d)

Status: v1 (2026-11-12; aligned with requirements v1).

## Components

| Module (notebook) | Holds |
|---|---|
| `explRL/window_confirm.py` (`nbs/window_confirm.ipynb`) | `ARMS25`, `SEEDS25`, `FAULTS25`, `COST25`, `ALLOW25`, `c1dCell`, `c1dGrid`, `c1dRange`, `C1D_PLAN`, `gateC1d`, `cleanC1d`, `C1D_MEASURES`, `c1dSummary`, `writeC1d` |
| `nbs/demo_c1d.ipynb` (not exported) | `ready25`, the live run cell |

## Data flow

1. `c1dGrid()` gives 32 cells through `colony_grid.colonyCell`, with `arms=ARMS25`.
2. `runWorkload` runs them with `relay_mech.runC1bCell` against the live client, which uses Phase 10's response cache and spend ledger under the monthly cap.
3. The cell writes to `results/multiagent/colony/c1d/`: `runs.csv`, `turns.jsonl`, `timing.jsonl` and `metrics.json`, with `*_live` copies.
4. `c1dSummary` builds the summary; `summary.json` and `report.md` follow.

## Gate

`gateC1d` calls `role_confirm.gateC1c` with `C1D_PLAN` (arm `mirrorWindow`, base `bridge1`); `bridge_report._d` defaults to the boards with independent liars, so the gate never reads a clean board. `cleanC1d` calls `_d` with `fault='clean'`. `C1D_MEASURES` drops C1c's bridge-only columns, which are empty on a window board, and adds collaboration (the `sharePerHeld` column, as in `bridge_mech`) and `inTokPerCall` (the window's prompt cost).

## Tests

| Test | Checks |
|---|---|
| `test_c1d_grid` | 32 cells, the fresh seeds, both faults (16 liars, none), both arms' options, `c1dRange() == (20.35, 21.37)` |
| `test_c1d_plan` | frozen on hash `27ff916003d1`; the gate, H25-3, the calls and the approval |
| `test_c1d_gate` | synthetic rows: a safe gain passes (p 1/256), no gain fails, a less safe gain fails, a loss fails; a clean result does not move the gate; the calls scored; missing cells refused; the report |
| `test_ready25` | an unfrozen or changed plan blocks the run |

## Build notes

- 2026-11-12: built and tested offline. A numpy dry run of one board per arm and fault at seed 1820 plays: `bridge1` relays (0.25-0.29 per bridge turn), and the clean window board scores 0.298 honestPooled against `bridge1`'s 0.118.
