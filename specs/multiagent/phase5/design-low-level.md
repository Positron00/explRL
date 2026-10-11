# Low-level design: Phase 5, shared multi-agent interface

## 1. Records and history (`explRL/multi.py`)

```python
class Record(NamedTuple):
    agent: int        # agent index
    t: object         # event start, in the team's time unit (int for 'sample', float for 's')
    dt: object        # event duration, same unit, > 0
    kind: str         # 'fixation' | 'saccade' (flexible), 'event' (pre-structured), 'iteration' (circuit), 'step' (default)
    location: object  # where the reward was earned: the location at the end of the event
    reward: float
    extras: tuple     # the member's native row, in the order of member.extraNames

class Outcome(NamedTuple):   # what member.event returns; runTeam adds agent and t
    dt: object
    kind: str
    location: object
    reward: float
    extras: tuple = ()
```

`TeamHistory(extraNames)`, where `extraNames` is a list with one tuple of names per agent:
- `add(record)`; `records` (list, in run order); `__len__`.
- `forAgent(i) -> list[Record]`.
- `toJSONL(path)`: one line per record, `json.dumps({'agent', 't', 'dt', 'kind', 'location', 'reward', 'extras': dict(zip(names, extras))})`. Values pass through `_plain(x)`: numpy scalars via `.item()`, numpy arrays via `.tolist()`, everything else unchanged.

`spawnRngs(seed, n) -> list[np.random.Generator]`: `[np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(n)]`.

## 2. Event queue (`Clock`)

```python
class Clock:
    def __init__(self, n, Ttot, t0=0):
        self.tEnd = t0 + Ttot                 # same expression as train_circuit: t0 + Ttot
        self.heap = [(t0, i) for i in range(n)]
        heapq.heapify(self.heap)

    def peek(self):
        "Index of the next member to run, or None. Members whose start time is not below tEnd are dropped."
        while self.heap and not self.heap[0][0] < self.tEnd:
            heapq.heappop(self.heap)
        return self.heap[0][1] if self.heap else None

    def pop(self):  -> (t, i)                # after peek() returned i
    def push(self, t, dt, i):
        if not dt > 0: raise ValueError(f'event duration must be > 0, got {dt}')
        heapq.heappush(self.heap, (t + dt, i))
        return t + dt < self.tEnd             # True if member i has more events
```

Exactness notes:
- `t0` and `Ttot` are passed through unchanged, so `tEnd` is computed exactly as the old loops do: flexible `0 + n_steps` (ints), pre-structured `0.0 + Ttot` (equals `Ttot`), circuit `float(t0) + float(Ttot)`.
- The only time arithmetic is `t + dt`, matching the old `t += dt`. IEEE addition is commutative, so `t + dt` equals the old `t += a + b` as long as `dt` is computed as `a + b` by the adapter (section 5).

## 3. `runTeam`

```python
def runTeam(members, world, Ttot, t0=0) -> TeamHistory:
    if not members: raise ValueError('team needs at least one member')
    units = {m.timeUnit for m in members}
    if len(units) != 1: raise ValueError(f'members must share one time unit, got {sorted(units)}')
    for i, m in enumerate(members): m.id = i
    clock = Clock(len(members), Ttot, t0)
    hist = TeamHistory([m.extraNames for m in members])
    while (i := clock.peek()) is not None:
        t, _ = clock.pop()
        out = members[i].event(world, t)
        hist.add(Record(i, t, out.dt, out.kind, out.location, out.reward, out.extras))
        clock.push(t, out.dt, i)
    return hist
```

The `dt > 0` check runs in `clock.push`, after the record is added, so the error message points to the bad event.

`runTeam` never calls `world.reset`. Native worlds (`HeadingArena`, `ZoneArena`) have no state to reset; for a generic world the caller runs `world.reset(seed, len(members))` first, as `TeamEnv.reset` does.

**Fast path: measured, not added.** A plain one-member loop was tried; on a 240 s flexible run (106 658 events) it took 1.64 s against 1.68 s for the heap (about 2%), and the full flexible demo is within NFR-2 with the heap alone. So one team and one agent run through the same code, which also keeps FR-11 true by construction.

## 4. `Member` base class and default `event`

```python
class Member:
    timeUnit = 's'
    extraNames = ()
    id = None                                  # set by runTeam / TeamEnv

    def event(self, world, t) -> Outcome:
        obs = world.observe(self.id)
        action = self.act(obs)
        reward, dt, location, info = world.apply(self.id, action)
        self.learn(obs, action, reward, info)
        return Outcome(dt, 'step', location, reward, ())

    def act(self, obs): raise NotImplementedError
    def learn(self, obs, action, reward, info): pass
```

## 5. Adapters (`explRL/members.py`)

Each adapter subclasses `Member`, stores the wrapped agent as `self.agent`, sets `timeUnit` and `extraNames`, and overrides `event`. Each `event` is the body of the old loop, in the same order. Only the record line and the time update move out (the record becomes `extras`; the time update becomes `dt`). `members.py` imports `math`, `prestructured.wrap`, `circuit.goalStats` and `multi`, and no training module.

### 5a. `FlexibleMember(agent)`: `timeUnit = 'sample'`, `extraNames = ('theta', 'saccade', 'dt', 'reward')`

```python
def event(self, world, t):
    ag = self.agent
    step = ag.rl.chooseAction(ag)
    new_theta, r = world.step(ag.theta, step.dx)
    ag.rl.updateParams(ag, step, r)
    ag.theta = new_theta
    return Outcome(step.dt, 'saccade' if step.saccade else 'fixation', new_theta, r,
                   (step.theta, step.saccade, step.dt, r))
```

The old loop records `step.theta` (heading **before** the step) after `updateParams` and sets `agent.theta` last; moving `agent.theta = new_theta` before the return is safe because nothing after it reads `agent.theta`.

### 5b. `PrestructuredMember(agent)`: `timeUnit = 's'`, `extraNames = ('thetaA', 'thetaC', 'fixDur', 'direction', 'jumped', 'reward', 'thetaG')`

```python
def event(self, world, t):
    ag, p = self.agent, self.agent.params
    ev = ag.rl.chooseAction(ag)
    thetaA1, r = world.step(ag.theta, ev.dx)
    ag.rl.updateParams(ag, ev, r)
    row = (ev.thetaA, ev.thetaC, ev.fixDur, ev.direction, ev.jumped, r, ag.policy.thetaG)
    ag.theta, ag.thetaC = wrap(thetaA1), ev.thetaC_next
    return Outcome(ev.fixDur + p.tS, 'event', ag.theta, r, row)
```

`dt = ev.fixDur + p.tS` is the same expression as the old `t += ev.fixDur + p.tS`.

### 5c. `CircuitMember(agent)`: `timeUnit = 's'`, `extraNames = ('a', 'c', 'direction', 'steps', 'jumped', 'valence', 'fixDur', 'thetaG', 'strength', 'mirror')`

```python
def event(self, world, t):
    ag, rl, p = self.agent, self.agent.rl, self.agent.params
    sac = rl.chooseAction(ag)
    for _ in range(sac.steps):
        if rl.learnC:
            rl.updateCompass(ag, world.ringActivity(ag.a), sac.size)
        ag.move(sac.direction)
    jumped = rl.jumps and ag.maybeJump(world.ringActivity(ag.a))
    R = world.valence(ag.a)
    fix = ag.sampleFixation()
    if rl.learnG and R != 0:
        rl.updateGoal(ag, R, math.ceil(fix / p.dtG))
    gs = goalStats(ag.policy.wG)
    row = (ag.a, ag.c, sac.direction, sac.steps, jumped, R, fix,
           gs['thetaG'], gs['strength'], (ag.a + ag.c) % p.nCirc)
    return Outcome(p.tS + fix, 'iteration', ag.a, float(R), row)
```

`dt = p.tS + fix` is the same expression as the old `t += p.tS + fix`. The record's reward is the valence as a float; the integer `R` stays in `extras` (`valence`).

## 6. Wrappers (old functions, same signatures)

```python
def train_agent(agent, env, Ttot=None):                       # train.py
    if Ttot is None: Ttot = agent.params.Ttot
    n_steps = round(Ttot / agent.params.delT)
    h = runTeam([FlexibleMember(agent)], env, n_steps, t0=0)
    rows = [(r.t,) + r.extras for r in h.records]
    t, theta, sac, dt, rew = zip(*rows) if rows else ((),) * 5
    return History(np.asarray(t, np.float64), np.asarray(theta, np.float64),
                   np.asarray(sac, bool), np.asarray(dt, np.int64), np.asarray(rew, np.float64))

def train_prestructured(agent, env, Ttot=None):               # prestructured_train.py
    Ttot = agent.params.Ttot if Ttot is None else Ttot
    h = runTeam([PrestructuredMember(agent)], env, Ttot, t0=0.0)
    rows = [(r.t,) + r.extras for r in h.records]
    cols = list(zip(*rows)) if rows else [()] * 8
    # then the unchanged line that builds EventHistory from cols

def train_circuit(agent, env, Ttot=None, t0=0.0):             # circuit_train.py
    T = agent.params.Ttot if Ttot is None else float(Ttot)
    h = runTeam([CircuitMember(agent)], env, T, t0=float(t0))
    return _history([(r.t,) + r.extras for r in h.records])
```

The three modules import `runTeam` and their member at module level (no import cycle: `members` and `multi` import only model modules). The old pre-structured loop raised `IndexError` on a run with no events; the wrapper now returns an empty history with the same dtypes, like the other two.

Dtype notes:
- `History`: the old arrays are preallocated with `t` float64 (holding integer sample counts), `theta` float64, `saccade` bool, `dt` int64, `reward` float64. The wrapper builds them with the same dtypes from lists; values are equal because the same numbers are stored.
- `EventHistory` and `CircuitHistory`: the wrappers reuse the existing construction lines unchanged.
- `train_circuit` passes `p.Ttot` (not `float(p.Ttot)`) when `Ttot is None`, exactly as the old code did.

## 7. `TeamEnv`

```python
class TeamEnv:
    def __init__(self, world, nAgents, Ttot, t0=0):
    def reset(self, seed=None):                # returns each agent's first observation
        self.world.reset(seed, self.nAgents)
        self.clock = Clock(self.nAgents, self.Ttot, self.t0)
        self.history = TeamHistory([()] * self.nAgents)
        return [self.world.observe(i) for i in range(self.nAgents)]
    def next_agent(self): return self.clock.peek()
    def observe(self, i): return self.world.observe(i)
    def step(self, action):
        i = self.clock.peek()
        if i is None: raise RuntimeError('all agents are done')
        t, _ = self.clock.pop()
        reward, dt, location, info = self.world.apply(i, action)
        self.history.add(Record(i, t, dt, 'step', location, reward, ()))
        more = self.clock.push(t, dt, i)
        return reward, not more
```

`TeamEnv.step` and the default `Member.event` call `world.apply` the same way and record the same fields, so FR-11 holds.

## 8. Toy world and members (tests only, in `nbs/multi.ipynb`)

- `ToyWorld(durations)`: agent `i`'s every action takes `durations[i]` seconds; `observe(i)` returns the agent's event count; `apply(i, action)` returns `(reward=float(action), dt=durations[i], location=i, info={})`; `reset(seed, n)` resets counts.
- `ToyMember(actions)`: `act` returns the next action from a fixed list (cycled); `learn` counts calls (`learnCalls`).
- Expected order for durations `(1.0, 1.5, 1.0)` and `Ttot = 3.0`: starts `0.0: 0, 1, 2`; `1.0: 0, 2`; `1.5: 1`; `2.0: 0, 2`. All three agents' next start time is then 3.0, which is not below 3.0, so they stop. Eight events in total (agent 0: 3, agent 1: 2, agent 2: 3).

## 9. Golden fixtures

`tools/make_phase5_fixtures.py` (refuses to overwrite) writes `nbs/fixtures/phase5/`. It must run on the **pre-Phase-5 code**: the committed fixtures were made from a git worktree of commit `905a48d` with that worktree first on `PYTHONPATH` (RUN.md shows the commands). Every field of every history is saved, under the prefixes below:

| File | Run | Saved |
|---|---|---|
| `flexible.npz` | `loadAgent(seed=0)`, `loadEnv()`, `train_agent(Ttot=2.0)` | every `History` field; final `omega` |
| `prestructured.npz` | `loadEnv(goal=pi)`; `loadPrestructuredAgent(seed=0)`, `train_prestructured(Ttot=240)` (learning on); and `loadPrestructuredAgent(seed=1, learn=False, thetaG0=pi)`, 240 s | every `EventHistory` field as `learn_*` and `fixed_*`; final goal headings `learn_thetaG_end`, `fixed_thetaG_end` |
| `circuit.npz` | `loadCircuitAgent(seed=0)`, `ZoneArena(symmetric=True)`, `train_circuit(Ttot=300)`; then the same agent `train_circuit(Ttot=200, t0=500)`; then `probe(agent, env, T=60, seed=7)` | every `CircuitHistory` field as `seg0_*`, `seg1_*`, `probe_*`; final `wG`, `wC`; `probe_PI`, `probe_jumpRate` |

The tests (in `train`, `prestructured_train` and `circuit_train`) compare every field with `np.array_equal` **and** equal dtype, and the final weights / goal headings exactly. Paths are found from the repo root (the folder containing `pyproject.toml`), as `demo_artifact_dir` does.

## 10. Baseline for the demos (T0)

`results/multiagent/baseline_phase5/` (gitignored): copies of the six `metrics.json` files (`quick/<demo>_metrics.json`, `full/<demo>_metrics.json`), a `sha256.txt` with one hash per file, and `timing.txt` with the wall time of each slow demo run (`nbdev-test --n-workers 0 --flags slow nbs/<demo>.ipynb`). Like the fixtures, the baseline is produced by running the pre-Phase-5 commit in a separate worktree, so it can be rebuilt at any time and can never be overwritten by output of the new code. The final check runs the same script on the new code in the same session and compares hashes and times.

## 11. `demo_multi.ipynb`

Artifacts go to `results/multiagent/demo_multi/quick/` through the existing helpers, with `demo_name='multiagent/demo_multi'` (`save_demo_figure`, `save_demo_metrics`, `demo_artifact_dir`).

1. Four circuit agents (seeds 0-3) in one `ZoneArena`: plot each agent's events on a timeline (one row per agent) to show interleaving; save as `timeline.png`.
2. Plot per-agent cumulative PI, held goal distance to safe, and cumulative jump rate; save as `learning.png`.
3. Check that each agent's records equal its solo run (AC-2), and print the result.
4. Export the team history to `team.jsonl` and show the first three lines.
5. Save `metrics.json`: `mode`, `seed`, `nAgents`, `Ttot_s`, `scene_symmetric`, events per agent, `independent`, and `learning_outcomes` (per-agent PI, distances, strengths, jump rate).
6. Quick run: 300 s, `results/multiagent/demo_multi/quick/`. Slow cell (`#| slow`): 1200 s, `full/`.

`historyFromRecords` in `circuit_train` builds a `CircuitHistory` from `TeamHistory.forAgent` records (same layout as `train_circuit`).
