# Tasks: Phase 24, confirm the dedicated bridge (C1c)

Status (2026-11-12): T1-T2 done. Next: T3, the run, after the frozen plan is pushed.

## T1. Module and plan
- **Covers:** FR-1 to FR-5.
- **What:** `role_confirm`: the grid, the cost, `C1C_PLAN` (frozen, hash pinned), the gate, the summary and the report.
- **Done when:** `test_c1c_grid`, `test_c1c_plan` and `test_c1c_gate` pass.
- **Status (2026-11-12): done.**

## T2. Run notebook and checks
- **Covers:** FR-6, NFR-1, NFR-2.
- **What:** `demo_c1c` with `ready24` and the live cell; the sidebar entries; the C1 regression and the full suite.
- **Done when:** `test_ready24` passes, the regression shows 0 differences, and the suite passes.
- **Status (2026-11-12): done.**

## T3. Run (Mac, live, about $10.50-11.03)
- **Needs:** T2; the frozen plan pushed; the user's approval of the estimate (given 2026-11-12).
- **What:** `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_c1c.ipynb`.
- **Done when:** `results/multiagent/colony/c1c/report.md` reports Gate C1c, its robustness and the scored calls.

## T4. Handoffs
- **What:**
  - Record Gate C1c and Gate C1b in Phase 19's README (P19-8: A1's bridge design), and point Phase 20's T7 bridge check at the chosen design.
  - Finish Phase 23's T8.
  - Update memory.
- **Done when:** Phase 19's README states A1's bridged world as Gate C1c decided it.

```
T1 -> T2 -> T3 -> T4
```
