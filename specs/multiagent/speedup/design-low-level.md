# Low-level design: faster live runs and follow-up experiments

Section numbers are referred to by [tasks.md](tasks.md). Phase 10 names (`LLMConfig`, `runLLM`, `taskMetrics`, `llmCell`, `estimateGrid`, `runAnyCell`, `rowKey`) are as in [../phase10/design-low-level.md](../phase10/design-low-level.md).

## 1. Budget split (`explRL/llm_budget.py`)

Moved unchanged from `llm_client`: `PRICES`, `TOKEN_PROFILE`, `USAGE`, `costOf`, `estimateCost`, `Budget`, `BudgetExceeded`. New:

```python
def maxCallCost(model, task, maxTokens, prices=PRICES, profile=TOKEN_PROFILE):
    "Dollars for one call that uses its whole output allowance (uncached and cache-read input from the profile)."
    i, r, _ = profile[(model, task)]
    p = prices[model]
    return (i * p['input'] + r * p['cacheRead'] + maxTokens * p['output']) / 1e6
```

`llm_client` imports `PRICES`, `USAGE`, `costOf`, `Budget`, `BudgetExceeded` from it; every notebook and module that imported these names from `llm_client` imports them from `llm_budget` (no re-exports).

## 2. Client changes (`explRL/llm_client.py`)

```python
class LLMClient:
    def __init__(self, ..., floor=0.0, timing=None):
        ...                       # floor: dollars that must stay unspent (FR-A4); timing: list to append call records to
        self.tag = ''             # the run's row key, set by runLLMCell (timing only; never part of a request)
    def complete(self, system, blocks, schema, task=''):
        t0 = time.perf_counter()
        ... cache hit -> record(cached=True) ...
        if self.budget is not None:
            self.budget.check(self.pending + self.floor)
        ... live call, budget.add(live cost), cache.put ...
        record(seconds=time.perf_counter() - t0, cached=False, retries=RetryCounter.take())
```

A timing record: `dict(key=self.tag, model, task, seconds, retries, cached)`; `LLMMember` passes `task=env.task`. `RetryCounter` (in this module, see section 3) supplies `retries`. `runLLMCell` sets `client.tag` to the first row key of the run and, after the run, writes `client.timing` to `logDir/timing/<row key>.jsonl` (sorted keys, one line per call). Records are appended to `self.timing` (a list) when given; nothing else changes, so requests and replies are as before. `self.calls` and `self.hits` stay (single-threaded event runs); in rounds the timing records are the per-call source of truth (H3).

## 3. Scheduling (`explRL/llm_sched.py`)

```python
def seqCalls(cell):
    "Sequential calls of one run: LLM agents x turns per agent x episodes, plus one belief call per agent per episode (foraging)."

def orderCells(cells, latency=None):
    """Longest expected duration first: seqCalls x seconds per call for (model, task); latency from a timing summary
    {(model, task): seconds} if given, else proportional to TOKEN_PROFILE output tokens; numpy runs last; ties by key."""

def checkWorkload(cells, budget, workers, prices=PRICES, profile=TOKEN_PROFILE):
    """-> (fits, need, left): need = sum of run estimates + workers x max run estimate + workers x max call cost;
    fits = need <= budget.remaining()."""

def runWorkload(grids, spec, workers, logDir, run=runAnyCell):
    """grids: [(name, cells)] in priority order. If spec is live and the workload does not fit (or with
    spec['pooled'] = False), run grid by grid as Phase 10 did; else one pool over orderCells(all cells) with
    chunksize = 1. Each LLM cell gets spec['floor'] = workers x max call cost, which `makeClient` passes to `LLMClient(floor=...)`. Returns
    dict(rows=sorted by rowKey, done=[grid names], refused=[row keys], stopped=reason or None)."""
```

A run refused by the budget inside the pool raises `BudgetExceeded` in its worker; `runWorkload` wraps `run` so that a refused cell returns no rows and its key is recorded in `refused` (the pool goes on; the floor keeps other runs inside the cap).

`RetryCounter` (defined in `llm_client`, used here only to install it): a `logging.Handler` attached to the `anthropic` logger (and its `_base_client` child) at INFO that counts records whose message starts with "Retrying request"; `take()` returns and resets the count for the calling thread. `mergeTiming(logDir, out)`: concatenates the per-run timing files (sorted by name) into `timing.jsonl`. `timingSummary(path)` -> `{'perModelTask': {(model, task): dict(calls, live, meanSeconds, p90Seconds)}, 'callsPerSecond', 'retries', 'wall'}`.

Settings: `LLM_WORKERS = 32` (decision SQ1) in `demo_llm` and `demo_followup`, used for live specs; fake and numpy workloads use `min(8, cpu)`.

`bench_grid.runGrid(cells, workers=None, run=runCell, chunksize=4)`: the only change is passing `chunksize` to `Pool.map`.

## 4. Team totals over time (`explRL/team_time.py`)

```python
def teamRates(L, net, period, tEnd):
    "Per complete period k ([k p, (k + 1) p) within tEnd): sum of net harvest of rows whose stay starts in it, / p."

def teamColumns(L, net, period, tEnd):
    "dict(teamWelfare=net.sum(), teamRate_0=..., teamRate_1=..., ...) (only complete periods)."

def marginalGain(rows, metric='teamWelfare'):
    "{(task or channel, N): (team total at N - at N/2) / (N/2)}, means over seeds."

def teamRateCell(cell):
    """Phase 8 main-grid or Phase 9 attack-grid cell: run its original runner (runHarness / runSafety), keep the row
    exactly as the original runner builds it, add teamColumns from the world's ledger (period = Tmove).
    Phase 8: world, hist, _, m = runHarness(...); row = benchMetrics(cell, world, hist, m, PREREG['delta']) (as runCell).
    Phase 9: world, _, _, row = runSafety(...); row.update(study, factor, level) (as runSafetyCell)."""
```

Foraging: `L = ledgerArrays(world.ledger)`, `net = netHarvest(world, L)`, period `world.Tmove` (40 s), start time `s0` for stays. Task board: `net` per ledger row comes from a new list `TaskBoardEnv.netRows` (appended in `apply` next to the ledger row: the value of a first-correct solve, `-penalty` for a wrong answer, else 0; independent of the reward scheme), period 10 turns, start time `t`. `taskMetrics` (`llm_runs`) and `runNumpy` (`llm_compare`) add `teamColumns`; `teamWelfare` equals `welfare x N x turns` (checked in tests).

FR-C2: `demo_llm` regenerates `full` from the cache with the new code; a check compares every column of the old file (kept as `full/runs_before_teamrate.csv`) with the new one, value by value, and records the new files' hashes in Phase 10 `RUN.md` as the AC-9 reference.

FR-C3: `teamRateGrids()` = Phase 8 `mainGrid('full')` cells and Phase 9 `attackGrid('full')` cells; run with `runGrid(cells, run=teamRateCell)`; written to `results/multiagent/bench/teamrate/runs.csv` and `results/multiagent/safety/teamrate/runs.csv`; a check compares every original column with `bench/full/runs.csv` (main study) and `safety/full/runs.csv` (attack grid) exactly.

## 5. Rounds (`explRL/rounds.py`)

Three phases per member event:

| Member | `prepare(world, t0)` | `decide(prep)` | `commit(world, t, dec)` |
|---|---|---|---|
| `LLMMember` | `env.observe(id, t0, channel)`, prompt blocks, system | `client.complete(...)` (the API call) | `env.parse`, `world.apply(id, action, t)`, `env.post`, notes, history line, turn record; returns `Outcome` |
| `CommBandit` (and `TerritoryBandit`, liars) | set `_world`, `_t = t0`; take messages; `obs = world.observe(id)`; `target = act(obs)` | identity | `world.apply(id, target, t)`, `learn(...)` (channel writes at `t`); returns `Outcome` like `PatchMember.event` |

`event(world, t)` of every member is equivalent to `commit(world, t, decide(prepare(world, t)))`, so event-driven runs are unchanged, and `runRounds(d=0)` reproduces them (AC-5). Note that a positive `d`, however small, still groups members with equal start times (all members start at `t0`), so only `d = 0` is the event-driven protocol.

```python
def runRounds(members, world, d, turns=None, Ttot=None, t0=0.0, threads=8):
    """Rounds of window d: the members whose next start time lies in [s, s + d), s the earliest pending start;
    prepare in agent order at s; decide concurrently (ThreadPoolExecutor(threads)); commit in (start, index) order at
    each member's own start time; reschedule each at start + dt. Stops a member after `turns` events or once its start
    reaches t0 + Ttot. With d = 0 a round holds only the earliest pending member (ties to the lower index), which is
    exactly the event-driven loop. Returns a TeamHistory like runTurns / runTeam."""
```

World time never goes backwards: commits are ordered by start time and all starts in a round are at or after `s`; observations use the world as advanced to `s` (`TextForagingEnv.observe(i, s, ...)` advances to `s`, not to the member's own start). Task board: every event lasts one turn, so with `d = 1` a round is one turn of the whole team.

## 6. Territories (`explRL/territory.py`, `llm_agent`, `llm_env`)

```python
def homeRanges(L, k):
    "k contiguous arcs of L // k locations covering 0 .. L-1 (the last arc takes the remainder)."

class TerritoryBandit(CommBandit):
    def __init__(self, channel, home, beta, **kw):    # home: set of locations
    def act(self, obs):
        """CommBandit's choice with beta added to home locations' scores; unknown home locations first, then unknown
        others; beta = inf restricts choices to home; beta = 0 gives CommBandit's choice exactly."""

def homeShare(L, homes):
    "Mean over agents of the share of an agent's stays inside its home range."
```

Squad of agent `i` with `k` squads and `N` agents: `s = i // (N // k)`; its home range `homeRanges(L, k)[s]`.

LLM agents: `LLMMember(..., home=None)`; when `home` is set, `system()` adds "Your squad's home range is the locations A, B, ... (an arc of the ring); prefer working there, but you may go anywhere." and `TextForagingEnv.home[i]` makes `observe` list home locations first in the travel line (the rest nearest first, as before). The cache keys of event-driven runs do not change (no home, same prompt).

## 7. Config and rows (`llm_runs`, `llm_compare`)

`LLMConfig` gains `protocol: str = 'events'`, `window: float = 0.0`, `squads: int = 0`, `beta: float = 0.0`. `runLLM` and `runNumpy` call `runTurns` for `'events'` and `runRounds(..., d=window)` for `'rounds'`; with `squads > 0` they build homes (`homeRanges`) and use `TerritoryBandit` (numpy) or `LLMMember(home=...)` (LLM). Rows gain the four fields (through `cellRow`), `homeShare` (when squads are used), `teamWelfare` and `teamRate_k`. Fixed-world-time numpy cells (B-numpy) use `Ttot` instead of turns: `LLMConfig.world['T']` sets it (600 s), and their row is built as in Phase 8 (`harnessMetrics` with `HarnessConfig(channel, budget='time', T, world)`, then `benchMetrics`), plus `teamColumns` and `homeShare`. In these rows `welfare` is the team total and `perAgentSecond` the per-agent measure (Phase 8 names), unlike Phase 10's per agent-turn `welfare`; they live in their own CSV (`followup/numpy/`) and reports label the measure explicitly.

## 8. Follow-up grids and plan (`explRL/followup_grid.py`)

| Grid | Cells | Calls | Cost (about) |
|---|---|---|---|
| `hardPilotGrid()` (study `hardPilot`, seeds 640-642) | board solo, difficulty {10, 12} x `maxTokens` {8000, 16000}, Haiku, effort low, 30 turns | 360 | $0.5 |
| `hardGrid(d, m)` (study `hard`, seeds 643-647) | board, {none, blackboard} x N {1, 4}, difficulty `d`, `maxTokens` `m`, 50 turns | 2 500 | $2-3 |
| `effortGrid()` (study `effort`, seeds 500-502) | board difficulty 8, {none, blackboard} x N {1, 4}, effort medium, `maxTokens` 8000, Haiku and Sonnet, 50 turns | 3 000 | $16-21 |
| `roundsNumpyGrid()` (study `roundsNumpy`, seeds 700-709) | foraging (5 s stays), blackboard, N {8, 16, 32, 64}, T = 600 s; arms: events, rounds (`d` 5), rounds + squads of 2 with `beta` {0, 0.25, 0.5, 1, 2, inf} | none | none |
| `roundsGrid(beta)` (study `rounds`, seeds 500-502) | foraging, blackboard, N 8, 50 turns, Haiku; arms: rounds (`d` 5), rounds + 4 squads at `beta` | 2 x 3 x 408 | $1-2 |
| `followupQuick()` | the first cell of each grid at 3 turns (numpy cells at T = 60 s, N 8), fake client | none | none |

`chooseHard(rows)` and `chooseBeta(rows)` implement the frozen rules (requirements FR-D2, FR-D5; `chooseBeta` considers `beta > 0` only); `chooseHard` returns `None` when no setting qualifies. The event-driven baseline for B-LLM is the Phase 10 main-grid foraging/blackboard/N 8 rows on seeds 500-502, read from `results/multiagent/llm/full/runs.csv` (no new call). `FOLLOWUP_PLAN` holds the requirements' analysis table as data, the rules, the seeds, models, settings and `PRICES`; `followupHash()` as `planHash`. `runFollowupCell(cell)` dispatches numpy round cells to `runNumpy` and LLM cells to `runLLMCell`.

## 9. Demos and reports

`demo_llm.run(mode, grids, spec, workers)` keeps its outputs and adds `timing.jsonl` and `metrics['timing']`, calling `runWorkload`. New `demo_followup`:

| Section | Flag | Content | Output |
|---|---|---|---|
| Quick | none | `followupQuick()` with the fake client, pooled and grid by grid, 1 and 8 processes (byte-identical); a tiny-cap check (AC-3) | `followup/quick/` |
| B-numpy | `slow` | `roundsNumpyGrid()`; `chooseBeta` printed | `followup/numpy/` |
| D1 pilot | `llm` | assert `FOLLOWUP_PLAN` frozen; `hardPilotGrid()` live at `LLM_WORKERS`; timing summary (the rate-limit probe); `chooseHard` (stops if `None`) | `followup/pilot/` |
| Main | `llm` | `hardGrid(chooseHard)`, `effortGrid()`, `roundsGrid(chooseBeta)` as one workload (priority D1, D2, B-LLM if it does not fit) | `followup/full/` |

`followup_report`: `summaries(rows, phase10Rows)` with the FOLLOWUP_PLAN contrasts; `writeReport` (provenance first: plan hash, commit, models, prices with date, cost of the runs, total spend, timing summary); figures `team_total.png`, `hard.png` (blackboard benefit at difficulty 8 vs the hard level), `effort.png` (size contrast at low vs medium effort), `rounds.png` (B-numpy per N and arm; B-LLM arms). `llm_report` adds team welfare and marginal gain next to per-agent welfare; `llm_figures.figTeamTotal`. `demo_multiagent` adds the team-total view (Phase 8-10: `team_total.png` for the Phase 8-9 reruns from `results/multiagent/{bench,safety}/teamrate/`, and Phase 10 from its regenerated rows) and a follow-up section to `REPORT.md`.

## 10. Determinism, cost and secrets

Requests depend only on seeds, prompts and settings, never on worker count, ordering or thread timing, so the cache makes every rerun exact (NFR-2, NFR-3). Live spend is bounded by the workload check and the per-call floor (FR-A4). Timing records carry no prompt text and no key; the quick demo scans every output for key-like strings, as in Phase 10.
