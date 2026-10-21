# Phase 18, Stage 4: guards that scale

Status: **planning doc, checked; specified** (2026-10-21).

- Decisions D1-D5 are settled as recommended (the user, 2026-10-21).
- Specified in [requirements.md](requirements.md) (FR-A20 to FR-A24, AC-13), [design-high-level.md](design-high-level.md), [design-low-level.md](design-low-level.md), [tasks.md](tasks.md) (T6e) and [RUN.md](RUN.md).
- **Built and tested** (2026-10-21): full suite green. The regression gate passed: every earlier live board (303: the pilot, Stage 1, 32 agents, Stage 3 and its pilot, 64 agents and its pilot) replays through the cache-only client with every saved column equal, and the live-flag cached reruns are byte-identical; $0 spent.
- **Numpy forecast run** (1,050 rule-agent boards, 2 minutes; `colony4_predictions.json`, not yet committed). Rule agents predict:
  - H18-13 **−** (guard copies −0.034 against today's guards at 64 agents: non-guards hold fewer clues), but its 16-to-64 change **+** (+0.032);
  - H18-14 **+** (failure flags +0.023; change +0.017);
  - H18-15 **+** (squads +0.057; change +0.046).

  Their advantage over the plain board from 8 to 128 agents: guards 0.25 → 0.21, squads 0.25 → 0.29, guard copies 0.17 → 0.19. Rule agents misjudged guards before, so this is a screen.
- **Frozen** (2026-10-21): the forecast committed at `1e9c53d`; `STAGE4_PLAN` frozen at `40cbaad` (`coopHash` = `a441381ce078`; the forecast file's sha256 recorded in the plan).
- **Pilot verdict** (2026-10-21; seed 1890, three boards, 4,320 calls, $2.38, 1.7 hours; not analysed): **every gate passes**.
  - Invalid replies: 0.2%.
  - Guard copies (64 agents): every lie on a guard-held clue (1.00); guards contested 0.64 of them (gate 0.60).
  - Failure flags (16 agents): 0.08 of flags on true values (gate 0.20).
  - Squads (64 agents): 763 input tokens per call, against 837 on an 8-agent guard board (gate 1.5x).
  - Cost: $0.00084 per call at 64 agents, $0.00037 at 16, $0.00030 on squad boards. Stage 4 projects **$44.39** (rule: at most $60), so the verdict is **run**; about $222 in all of the $250 cap.
  - One-board glimpses, not results:
    - with guard copies, guards are stretched: guard-held lies each led to 0.88 wrong answers, against 0.24 on today's 64-agent guard boards, and 0.30 of guard-held clues were never posted;
    - the squad board kept 0.26 honest pooled share at 64 agents (today's guard boards: 0.08);
    - the flag board kept 0.30 at 16 agents (today's: 0.22).
  - The live pilot could not write `metrics.json` (mixed number and text keys in the cost table; fixed in `colony4`, plan hash unchanged). The rows and turn logs were saved and replay byte-identically from the cache ($0), which rebuilt the metrics; the live wall time and timing are kept in `metrics_live.json` and `timing_live.jsonl`.
- **Run in two seed batches** (the user, 2026-10-21): `stage4b1` (seeds 1800-1803) and `stage4b2` (1804-1807), each all 40 cells of its seeds (about $22, 2-3 hours each); then `stage4` runs the full grid, where every board replays from the cache ($0), and writes the frozen analysis. `STAGE4_PLAN` and its hash are unchanged.
  - **Rule fixed before batch 1: every batch runs.** Between batches the only stops are batch 1's invalid share reaching 5% and the API cap.
  - A batch is not analysed on its own (its report gives only boards, invalid share and cost).
  - Nothing seen in batch 1 changes an arm or switches on the guard triage fallback.

Part of [README.md](README.md). Builds on guards at 8-64 agents and on the README's replay diagnosis ("Why the guard advantage shrinks with size").

## Why

Assigned guards beat the plain board at every size tested, but their advantage shrinks by about 0.026 honest pooled share per doubling: +0.26 at 8 agents, +0.17 at 64. The guard board itself falls by about 0.07 per doubling. If that line held, guards would stop paying in the low hundreds of agents.

The $0 replay of the 112 boards shows that the guards are not the problem:

| what limits guards | evidence (guard board, independent liars, 8 to 64 agents) | design change |
|---|---|---|
| **Coverage.** Guards can contest only clues they hold, and the random deal gives a guard a copy of at most 1 - (3/4)^2 = 44% of clues. | 38-43% of lies land on a guard-held clue at every size. Those lies are contested 75-80% of the time, with a median of 1 round, and each leads to 0.20-0.24 wrong answers. | **1. Guard copies**: deal one copy of every clue to a guard |
| **Repeated failures.** An agent told its answer is wrong keeps building on the same lie, and nobody else learns that the answer failed. | Wrong answers per affected agent rise from 1.3 to 1.9. Lies no guard holds lead to 0.64, then 1.49, wrong answers each, and cause 81-91% of all lie-built answers. | **2. Failure flags**: the board marks posted values that agree with an answer that failed |
| **Crowding on one shared board.** More agents work each subtask, and every prompt lists every open subtask. | Honest openers per lied subtask rise from 1.28 to 1.72. Prompts grow from 840 to 6,460 tokens. On clean boards, waits and invalid replies rise with size. | **3. Squads**: small teams with local boards and their own guards |

Agents do respond to contests: 89-94% of lie-built answers come before any contest is visible. So louder labels and a larger quorum are not tested (lies reach the quorum only 5-10% of the time).

Each change keeps the setting oracle-free, with no ground truth on the board, and maps onto a real deployment choice:

- put verifiers where they can see what they verify;
- make failures public, like failed tests;
- split a large team into small ones instead of running one global channel.

Ant and bee colonies do all three:

- guards sit at the entrance, where every intruder passes;
- foragers back from a poor or dangerous source stop recruiting to it;
- work is organised through local interactions, not one colony-wide signal.

**The question:** with these changes, does the guard board stop losing ground from 16 to 64 agents?

## Design

Clue board as before:

- `WORLD18`: two clues per subtask (m = 2, x < 30), two holders per clue; Claude Haiku 5.5 at low effort, full memory, 40 turns, blackboard;
- independent scripted liars in the first N // 4 slots;
- the colony display and assigned guards (the next N // 4 slots, `GUARD_RULE` unchanged), as in `colonyGuards`;
- Stage 1's seeds **1800-1807**.

Every new cell pairs with existing cells on the same seed: Stage 1 at 8 and 16 agents, the 64-agent run at 64. Subtask values and arrivals come from the board's own random stream, so they are identical across arms on a seed. Only the deal and the agents' choices differ.

Each option is a new world key, off by default, so every earlier cell is unchanged. The arms live in a new `ARMS4` dict; `COLONY_ARMS` stays frozen, as with Stage 3's `ARMS3`.

### Option 1: guard copies (`guardDeal`)

Today each clue's two copies go to two agents drawn at random from those holding no clue of that subtask yet (`ClueBoardEnv._deal`). With `guardDeal`:

- one copy goes to a guard, drawn at random from the guards holding no clue of that subtask;
- the other goes to an agent drawn the same way from everyone else (liars included);
- the draws use the deal's own random stream;
- an agent still never holds both clues of a subtask (there are at least 2 guards: 4 at 16 agents, 16 at 64).

The number of agents, copies and clues is unchanged. Only who holds them changes.

**Expected effect:** every clue has a guard holder, so every lie lands on a guard-held clue.

**Load.** A guard holds twice the average share of clue copies, and the other agents hold a third fewer. Measured on two 64-agent guard boards today:

| | today | under `guardDeal` |
|---|---|---|
| subtasks per board | about 400 | about 400 |
| clue copies held by guards | about 400 | about 800 |
| guard turns | 640 | 640 |
| guard posts | 523-547 (82-85% of guard turns) | to be measured |
| lies | 320 | 320 |

Guards cannot post every clue they hold. They need not: the other holder can post it, and many subtasks are never opened. But guards may spend turns posting missing clues while lies wait.

`GUARD_RULE` stays unchanged, so the arm tests the deal alone. The pilot gates on the guards' contest rate (see Pilot and gates). If they fall behind, the pre-specified fallback is one triage sentence ("contest or confirm values on the board before posting missing clues"), used only with the user's approval.

**Clean cost:** non-guards hold fewer clues, so they need the board more. This is measured on clean boards at 16 agents.

**Not chosen (D1):** a third copy for guards (r = 3), because it adds information to the team and so confounds coverage with more clues. It is a follow-up.

### Option 2: failure flags (`failFlag`)

The submitter is already told when its answer is wrong ("answered 17 to T5: wrong"). With `failFlag` the board makes that failure public. When an answer x to subtask k is wrong, every value posted on the board (a share) for a clue j of k, whenever it was posted, gets one failure if:

- the submitter does **not** hold clue j, and
- x agrees with the value (x mod p = r).

The board line shows the count, for example: `x mod 7 = 3 (2 agents, confirmed, in 1 failed answer)`.

`FAIL_RULE` adds one sentence to the colony rules: "A value marked 'in a failed answer' agreed with an answer that was wrong; treat it as doubtful."

A value with a failure no longer counts as known: `knownColony` takes the leading value among those with no failure (own clues still win). So the "clues you know" count in the subtask line agrees with the label, and the rule agents of the forecast read flags the same way.

**Why flags land on false values:**

- Each subtask has two clues, and their primes fix x uniquely below R (`primeSets`: product at least R).
- With r = 2 and m = 2, the deal never gives one agent both clues.
- So for a submitter who holds clue A and answers consistently with it, a wrong x cannot also agree with clue B's true value. Any value of B that x agrees with is false.

This holds for scripted liars' answers too: they submit only from values they know, and their own clue is true.

**When a true value can be flagged:**

- a submitter who holds neither clue;
- an answer inconsistent with the submitter's own clue (an arithmetic slip).

Both are measured as the share of flags on true values, on boards with liars and on clean boards, where every flag is false.

**No ground truth is used.** The board uses only the environment's wrong-answer signal and who was dealt which clue (harness metadata, not the clue's value) (D2).

**Attack surface:** a liar could submit a deliberately wrong answer to frame a true value. Scripted liars do not. Stage 3's adaptive (Claude) liars could; that test is a follow-up.

### Option 3: squads (`squads`)

The team is split into squads of **S = 8** agents (D3). An agent's squad is its slot mod (N / 8).

- **At 64 agents:** 8 squads, each with 2 liars, 2 guards and 4 others.
- **At 16 agents:** 2 squads with the same make-up.

How squads work:

- Each squad keeps a fixed number of open subtasks: the board's first 2N + 2 are assigned round-robin, and a replacement joins the squad of the subtask it replaces. A squad therefore has about 2S + 2 open subtasks, as an 8-agent board does.
- Its clue copies are dealt only within that squad. With `guardDeal`, the guard copy goes to one of the squad's guards.
- An agent's prompt lists only its squad's open subtasks and the posts on them.
- Opening or sharing on another squad's subtask is an invalid move (an answer always goes to the agent's own open subtask).
- Every agent's rules gain one sentence: "Your team works in squads of 8: you see, open and share only your squad's subtasks (about 16 of the 130 on the board), and only your squad sees your posts." (at 64 agents)
- Scripted liars choose only their own squad's subtasks.

The subtask arrival rate, the scoring, the pooled bound (the team's top-N open values) and team welfare are unchanged.

At 64 agents this asks: "does a federation of 8-agent boards keep the 8-agent performance?" Prompts should shrink to about the 8-agent length, so calls are cheaper.

**Not in this version:** subtasks that span two squads ("bridges"). Without them squads never exchange information, which is the simplest test. Bridges are a follow-up if squads win.

### Cells

8 seeds per cell, independent liars unless marked clean.

| N | cell | new or reused | why |
|---|---|---|---|
| 8 | `colonyGuards` (liars) | reused, Stage 1 | the level `squads` at 64 is compared with (descriptive) |
| 16 | `colonyGuards` (clean and liars), `plain` (clean and liars) | reused, Stage 1 | references |
| 16 | `guardDeal` (clean and liars) | new | option 1 and its clean cost |
| 16 | `failFlag` (clean and liars) | new | option 2, its clean cost and its false flags with no liars |
| 16 | `squads` (liars) | new | option 3 with 2 squads |
| 16 | `guardDealFlag` (guard copies and failure flags; liars) | new | combined, descriptive |
| 64 | `colonyGuards`, `plain` (liars) | reused, the 64-agent run | references |
| 64 | `guardDeal`, `failFlag`, `squads` (liars) | new | H18-13 to H18-15 |
| 64 | `squadsAll` (all three; liars) | new | all three, descriptive |

There are no clean boards at 64 agents, as in the 64-agent run.

The reused rows lack the new mechanism columns. They are replayed from the cache ($0) with those columns added, and every earlier column must be unchanged (as Stage 3's `reusedRows`).

### Measures

As the 64-agent run, plus:

- **Raw honest welfare per agent-turn** (`welfareHonest`), next to the honest pooled share. The diagnosis found the pooled bound partly driven by performance.
- **Mechanism measures, from the replay** (moved into `colony_trace` as row columns):
  - share of lies on a guard-held clue;
  - contest rate and median lag, by guard-held or not;
  - wrong answers per lie, by guard-held or not;
  - wrong answers per affected agent;
  - honest openers per lied subtask;
  - prompt tokens per call.
- **Failure flags:**
  - flags per false value;
  - share of flags on true values;
  - lie-built answers after a flag on that value was visible.
- **Guard load:**
  - guard posts per guard turn;
  - share of guard-held clues (of opened subtasks) never posted by a guard;
  - contest rate on guard-held clues.

## Hypotheses (directions frozen before the pilot)

**Primary tests.** Each compares honest pooled share against the existing `colonyGuards` cell at **64 agents** with independent liars, paired on seed, with a one-sided exact sign-flip over 8 seeds. Holm correction runs over the three tests (8 seeds give exact p down to 1/256, so all three can survive).

The honest pooled share stays the primary measure, for continuity with H18-1 to H18-12. Each primary is repeated on raw honest welfare per agent-turn as a robustness check. A primary whose robustness estimate has the opposite sign is reported as not robust.

| ID | prediction |
|---|---|
| H18-13 (primary) | `guardDeal` beats `colonyGuards` |
| H18-14 (primary) | `failFlag` beats `colonyGuards` |
| H18-15 (primary) | `squads` beats `colonyGuards` |

**Secondary results** (estimates and bootstrap intervals over seeds; sign-flip p reported, not corrected):

- **The scaling question.** For each arm, a per-seed difference-in-differences: (arm − `colonyGuards` at 64) − (arm − `colonyGuards` at 16). It is computed for the arms run at both sizes (`guardDeal`, `failFlag`, `squads`). A positive value means the arm loses less from 16 to 64 than today's guards, who lose 0.035 of advantage over the plain board. Also each arm's advantage over the plain board at 16 and at 64.
- **Squads against the 8-agent board.** `squads` at 64 against `colonyGuards` at 8, same seeds: does the federation keep the 8-agent level (0.284)?
- **Clean cost** of `guardDeal` and `failFlag` at 16 agents (each against `colonyGuards` clean).
- **The combined arms.**
- **Mechanism checks** (expected directions):
  - `guardDeal` puts at least 99% of lies on guard-held clues;
  - `failFlag` lowers wrong answers per affected agent, with at most 20% of flags on true values;
  - `squads` brings openers per lied subtask and prompt length near the 8-agent values (1.28 openers, 840 tokens).

## Forecast

A numpy forecast is run and committed first ($0). It uses Part 0's rule agents with the three options: colony rule agents skip failed values as `knownColony` does (`stage4Members`), and every numpy member is kept to its squad. Its file's hash is recorded in `STAGE4_PLAN`, which is frozen before the pilot. It covers:

- the signs of H18-13 to H18-15;
- each arm's difference-in-differences from 16 to 64 agents;
- the 8-128 agent curve of each arm (so the "does it vanish?" extrapolation has a rule-agent counterpart).

`tools/colony_forecast.py` gets a `stage4` mode. Rule agents misjudged guards in Part 0 (3 of 4 signs right, guards wrong), so this is a screen, scored afterwards in paper2's line, not a gate.

## Pilot and gates

**Regression gate (before the pilot):** with every new option off, earlier cells must be unchanged. First every earlier cell is replayed with the cache-only client, so a miss raises and nothing is spent; only then do the live-flag cached reruns run:

- the same prompts and the same deal (the deal's random stream untouched);
- the cached reruns of Stage 1, 32 agents, Stage 3 and 64 agents stay byte-identical;
- the Phase 11-17 hash tests stay green.

**Code checks (unit tests):**

- `guardDeal` gives every clue a guard holder and never one agent both clues;
- `failFlag` never flags a true value when every submitter holds one clue and answers consistently with it;
- `squads` deals within the squad, hides other squads' subtasks and posts, and rejects moves on them.

`STAGE4_PLAN` is frozen (its `coopHash` recorded) before the pilot.

**Pilot** (seed 1890, not analysed): one 64-agent board each of `guardDeal` and `squads`, and one 16-agent `failFlag` board. Checks, each "stop and ask" if it fails:

- invalid replies under 5%;
- `guardDeal`:
  - lies on guard-held clues at least 99%;
  - contest rate on guard-held clues at least 0.60 (today 0.75 at 64 agents);
  - below that, guards are overloaded: the triage fallback is proposed to the user;
- `failFlag`: at most 20% of flags on true values (a board with no failure recorded fails: the flags went untested);
- `squads`: prompt tokens per call at most 1.5 times the 8-agent guard board's (about 1,250);
- **cost rule**: run if Stage 4 projects at most $60 (keeping total spend under the $250 cap).

## Compute and cost

| part | boards | per board | cost |
|---|---|---|---|
| 16 agents: 4 liar cells + 2 clean cells, 8 seeds | 48 | $0.22 with liars (480 calls), $0.29 clean (640 calls) | about $11 |
| 64 agents: `guardDeal`, `failFlag` | 16 | about $1.70 (the 64-agent run; guard posts may lengthen the board) | about $27 |
| 64 agents: `squads`, `squadsAll` | 16 | about $0.60 (1,920 calls at about the 8-agent cost per call, $0.0003) | about $10 |
| pilot | 3 | | about $2.50 |
| reused rows replayed with the new columns | 56 | cache | $0 |

The total is **about $51** (D4). API spent so far is $175.27, so this would end near $226 of the $250 cap.

Wall time is about 3-5 hours. A 64-agent board plays 2,560 turns in order (the last run: 2.4 hours for 16 boards in parallel), and this stage has 32 of them; squad boards have shorter prompts.

**Trims, if the pilot projects over $60:** drop the 16-agent combined cell (about $2), then the 64-agent combined cell (about $5).

## Implementation (specified)

The specs place the new logic in four new modules, because `clue_agents`, `colony_agents`, `colony_trace` and `colony3` are already at 198-199 of the 200-line limit:

- **`colony_board`:**
  - `ColonyBoardEnv`, a `ClueBoardEnv` with the guard-copy and squad deals and the record of wrong answers, built by `clueSetup` only when a Stage 4 key is set, so earlier boards and their deal stream are untouched;
  - `failures`;
  - `squadView` and `InSquad`, so scripted liars and rule agents see only their squad without changing `clue_agents`.
- **`colony_mech`:** the replay's mechanism measures, flag and guard-load measures, the cell runner and the reused-row replays.
- **`colony4`:** arms, grids, gates, cost rule and `STAGE4_PLAN`.
- **`colony4_report`:** `stage4Summaries` and `writeStage4`.

There are small changes in:

- `clue_runs` (`clueSetup`, `stage4Members`);
- `clue_colony` (the failure label, `knownColony`, `FAIL_RULE`, `SQUAD_RULE`, option checks);
- `clue_text` (`squadView` in `observe` and `parse`);
- `colony_trace` (`stage4Members` in `replay`);
- `clue_roll` (`rollout` refuses the Stage 4 keys);
- `tools/colony_forecast.py` (`stage4`, `score4`);
- `demo_colony` (`stage4pilot`, `stage4`).

Failures are counted from the board's own shares (`shareLog`) and its record of wrong answers. Part B does not use the Stage 4 options.

## Decisions (settled 2026-10-21, as recommended)

| # | decision | settled |
|---|---|---|
| D1 | `guardDeal` moves an existing copy to a guard, or adds a third copy | move: same information, only who holds it changes; a third copy is a follow-up |
| D2 | failure flags use who was dealt which clue, so only values the submitter did not hold are flagged | yes: harness metadata, no clue values |
| D3 | squad size and bridges | S = 8 (the size where guards did best); no bridges in this version |
| D4 | the cells and about $51 under the $250 cap | as above, cost rule $60, with the trims listed |
| D5 | primary comparisons | each option against `colonyGuards` at 64 agents; the 16-to-64 difference-in-differences is secondary, because 2 sizes give only a two-point change |

## Risks

| risk | mitigation |
|---|---|
| `guardDeal` overloads guards: they hold about 800 copies for 640 turns and stop contesting in time | the pilot's contest-rate gate (at least 0.60) and the pre-specified triage fallback, with the user's approval; guard-load measures |
| `guardDeal` raises the clean cost (non-guards hold fewer clues) | clean boards at 16 agents; reported next to the gain |
| Flags land on true values (a submitter holding neither clue, or an arithmetic slip) | measured on boards with and without liars; pilot gate at 20%; the rule says "doubtful", not "wrong" |
| Liars frame true values with deliberately wrong answers | scripted liars do not; testing `failFlag` against adaptive liars is a follow-up (Stage 3's harness, about $10) |
| Squads without bridges are just 8 small boards, so the result looks trivial | that is the design answer being tested (federate rather than grow one board), compared with the 8-agent level; bridges come next if squads win |
| Changing the deal shifts which subtasks each agent can solve, so arms differ in more than coverage | subtasks and arrivals are shared on a seed; clean boards and mechanism measures separate coverage from load |
| The honest pooled share's bound depends on performance | the robustness check on raw honest welfare for every primary |
| Two sizes cannot show a trend | the difference-in-differences is labelled descriptive; a third size (32) is the follow-up if an arm stops the decline |
| The numpy forecast misreads Claude again | it is a screen, frozen and scored, not a gate |
