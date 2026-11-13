# Plan: Phase 19, training the guard role with RL (contest credit)

Status: **engineering done except the bridged world, not run** (2026-11-08). T1-T4 are implemented and tested, committed in bfe5e5b (2026-11-08); nothing has run on a GPU. A1 waits for Gate C1 (squads joined by bridges, specified as Phase 20) and Gate A2 (prompted screens), per the user's decisions below. C1's main run waits for B3's fitted simulator (Phase 20, P20-13), so A1 waits for B3 too; C1's code has existed since 2026-11-10; T5a and T5b were done on 2026-11-12. **Gate C1 recorded (2026-11-12, Phase 20's T11):** Gate C1 passed on 2026-11-11 (`bridge1` − `colonyGuards` +0.105 [0.086, 0.125], p 0.004; margin +0.020, p 0.047; robust on raw welfare) and the inert-bridge flag did not fire (`bridge1` − `coupled` +0.013), so A1 trains in squads joined by bridges (P19-1), with `bridge1` on every arm (P19-8, settled by Gates C1b, C1c and C1d). Cost without liars (H20-8, clean boards, seeds 1800-1804, honest pooled share): squads 0.336, coupled squads 0.244 (−0.092), squads with `bridge1` 0.278 (−0.058 against squads). B3 is built and refit (Phase 22). T5a and T5b are done (2026-11-12): A1's bridged world is wired in (`rl19_bridge.py`: `bridge1` on every arm, single-squad cells unbridged, relay-aware contest credit and measures, border contests, `longestBridge` in the step metrics) and Gate C1 is recorded in `RL19_PLAN['gates']`. A1 now waits only for Gate A2 (Phase 21), then the speed check (T6) on Colab. C3 stays eligible. This phase is experiment A1 of the Stage 1 research plan: the main RL experiment of project A, "train agents into the verification role with RL". It tests the plan's hypotheses P2 (caution that tracks the threat; arms 1-3) and P1 (roles from experience; arm 4). The user decided P19-1 to P19-5 and P19-7 (2026-11-08) and P19-8 to P19-11 (2026-11-10); only P19-6 (the GPU budget) is open, until the speed check.

**Order relative to the plan.** The plan runs A1 in weeks 4-10, after its cheap screens:

- Gate C1 sets A1's training world (squads with bridges);
- Gate A2 decides whether arm 4 keeps per-agent records.

This phase was specified first, by the user's choice of the simpler task, but it runs in the plan's order: C1 and A2 run first. C1's main run waits for B3's fitted simulator (Phase 20, P20-13, the user, 2026-11-09), so B3 (Phase 22, specified with the user's decisions on 2026-11-10, not built) must be built and refit on C1's pilot before Gate C1 can be read, and A1 waits for B3 too. The plan's fallback world (squads without cross-squad subtasks) applies only if Gate C1 fails; if Gate A2 fails, arm 4 runs without records, as the plan says.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the frozen plans, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Components, data flow, key decisions, gates |
| [design-low-level.md](design-low-level.md) | Module contents, the contest-credit reward, the penalty, measures, statistics, tests |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |

## Why

explRL found that verification works when it is assigned, and does not appear on its own:

- **Assigned guards work.** A quarter of the team assigned as guards won back about two-thirds of the liars' damage at 8 and 16 agents (Phase 18, Stages 1-2).
- **Nobody volunteers.** No honest Claude agent took the guard role when it was offered on 24 boards (Stage 3).
- **Team reward created no roles.** Five team-reward RL runs of the 3B model created none. Two of them collapsed into "everyone posts, nobody solves" (Phase 18 Part B).
- **Credit reward keeps agents sharing.** It pays the poster of a clue when a solver uses it (Phases 12-13, 17).

A1 extends credit to contests. A guard that posts a clue's true value against a liar's false one is paid when the true value is used, and also when it prevents a wrong answer. The question is whether this trains better guards than credit alone, and whether training across threat levels makes everyone's waiting track the threat. That second part is the plasticity hypothesis P2, from honeybee guards that grow more permissive when robbing declines (Downs and Ratnieks 2000).

## Questions and hypotheses

| ID | Hypothesis | Family |
|---|---|---|
| H19-1 | Contest credit (arm 2) beats credit alone (arm 1) on damage won back at 4 liars of 16 | Primary (Gate A1) |
| H19-2 | Varied threat makes waiting track the threat: arm 2's waiting rate (the share of a non-guard's answers that used a posted value only after a second sender had posted it) rises with liar share (0, 2, 4, 6, 8 of 16) more steeply than arm 3's, which trained at a fixed 4. Arm 2 uses posted values at once without liars, waits more as liars become common, and at the untrained shares 2 and 8 waits at intermediate and higher rates, as honeybee guards grew more permissive when robbing declined (Downs and Ratnieks 2000) | Primary (Gate A1) |
| H19-3 | Guarding costs little without liars: arm 2's honest pooled share without liars stays within 0.05 of the warm start's without guards (the plain board in the same squads and seeds), with raw welfare reported beside it | Constraint on Gate A1 |
| H19-4 | With no assignment and contest credit open to all (arm 4), agents at 16 agents specialize (Part B's variance-ratio index) more than the warm start, whose rule-agent imitation already specializes (+3.44 in Part B). Guard-like specialists appear only if A2 finds that experience makes roles persist; specialization then grows with team size, 8 to 32 (Ulrich et al. 2018). After the most active quarter of contesters is removed, others take up the role (Bonabeau et al. 1996); when they return, the earlier arrangement may not come back (Theraulaz et al. 1998) | Secondary; its 16-agent test is the kill criterion's |
| H19-5 | Goal drift stays low: misreporting (honest false values per 100 shares) does not rise above the warm start's, and no arm collapses into all-sharing | Secondary |
| H19-6 | Agents wait less when subtasks expire sooner, as ants lower their quorum when a move is urgent (Franks et al. 2003) | Secondary (the plan's) |

Each prediction can fail. H19-1 fails if contests add nothing over shared clues. H19-2 fails if waiting stays flat across liar shares, or rises as steeply under fixed threat.

## Design summary

- **Model and recipe.**
  - Qwen2.5-3B with one shared LoRA adapter, warm-started from rule-agent imitation, as in Phases 12-18.
  - Phase 17's recipe `p17a` with `FIX17` (value tokens, per-token clip, `maxLen` 3,072) and Part B's KL fix `FIX18` (k3 capped at 10; a KL halt only after 2 steps in a row).
  - A wrong answer costs 3 in training (0.5 plus the extra 2.5 of `BASE17`) to curb guessing. 30 steps per run.
  - The plan's training hygiene applies: KL capped per token, a KL halt only after 2 steps in a row, and a new answer halt when answers per board stay below a third of the warm start's for 3 steps. Halted runs are evaluated at the last checkpoint whose policy produced no step of the halting streak (a step's rollouts come from the policy before its update), and reported.
- **Board.**
  - Phase 18's counting board (`colony`), with two holders per clue (`r = 2`) and scripted independent liars.
  - 16 agents in squads joined by bridges, as the plan intends (P19-1): A1 waits for C1 (Phase 20) to build bridges and for Gate C1. Each squad has its own board view, subtasks and guards. Only if Gate C1 fails does A1 train in the plan's fallback, squads without cross-squad subtasks.
  - A quarter of the agents are guards (4 of 16), placed evenly across squads.
- **Arms.**
  1. Guards on credit reward only; varied threat.
  2. Guards on contest credit; varied threat.
  3. Guards on contest credit; a fixed 4 liars of 16, with arm 2's two subtask lifetimes.
  4. No assignment; contest credit open to every agent (the emergence arm). As in the plan, each agent has its own record of past payoffs, played over sequences of boards. It runs without records if Gate A2 fails (P19-5).

  "Varied threat" means each board draws 0, 4 or 6 liars of 16 and one of two subtask lifetimes, 15 or 30 turns (the board's default is 30; P19-7). Arms 1-3 get 8 seeds each, arm 4 gets 5.
- **Reference for damage won back and cost without liars.** The warm start without guards, as the plan's Terms define it for 3B teams: the plain board (no counting, no guards) in the same squads, the same world (with the same coupling and bridges in the bridged world, P19-9) and on the same seeds. It is common to every arm, so H19-1 compares honest losses and H19-3 prices guarding against the same team.
- **Pilot of the squad size.** Two 10-step runs of arm 2, with squads of 4 and squads of 8, in the training world. The main runs use the size with the larger gain. Phase 17 gained at 4 agents but barely at 8.
- **Gate A1 (after the main runs).**
  - Two one-sided exact permutation tests over 8 runs per arm, with Holm across the two: H19-1 and H19-2.
  - H19-3 must also hold, with raw welfare reported beside it.
  - **Stability check:** the main cell trains the first 2 runs and stops; the rest run only after the user checks their halts and sets `STABLE19 = True`.
  - **Kill criterion:** C3 and any further training of honest teams stop if Gate A1 fails and arm 4's specialization at 16 agents does not exceed the warm start's (a single one-sided sign-flip over its 5 seeds). C4 runs either way, against arm 1's teams if Gate A1 fails. The team-scaling eval and the assigned structures stand regardless.
- **Evaluation beyond the gate.** Following the plan's held-out tests:
  - team sizes 8 and 32;
  - mistaken members and colluding liars, fault types never trained;
  - boards without liars;
  - C4's trained liars once they exist.

  The best arm is also evaluated descriptively in 64-agent squads joined by bridges, as the plan says; the main cell requires bridged rollouts for it.
- **Cost.** About 295 A100 hours on the two Colab Pro+ accounts, as in the plan:
  - 29 runs of about 9 hours at 16 agents. This is projected from Part B's 628 s per step on mixed 4- and 8-agent boards, assuming each update trains a fixed number of replies;
  - about 6.5 hours for the squad-size pilot (2 runs of 10 steps, plus about 0.5 hours of evaluation);
  - about 28 hours of evaluation.

  No API spend. The speed check replaces these estimates before the main runs; it also reports the longest prompt, a bridge agent's included (it reads its own squad's board and its pair's mirror lines, P20-3). The user decides the GPU budget after the speed check (P19-6).

## Decisions

| ID | Decision | Value |
|---|---|---|
| P19-1 | Training world | Squads joined by bridges (C1), as the plan intends. A1 waits for C1 (Phase 20) and Gate C1; squads without cross-squad subtasks only if Gate C1 fails. |
| P19-2 | Contest bonus decay | The bonus halves every 4 turns after the lie (half-life `H` = 4), so a contest within a turn or two pays nearly in full and delay does not pay. |
| P19-3 | All-sharing penalty | On a training board where the team's honest answers fall below a third of the warm start's mean for that board type (in the arm's own world: with guards for arms 1-3, without for arm 4), every honest agent loses 0.5 at the board's end. No agent is penalized for its own mix of posts and answers. |
| P19-4 | Held-out liar shares for H19-2 | 2 and 8 of 16, added to the trained 0, 4 and 6 at evaluation. |
| P19-5 | Arm 4's records | The records are built either way (the plan's engineering row puts them in A1's code). A2 runs first; arm 4 keeps records if Gate A2 passes and drops them if it fails, set when `RL19_PLAN` is frozen. **Format (A2's P21-11, accepted 2026-11-09):** if Gate A2 passes, the record line (`Records.line`) also lists, per board, the contests made and the correct answers that followed, beside the payoffs, so A1 tests the format that passed. Set at the freeze (T8 step 1). |
| P19-6 | GPU budget (open) | About 295 A100 hours across the two Pro+ accounts, or a lever, in the plan's order (its risk table: "Cut arm 4 and C4's secondary runs first … primary arms keep 8 seeds"): arm 4 dropped (saves about 45 hours), then 20 steps per run (about a third of the roughly 261 training hours). Arm 3 down to 5 seeds (about 27 hours) would be a stated deviation, because arm 3 is in H19-2, a primary test. The speed check (T6, about 3 A100 hours) is outside the 295. Decided after the speed check. |
| P19-7 | Subtask lifetimes | 15 and 30 turns. The plan names two lifetimes without values; 30 is the board's default and 15 makes subtasks urgent. |
| P19-8 | Bridge configuration | `bridge1` for every arm (arm 4 has no guard slot for `bridgeGuard`). If Gate C1's inert-bridge rule fires, or P20-11 finds the 3B warm start never relays, stop and ask before the speed check whether A1 keeps bridges; a decline means squads without cross-squad subtasks, recorded with Gate C1 as {passed, inertFired, userAcceptsBridges}. A late C1 delays A1; there is no fallback for lateness. **Amended by P23-7 (the user, 2026-11-11):** A1's bridged world follows Gate C1b (Phase 23). Pass: evidence on every arm; arms 1-3 get a dedicated bridge in squads of 8 and solver bridges in squads of 4; arm 4 gets evidence and solver bridges. Gate C1b's safety part fails: no bridges. Only its effectiveness part fails: stop and ask. **Settled by Gates C1b and C1c (2026-11-12): `bridge1` for every arm, as first decided.** Gate C1b asked (`bridgeFix` − `bridge1` −0.003, p 0.62; safer, contamination −0.048); the user chose to confirm `bridgeRole` on fresh seeds (Phase 24); Gate C1c fails (`bridgeRole` − `bridge1` −0.013 [−0.029, 0.002], p 0.92, seeds 1810-1817; contamination −0.040, non-inferior). A1 gets no evidence and no dedicated bridge. **Gate C1d (Phase 25, 2026-11-12) fails, so the mirror window is not adopted either:** `mirrorWindow` − `bridge1` +0.008 [−0.008, 0.025], p 0.22, seeds 1820-1827; contamination +0.044, 95th percentile 0.076 against the 0.05 margin. On clean boards the window is better (+0.063, 8 of 8), so it stays a candidate for worlds without liars. |
| P19-9 | Measures and cells in the bridged world | Answers on coupled subtasks are left out of the waiting rate, exempt from `enforceK` and reported apart. The damage and cost reference is the plain board with the same coupling and bridges. Cells with a single squad (N // S < 2: the held-out 8-agent cells and the 8-agent sequences `seq8` when S = 8) run without coupling, as stated, since C1's `checkBridge` refuses them. The 64-agent cells use squads of 8, C1's board. |
| P19-10 | Contest credit and mirror posts | Mirror posts are not board shares, so a true mirror post against a mirror lie is not a contest and earns no contest credit. Contest credit stays on the squad's own board, where contesting a relayed lie is paid (through `relaySource`). **Amended by P23-8 (the user, 2026-11-11):** in the bridged world, a true holder's mirror post that contests a false mirror value earns contest credit, as a contest on the squad's own board does; with Phase 23's evidence it reaches the receiving squad. Note (2026-11-12): A1 has no evidence (P19-8 settled on `bridge1`), so this credit's reason "it reaches the receiving squad" no longer holds. **Kept by the user (2026-11-12):** a true holder's mirror post that contests a false mirror value earns contest credit in A1, without evidence. Its watchers (the user, 2026-11-12, over bridges only and a flat payment) are the receiving squad's honest agents without the clue that were shown a lie of the slot before any true value, on their own board after a relay or on the mirror for the pair's bridge; each one's later correct solve pays as any contest does. Only the first true mirror post against the lie is a border contest (one per slot): mirror lies never go away and the receiving squad never sees the mirror, so repeated true posts would otherwise each pay the same watchers (found in review, 2026-11-12). |
| P19-11 | Colluding liars in the bridged world | C1 converts only exact `ClueLiar` members to mirror liars (`bridgeMembers`), so in the bridged world the held-out `collude` cell has no mirror lies; it is reported as such (no new code). |

**Decided by the user (2026-11-08):**

- **P19-1, training world.** Wait for C1: A1 trains in squads joined by bridges, as the plan intends. C1 is built and Gate C1 runs before A1, so A1 runs in the plan's order; the fallback (squads without cross-squad subtasks) applies only if Gate C1 fails. `SPEED19`, `PILOT19_PLAN` and `RL19_PLAN` carry this `world`; `rl19Config` refuses 'bridges' (naming Phase 20) until bridged rollouts exist, and the three Colab cells assert that Gate C1 is recorded and that the world matches it.
- **P19-5, arm 4's records.** A2 runs first, alongside C1. Arm 4 keeps records if Gate A2 passes and drops them if it fails; this is set at the freeze.
- **P19-2, P19-3, P19-4 and P19-7.** Accepted as proposed: a half-life of 4 turns, a penalty of 0.5, held-out shares of 2 and 8 of 16, and lifetimes of 15 and 30 turns.
- **P19-8 and P19-9 (the user, 2026-11-10).** Accepted as proposed after the spec review: `bridge1` with stop-and-ask on an inert result, waiting for Gate C1 however late (the plan's risk row was corrected to match), coupled answers left out of the waiting rate and `enforceK`, a coupled reference, unbridged single-squad cells and 64-agent cells in squads of 8.
- **P19-10 and P19-11 (the user, 2026-11-10).** Accepted as recommended: a mirror post is not a contest and earns no contest credit (contest credit stays on the squad's own board, where contesting a relayed lie is paid); the held-out `collude` cell has no mirror lies in the bridged world and is reported as such.
- **P19-6, GPU budget.** Decided after the speed check, which reports the projection in A100 hours, compute units and months of the two Pro+ plans.
- **Power.** The primary tests are powered for a 1.5-SD effect with 8 seeds per arm, about 0.87 under Holm at Phase 17's spread. A 1-SD effect would likely read as "not shown", and the report will say so.
- **Order of API spend.** C1 and A2 run before the capability plan's month 1, on the $100-a-month API credit: the plan put them at about $65-90, and Phases 20 and 21 project about $61-72 together (C1 $27-33 with its clean boards, Phase 20 P20-14; A2 $34-39). The cap is $250 of total spend per calendar month (the user, 2026-11-09); the user sees each cost estimate before a run and may raise the cap then (Phase 20, P20-9; Phase 21, P21-10). This holds once `Budget` counts by month (Phase 20, T0): the ledger still counts all-time spend, $233.18 before November.

These values are recorded in `DECISIONS19` (`explRL/rl19_grid.py`).

**Handoffs accepted by the user (2026-11-09), from Phases 20 and 21:**

- **Record format (Phase 21, P21-11).** If Gate A2 passes, arm 4's record line also lists, per board, the contests made and the correct answers that followed (other honest agents' correct answers to the contested subtask after the contest), beside the payoffs. Set at the `RL19_PLAN` freeze (T8 step 1). If Gate A2 fails or is not read, arm 4 has no records, so the format does not arise.
- **Relay credit (Phase 20, P20-12).** In the bridged world, under scheme `'credit'` or `'contest'`, a relayed clue's credit share is split equally between the bridge and the first true poster of that clue on the mirror. `ContestLog` treats a relayed liar's value as the liar's (through `relaySource`), so contesting a relayed lie can pay. The split itself is built in Phase 20 (`BridgeBoardEnv._creditTo` and `_reward`, P20-12); the relay-aware `ContestLog` (`rl19_bridge.BridgeContestLog`) was built in T5a (FR-A9, 2026-11-12).

## Relation to the other experiments

- **A2 (prompted screens):** its experience screen (Gate A2) sets arm 4's records (P19-5). If Gate A2 passes, arm 4's record line also takes A2's format, the contests made and the correct answers that followed per board, beside the payoffs (P21-11, accepted 2026-11-09). Its rule-text screen does not change Phase 19, whose counting board already replaces the re-sharing sentence. A2 is specified as Phase 21. Its rule-text screen (8 and 32 agents, suppression) and the capability plan's E4 drop-only arm (16 agents, first wrong answers) share one implementation of the drop-only prompt and complement each other; E4 does not replace A2's screen.
- **C1 (squads and bridges, Phase 20):** runs before A1, and A1 waits for Gate C1. C1's main run waits for B3's fitted simulator (P20-13), so A1 waits for B3 too. If Gate C1 passes, A1 trains in squads with bridges, with relay credit as P20-12 (accepted 2026-11-09); if it fails, in squads without cross-squad subtasks. Either way, A1's best arm is evaluated, descriptively, in 64-agent squads with bridges, and cross-squad contamination is Phase 20's `bridgeColumns['crossContamination']`, already in every bridged row through `coopRows`. C1's clean boards (P20-14) report the cost without liars of squads, coupled squads and squads with one bridge per pair: the worlds A1 may train in, whose varied threat includes boards without liars.
- **C3 (emergent structure):** runs only if Gate C1 passes and either Gate A1 passes or arm 4's specialization exceeds the warm start's.
- **C4 (trained liars):** trains liars against A1's best team, or arm 1's if Gate A1 fails.
