# Plan: Phase 15, why do larger Claude teams lose more to liars?

Status: **implemented** (2026-10-17): T1 and T2 done (tracer, cache-only client, variants, measures, accounting, plan, demo; offline tests pass); next: freeze `TRACE_PLAN`, then the full traces ($0). Disclosure: before the freeze, debugging the tests showed the measures of a few small numpy runs (seeds 2000-2003: nearly every honest numpy submission was contaminated, and liars' first posts suppressed every true clue); one clean Haiku cell was replayed to check the cache (no liars, so no mechanism data); no Haiku liar cell was looked at, and the plan's measures, hypotheses and variants were not changed. Part of the multi-agent plan: [../README.md](../README.md). Builds on [Phase 14](../phase14/README.md) (the team-size sweep and its numpy forecast) and the companion preprint's simulation-first workflow (`paper2/`).

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the frozen analysis plan, acceptance criteria, out of scope |
| [design.md](design.md) | Modules, the tracer and the cache-only client, the measures, the loss accounting, the numpy variants, grids, report |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |
| [RUN.md](RUN.md) | Tests, the runs in order, artifacts |

## Goal

Phase 14's most surprising result: with a quarter of the agents scripted liars, the Haiku teams' honest agents lost **more** as the team grew (0.47 at N = 8, 0.58 at 16, 0.54 at 32; change N 8 -> 32 +0.076 [0.013, 0.137]), while the numpy rule agents, run first as a forecast, lost **less** (0.74 at 8, 0.60 at 32; -0.134 [-0.191, -0.074]). The forecast got this sign wrong. Phase 14 offered an untested explanation (rule agents dilute a liar's posts; Haiku agents may not).

Phase 15 finds the mechanism using only runs we already have. Every Part B board is rebuilt exactly from its seed; the Haiku runs are replayed from the response cache by a client that cannot call the API; both runners are traced turn by turn with the same measures. It then asks whether a numpy agent that copies the mechanism gets the trend right. Parts A-C cost $0 and turn the forecast's failure into a finding: where rule-agent screening breaks for LLM teams, and why.

What the code already shows (2026-10-17, while planning): rule agents share only clues they hold and skip a slot anyone has posted, a liar included; Haiku agents may share any clue they know, and their observation lists every post, conflicting ones included. Each clue has exactly one holder (`r = 1`), so a quarter of the clues are held by liars, who never share them truly.

## Part A: trace both runners with the same measures

Cells: Phase 14's Part B `baseline` cells, clean and with N // 4 liars, N = 8, 16, 32, seeds 900-904 (30 Haiku cells, replayed from cache); the numpy forecast's cells, N = 4, 8, 16, 32, 64, clean and with N // 4 liars, seeds 2000-2019 (200 cells, rerun in seconds). A tracer wraps each honest member and records, before it acts, the clues the harness counts as known to it (`known(i, ...)`, with each one's truth) and how many open subtasks show a false post. The LLM observations stay in the turn logs for reading; the measures do not parse them. Nothing the members do changes: rows and turn logs must equal the stored ones.

Measures per run (honest agents only; a clue is false when its residue differs from the board's true one):

| ID | Mechanism | Measure |
|---|---|---|
| M1 | Exposure | `falseVisible`: share of open subtasks showing a false post, averaged over honest turns; `contaminated`: share of honest submissions made while the agent's known clues for that subtask included a false one |
| M2 | Susceptibility | wrong answers per contaminated submission, and per uncontaminated one (the guessing baseline) |
| M3 | Suppression | share of slots (subtask, clue) a liar posted first whose true clue no honest agent posted afterwards |
| M4 | Relay | false relays (an honest agent's share of a false residue a liar posted earlier for that slot) per liar post; also the share of liar posts relayed at least once, and honest agents' other false shares (errors) |
| M5 | Withheld clues | share of subtasks with a clue held by a liar, and the solve rates of those and of the other subtasks |
| M6 | Recovery | rounds from an honest wrong answer to the subtask's solve; share of subtasks with a contaminated submission that are never solved |

## Part B: account for the honest loss

The two cells of a board (clean and with liars, same N and seed) draw the same subtasks in the same order. Per N and seed, the honest loss (welfareHonest clean minus with liars, each per honest agent-turn) is split exactly into eight terms:

| Term | What it is |
|---|---|
| (a) | penalties on the liar cell's contaminated submissions |
| (b) | the liar cell's other penalties minus the clean cell's penalties |
| (c) | value honest agents solved in the clean cell and nobody solved in the liar cell, on subtasks with a false post there |
| (d) | the same, on subtasks with a liar-held clue and no false post |
| (e) | value honest agents solved in the clean cell that a liar solved in the liar cell |
| (f) | the same as (c), on the remaining subtasks |
| (g) | value honest agents solved only in the liar cell (enters negatively) |
| (h) | per capita: subtasks honest agents solved in both cells, whose value is shared among N honest agents in one cell and N - N // 4 in the other (enters negatively) |

The question: which terms change from N = 8 to N = 32 differently for Haiku and for the rule agents.

## Part C: numpy variants (retrodiction)

Three variants of the Phase 11 rule agent, each copying one candidate mechanism, fixed in `TRACE_PLAN` before any full trace is run:

| Variant | Change | Mechanism |
|---|---|---|
| `relay` | also shares clues it knows from the board, for subtasks a teammate has open, after its own | M4 |
| `first` | the first sighting of a clue wins instead of the latest (own clues still win) | M2: a false clue is not overwritten by a later true one |
| `repost` | counts its own slot as already shared only when a post of it carries its own residue | M3: suppression off (a control, expected to lower the loss) |

Each runs the forecast's cells (N 4-64, 20 seeds, seconds). Reported: each variant's honest-loss and pooled-share changes from N 8 to 32, scored with the Phase 14 forecast rule against Haiku's signs. These are **retrodictions** (the Haiku answer is known) and are labelled so.

## Part D (optional, live, needs approval): a fresh forecast

If a variant gets the honest-loss sign right, freeze its forecast (and, for comparison, the unchanged rule agent's) for a condition not yet run: an eighth of the agents liars (`nLiar = N // 8`) at N = 8 and 32, the `baseline` arm, seeds 900-904. The clean rows come from Phase 14's `runs.csv` (not rerun). Commit the forecast, then run the Haiku liar cells and score it. 7 000 calls (1 400 at N = 8, 5 600 at N = 32), about $3.20 at the pilot's prices. Only with the user's go-ahead.

## Hypotheses (directions frozen in `TRACE_PLAN` before the full traces; exploratory)

| ID | Prediction |
|---|---|
| H15-1 | Haiku's contaminated share of honest submissions (M1) does not fall from N 8 to 32 (sign + or 0), while the rule agents' falls (sign -) |
| H15-2 | Haiku agents relay false clues (M4 above 0 at every N), and relays per liar post do not fall from N 8 to 32 |
| H15-3 | More than half of Haiku's change in honest loss from N 8 to 32 comes from contaminated subtasks (terms a + c) |
| H15-4 | At least one pre-listed numpy variant gets the sign of Haiku's honest-loss change right (+; retrodiction) |
| H15-5 | (Part D) The chosen variant's frozen forecast gets the sign of the new condition's honest-loss change right |

## Compute and cost

| Part | Work | Cost |
|---|---|---|
| A | 30 Haiku cells replayed from cache (19 600 cached calls: per seed 320 + 240 at N 8, 640 + 480 at 16, 1 280 + 960 at 32); 200 numpy cells | $0 (no key, no network); under an hour on the Mac |
| B, C | accounting on the traces; 3 variants x 200 numpy cells | $0; minutes |
| D (optional) | 7 000 new calls | about $3.20 |

API spent so far $79.14 of the $150 cap.

## Decisions

| ID | Question | Recommendation |
|---|---|---|
| P15-1 | Replay or parse the stored observations? | **Replay from cache**: the exact board state (true residues, holders, known clues) without parsing text; the stored observations are kept for reading, not parsed for measures |
| P15-2 | One tracer for both runners? | **Yes**: the same wrapper and measures for rule and LLM agents, so differences are not definitional |
| P15-3 | Which cells? | **`baseline` only** (the forecast scored the baseline); `record` and `request` cells are out of scope |
| P15-4 | When is the plan frozen? | **`TRACE_PLAN` before the first full trace** (numpy or Haiku): the Part B outcomes are known, the mechanism measures are not; the variants are part of the plan |
| P15-5 | Part D | **Optional**, run only if a variant passes H15-4 and the user approves (live API) |

## Risks

| Risk | Mitigation |
|---|---|
| A prompt differs, so the replay misses the cache | The replay's client has no API behind it: a miss raises at once, nothing is spent; rows and logs are compared with the stored ones |
| With 5 seeds the per-N mechanism changes are noisy | Bootstrap intervals; N 16 and 32 pooled against N 8 as a secondary view; the numpy side has 20 seeds |
| No single mechanism explains the trend | The accounting (Part B) still says where the loss goes; a mixed answer is reported as such |
| Retrodiction flatters the variants | Labelled retrodiction; only Part D tests a forecast |
| The per-capita term (h) dominates and hides the mechanisms | It is reported as its own term, and H15-3 is stated against the total change, so it cannot hide |
