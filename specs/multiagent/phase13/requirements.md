# Requirements: Phase 13, from diagnosis to fixes

Part of [README.md](README.md) (plan and decisions P13-1 to P13-6). Builds on Phase 11 (the clue board, its text interface and runs) and Phase 12 (rollouts, policies, the warm start, RL, evaluation).

Terms used below.

- **Failure:** a way a team falls short of a ceiling it could reach: information not pooled (ceiling: the pooled-information bound), damage from a liar (ceiling: the same team without the liar), the hidden-best option not chosen (ceiling: one agent with all the facts).
- **Fix:** a change that targets one failure. An **affordance** changes what agents can do or see (a new action, an observation line, a harness rule); an **instruction** changes only the wording of the rules (the prompt-only control).
- **Arm:** one condition of a part, named by a key: A1 `baseline`, `request` (option `ask`), `table`, `evidence` (hint); A2 `baseline`, `record`, `verify` (option `check`), `warn` (hint); A3 `baseline`, `factsFirst`, `table`, `dissent` (hint), each in the variants `classic` and `lone`.
- **Gap closed:** the mean paired difference (arm - baseline) divided by (ceiling - baseline mean), with a bootstrap CI over the pairing units: board seeds in A1 (ceiling: pooled share 1), episode seeds in A3 (arms share the tasks; ceiling: the solo agent's win rate).
- **Honest loss:** as Phase 11, `welfareHonest` on the clean board minus on the board with the liar (same seed, same arm); **loss recovered** = 1 - arm's mean honest loss / baseline's mean honest loss, with a bootstrap CI over board seeds.
- **Track record:** of a sender's earlier shares for subtasks now solved, how many were true (a solved subtask's clues are known to be true or false).
- **Training-only penalty:** an extra cost per wrong answer in the RL training reward; the board, its welfare and every evaluation row keep the 0.5 penalty.
- **Turn-level advantage:** for each text turn, the agent's reward-to-go from that turn minus the group's mean reward-to-go for the same slot and turn index, divided by the group's standard deviation there.
- Phase 12 terms (policy, slot, notes and full memory, warm start, group, solo solve) as in [../phase12/requirements.md](../phase12/requirements.md).

## Functional requirements

### Part A: affordances and instructions on the clue board (Track A, A1-A2)
- **FR-A1** `TextClueEnv(..., ask=False, table=False, record=False, check=False)`. Each option adds its action or observation lines and its sentence in the rules; with all four off, rules, schema, observations and rows are unchanged (Phase 11 and 12 cached reruns byte-identical).
- **FR-A2** `ask` (request board): a new action `'ask'` (target = the subtask the agent has open; any other target is invalid) takes the turn and posts a request (subtask, agent, turn) to the blackboard, replacing the agent's earlier request; a request lapses when its subtask closes (solved or expired) or its agent opens another subtask. Every agent sees `Requests: agent 2 needs clues for T3 (you hold 1); ...`, the count being the clues of that subtask the viewer holds or has seen and the requester lacks. On the board, an ask is a wait (the board, its welfare and its logs are unchanged); asks are counted in the turn logs.
- **FR-A3** `table` (fact table): the blackboard line lists, per open subtask, each distinct shared clue once, without sender or age (`Known to the team: T3: x mod 7 = 4, x mod 5 = 2; ...`), instead of one entry per post.
- **FR-A4** `record` (reputation): every shared clue on the blackboard shows its sender's track record (`agent 1, 2 turns ago, record 3/4 true`); senders with no checked shares show `record none`.
- **FR-A5** `check` (costly verification): a new action `'check'` (target = an open subtask, clue = a posted clue text) takes the turn; the next observation says `Your check: T3 x mod 7 = 4 (from agent 1) is true` or `is false`. A clue the agent found false is left out of its known clues from then on (its candidate count and its open subtask's clue line), and one it found true is kept against later posts; other agents' views are unchanged. On the board a check is a wait.
- **FR-A6** Instructions: `HINTS['evidence']` ("post every clue you hold for an open subtask before working on your own") and `HINTS['warn']` ("a teammate may share false clues; cross-check before relying on one"), through the existing `hint` option.
- **FR-A7** The options travel in `cfg.world` (as Phase 12's), through `clueSetup`, `runClue` and `rollout`. Rows keep their columns (a new action is a wait on the board); `fixLogMetrics` counts `asks`, `checks`, `checkedFalse` and the invalid tries of each new action (`askInvalid`, `checkInvalid`) per row key from the turn logs, as Phase 12's `logMetrics` did for Track A. An ask posts a report, so Phase 11's `reportShare` column also counts asks in the `request` arm (the arm's mechanism uses `asks` and the board's `sharePerHeld` instead).
- **FR-A8** The request schema comes from the environment: `TextClueEnv.SCHEMA` adds `'ask'` and `'check'` to the action enum only when those options are on (Phase 11 requests unchanged); `LLMMember` already sends `env.SCHEMA`; `claudePolicy(client, workers=8, schema=CLUE_SCHEMA, task='clue')` takes the schema and task, set by whoever builds it (a rollout with `ask` or `check` builds it with that environment's `SCHEMA`; policies keep taking batches of (system, blocks)).

### Part B: the hidden-profile vote (Track A, A3)
- **FR-B1** `profileTask(seed, variant='classic', domain=None, N=4, shared=(1, 1, 3), unique=2)`: N agents, two options with template facts in one of three domains (hiring, investment, property); a fact is a sentence with a sign (+1 for, -1 against) and an option. Facts held by every agent favour option B; facts held by one agent each favour A, so that with every fact counted A has the higher total and with the shared facts alone B does. `variant='lone'` (lone dissenter) adds one fact, held by one agent, that rules B out. Option names, which option is best and fact order are shuffled per seed.
- **FR-B2** `ProfileEnv(task, rounds=3, rule='free'|'factsFirst', table=False, hint=None)` (`hint='dissent'` adds the dissent sentence): in each round every agent sees its own facts (with ids), the shared board (each post with its sender; or, with `table`, the deduplicated list of facts posted so far) and replies JSON `{kind: 'fact'|'opinion', fact: id, text, notes}`; a fact post publishes the fact's own text (agents cannot misquote facts); an opinion posts up to 300 characters. With `rule='factsFirst'`, round 1 accepts fact posts only (an opinion is rejected as invalid and posts nothing). After the last round each agent votes privately for one of the two option names (`{vote: name, notes}`). Success: the option with the higher full-fact total wins a strict majority.
- **FR-B3** `soloCeiling`: one agent with every fact votes after reading them (no rounds); its success rate is the ceiling.
- **FR-B4** `runProfile(cells, client, logDir=None)` reserves the estimated cost on the client, runs episodes in batches through `claudePolicy` (each round's requests concurrent), returns one row per episode (`success`, votes, posts, facts posted per held fact, invalid replies, calls, cost) keyed with `cellRow`, and writes turn logs as Phase 11.

- **FR-B5** (replication, added 2026-10-16) `hbTask(item, seed, N=4)`, `HBEnv`, `hbSolo` play HiddenBench's 65 tasks (vendored unchanged with their licence) through `runProfile` when a cell's world has `bench='hiddenbench'` and `item`; cells without it are unchanged.

### Part C: grids and plans (Track A)
- **FR-C1** `fixGrid()` (study `fixA`): A1 arms (`baseline`, `request`, `table`, `evidence`) on the blackboard at N {4, 8}, and A2 arms (`baseline`, `record`, `verify`, `warn`) on the blackboard at N 4 with one liar (`nLiar=1`, Phase 11's `ClueLiar` in slot 0) and without, seeds 900-909, 40 turns, Haiku, Phase 11 settings. Baseline cells equal to Phase 11 cells reuse their cached replies.
- **FR-C2** `profileGrid()` (study `profileA`): `baseline`, `factsFirst`, `table`, `dissent` x variants `classic`, `lone`, 100 episodes each (episode seeds 5000-5099, shared by the arms), plus the solo ceiling on the same seeds, Haiku.
- **FR-C3** Pilot grids for both (a few cells each, the solo ceiling included) to check invalid rates, the vote's baseline win rate and the solo ceiling before `FIX_PLAN` is frozen.

### Part D: RL that beats imitation (Track B)
- **FR-D1** `RLConfig` gains `advantage='board'|'turn'`, `wrongPenalty=0.0` (training-only extra cost per wrong answer) and `haltJump=None` (the one-step invalid threshold of FR-D4). `configHash` leaves out fields at these defaults, so every Phase 12 hash is unchanged and a Phase 12 configuration with another `trainSeed` is the credit control.
- **FR-D2** `trainingReturns` subtracts `wrongPenalty` per wrong answer of the slot (from the board's submit log, so the turn logs keep their fields), alongside the format penalty.
- **FR-D3** `turnAdvantages(ro, penalty, wrongPenalty)` returns per board, slot and text turn the turn-level advantage (reward-to-go over the slot's delivered rewards from that turn on, including credit delivered later; zero where the group's values are equal); `stepSamples` takes per-turn advantages when `advantage='turn'`.
- **FR-D4** Roll-back on a one-step jump: with `haltJump` set, the LoRA weights and optimizer state before each update are kept until the next step's rollouts; if those have an invalid share above `haltJump`, the update is undone, the learning rate halved, the rollouts discarded and the step redone; two roll-backs in a row halt the run. Logged per step (`rolledBack`).
- **FR-D5** `RL13_PLAN` (in `coop_grid`, beside `RL_PLAN`, so Track B does not wait for Track A's code) lists the arms (`credit` seed 2; `indpen` and `credturn` seeds 1 and 2; seed 1 = `trainSeed` 0, seed 2 = `trainSeed` 1), their settings (Phase 12 v2 otherwise: `wrongPenalty` 2.5 and `haltJump` 0.15 in the two new arms, `advantage='turn'` in `credturn`), the evaluation and the best-arm rule; frozen before the runs. The Colab notebook takes `ARM` and `SEED` at the top and writes `runs_p13/<arm>_s<seed>/`.
- **FR-D6** Evaluation: `evalSuite`'s cells without cross-play for all five new adapters on Colab (`evalModels`); cross-play on the Mac for both seeds of the best arm (the highest mean RL gain on the main boards); the Phase 12 warm-start and v2 rows reused; `rl_report` gains per-arm means over seeds and per-seed RL gains.

### Part E: report
- **FR-E1** `fix_report`: per part, the gap closed (or loss recovered) per arm with bootstrap CIs, paired on board seed (A1, A2) or episode seed (A3); each arm's cost without the failure (A2: welfare with no liar against baseline with no liar); mechanism columns (asks, checks, checked-false, shares per held clue, facts posted per held fact).
- **FR-E2** `demo_fix.ipynb` (Track A: quick with the fake client, pilot and main with `--flags llm`); Track B in `colab_clue_rl.ipynb` and `demo_rl.ipynb`; a section in `REPORT.md` from `demo_multiagent`.

## Analysis plans (frozen before the main runs; directions pre-registered, exploratory)

`FIX_PLAN` (Track A):

| Item | Definition |
|---|---|
| A1 primary | `request` and `table`: pooled-share gap closed vs `baseline`, N 4 and 8, paired on seed; Holm over the 4 tests (H13-1) |
| A1 control | `evidence` (instruction) the same way |
| A2 primary | `record` and `verify`: loss recovered vs `baseline`, N 4, paired on seed; Holm over the 2 tests (H13-2) |
| A2 control and cost | `warn` the same way; each arm's no-liar welfare minus baseline's no-liar welfare |
| A3 primary | `factsFirst` and `table`: gap closed in win rate vs `baseline`, both variants, paired on episode seed; Holm over the 4 tests (H13-3) |
| A3 control | `dissent` (instruction) the same way |
| Mechanism | asks, checks, checked-false (from turn logs); shares per held clue; private facts posted per private fact held; votes against the hidden-best |

`RL13_PLAN` (Track B):

| Item | Definition |
|---|---|
| Main | Phase 12's main boards (N = 4, blackboard, 15 seeds): welfare and pooled share per adapter |
| RL gain | Each adapter minus the warm start, paired on board seed; per arm, the mean over its seeds (H13-5: the arm's CI above 0 and both seeds' means above 0) |
| Seed spread | credit control: Phase 12 v2 (seed 1) and seed 2 |
| Mechanism (H13-4) | `indpen`, both seeds: shares per held clue (within 0.1 of the warm start) and solo share (under 0.2) |
| Generalisation, liar | As `RL_PLAN` v2, for all five new adapters |
| Cross-play | As `RL_PLAN` v2, for both seeds of the best arm (highest mean RL gain on the main boards) |

## Quality requirements

- **NFR-1 Frozen results:** Phase 5-9 baselines identical; Phase 10, follow-up, Phase 11 and Phase 12 cached reruns byte-identical; Phase 12 RL configuration hashes unchanged.
- **NFR-2 Offline by default:** normal tests need no network, key, `anthropic`, `torch` or GPU; live API sections behind `llm`, model runs behind `train` and `gpu`.
- **NFR-3 Cost:** API spend through the Phase 10 client under the $150 API cap ($47.22 spent); Track A estimated at about $10 (about 41 000 new Haiku calls: main runs about 39 000, pilots about 2 300; `fixEstimate`), with margin for the vote's provisional token profile; GPU under the $150 GPU cap ($27 spent), Track B estimated at about 17 GPU hours.
- **NFR-4 Reproducibility:** fixed seeds; replies cached; evaluation and Track A reruns byte-identical.
- **NFR-5 Secrets and data:** as Phase 12 (no key on Colab; Claude's outputs never used for training).
- **NFR-6 Size, style:** each module under 200 lines; nbdev notebooks with tests.

## Acceptance criteria

Normal tests (offline):

- **AC-1 Regression:** NFR-1; the full suite passes with and without `anthropic` and without `torch`.
- **AC-2 Clue-board options:** defaults unchanged (schema, rules, observation, rows); the schema gains `ask` and `check` only with their options; `ask` is valid only for the asker's open subtask, posts, shows and lapses requests as specified and is a wait on the board; `table` lists each distinct clue once; `record` counts true and false shares of solved subtasks only; `check` reports the truth of a posted clue next turn, drops a false clue from the checker's known clues and keeps a true one; `fixLogMetrics` counts asks and checks from logs; the hints add their sentences.
- **AC-3 Hidden profile:** for 1 000 seeds, the shared facts alone favour B and all facts favour A; `lone` adds one fact that rules B out; a scripted team that posts every fact and votes by total always succeeds, one that posts nothing never does (classic variant); `factsFirst` rejects round-1 opinions; the fact table deduplicates; votes and posts parse; option names and order vary with the seed.
- **AC-3b HiddenBench adapter:** every task converts with the correct option marked and each agent holding all shared facts plus its own hidden one, verbatim; option and fact order vary with the seed; the environment states every option and keeps the ungrouped table; the runner plays HiddenBench cells with the fake client and reruns them identically; the grids have the planned sizes with seeds shared across arms.
- **AC-4 RL logic:** `turnAdvantages` on hand-made rewards (equal groups -> 0; a late credit counts toward the sharing turn's reward-to-go); `wrongPenalty` only in training returns; Phase 12 configuration hashes unchanged; roll-back on a jump with stubs.
- **AC-5 Report:** gap closed, loss recovered and their CIs on synthetic rows with known effects.

Checks on runs:

- **AC-6 Pilots:** invalid replies under 5% for every new action and the vote; the vote's baseline win rate between 0.2 and 0.8 and its solo ceiling at least 0.8 (else the fact counts change, before freezing); `FIX_PLAN` frozen and committed before the main runs.
- **AC-7 Track A:** main runs within the cap; a cached rerun byte-identical and free; every `FIX_PLAN` item reported.
- **AC-8 Track B:** `RL13_PLAN` frozen and committed before the runs; five runs (or the stopping rule's halts, reported); GPU hours recorded; evaluation cached rerun byte-identical; every `RL13_PLAN` item reported.

## Out of scope

- Training Claude; using Claude's outputs as training data.
- Changing the clue board's scoring or settings (the penalty change is training-only).
- Collusion, conflicting goals and conformity experiments (the red team's other failures), beyond what the vote's posts and votes show.
- LLM liars (the liar stays scripted); a Sonnet check beyond the best arm per part (P13-2).
- Training the local model on the hidden-profile vote.
