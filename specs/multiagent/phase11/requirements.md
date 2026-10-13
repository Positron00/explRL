# Requirements: Phase 11, the clue board

Part of [README.md](README.md) (decisions K1-K11). Builds on Phase 10 and the follow-ups.

Terms used below.

- **Subtask**: a hidden integer `x` in `[0, R)`, a value, an appearance and an expiry time, and `m` clues.
- **Clue**: a fact "x mod p = r" about one subtask; held by the agents it was dealt to.
- **Known clue**: a clue an agent holds, or has seen through its channel (shared on the board, received in a message, or routed by the coordinator).
- **Determined**: an agent knows enough clues of a subtask to fix `x` in `[0, R)` (all `m`, or fewer when the known primes' product already reaches `R`).
- **Share**: the action of posting one known clue of one subtask to the channel; costs a turn.
- **Assisted solve**: a first correct answer by an agent that did not hold all clues of that subtask itself.
- **Share-to-use time**: for an assisted solve, the time from the first share of a clue the solver lacked to the solve (mean over such clues).
- **Pooled bound**: the welfare a team would reach if every agent knew every clue at once (the Phase 10 board's social optimum with solve rate 1).

## Functional requirements

### Part A: the board (`explRL/cluetask.py`, `explRL/clueboard.py`)
- **FR-A1** `makeClueTask(rng, m, R)` shall draw `m` distinct primes from a fixed list (2, 3, 5, 7, 11, 13) whose product is at least `R` and every `m - 1` of which multiply to at most `R / 2` (each clue is needed; missing one leaves at least two candidates), a hidden `x` in `[0, R)`, and the residues; it returns the clues and a checker (exactly one answer in range satisfies all clues). The feasible `(m, R)` pairs are `CLUE_PAIRS` = (2, 30), (2, 60), (3, 105), (3, 210), (4, 210).
- **FR-A2** `ClueBoardEnv(seed, nAgents, m, r, R, value, life, penalty, scheme, credit)` shall implement the world protocol as the Phase 10 board (time in turns, every action one turn, `2 nAgents + 2` subtasks open, expiry and replacement, first correct answer scores its value, later ones nothing, wrong answers cost `penalty`), deal each new subtask's clues per K2, and accept the actions `('open', k)`, `('submit', x)`, `('share', (k, j, r))` (clue `j` of open subtask `k` with posted residue `r`; whether the agent knows the clue is checked by the agent or adaptor, which sees the channel; the board flags a residue that differs from the truth as false) and `('wait', None)`.
- **FR-A3** The board shall keep the share log (time, agent, subtask, clue, residue, redundant = the same clue already shared by anyone, false = residue differs from the truth), the solve log (time, agent, subtask, assisted or not) and the submissions' candidate counts (`noteSubmit`, reported by the agent or adaptor, for counting guesses), the ledger in the Phase 6 format and `netRows` (net value per ledger row), and offer `pooledBound()` (per turn), `holders(k)`, and the reward schemes individual, team and credit (K8).

### Part B: channels and numpy agents (`explRL/clue_agents.py`)
- **FR-B1** Channels shall carry clues: `ClueBoard` (shared clues per subtask, visible to all, with author and time), `ClueMessages` (a share goes to `k = 2` random teammates' inboxes), `ClueLead` (routes each shared clue to every agent with that subtask open; suggests the open subtask with the most pooled clues not assigned to another agent). Each offers the per-agent view of known clues.
- **FR-B2** `RuleAgent(channel, rng, share, guess)` (numpy) shall: submit the answer of its open subtask when determined; else, if it has a channel, share a clue it holds that no one has shared yet (policy `share`: `'needed'` = only for subtasks a teammate has open, `'always'`, `'never'`; with no channel it never shares); else open the open subtask with the most known clues (ties: value, then random); else, with probability `guess`, submit a random candidate consistent with its known clues; else wait. `ClueLiar` shares, every other turn, a false residue for an open subtask it does not work on.
- **FR-B3** `clueSweep()` shall run the numpy agents over settings `(m, R)` in `CLUE_PAIRS`, `r` in {1, 2}, guess rate in {0, 0.2}, share policy in {needed, never}, at N {1, 2, 4, 8, 16, 32, 64} and all four channels, seeds 800-819, 40 turns per agent; `chooseClueSettings(rows)` shall implement the frozen rule: among settings where, at N = 4 with the `needed` policy, the blackboard's welfare is at most 0.8 of the pooled bound and the no-channel welfare at most half the blackboard's, the one with the largest blackboard-minus-none gap relative to the pooled bound (ties: smaller `R`, then smaller `m`); none qualifying stops the phase before any spend. The sweep also reports, descriptively, at N = 4 with the blackboard: team welfare with `needed` vs `never` sharing (does sharing pay the team), and under individual reward the mean reward of agents who shared at least once vs agents who never shared (does sharing cost the sharer).

### Part C: language-model agents (`explRL/clue_text.py`, `explRL/clue_runs.py`, `explRL/clue_grid.py`)
- **FR-C1** `TextClueEnv(board)` shall give the clue board the Phase 10 text interface (`rules`, `observe`, `parse`, `post`, `explored`, `summary`, `SCHEMA`, `task = 'clue'`, `unit = 'points'`): the rules explain clues, the remainder rule with a worked example, sharing and scoring; the observation lists the open subtasks (value, turns left, known clues out of `m`), the agent's held clues, the clues visible through its channel, and, for its open subtask, all known clues and the answer range. Anything unusable becomes `wait`, invalid; sharing a clue the agent does not know is invalid.
- **FR-C2** `runClue(cfg, seed, client)` and `runClueNumpy(cfg, seed)` shall run one board with LLM members (scripted liars in the first slots) or rule agents through `runTurns`, and return rows with: welfare per agent-turn, honest welfare, team totals and rates (follow-up Part C), solved, opens, wrong, guesses, shares, shares per held clue, redundant shares, assisted solves, share-to-use time, pooled-bound share, mean individual reward of sharers and non-sharers, and (LLM) the Phase 10 interface, token and cost columns. `cfg` is an `LLMConfig` with `task = 'clue'` and the board settings in `cfg.world`.
- **FR-C3** The grids (`cluePilotGrid`, `clueMainGrid`, `clueFramingGrid`, `clueLiarGrid`, optional `clueEffortGrid` and `clueScaleGrid`, `clueNumpyGrid` for the main cells, `clueQuick`) shall return cells as Phase 10 (`runner` `'llm'` or `'numpy'`), runnable by `runWorkload(..., run=runClueAny)`; `estimateGrid` shall price them (a provisional token profile for the clue task until the pilot measures it).
- **FR-C4** `CLUE_PLAN` (the analysis plan below as data, with the settings, models, prices and seeds) and `clueHash()` shall be frozen and committed before the main live runs.

### Part D: training packaging (`explRL/clue_train.py`)
- **FR-D1** `ClueEpisodes(batch, nAgents, settings, scheme, turns, seed, channel)` shall run a batch of boards with seeded episodes for rollouts: reset, per board the acting agent and its text observation, step with that agent's JSON reply, rewards per the scheme, done flags.
- **FR-D2** `exportTrajectories(log, path, format)` shall write per-agent JSONL (observation, action, reward, done) and a chat-format file (system, user, assistant turns per step) from a run's turn log; both round-trip.
- **FR-D3** `teacherAction(board, i, channel)` shall render `RuleAgent`'s choice as the JSON action the text interface parses, for supervised warm-starting.

### Report and demo
- **FR-E1** `explRL/clue_report.py` shall summarise welfare and team totals vs N per channel, the benefit over no channel, the information metrics, the framing and liar contrasts, numpy vs LLM (Spearman over the 12 channel x size cells with a bootstrap CI over seeds), and interface, token and cost totals, and write `report.md` with the plan hash and provenance, and figures.
- **FR-E2** `nbs/demo_clue.ipynb` shall run: a quick section (fake client, small numpy cells) in normal tests; the numpy sweep and `chooseClueSettings` with `--flags slow`; the live pilot and main grids with `--flags llm` and `EXPLRL_LLM_LIVE=1`, through `runWorkload`; outputs under `results/multiagent/clue/{quick,sweep,pilot,full}/`. Optional arms run only when their flag in the demo is set.

## Analysis plan (`CLUE_PLAN`, frozen before the main live runs; exploratory)

| Item | Definition |
|---|---|
| Main | Welfare per agent-turn and team total vs N per channel (Haiku, seeds 900-904) |
| Channel benefit | Per (channel, N): welfare minus the `none` cell, paired on seed, bootstrap CI |
| Information | Shares per held clue, redundant shares, assisted solves, share-to-use time per (channel, N) |
| Numpy vs LLM | Spearman's rho over the 12 (channel, N) cells between LLM and rule agents (`needed` policy, same seeds and settings), bootstrap CI over seeds |
| Framing | Blackboard, N 4 and 8, seeds 910-912: team framing minus own framing on shares per held clue and welfare, paired on seed |
| Liar | N = 4, seeds 900-902: honest welfare loss from one false-clue liar on the blackboard and with messages; its blackboard-minus-messages sign compared with H3 |
| Optional | Matched effort: (Sonnet minus Haiku) blackboard benefit at N = 4, effort medium; scale: blackboard and none at N = 16 |

## Quality requirements

- **NFR-1 Frozen results:** no earlier result changes; Phase 5-9 baselines identical; Phase 10 and follow-up reference outputs identical (cached reruns).
- **NFR-2 Offline by default:** normal tests and the quick demo need no network, package or key.
- **NFR-3 Cost:** live runs only through `runWorkload` with the $150 cap and its margins; the main scope about $6-8.
- **NFR-4 Reproducibility:** with the cache present, reruns are byte-identical and free.
- **NFR-5 Secrets:** as Phase 10.
- **NFR-6 Size, style:** each module under 200 lines; nbdev notebooks with tests.

## Acceptance criteria

Normal tests (offline):

- **AC-1 Regression:** NFR-1; the full suite passes with and without `anthropic`.
- **AC-2 Clues:** for every pair in `CLUE_PAIRS` and every feasible prime set, `makeClueTask` gives a unique answer in range satisfying all clues; any `m - 1` clues leave at least two candidates; the same seed gives the same tasks.
- **AC-3 Board:** dealing follows K2 (no agent holds all clues of a subtask when `r x m <= N x (m - 1)`; a solo agent holds all); false residues are flagged; shares are logged with redundancy; only the first correct answer scores; wrong answers pay the penalty; assisted solves and share-to-use times match hand-made cases; individual, team and credit rewards sum to the same team total.
- **AC-4 Channels and rule agents:** each channel delivers shared clues as specified (board to all, messages to two, coordinator to the openers); a rule team with the blackboard and `needed` sharing solves more than with no channel on a fixed seed; with no channel the rule agents never share; with a channel, `never` sharing gives the no-channel result.
- **AC-5 Text interface:** the observation lists held, visible and open-subtask clues; parsing maps the four actions; sharing an unknown clue and unusable replies become invalid waits; a fake-client team shares through each channel.
- **AC-6 Runs, grids, quick demo:** cell counts and call estimates per grid; the quick demo writes every artifact in under 30 s; outputs identical for 1 and 8 processes, pooled and grid by grid.
- **AC-7 Training package:** batched episodes are deterministic per seed; exports round-trip; the teacher solves every subtask it is given all clues for.

Checks on saved and live results:

- **AC-8 Sweep:** the numpy sweep runs (`--flags slow`), and `chooseClueSettings` returns settings (else the phase stops).
- **AC-9 Pilot:** Haiku solves at least 80% of the subtasks it opens when it holds all clues (the pilot's N = 1 cells), with under 5% invalid actions; token profile measured; `CLUE_PLAN` frozen and committed.
- **AC-10 Main:** every main-scope grid runs within the cap; cost, calls, retries and wall time recorded; findings reported, labelled exploratory; a cached rerun is byte-identical and free.

## Out of scope

- RL training of any model (the next phase, K10).
- Free-text messages, LLM coordinators or LLM liars (the liar is scripted), more than 16 LLM agents.
- Other clue types (logic grids and similar).
