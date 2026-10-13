# Low-level design: Phase 11, the clue board

Section numbers are referred to by [tasks.md](tasks.md). Phase 10 and follow-up names (`LLMConfig`, `LLMMember`, `runTurns`, `llmStats`, `cellRow`, `makeClient`, `llmCell`, `runAnyCell`, `estimateGrid`, `runWorkload`, `teamColumns`, `rowKey`) are as in [../phase10/design-low-level.md](../phase10/design-low-level.md) and [../speedup/design-low-level.md](../speedup/design-low-level.md).

## 1. Clues (`explRL/cluetask.py`)

```python
PRIMES = (2, 3, 5, 7, 11, 13)

@dataclass
class ClueTask:
    primes: tuple      # m distinct primes
    x: int             # the hidden answer, 0 <= x < R
    R: int
    def clue(self, j): return (self.primes[j], self.x % self.primes[j])          # (p, r): "x mod p = r"
    def check(self, a): return isinstance(a, int) and not isinstance(a, bool) and 0 <= a < self.R and a == self.x
    def candidates(self, known):                                                  # known: {j: r}, possibly false
        return [y for y in range(self.R) if all(y % self.primes[j] == r for j, r in known.items())]

def primeSets(m, R): ...    # the m-subsets of PRIMES meeting both product conditions
def makeClueTask(rng, m, R):
    "m distinct primes with product >= R and every (m - 1)-subset product <= R / 2 (so each clue is needed and
    missing one leaves at least two candidates); x uniform in [0, R)."

CLUE_PAIRS = ((2, 30), (2, 60), (3, 105), (3, 210), (4, 210))      # the feasible (m, R) pairs with PRIMES
```

The prime set is drawn uniformly from the sets that satisfy both product conditions for `(m, R)` (`primeSets(m, R)`; `makeClueTask` raises if none exists). With `PRIMES` up to 13 the feasible pairs are (enumerated 2026-10-12): `(m, R) = (2, 30)`: 8 sets, for example {5, 7}; `(2, 60)`: 4, for example {7, 11}; `(3, 105)`: {3, 5, 7} only; `(3, 210)`: 4, for example {5, 7, 11}; `(4, 210)`: {2, 3, 5, 7} only. `CLUE_PAIRS` lists them; the tests check the conditions for every set (AC-2).

## 2. The board (`explRL/clueboard.py`)

`ClueBoardEnv(seed, nAgents, m=3, r=1, R=105, value=(1, 2, 3), life=30, penalty=0.5, scheme='individual', credit=0.5)`: time in turns; `2 nAgents + 2` subtasks open with staggered initial ages, each replaced at once when it expires or is solved (as `TaskBoardEnv`). On creation a subtask's clues are dealt: for clue `j`, `r` holders drawn without replacement from the agents, each time preferring the agents that hold the fewest clues of this subtask and never giving an agent its last missing clue while another choice exists (so no agent holds all `m` clues whenever `r x m <= N x (m - 1)`; with `N >= m` and `r = 1` each holder has one clue); with `N = 1`, agent 0 holds all.

| Action | Effect | Ledger row (Phase 6 format) |
|---|---|---|
| `('open', k)` | the agent works on `k` from its next turn | `travel`, location `k` |
| `('submit', a)` (on its open subtask) | first correct: value, closes `k`; later correct: 0; wrong: `-penalty` | `stay`, location `k`, harvest = value if first correct |
| `('share', (k, j, r))` | records the share of clue `j` of open subtask `k` with residue `r` (the agent or adaptor checks that the agent knows the clue, and posts it to the channel); logs whether it was redundant (the same clue already shared by anyone) and false (`r` differs from the truth) | `stay`, location `k`, no harvest |
| `('wait', None)` or invalid | nothing | `stay`, location -1 |

Logs: `shareLog` (t, agent, k, j, r, redundant, false), `solveLog` (t, agent, k, assisted = the solver did not hold all clues of `k`), `netRows` (value of a first-correct solve, `-penalty` for a wrong answer, else 0). `holders(k)` -> list per clue. `pooledBound()`: team value per turn with every clue known to all: at each new turn the board records the sum of the top `N` open values / 2 (open + submit, as Phase 10's `socialOptimum(1)`); `pooledBound()` is the mean of these over the run's turns.

Rewards (`scheme`): `individual` (value to the solver, `-penalty` to a wrong answer); `team` (each solve's value and each penalty shared equally); `credit` (the solver gets `(1 - c)` value; the agents whose true shares first supplied the clues of `k` that the solver did not hold split `c` value equally (false shares earn nothing); with no such shares the solver gets the full value). All three give the same team total per run (AC-3).

## 3. Channels and rule agents (`explRL/clue_agents.py`)

```python
class ClueBoard:                    # blackboard of clues
    def post(self, i, k, clue, t)   # clue = (j, p, r), true or false (liar)
    def view(self, i, t, board)     # {k: [(j, p, r, author, t)]} for open subtasks, newest first
class ClueMessages:                 # k = 2 random recipients per share, inbox per agent, received clues kept
    def __init__(self, n, k=2, rngs=None) ; def post(self, i, k, clue, t) ; def take(self, i)   # seeded rngs per sender
class ClueLead:                     # routes a shared clue to every agent with k open; suggests a subtask
    def post(self, i, k, clue, t, board) ; def take(self, i) ; def suggest(self, i, board)
def known(i, board, channel)        -> {k: {j: (p, r)}}   # held clues + clues seen through the channel
```

`known` takes the agent's held clues from the board and adds what the channel showed it (board view; kept messages; routed clues). A false clue from a liar is "known" like any other; a submitted answer inconsistent with it is simply wrong.

`candidates(task, knownClues)`: the `y` in `[0, R)` consistent with the known residues (computed from the clue values the agent knows, not from the hidden `x`).

`RuleAgent(PatchMember)` with `share in {'needed', 'always', 'never'}` and `guess` in [0, 1] (requirements FR-B2): each event, in order: (1) open subtask determined (one candidate) -> submit it; (2) if it has a channel and `share != 'never'`: a clue it holds of an open subtask that no one has shared yet (`needed`: some teammate has `k` open; `always`: any open subtask) -> share it (`('share', (k, j, r))` with the true residue; rule agents do not relay clues they have only seen, LLM agents may); (3) open the open subtask with most known clues (ties: higher value, then random); (4) with probability `guess`, submit a random candidate; (5) else wait. `ClueLiar(RuleAgent)`: on every other turn (its 1st, 3rd, ...) shares a false residue (a seeded wrong value) for a random open subtask other than its own; on the other turns acts as a `RuleAgent` with `share = 'never'`; never submits wrong on purpose.

## 4. Text interface (`explRL/clue_text.py`)

```python
CLUE_SCHEMA = {'type': 'object', 'additionalProperties': False,
               'required': ['action', 'target', 'answer', 'clue', 'notes'],
               'properties': {'action': {'type': 'string', 'enum': ['open', 'submit', 'share', 'wait']},
                              'target': {'type': 'string'},     # subtask name T<k> (open, share)
                              'answer': {'type': 'integer'},    # submit
                              'clue': {'type': 'string'},       # share: e.g. 'x mod 5 = 3' (must be a known clue of target)
                              'notes': {'type': 'string'}}}
```

`TextClueEnv(board)`: `task = 'clue'`, `timeUnit = 'turn'`, `unit = 'points'`, `SCHEMA = CLUE_SCHEMA`. `rules()` (above 512 tokens): the board, the clues, a worked Chinese-remainder example (`x mod 3 = 2`, `x mod 5 = 3`, `x mod 7 = 2`, `0 <= x < 105` -> 23, with the method: list the numbers below `R` with the largest prime's residue and test the others), sharing and its cost, scoring, the channels, the reply format. `observe(i, t, channel)`: turn, last reward; open subtasks (`T<k>`, value, turns left, known clues `a/m`); the agent's held clues; clues visible through the channel (board, received messages, routed clues; with author and age); the open subtask with all its known clues and `0 <= x < R`; the coordinator's suggestion. `parse`: `open`/`share` need a known open target; a share needs a clue string `x mod p = r` matching a clue the agent knows for it (held or seen), and becomes `('share', (k, j, r))`; `submit` needs an open subtask and an integer; otherwise `('wait', None)`, invalid. `post`: after a share, the clue goes to the channel (`ClueBoard.post`, `ClueMessages.post`, `ClueLead.post`). `explored`: opening a subtask no clue or suggestion pointed to. `summary`: one history line per turn.

## 5. Runs (`explRL/clue_runs.py`)

`LLMConfig` is reused with `task = 'clue'`; the board settings live in `cfg.world` (`m`, `r`, `R`, `value`, `life`, `penalty`) and default to `CLUE_SETTINGS` (section 6). `clueSetup(cfg, seed)` -> board, `TextClueEnv`, channel (`none` / `ClueBoard` / `ClueMessages(seeded)` / `ClueLead`). `runClue(cfg, seed, client)`: reserve the estimate; scripted `ClueLiar`s in the first `nLiar` slots; `LLMMember` for the rest (framing as Phase 10, `unit = 'points'`); `runTurns(members, board, T)`; row = `dict(episode=0, **clueMetrics(...), **llmStats(llm))`. `runClueNumpy(cfg, seed)`: the same with `RuleAgent(channel, rng, share=cfg.world.get('share', 'needed'), guess=cfg.world.get('guess', 0.0))`. `runClueAny(cell)`: clue cells (`cfg['task'] == 'clue'`) to `runLLMCell(cell, run=runClue)` (`llm_runs.runLLMCell` gained an optional `run` argument, default `runLLM`: it builds the client with `makeClient`, sets its tag, writes the turn log and timing as Phase 10) or `runClueNumpy` (with `cellRow`), others to `runAnyCell`. The fake client (`llm_fake.fakeReply`) gained a clue branch: on every third history step it shares one of the agent's own clues, so offline runs exercise sharing. `bench_grid.writeCSV` writes a tuple value (the board's `world.value`) as `1|2|3`.

`clueMetrics(cfg, board, hist, honest, T)`: `welfare` (net per agent-turn), `welfareHonest`, `teamColumns(L, netRows, 10, T)`, `solved`, `opens`, `wrong`, `guesses` (submissions made while the submitter's known clues left more than one candidate: `RuleAgent` and `TextClueEnv.parse` pass that count to the board with the submission, `board.noteSubmit(i, nCandidates)`, so the board can count them), `shares`, `sharePerHeld` (shares / clues held), `redundantShares`, `assisted` (share of solves that were assisted), `shareToUse` (mean), `pooledShare` (team net / (T x `pooledBound()`)), `sharerReward` and `nonSharerReward` (mean individual reward of the agents who shared at least once and of those who never did; nan when a group is empty).

## 6. Grids, settings and plan (`explRL/clue_grid.py`)

| Grid | Cells | Calls (about) | Cost (about) |
|---|---|---|---|
| `clueSweep()` (study `clueSweep`, seeds 800-819) | numpy: `(m, R)` in `CLUE_PAIRS` x `r` {1, 2} x guess {0, 0.2} x share {needed, never}, N {1, 2, 4, 8, 16, 32, 64}, 4 channels, 40 turns (5 x 2 x 2 x 2 x 7 x 4 x 20 = 22 400 runs; measured: 242 s on 8 processes) | none | none |
| `cluePilotGrid()` (study `cluePilot`, seeds 1100-1101) | N = 4, blackboard and none, 30 turns; plus N = 1 (all clues held) for the solve-rate check | about 500 | $0.2 |
| `clueMainGrid()` (study `clue`, seeds 900-904) | 4 channels x N {2, 4, 8}, 40 turns | 11 200 | $4-5 |
| `clueFramingGrid()` (study `clueFraming`, seeds 910-912) | blackboard, N {4, 8}, framing {own, team}, 40 turns | 2 880 | $1-2 |
| `clueLiarGrid()` (study `clueLiar`, seeds 900-902) | blackboard and messages, N = 4, one `ClueLiar`, 40 turns (clean cells: the main grid's) | 720 | $0.3 |
| `clueEffortGrid()` (optional; study `clueEffort`, seeds 900-902) | blackboard and none, N = 4, Haiku and Sonnet, effort medium | 1 920 | $6-8 |
| `clueScaleGrid()` (optional; study `clueScale`, seeds 920-922) | blackboard and none, N = 16, 40 turns | 3 840 | $1.5-2 |
| `clueNumpyGrid()` (study `clueNumpy`) | the main cells with rule agents (`needed`, guess as `CLUE_SETTINGS`) | none | none |
| `clueQuick()` | one cell of each grid at 3 turns (numpy at 10 turns), fake client | none | none |

`sweepIncentives(rows)`: the two descriptive checks of FR-B3 (team welfare with `needed` vs `never` sharing; mean individual reward of agents who shared at least once vs agents who never shared, from the row columns `sharerReward` and `nonSharerReward`). `chooseClueSettings(rows)`: the frozen rule of requirements FR-B3, applied to the sweep at N = 4 with the `needed` policy and guess as swept; returns `dict(m, r, R, guess)` or `None`. `CLUE_SETTINGS` holds the chosen values (with `value=(1, 2, 3)`, `life=30`, `penalty=0.5`, effort low, `maxTokens` 8000): from the T5 sweep (2026-10-12), `m = 2, r = 1, R = 30, guess = 0` (see the README). `CLUE_PLAN`: the requirements' analysis table as data, `CLUE_SETTINGS`, seeds, models, `PRICES`, `frozen`; `clueHash()` (12 hex digits). `TOKEN_PROFILE[(model, 'clue')]` provisional as the board's until the pilot.

## 7. Training package (`explRL/clue_train.py`)

```python
class ClueEpisodes:
    def __init__(self, batch, nAgents, settings=None, scheme='individual', turns=40, seed=0, channel='blackboard')
    def reset(self) -> list                           # per board: (agent, text observation) of its next turn, or None
    def step(self, replies) -> (next, rewards, done)  # replies: per board, the acting agent's JSON reply (dict) or None;
                                                      # rewards: per board (agent, r); done: per board
def exportTrajectories(log, path, format='jsonl', system='')   # 'jsonl': per-agent steps; 'chat': system / user / assistant
def readTrajectories(path) -> list
def teacherAction(board, i, channel, rng=None) -> dict          # RuleAgent's choice rendered as a CLUE_SCHEMA reply
```

`ClueEpisodes` runs `batch` independent boards (seeds `seed + b`) one event at a time in event order, returning whose turn it is with that agent's observation, so a policy can act for any agent (self-play with a shared policy). `exportTrajectories` reads a run's turn log (`turns.jsonl` lines) and writes per-agent JSONL (`obs`, `action`, `reward`, `done`) or chat format (`system` = the given system text, e.g. the rules; `user` = the logged observation; `assistant` = the response JSON; plus the reward and done flag); a round-trip test reads them back. `teacherAction` gives SFT targets.

## 8. Report and demo

`clue_report`: `summaries(rows, numpyRows)` (main table with welfare and team totals, channel benefit, information metrics, numpy vs LLM Spearman over 12 cells with bootstrap CI, framing and liar contrasts, optional arms, interface table); `writeReport` (provenance first: plan hash, commit, settings, models, prices, cost, total spend, timing); figures `clue_welfare.png` (welfare and team total vs N per channel), `clue_info.png` (shares per held clue, assisted solves, share-to-use time), `clue_numpy.png` (LLM vs rule-agent cell means), `clue_arms.png` (framing and liar).

`demo_clue.ipynb` (outputs under `results/multiagent/clue/{quick,sweep,pilot,full}/`): setup (as `demo_followup`: `run(mode, grids, spec, workers=None)` through `runWorkload(run=runClueAny)`, `LLM_WORKERS = 32`, shared cache and ledger); quick (fake client; outputs identical for 1 and 8 processes, pooled and grid by grid; key scan); sweep (`slow`: `clueSweep()`, `chooseClueSettings` printed); pilot (`llm`: assert settings chosen; pilot live; solve rate with all clues known, invalid rate, token profile printed); main (`llm`: assert `CLUE_PLAN` frozen; main, framing and liar grids as one workload, priority in that order; optional arms only if `OPTIONAL = True`; after a live run, `metrics.json` and `timing.jsonl` are copied to `*_live` before any cached rerun). The pilot's solve rate with all clues known is solved / opened over its N = 1 cells (AC-9).

## 9. Determinism, cost, secrets

Seeds fix tasks, dealing, message recipients, rule-agent and liar draws; the response cache fixes replies; rows are sorted by key within each grid. Cost and secrets as Phase 10 and the follow-ups.
