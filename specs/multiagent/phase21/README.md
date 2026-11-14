# Plan: Phase 21, experience and rule-text screens (Claude Haiku)

Status: **built and tested 2026-11-14 (T0-T4); the pilot (T5) waits for the user's approval of its estimated cost, about $1.89.** Decisions made 2026-11-09 and 2026-11-10. This phase is experiment A2 of the Stage 1 research plan (project A, "train agents into the verification role with RL"). It is the cheap prompted screen behind the plan's main scientific bet, P1 (experience makes specialists), and it also tests one piece of the harness behind the "larger teams are more gullible" finding (the re-sharing sentence). The user decided P21-1 to P21-12 on 2026-11-09 and P21-13 to P21-14 on 2026-11-10 (table below). No live call has been made and no API money has been spent.

**Order relative to Phase 19.** The user decided on 2026-11-08 that A2 runs before A1 (Phase 19), alongside C1. A2 does not wait for B3 (P21-8, 2026-11-09), unlike C1's main run. Gate A2 sets one item of Phase 19's frozen plan: whether arm 4 (the emergence arm) keeps per-agent records (P19-5). The handoff is stated under "Handoff to Phase 19" below.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the frozen plans, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Components, data flow, key decisions, gates |
| [design-low-level.md](design-low-level.md) | Module contents, the sequence runner, records, targeted liars, measures, statistics, cost derivation, tests |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |

## Why

Two findings set up this screen:

- **Nobody volunteers.** When Phase 18's Stage 3 offered the guard role to every honest agent, no agent took it on any of 24 boards (0 volunteers; specialization at its shuffled baseline, -0.003). Each board was a fresh team with no memory of earlier boards. Ant workers specialized through experience alone: those led to succeed at foraging kept foraging, and those led to fail stopped (Ravary et al. 2007). The plan asks whether a private record of one's own experience does the same for Claude agents.
- **A posted lie sticks.** When a liar was first to post a clue, no honest agent posted its true value afterwards in 89-94% of cases at 8, 16 and 32 agents (Phase 15's tracer on Phase 14's one-holder runs, seeds 900-904). The preprint notes that the harness may have invited this: the plain board's rules say "A clue shared once is known to everyone who saw it, so sharing it again only helps teammates who did not see it." That sentence (`SHARE_AGAIN` in `clue_colony`) was never tested on its own.

## Questions and hypotheses

The plan's A2 card, as written:

- **Experience (P1).** 16 agents play 6 consecutive boards as one team, with clues re-dealt each board. On boards 1-2 a random quarter are assigned as guards: for half of them liars target their clues, so their contests succeed; for the rest none do. From board 3 the role is only offered. Arms: no record; a shared record of team totals with no names; each agent's own record, listing its past contests and the correct answers that followed. 8 teams per arm, paired on board seed.
- **Rule text (P2).** The plain board with the re-sharing sentence removed, at 8 and 32 agents, to measure how often that sentence led honest holders to leave a liar's first post uncorrected.

| ID | Hypothesis | Family |
|---|---|---|
| H21-1 | With own records, the success-minus-failure contrast in guarding on boards 3-6 is larger than with the shared record | Primary (Gate A2) |
| H21-2 | With own records, agents whose early contests succeeded keep guarding and the others stop: the own-record contrast is above 0 | Secondary |
| H21-3 | Without the re-sharing sentence, fewer liar-first posts go uncorrected, at 8 and at 32 agents | Rule-text family (2 tests, Holm) |
| H21-4 | Descriptive: role persistence, volunteers, specialization against its null, the division of labour (Gorelick's index on boards 3-6), and welfare by arm; the shared record and no record show no contrast | Descriptive |

Each prediction can fail. H21-1 fails if agents ignore their own record, or react to it no more than to team totals. H21-3 fails if the liar-first posts stay uncorrected as often without the sentence.

## Design summary

- **Model.** Claude Haiku 5.5 (`HAIKU`), low effort, 8,000-token reply limit, blackboard, 40 turns per agent, as in Phases 14-18.
- **Experience screen (P1).**
  - Board: Phase 18's counting board (`WORLD18`: two holders per clue, colony rules), 16 agents, 4 scripted liars (P21-1). On this board `colonyRules` already replaces the re-sharing sentence, so P1 and P2 do not interact.
  - Teams and identities: each team has 12 honest agents that keep their identity across its 6 boards; a seeded permutation seats them in slots each board (P21-3).
  - Boards 1-2: 4 random honest identities are assigned guards (`GUARD_RULE`); 2 of them, drawn at random, are the success guards. Scripted targeted liars post their lies only on clues a success guard holds and never on clues a failure guard holds (P21-2).
  - Boards 3-6: no assignment; every honest agent gets Stage 3's `VOLUNTEER_RULE`; scripted independent liars (`ClueLiar`), untargeted.
  - Records are shown from board 3 on, so boards 1-2 are identical in every arm. They are played once per team and shared by the three arms through the response cache (P21-4).
  - Arms on boards 3-6: no record; shared record (team totals of contests and of the correct answers that followed, no names); own record (the agent's own contests and the correct answers that followed, per earlier board). Every arm gets the same line saying which board of 6 this is (P21-4).
  - 8 teams per arm, team seeds 2100-2107, the same board seeds in every arm; pilot team 2190.
- **Rule-text screen (P2).**
  - Board: Phase 14's plain board exactly (`scaleB` baseline cells: one holder per clue, a quarter scripted liars, `CLUE_SETTINGS`), with world key `dropShare` removing `SHARE_AGAIN` (P21-6, P21-9).
  - 8 and 32 agents, seeds 900-907. The original-prompt arm replays seeds 900-904 from Phase 14's cache ($0) and runs 905-907 new; the drop-only arm runs all 8 seeds.
  - Liar boards only. Clean boards for the cost without liars are an option (P21-6), not taken.
- **Core measures.** A2 reports the plan's core measures where they apply, reusing Phase 19's functions (requirements FR-C5):
  - B1's gullibility, verification and collaboration, error correlation, welfare per agent-turn and per 1,000 tokens, and tokens per solved task, on every board;
  - the division of labour (Gorelick's index) on P1's boards 3-6 per arm, descriptively, where division of labour is the point;
  - role persistence on P1, as before.
  - **Not measured, a recorded gap: cost without liars.** P21-6 chose liar boards only, and P1's boards 3-6 always have liars, so no A2 board is clean. P21-6's option (about $6.83) would cover P2 only.
  - Contamination across squads does not apply: A2 has no squads.
- **Gate A2 (plan: week 3).** Guarding is each agent's share of turns spent posting or contesting clues it holds. The success-minus-failure contrast in guarding on boards 3-6 must be larger with own records than with the shared record: one-sided exact sign-flip over the 8 seed pairs, α = 0.05 (smallest p 1/256). A manipulation check must pass first (P21-12). The shared record cannot tell success guards from failure guards, so its contrast is expected near 0 and the gate in effect tests whether the own-record contrast is above 0; H21-2 is reported beside it (P21-5).
- **Cost.** About $34 of API calls, about $39 with a 15% margin. The plan estimates $35-50. The derivation is in [design-low-level.md](design-low-level.md#cost); the pilot replaces it.
- **Budget.** The cap is $250 of total spend per calendar month (P21-10). It reset for November 2026, and the spend comes from the user's $100-a-month API credit. The user sees the pilot's estimated cost before the pilot and its projection before the main run, and may raise the cap then. The ledger holds $233.18 from before November 2026, so `Budget` must count only the current month's spend first (NFR-7). C1 and A2 (about $61-72 together as specified, with C1's clean boards, Phase 20 P20-14; the plan says $65-90) run in the same month, before the capability plan's month 1.

## Decisions (the user, 2026-11-09)

All twelve were decided by the user on 2026-11-09. P21-5 was accepted with an added caveat and P21-10 was changed; the others were accepted as proposed. A change is marked **Changed**, and the text after it is the decided value.

| ID | Decision | Decided value |
|---|---|---|
| P21-1 | P1's board | **Accepted as proposed.** Phase 18's counting board (`WORLD18`, `colony`, two holders per clue), 16 agents, 40 turns, 4 scripted liars (a quarter), Haiku 5.5 at low effort. This is Stage 3's volunteer board, the source of "0 of 24", so the null being targeted is replicated exactly. The plan does not name the board. |
| P21-2 | Liars in P1 | **Accepted as proposed.** Boards 1-2: 4 `TargetedLiar`s. On a lying turn (every other turn, as `ClueLiar`), each lies on a clue of an open subtask that a success guard holds and no failure guard holds. If there is none, it lies on a clue that no failure guard holds. It never lies on a clue a failure guard holds. Boards 3-6: `ClueLiar` (independent, untargeted), so ex-guards get equal chances to contest. |
| P21-3 | Guards and identities | **Accepted as proposed.** The 12 honest identities are seated by a permutation seeded by team and board. On boards 1-2 the 4 guard identities (a random quarter of the team, drawn from the honest agents) sit in the guard slots, in random order, so existing guard code is unchanged. Success and failure pairs are drawn at random among them. Identities, permutations and the success/failure split are the same in every arm. |
| P21-4 | Records: timing, content, placement | **Accepted as proposed.** **Timing:** records appear from board 3, covering boards 1 to b-1, so boards 1-2 are shared across arms. **Own:** per earlier board, "you contested N false values; teammates then answered those subtasks correctly M times". **Shared:** the same two numbers as team totals, no names. **None:** no record line. Every arm gets the line "This is board b of 6 played by the same team". **Placement:** the lines are added to the agent's system text, which is fixed within a board. "Correct answers that followed" = correct answers by other honest agents to the contested subtask after the contest; ContestLog's watcher count is reported beside it. |
| P21-5 | Guarding measure and Gate A2's statistic | **Accepted as proposed, with a caveat.** Guarding = turns on which the agent posts a residue of a clue it holds, over its turns on that board (a contest is such a post). Per team: the mean over boards 3-6 of the success pair's mean guarding minus the failure pair's. Gate: own minus shared per team, one-sided exact sign-flip over the 8 teams, α = 0.05, a single test (no Holm family). **Caveat (2026-11-09):** the shared record cannot tell success guards from failure guards, so its contrast is expected near 0, and Gate A2 effectively tests whether the own-record contrast is above 0. The shared arm still controls for "any record makes guarding salient". H21-2 (the own-record contrast against 0) is reported beside the gate. |
| P21-6 | P2's cells | **Accepted as proposed.** Phase 14's `scaleB` baseline settings at N 8 and 32 with N // 4 liars, seeds 900-907. Originals: 900-904 from cache ($0), 905-907 new. Drop-only: all 8 seeds. Liar boards only; adding clean boards for cost without liars costs about $6.83 more. |
| P21-7 | P2's measure and test | **Accepted as proposed.** Primary: `suppressedHeld`, Phase 15's suppression restricted to liar-first slots whose clue has an honest holder. The plan asks about "honest holders", and with one holder per clue a liar-held clue cannot be corrected. Phase 15's `suppressed` is reported beside it, for comparison with the 89-94%. Tests: drop-only minus original per size, one-sided exact sign-flip over 8 seeds, Holm across 8 and 32. |
| P21-8 | Forecast (plan's B3) | **Accepted as proposed:** A2 does not wait for B3. The plan asks for a forecast of every planned effect, refit on each Claude experiment's pilot and frozen before the main run. Rule agents read no rules or records, so the fitted simulator cannot represent either screen. Proposal: freeze the every-design-helps forecast and a pilot-only forecast in `A2_PLAN`. Add the fitted simulator's forecast if B3's code exists when the plan is frozen; otherwise record its absence as a deviation. *Note (Phase 22, 2026-11-10):* B3 found none of A2's four effects representable, so the fitted line reads "not represented" whether or not B3's code exists, and that is not a deviation. The forecast is the file `a2_predictions.json` in this folder, its SHA-256 in `A2_PLAN`. |
| P21-9 | Overlap with the capability plan's E4 | **Accepted as proposed.** One implementation: a world key `dropShare` that removes `SHARE_AGAIN` in `colonyRules` for the plain board (refused with `colony` or `confirm`, which already replace it). E4's drop-only arm (Haiku, 16 agents, seeds 900-919) uses the same key and the same Phase 14 cells. A2 builds it first, because A2 runs first. |
| P21-10 | Budget and cap | **Changed.** No raise. The cap is $250 of total spend per calendar month (the user, 2026-11-09); it reset for November 2026, and the user has $100 of API credit per month. Cost rule, **report and wait:** before the pilot, report its estimated cost to the user and wait for approval; after the pilot, report its projection of the main grid and wait for approval. $50 (the top of the plan's range) stays as the expected ceiling, but nothing runs automatically under it. The user may raise the cap when shown an estimate. `Budget` must count only the current month's spend (NFR-7), and `A2_PLAN` records `cap=250.0` with `capNote='per calendar month (the user, 2026-11-09)'`. |
| P21-11 | Record format handed to Phase 19 | **Accepted as proposed.** Phase 19's 3B `Records.line` lists payoffs per board ("your answers earned ..., your contests earned ..."). A2's own record lists contests and the correct answers that followed. If Gate A2 passes, `RL19_PLAN` should test the format that passed. So, at the freeze, Phase 19's line also lists, per board, the contests made and the correct answers that followed, beside the payoffs (a Phase 19 change, made in Phase 19, not here). Recorded in Phase 19's README, requirements FR-A7, design-low-level and tasks T8 (2026-11-09). |
| P21-12 | Pilot and manipulation checks | **Accepted as proposed.** Pilot: team 2190, own-record arm, all 6 boards, and one drop-only board at 32 agents (seed 990), not analysed. Pass if invalid replies are under 5%; on boards 1-2, both success guards contest at least once and at least one correct answer follows; failure guards' clues get no lies (a code invariant); and the record lines render as specified. Main-run manipulation check: in at least 6 of the 8 teams, both success guards have at least one contest on boards 1-2 followed by a correct answer. If that fails, Gate A2 is not read; stop and ask. |
| P21-13 | Reply limit | **Decided by the user, 2026-11-10** (spec review). `maxTokens=8000`, frozen in `A2_PLAN`, whatever E4 does; raised only if A2's own pilot shows invalid replies at 5% or more. No rerun of P2's cached seeds. |
| P21-14 | P2 and a stop after wave 2 | **Decided by the user, 2026-11-10** (spec review). P2 runs in the same pool as waves 1-2, so a stop after wave 2 still leaves P2's result and a "Gate A2 not read" report. |

## Handoff to Phase 19

- **Gate A2 passes:** `RL19_PLAN` freezes arm 4 (`a19open`) with `records=True` (P19-5, `DECISIONS19` in `explRL/rl19_grid.py`), with the record format of P21-11 (accepted): per board, the contests made and the correct answers that followed, beside the payoffs.
- **Gate A2 fails:** arm 4 runs without records (`records=False`), as a test of contest credit alone. Phase 19's README records this as the plan's own outcome, not a deviation.
- **Gate A2 not read** (the manipulation check fails, or A2 has not finished when `RL19_PLAN` is frozen): the plan's fallback applies. Arm 4 runs without records, and Phase 19's README records it as a deviation.
- **Only Gate A2 crosses over.** P2's result does not change Phase 19. Phase 19 trains on the counting board, where the re-sharing sentence is already replaced by the colony rules.
- The plan's A1 prediction is conditioned on A2: "guard-like specialists appear only if A2 finds that experience makes roles persist". Phase 19's H19-4 carries that clause, and its report reads Gate A2's result.

## Relation to the other experiments

- **Capability plan, E4 (prompt framing).** Its drop-only prompt "removes just that sentence", the same `SHARE_AGAIN`. It runs at 16 agents (Haiku, 20 seeds), with first wrong answers per honest agent-turn as its primary measure. A2's P2 runs at 8 and 32 agents with suppression as its measure. Together they give drop-only at 8, 16 and 32 agents on the same Phase 14 board.
  - E4 has no 8- or 32-agent cells and does not test suppression, so it complements A2's P2 rather than replacing it, as Phase 19's README now says. P21-9 shares the code; the cells stay A2's.
  - Each report gives the other's measure as secondary: A2 reports E4's primary measure at 8 and 32 agents, and E4 can report suppression at 16.
  - **Reply limit.** A2 freezes `maxTokens=8000` (P21-13) whatever E4 does; it raises the limit only if A2's own pilot shows invalid replies at 5% or more. E4's contingency changes E4's arms only, so P2's seeds 900-904 still replay from the cache.
- **B1 (team-scaling eval).** A2 reports B1's measures where they apply: gullibility (first wrong answers made while misinformed) and suppression, contests per lie, time to contest, sharing per held clue, error correlation, honest pooled share, and the plan's other core measures (see "Core measures" above). Cost without liars is not measured.
- **B3 (cheap screen):** see P21-8. A2 does not wait for B3; C1's main run does (Phase 20, P20-13).
- **C1 (Phase 20):** runs alongside A2. The two share the API credit and the $250-per-month cap. Whichever phase is built first makes `Budget` count by month (NFR-7); the other reuses it.
- **Stage 3 (Phase 18).** It is A2's direct predecessor: the same volunteer sentence, board, liar share and Haiku settings. What A2 adds is the 6-board sequence, the assigned start and the records.
