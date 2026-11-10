# Requirements: Phase 21, experience and rule-text screens

Part of [README.md](README.md) (plan and decisions P21-1 to P21-14). It builds on these modules:

- `clue_colony` (`SHARE_AGAIN`, `GUARD_RULE`, `VOLUNTEER_RULE`, `colonyRules`, `guardSlots`, `checkOptions`), `clue_text` (`TextClueEnv`), `clue_fix` (`fixOptions`);
- `colony_grid` (`WORLD18`, `colonyCell`), `colony3` (`volunteering`, `liarBehaviour`, `costRule3`, `complianceGate`), `colony_trace` (`replay`, `colonyColumns`, `specIndex`), `colony_report` (`signFlipExact`, `bootSeeds`);
- `clue_agents` (`ClueLiar`), `clue_runs` (`runClue`), `llm_runs` (`runLLMCell`, `cellRow`), `llm_client` (`ResponseCache`), `llm_budget` (`Budget`, `PRICES`);
- `scale_grid` (`scaleGrid`, Phase 14's `scaleB` cells), `fix_grid` (`fixCell`), `liar_trace` (`traceRun`, `cacheOnlyClient`) and `liar_report` (`mechanics`, Phase 15's suppression);
- `contest` (`ContestLog`) and `contest_eval` (`contestsOf`, `contestColumns`, `misinformedFirst`, `uncorrected`, `sameWrong`) from Phase 19, for contests and the core measures' counts on a finished board;
- `rl19_measures` (`index`, `ratio`, `lags`) and `rl19_spec` (`dolIndex`, and `persistence`'s rule) from Phase 19, for the core measures;
- `bench_stats` (`holm`).

## Terms

Terms are as in Phases 14-19. In addition:

- **Team:** 16 slots, of which the first 4 are scripted liars and 12 are honest Claude Haiku agents. The honest agents keep their identity (`a` = 0..11) across the team's 6 boards.
- **Seating:** a permutation, seeded by team and board, that seats identities in slots 4-15 on each board (P21-3).
- **Guard identities:** 4 honest identities drawn at random per team (a quarter of the team). On boards 1-2 they sit in the guard slots `guardSlots(env)` = 4-7. Two of them, drawn at random, are the **success guards**; the other two are the **failure guards**.
- **Targeted liar:** a scripted liar for boards 1-2. On a lying turn (every other turn, as `ClueLiar`) it posts a false residue for a clue of an open subtask that a success guard holds and no failure guard holds. If none is open, it lies on a clue that no failure guard holds, and it never lies on a clue a failure guard holds (P21-2).
- **Contest:** as Phase 19 (`contestsOf`): an honest post of a clue's true value while the slot shows a false value first posted by a liar.
- **Correct answers that followed:** for a contest on subtask k at time t_c, the correct answers to k submitted after t_c by honest agents other than the contester (at most one per subtask, since only the first correct answer scores). ContestLog's **watcher** count (honest agents who lacked the clue, saw the lie first and later solved) is reported beside it (P21-4).
- **Own record:** in the own-record arm, one line per earlier board of the team's sequence, giving the agent's own contests and the correct answers that followed. It covers boards 1 to b-1 and is shown on boards 3-6 (P21-4).
- **Shared record:** the same two numbers summed over the team's honest agents, per earlier board, with no names; every honest agent sees the same line.
- **Board line:** "This is board b of 6 played by the same team." It is shown to every honest agent in every arm, on every board.
- **Guarding:** an agent's turns posting a residue of a clue it holds, over its turns on that board. A contest is such a post. This is the plan's "share of turns spent posting or contesting clues it holds" (P21-5).
- **Contrast:** per team and arm, the mean over boards 3-6 of (mean guarding of the 2 success guards − mean guarding of the 2 failure guards).
- **Role persistence:** the plan's term: the correlation of each honest agent's share of contesting turns between consecutive boards, averaged over the 5 consecutive pairs. It is the rule of Phase 19's `rl19_spec.persistence`.
- **Division of labour:** Gorelick et al. (2004)'s index, as Phase 19 defines it (`rl19_spec.dolIndex`): the mutual information between honest identities and tasks (contest, other share, submit, open, wait) over the tasks' marginal entropy, pooled over a team's boards 3-6.
- **Cost without liars:** the plan's core measure (honest pooled share without liars). **Not measured in A2**, a recorded gap: P21-6 chose liar boards only, and P1's boards always have liars.
- **Drop-only prompt:** the plain board's rules with the sentence `SHARE_AGAIN` ("A clue shared once is known to everyone who saw it, so sharing it again only helps teammates who did not see it.") removed (world key `dropShare`). Nothing replaces it.
- **Liar-first slot:** a (subtask, clue) whose first post was by a liar. **Suppressed:** no honest agent posted its true residue later (Phase 15, `TRACE_PLAN` M3). **suppressedHeld:** the same, over liar-first slots whose clue has an honest holder (P21-7).

## Functional requirements

### Part A: board options (shared code)
- **FR-A1** `dropShare` (P21-9). With `world['dropShare']` true, `colonyRules` removes `SHARE_AGAIN` from the plain board's rules: the sentence and the space before it, so the paragraph ends cleanly.
  - `checkOptions` refuses `dropShare` with `colony` or `confirm`, which already replace the sentence.
  - The rules assert that the sentence was present before removal, as `colonyRules` already does for `colony`.
  - `fixOptions` passes it to `TextClueEnv`.
  - Phase 15's `traceRun` accepts cells whose only option is `dropShare`, so the tracer scores P2's and E4's drop-only cells.
  - The capability plan's E4 uses the same key.
- **FR-A2** Per-slot lines. `world['slotLines']` maps a slot to text that `colonyRules` appends to that slot's system text after the slot's role sentence. It carries the board line and the record line (P21-4). Slots it does not name get nothing, and it makes `slotRules` true.
- **FR-A3** `TargetedLiar(ClueLiar)` with `hit` and `avoid` slot sets, as in Terms. It never posts on a clue held by a slot in `avoid`. Its lying cadence and false-residue draw are `ClueLiar`'s.
- **FR-A4** A board runner `runBoard21(cfg, seed, client)`: `runClue` with the liars built from `world['targets']` (TargetedLiars with `hit` and `avoid`) instead of `faultMembers`. It returns `runClue`'s rows and log plus Phase 21's columns (FR-C1). Without `targets` it equals `runClue`'s rows and log, plus Phase 21's columns.

### Part B: sequences, grids and plans
- **FR-B1** `seating(team, board)`: the seeded seating; `guardIds(team)` and `successIds(team)`: the guard identities and the success pair. Seeded by the team (the seating also by the board), never by the arm, so every arm gets the same seating and roles.
- **FR-B2** `boardCell21(team, b, arm, history)`: the cell for board b of a team's sequence.
  - Boards 1-2: `WORLD18`, `colony`, 4 guards, 4 TargetedLiars (`targets`: the slots of the success and failure guards), and the board line only. The cell is identical in every arm.
  - Boards 3-6: `WORLD18`, `colony`, `volunteer`, 4 `ClueLiar`s, and the arm's record line built from `history`, the team's finished boards 1 to b-1.
  - The board seed is 10 × team + b.
- **FR-B3** `recordLines(arm, history, b, team)`: the per-slot lines of P21-4, from each finished board's contests (`contestsOf`) and correct answers that followed, mapped from slots to identities by the seating.
- **FR-B4** `runSequences21(teams, arms, spec)`: plays sequences in 6 waves by board position. Every team's board b runs in parallel (`runWorkload`) once its board b-1 has finished in that arm. Boards 1-2 run once per team: waves 1-2 run one cell per team, keyed without the arm, and its rows and record history are copied into each arm (the response cache alone would not stop three parallel live calls, because `ResponseCache.put` stores a reply only after the live call). Waves 3-6 run one cell per team and arm. It writes `runs.csv`, `turns.jsonl` and `records.jsonl` (each board's record lines).
- **FR-B5** `p2Grid()`: Phase 14's `scaleB` baseline cells with N // 4 liars at N 8 and 32 (`fixCell`, `CLUE_SETTINGS`), seeds 900-907, original and drop-only. The original cells at seeds 900-904 must be byte-identical requests to Phase 14's, so they replay from the cache.
- **FR-B6** `A2_PLAN`, frozen and hashed (`coopHash`) before the pilot. It holds:
  - the arms, teams, seeds, board seeds, seating rule and record texts;
  - H21-1 to H21-4 with their tests and families, the manipulation check and the claim rules;
  - the cost rule (report and wait, expected ceiling $50) and the cap (`cap=250.0`, `capNote='per calendar month (the user, 2026-11-09)'`);
  - the forecasts of P21-8.
- **FR-B7** `pilotGrid21()` (team 2190, own-record arm, 6 boards; one drop-only board at N 32, seed 990), `pilotCheck21(rows)` (P21-12) and `costRule21(perCall)`: the main grid's new calls times the pilot's measured cost per call, reported beside the expected ceiling ($50). It never returns `run` on its own: the main grid runs only after the user approves the projection (P21-10).
- **FR-B8** `demo_a2` stages behind `EXPLRL_A2_STAGE`, as `demo_colony` does: `pilot`, `quick` (fake client), `main` (only once the pilot verdict is recorded and the user's approval of the projection is in `A2_PLAN['approved']['main']`, which the stage asserts; also noted in the README), and `rerun` (the cache only, $0).

### Part C: measures and analysis
- **FR-C1** Per board, Phase 21's columns:
  - per identity: guarding, contests, correct answers that followed, watchers, shares of held clues, answers;
  - per board: the success and failure guards' guarding; liar posts, and their share on success-guard clues and on failure-guard clues (the latter must be 0 on boards 1-2); `volunteers` (Stage 3); `specIndex` and its null;
  - `colonyColumns`: honest pooled share, contamination, suppression, contests and confirmations;
  - Phase 19's `contest_eval.contestColumns(cfg, board, [log])`, and the row keys `agents` (per slot: the liar's slot 0-3, or the honest identity + 4), `pos` (b − 1) and `seqId` (the team). `a2Summaries` builds an index in `rl19_spec`'s layout (level `<arm>|seq16`, with the shared boards 1-2 copied into each arm), so `rl19_spec`'s functions read A2's rows unchanged (FR-C5).
- **FR-C2** Per P2 board: `suppressed` (Phase 15), `suppressedHeld`, liar-first slots with and without an honest holder, `contaminated`, first wrong answers per honest agent-turn (E4's primary measure, counted without the misinformed flag), honest pooled share, sharing per held clue, and Phase 19's `contestColumns`.
- **FR-C3** `a2Summaries(rows, plan)`:
  - H21-1 (Gate A2) with H21-2, the own-record contrast against 0, beside it (P21-5);
  - the contrast in each arm with a bootstrap interval over teams;
  - role persistence, volunteers, specialization and the division of labour by arm;
  - the core measures (FR-C5);
  - H21-3 with Holm across N 8 and 32;
  - the manipulation check;
  - the claim rules.

  It refuses to report unless every planned board is present, except with `partial='stopped'` (a stop after wave 2): then it reports P2, the manipulation check and "Gate A2 not read". `a2TeamEstimates(rows)` gives the per-team contrasts and P2 differences with no coverage check; `a2Summaries` uses it, and so does Phase 22's `a2Forecast` on the pilot.
- **FR-C4** `writeA2` (`report.md`, `metrics.json`), `figA2` (`a2.png`: guarding by board and arm, success against failure; P2's suppression by size and prompt), and `syntheticRows21` with known effects for the offline tests.
- **FR-C5** The plan's core measures, where they apply, reusing Phase 19's functions by name:
  - **division of labour (P1):** Gorelick's index per team and arm on boards 3-6, `rl19_spec.dolIndex(rs, 4, positions=range(2, 6))` on the team's rows; the arm's mean with a bootstrap interval over teams; descriptive (H21-4). Boards 1-2 are shared by the arms and assigned, so they are left out;
  - **role persistence (P1):** `rl19_spec.persistence`'s rule on the team's rows (all 5 board pairs), and over boards 3-6 only;
  - **gullibility and suppression:** `rl19_measures.ratio` over the arm's boards 3-6 (boards 1-2, shared and assigned, reported once, apart): `misinformedFirst` / `honestTurns` and `uncorrected` / `liarFirst`; on P2 beside E4's measure and `suppressedHeld`;
  - **verification:** contests per lie (`contests` / `liarPosts`), time to contest (median of `rl19_measures.lags`), share of lies on a guarded clue (`guardLies` / `liarPosts`, P1 boards 1-2);
  - **collaboration:** sharing per held clue, as now;
  - **error correlation:** `sameWrong` / `wrongHonest`;
  - **welfare per agent-turn** (`welfare`, `welfareHonest`) and **per 1,000 tokens** (as `welfarePerKTok` in `rl19_measures.runMeasures`, with the board's N in place of 16), and **tokens per solved task** ((`inputTokens` + `outputTokens`) / `solved`);
  - **not measured:** cost without liars and damage won back (both need honest welfare without liars on the same boards, and no A2 board is clean; recorded gaps, Terms), and contamination across squads (A2 has no squads).

## Quality requirements

- **NFR-1** Phase 5-19 reference outputs and configuration hashes are unchanged: the new world keys are absent at their defaults, and every earlier cell's prompts are byte-identical. A cached rerun of Stage 3 and of Phase 14's `scaleB` cells through the cache-only client is a free regression gate.
- **NFR-2** Offline tests need no network, key or GPU. Live calls run only with `EXPLRL_LLM_LIVE=1`, the response cache and the spend ledger with its cap.
- **NFR-3** API spend stays within the cap of $250 per calendar month (P21-10). The user approves the pilot's estimated cost before the pilot and its projection of the main grid before the main run.
- **NFR-4** Seeds are fixed. A rerun from the cache is byte-identical, and an interrupted sequence resumes from its finished boards.
- **NFR-5** Each module stays under 200 lines. `clue_text` (193 lines) and `colony_agents` (198) take no new code beyond option passing. New code goes into new modules.
- **NFR-6** Notebook first: each module is written in its notebook and exported with `nbdev-export`, then `nbdev-clean`. New notebooks are added to `nbs/sidebar.yml` by hand.
- **NFR-7** Monthly ledger (shared with Phase 20; whichever phase is built first does it, the other reuses it). Today `llm_budget.Budget.spent()` sums every entry ever written to the untracked ledger `results/multiagent/llm/spend.jsonl`: 491,301 entries, $233.18, all from before November 2026, written as `{"cost", "note"}` with no date. A $250 cap would then refuse C1 and A2. The change:
  - each new ledger entry carries `month`, the UTC `'YYYY-MM'`;
  - `spent()` counts only entries of the current month, and undated legacy entries count as earlier months;
  - `spentAll()` returns the all-time total, used in reports;
  - tests in `nbs/llm_budget.ipynb` cover a month boundary and legacy entries;
  - frozen plans record `cap=250.0` with `capNote='per calendar month (the user, 2026-11-09)'`.

## Acceptance criteria

- **AC-1** Regression: NFR-1, and the full suite passes.
- **AC-2** `dropShare`: the rules differ from the original by exactly the sentence and its leading space. The option is refused with `colony` or `confirm`. A `scaleB` cell without it has the same request key as Phase 14's.
- **AC-3** `slotLines`: a named slot's system text ends with its line; other slots' texts are unchanged.
- **AC-4** Targeted liars, on recorded and hand-built boards: no lie lands on a clue a failure guard holds. When a clue that a success guard holds and no failure guard holds is open, the lie lands on one. The lying cadence equals `ClueLiar`'s.
- **AC-5** Seating: the same team gives the same seating, guard identities and success pair in every arm. On boards 1-2 the guard identities sit in slots 4-7.
- **AC-6** Records, on hand-built boards:
  - the own-record line counts only the agent's own contests and the correct answers that followed;
  - the shared line has the team totals and no slot or identity;
  - the no-record arm has only the board line;
  - no record appears on boards 1-2;
  - boards 1-2 are identical requests in the three arms.
- **AC-7** Sequences: with the fake client, a 2-team, 3-arm run plays 6 waves. Boards 1-2 run one cell per team and are copied into each arm, so the fake client sees each of their requests once. A resume after board 4 repeats nothing.
- **AC-8** Plans: `A2_PLAN` is frozen and pushed before the pilot cell runs; the main stage refuses to run without the recorded pilot verdict and `A2_PLAN['approved']['main']`.
- **AC-9** Analysis: on `syntheticRows21`, the sign-flip test, Holm and the contrast recover known effects. Every `A2_PLAN` item is reported, the core measures of FR-C5 included, and the report states that cost without liars and damage won back are not measured. With `partial='stopped'` it reports P2, the manipulation check and "Gate A2 not read".
- **AC-10** Core measures: on a hand-built 6-board team, `dolIndex` over boards 3-6 and the persistence rule equal hand counts from the rows' `agents`, `pos` and per-slot columns, with the seating mapped to identities.

## Out of scope

- RL and 3B agents (Phase 19). Changing Phase 19's `Records.line` (P21-11) is Phase 19's task, not this phase's.
- The reworded prompt, Opus runs and the 16-agent drop-only cells (the capability plan's E3 and E4).
- Adaptive (Claude) liars, poisoned records, and records that persist across teams.
- Squads and bridges (C1), so contamination across squads.
- Clean boards, so cost without liars (P21-6; a recorded gap).
