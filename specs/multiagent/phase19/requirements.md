# Requirements: Phase 19, contest credit

Part of [README.md](README.md) (plan and decisions P19-1 to P19-11). It builds on these modules:

- `clue_rl` (`RLConfig`, `trainRL`) and `rl17_grid`, `rl17_update`, `rl17_train` (`RL17Config`, `trainRL17`, `FIX17`, claiming);
- `rl18_grid` (`FIX18`, `evalAdapter`, `colonySuite`);
- `clueboard` (`_creditTo`, `_reward`) and `clue_colony` (`tally`, guard slots and rules);
- `colony_board` (`ColonyBoardEnv`, squads) and `colony_trace` (contests, confirmations);
- `rl16_report` (exact tests, hierarchical bootstrap).

## Terms

Terms are as in Phases 16-18. In addition:

- **Contest:** an honest agent's post of a clue's true value while the board's tally for that subtask and clue shows a value a liar posted, which is false.
- **Contest credit:** two parts, paid to the contester (the plan's Terms: "the credit share when a solver uses the contester's value, plus a decaying 0.5 for each honest agent without the clue who saw the liar's value first and later answered correctly").
  - **Credit share:** when a solver uses the contester's value, the contester gets the credit share, by credit reward's existing rule (`_creditTo`).

    That rule credits the first true post of each clue the solver lacked. A contest is normally that first true post, because the board showed only the lie before it. If an honest agent had posted the true value earlier, that agent keeps the credit, as under credit reward.
  - **Prevention bonus:** 0.5 × 2^(−(t_c − t_l) / H) for each honest agent (a "watcher") that meets three conditions:
    - it did not hold the clue;
    - it saw the liar's value first, that is, it was shown the lie (posted at t_l) before it was shown any true value of that clue and before the contest at t_c;
    - it later solved that subtask with a correct answer, strictly after the contest (t > t_c).

  Contests against false values posted by honest agents earn nothing, and false posts earn nothing, the contester's own included.
- **Role-conditioned reward:** guard slots are paid credit plus contest credit; other honest slots are paid credit only. In arm 4, every honest slot is paid both.
- **All-sharing penalty:** on a training board where the honest agents' answers (submissions) fall below a third of the warm start's mean for that board type (team size, liar count, lifetime) in the arm's own world (4 guards for arms 1-3; no guards for arm 4), every honest agent loses `sharePenalty` (P19-3) at the board's end.
- **Board type:** team size, liar count and subtask lifetime.
- **Varied threat:** each training board draws its liar count from {0, 4, 6} of 16 and its subtask lifetime from {15, 30} turns (P19-7). Arm 3 fixes 4 liars and draws the same two lifetimes.
- **Per-agent record (arm 4):** each agent's prompt carries its own past payoffs from contests and solves over earlier boards in a sequence of 6 boards. Records are reset between sequences; training rollouts play sequences, one per board slot (team size, liar count, board, GRPO copy), so a sequence's liar slots never change.
- **Training world (P19-1):** 16 agents in squads joined by bridges (C1, Phase 20): a bridge agent reads its own squad's board and its pair's mirror lines on the next squad's board (P20-3), and relays values posted there onto its own squad's coupled subtasks. Squads without cross-squad subtasks are used only if Gate C1 fails.
- **Waiting rate (the plan's Terms):** the share of a non-guard's answers that used a posted value only after a second sender had posted it.
  - An answer *uses a posted value* when it agrees, mod p_j, with a value posted before it for a clue j of the subtask that the agent does not hold. Guesses that agree with no posted value are not counted, and a refused submission (`enforceK`) is no answer.
  - It *waited* when every posted value it used had at least two distinct senders by then.
  - In the bridged world, answers on coupled subtasks are left out of the waiting rate and reported apart (P19-9): their cross clue reaches the squad's board only through the bridge's relay, so they could never wait.
- **Damage won back:** 1 − (honest loss of the arm) / (honest loss of the reference), as in Phase 18, on the same boards. The reference is the warm start without guards (the plan's Terms for 3B teams): the plain board (no counting, no guards) in the same squads and world, with the same coupling and bridges in the bridged world (P19-9), and on the same seeds, common to every arm. Honest loss is clean welfare minus welfare with liars.
- **Cost without liars:** honest pooled share on boards without liars, the reference's (the warm start without guards, as above) minus the arm's; raw welfare the same way.
- **Regret:** welfare lost against the best fixed waiting threshold at the same liar share: for each liar count and lifetime, the warm start's best `enforceK` there, minus the arm's welfare; averaged over the grid.
- **Specialization:** Part B's variance-ratio index (the variance across agents of their share of turns spent sharing, over its binomial expectation) across boards, minus its shuffled-turns null.
- **Division of labour:** Gorelick et al. (2004)'s index, the plan's measure: the mutual information between agents and tasks (contest, other share, submit, open, wait), normalized by the tasks' marginal entropy. Reported separately from specialization.
- **Role persistence:** the correlation, across agents, of each agent's share of contesting turns between consecutive boards of a sequence.
- **Gullibility:** first wrong answers made while misinformed per honest agent-turn: an agent's first wrong answer to a subtask while a false value was posted for one of its clues the agent does not hold. Beside it, **suppression**: the share of liar-first clues (the first value posted was a liar's false one) that no honest agent later corrected.
- **Error correlation:** the share of honest wrong answers that repeat a wrong value another honest agent gave the same subtask earlier (correlated errors). **Contamination across squads** (an answer in one squad built on a false value from another) is Phase 20's `bridgeColumns['crossContamination']`, already in every bridged row through `coopRows`; `contestColumns` is unchanged.

## Functional requirements

### Part A: board and reward
- **FR-A1** Squads in RL rollouts:
  - The text environment used by `rollout` accepts `colony`, `r`, `guards` and `squads` from `RL17Config.world`.
  - Each squad gets its own board view, subtasks and liars.
  - Liar counts may be uneven across squads: liars are dealt to squads in order, so 6 of 16 in 4 squads gives 2, 2, 1, 1.
  - Guards are spread evenly across squads.
- **FR-A2** `ContestLog`: from the board's share log and the tally, it records every contest with its time, contester, slot and the lie it answers. For each contest it also records the honest agents that were shown the lie before it, and whether and when each later solved the subtask.
- **FR-A3** Contest credit:
  - `scheme='contest'` keeps credit reward's `_creditTo` for solves.
  - It adds each contest's prevention bonus to the contester's pending reward when the qualifying solve happens.
  - `contestSlots` says who can earn it: `'guards'` (arms 2, 3) or `'all'` (arm 4).
  - `halfLife` is `H`.
  - At `scheme='credit'` the rewards equal `clueboard`'s exactly.
- **FR-A4** The all-sharing penalty is applied at a board's end from a frozen reference table (`WARM_ANSWERS`, measured in the speed check), as `sharePenalty` on every honest slot. The table is kept per squad size and per guard count: with 4 guards (arms 1-3) and without guards (arm 4, whose penalty and answer halt use the guard-free table).
- **FR-A5** The varied-threat mix: `threat=((0, 4, 6), lifetimes)` draws each step's board types from seeded RNGs; every configuration sees the same board seeds at a given step.
- **FR-A6** The enforced waiting threshold, for evaluation only: `enforceK` in {1, 2, 3} refuses a submission using a posted value supported by fewer than `enforceK` senders, and counts the refusal as a wait. Answers on coupled subtasks are exempt (P19-9). Swept with the warm start, it gives the best fixed threshold for the regret measure.
- **FR-A7** Per-agent records for 3B agents (the plan's engineering row): an option `records` in {False, 'payoffs', 'a2'}; `'payoffs'` (today's `True`) adds each agent's own past payoffs to its prompt across a sequence of 6 boards, for training and evaluation. In training, records are keyed by board slot (team size, liar count, board, GRPO copy), so the liar slots stay fixed within a sequence. Built in this phase whatever P19-5 decides; arm 4 uses it only if Gate A2 has passed, and then in the `'a2'` format (P21-11): beside the payoffs, per board, the contests the agent made and the correct answers that followed them (at most one per subtask, Phase 21's rule). If Gate A2 is not read (too few calls or not run), arm 4 runs without records, recorded as a deviation (Phase 21).
  - **Record format (A2's P21-11, accepted 2026-11-09).** If Gate A2 passes, the record line (`contest.Records.line`) also lists, per earlier board, the contests the agent made and the correct answers that followed (correct answers to the contested subtask by other honest agents after the contest), beside the payoffs. So A1 tests the format that passed in A2. `RL19_PLAN` records the format at the freeze (T8 step 1).
- **FR-A8** The answer halt (the plan's training hygiene): a run halts when answers per board stay below a third of the warm start's (`WARM_ANSWERS`) for 3 steps in a row. This joins `FIX18`'s KL rule and the invalid-reply halt. A halted run is evaluated with the last checkpoint whose policy produced no step of its halting streak (`evalAdapter19`: step m's rollouts and logged KL come from the policy before step m's update, ckpt-(m-1), so a streak of n steps ending at step h is evaluated at ckpt-(h-n-1)), and reported.
- **FR-A9** The bridged world (P19-1): A1 trains and is evaluated in squads joined by bridges once C1's code (Phase 20) exists. `SPEED19`, `PILOT19_PLAN` and `RL19_PLAN` carry `world` (`'bridges'`, from `DECISIONS19['P19_1']`; `'squads'` only if Gate C1 fails), read by `rl19Config`. Until bridged rollouts exist, `rl19Config` and `contestSuite` refuse `'bridges'` with a `NotImplementedError` naming Phase 20. The bridged rollouts must log a bridge agent's longest prompt plus reply (`longestBridge`), computed in Phase 19's own code (`rl19_step` / `rl19_bridge`) from the step rollout's prompts and `board.bridgeOf`; `SPEED19` also records `bridgePromptTokens(cfg, seeds, tok=<3B tokenizer>, policy=<warm LocalPolicy>)['bridge']` (the prompt only). `bridge_agents` is at 198 lines and `clue_roll` at 199, so neither takes this code.
  - **Contest credit and mirror posts (P19-10, the user, 2026-11-10).** Mirror posts are not board shares, so a true mirror post against a mirror lie is not a contest and earns no contest credit. Contest credit stays on the squad's own board, where contesting a relayed lie is paid.
  - **Relay credit (Phase 20's P20-12, accepted 2026-11-09).** Under `scheme='credit'` or `'contest'`, a relayed clue's credit share is split equally between the bridge and the first true poster of that clue on the mirror. `ContestLog` treats a relayed liar's value as the liar's (it reads `bridge_board.relaySource`), so a contest against a relayed lie earns contest credit. The split is built in Phase 20 (`BridgeBoardEnv._creditTo` and `_reward`); the relay-aware `ContestLog` is built in T5a: it looks up `relaySource` at contest time, since `relayLog` is written after the relay's own `onShare`. At the default schemes, and on boards without bridges, rewards are unchanged.

### Part B: plans, grid, Colab
- **FR-B1** `RL19Config(RL17Config)` adds `contestSlots`, `halfLife`, `sharePenalty`, `threat`, `records` and `haltAnswers` (the answer halt, FR-A8) at defaults that reproduce `RL17Config`. `configHash19` leaves them out at their defaults, so the Phase 17-18 hashes are unchanged; `records='a2'` and `'payoffs'` hash differently. `RL19_PLAN` records the format as `recordFormat`.
- **FR-B2** `SPEED19`: a 3-step speed check of arm 2 at 16 agents in squads of 4 and squads of 8, in its `world`. It records:
  - seconds per step and the longest prompt plus reply, a bridge agent's reported apart (it reads its own squad's board and its pair's mirror lines, P20-3; the 3,072 window is refused if either exceeds it);
  - invalid replies;
  - `WARM_ANSWERS`, from warm-start rollouts on every training board type, with 4 guards and without guards;
  - Colab compute units per A100 hour.

  The projection assumes each update trains a fixed number of replies, as the plan's 9 hours per run does. If the check finds 16-agent steps much slower, the reply sample per update (`turnFraction`) is the lever, set in `RL19_PLAN`.
- **FR-B3** `PILOT19_PLAN`, frozen before the pilot:
  - arm 2, 10 steps, seed 1, in squads of 4 and squads of 8, in its `world`;
  - the selection rule: honest welfare at 4 liars of 16 minus the warm start's, on 5 held-out boards (seeds 950-954) per adapter; the larger gain wins, and squads of 4 win ties.
- **FR-B4** `RL19_PLAN`, frozen after the pilot and before the main runs:
  - the chosen squad size, and the training world: squads with bridges (P19-1), or squads without cross-squad subtasks only if Gate C1 failed; Gate C1's outcome is recorded in `gates`;
  - arm 4 with or without records (P19-5), and with records, A2's record format (P21-11, FR-A7);
  - the arms, seeds and steps, and the projected hours confirmed by the user;
  - P19-2 to P19-5 and P19-7 to P19-11 as decided;
  - the evaluation grid (FR-C1), H19-1 to H19-6 with tests and families, and the claim rules.
- **FR-B5** Claiming as Phase 17 (`claim`, `TAKEOVER`, one evaluation host), so the two Pro+ accounts share one Drive folder.
- **FR-B6** A section "Phase 19" in `nbs/colab_clue_rl.ipynb` with three cells, each one cell that runs to its end and is resumable, checkpointing every step. The cells assert that the plans are frozen, that Gate C1 is recorded (`RL19_PLAN['gates']['C1']`), and that the plan's world matches it:
  - speed check;
  - pilot;
  - main (claimed runs, then evaluation and packing). It trains the first 2 runs and stops when they finish, printing their halts (the stability check); the rest run only after `STABLE19 = True` is set.

### Part C: evaluation and analysis
- **FR-C1** `contestSuite(models)`, per model:
  - 16 agents in the chosen squads of the training world;
  - the reward scheme of the prompts: the default (individual) on every board, as in Phases 17-18, so every arm sees the same reward feedback; arm 4's sequences use arm 4's world (contest credit open to all). Contests are counted after the game, whatever the scheme;
  - liar counts 0, 2, 4, 6, 8 of 16, with both lifetimes;
  - seeds 900-909, 40 turns;
  - the warm start without guards (the plain board: no counting, no guards) in the same squads and seeds, as the reference for damage won back and cost without liars;
  - the warm start with `enforceK` 1, 2, 3, for regret (the best threshold chosen at each liar count and lifetime).

  Held-out tests, as the plan requires of every trained policy:
  - team sizes 8 and 32 (outside training) at 4 liars per 16;
  - fault types never trained: mistaken members (`MistakenAgent`) and colluding liars (`ColludingLiar`), at 4 of 16. In the bridged world C1 converts only exact `ClueLiar` members to mirror liars, so the `collude` cell has no mirror lies; it is reported as such (P19-11, the user, 2026-11-10; no new code);
  - in the bridged world, cells with a single squad (N // S < 2: the held-out 8-agent cells, and the 8-agent sequences `seq8` when S = 8) run without coupling, since C1's `checkBridge` refuses them (P19-9);
  - boards without liars (included above);
  - C4's trained liars, added once they exist.

  Arm 4's adapters, and the warm start, are evaluated over sequences of 6 boards at 8, 16 and 32 agents. At 16 agents, the most active quarter of contesters is removed after board 3 and returns after board 5.

  The best arm (arm 2 if Gate A1 passes, else the arm with the most damage won back) is also evaluated descriptively in 64-agent squads joined by bridges; this needs bridged rollouts, and the main cell refuses it until they exist.
- **FR-C2** `rl19Summaries`, per run:
  - damage won back;
  - contests per lie and per guard-held lie, and time to contest (the median over every contest);
  - misreporting and cost without liars;
  - waiting rate by liar count × lifetime, by liar count, and its slope and regret;
  - specialization (Part B's variance ratio) at 8, 16 and 32 agents and its slope over log2 of team size, the division of labour (Gorelick's index) at the same sizes, role persistence, and how they recover after the removal and the return (arm 4);
  - the plan's core measures, as the team-scaling eval (B1) defines them:
    - gullibility, as the plan's Terms define it: the share of honest answers made while misinformed (right or wrong), contamination (honest answers built on a false clue, `colony_trace`'s column), and suppression (liar-first clues left uncorrected); first wrong answers made while misinformed per honest agent-turn (`misinformedFirst`) is kept as a named variant;
    - tokens per solved task;
    - verification: contests per lie, time to contest, and the share of lies on a guarded clue;
    - collaboration (sharing per held clue);
    - error correlation (repeated wrong values); contamination across squads, Phase 20's `bridgeColumns['crossContamination']`, already in every bridged row through `coopRows`;
    - welfare per agent-turn and per 1,000 tokens;
  - halts by cause.

  It reports H19-1 to H19-6 (H19-5 and H19-6 secondary), with Holm within the primary family, and refuses rows unless every run covers the grid.
- **FR-C3** `writeRL19`, `figRL19` (`rl19.png`), and `demo_rl19` (quick: synthetic; full: flag `train`).

## Quality requirements

- **NFR-1** Phase 5-18 reference outputs and configuration hashes are unchanged; `trainRL` and `trainRL17` behave the same at their defaults.
- **NFR-2** Offline tests need no network, key or GPU; `torch` is used only in tests flagged `train`.
- **NFR-3** No API spend.
- **NFR-4** Seeds are fixed, resumes are exact, and two hosts never train the same run.
- **NFR-5** Each module stays under 200 lines.

## Acceptance criteria

- **AC-1** Regression: NFR-1, and the full suite passes.
- **AC-2** Board: squads deal the stated uneven liar counts and even guards. At `scheme='credit'` the rewards match `clueboard` on recorded games.
- **AC-3** Contest credit, on hand-built boards:
  - a contest at lag 0 and lag `H` pays 0.5 and 0.25 per qualifying solve; a solve at the contest's own time does not qualify;
  - a contest against an honest false value pays nothing;
  - a non-guard pays nothing at `contestSlots='guards'`;
  - an agent that held the clue does not qualify.
- **AC-3b** A watcher shown a true value of the clue before the lie does not qualify, and a contest that is not the first true post earns the bonus but not the credit share.
- **AC-4** The penalty fires exactly when answers fall below a third of the reference, and on every honest slot. The answer halt fires after exactly 3 such steps in a row.
- **AC-4b** Records: an agent's record lists only its own payoffs, and resets between sequences. With A2's format (P21-11), it also lists, per board, the agent's own contests and the correct answers that followed, counted on a hand-built board.
- **AC-5** The trainer: one `trainRL19` step at the defaults equals `trainRL17`'s (flag `train`, tiny model). Liar slots are never trained.
- **AC-6** Plans: `PILOT19_PLAN` is frozen before the pilot cell runs. `RL19_PLAN` is frozen, with the user's confirmation of the hours, before the main cell runs. Each cell stops until Gate C1 is recorded and its world matches it; the main cell trains only the first 2 runs until `STABLE19` is set.
- **AC-7** Analysis: the exact tests and Holm recover known effects on synthetic runs, and every `RL19_PLAN` item is reported.
- **AC-8** World: `rl19Config`, `speedConfig19`, `pilotConfig19`, `warmCells` and `contestSuite` refuse `'bridges'` with a `NotImplementedError` naming Phase 20 until T5a wires in bridged rollouts; the 64-agent cells always need them. After T5a, a hand-built bridged board shows P20-12's split of a relayed clue's credit share, and a contest against a relayed liar's value pays the contester.
- **AC-9** Threat: at a given step every arm draws the same board types, and arm 3's lifetimes are arm 2's (FR-A5).
- **AC-10** `enforceK`: 1 never refuses; 2 refuses a value with one sender and logs a wait; an answer on a coupled subtask is never refused (FR-A6, P19-9).
- **AC-11** `contestSuite` builds the cells FR-C1 lists, at the stated sizes, liar counts and seeds.

## Out of scope

- Building bridges and cross-squad subtasks (C1, Phase 20) and board choice (C3). A1 trains in C1's squads with bridges (FR-A9) once that code exists; squads without cross-squad subtasks only if Gate C1 fails.
- Trained liars (C4).
- Claude or other API agents.
- Teams larger than 16 in training.
