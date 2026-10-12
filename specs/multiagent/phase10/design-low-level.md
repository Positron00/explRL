# Low-level design: Phase 10, language-model agents (Claude API)

The pilot (task T7, 2026-10-12; results in the README) fixed the provisional settings before the analysis plan was committed.

## 1. Packaging

`pyproject.toml`: `[project.optional-dependencies] llm = ['anthropic']` (`pip install -e ".[llm]"`); `tst_flags = "notest slow sweeps llm llm_pilot"`. `explRL/__init__.py` imports nothing from Phase 10, and `llm_client` imports `anthropic` only inside `LLMClient.__init__`, so the package and all offline tests work without it (AC-1).

## 2. API client (`explRL/llm_client.py`)

```python
PRICES = {   # $ per million tokens; checked 2026-10-06 (claude-api reference); re-checked in T7 and T9
    'claude-haiku-5-5':  dict(input=0.10, output=0.50, cacheWrite=0.125, cacheRead=0.01, checked='2026-10-12'),  # prompts <= 100K
    'claude-sonnet-5-5': dict(input=2.00, output=10.00, cacheWrite=2.50, cacheRead=0.10, checked='2026-10-12'),  # reads 0.05x input
}
TOKEN_PROFILE = {(model, task): (uncached input, cache-read input, output) per call}   # measured in the pilot

class LLMClient:
    def __init__(self, model, effort='low', maxTokens=2000, cache=None, budget=None, prices=PRICES, client=None):
        if client is None:
            import anthropic                                   # optional extra
            client = anthropic.Anthropic(max_retries=6)        # credentials from the environment / SDK profile
        ...

    def reserve(self, estimate):
        "A run's expected cost, checked against what is left before its first live call."

    def request(self, system, blocks, schema):
        "The full request; also what the cache key hashes. No sampling parameters, no fallbacks."
        return dict(model=self.model, max_tokens=self.maxTokens,
                    system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
                    messages=[{'role': 'user', 'content': blocks}],          # last history block carries a breakpoint
                    output_config={'effort': self.effort, 'format': {'type': 'json_schema', 'schema': schema}})

    def complete(self, system, blocks, schema):
        req = self.request(system, blocks, schema)
        key = hashlib.sha256(json.dumps(req, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if (hit := self.cache.get(key)) is not None:
            return LLMReply(**hit, cached=True)                # nothing charged; `cost` stays the original call's
        self.budget.check(self.pending)                        # the run's reserved estimate, then the cap itself
        self.pending = 0.0
        resp = self.client.messages.create(**req)
        reply = LLMReply.fromResponse(resp, self.prices[self.model])
        self.cache.put(key, reply.asDict())
        self.budget.add(reply.cost)
        return reply
```

`LLMReply.fromResponse`: `stopReason = resp.stop_reason`; when it is `'refusal'`, `refusal = resp.stop_details.category` and `parsed = None`; when `'max_tokens'`, `parsed = None`; otherwise `parsed = json.loads(first text block)` (`None` on a decode error). `usage` keeps `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens` (thinking tokens are billed as output). `cost = sum(tokens x price) / 1e6`. A reply served from the cache keeps the cost of the call that produced it (so a rerun's rows are byte-identical) but is not charged to the budget; `cached` marks it for the caller only. `ResponseCache.put` stores a reply only if its key is absent (first writer wins, through a hard link) and returns the stored reply, which the live call then returns: two processes sending the same request at once both use one reply.

`ResponseCache(dir)`: one JSON file per key (`dir/ab/cdef....json`), written atomically (temporary file, then rename); stores the reply dict only (no headers, no credentials). Default `results/multiagent/llm/cache/` (gitignored).

`Budget(cap, ledger)`: spend is appended to `ledger` (`results/multiagent/llm/spend.jsonl`) under an exclusive `fcntl` lock, so parallel processes share one cap; `check(need)` raises `BudgetExceeded` when the total has reached the cap or `need` exceeds what is left; `remaining()` is what is left. `estimateCost(model, task, agents, turns)` = agents x turns x (uncached input x input price + cache-read input x cache-read price + output x output price), from the per-task, per-model `TOKEN_PROFILE` measured in the pilot (Haiku board 208 / 1 771 / 901, Haiku foraging 840 / 1 824 / 433, Sonnet board 214 / 1 743 / 805). `runLLM` reserves its estimate (`client.reserve`); the client checks it at the run's first live call, so a run whose estimate exceeds what is left is refused before it sends anything, while a fully cached rerun is never refused.

`FakeClient(script)`: same `messages.create` surface, returns scripted responses (`stop_reason`, text, refusal category, usage; `script` is a list or a function of the request), records the requests it received; used by every offline test and, with the deterministic `llm_runs.fakeReply` policy, by the quick demo.

## 3. Text foraging (`explRL/llm_env.py`) and the text board (`explRL/llm_board.py`)

`locationNames(L, seed)`: `L` distinct pronounceable names from a seeded syllable list (two syllables, capitalised), stable for a world seed.

Both text tasks are adaptors with one interface, so `LLMMember` does not depend on the task: `world` (the underlying world), `task`, `timeUnit`, `SCHEMA`, `unit` (the scoring word used by the framing sentences), `rules()`, `observe(i, t, channel)` (advances the world to `t`, renders the text and records which locations or subtasks the channel pointed to), `parse(parsed, i)`, `post(i, report, t, channel, info)` (sends a voluntary report to the channel), `explored(i, action, info)` and `summary(i, t, action, reward, report, info)` (the one-line history entry).

`TextForagingEnv(world, names)`: holds a `TeamPatchWorld` (default `benchWorld()`); `rules()` is the static text (task, scoring, the 64 names in ring order, danger and moving-patch rules, what each turn shows, an example and the reply format) that goes in the cached system prompt (above the 512-token minimum at a conservative 5 characters per token); `observe(i, t, channel)` renders:

```
Time 37.2 s. You are at Talo. Your last stay earned 0.42.
Travel times from Talo: Bemi 0.5 s, Cora 1.0 s, ... (all 64, nearest first)
Board (teammates' reports, mean reward per second, weight fades with age): Vesu 0.85 (weight 1.6); ...
```

with, instead of the board line, `Messages: agent 2 says Vesu 0.85 (12.0 s ago); ...` (messages received since the last turn) or `The coordinator suggests: Vesu.` (the Phase 7 `Lead`). Reports go to `Blackboard.write`, to `MessageBus.send` (2 random teammates, when `due`) or to `Lead.report`.

Schema (fixed for the task):

```python
FORAGE_SCHEMA = {'type': 'object', 'additionalProperties': False,
                 'required': ['action', 'target', 'reportLocation', 'reportValue', 'notes'],
                 'properties': {'action': {'type': 'string', 'enum': ['stay', 'go']},
                                'target': {'type': 'string'},          # a location name, '' for stay
                                'reportLocation': {'type': 'string'},  # '' for no report
                                'reportValue': {'type': 'number'},
                                'notes': {'type': 'string'}}}
```

`parse(parsed, i)` -> `(target index, report (location, value) or None, valid)`: names are case-insensitive; unknown names, a non-dict reply (schema failure, `max_tokens` stop, refusal) give "stay" and `valid = False`; a report with an unknown name or a non-finite value is dropped. `explored`: a move to a location no report or suggestion pointed to this turn (for `exploreShare`).

`TextBoardEnv(board)` (`llm_board.py`): the same interface on a `TaskBoardEnv`; the rules include a worked puzzle example and how `^` and `%` work; the observation lists the open subtasks with value and turns left, the agent's open subtask and its puzzle, and the latest claims on the claim board (`T5 working (agent 2, 3 turns ago)`), the messages received, or the coordinator's suggestion. `parse` gives `('open', k)`, `('submit', answer)` (only with a subtask open and an integer answer) or `('wait', None)`; anything unusable is "wait", invalid. Claims go to `ClaimBoard.post` or `MessageBus.send` (value 1 = working, 2 = solved); the coordinator takes no claims (it assigns from the board).

## 4. Task board (`explRL/taskboard.py`, `explRL/board_agents.py`)

`makePuzzle(rng, difficulty)`: draws `difficulty + 1` operations from `{+k, *k, ^k, %m}` with small constants, an answer range `[0, R)` with `R = 50 x 2^difficulty`, a hidden `x*` in the range, and `y = f(x*)`. Returns the text (`def f(x): return ((x * 7 + 3) ^ 21) % 97`, "find x in [0, 400) with f(x) == 42"), and a checker evaluating the same operations in Python (our code; model text is never executed). Any `x` in range with `f(x) == y` is correct.

`TaskBoardEnv(seed, nAgents, difficulty, value=(1, 2, 3), life=30, penalty=0.5, scheme='individual')`: world protocol with time in turns (every action takes 1); keeps `2 nAgents + 2` subtasks open, named `T<k>` (each with a value and an expiry `life` turns after it appears; the initial ones have staggered ages so expiries spread over the first `life` turns; a new one appears when one expires or is solved); actions:

| Action | Effect | Ledger row (Phase 6 format) |
|---|---|---|
| `open <task>` | shows the agent the subtask text from its next turn (switching cost) | `kind='travel'`, location = task |
| `submit <answer>` (on its open task) | first correct answer: reward = value, task closes; later correct: 0; wrong: -penalty | `kind='stay'`, `patch` = task, `harvest` = value if first correct |
| `wait` (or an unusable action) | nothing | `kind='stay'`, location -1 |

Rewards: `scheme='individual'` (default; value for a first correct answer, `-penalty` for a wrong one), `'team'` (each solve's value and each penalty shared equally across the team), `'difference'` (equal to individual, because only the first correct answer scores). References: `socialOptimum(solveRate)` = the expected team value per turn from putting agents on the highest-value distinct open tasks (two turns per attempt), an upper bound (`soShare` uses `solveRate = 1` on the end-of-run board); `netByAgent()` = value solved minus penalties paid, per agent (welfare, independent of the reward scheme); `firstSolves()` for discoveries; `duplicateTurns()` = turns spent opening or answering a subtask that another agent solved (the duplicate-work measure); `counts` = solved, wrong, late correct answers, opens (solve rate = solved / opens). `TaskBoardSim(seed, nAgents, solveRate, ...)`: the same board for numpy agents, where `('submit', None)` succeeds with the pilot's solve rate.

`board_agents.py`: `ClaimBoard` (blackboard for claims: latest `working` / `solved` claim per task with author and time; `view(i, t, open)` shows others' claims on open tasks, newest first); messages reuse `MessageBus` (period 1 turn) with the claim kind as the value; `BoardLead(n)` (numpy coordinator) suggests the highest-value open task not assigned to another agent; `BoardBandit(channel, rng)`: the numpy board agent, which submits on its open task until it closes and otherwise opens the highest-value open task with time left that no teammate has claimed (or the lead's suggestion), ties at random, posting `working` and `solved` claims.

Schema: `action` (`open` / `submit` / `wait`), `target` (task name), `answer` (integer), `claimTask` (task name or ''), `claimKind` (`none` / `working` / `solved`), `notes`.

## 5. Agents (`explRL/llm_agent.py`)

```python
class LLMMember(Member):
    extraNames = ('valid', 'cached', 'cost', 'explore', 'reported')

    def __init__(self, client, env, channel=None, memory='full', framing='own', lessons=''):
        ...
    def event(self, world, t):
        obs = self.env.observe(self.id, t, self.channel)               # text, includes channel contents
        blocks = self.history() + [{'type': 'text', 'text': 'Now:\n' + obs}]
        reply = self.client.complete(self.system(), blocks, self.env.SCHEMA)
        action, report, valid = self.env.parse(reply.parsed, self.id)
        reward, dt, loc, info = world.apply(self.id, action, t)
        self.env.post(self.id, report, t, self.channel, info)           # blackboard / messages / lead, if any
        ...                                                             # notes, history line, turn record
        return Outcome(dt, info['kind'], loc, reward, (valid, reply.cached, reply.cost, explore, report is not None))
```

The member runs for as many events as `runTurns` gives it (the turn budget lives in the loop, not the member). `system()` = `env.rules()` (which ends with the output instructions) + the framing sentence + the lessons (persistence arm); identical every turn, so it is cached. `history()`: `'full'`: one text block per past turn (compact: time, action, reward, own report, messages received), the first prefixed "Your past turns, oldest first:", with `cache_control` on the last; `'last8'`: the last 8 such blocks; `'notes'`: one block with the agent's latest `notes`. The turn log holds, per turn: agent, time, observation, response text, parsed action, valid, reward, report, explore, stop reason, refusal, usage, cost (no cache flag, so the log does not depend on the cache). Framing sentences (`{u}` is the task's unit, "food"): `own` "You are scored on the {u} you collect yourself." (control); `team` "You are scored on the team's total {u}, the sum over all teammates."; `credit` "You are scored on the {u} you collect yourself plus a share of the {u} others collect at locations you reported first."

`ScriptedLiarText(task, channel, rng)`: no API calls. Text foraging: the Phase 9 `Liar` itself (it forages as a numpy bandit on the same world and reports `-dangerCost` where it harvested and `c` elsewhere). Task board: `BoardLiar`, a `BoardBandit` that knows each answer and gets it right with probability `solveRate` (0.5), but after every turn claims `solved` on a random open task it has not solved, or `working` on one it did not open.

`elicitBeliefs(member)` (text foraging only): one request (the same system prompt and history, then the question) with the schema `{'estimates': [{'location': name, 'value': number}]}` (structured outputs need fixed property names); unknown names and non-numbers are dropped; returns the `{'mean', 'n'}` lists Phase 8's `beliefs` takes (`n = 1` where an estimate was given).

`runTurns(members, world, turns)`: the Phase 5 event queue (earliest start first, ties to the lower index; `Record`s in a `TeamHistory`) in which member `i` leaves the queue after `turns[i]` events (an int applies to all), so every agent makes exactly its turn budget.

## 6. Runs (`explRL/llm_runs.py`)

```python
@dataclass
class LLMConfig:
    task: str = 'forage'            # 'forage' | 'board'
    channel: str = 'none'
    N: int = 4
    turns: int = 50                 # per agent; or B / N in the equal-budget arm
    B: int = 0                      # equal-budget total agent-turns (0 = off)
    model: str = 'claude-haiku-5-5'
    effort: str = 'low'
    maxTokens: int = 8000           # pilot: 2000 cut off long puzzle reasoning
    memory: str = 'full'
    framing: str = 'own'
    nLiar: int = 0
    episodes: int = 1               # persistence arm
    lessons: bool = False
    difficulty: int = 2             # task board; the grids use SETTINGS['difficulty'] = 8 (pilot)
    world: dict = field(default_factory=dict)   # overrides for benchWorld / TaskBoardEnv; board 'solveRate' (numpy)
    # asDict / fromDict; turnsPerAgent() = B // N if B else turns
```

In the persistence arm, episode `e` of a run with seed `s` uses world seed `10 000 + 100 s + e` (as in Phase 8 study B); with `lessons`, each agent's system prompt in episode `e + 1` carries its last `notes` from episode `e` (no extra call).

`setup(cfg, seed, numpy=False)` builds the world (text foraging: `benchWorld(**cfg.world)` reset with `seed`, names `locationNames(64, seed)`; task board: `TaskBoardEnv(seed, ...)`, or `TaskBoardSim` for numpy), the text adaptor and the channel (Phase 7 `makeChannel` for foraging; `ClaimBoard` / `MessageBus` / `BoardLead` for the board). `runLLM(cfg, seed, client)` reserves the run's estimate, builds the team (scripted liars in the first slots, seeded from `seed + 3000`), runs `runTurns`, elicits beliefs (foraging), and returns one row per episode and the turn log. Row: `episode`, `welfare` (net of danger or penalties, per agent-turn), `welfareHonest`, `tEnd`, `soShare` (foraging: net harvest / (`tEnd` x Phase 6 social-optimum yield); board: net / (turns x `socialOptimum(1)`)); foraging: `rmrt`, `reached`, `ifdMean`, `discoveries`, `freeRiding`, `diversity`, `beliefError`; board: `solved`, `opens`, `wrong`, `duplicates` (`duplicateTurns`), `discoveries`; LLM: `invalid`, `refusals`, `maxTokenStops`, `reportShare`, `exploreShare` and `exploreSpread` (mean and standard deviation across agents of the share of an agent's turns spent moving to a location (or opening a subtask) that no report or suggestion pointed to), `calls`, token totals (`inputTokens`, `cacheWriteTokens`, `cacheReadTokens`, `outputTokens`), `cost`, `promptCacheRead` (share of input tokens read from the prompt cache). With 50 turns a foraging run spans only about 60-150 s of world time, under two 40 s move periods, so `rmrt` is mostly undefined (censored) and the numpy teams are still exploring; the pilot reports this (task T7).

`makeClient(cfg, spec)`: `spec['kind']` is `'fake'` (default: `FakeClient(fakeReply)`, a deterministic policy computed from the request text) or `'live'`, which needs `EXPLRL_LLM_LIVE=1` and a cap (else `RuntimeError`); optional `cache` dir and `ledger` (with `cap`). `runLLMCell(cell)` constructs the client in the worker process (one client per process), calls `runLLM`, prefixes each row with the cell keys and the flattened config (`cellRow`: `runner`, `budget` = `'equal'` or `'turns'`, `world.*` columns), and writes the turn log to `cell['logDir']/<row key>.jsonl` (one line per call, with the row key).

`llm_compare.py`: `runNumpy(cfg, seed)` runs the matching numpy team (`makeTeam`'s `CommBandit` / `LeadFollower` on the same foraging world, or `BoardBandit`s on `TaskBoardSim`; liars `Liar` / `BoardLiar`) through `runTurns` with the same turn budget, and returns the row columns that apply (beliefs from the bandits' estimates); `runNumpyCell` wraps it for `runGrid`. `compareNumpy(llmRows, numpyRows, metric='welfare')`: per task, the cell means over the (channel, N) cells both have (16 in the main grid); Spearman's rho (`rankAvg`: ranks with average ties, then Pearson; numpy only); 95% bootstrap CI resampling the shared seeds jointly (both sides use the same seeds and worlds).

## 7. Grids and analysis plan (`explRL/llm_grid.py`)

| Grid | Cells | LLM calls (about) |
|---|---|---|
| `pilotGrid(1)`, `pilotGrid(2, d)` (seeds 1000-1004, 1010) | stage 1: board solo, difficulty 1-4 x 5 seeds x 30 turns; forage solo and N = 4 blackboard (seed 1010, 30 turns); stage 2 at the chosen difficulty `d`: Haiku effort medium (5 seeds), Sonnet solo (3 seeds) | 750 + 240 |
| `mainGrid` (seeds 500-504) | 2 tasks x 4 channels x N (1, 2, 4, 8) x 50 turns | 30 000 + 300 belief calls (foraging) |
| `sonnetGrid` (seeds 500-502) | board x 4 channels x N (1, 4) x 50 turns, Sonnet 5.5 | 3 000 |
| `budgetGrid` (seeds 600-602) | forage x (none, blackboard) x N (1, 2, 4, 8) at B = 200 agent-turns | 4 800 |
| `framingGrid` (seeds 610-612) | forage x blackboard x N = 4 x framing (own, team, credit) | 1 800 |
| `memoryGrid` (seeds 610-612) | forage x blackboard x N = 4 x memory (last8, notes); `full` is the framing control | 1 200 |
| `persistGrid` (seeds 620-622) | forage x blackboard x N = 4 x 4 episodes x 25 turns x lessons (off, on) | 2 400 |
| `liarGrid` (seeds 630-632) | 2 tasks x (blackboard, messages) x N = 4 x (clean, 1 scripted liar) | 4 200 |
| `numpyGrid(task)` | the main-grid cells with `CommBandit` / `LeadFollower` (forage) or `TaskBoardSim` bandits (board), run by `runNumpyCell` | none |
| `quickGrid()` | the first seed of every grid above (all main cells at seed 500) and the numpy main cells at seed 500, at 3 turns (persistence: 2 episodes of 2 turns; equal budget: 3 N agent-turns), with `FakeClient` | none |

Calls in the table are turn calls; foraging runs add one belief call per LLM agent per episode (main 300, equal budget 90, liar 42, framing 36, memory 24, persistence 96). Cells are `dict(study, factor, level, N, seed, runner, cfg)` (`llmCell`); `level` names the task or arm level so that row keys are unique. `GRIDS` lists the main-run grids in priority order (main, Sonnet, budget, liar, framing, memory, persistence); `SETTINGS` holds the pilot's choices (effort low, `maxTokens` 8000, difficulty 8, the numpy board's solve rate 0.889, and the foraging world override `tStay = 5`), applied to every cell; `withClient(cells, spec, logDir)` attaches the client spec and the turn-log directory; `runAnyCell` dispatches to `runLLMCell` or `runNumpyCell`; `estimateGrid(cells)` gives turn calls, belief calls and expected cost per model.

`ANALYSIS_PLAN` (frozen in T7: `frozen=True` and the pilot's `SETTINGS`) holds the requirements' analysis table as data (seeds per grid, metrics, analyses), the models, the settings and the price table; `planHash()` (12 hex digits of its sha256) goes into every report. The main section of the demo refuses to run until the plan is frozen.

## 8. Cost estimate (before the pilot; superseded)

Assumed per call (to be replaced by the pilot's `TOKEN_PROFILE`): 3 000 input tokens of which about 2 000 are read from the prompt cache, and 300 output tokens (Haiku 5.5) or 500 (Sonnet 5.5), thinking included.

| Model | Calls | Per call | Total |
|---|---|---|---|
| Claude Haiku 5.5 | about 46 000 (all grids and the pilot) | 1 000 x $0.10 + 2 000 x $0.01 + 300 x $0.50, per million = about $0.00027 | about $13 |
| Claude Sonnet 5.5 | about 3 100 | 1 000 x $2 + 2 000 x $0.20 + 500 x $10, per million = about $0.0074 | about $23 |

After the pilot (measured token profile, `maxTokens` 8000, difficulty 8, 5 s stays) the main grids are estimated at about $43 (Haiku about $17, Sonnet about $26; `estimateGrid`), plus about $1.6 spent on the pilot. Before the pilot: about $36, or $50-70 with a factor-two margin for longer prompts and thinking; proposed cap $150 (decision L2). Wall time: about 3 s per call, sequential within an episode, 8 processes: about 5 hours for everything (rate limits permitting; the cache makes interrupted runs resumable).

## 9. Demo (`nbs/demo_llm.ipynb`)

| Section | Flag | Content | Output |
|---|---|---|---|
| Quick | none | every grid's quick cells with `FakeClient` (pipeline check) | `llm/quick/` |
| Pilot | `llm_pilot` | `pilotGrid(1)`, live; the difficulty with a solve rate (solved / opened) in 30-70%, closest to 50%, is chosen; then stages 1 and 2 (stage 1 from the cache); solve rates for effort medium and Sonnet, the token profile per (model, task), invalid-action and `max_tokens` rates printed | `llm/pilot/` |
| Main and arms | `llm` | main, Sonnet, budget, framing, memory, persistence, liar grids and `numpyGrid`, live | `llm/full/` |

Live sections check `EXPLRL_LLM_LIVE=1` first and skip otherwise; the cap ($150) is set in the demo and passed to every worker's `Budget`, with the shared ledger `llm/spend.jsonl` and cache `llm/cache/`. `run(mode, grids, spec)` runs the grids in order and stops at the first `BudgetExceeded`, recording which grids finished. `metrics.json`: mode, `ANALYSIS_PLAN` and its hash, git commit, models, effort, prices (with their date), cap, cost of these runs and total spend, calls and cache hits, wall time, grids done and where it stopped, the estimate per grid, and the summary tables. `turns.jsonl`: one line per call (row key, episode, agent, time, observation text, response text, parsed action, valid, reward, report, explore, stop reason, refusal, usage, cost). Cache hits are counted per mode (calls minus new ledger lines) and go to `metrics.json` only. The quick section also checks that it runs in under 30 s, writes every artifact, gives the same `runs.csv` with 1 worker and with `WORKERS` (up to 8), and contains no key-like strings.

Report (`llm_report.py`): `summaries(rows, numpyRows)` gives the main table, the harness benefit per model, the model-size contrast per channel (verdict "shrinks" if the CI lies below 0, "grows" if above, else "unclear"), `compareNumpy`, the equal-budget table, the arms (framing team / credit minus own, on welfare and `exploreShare`; memory last8 / notes minus full, where full is the framing `own` cell on the same seeds; persistence lessons minus none at episode 4; liar honest loss per task and channel, and its blackboard-minus-messages difference, H3's sign being > 0) and the interface table; `writeReport` puts the provenance first. Figures (`llm_figures.py`): `welfare.png`, `model_size.png`, `tokens.png`, `numpy_vs_llm.png`, `arms.png`.

## 10. Determinism, secrets and speed

Seeds fix the world, names, puzzles, liar and message recipients; the response cache fixes the model's replies; rows are sorted by key. A rerun with the cache present sends no request and writes byte-identical files (AC-9). The API key is resolved by the SDK from the environment; for live runs `loadEnvFile()` first copies missing variables from the git-ignored `.env.local` (mode 600) into the environment and reports only their names, and requests, cache entries, logs and results contain only prompts and replies; a test scans the quick run's outputs for key-like strings.
