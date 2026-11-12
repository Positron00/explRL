# Design: Phase 24, confirm the dedicated bridge (C1c)

Status: v1 (2026-11-12; aligned with requirements v1).

## Components

| Module (notebook) | Holds |
|---|---|
| `explRL/role_confirm.py` (`nbs/role_confirm.ipynb`) | `ARMS24`, `SEEDS24`, `COST24`, `ALLOW24`, `c1cCell`, `c1cGrid`, `c1cRange`, `C1C_PLAN`, `gateC1c`, `C1C_MEASURES`, `c1cSummary`, `writeC1c` |
| `nbs/demo_c1c.ipynb` (not exported) | `ready24`, the live run cell |

## Data flow

1. `c1cGrid()` gives 16 cells through `colony_grid.colonyCell`, with `arms=ARMS24`.
2. `runWorkload` runs them with `relay_mech.runC1bCell` against the live client, which uses Phase 10's response cache and spend ledger under the monthly cap.
3. The cell writes to `results/multiagent/colony/c1c/`: `runs.csv`, `turns.jsonl`, `timing.jsonl` and `metrics.json`, with `*_live` copies.
4. `c1cSummary` builds the summary; `summary.json` and `report.md` follow.

## Gate

`gateC1c` mirrors `relay_report.gateC1b`, with the arm and base taken from `C1C_PLAN['gate']` (`bridgeRole`, `bridge1`). It reuses `bridge_report._d` (paired on seed), `_test` (`bootSeeds` interval and exact sign-flip p) and `relay_report.upperBound`.

## Tests

| Test | Checks |
|---|---|
| `test_c1c_grid` | 16 cells, the fresh seeds, both arms' options, `c1cRange() == (10.5, 11.03)` |
| `test_c1c_plan` | frozen on hash `c7a01f678d5a`; the gate, the calls and the approval |
| `test_c1c_gate` | synthetic rows: a safe gain passes (p 1/256), no gain fails, a less safe gain fails, a loss fails; the calls scored; missing cells refused; the report |
| `test_ready24` | an unfrozen or changed plan blocks the run |

## Build notes

- 2026-11-12: built and tested offline. A numpy dry run of one board per arm at seed 1810 plays, with relays on both arms.
