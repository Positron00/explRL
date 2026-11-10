# Tasks: Phase 21

Status (2026-11-10): specified, decisions made 2026-11-09 and 2026-11-10, not built. The user decided P21-1 to P21-12 (README) on 2026-11-09 and P21-13 to P21-14 on 2026-11-10. **Before T5:** `Budget` counts by month (T0), and the user approves the pilot's estimated cost (P21-10). The cap is $250 per calendar month. A2 does not wait for B3 (P21-8). Gate A2 must be read before Phase 19's `RL19_PLAN` is frozen (Phase 19, T8 step 1).

Rules are as in Phases 16-19:

- notebook first, then `nbdev-export` and `nbdev-clean`, with one notebook per test call;
- new notebooks go into `nbs/sidebar.yml`;
- modules stay under 200 lines;
- offline tests run without the network, `anthropic` or a key;
- Phase 5-19 outputs and hashes stay unchanged;
- each frozen plan is pushed before its cell runs;
- live calls only with `EXPLRL_LLM_LIVE=1`, from a script file with a `__main__` guard (macOS spawn), with the response cache and the ledger cap.

## T0. Monthly ledger (shared with Phase 20; about 2 hours)
- **Who:** whichever of Phases 20 and 21 is built first does it; the other reuses it (Phase 20, T0).
- **Files:** `nbs/llm_budget.ipynb` -> `explRL/llm_budget.py` (`Budget`).
- **What:** each new ledger entry carries `month` (UTC `'YYYY-MM'`). `spent()` counts only the current month's entries; undated legacy entries count as earlier months. `spentAll()` gives the all-time total, for reports.
- **Done when:** NFR-7's tests pass (a month boundary and legacy entries), the full suite passes, and on the real ledger (491,301 undated entries, $233.18) `spent()` is $0 in November 2026 and `spentAll()` is $233.18.

## T1. Board options shared with E4 (about half a day)
- **Files:** `nbs/clue_colony.ipynb` (`dropShare`, `slotLines`, `checkOptions`), `nbs/clue_text.ipynb` (option passing), `nbs/liar_trace.ipynb` (the `traceRun` guard).
- **Done when:** `test_dropshare`, `test_slotlines`, `test_trace_drop` and `test_hashes21` pass, and the full suite passes. A rendered drop-only prompt at 8 agents differs from Phase 14's by exactly the sentence.

## T2. Targeted liars, seating, records and the board runner (about 1 day)
- **Files:** `nbs/a2_cols.ipynb` (new: `followed`, `a2Columns`), `nbs/a2_seq.ipynb` (new: `TargetedLiar`, `seating`, `guardIds`, `successIds`, `recordLines`, `runBoard21`, `runBoard21Cell`).
- **Done when:** `test_targeted`, `test_seating` and `test_records21` (AC-4 to AC-6) pass. A recorded 16-agent board with the fake client shows no lie on a failure guard's clue, and the record lines are as frozen.

## T3. Sequences, grids, plan and demo stages (about 1 day)
- **Files:** `nbs/a2_seq.ipynb` (`runSequences21`), `nbs/a2_grid.ipynb` (new: `ARMS21`, `boardCell21`, `p2Grid`, `pilotGrid21`, `A2_PLAN` unfrozen, `estimate21`, `costRule21`, `pilotCheck21`), `nbs/demo_a2.ipynb` (stages `quick`, `pilot`, `main`, `rerun`).
- **Done when:**
  - `test_sequences21` (AC-7) passes;
  - `estimate21` reproduces design-low-level's call counts (480 per 16-agent board, 240 and 960 per P2 board), with boards 1-2 once per team and P2 seeds 900-904 at zero;
  - `demo_a2` quick runs end to end with the fake client;
  - the pilot and main stages refuse to run unfrozen (AC-8).

## T4. Report (about half a day)
- **Files:** `nbs/a2_report.ipynb` (new: `p2Columns`, `a2TeamEstimates`, `a2Summaries` with `partial='stopped'`, `writeA2`, `figA2`), `nbs/a2_synth.ipynb` (new: `syntheticRows21`).
- **Also:** the core measures (FR-C5) through Phase 19's `contest_eval.contestColumns`, `rl19_measures` (`index`, `ratio`, `lags`) and `rl19_spec` (`dolIndex`, the persistence rule), with the rows' `agents`, `pos` and `seqId`.
- **Done when:** `test_a2_report` (AC-9), `test_a2_measures` (AC-10) and the full suite pass, and the report on synthetic rows lists every `A2_PLAN` item, Gorelick's index on boards 3-6 per arm, and the note that cost without liars is not measured.

## T5. Regression gate, freeze and pilot (Mac, about $1.90)
- **What:**
  1. Run the regression gate: the full suite, then the cached reruns of Stage 3 and Phase 14's `scaleB` cells through the cache-only client (a miss raises; $0).
  2. Check that T0 is done. Report the pilot's estimated cost (about $1.90) to the user and wait for approval (P21-10). The decisions P21-1 to P21-12 are recorded in the README (2026-11-09).
  3. Freeze `A2_PLAN` with the record texts and the cap (`cap=250.0`, `capNote='per calendar month (the user, 2026-11-09)'`), commit and push. Record the commit and `coopHash(A2_PLAN)` in the README.
  4. Run `EXPLRL_A2_STAGE=pilot`: team 2190 with own records over 6 boards, and one drop-only board at 32 agents.
- **Then:**
  - `pilotCheck21` gives the checks' verdict and `costRule21` the projection of the main grid; record both in the README with the measured cost per call and the wall time per wave.
  - Report the projection to the user and wait for approval before T6 (P21-10).
  - Estimate power from the pilot (design-low-level, Statistics) and report it.
  - Freeze the forecasts of P21-8, and add them to `A2_PLAN` in a second frozen version before the main run.
  - **If either check fails, stop and ask.** One fix that changes no compared setting is allowed, such as the reply parser or a record line's wording.

## T6. Main runs (Mac, about $32)
- **Needs:** the pilot's checks passed, and the user approved the projection (P21-10).
- **What:**
  1. Run `EXPLRL_A2_STAGE=main` (only after the user's approval of the projection is recorded in `A2_PLAN['approved']['main']`, P21-10): the experience screen in 6 waves (boards 1-2 once per team, then 3 arms × 8 teams per wave), and the rule-text screen (`p2Grid`; originals 900-904 from the cache), which runs in the same pool as waves 1-2 (P21-14).
  2. Copy `metrics.json` and `timing.jsonl` to `*_live` before any cached rerun.
  3. Run `EXPLRL_A2_STAGE=rerun`: byte-identical from the cache, $0.
- **Stability check after wave 2:** invalid replies under 5%, and the manipulation check on boards 1-2 (at least 6 of 8 teams). If either fails, stop before wave 3 and ask; nothing is spent on boards 3-6. P2 has already run with waves 1-2 (P21-14), so its result and "Gate A2 not read" are reported (`a2Summaries(partial='stopped')`).
- **Done when:** `results/multiagent/a2/main/` and `results/multiagent/a2/p2/` hold every planned board, and the rerun matches.

## T7. Analysis, Gate A2 and the handoff
- **What:**
  - Run `demo_a2` on the saved runs: Gate A2 as frozen (H21-1, with the manipulation check), with H21-2 (the own-record contrast against 0) reported beside it (P21-5), H21-3 with Holm, and H21-4.
  - Put the results in this README, `REPORT.md` and the research plan (Gate A2's row and A2's card).
  - Hand off to Phase 19's README, P19-5: arm 4 keeps records on a pass, drops them on a fail, and records a deviation if the gate was not read. On a pass, also P21-11 (accepted): Phase 19's record line adds, per board, the contests made and the correct answers that followed.
  - Tell the capability plan's E4 owner which drop-only cells and cache keys exist.
  - Change the preprint and summary page only where a claim changes. P2 bears on the preprint's gullibility section (`sec:gullible`), "the rules said that a clue shared once is known to everyone who saw it ...; we did not test either on its own".
- **Done when:** Gate A2's verdict and its consequence for arm 4 are recorded in both READMEs before `RL19_PLAN` is frozen.
