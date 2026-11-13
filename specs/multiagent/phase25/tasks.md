# Tasks: Phase 25, confirm the mirror window (C1d)

Status (2026-11-12): T1-T2 done. Next: T3, the run, after the frozen plan is pushed.

## T1. Module and plan
- **Covers:** FR-1 to FR-5.
- **What:** `window_confirm`: the grid, the cost, `C1D_PLAN` (frozen, hash pinned), the gate, H25-3, the summary and the report.
- **Done when:** `test_c1d_grid`, `test_c1d_plan` and `test_c1d_gate` pass.
- **Status (2026-11-12): done.**

## T2. Run notebook and checks
- **Covers:** FR-6, NFR-1, NFR-2.
- **What:** `demo_c1d` with `ready25` and the live cell; the sidebar entries; the C1 regression and the full suite.
- **Done when:** `test_ready25` passes, the regression shows 0 differences, and the suite passes.
- **Status (2026-11-12): done.**

## T3. Run (Mac, live, about $20.35-21.37)
- **Needs:** T2; the frozen plan pushed; the user's approval of the estimate (given 2026-11-12).
- **What:** `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_c1d.ipynb`.
- **Done when:** `results/multiagent/colony/c1d/report.md` reports Gate C1d, its robustness, H25-3 and the scored calls.

## T4. Handoffs
- **What:**
  - Record Gate C1d in Phase 19's README (P19-8: A1's bridged world; P20-12 relay credit and the P20-11 check if the window is adopted).
  - Add C1d to `results/multiagent/REPORT.md` section 16 and the C1 card of the research plan.
  - Update memory.
- **Done when:** Phase 19's README states A1's bridged world as Gate C1d decided it.

```
T1 -> T2 -> T3 -> T4
```
