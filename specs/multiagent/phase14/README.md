# Plan: Phase 14, what makes trust information pay, and do the fixes scale?

Status: **code done; live runs in progress** (2026-10-17). `TRUST_PLAN` frozen at `b875c5f` (`coopHash(TRUST_PLAN)` = `6d2818ae84c2`) before Part A's run. T1, T2 (settings, grids, plans, report, demo) and T4 (numpy forecast, frozen) done. Part of the multi-agent plan: [../README.md](../README.md). Builds on [Phase 13](../phase13/README.md) (fixes for Claude teams on the clue board) and the companion preprint's simulation-first workflow (`paper2/`).

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the frozen analysis plans, acceptance criteria, out of scope |
| [design.md](design.md) | Modules, the two new affordance settings, grids, the numpy forecast, report |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |
| [RUN.md](RUN.md) | Tests, the runs in order, artifacts |

## Goal

Two steps, chosen for the most novelty per day and for the scale the role asks about ([../LITERATURE.md](../LITERATURE.md), sections 13-14):

- **Part A, publicity or verification?** Phase 13's clearest positive result: a public, harness-computed track record recovered a third of a liar's damage at no cost, while a private check that costs a turn caught lies and recovered nothing. Two things differ between them: who sees the information, and what it costs. Two new arms complete a 2 x 2 that separates them.
- **Part B, do the fixes scale?** Our Claude teams stopped at 8 agents; Anthropic's red team ran 10 to 80. Rerun the clearest positive fix (the track record against liars) and the clearest negative one (the request board) at 8, 16 and 32 agents, with the share of liars held fixed. Before the LLM runs, freeze a numpy forecast of how the baseline team's pooled share and liar damage change with team size, so the run also tests simulation-first screening at scale.

## Part A: the 2 x 2 of trust information

Clue board, blackboard, N = 4, one scripted liar (and the same cells without it), Claude Haiku 5.5, Phase 11-13 settings, seeds 900-909.

| | free (harness-computed) | costly (a turn per check) |
|---|---|---|
| **public** (everyone sees it) | `record` (Phase 13): each post shows its sender's track record over all solved subtasks | **`verifyPublic`** (new): a `check` whose result every agent sees in its next observation; every agent's known clues drop a clue found false |
| **private** (only the agent sees it) | **`recordPrivate`** (new): each post shows its sender's track record over the subtasks *this agent* solved | `verify` (Phase 13): a `check` whose result only the checker sees |

`record` and `verify` rows are reused from Phase 13 (same cells, cached replies); the baseline cells as well. New calls: 2 arms x 2 (liar, no liar) x 10 seeds x about 140 calls = about 5 600 calls, about $1.70.

Metric: loss recovered, as Phase 13 (A2): 1 - arm's mean honest loss / baseline's, paired on seed. Analysis: the publicity effect (mean of the public arms minus mean of the private arms, in loss recovered) and the cost effect (free minus costly), each with a bootstrap CI over seeds, and their difference (H14-2); each new arm against the baseline as in Phase 13. Mechanism: checks and checks found false; for the private record, how many checked shares stood behind the records agents saw.

## Part B: team-size sweep

Clue board, blackboard, N = 8, 16, 32 (the board grows with N: 2N + 2 open subtasks), Claude Haiku 5.5, 40 turns per agent, seeds 900-904.

| Cells | Arms | Purpose |
|---|---|---|
| clean | `baseline`, `request` | does the request board's harm persist, grow or vanish with N? |
| a quarter of the agents liars (2, 4, 8) | `baseline`, `record` | does the track record's benefit hold as liars and posts multiply? (its clean reference: the baseline's clean cell, same N and seed) |

N = 8 cells for `baseline` and `request` (clean) at seeds 900-904 replay Phase 13's cached replies; everything else is new. Estimate: about 33 000 new calls; at N = 32 prompts are longer (66 open subtasks, many posts), so the cost per call is measured in the pilot. Budget: $40; if the pilot projects more, N = 32 runs 3 seeds instead of 5, and if that still projects more, stop and ask (a pre-set rule, not a choice after seeing results).

**Numpy forecast first.** The Phase 11 rule agents (no affordances) play the same baseline cells, clean and with a quarter liars, at N = 4, 8, 16, 32 (and 64, for free), 20 seeds. The forecast, frozen and committed before any Part B LLM run: the sign of the change from N = 8 to N = 32 in (a) the clean team's pooled share and (b) the honest agents' loss from liars. Scored afterwards against the Haiku baseline cells with the Phase 13 forecast rule: each side's change is the mean at N = 32 minus the mean at N = 8, with a bootstrap interval resampling seeds within each N (boards differ by N, so seeds are not paired); a sign is + or - when the interval excludes 0, else 0.

## Hypotheses (directions frozen before the runs; exploratory)

| ID | Prediction |
|---|---|
| H14-1 | Publicity matters: the public arms recover more of the liar's damage than the private arms (publicity effect above 0) |
| H14-2 | Cost matters less than publicity: the publicity effect minus the cost effect is above 0 |
| H14-3 | The request board lowers pooled share at every team size (8, 16, 32) |
| H14-4 | The track record recovers part of the liars' damage at every team size |
| H14-5 | The numpy forecast gets both baseline trends' signs right |

## Compute and cost

| Part | Calls (Haiku) | Cost |
|---|---|---|
| A | about 5 600 new | about $1.70 |
| B pilot | N = 32: baseline clean and with liars, seed 900; about 2 300 calls | about $1-2 |
| B main | about 33 000 new | up to $40 (pilot-checked) |
| Numpy forecast | none | minutes on the Mac |

API spent so far $60.73 of the $150 cap.

## Decisions

| ID | Question | Recommendation |
|---|---|---|
| P14-1 | How private is the private record? | **Only subtasks the viewing agent solved itself**: the truth an agent learns first-hand. It is also less information than the public record; that is inherent to privacy and is reported, not hidden |
| P14-2 | Liars in Part B | **A quarter of the agents** (as Phase 9's liar share), so the liar pressure per honest agent is comparable across N |
| P14-3 | Team sizes | **8, 16, 32**; 64 only in numpy (an LLM board at N = 64 costs about 2 500 calls) |
| P14-4 | Seeds | **A: 10** (as Phase 13); **B: 5** (cost), cut to 3 at N = 32 if the pilot projects over $40 |
| P14-5 | Order | Part A first (half a day), then the numpy forecast, then Part B's pilot and main |

## Risks

| Risk | Mitigation |
|---|---|
| At N = 32 prompts exceed limits or slow the run | Pilot measures tokens per call and wall time; full memory stays (as Phases 11-13), the cost rule cuts seeds |
| Many liars at N = 32 overwhelm every arm | The quarter share matches Phase 9, where effects stayed measurable at N = 64 in numpy |
| The private record has too little data to matter | Report how many checked shares each private record showed on average |
| Publicity and information quantity are confounded in the record pair | The verify pair (same checks, public vs private) has no such confound; report both pairs |

## Numpy forecast (T4, 2026-10-17; frozen before any Part B LLM cell)

`tools/scale_forecast.py run`: Phase 11 rule agents, blackboard, N = 4-64, clean and with a quarter liars, seeds 2000-2019, 40 turns; 14 s on the Mac, byte-identical on rerun. Predictions in [scale_predictions.json](scale_predictions.json).

| N | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|
| clean pooled share | 0.58 | 0.51 | 0.44 | 0.36 | 0.26 |
| honest loss from liars | 0.74 | 0.74 | 0.70 | 0.60 | 0.53 |

**Predicted signs, N 8 -> 32:** clean pooled share **falls** (-0.156 [-0.170, -0.141]); honest agents' loss from a quarter liars **falls** (-0.134 [-0.191, -0.074]). To be scored against the Haiku baseline cells with `tools/scale_forecast.py score` after Part B's main run.

## Part B pilot and the SCALE_PLAN freeze (T5, 2026-10-17)

N = 32, `baseline`, clean and with 8 liars, seed 900: 2 240 calls, $1.14, about 67 minutes (a 32-agent board plays its 1 280 turns in order). Invalid replies 0.22% (band: under 5%); cost per call $0.00051 (about twice the N = 4 price); projected main run $17.25 (the cut: $12.67), within the $40 budget: the cost rule's verdict is **run** (all five seeds). `SCALE_PLAN` frozen at `04f83ed` (`coopHash(SCALE_PLAN)` = `b886baefb2ef`). One-seed glimpse, not a result: with 8 liars the honest agents' welfare was -0.12 against +0.45 clean.
