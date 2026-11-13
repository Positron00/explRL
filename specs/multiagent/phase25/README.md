# Phase 25: confirm the mirror window (C1d)

Status: **v1, 2026-11-12. The user approved the design and the $20.35-21.37 estimate on 2026-11-12 (P25-1 to P25-6). Built and tested offline (T1-T2); `C1D_PLAN` frozen (hash `27ff916003d1`).** Next: push the frozen plan, then the run (T3).

## Why

Gates C1b and C1c (Phases 23 and 24, 2026-11-12) left A1 (Phase 19) on `bridge1`. That bridge relays on under 1% of its turns, so it wins back only 14% of what coupling costs squads (C1).

C1b also ran `mirrorWindow`: no bridge agents; the receiving squad's board shows every coupled clue's mirror tally from the start (Phase 23, FR-A3). On C1b's 5 exploratory boards (seeds 1800-1804, paired) it beat `bridge1` on all 5:

- with independent liars: honestPooled +0.017 (contamination +0.017, slightly worse);
- clean: honestPooled +0.066, level with uncoupled squads (+0.008), so the window removed the whole cost of coupling without liars.

The window was picked after seeing those boards, and `bridgeRole` had a similar 5-of-5 edge that failed on fresh seeds (C1c). So the user asked for a confirmation before A1 adopts it.

## Hypotheses and gate

- **H25-1, effective (Gate C1d part i).** `mirrorWindow` − `bridge1` on honestPooled, 64 agents, independent liars, seeds 1820-1827 paired. One-sided exact sign-flip test above 0, alpha 0.05 (the smallest p is 1/256). Robustness: the same contrast on welfareHonest; an estimate of the opposite sign marks part (i) not robust.
- **H25-2, safe (Gate C1d part ii, non-inferiority).** Contamination, the same 8 pairs. The 95th percentile of 2,000 paired bootstrap means must be below 0.05, C1b's margin.
- **H25-3, secondary (not in the gate).** `mirrorWindow` − `bridge1` on honestPooled, clean boards, the same seeds paired. One-sided exact sign-flip test above 0, alpha 0.05, uncorrected; welfareHonest beside it.
- **What the gate decides:**
  - Both parts hold: the gate **passes**. A1's bridged world replaces bridges with the window (amends P19-8). With no bridge agents, relay credit (P20-12) lapses and the 3B check (P20-11) measures the window's prompt length instead of relaying. The border contest credit (P23-8, kept by the user on 2026-11-12) stays; with the window, a true holder's mirror post reaches the receiving squad.
  - Otherwise it **fails**, and A1 keeps `bridge1` (P19-8 as settled by C1b and C1c).

## Decisions (the user, 2026-11-12)

| ID | Decision | Choice |
|---|---|---|
| P25-1 | What to confirm | `mirrorWindow` against `bridge1`. Both arms are exactly as in C1b's `ARMS23`. |
| P25-2 | Seeds | 1820-1827, fresh and paired across arms and faults. C1 and C1b used 1800-1807, C1c 1810-1817; the pilots 1890. |
| P25-3 | Gate | As above: Gate C1c's test and margin, with `mirrorWindow` in place of `bridgeRole`. |
| P25-4 | Scope | Liars and clean (the user chose this over liars only): 16 boards with liars for the gate, 16 clean for H25-3. No pilot: both arms ran at this size, with liars and clean, in C1 and C1b, with invalid replies under 0.2%. |
| P25-5 | Calls before the run | As P23-10. Pilot-only, from C1b's 5 boards: H25-1 passes (+0.017), H25-2 holds (+0.017), H25-3 supported (+0.066), gate passes. Every-design-helps: the same. |
| P25-6 | Cost | $20.35-21.37 for 32 boards, from the measured cost per board by arm and fault ($0.651 and $0.686 with liars, $0.609 and $0.598 clean, for `bridge1` and `mirrorWindow`) with a 5% allowance; ceiling $23; under the cap of $250 per calendar month (about $82 after the run). The run stops and asks at 5% invalid replies or at the cap. |

## Documents

| File | Holds |
|---|---|
| `requirements.md` | FR-1 to FR-6, NFR-1 and NFR-2, the acceptance criteria |
| `design.md` | The modules, the data flow and the tests |
| `tasks.md` | T1-T4 with their status |

Precedence: requirements, then design, then this README.

## Reuse

The arms come from `relay_grid.ARMS23`. The runner is `relay_mech.runC1bCell`. The gate is `role_confirm.gateC1c` read with `C1D_PLAN`; H25-3 uses `bridge_report._d` and `_test`. The scheduler and budget are `llm_sched.runWorkload` and `llm_budget.Budget`. No board, agent or prompt code changes.
