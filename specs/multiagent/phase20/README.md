# Plan: Phase 20, squads with coupled work and bridges (C1)

Status: **main run done 2026-11-11 (T10): Gate C1 passes** (part i: `bridge1` − `colonyGuards` +0.105 [0.086, 0.125], p 0.004; part ii margin +0.020 [0.001, 0.037], p 0.047; robust on raw honest welfare); the inert-bridge flag does not fire (`bridge1` − `coupled` +0.013). H20-3 not supported (bridges win back 14% of the coupling cost), H20-4 and H20-5 supported. Cost $23.95 for the 38 boards (82,560 calls; pilot $2.06). B3 scored on C1: `c1_score.json`. T11 done 2026-11-12: Gate C1 and H20-8 recorded in Phase 19 (A1 trains in squads joined by `bridge1`, as Phases 23 and 24 settled), the results in `results/multiagent/REPORT.md` section 16 and the research plan. Open: T7 (part b and the bridge check, Colab); the C4 part b world waits for C4's spec. Earlier: **built and tested offline 2026-11-10** (T0-T6 done; the regression gate passed; nothing live has run: no API call has been made and no GPU has run). Next: T7 (part b and the 3B bridge check on Colab; the user runs it) and T8 (the pilot, which needs the user's approval of its estimate of about $2). T9-T10 wait for B3 (Phase 22). This phase is experiment C1 of the Stage 1 research plan (project C, "test which team structures help and can arise from RL"; hypothesis P5, local worlds). The user decided P20-1 to P20-14 on 2026-11-09 and P20-15 to P20-17 on 2026-11-10 (table below). P20-14 (clean boards), the core measures, part b's weights (P20-10) and the Phase 19 handoffs were added later the same day.

**Order relative to the plan.** The plan runs C1 in weeks 1-3, as one of the cheap screens whose gates set up the RL experiments. The user decided on 2026-11-08 that A1 (Phase 19) waits for C1: **if Gate C1 passes, A1 trains in squads joined by bridges**; if it fails, A1 uses the plan's fallback, squads without cross-squad subtasks.

**C1's main run waits for B3** (the user, 2026-11-09, P20-13). The forecast must come from B3's fitted simulator, refit on C1's pilot. So B3 must be specified and built before C1's main run, and A1, which waits for Gate C1, waits for B3 too. Part b (the 3B evaluation) and the 3B bridge check (P20-11) do not depend on B3 and may run earlier. So does C1's pilot.

So C1's code must do two jobs:

- run the Claude Haiku screen (part a) and the 3B evaluation (part b);
- give A1, C3 and C4 bridges and cross-squad subtasks that work in RL rollouts (`clue_roll.rollout`, `boardFactory`), with the squad deal of `colony_board.dealSquads` and the views of `squadView`.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the frozen plans, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Components, data flow, key decisions, gates |
| [design-low-level.md](design-low-level.md) | Module contents, the coupled deal, mirrors and relays, measures, statistics, cost derivation, tests |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |

## Why

Squads were Phase 18's strongest design, but they were tested in the easiest form:

- **Squads hold up as teams grow.** Squads of 8 beat guards on one board by +0.171 honest pooled share at 64 agents (Holm p 0.012, all 8 seeds). Their advantage over the plain board went 0.26, 0.34, 0.34 at 16, 32 and 64 agents. Prompts stayed at 780 input tokens per call, against 6,463 on one 64-agent guard board (Stage 4, Stage 4b).
- **No work crossed squads.** Each squad's subtasks and clues stayed inside it, so the squads never had to exchange information. Stage 4 named bridges as "a follow-up if squads win" (D3). The plan therefore treats squads' advantage as "likely an upper bound".
- **Real teams are coupled.** Splitting a team is easy when the work splits. C1 asks what is left of the squads' lead when a quarter of each squad's work needs a clue held in another squad, and whether a few bridge agents that read both boards and relay values win it back.

Honeybee guards stand at the nest entrance (Breed et al. 2004), so the plan also tests a bridge that guards. Part b asks a 3B question that A1's squad size depends on: Phase 17's adapters gained at 4 agents (+0.078 welfare) and not at 32 (+0.006). Does that gain come back when a 32-agent team works in squads of 4?

## Questions and hypotheses

| ID | Hypothesis | Family |
|---|---|---|
| H20-1 | With one bridge per pair, coupled squads beat one board of 64 with guards in honest pooled share | Primary (Gate C1, part i) |
| H20-2 | Coupled squads with one bridge per pair keep at least half of the uncoupled squads' lead over one board of 64 | Gate C1, part ii (a margin, P20-7) |
| H20-3 | One bridge per pair wins back most (more than half) of what coupling costs | Secondary |
| H20-4 | A second bridge per pair adds little: less than a quarter of what coupling costs (P20-7) | Secondary |
| H20-5 | Guarding bridges relay fewer false values than bridges that do not guard | Secondary |
| H20-6 | Part b (3B, descriptive): the 4-agent training gain reappears inside squads of 4 at 32 agents, but not on one board of 32 | Descriptive |
| H20-7 | Cross-squad contamination: relayed false values lead to wrong answers in the receiving squad, more often without guarding bridges | Exploratory |
| H20-8 | Cost without liars (P20-14): on clean boards, coupling and bridges cost little output. `coupled` − `squads` and `bridge1` − `squads` in honest pooled share, 5 clean boards (a negative contrast is a cost; the plan's cost without liars, reference minus design, is the negative: `squads` − `coupled` and `squads` − `bridge1`; the report states both) | Descriptive, not part of Gate C1 |

Each can fail. H20-1 fails if coupling costs the squads their lead. H20-3 fails if bridges relay too little or too late. H20-5 fails if guard rules do not change what a bridge relays. H20-6 fails if squads of 4 show no more gain than one board.

The plan's gate does not compare bridges with coupled squads that have none. If coupling costs less than half the lead, Gate C1 can pass with bridges that do nothing. P20-7 adds a stop-and-ask rule for that case.

## Design summary

- **Part a (Claude Haiku 5.5).**
  - **Board:** Phase 18's counting board (`WORLD18`: two clues per subtask, two holders per clue, x < 30, colony display), 40 turns, blackboard, full memory, low effort, as in Stage 4.
  - **Team:** 64 agents in eight squads of 8. A quarter of the agents (16) are independent scripted liars and a quarter (16) are guards, so each squad has 2 liars, 2 guards and 4 others, as in Stage 4's `squads` arm.
  - **Coupling:** a quarter of each squad's subtasks need one clue held in the next squad around a ring, so 8 pairs of squads are coupled (P20-1).
  - **Bridges** are drawn from the 64 (P20-2). A bridge reads its own board and the next squad's posts for the coupled subtasks, and relays values (P20-3, P20-4).
  - **Arms**, with the number of boards in each:

| Arm | Key | Boards with liars | Clean boards | Source |
|---|---|---|---|---|
| Squads without cross-squad subtasks | `squads` | 8 | 5 | with liars: reused, Stage 4's `squads` cell, from the cache (P20-6); clean: new (P20-14) |
| One board of 64 with guards | `colonyGuards` | 8 | none | reused: the 64-agent run's cell, from the cache (P20-6) |
| Coupled squads, no bridges | `coupled` | 5 | 5 | new |
| One bridge per pair | `bridge1` | 8 | 5 | new (the gate's arm) |
| Two bridges per pair | `bridge2` | 5 | none | new |
| One bridge per pair that also guards | `bridgeGuard` | 5 | none | new |

  The plan asks for "5 boards per arm, 8 for the gate's two arms". The gate also needs the uncoupled squads' lead on the same boards, and reusing Stage 4's cell gives it all 8.

  - **Clean boards (P20-14).** No liars: all 64 agents are honest Claude agents, and the 16 guards stay. They give the plan's core measure, cost without liars, and show whether coupling and bridges cost output when nobody lies. A1 trains in this world, and its varied threat includes boards without liars. Stage 4 never played `squads` without liars: its only clean cells are at 16 agents (`guardDeal`, `failFlag`, `colonyGuards`, `plain`). So all 15 clean boards are new. They are descriptive (H20-8) and not part of Gate C1.

  Seeds: 1800-1807 (Stage 1's seeds, as in Stage 4) for the 8-board arms, 1800-1804 for the 5-board arms and the clean boards; the pilot uses seed 1890.
- **Part b (3B, evaluation only).** The warm start and Phase 17's 8 `r17mix` adapters, on Phase 17's plain board (m = 2, one holder per clue, R = 30) at 32 agents, seeds 900-909, clean and with 8 scripted liars, 40 turns, notes memory. Two arms:
  - one board of 32, reused from Phase 17's evaluation rows;
  - eight squads of 4, new (P20-10).
- **3B bridge check (an addition, P20-11).** The warm start in A1's world, 16 agents in squads with one bridge per pair, to see whether a 3B model that never saw a relay makes any, and whether a bridge's prompt fits the 3,072-token window.
- **Gate C1 (plan: week 3).** Both parts must hold:
  - **(i)** `bridge1` beats `colonyGuards` at 64 agents in honest pooled share: a one-sided exact sign-flip over 8 boards, α = 0.05.
  - **(ii)** `bridge1` keeps at least half of `squads`' lead over `colonyGuards`. On these seeds that lead is 0.171, so the bar is about 0.086.

  Each part is repeated on raw honest welfare as a robustness check. If the gate passes, squads with bridges become the training world for A1 and C3.
- **Forecast.** As the plan's B3 requires, B3's fitted simulator is refit on C1's pilot. Its forecast of every planned effect is frozen before the main run, with its SHA-256 in `C1_PLAN` (P20-13). The main run waits until B3's simulator exists. The simulator models bridges through `RuleBridge`, the rule-agent bridge this phase builds.

## Cost

**API (part a): about $27-33, against the plan's $30-40.** The two reference arms with liars are reused (the plan's "less if the two reference arms reuse explRL's cached 64-agent boards"), and the 15 clean boards (P20-14) add about $12-14. The derivation uses measured per-board costs from `results/multiagent/colony/*/runs.csv`:

| Item | Boards | Per board | Cost |
|---|---|---|---|
| New arms with liars (`coupled` 5, `bridge1` 8, `bridge2` 5, `bridgeGuard` 5) | 23 | $0.588 measured on Stage 4's 64-agent `squads` boards (8 boards; 1,920 calls; $0.000306 per call; 780 input tokens per call), up to $0.74 with a 1.25x allowance for mirror lines and bridge prompts | $13.5-17.0 |
| Clean boards (`squads`, `coupled`, `bridge1`, 5 each; P20-14) | 15 | $0.784: the $0.588 above × the calls ratio 2,560 / 1,920 (all 64 agents are model calls, against 48 honest agents on a liar board), up to $0.98 with the 1.25x allowance on `coupled` and `bridge1` | $11.8-13.7 |
| Pilot (seed 1890: `coupled`, `bridge1`, `bridgeGuard`, with liars) | 3 | as the first row | $1.8-2.2 |
| Reference arms reused from the cache (`squads`, `colonyGuards` at 64, with liars) | 16 | replayed, $0 | $0 |
| **Total** | 41 new | | **$27.0-32.8** |

- **The allowance.** On a squad board, output tokens are about 69% of the cost (seed 1800: $0.411 of $0.599), so even a 50% rise in input tokens adds only about $0.09 per board. The 1.25x allowance covers that and longer bridge replies. It applies to every coupled arm, clean or not, because `coupled` has mirror lines too.
- **The clean boards' calls ratio is measured.** Stage 4's 16-agent clean boards made 640 calls, against 480 on its liar boards: the same 4/3. Scaling by calls is conservative. On those 16-agent cells a clean board cost 0.62-0.73 times a liar board per call (about 900-960 input tokens per call, against 1,435-1,594), so 0.83-0.97 times a liar board in total.
- **The pilot has no clean board** (P20-14). Clean boards use the same arms, prompts and code as the pilot's liar boards, minus the liars. The projection prices them at the pilot's cost per call by arm × 2,560 calls, which, by the point above, overstates them.
- **Without reuse** the two reference arms add 8 × $0.588 + 8 × $1.721 = $18.47, giving $45-51. $1.721 is the measured mean of the 64-agent `colonyGuards` boards; the "about $1.69" quoted for Phase 18 is the mean of its two 64-agent cells, $1.659 and $1.721.
- **The cap.** $250 per calendar month (P20-9). The user sees the cost estimate before the pilot and the pilot's projection before the main run, and may raise the cap then (P20-8). The ledger (`results/multiagent/llm/spend.jsonl`) holds $233.18, all from before November 2026, so `Budget` must count only the current month's spend first (NFR-7).
- **Wall time.** Stage 4 played its 80 boards in two batches of 1.8 and 1.9 hours. C1's 41 boards, 15 of them clean with a third more calls each, should take about 3.5-5 hours. Spend counts against the user's $100-a-month API credit.

**GPU (part b and the bridge check): about 5.5 A100 hours, against the plan's ~12,** on one of the two Colab Pro+ accounts:

- **The squads-of-4 arm** is 9 models × (10 clean boards × 32 agents × 40 turns + 10 liar boards × 24 honest agents × 40 turns) = 9 × 22,400 = 201,600 agent turns.
- **The rate.** Phase 17's step 0 evaluated 15 models on `teamSizeSuite`, 42,800 agent turns each, in about 16 hours: about 40,000 turns per A100 hour, model loading included. `RL17_PLAN`'s "about 9 more" hours for 9 models agrees (about 43,000 per hour). The squads-of-4 arm is then **about 5 hours**. Its prompts are 4-agent length, so this is conservative.
- **The bridge check (P20-11):** 2 sizes × 5 boards × 12 honest agents × 40 turns = 4,800 turns, about 0.5 hours with loading.
- **Without reuse**, re-running the one-board arm adds at least another 5 hours of longer 32-agent prompts: about 10-12 hours, the plan's figure.
- **Compute units.** At Phase 17's measured roughly 12 compute units per A100 hour, 5.5 hours is about 66 units, and 12 hours about 144.

## Decisions (the user, 2026-11-09 and 2026-11-10)

The user decided P20-1 to P20-14 on 2026-11-09, and P20-15 to P20-17 on 2026-11-10: P20-15 and P20-16 after a review of the specs, P20-17 during T3. P20-8, P20-9 and P20-13 were changed from the proposals; the others were accepted as proposed. P20-14 was added later that day, and it raised P20-8's expected ceiling; P20-10's open note was then settled. A change is marked **Changed**, and the text after it is the decided value. Two B3 decisions (Phase 22, the user, 2026-11-10) amend this phase: honest rule agents post cross clues on mirrors (P22-12, FR-A4), and B3's forecast in `C1_PLAN` covers 8 effects, not H20-1 to H20-5 alone (P22-8, FR-C4).

| ID | Decision | Decided value |
|---|---|---|
| P20-1 | How a subtask is coupled | **Accepted as proposed.** Every fourth subtask a squad receives (its 4th, 8th, ...) is coupled: deterministic, with no new random draws, so exactly a quarter. Its clue 0 is dealt within squad s (two holders) and its clue 1 to two agents of squad s + 1 (mod 8). Squad s + 1 sees the subtask as a **mirror** line: it can post its clue there but cannot open or answer it. Posts on the mirror stay off squad s's board. Every coupled arm has mirrors, `coupled` included, so the bridges are the only difference between arms. |
| P20-2 | Who is a bridge | **Accepted as proposed.** A bridge belongs to the receiving squad s and is the first honest non-guard slot of s (two bridges: the first two). It still opens and solves its own squad's subtasks. A bridge from s never holds the clues it relays, which are dealt in s + 1, so a relay is never its own clue. **Guarding bridge:** the first guard slot of s takes the bridge role and keeps `GUARD_RULE`, so the team (16 liars, 16 guards, 32 others) is the same as in `bridge1` and only who bridges changes. |
| P20-3 | What a bridge reads | **Accepted as proposed.** Its own squad's board in full, plus the next squad's mirror lines for its pair (each coupled subtask's posted values, with sender counts), not the next squad's whole board. Relays need only these lines, and a 3B bridge's prompt must fit the 3,072-token window (Phase 17: 8-agent prompts reach about 2,200 tokens). This reads the plan's "reads both boards" as the part of the second board that can be relayed. The alternative, the full neighbour board, is for Claude only. |
| P20-4 | How a relay works | **Accepted as proposed.** A relay is a bridge's share, on squad s's coupled subtask, of **any** value posted on its mirror, not only the leading one, so a bridge can relay a liar's value and guarding can matter. Relays go one way (s + 1 to s). The board shows a relay as the bridge's post, with no "relayed" label, so the counting display is unchanged. The harness logs each relay with its source post. The rule sentences are in design-low-level (`COUPLE_RULE`, `MIRROR_RULE`, `BRIDGE_RULE`). |
| P20-5 | Liars and mirrors | **Accepted as proposed.** Scripted liars in squad s + 1 count its mirrors among their targets and post false residues of the cross clue there, so false values can reach bridges. Liars in squad s may still post on any clue of their own subtasks, the cross clue included, as today. |
| P20-6 | Reused references and seeds | **Accepted as proposed.** Reuse Stage 4's `squads|independent` and the 64-agent run's `colonyGuards|independent` (N 64, seeds 1800-1807). They are replayed from the cache at $0 with C1's columns added, and every saved column must be unchanged (as `reusedRows4`). The 8-board arms use seeds 1800-1807, the 5-board arms 1800-1804 and the pilot 1890. Stage 4 has no clean `squads` cell to reuse, so `squads`' clean boards are new (P20-14). |
| P20-7 | Gate and secondary statistics | **Accepted as proposed**, with the point-estimate margin for part (ii) and the inert-bridge rule. Gate part (i): the sign-flip above. Part (ii): a point-estimate margin, mean(`bridge1` − `colonyGuards`) ≥ 0.5 × mean(`squads` − `colonyGuards`), reported with a bootstrap interval and an uncorrected sign-flip p of the per-board margin. Making part (ii) a test as well would form a family of two under Holm, which the plan's single named test does not have. Secondary tests use the 5 shared boards with uncorrected sign-flip p, whose smallest value is 1/32. H20-3: the win-back (`bridge1` − `coupled`) / (`squads` − `coupled`) > 0.5. H20-4: (`bridge2` − `bridge1`) < 0.25 × (`squads` − `coupled`). H20-5: the false share of relayed values, `bridgeGuard` against `bridge1`. *Implementation note (T5, not a changed decision):* `c1Summaries` marks H20-3 supported only when the coupling cost is above 0 and the win-back above 0.5, since the ratio is meaningless without a cost; H20-4 also reports a one-sided p for its margin below 0. **Inert-bridge rule:** if the gate passes but `bridge1` does not beat `coupled` on seeds 1800-1804 (point estimate), stop and ask before A1 adopts bridges. |
| P20-8 | Pilot checks and cost rule | Pilot: one 64-agent board each of `coupled`, `bridge1` and `bridgeGuard` (seed 1890, not analysed). Stop and ask if invalid replies reach 5%, if there are no mirror posts, if there are no relays on a bridge board, or if a bridge's input tokens per call exceed twice the squad board's 780 (1,560). **Changed (cost rule): report and wait.** Before the pilot, report its estimated cost to the user and wait for approval. After the pilot, report its projection of the main run (calls × the pilot's cost per call by arm, clean boards included) and wait for approval. The expected ceiling for the main run is $35, but nothing runs automatically under it. **Updated with P20-14:** the ceiling was $25; the clean boards put the main run at $25.3-30.6, so it was raised to $35, the top of that estimate plus about 15%. The pilot has no clean board. The pilot checks above are accepted as proposed. |
| P20-9 | API cap | **Changed.** No raise. The cap is $250 of total spend per calendar month (the user, 2026-11-09). It reset for November 2026, and the user has $100 of API credit per month. The user sees the cost estimate before each run (P20-8) and may raise the cap then. C1 (about $27-33 with P20-14's clean boards) and A2 (Phase 21, about $34-39) together, about $61-72, fit one month's credit. `Budget` must count only the current month's spend (NFR-7), and frozen plans record `cap=250.0` with `capNote='per calendar month (the user, 2026-11-09)'`. |
| P20-10 | Part b's grid | **Accepted as proposed.** 9 models (the warm start and `r17mix_s1`-`s8` final), 32 agents, plain board at Phase 17's settings, seeds 900-909, clean and with N // 4 = 8 liars (one per squad of 4). The squads-of-4 cells are new (about 5 A100 hours). The one-board cells reuse `eval_p17/*.csv` and `eval_p17s0/warm.csv` (`|n32`, `|n32liar`) at $0, after a check that their cell configuration equals the new cells' apart from `squads`. Measures: each adapter's welfare gain over the warm start on clean boards, and honest loss with liars. Alternative: re-run the one-board arm too (about 10-12 A100 hours, the plan's figure). **Weights (the user, 2026-11-09):** part b uses the final `r17mix` adapters, as published. They match the reused one-board rows and the preprint, so the two arms compare like with like. As the preprint's Phase 17 caveat says, the five halted runs' (s1, s2, s3, s6, s7) final weights are 2-4 updates past the checkpoint before the halt. |
| P20-11 | 3B bridge check (not in the plan) | **Accepted as proposed.** The warm start in A1's world (16 agents, counting board, r = 2, 4 guards, 4 liars, one bridge per pair), in squads of 8 and of 4, seeds 900-904, 40 turns: relays per bridge turn, mirror posts, the longest prompt, invalid replies. Descriptive, about 0.5 A100 hours. It tells A1, before `RL19_PLAN` is frozen, whether a model that never saw a relay makes any. |
| P20-12 | Relay credit in RL (for A1 and C3; C1's Claude boards keep the default reward) | **Accepted as proposed.** Under `scheme='credit'` or `'contest'`, the credit share for a relayed clue is split equally between the bridge and the first true poster of that clue on the mirror, so holders in s + 1 still earn for posting. `ContestLog` treats a relayed liar's value as the liar's, so contesting it can pay. Phase 19 recorded both on 2026-11-09 (its FR-A9 and T5). |
| P20-13 | Forecast | **Changed: wait for B3.** C1's main run waits until B3's fitted simulator exists and has been refit on C1's pilot. The forecast file's SHA-256 goes into `C1_PLAN` before the main run, and the forecast is scored afterwards in paper2's line, by B3's code (Phase 22), not C1's. There is no fallback to the unfitted rule agents. `RuleBridge` stays, because the simulator needs a rule-agent bridge to model bridges. Consequence: B3 must be specified and built before C1's main run, and A1 (Phase 19), which waits for Gate C1, waits for B3 too. Part b and the bridge check (P20-11) do not depend on B3 and may run earlier. |
| P20-14 | Clean boards (added 2026-11-09) | **Decided by the user.** 5 clean boards (no liars, so no scripted liars; all 64 agents honest; the 16 guards stay; seeds 1800-1804) for each of `squads`, `coupled` and `bridge1`: 15 new boards. `colonyGuards` gets none. Stage 4 has no clean `squads` cell at 64 agents, so none is reused. Purpose: the plan's core measure, cost without liars (the honest pooled share without liars), and whether coupling and bridges cost output when nobody lies; A1 trains in this world. Report each arm's honest pooled share and raw honest welfare on clean boards, and the contrasts `bridge1` − `squads` and `coupled` − `squads`, with uncorrected one-sided sign-flip p over the 5 boards (smallest p 1/32). Descriptive (H20-8); not part of Gate C1. Cost: $0.784-0.98 per board (README Cost), $11.8-13.7 in all. No clean pilot board. |
| P20-15 | The squad rule on coupled boards | **Decided by the user, 2026-11-10** (spec review). `SQUAD_RULE` ("you see, open and share only your squad's subtasks … only your squad sees your posts") stays byte-identical; the mirror and bridge rules open with "This is the one exception to the squad rule". The reused and clean `squads` cells keep their prompts. |
| P20-16 | Who sees the mirror lines | **Decided by the user, 2026-11-10** (spec review). Only the agents of s + 1 that hold the cross clue see its mirror line and its posts; other agents of s + 1 see none, so they cannot make invalid confirmations there and their prompts do not grow. Scripted liars of s + 1 still draw mirrors as targets (P20-5). |
| P20-17 | Relays in the rule-agent simulator | **Decided by the user, 2026-11-10** (found in T3). A relay is one post, so honest rule agents (who count a value as known at `Q` = 2 senders) never build on it, and `bridge1` gives them nothing. Left as is: a relay shows as one sender to Claude too. The unfitted simulator therefore predicts no bridge benefit for honest agents; B3's fitted `trustOne` decides whether relays get used. In the unfitted simulator, scripted `ClueLiar`s trust single posts, so relays feed liars' coupled solves (numpy `bridge1`, seed 1890: 32 coupled solves, all by liars; honest 0); B3's forecast should know this (Phase 22, P22-20). |

## Relation to the other experiments

- **A1 (Phase 19):** waits for Gate C1 (the user, 2026-11-08), and so also for B3, which C1's main run waits for (P20-13).
  - **Passes:** A1 trains in squads joined by bridges, with the `bridge1` configuration for every arm (Phase 19, P19-8, the user, 2026-11-10). A1 adds one engineering step: its speed check measures relays and the longest bridge prompt, and `WARM_ANSWERS` is measured in the bridged world.
  - **Fails, or the inert-bridge rule fires and the user declines bridges:** A1 uses squads without cross-squad subtasks.
  - **Part b and P20-11** inform A1's choice between squads of 4 and of 8, which A1's pilot makes.
  - **The clean boards (P20-14)** tell A1 whether its bridged world costs output on the boards without liars that its varied threat includes.
  - **A1's best arm** is evaluated descriptively in 64-agent squads with bridges, on C1's board.
- **A2:** runs alongside C1; it does not wait for B3 (P21-8). The two share the API credit and the $250-per-month cap (P20-9): about $61-72 together as specified (C1 $27-33 with its clean boards, A2 $34-39), against the plan's $65-90. Whichever phase is built first makes `Budget` count by month (NFR-7); the other reuses it.
- **B1:** C1's rows carry the existing Phase 18 measure columns, Phase 19's per-board columns (`contest_eval.contestColumns`) and bridge columns for B1 to adopt. C1 reports the plan's core measures where they apply: B1's gullibility, verification and collaboration; welfare per agent-turn and per 1,000 tokens; tokens per solved task; cost without liars (P20-14); the division of labour (Gorelick's index, per board); error correlation; and contamination across squads. Role persistence does not apply: C1 plays single boards, not sequences.
- **B3:** supplies the forecast (P20-13). B3 must be specified and built, and its simulator refit on C1's pilot, before C1's main run. It uses `RuleBridge` to model bridges. Part b, the bridge check and C1's pilot do not wait for it.
- **C3:** runs only if Gate C1 passes (and A1 or its emergence arm succeeds). C1's bridge board, relay log and `RuleBridge` are the base of C3's relay action and of the rule agents its new warm start imitates. Board choice is C3's to build (plan: weeks 4-10).
- **C4:** part b prompts Claude liars, told that guards exist, in 64-agent squads with bridges. It uses C1's `bridge1` world with `fault='adaptive'`, which C1's tests cover offline. Part a evaluates trained liars in 3B squads with bridges through `rollout`.
