# Requirements: Phase 24, confirm the dedicated bridge (C1c)

Status: v1 (2026-11-12; decisions P24-1 to P24-6 decided by the user, all as proposed).

## Functional

- **FR-1 Grid (P24-1, P24-2).** `role_confirm.c1cGrid()` gives 16 cells:
  - arms `bridge1` and `bridgeRole` from `ARMS23`, unchanged;
  - seeds 1810-1817, level `<arm>|independent`;
  - N 64, 16 liars; study `colony24`.
  - Each cell is checked by `checkOptions`.
- **FR-2 Plan (P24-3, P24-5, P24-6).**
  - `C1C_PLAN` records the arms, the cells and seeds, H24-1 and H24-2, the gate and what it decides, the robustness rule, the hand-recorded calls, the cost rule with its ceiling, the user's approval, the cap of $250 per calendar month and the results folder.
  - It is frozen and its hash is pinned in `test_c1c_plan`.
- **FR-3 Cost (P24-6).** `c1cRange()` gives (low, high) dollars from `COST24` per board and `ALLOW24`: (10.50, 11.03). The high end is at most the ceiling.
- **FR-4 Gate (P24-3).** `gateC1c(rows, plan, nboot, metric)`:
  - Part (i) is a one-sided exact sign-flip test of arm − base in `metric` over the 8 seeds. It passes at p < 0.05 with a positive estimate.
  - Part (ii) holds when `upperBound` (the 95th percentile of the paired bootstrap means of the contamination difference) is below 0.05.
  - The verdict is `passes` (both hold) or `fails`, with what it decides.
- **FR-5 Summary and report.**
  - `c1cSummary(rows, plan)` raises ValueError unless all 16 planned cells are present.
  - It gives the gate, part (i)'s robustness on welfareHonest, each arm's measures (`C1C_MEASURES`) with bootstrap intervals, the calls scored against the verdicts, the cost and the invalid share.
  - `writeC1c` writes `report.md`.
- **FR-6 Run.** `demo_c1c`'s `#| llm` cell:
  - runs only with `EXPLRL_LLM_LIVE=1` and `ready24() == []`: the plan frozen on the pinned hash, `role_confirm` committed, and HEAD on origin/main;
  - runs the 16 cells through `runWorkload` with `runC1bCell` under the monthly cap;
  - writes the artifacts and keeps `*_live` copies;
  - stops and asks at 5% invalid replies.

## Non-functional

- **NFR-1.** No change to boards, agents, prompts or any earlier phase's code or results. The C1 regression (`tools/c1_regression.py`) still shows 0 differences.
- **NFR-2.** The tests run offline, with no API key and no `results/` folder. CI and the docs build run every cell that has imports, and none of those cells reads saved results.

## Acceptance criteria

| AC | Requirement | Check |
|---|---|---|
| AC-1 | FR-1, FR-3 | `test_c1c_grid` |
| AC-2 | FR-2 | `test_c1c_plan` (the pinned hash) |
| AC-3 | FR-4, FR-5 | `test_c1c_gate` (synthetic rows: passes, no gain, less safe, worse, missing cells, the report) |
| AC-4 | FR-6 | `test_ready24`; the run's `report.md` |
| AC-5 | NFR-1, NFR-2 | the C1 regression; the full suite; offline tests in a clean clone |
