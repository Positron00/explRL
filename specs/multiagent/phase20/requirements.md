# Requirements: Phase 20, squads with coupled work and bridges

Part of [README.md](README.md) (plan and decisions P20-1 to P20-17). It builds on these modules:

- `colony_board` (`ColonyBoardEnv`, `squadOf`, `dealSquads`, `squadView`, `SquadView`, `InSquad`, `stage4Members`) and `clueboard` (`ClueBoardEnv`, `_creditTo`, `_reward`);
- `clue_colony` (`tally`, `knownColony`, `colonyRules`, `SQUAD_RULE`, `GUARD_RULE`, `DECEIVER_RULE`, `checkOptions`) and `clue_text` (`TextClueEnv.observe`, `parse`);
- `clue_runs` (`clueSetup`) and `clue_roll` (`boardFactory`, `rollout`, `coopRows`, `runEval`, `evalModels`);
- `colony_grid` (`WORLD18`, `colonyCell`, `COLONY_SEEDS`, `PILOT_SEED`), `colony4` (`ARMS4`, `boardKind`), `colony64` (`stage64Grid`);
- `colony_mech` (`stage4Columns`, `runStage4Cell`, `reusedRows4`, `replayCheck`) and `colony_trace` (`replay`, `falseValues`, `contaminatedBy`);
- `colony_report` (`pairs`, `signFlipExact`, `bootSeeds`, `cellVals`), `fix_grid` (`cellCalls`, `fixEstimate`), `llm_budget` (`Budget`, `PRICES`);
- `coop_grid` (`evalCell`), `rl17_grid` (`teamSizeSuite`, `BIG_SEEDS`, `claim`) and `contest` / `contest_eval` (Phase 19, for the RL hooks and the per-board columns `contestColumns`, `misinformedFirst`, `uncorrected`, `sameWrong`, `contestsOf`);
- `rl19_measures` (`index`, `mean`, `ratio`, `lags`) and `rl19_spec` (`dolIndex`) from Phase 19, for the core measures.

## Terms

Terms are as in Phases 18-19 and the research plan. In addition:

- **Ring:** squad s's coupled subtasks need a clue held in squad (s + 1) mod n, where n = N // S is the number of squads. The 8 pairs (s, s + 1) at 64 agents in squads of 8 are the coupled pairs.
- **Coupled subtask:** a subtask of squad s whose clue 0 is dealt within s and whose clue 1 (the **cross clue**) is dealt to two agents of squad s + 1 (P20-1). Only squad s can open or answer it.
- **Mirror:** the coupled subtask's line on squad s + 1's board. Only the agents of s + 1 that hold the cross clue see the mirror line (P20-16); they can post the clue there and see each other's posts. Nobody can open or answer a mirror. Mirror posts are kept in their own log, not on squad s's board.
- **Bridge:** an honest agent of squad s that also reads s + 1's mirror lines for the pair, and may relay a value posted there onto s's coupled subtask (P20-2, P20-3). One per pair (`bridges=1`) or two (`bridges=2`).
- **Guarding bridge:** a bridge that is one of its squad's guards and keeps `GUARD_RULE` (`bridgeGuard=True`).
- **Relay:** a bridge's share, on squad s's coupled subtask, of a value posted on that subtask's mirror. It is logged with its source post (P20-4).
- **False relay:** a relay of a value that is not the clue's true residue.
- **Coupling cost:** `squads` − `coupled` in honest pooled share, on the same boards.
- **Win-back:** (`bridge1` − `coupled`) / (`squads` − `coupled`), a ratio of means over the shared boards.
- **Lead:** `squads` − `colonyGuards` at 64 agents in honest pooled share, per board (0.171 on seeds 1800-1807, per-board SD 0.023, measured from Stage 4 and the 64-agent run).
- **Cross-squad contamination:** the share of squad s's honest answers on coupled subtasks that agree with a false value relayed from s + 1 before them (so always wrong), over honest answers on coupled subtasks (as `colony_trace`'s outcome-based contamination, restricted to relayed values).
- **Clean board:** a board without liars (fault `clean`, `nLiar=0`): all 64 agents are honest Claude agents, and the 16 guards stay (P20-14).
- **Cost without liars:** the plan's core measure, the honest pooled share on clean boards. C1 reports it per arm, and as the paired contrasts `coupled` − `squads` and `bridge1` − `squads` on seeds 1800-1804; a negative contrast is a cost of coupling or bridges. Phase 19's `rl19_measures.cost0` has the same reference-minus-arm idea but is tied to Phase 19's test names, so C1 computes the contrasts with `colony_report.pairs(..., fault='clean', base='squads')`.
- **Honest pooled share, damage won back, made while misinformed, contamination:** as the research plan's Terms. Coupling and mirrors do not change the pooled bound, which uses only the board's open subtasks.

## Functional requirements

### Part A: the bridge board

- **FR-A1** `BridgeBoardEnv(ColonyBoardEnv)`, built only when a bridge key (`couple`, `bridges`, `bridgeGuard`) is set. It adds:
  - `couple=0.25`: every fourth subtask assigned to each squad is coupled (P20-1). The count is kept per squad, and no random draw is added to the board's streams. Clue 0 is dealt within s and clue 1 within s + 1, each to two slots, by `ColonyBoardEnv._pick` on `rngDeal`.
  - mirrors in squad s + 1's view of the board. A share by an agent of s + 1 on a mirror goes to `mirrorLog` (same tuple layout as `shareLog`), not to `shareLog`. Opening or answering a mirror is an invalid move.
  - `bridges` in {0, 1, 2} per pair and `bridgeGuard`. The bridge slots come from `dealBridges` (FR-A2). A bridge's share on a coupled subtask of a value in that subtask's `mirrorLog` is a relay, logged in `relayLog` with its source post.
  - Without a bridge key, nothing changes: `ColonyBoardEnv` and `ClueBoardEnv` boards, their deal streams and their outputs are unchanged.
- **FR-A2** `dealBridges(N, S, nLiar, guards, perPair, guarding)`: the bridge slots of each squad, in `squadOf`'s placement.
  - Ordinary bridges are the first `perPair` honest non-guard slots of each squad. Guarding bridges are the first guard slot of each squad.
  - Liars are the first nLiar slots (round-robin, uneven counts allowed, as `dealSquads`); guards are the next `guards`.
  - It raises `ValueError` if a squad has too few honest non-guard slots or guards. A1's 16 agents in squads of 4 with 6 liars leave some squads one such slot, which is enough for one bridge.
- **FR-A3** `BridgeView`: one agent's view of a bridge board.
  - The squad's open subtasks, as `SquadView`.
  - For the agents of squad s + 1 that hold a cross clue, the mirrors of s's coupled subtasks whose clue they hold (P20-16); other agents of s + 1 see no mirror line.
  - For a bridge, its pair's mirror lines: each coupled subtask's posted values with sender counts, from `mirrorLog` (P20-3).
  - `squadView(board, i)` returns it when the board has a `viewFor` method, so `TextClueEnv`, `InSquad` and scripted liars need no other change.
- **FR-A4** Scripted liars (`ClueLiar` through `InSquad`) in squad s + 1 count mirrors among their candidate subtasks, and on a mirror post a false residue of the cross clue (P20-5). Honest rule agents of squad s + 1 that hold a cross clue post it on its mirror when the mirror's leading value is missing, different from theirs or unconfirmed (`ColonyAgent`'s sharing rule, applied to mirrors; P22-12, the user, 2026-11-10). So honest posts reach the mirrors in the simulator, as Claude's do, and a `RuleBridge` relay is not always a lie. This is structure, not a fitted behaviour: B3's fitted and unfitted simulators and C3's imitation data all get it.
- **FR-A5** Relay credit for RL (P20-12). Under `scheme='credit'` or `'contest'`, when a solve's credited first true post of a clue is a relay, the credit share for that clue is split equally between the bridge and the first true poster of that clue on the mirror. `relaySource(board, share)` returns the source post, so `ContestLog` can treat a relayed liar's value as the liar's. Default schemes and every earlier board are unchanged.

### Part B: prompts, rule agents and rollouts

- **FR-B1** Rule text (P20-4), added by `colonyRules` only when a bridge key is set:
  - `COUPLE_RULE` for every agent of a coupled board;
  - `MIRROR_RULE` for the agents who see mirrors;
  - `BRIDGE_RULE` for bridges;
  - a guarding bridge gets `GUARD_RULE` and `BRIDGE_RULE`.

  No earlier rule string changes.
- **FR-B2** `TextClueEnv` with a bridge board:
  - `observe` adds the view's mirror lines and, for a bridge, its pair's mirror board, as at most 3 new lines that call `bridge_agents.bridgeLines`;
  - `parse` accepts a share on a mirror from an agent who holds its cross clue, and a relay from a bridge of any value posted on the mirror;
  - every other prompt and parse is unchanged.
- **FR-B3** `clueSetup` and `clue_roll.boardFactory` build `BridgeBoardEnv` when a bridge key is in the world, so Claude cells and 3B rollouts (training and evaluation) use the same board. `checkOptions` checks:
  - `couple` needs `squads`;
  - `bridges` needs `couple`;
  - `bridgeGuard` needs `bridges=1` and at least one guard per squad;
  - `dealBridges` must succeed.
- **FR-B4** `RuleBridge`, a numpy rule agent that relays the leading mirror value of a coupled subtask its squad has open, if no true-or-false value of that clue is on its board yet; otherwise it acts as its base rule agent. `bridgeMembers(world, members)` applies it and the bridge view, as `stage4Members` does. B3's fitted simulator uses it to model bridges in C1's forecast (P20-13), and C3 uses it later for imitation data.
- **FR-B5** Adaptive (Claude) liars (`fault='adaptive'`, `DECEIVER_RULE`) work on bridge boards and may post on mirrors, for C4 part b. They are covered by an offline test with the fake client; C1 itself runs scripted liars only.
- **FR-B6** Prompt length: `bridgePromptTokens(cfg, seeds)` reports the longest rendered prompt per role (bridge, mirror holder, other) for 3B rollouts. A1's speed check uses it against the 3,072-token window.

### Part C: grids, plans and runs

- **FR-C1** `ARMS20`: `ARMS4['squads']` plus `couple=0.25` and, per arm, `bridges` and `bridgeGuard`, as the README's table. `c1Grid()` returns the 38 new cells (study `colony20`, N 64):
  - with independent liars (23): `coupled`, `bridge2` and `bridgeGuard` on seeds 1800-1804, and `bridge1` on seeds 1800-1807;
  - clean (15, P20-14): `squads`, `coupled` and `bridge1` on seeds 1800-1804, no liars, 16 guards.

  `c1PilotGrid()` is the 3 pilot cells (P20-8), all with liars. `reusedCells20()` is the 16 reference cells, from `stage4Grid` and `stage64Grid`, all with liars. `colonyGuards` has no clean cell.
- **FR-C2** `c1Estimate(cells, perCall)` returns calls and cost per arm (`cellCalls`: 1,920 per liar board, 2,560 per clean board). `costRule20(projected)` reports the projection beside the expected ceiling ($35, P20-8 as updated with P20-14) and always waits for the user's approval; it never runs on its own (P20-8). The pilot's estimated cost is reported the same way before the pilot. `pilotCheck20(rows)` checks:
  - invalid replies under 5%;
  - mirror posts above 0;
  - relays above 0 on each bridge board;
  - a bridge's input tokens per call at most 2 × 780.

  It returns the verdict and the projection.
- **FR-C3** `C1_PILOT_PLAN`, frozen and committed before the pilot. It holds:
  - the arms, cells, seeds and reused cells;
  - H20-1 to H20-8 with tests, families and claim rules (P20-7, P20-14);
  - the pilot checks and the cost rule;
  - the cap, `cap=250.0` with `capNote='per calendar month (the user, 2026-11-09)'` (P20-9);
  - the plan hash (`coopHash`, as Stage 4).
- **FR-C4** `C1_PLAN`, frozen after the pilot and before the main run. It holds:
  - `C1_PILOT_PLAN`'s hash, unchanged in content;
  - the pilot's verdict and projection;
  - the forecast file and its SHA-256 (P20-13), from B3's fitted simulator refit on the pilot, with signs for 8 effects: H20-1 to H20-4, H20-5 on both measures, and H20-8's two clean contrasts (P22-8). `C1_PLAN` cannot be frozen without it.

  Nothing in the hypotheses or the gate may change between the two freezes.
- **FR-C5** The main run follows Stage 4's pattern:
  - the 38 new boards (23 with liars, 15 clean) play live, in one or two seed batches, with a stop only at 5% invalid replies or the cap;
  - the full grid, new and reused, then replays from the cache at $0 for the frozen analysis;
  - the reused rows gain C1's columns, and every earlier column must be unchanged (`reusedRows4`'s check).
- **FR-C6** Part b (P20-10): `squadEvalSuite(models)`, with the warm start and the final `r17mix` adapters as published (the user, 2026-11-09), per model, 32 agents in squads of 4 on Phase 17's plain board (`evalCell`'s settings with `cell['cfg']['world']['squads'] = 4` set after it builds the cell, since `evalCell` fixes `world` itself), seeds 900-909, clean and with 8 liars, 40 turns, levels `<model>|n32sq4` and `<model>|n32sq4liar`. `reusedPartB()` reads the one-board rows (`|n32`, `|n32liar`) from `eval_p17` and `eval_p17s0/warm.csv`, after a check that every configuration field but `squads` equals the new cells'.
- **FR-C7** The 3B bridge check (P20-11): `bridgeCheckCells()`, the warm start at 16 agents in A1's world (`rl19_suite.world19e` plus `couple=0.25`, `bridges=1`), in squads of 8 and of 4, seeds 900-904.
- **FR-C8** A section "Phase 20" in `nbs/colab_clue_rl.ipynb`: one cell, resumable and claim-aware (`evalModels` writes each model's rows as soon as it is done). It runs `squadEvalSuite` and `bridgeCheckCells` and packs `explRL_c1b.zip`.

### Part D: measures and analysis

- **FR-D1** `bridgeColumns(cfg, board, logs)`, the row columns of a bridge board, added to every C1 row by `runC1Cell` (as `colony_mech.runStage4Cell`, for the LLM and numpy runners alike; B3's forecast runs numpy cells through it). Names: `mirrorPosts`, `mirrorPostsPerHolder`, `mirrorFalse`, `bridgeRelays`, `relaysPerBridgeTurn`, `falseRelayShare`, `relayLag`, `relaysUsed`, `crossContamination` (not `relay`, which `traceBoard` already emits):
  - mirror posts, mirror posts per cross-clue holder, and their false share;
  - relays, relays per bridge turn, the false-relay share, relay lag (the source post's time to the relay's), and relays used in a correct answer;
  - coupled subtasks opened, solved, and their share of solves;
  - honest pooled share and raw honest welfare on coupled and uncoupled subtasks;
  - cross-squad contamination;
  - bridges' own opens and solves;
  - input tokens per call by role (bridge, mirror holder, other).

  Added to `coopRows` and to the Claude rows when the world has a bridge key (`isPhase20`).
- **FR-D2** `c1Summaries(rows, plan)` reports:
  - Gate C1, parts (i) and (ii), each on honest pooled share and on raw honest welfare;
  - H20-3 to H20-5 and H20-7 with estimates, bootstrap intervals and uncorrected sign-flip p;
  - H20-8, cost without liars (P20-14): each arm's honest pooled share and raw honest welfare on clean boards, and the contrasts `coupled` − `squads` and `bridge1` − `squads` over seeds 1800-1804, with bootstrap intervals and uncorrected one-sided sign-flip p (smallest 1/32); descriptive, outside Gate C1;
  - the inert-bridge flag;
  - each arm's honest pooled share, advantage over `colonyGuards`, the Phase 18 mechanism columns and the core measures (FR-D5).

  It refuses to report unless every planned cell, clean cells included, is present.
- **FR-D3** `partBSummaries(rows)`, per run: welfare gain over the warm start in squads of 4 and on one board, at 32 agents on clean boards, and their difference, with a sign-flip p over the 8 runs. Phase 17's 4-agent gain (+0.078) is shown beside it. Honest loss with liars is reported beside each. All descriptive (H20-6).
- **FR-D4** `writeC1`, `figC1` (`c1.png`: honest pooled share per arm, with the lead and the half-lead bar), and `demo_c1` with four modes: quick (fake client, synthetic rows), pilot, main and part b.
- **FR-D5** The plan's core measures, per arm, on boards with liars unless stated, reusing Phase 19's functions by name:
  - **per-board columns:** `contest_eval.contestColumns(cfg, rp.board, [rp.log])` on every C1 row, new and reused (from the cached replay; earlier columns unchanged). It gives `misinformedFirst`, `honestTurns`, `liarFirst`, `uncorrected`, `wrongHonest`, `sameWrong`, `liarPosts`, `contests`, `guardLies`, `contestLags` and the per-slot counts `agentTurns`, `agentShares`, `agentContests`, `agentSubmits`, `agentOpens`;
  - **pooled per arm** with `rl19_measures.index` and `ratio` (C1's levels are `<arm>|independent` and `<arm>|clean`, the `'<model>|<test>'` layout these functions read):
    - gullibility, `ratio(..., 'misinformedFirst', 'honestTurns')`, and suppression, `ratio(..., 'uncorrected', 'liarFirst')`;
    - verification: contests per lie, `ratio(..., 'contests', 'liarPosts')`; time to contest, the median of `rl19_measures.lags`; the share of lies on a guarded clue, `ratio(..., 'guardLies', 'liarPosts')`;
    - collaboration: `sharePerHeld`, as Phase 18;
    - error correlation, `ratio(..., 'sameWrong', 'wrongHonest')`;
  - **welfare per agent-turn** (`welfare`, `welfareHonest`) and **per 1,000 tokens** (as `welfarePerKTok` in `rl19_measures.runMeasures`, with the board's N in place of 16), and **tokens per solved task**: (`inputTokens` + `outputTokens`) / `solved`, per board, then the arm's mean; on boards with liars and on clean boards;
  - **cost without liars:** H20-8 (P20-14);
  - **division of labour:** Gorelick's index per board, `rl19_spec.dolIndex(rs, nLiar, positions=(0,))` on a one-board sequence (`pos` 0, `agents` the slot order), the arm's mean over boards; descriptive;
  - **contamination across squads:** FR-D1's cross-squad contamination;
  - **role persistence does not apply:** C1 plays single boards, not sequences.

  `contestColumns` reads `shareLog` only. On a bridge board a relayed false value is therefore the bridge's post, not a liar's, in these columns. Relayed lies are measured by FR-D1's relay and contamination columns instead.

## Quality requirements

- **NFR-1** Phase 5-19 reference outputs and configuration hashes are unchanged. Every earlier live board replays through the cache-only client with every saved column equal, and the cached reruns stay byte-identical (Stage 4's regression gate). Phase 19's tests pass.
- **NFR-2** Offline tests need no network, key or GPU. `torch` is used only in tests flagged `train`.
- **NFR-3** API spend goes through `llm_budget.Budget` on the shared ledger, under the cap of $250 per calendar month (P20-9), and only after the frozen plans and the user's approval of each estimate (P20-8). No paid call runs before T8.
- **NFR-4** Seeds are fixed, cached replies replay exactly, and two hosts never evaluate the same model (`claim`).
- **NFR-5** Each module stays under 200 lines. `clue_text` (193), `clue_roll` (195) and `colony_board` (190) take hooks of at most 3 lines each, `clueboard` (197) at most 2 (otherwise the weighted relay split overrides `_reward` in `BridgeBoardEnv`), and `colony_trace` (199) and `clue_agents` (199) none; the logic goes in new modules.
- **NFR-6** Every new notebook is added to `nbs/sidebar.yml`. After a notebook is created or edited, `nbdev-clean` runs, then `nbdev-export`.
- **NFR-7** Monthly ledger (shared with Phase 21; whichever phase is built first does it, the other reuses it). Today `llm_budget.Budget.spent()` sums every entry ever written to the untracked ledger `results/multiagent/llm/spend.jsonl`: 491,301 entries, $233.18, all from before November 2026, written as `{"cost", "note"}` with no date. A $250 cap would then refuse C1 and A2. The change:
  - each new ledger entry carries `month`, the UTC `'YYYY-MM'`;
  - `spent()` counts only entries of the current month, and undated legacy entries count as earlier months;
  - `spentAll()` returns the all-time total, used in reports;
  - tests in `nbs/llm_budget.ipynb` cover a month boundary and legacy entries;
  - frozen plans record `cap=250.0` with `capNote='per calendar month (the user, 2026-11-09)'`.

## Acceptance criteria

- **AC-1** Regression: NFR-1, and the full suite passes.
- **AC-2** Coupling, on a seeded 64-agent board in squads of 8:
  - exactly every fourth subtask per squad is coupled;
  - each coupled subtask's clue 0 holders are in s and its clue 1 holders in s + 1;
  - no agent holds both clues of a subtask;
  - the k-th subtask's value and clues equal the `squads` board's on the same seed. They come from the board's own stream, which coupling does not touch; only the deal differs.
- **AC-3** Isolation (P20-16: only holders of the cross clue see the mirror line): a mirror post, by a Claude agent or a numpy agent, never appears in squad s's `tally(channel, view)`, its `colonyLine` or `knownColony`, or its prompt. Squad s + 1 cannot open or answer a mirror (invalid). Agents of other squads never see the mirror.
- **AC-4** Bridges:
  - `dealBridges` places one or two honest non-guard bridges per squad, or one guard with `bridgeGuard`, and handles uneven liar counts;
  - a bridge's prompt shows its pair's mirror lines;
  - a relay of any posted mirror value is valid and logged with its source;
  - a non-bridge's attempt to post a mirror value it does not know is invalid, as today.
- **AC-5** Liars and mirror posts: a scripted liar of s + 1 (`MirrorLiar`) posts on mirrors in proportion to the mirrors' share of `open + mirrors`, and its values can be relayed; with no bridge key its draws equal `ClueLiar`'s. Honest rule holders post true cross clues on mirrors (P22-12).
- **AC-6** Relay credit: under `'credit'` the split of FR-A5 holds on a hand-built board; under `'individual'` rewards equal `ColonyBoardEnv`'s. `relaySource` returns the liar for a relayed lie.
- **AC-7** Rollouts: a 16-agent `rollout` with a fake policy in squads of 4 with one bridge per pair runs, logs relays and refuses no prompt. The adaptive-liar path builds on a bridge board with the fake client.
- **AC-8** Plans: `C1_PILOT_PLAN` is frozen before the pilot cell runs, and `C1_PLAN` (with the forecast's SHA-256) before the main cell runs. The cells assert both.
- **AC-9** Analysis: the gate, the margin, the secondary tests and the clean contrasts of H20-8 recover known effects on `syntheticRows20`. Every `C1_PLAN` item is reported, the core measures of FR-D5 included.
- **AC-10** Clean boards (P20-14): `c1Grid` has 15 clean cells (`squads`, `coupled`, `bridge1` × seeds 1800-1804) with `nLiar=0`, 64 Claude agents, 16 guards and, for `coupled` and `bridge1`, the same coupling and bridges as the liar cells; 2,560 calls per board; no clean `colonyGuards` cell and no clean pilot cell. `dealBridges` succeeds with 0 liars. The clean `squads` cell's configuration equals Stage 4's `squads` cell apart from the fault and `nLiar`.
- **AC-11** Core measures (FR-D5): on a hand-built board, `contestColumns`' counts, the pooled ratios and `dolIndex` on a one-board sequence equal hand counts, and `welfarePerKTok` and tokens per solved task equal their definitions.

## Out of scope

- Board choice and learned bridging (C3); trained or prompted adaptive liars as an arm (C4); A1's training in the bridged world (Phase 19's next step).
- Bridges at sizes other than 64 for Claude, and squads of 4 for Claude.
- Clean boards for `colonyGuards`, `bridge2` and `bridgeGuard`, and a clean pilot board (P20-14).
- Relays in both directions, or rings with more than one neighbour per squad.
- Labels on relayed values, and bridges that read the neighbour's full board (P20-3, P20-4 alternatives).
