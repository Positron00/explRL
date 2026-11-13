# Requirements: Phase 25, confirm the mirror window (C1d)

Status: v1 (2026-11-12; decisions P25-1 to P25-6 decided by the user).

## Functional

- **FR-1 Grid (P25-1, P25-2, P25-4).** `window_confirm.c1dGrid()` gives 32 cells:
  - arms `bridge1` and `mirrorWindow` from `ARMS23`, unchanged;
  - seeds 1820-1827, levels `<arm>|independent` (16 liars) and `<arm>|clean` (no liars);
  - N 64; study `colony25`.
  - Each cell is checked by `checkOptions`.
- **FR-2 Plan (P25-3, P25-5, P25-6).**
  - `C1D_PLAN` records the arms, the cells and seeds, H25-1 to H25-3, the gate and what it decides, the robustness rule, the hand-recorded calls, the cost rule with its ceiling, the user's approval, the cap of $250 per calendar month and the results folder.
  - It is frozen and its hash is pinned in `test_c1d_plan`.
- **FR-3 Cost (P25-6).** `c1dRange()` gives (low, high) dollars from `COST25` per board by fault and arm and `ALLOW25`: (20.35, 21.37). The high end is at most the ceiling.
- **FR-4 Gate and secondary test (P25-3).**
  - `gateC1d(rows, plan, nboot, metric)` is `gateC1c` with `C1D_PLAN`: part (i), a one-sided exact sign-flip of arm − base in `metric` over the 8 seeds with liars, passes at p < 0.05 with a positive estimate; part (ii) holds when the 95th percentile of the paired bootstrap means of the contamination difference is below 0.05. The verdict is `passes` or `fails`, with what it decides.
  - `cleanC1d(rows, plan, nboot)` is H25-3 on the clean boards: honestPooled (supported at p < 0.05 with a positive estimate) and welfareHonest.
- **FR-5 Summary and report.**
  - `c1dSummary(rows, plan)` raises ValueError unless all 32 planned cells are present.
  - It gives the gate, part (i)'s robustness on welfareHonest, H25-3, each arm's measures per fault (`C1D_MEASURES`) with bootstrap intervals, the calls scored against the results, the cost and the invalid share.
  - `writeC1d` writes `report.md`.
- **FR-6 Run.** `demo_c1d`'s `#| llm` cell:
  - runs only with `EXPLRL_LLM_LIVE=1` and `ready25() == []`: the plan frozen on the pinned hash, `window_confirm` committed, and HEAD on origin/main;
  - runs the 32 cells through `runWorkload` with `runC1bCell` under the monthly cap;
  - writes the artifacts and keeps `*_live` copies;
  - stops and asks at 5% invalid replies.

## Non-functional

- **NFR-1.** No change to boards, agents, prompts or any earlier phase's code or results. The C1 regression (`tools/c1_regression.py`) still shows 0 differences.
- **NFR-2.** The tests run offline, with no API key and no `results/` folder. CI and the docs build run every cell that has imports, and none of those cells reads saved results.

## Acceptance criteria

| AC | Requirement | Check |
|---|---|---|
| AC-1 | FR-1, FR-3 | `test_c1d_grid` |
| AC-2 | FR-2 | `test_c1d_plan` (the pinned hash) |
| AC-3 | FR-4, FR-5 | `test_c1d_gate` (synthetic rows: passes, no gain, less safe, worse, the clean test apart from the gate, missing cells, the report) |
| AC-4 | FR-6 | `test_ready25`; the run's `report.md` |
| AC-5 | NFR-1, NFR-2 | the C1 regression; the full suite; offline tests in a clean clone |
