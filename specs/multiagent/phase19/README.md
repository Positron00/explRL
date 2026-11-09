# Plan: Phase 19, training the guard role with RL (contest credit)

Status: **engineering done except the bridged world, not run** (2026-11-08). T1-T4 are implemented and tested, not committed; nothing has run on a GPU. A1 waits for C1 (squads joined by bridges, specified as Phase 20) and A2 (prompted screens), per the user's decisions below; once C1's code exists, T5 adds training in squads with bridges. This phase is experiment A1 of the Stage 1 research plan: the main RL experiment of project A, "train agents into the verification role with RL". It tests the plan's hypotheses P2 (caution that tracks the threat; arms 1-3) and P1 (roles from experience; arm 4). The user decided P19-1 to P19-5 and P19-7; only P19-6 (the GPU budget) is open, until the speed check.

**Order relative to the plan.** The plan runs A1 in weeks 4-10, after its cheap screens:

- Gate C1 sets A1's training world (squads with bridges);
- Gate A2 decides whether arm 4 keeps per-agent records.

This phase was specified first, by the user's choice of the simpler task, but it runs in the plan's order: C1 and A2 run first. The plan's fallback world (squads without cross-squad subtasks) applies only if Gate C1 fails; if Gate A2 fails, arm 4 runs without records, as the plan says.

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
- **Reference for damage won back and cost without liars.** The warm start without guards, as the plan's Terms define it for 3B teams: the plain board (no counting, no guards) in the same squads, the same world and on the same seeds. It is common to every arm, so H19-1 compares honest losses and H19-3 prices guarding against the same team.
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

  No API spend. The speed check replaces these estimates before the main runs; it also reports the longest prompt, a bridge agent's included (it reads two squads' boards). The user decides the GPU budget after the speed check (P19-6).

## Decisions

| ID | Decision | Value |
|---|---|---|
| P19-1 | Training world | Squads joined by bridges (C1), as the plan intends. A1 waits for C1 (Phase 20) and Gate C1; squads without cross-squad subtasks only if Gate C1 fails. |
| P19-2 | Contest bonus decay | The bonus halves every 4 turns after the lie (half-life `H` = 4), so a contest within a turn or two pays nearly in full and delay does not pay. |
| P19-3 | All-sharing penalty | On a training board where the team's honest answers fall below a third of the warm start's mean for that board type (in the arm's own world: with guards for arms 1-3, without for arm 4), every honest agent loses 0.5 at the board's end. No agent is penalized for its own mix of posts and answers. |
| P19-4 | Held-out liar shares for H19-2 | 2 and 8 of 16, added to the trained 0, 4 and 6 at evaluation. |
| P19-5 | Arm 4's records | The records are built either way (the plan's engineering row puts them in A1's code). A2 runs first; arm 4 keeps records if Gate A2 passes and drops them if it fails, set when `RL19_PLAN` is frozen. |
| P19-6 | GPU budget (open) | About 295 A100 hours across the two Pro+ accounts, or a lever: arm 3 down to 5 seeds (saves about 27 hours), arm 4 dropped (about 45), or 20 steps per run (about a third). Arm 3 is needed for H19-2, so dropping it removes a primary test. Decided after the speed check. |
| P19-7 | Subtask lifetimes | 15 and 30 turns. The plan names two lifetimes without values; 30 is the board's default and 15 makes subtasks urgent. |

**Decided by the user (2026-11-08):**

- **P19-1, training world.** Wait for C1: A1 trains in squads joined by bridges, as the plan intends. C1 is built and Gate C1 runs before A1, so A1 runs in the plan's order; the fallback (squads without cross-squad subtasks) applies only if Gate C1 fails. `SPEED19`, `PILOT19_PLAN` and `RL19_PLAN` carry this `world`; `rl19Config` refuses 'bridges' (naming Phase 20) until bridged rollouts exist, and the three Colab cells assert that Gate C1 is recorded and that the world matches it.
- **P19-5, arm 4's records.** A2 runs first, alongside C1. Arm 4 keeps records if Gate A2 passes and drops them if it fails; this is set at the freeze.
- **P19-2, P19-3, P19-4 and P19-7.** Accepted as proposed: a half-life of 4 turns, a penalty of 0.5, held-out shares of 2 and 8 of 16, and lifetimes of 15 and 30 turns.
- **P19-6, GPU budget.** Decided after the speed check, which reports the projection in A100 hours, compute units and months of the two Pro+ plans.
- **Power.** The primary tests are powered for a 1.5-SD effect with 8 seeds per arm, about 0.87 under Holm at Phase 17's spread. A 1-SD effect would likely read as "not shown", and the report will say so.
- **Order of API spend.** C1 and A2 (about $65-90) run before the capability plan's month 1, on the $100-a-month API credit.

These values are recorded in `DECISIONS19` (`explRL/rl19_grid.py`).

## Relation to the other experiments

- **A2 (prompted screens):** its rule-text screen and experience screen set arm 4's records (P19-5). A2 is specified as Phase 21. Its rule-text screen (8 and 32 agents, suppression) and the capability plan's E4 drop-only arm (16 agents, first wrong answers) share one implementation of the drop-only prompt and complement each other; E4 does not replace A2's screen.
- **C1 (squads and bridges, Phase 20):** runs before A1. If Gate C1 passes, A1 trains in squads with bridges; if it fails, in squads without cross-squad subtasks. Either way, A1's best arm is evaluated, descriptively, in 64-agent squads with bridges, and cross-squad contamination is measured once bridged rollouts exist.
- **C3 (emergent structure):** runs only if Gate C1 passes and either Gate A1 passes or arm 4's specialization exceeds the warm start's.
- **C4 (trained liars):** trains liars against A1's best team, or arm 1's if Gate A1 fails.
