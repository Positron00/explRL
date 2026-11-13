# Tasks: Phase 24, confirm the dedicated bridge (C1c)

Status (2026-11-12): T1-T4 done. Gate C1c **fails** (2026-11-12, $10.57, 16 boards, invalid 0.07%): `bridgeRole` − `bridge1` honestPooled −0.013 [−0.029, 0.002], p 0.92 (welfareHonest −0.018, same sign); contamination −0.040, 95th percentile −0.010 < 0.05 (holds). `bridgeRole` relayed 27 times as often (0.243 against 0.009 relays per bridge turn, 88% confirmed on arrival) but carried more lies across squads (cross-squad contamination 0.126 against 0.023). Both recorded call lines said 'passes' and were wrong on the gate, right on safety: C1b's +0.021 on 5 boards did not replicate. A1 keeps `bridge1` (P19-8).

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
- **Status (2026-11-12): done.** $10.57; Gate C1c fails (see the status line).

## T4. Handoffs
- **What:**
  - Record Gate C1c and Gate C1b in Phase 19's README (P19-8: A1's bridge design), and point Phase 20's T7 bridge check at the chosen design.
  - Finish Phase 23's T8.
  - Update memory.
- **Done when:** Phase 19's README states A1's bridged world as Gate C1c decided it.
- **Status (2026-11-12): done.** P19-8 settled on `bridge1`; Phase 20's T7 points back at `bridgeCheckCells` as written; Phase 23's T8 done; P19-10's evidence rationale flagged for the user.

```
T1 -> T2 -> T3 -> T4
```
