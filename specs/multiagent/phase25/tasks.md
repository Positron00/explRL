# Tasks: Phase 25, confirm the mirror window (C1d)

Status (2026-11-12): T1-T4 done. Gate C1d fails; A1 keeps `bridge1`.

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
- **Status (2026-11-12): done.** **Gate C1d (2026-11-12): fails.** With liars (seeds 1820-1827): `mirrorWindow` − `bridge1` +0.008 [−0.008, 0.025], p 0.22 (welfareHonest +0.006, same sign); contamination +0.044 [0.005, 0.082], 95th percentile 0.076 against the 0.05 margin, so part (ii) fails too. Clean boards (H25-3, uncorrected): +0.063 [0.057, 0.068], 8 of 8, p 0.004. Cost $20.42, invalid replies 0.14%. Both call lines got the gate wrong and H25-3 right. The first summary pass stopped on a measure name (`collaboration` is the `sharePerHeld` column); fixed in `C1D_MEASURES` and the report replayed from the cache at $0.

## T4. Handoffs
- **What:**
  - Record Gate C1d in Phase 19's README (P19-8: A1's bridged world; P20-12 relay credit and the P20-11 check if the window is adopted).
  - Add C1d to `results/multiagent/REPORT.md` section 16 and the C1 card of the research plan.
  - Update memory.
- **Done when:** Phase 19's README states A1's bridged world as Gate C1d decided it.
- **Status (2026-11-12): done.** P19-8 records Gate C1d; the window is not adopted, so P20-11 and P20-12 stand as written; REPORT section 16, the preprint `paper_bridges/` and the research plan's C1 card include C1d.

```
T1 -> T2 -> T3 -> T4
```
