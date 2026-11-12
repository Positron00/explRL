# Tasks: Phase 23, bridges that carry evidence (C1b)

Status (2026-11-11): T0-T5 done (build notes and the alignment check in design.md). T6: the user approved the estimate; `C1B_PILOT_PLAN` frozen. Next: push it, then the pilot.

Order:

1. T0.
2. T1-T4: offline, $0.
3. T5: the regression gate.
4. T6: the pilot, about $3, after the user approves the estimate.
5. T7: the main run, about $21-24, after the user approves the projection.
6. T8: the report and the handoffs.

A2's build (Phase 21) can run alongside.

## T0. Decisions
- **What:** the user decides P23-1 to P23-10 (README). Record each with its date. Amend P19-8 and P19-10 in Phase 19's README only where the user decided to.
- **Done when:** README's decisions table holds the decided values, and this file's status says so.
- **Status (2026-11-11): done.** All ten as proposed. P19-8 and P19-10 amended in Phase 19's README; Phase 20's T7 bridge check re-pointed (P23-6).

## T1. Board: evidence, window, dedicated-bridge slots, counted lies (about 1 day)
- **Covers:** FR-A1 to FR-A6, FR-D1 (the `falseValues` hook), AC-1 to AC-4, AC-10, NFR-1, NFR-2.
- **What:**
  - `relay_board`;
  - the `tally` hook in `clue_colony` and the `falseValues` hook in `colony_trace`;
  - the display tag.
- **Done when:** these tests pass, and so does the full suite:
  - `test_relay_off`, `test_check_relay`, `test_evidence_tally`, `test_window`, `test_counted_false`;
  - `tools/c1_regression.py`, extended to replay all 38 C1 boards, reports 0 differences.

- **Status (2026-11-11): done.**
## T2. Prompts and rule agents (about half a day)
- **Covers:** FR-B1 to FR-B6, AC-5, AC-6, NFR-4.
- **What:** `relay_agents`:
  - the three rule sentences and `relayRules`;
  - the pair line's marks;
  - `RoleBridge` and `relayMembers`.
- **Done when:** `test_relay_rules`, `test_role_bridge_numpy` and `test_relay_prompt_tokens` pass. The estimated ratio of a dedicated bridge's prompt to C1's `bridge1` prompt (64 agents) is under 1.15, so C1's measured mean (1,038) times it is under 1,560; a 3B bridge prompt in A1's world is under 3,072. The measured mean is checked in the pilot.

- **Status (2026-11-11): done.**
## T3. Measures and report (about 1 day)
- **Covers:** FR-D1 to FR-D4, AC-9.
- **What:**
  - `relay_mech`: `relayColumns`, `runC1bCell`, `reusedRows23`;
  - `relay_report`: `gateC1b`, `c1bSummaries`, `writeC1b`, `figC1b`, `syntheticRows23`.
- **Done when:** `test_relay_columns`, `test_gate_c1b` (including a planted safety failure alongside an effectiveness pass) and `test_write_c1b` pass.

- **Status (2026-11-11): done.**
## T4. Grid, plans and demo (about half a day)
- **Covers:** FR-C1 to FR-C5, AC-7, AC-8.
- **What:** `relay_grid`, `relay_plan`, `demo_c1b`, and the sidebar entries.
- **Done when:** `test_c1b_grid`, `test_c1b_plans`, `test_main_ready23` and the slow `test_reused23` pass, and `demo_c1b`'s quick stage runs end to end.

- **Status (2026-11-11): done.**
## T5. Regression gate ($0)
- **Covers:** NFR-1.
- **Done when:** `tools/c1_regression.py` (all 38 C1 boards and the 16 reused cells) and `tools/b3_run.py check` report 0 differences, and the full suite passes with slow tests. Then commit.

- **Status (2026-11-11): done.** Regression 0 differences, B3 check 0 differences, full suite with slow tests passes; rerun after the alignment fixes.

## T6. Pilot (Mac, live, about $3)
- **Needs:** T5, and your approval of the pilot estimate (P23-9).
- **What:**
  1. Freeze and push `C1B_PILOT_PLAN`.
  2. Run the four new arms at seed 1890.
  3. Run `pilotCheck23`.
- **Then:** report the checks, the cost per call by arm and the main run's projection to you, and wait. Stop and ask on any failed check.

## T7. Main run (Mac, live, about $21-24; then $0)
- **Needs:** T6, and your approval of the projection.
- **What:**
  1. Record the pilot-only and every-design-helps calls (P23-10) in `C1B_PLAN`, then freeze and push it.
  2. Run batches main1 and main2.
  3. Run the full grid from the cache, then the report.
- **Done when:** `results/multiagent/colony/c1bmain/report.md` reports, as frozen:
  - Gate C1b, both parts, with robustness;
  - H23-3 to H23-8;
  - `truthConfirmable` and `liarConfirmed`.

## T8. Handoffs and docs
- **What:**
  - Record Gate C1b in Phase 19 (P23-7: A1's bridge configuration per arm and squad size), and P23-8's contest credit if decided.
  - Point Phase 20's T7 bridge check at the chosen design (P23-6).
  - Update this README's status, the findings in `specs/multiagent/README.md`, and memory.
- **Done when:** Phase 19's README states A1's bridged world as Gate C1b decided it, and the C1 and C1b findings are written together.

## Dependency graph

```
T0 -> T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T7 -> T8
      (T3 needs T1's hooks; T4 needs T2's members)
```
