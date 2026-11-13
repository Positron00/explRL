# Phase 24: confirm the dedicated bridge (C1c)

Status: **v1, 2026-11-12, done. The user approved the design and the $10.50-11.03 estimate on 2026-11-12 (P24-1 to P24-6, all as proposed). Built and tested offline (T1-T2); `C1C_PLAN` frozen (hash `c7a01f678d5a`).** Pushed; T3 ran. Gate C1c **fails** (2026-11-12, $10.57, 16 boards, invalid 0.07%): `bridgeRole` − `bridge1` honestPooled −0.013 [−0.029, 0.002], p 0.92 (welfareHonest −0.018, same sign); contamination −0.040, 95th percentile −0.010 < 0.05 (holds). `bridgeRole` relayed 27 times as often (0.243 against 0.009 relays per bridge turn, 88% confirmed on arrival) but carried more lies across squads (cross-squad contamination 0.126 against 0.023). Both recorded call lines said 'passes' and were wrong on the gate, right on safety: C1b's +0.021 on 5 boards did not replicate. A1 keeps `bridge1` (P19-8). T4 done: the handoffs to Phases 19, 20 and 23.

## Why

Phase 23 (C1b) ended with Gate C1b **ask** on 2026-11-12:

- `bridgeFix` (a dedicated bridge with evidence) was no more effective than C1's `bridge1`: honestPooled −0.003 [−0.022, 0.014], p 0.62.
- It was safer: contamination −0.048, with a 95th-percentile bound of −0.006 against the 0.05 margin.

C1b's exploratory 2 × 2 pointed elsewhere:

- The dedicated role helped (main effect +0.016, p 0.031). Evidence did not (−0.001).
- `bridgeRole`, a dedicated bridge without evidence, was the best coupled arm: honestPooled 0.193 against `bridge1`'s 0.172 on seeds 1800-1804. Its contamination, 0.246, was the lowest of any arm.

`bridgeRole` was picked after seeing those 5 boards. So before A1 (Phase 19) adopts it, the user asked for a confirmation on fresh seeds.

## Hypotheses and gate

- **H24-1, effective (Gate C1c part i).** `bridgeRole` − `bridge1` on honestPooled, 64 agents, independent liars, seeds 1810-1817 paired. One-sided exact sign-flip test above 0, alpha 0.05 (the smallest p is 1/256). Robustness: the same contrast on welfareHonest; an estimate of the opposite sign marks part (i) not robust.
- **H24-2, safe (Gate C1c part ii, non-inferiority).** Contamination, the same 8 pairs. The 95th percentile of 2,000 paired bootstrap means must be below 0.05, C1b's margin.
- **What the gate decides:**
  - Both parts hold: the gate **passes**, and A1's bridged arms use `bridgeRole` in place of `bridge1` (amends P19-8).
  - Otherwise it **fails**, and A1 keeps `bridge1` (P19-8 as amended by C1).
- **Confirmatory:** two parts, both must hold, no other tests.

## Decisions (the user, 2026-11-12, all as proposed)

| ID | Decision | Choice |
|---|---|---|
| P24-1 | What to confirm | `bridgeRole` against `bridge1`. Both arms are exactly as in C1b's `ARMS23`. |
| P24-2 | Seeds | 1810-1817, fresh and paired. C1 and C1b used 1800-1807; the pilot seed was 1890. |
| P24-3 | Gate | As above. Gate C1b's test and margin, with `bridgeRole` in place of `bridgeFix`. |
| P24-4 | Pilot | None. Both arms ran at this size in C1 and C1b with invalid replies under 0.2%. |
| P24-5 | Calls before the run | As P23-10. Pilot-only, from C1b's 5 boards: passes (+0.021) and holds (−0.113); `bridgeRole` beat `bridge1` on all 5. Every-design-helps: passes. |
| P24-6 | Cost | $10.50-11.03 for 16 boards, from the measured cost per board ($0.651 `bridge1`, $0.662 `bridgeRole`) with a 5% allowance; ceiling $12; under the cap of $250 per calendar month (about $61 after the run). The run stops and asks at 5% invalid replies or at the cap. |

## Documents

| File | Holds |
|---|---|
| `requirements.md` | FR-1 to FR-6, NFR-1 and NFR-2, the acceptance criteria |
| `design.md` | The modules, the data flow and the tests |
| `tasks.md` | T1-T4 with their status |

Precedence: requirements, then design, then this README.

## Reuse

The arms come from `relay_grid.ARMS23`. The runner is `relay_mech.runC1bCell`, which gives C1b's columns. The tests are `bridge_report._d` and `_test`, and `relay_report.upperBound`. The scheduler and budget are `llm_sched.runWorkload` and `llm_budget.Budget`. No board, agent or prompt code changes.
