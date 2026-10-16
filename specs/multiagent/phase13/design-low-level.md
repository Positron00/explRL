# Low-level design: Phase 13, from diagnosis to fixes

Section numbers are referred to from [tasks.md](tasks.md).

## 1. Clue-board options (`clue_agents`, `clue_text`, `clue_fix`)

```python
class ClueBoard:                    # changed: requests and track records
    def ask(self, i, k, t)          # request (k, i, t), k = agent i's open subtask; a new ask replaces the agent's last
    def requests(self, board)       # [(k, i, t)] still live: k open and board.opened[i] == k
# clue_fix.trackRecord(a, board)  # (true, checked) over agent a's shares (board.shareLog) of subtasks solved so far

def known(i, board, channel, checked=None)   # checked: {(k, j, r): true?} of agent i; None = Phase 11 behaviour
```

`known` with `checked`: after the Phase 11 merge (later sightings overwrite earlier, own clues win), a seen clue `(k, j, r)` the agent found false is removed (falling back to the latest other value seen for `(k, j)` it has not found false), and a clue it found true replaces whatever was seen for `(k, j)`; own clues still win.

`TextClueEnv(board, hint=None, showOpen=False, ask=False, table=False, record=False, check=False)`:

| Option | Rules sentence (added after the channel paragraph) | Observation | Parsing |
|---|---|---|---|
| `ask` | "'ask' for the clues you lack on the subtask you have open (target = it): your request shows on the board to every teammate until you open another subtask or it closes; asking takes your turn." | `Requests: agent 2 needs clues for T3 (you hold 1); ...` (or `none`); the count: clues of T3 the viewer holds or has seen that the requester does not know | `ask` whose target is the agent's open subtask (still open) -> board action `('wait', None)`, report `('ask', k)` posted with `ClueBoard.ask`; any other target invalid |
| `table` | "The board lists each clue known to the team once per subtask." | `Known to the team: T3: x mod 7 = 4, x mod 5 = 2; ...` replaces `Clues shared on the board: ...` | none |
| `record` | "Each shared clue shows how many of its sender's earlier shares were true, counted over subtasks solved so far." | each board entry gains `, record 3/4 true` (or `, record none`) | none |
| `check` | "'check' a clue on the board (target = its subtask, clue = its text): next turn you learn whether it is true; checking takes your turn." | `Your check: T3 x mod 7 = 4 (from agent 1) is true.` in the turn after a check | `check` with an open target and a clue text equal to one posted for it -> `('wait', None)`, the result stored in the agent's `checked` (the sender shown is the clue's first poster) |

- Schema: `self.SCHEMA` is `CLUE_SCHEMA` unless `ask` or `check` is on; then a copy whose action enum adds them (Phase 11 requests, and so cached replies, unchanged). `LLMMember` sends `env.SCHEMA`; a `claudePolicy` for a rollout with these options is built with `schema=env.SCHEMA`.
- `HINTS['evidence']` = "Before working on your own subtask, post every clue you hold for an open subtask that has not been posted yet." `HINTS['warn']` = "A teammate may share false clues. Cross-check a shared clue before relying on it, for example against the answer range."
- The table's middle three columns live in `clue_fix` (`fixRules`, `fixBoard`, `fixLines`, `fixParse`; `clue_text` would pass 200 lines), called from `TextClueEnv`. `ask` and `check` are valid only on the blackboard (with another channel they are invalid waits); a request lapses once its asker has opened anything since asking (so re-opening the same subtask does not revive it); with `table` and `record` both on, `table` wins (its entries have no sender). With `ask` or `check` on, the reply-format sentence lists the new actions, and the turn summary reads `asked for clues for T3` or `checked T3: ...` instead of `waited`.
- Rows are unchanged. `fixLogMetrics(records)` (in `fix_report`) counts per row key `asks` (valid asks), `checks` and `checkedFalse` (checks that found a false clue) from the turn logs' parsed actions and the check lines of the next observation.

## 2. The hidden-profile vote (`hidden_profile`, `profile_runs`)

```python
DOMAINS = dict(hiring=..., investment=..., property=...)   # per domain: option names, >= 12 positive and >= 6 negative templates
def profileTask(seed, variant='classic', domain=None, N=4, shared=(1, 1, 3), unique=2) -> dict
class ProfileEnv:
    def __init__(self, task, rounds=3, rule='free', table=False, hint=None)
    def rules(self) -> str
    def observe(self, i, r) -> str      # own facts with ids, the board (or table), round r of R
    def post(self, i, parsed) -> bool   # valid?
    def voteText(self, i) -> str
    def vote(self, i, parsed) -> int | None
    def success(self, votes) -> bool    # strict majority for the hidden-best option
def soloCeiling(task) -> str            # the one-agent prompt with every fact
def runProfile(cells, client, logDir=None) -> list[dict]
```

**The task.** Options 0 and 1 get shuffled names and a shuffled order; the hidden-best (A) is option 0 or 1 by seed. `shared = (aPos, aNeg, bPos)`: facts every agent holds, in favour of A (aPos), against A (aNeg), and in favour of B (bPos). `unique`: per agent, that many facts in favour of A held by that agent only. Defaults: shared A +1 -1, B +3; unique 2 per agent, so the full totals are A +8, B +3, the shared facts alone A 0, B +3, and each agent alone A +2, B +3 (each agent prefers B until the private facts are pooled). `variant='lone'` gives one random agent a fact that rules B out ("... was found to have falsified ..."). Sentences come from the domain's templates without repeats; the pilot may change `shared` and `unique` (AC-6) before `FIX_PLAN` is frozen.

**Rounds.** In each of `rounds` rounds, every agent's request is sent at once (one batch); posts are applied in agent order after the round (so no agent sees a same-round post). Reply schema `{kind: 'fact' | 'opinion', fact: 'F2', text: str, notes: str}`; a fact post must name one of the agent's own fact ids and publishes that fact's sentence; an opinion posts `text[:300]`; with `rule='factsFirst'`, an opinion in round 1 is invalid. `hint='dissent'` adds to the rules: "If you hold information the others seem to lack, say so before the vote." Invalid replies post nothing. The board shows each post with its sender and round; with `table`, the deduplicated facts posted so far, grouped by option, without senders (opinions are still listed below).

**Vote.** After the last round, each agent's vote request (its facts, the board, schema `{vote: '<name 1>' | '<name 2>', notes}`) is sent at once; success = strictly more than N/2 votes for A. The solo ceiling sends one request with every fact and the vote schema.

**Implementation choices.** Fact ids are per agent (F1..Fk in the agent's own shuffled order, so ids do not reveal what others hold); notes carry over between rounds and into the vote (notes memory); `endRound()` applies a round's queued posts in agent order; in `lone` the rule-out fact counts -1 for B, is flagged `ruleOut` and is private; the domain templates (13 positive, 6 negative each) live in the data-only `profile_domains`. Cells come from `profileCell(study, arm, variant, seed, ...)`: `cfg['world'] = dict(arm, variant, rule, table, solo, [hint])`, arm `solo` the ceiling. `estimateCost(model, 'profile', N, rounds + 1)` uses a provisional token profile (700 in, 300 out per call) that the pilot measures. The fake client answers the post and vote schemas deterministically (existing schemas unchanged).

**Rows.** Per episode: `study`, `level` (`<arm>|<variant>`, or `solo|<variant>`), `seed`, `domain`, `success`, `votesA`, `factsPosted`, `factsHeld`, `uniquePosted` (private facts posted / private facts held), `opinions`, `invalid`, `calls`, `cost`, `latency` (sequential request stages, rounds + 1, not wall-clock, so reruns stay byte-identical); keyed with `cellRow`. Turn logs as Phase 11 (prompt, reply, parsed, valid, per agent and round).

`claudePolicy(client, workers=8, schema=CLUE_SCHEMA, task='clue')`: the vote passes its schemas and `task='profile'` (cache key and ledger task); defaults unchanged.

## 3. Grids and plans (`fix_grid`)

```python
def fixGrid() -> list[dict]          # study 'fixA'
def fixPilotGrid() -> list[dict]
def profileGrid() -> list[dict]      # study 'profileA'
def profilePilotGrid() -> list[dict]
FIX_PLAN = dict(version=1, frozen=False, ...)      # the items of the requirements' FIX_PLAN; arms; seeds; profile settings; prices; Holm families

# in coop_grid, beside RL_PLAN:
RL13_PLAN = dict(version=1, frozen=False, ...)     # arms, seeds, settings (RL_PLAN v2 overridden), evaluation, best-arm rule
```

| Part | Cells | Calls (Haiku) |
|---|---|---|
| A1 | 4 arms x N {4, 8} x seeds 900-909 (baseline seeds 900-904 replay Phase 11's cached replies) | about 17 000 new |
| A2 | 4 arms x {liar, no liar} x N 4 x seeds 900-909 (baseline cells Phase 11 has replay its cache) | about 10 000 new |
| A3 | 4 arms x 2 variants x 100 episodes x 16 calls; solo 2 x 100 | about 13 000 |
| Pilots | A1-A2: each new arm, N 4, seeds 900-901 (A2 arms with the liar); A3: `baseline` and `factsFirst`, 20 episodes each, and the solo ceiling on the same 20 | about 3 000 |

Seeds of the vote are 5000 + episode, the same for every arm and the solo ceiling (paired); the cost estimate goes through `estimateCost` and the client reserves it before each run, as Phase 11.

`RL13_PLAN` arms (each overrides `RL_PLAN['rl']`):

| Arm | `scheme` | `advantage` | `wrongPenalty` | `haltJump` | `trainSeed` |
|---|---|---|---|---|---|
| `credit` | credit | board | 0 | none | 1 (seed 2; seed 1 is Phase 12's v2 run, `trainSeed` 0, reused) |
| `indpen` | individual | board | 2.5 (total 3, P13-4) | 0.15 | 0 (seed 1), 1 (seed 2) |
| `credturn` | credit | turn | 2.5 | 0.15 | 0 (seed 1), 1 (seed 2) |

## 4. RL changes (`clue_rl`, `rl_control`, `rl_torch`)

```python
def trainingReturns(ro, penalty, wrongPenalty=0.0)      # also minus wrongPenalty per wrong answer (from ro.boards[b].submits: agent, turn, result 'wrong')
def turnRewards(ro, penalty, wrongPenalty=0.0)          # per board, slot: the list of per-turn rewards (delivered reward, minus the penalties)
def turnAdvantages(ro, penalty, wrongPenalty=0.0)       # per board, slot, turn: (G_t - mean_g G_t) / (std_g G_t + 1e-6), 0 where std = 0
```

`G_t` is the sum of the slot's per-turn rewards from turn t to the end, plus the board's pending credit for the slot at the end (as `rollout`'s returns). Groups are the G rollouts of one seed; turn indices align because every slot has the same number of text turns (`turns` per agent). `stepSamples(ro, adv, ...)` takes per-turn advantages when `adv` is per turn (a list per board and slot) and per-slot ones as before.

Wrong answers come from each board's `submits` log (time, agent, subtask, candidates, result), matched to the slot's text turn by its time, so the turn logs keep their fields (Phase 12 logs byte-identical).

**Roll-back (FR-D4).** In `rl_control.jumpGuard(play, jumped, undo, rolls)`, used by `trainRL`. With `haltJump`: before each update `prev = snapshot(model, opt)` (the P12-10 snapshot); after the next step's rollouts, if their invalid share is above `haltJump`, `restore(prev)`, `lr *= 0.5`, discard the rollouts and redo the step with the same seeds; two roll-backs in a row (at the redone step, or at the next step after a step that rolled back) write `halted.json` (reason starting `jump:`); the final adapter is the restored one. The metrics line gains `rolledBack` only with `haltJump` set. The snapshot is held in memory only: after a disconnect right after a roll-back, the resume starts from the last checkpoint.

**Hash.** `configHash` (and `config.json`, through `runFields`) drops `advantage`, `wrongPenalty` and `haltJump` when they equal their defaults (`'board'`, `0.0`, `None`), so Phase 12 hashes are unchanged (tested against the saved `config.json` hashes).

## 5. Report (`fix_report`, `rl_report`)

- `fixSummaries(rows, p11rows, logMetrics)`: per part and arm, the gap closed (A1: pooled share; A3: win rate against the solo ceiling) or loss recovered (A2, from `welfareHonest`) with bootstrap CIs over the pairing units (A1, A2: board seeds; A3: episode seeds, which arms share), Holm p-values within each primary family, the controls, each A2 arm's no-liar cost, the mechanism columns.
- `writeFix(path, S, meta)`: tables per part, labelled exploratory, with the plan hash and commit; `figFix(out, S)`: gap closed per arm with CIs, one panel per part (affordances in one colour, instructions in another).
- `rl_report`: `rlSummaries` groups adapters `<arm>_s<seed>` (`armSeed`; Phase 12's `credit` relabelled `credit_s1` with `renameModel`) by arm, and `bestArm(S)` applies `RL13_PLAN`'s rule: per-arm mean of the per-seed RL gains (CI from the pooled paired differences) and each seed's own gain.

## 6. Notebooks and outputs

| Notebook | Sections | Outputs |
|---|---|---|
| `demo_fix` | quick (normal tests): `fixQuick` and `profileQuick` with the fake client (which asks and checks when the schema allows), identical at 1 and 8 processes; pilot (`llm`): invalid rates per arm and new action, the vote's baseline win rate and solo ceiling against the AC-6 bands; main (`llm`, asserts `FIX_PLAN` frozen); cached rerun (`llm`: byte-identical, ledger unchanged) | `results/multiagent/fix/{quick,pilot,full}/`, `results/multiagent/profile/{quick,pilot,full}/` |
| `colab_clue_rl` | Phase 13 RL section: `ARM`, `SEED` at the top, asserts `RL13_PLAN` frozen, resumes; evaluation of all five new adapters (no cross-play) | Drive `explRL_rl/runs_p13/<arm>_s<seed>/`, `eval_p13/` |
| `demo_rl` | Phase 13 evaluation: reads Colab's `eval_p13`, picks the best arm by `RL13_PLAN`'s rule, runs cross-play for both its seeds on the Mac (reusing Phase 12's `credit` cross-play rows as `credit_s1`), report; skips when Colab's files are absent | `results/multiagent/rl/eval_p13/` |
| `demo_multiagent` | section 10 (Phase 13) | `REPORT.md`, `report/fix.png` |

## 7. Determinism, cost, secrets

As Phase 12: board, vote and sampling seeds fixed; Claude's replies cached (a rerun is byte-identical and free); the API cap and ledger of Phase 10; no key on Colab; Claude's outputs never used for training.
