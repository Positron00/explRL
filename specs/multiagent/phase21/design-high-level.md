# Design (high level): Phase 21

Part of [README.md](README.md); requirements are in [requirements.md](requirements.md), and details in [design-low-level.md](design-low-level.md).

## Components

| Component | New or changed | Role |
|---|---|---|
| `nbs/clue_colony.ipynb` -> `explRL/clue_colony.py` | changed | `dropShare` (removes `SHARE_AGAIN` on the plain board) and `slotLines` (per-slot text after the role sentence) in `colonyRules`; both added to `COLONY_OPTS`; `checkOptions` refuses `dropShare` with `colony` or `confirm` |
| `nbs/clue_text.ipynb` -> `explRL/clue_text.py` | changed (option passing only) | `TextClueEnv` accepts `dropShare` and `slotLines`; `slotLines` makes the rules slot-dependent |
| `nbs/liar_trace.ipynb` -> `explRL/liar_trace.py` | changed (one guard) | `traceRun` admits cells whose only option is `dropShare` |
| `nbs/a2_seq.ipynb` -> `explRL/a2_seq.py` | new | `TargetedLiar`, `runBoard21`, `seating`, `guardIds`, `successIds`, `recordLines`, `runBoard21Cell` (as `colony3.runStage3Cell`), `runSequences21` |
| `nbs/a2_cols.ipynb` -> `explRL/a2_cols.py` | new | `followed(board, nLiar, log)` (contests and the correct answers that followed) and `a2Columns`; imported by `a2_seq` and `a2_report`, so neither imports the other |
| `nbs/a2_grid.ipynb` -> `explRL/a2_grid.py` | new | `ARMS21`, `TEAMS21`, `boardCell21`, `p2Grid`, `pilotGrid21`, `A2_PLAN`, `estimate21`, `costRule21`, `pilotCheck21` |
| `nbs/a2_report.ipynb` -> `explRL/a2_report.py` | new | `p2Columns` (with Phase 19's `contestColumns`), `a2TeamEstimates`, `a2Summaries` (with the core measures through `rl19_measures` and `rl19_spec.dolIndex`), `writeA2`, `figA2` |
| `nbs/a2_synth.ipynb` -> `explRL/a2_synth.py` | new | `syntheticRows21` and the power simulation, kept apart so `a2_report` stays under 200 lines (NFR-5) |
| `nbs/demo_a2.ipynb` | new | Stages `quick` (fake client), `pilot`, `main` and `rerun` behind `EXPLRL_A2_STAGE` |
| `nbs/sidebar.yml` | changed | The six new notebooks |
| `nbs/llm_budget.ipynb` -> `explRL/llm_budget.py` | changed (shared with Phase 20, NFR-7) | `Budget` dates new ledger entries by UTC month and counts only the current month; `spentAll()` for reports |

Unchanged: `colony_agents` (198 lines; the targeted liar subclasses `ClueLiar` in `a2_seq`), `colony3`, `contest`, `contest_eval`, every Phase 5-19 configuration hash and every earlier cell's prompts.

## Data flow

```text
Mac: implement -> offline tests (options, seating, targeted liars, records, sequences with the fake client) -> push
Mac: regression gate: cached reruns of Stage 3 and Phase 14 scaleB through the cache-only client (a miss raises, $0)
Mac: Budget counts by month (NFR-7; done once, by Phase 20 or 21, whichever is built first)
User: approves the pilot's estimated cost (P21-10); Mac: freeze A2_PLAN (coopHash; cap $250 per month) -> push
Mac: pilot (team 2190, own records, 6 boards; one drop-only board at 32) -> pilotCheck21, cost per call, costRule21
     -> verdict recorded in the README; forecasts frozen in A2_PLAN before the main run (P21-8)
User: approves the pilot's projection of the main grid (P21-10)
Mac: main, experience screen: waves b = 1..6
       b = 1, 2: one cell per team (all arms ask for it; the cache serves repeats) -> finished boards
       b = 3..6: per arm and team: recordLines(arm, boards 1..b-1) -> boardCell21 -> runBoard21
     -> results/multiagent/a2/main/{runs.csv, turns.jsonl, records.jsonl}
Mac: main, rule-text screen: p2Grid (originals 900-904 from the cache) -> traced -> results/multiagent/a2/p2/
Mac: rerun from the cache (byte-identical) -> a2Summaries -> Gate A2, H21-3 -> report.md, a2.png
Mac: Gate A2 -> Phase 19 README (P19-5 at RL19_PLAN's freeze), research plan; preprint only if a claim changes
```

## Key decisions

- **Records live in the prompt, written only by the harness.** A record is a line in the agent's system text, computed from finished boards and fixed for the whole board. Agents cannot write to it, which is the plan's defence against records becoming an attack surface.
- **The arms branch at board 3.** No record is shown on boards 1-2, so those boards are the same requests in every arm. They are played once per team, cost a third as much, and give every arm exactly the same early experience. Any difference between arms comes from the record alone.
- **Identity is separated from slot.** Liars and guards keep the fixed slots that the existing code expects (liars first, then guards). A seeded seating puts each team's persistent honest identities into slots on each board. The random quarter, the turn order and the records follow the identities, and no Phase 18 code changes.
- **Success and failure are set up through the liars, not the outcome.** Liars target the success guards' clues and avoid the failure guards' clues, as the plan states. Whether those contests are then followed by correct answers is measured. The manipulation check stops the gate from being read when it did not happen.
- **One drop-only option for two plans.** A2's P2 and the capability plan's E4 remove the same sentence on the same Phase 14 board, so they share one world key, one tracer and the same seed convention. A2's cells (8 and 32 agents) and E4's (16) then make one size curve.
- **The plan's core measures, from Phase 19's code.** A2 reports them where they apply, through `contest_eval.contestColumns`, `rl19_measures` and `rl19_spec`. Gorelick's index on P1's boards 3-6 is the one that matters most, because there division of labour is the point. Cost without liars is a recorded gap: no A2 board is clean.
- **Reuse before new calls.** P2's original-prompt seeds 900-904 replay free from Phase 14's cache. P1's boards 1-2 are shared across arms. Every new cell lands in the response cache for later replays and measures (B1).

## Gates

1. **Regression gate before the pilot:** the full suite, and cached reruns of Stage 3 and Phase 14's `scaleB` cells byte-identical through the cache-only client.
2. **Cost approval and the cap** (P21-10): the user approves the pilot's estimated cost. The cap is $250 per calendar month, counted by `Budget` per month (NFR-7). Then `A2_PLAN` is frozen and pushed before the pilot.
3. **Pilot gate (P21-12):** invalid replies under 5%, both success guards contest at least once on boards 1-2 and at least one correct answer follows a success guard's contest, and no lie lands on a failure guard's clue. Any failure stops and asks. The cost rule: report the main grid's projection (expected ceiling $50) to the user and wait for approval.
4. **Manipulation check (main run):** in at least 6 of 8 teams, both success guards have a contest on boards 1-2 followed by a correct answer. Otherwise Gate A2 is not read; stop and ask.
5. **Gate A2 (plan: week 3):** H21-1, a one-sided exact sign-flip over 8 seed pairs at α = 0.05. Its result sets `records` for Phase 19's arm 4 at the freeze of `RL19_PLAN`. The shared contrast is expected near 0, so the gate in effect tests the own-record contrast; H21-2 is reported beside it (P21-5).
6. **Rule-text family:** H21-3 at 8 and 32 agents, Holm across the two. No gate depends on it.
