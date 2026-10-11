# Low-level design: Phase 6, team environment with incentives

Defaults marked *(T1)* were provisional until the prototype ran. **T1 result (2026-10-11): all four (layout, model) pairs pass AC-11 with these defaults unchanged**, so every *(T1)* value below is confirmed as is (section 10).

## 1. Phase 5 amendments

`explRL/multi.py` (S4): the world gets the start time.

```python
class Member:
    def event(self, world, t) -> Outcome:
        obs = world.observe(self.id)
        action = self.act(obs)
        reward, dt, location, info = world.apply(self.id, action, t)   # t added
        self.learn(obs, action, reward, info)
        return Outcome(dt, 'step', location, reward, ())

class TeamEnv:
    def step(self, action):
        ...
        reward, dt, location, info = self.world.apply(i, action, t)    # t added
```

The toy world in `nbs/multi.ipynb` gets `apply(self, i, action, t=None)`. The `Record.kind` comment gains `'stay'` / `'travel'` (patch world); no code depends on the kind values.

`explRL/members.py` (S6): the valence read moves after the fixation draw, behind a hook. No random draw depends on it, so results are unchanged (checked by the golden fixtures).

```python
class CircuitMember(Member):
    def event(self, world, t):
        ag, rl, p = self.agent, self.agent.rl, self.agent.params
        sac = rl.chooseAction(ag)
        for _ in range(sac.steps):
            if rl.learnC:
                rl.updateCompass(ag, world.ringActivity(ag.a), sac.size)
            ag.move(sac.direction)
        jumped = rl.jumps and ag.maybeJump(world.ringActivity(ag.a))
        fix = ag.sampleFixation()
        R = self.reward(world, t, fix)                 # was: world.valence(ag.a), before the fixation draw
        if rl.learnG and R != 0:
            rl.updateGoal(ag, R, math.ceil(fix / p.dtG))
        ...                                            # row and Outcome unchanged

    def reward(self, world, t, fix):
        return world.valence(self.agent.a)
```

## 2. Layouts (`explRL/patchworld.py`)

```python
@dataclass
class Layout:
    name: str          # 'ring' or 'torus'
    pos: np.ndarray    # (L,) grid index (ring) or (L, 2) cell (torus)
    dist: np.ndarray   # (L, L) layout distance: steps (ring) or cells (torus)
    T: np.ndarray      # (L, L) travel time, s = travelScale * dist

def ringLayout(N=32, travelScale=0.1) -> Layout
    # dist[j, k] = min(|j - k|, N - |j - k|)

def torusLayout(side=8, travelScale=0.5) -> Layout
    # location = y * side + x; dx = min(|x1 - x2|, side - |x1 - x2|), same for dy; dist = sqrt(dx^2 + dy^2)
```

## 3. World

```python
class TeamPatchWorld:
    def __init__(self, layout, nPatches=4, nDanger=4, model='fixed',
                 intake=(0.5, 1.0, 1.5, 2.0), K=100.0, g=0.2, Smin=1.0, c=1.0,
                 tStay=1.0, dangerCost=1.0, Tmove=120.0, noise=0.0, scheme='individual',
                 symmetric=False, patchSites=None, dangerSites=None)
```

| Setting | Default | Meaning |
|---|---|---|
| `model` | `'fixed'` *(T1)* | `'fixed'` intake or `'logistic'` stock (S2) |
| `intake` | `(0.5, 1.0, 1.5, 2.0)` /s *(T1)* | fixed-intake rate per patch (length `nPatches`; a scalar is broadcast) |
| `K`, `g`, `Smin` | 100, 0.2 /s, 1 *(T1)* | logistic capacity, growth rate, floor; most sustainable yield `g K / 4` = 5 /s, so one patch sustains 5 agents at `c = 1` (4 patches: 20), and larger teams over-harvest. `g K / 4` must stay above `c`, or a single agent collapses a patch |
| `c` | 1.0 /s | most one agent can take per second |
| `tStay` | 1.0 s | length of a stay |
| `dangerCost` | 1.0 /s | cost per second at a danger location |
| `Tmove` | 120 s *(T1)* | patch move period (`None` = never) |
| `noise` | 0.0 | relative noise on observed harvest |
| `scheme` | `'individual'` | `'individual'`, `'team'` or `'difference'` |
| `symmetric` | `False` | ring scene for `ringActivity` (plan: asymmetric for team experiments) |
| `patchSites`, `dangerSites` | `None` | fixed sites; `None` draws them in `reset` |

State after `reset(seed, nAgents)`:

```python
self.rngSites, self.rngMoves, self.rngNoise = spawnRngs(seed, 3)        # D7
self.site    = np.array(...)  # (P,) int, location of each patch (drawn without replacement unless given; a copy)
self.danger  = set(...)       # danger locations, plain ints (drawn from the rest unless given)
self.stock   = np.full(P, K)  # logistic only (None for fixed intake)
self.loc     = list(rngSites.integers(L, size=nAgents))   # generic agents' start locations
self.stay    = [None] * nAgents    # current stay: (location, patch or None, s0, s1)
self.last    = [(0.0, 0.0)] * nAgents   # (reward, observed harvest) of the last event
self.tWorld, self.nextMove = 0.0, Tmove
self.ledger  = []
```

### 3.1 Time and moves (FR-5)

```python
def advance(self, t):
    if t < self.tWorld: raise ValueError('time went backwards')
    while self.Tmove and self.nextMove <= t:
        self._regrow(self.nextMove - self.tWorld); self.tWorld = self.nextMove
        self._move(); self.nextMove += self.Tmove
    self._regrow(t - self.tWorld); self.tWorld = t

def _regrow(self, d):          # logistic closed form, S >= Smin > 0
    S = self.stock; self.stock = K / (1 + (K / S - 1) * np.exp(-g * d))

def _move(self):               # S9, patches in index order
    for p in range(P):
        free = [j for j in range(L) if j not in self.site and j not in self.danger]
        self.site[p] = int(self.rngMoves.choice(free))
        # stays registered on patch p are dropped (those agents now stand on an empty location)
```

### 3.2 Claim (FR-4, S3)

```python
def patchAt(self, loc):
    m = np.flatnonzero(self.site == loc); return int(m[0]) if len(m) else None

def _claim(self, i, loc, s0, dur):
    p = self.patchAt(loc)                         # patch id or None
    self.stay[i] = (loc, p, s0, s0 + dur)
    if p is None: return 0.0, 0, None
    n = 1 + sum(1 for k, st in enumerate(self.stay)
                if k != i and st and st[1] == p and st[2] <= s0 < st[3])
    if model == 'fixed':  h = min(c, intake[p] / n) * dur
    else:                 h = min(c * dur, (self.stock[p] - Smin) / n); self.stock[p] -= h
    return h, n, p
```

### 3.3 `apply` (FR-3, FR-6 to FR-8)

```python
def apply(self, i, target, t):
    if not 0 <= target < L: raise ValueError(f'target {target} is not a location')
    self.advance(t)
    loc = self.loc[i]
    if target == loc:
        kind, dur = 'stay', tStay
        h, n, p = self._claim(i, loc, t, dur)
    else:
        kind, dur = 'travel', float(self.layout.T[loc, target])
        self.stay[i], self.loc[i] = None, int(target)
        h, n, p = 0.0, 0, None
    danger = kind == 'stay' and loc in self.danger
    obsH = self._observed(h)          # h * max(0, 1 + noise * z); z drawn only when noise > 0 and h > 0
    reward = self._reward(i, kind, p, n, obsH, danger, dur, t)
    self.last[i] = (reward, obsH)
    s0, s1 = (t, t + dur) if kind == 'stay' else (nan, nan)
    self.ledger.append((i, t, dur, kind, self.loc[i], p, h, reward, s0, s1))
    return reward, dur, self.loc[i], dict(kind=kind, harvest=h, observed=obsH, nHere=n,
                                           patch=p, danger=danger, dur=dur)
```

Rewards (S5); `E = yieldModel` (section 5); `n_q` and `nDanger` count the stays (at patch `q`, at danger locations) that cover `t`, after this event's stay is registered; `n` is the claim's count:

| Scheme | Stay at patch `p` | Stay at danger | Stay elsewhere | Travel |
|---|---|---|---|---|
| `individual` | `obsH` | `-dangerCost * dur` | 0 | 0 |
| `team` | `(sum_q E(q, n_q) - dangerCost * nDanger) / nAgents * dur` (same formula everywhere) | same | same | 0 |
| `difference` | `(E(p, n) - E(p, n - 1)) * dur` | `-dangerCost * dur` | 0 | 0 |

### 3.4 Observation and neighbours

```python
def observe(self, i) -> dict:
    return dict(location=self.loc[i], travel=self.layout.T[self.loc[i]], lastReward=self.last[i][0],
                lastHarvest=self.last[i][1])

def neighbours(self, i, radius) -> list[int]:
    # generic agents k != i with layout.dist[loc[i], loc[k]] <= radius (loc is the destination while travelling)
```

### 3.5 Ring methods and `zoneConfig` (FR-10, FR-11)

```python
def ringActivity(self, a): return circuit.ringActivity(a, self.layout.dist.shape[0], self.symmetric)
def valence(self, a):      return 1 if self.patchAt(a) is not None else (-1 if a in self.danger else 0)

def fixate(self, i, a, s0, dur, t):
    self.advance(t)
    h, n, p = self._claim(i, a, s0, dur)
    net = self._observed(h) - (dangerCost * dur if a in self.danger else 0.0)
    self.ledger.append((i, t, s0 - t + dur, 'iteration', a, p, h, float(np.sign(net)), s0, s0 + dur))
    return h, net

@classmethod
def zoneConfig(cls, symmetric=True, N=32, intake=np.inf, **kw):
    z = ZoneArena(N=N, symmetric=symmetric)
    safe = [a for a in range(N) if z.isSafe(a)]
    return cls(ringLayout(N), nPatches=len(safe), nDanger=N - len(safe), model='fixed',
               intake=intake, Tmove=None, symmetric=symmetric,
               patchSites=safe, dangerSites=[a for a in range(N) if a not in safe], **kw)
```

With `intake = inf` (and `noise = 0`) every safe location pays `c * dur > 0` and every other location costs `dangerCost * dur > 0`, so `sign(net)` equals `ZoneArena.valence` (AC-1). `zoneConfig` keeps `ZoneArena`'s default `symmetric=True`; team experiments pass `symmetric=False` (plan guidance). The AC-1 test calls `world.reset(seed, 1)` before `runTeam`.

## 4. Agents (`explRL/team_agents.py`)

```python
class PatchMember(Member):
    timeUnit = 's'
    extraNames = ('target', 'harvest', 'nHere', 'patch')
    def event(self, world, t):
        obs = world.observe(self.id)
        target = self.act(obs)
        reward, dt, loc, info = world.apply(self.id, target, t)
        self.learn(obs, target, reward, info)
        return Outcome(dt, info['kind'], loc, reward, (target, info['harvest'], info['nHere'], info['patch']))

class randomAgent(PatchMember):
    def __init__(self, rng): self.rng = rng
    def act(self, obs): return int(self.rng.integers(len(obs['travel'])))

class banditAgent(PatchMember):
    def __init__(self, K=None, cUCB=1.0, H=10.0): ...       # rates: list of deques (maxlen=K), made on first act
    def act(self, obs):
        n = np.array([len(r) for r in self.rates]); T = obs['travel']
        if (n == 0).any():                                   # nearest unvisited, then lower index
            idx = np.flatnonzero(n == 0); return int(idx[np.argmin(T[idx])])
        mean = np.array([np.mean(r) for r in self.rates])
        score = (mean + self.cUCB * np.sqrt(np.log1p(n.sum()) / n)) * self.H / (self.H + T)
        return int(np.argmax(score))
    def learn(self, obs, target, reward, info):
        if info['kind'] == 'stay': self.rates[obs['location']].append(reward / info['dur'])

class CircuitPatchMember(CircuitMember):
    extraNames = CircuitMember.extraNames + ('harvest',)
    def reward(self, world, t, fix):
        h, net = world.fixate(self.id, self.agent.a, t + self.agent.params.tS, fix, t)
        self._harvest = h
        return int(np.sign(net))
    def event(self, world, t):
        out = super().event(world, t)
        return out._replace(extras=out.extras + (self._harvest,))
```

`np.argmin` / `np.argmax` return the lowest index on ties, which gives the tie rules of FR-15. The `banditAgent` defaults `cUCB = 1.0` and `H = 10 s` are *(T1)*: rewards are about 1 per second, so `cUCB = 1` explores a lot on 64 locations; the prototype passed with these values, so they stay. The AC-8 test sets `cUCB = 0.2` on a small ring.

## 5. References (`explRL/team_refs.py`)

```python
def yieldModel(world, p, n) -> float:
    if n == 0: return 0.0
    if world.model == 'fixed': return min(n * world.c, world.intake[p])
    msy = world.g * world.K / 4
    return n * world.c if n * world.c <= msy else world.g * world.Smin * (1 - world.Smin / world.K)

def idealFree(world, N) -> (np.ndarray, float):
    n = np.zeros(P, int)
    for _ in range(N):
        pay = [yieldModel(world, p, n[p] + 1) / (n[p] + 1) for p in range(P)]
        best = int(np.argmax(pay))
        if pay[best] <= 0: break
        n[best] += 1
    return n, sum(yieldModel(world, p, n[p]) for p in range(P))

def socialOptimum(world, N) -> (np.ndarray, float):
    # V[p][m] = best total with patches 0..p-1 and at most m agents; keep argmax for the allocation.
```

Worked check (AC-7): fixed intake `I = (1, 2, 3)`, `c = 100`, `N = 6`. With `c` large, adding an agent to patch `p` pays `I_p / (n_p + 1)`.

| Agent | Payoffs (patch 0, 1, 2) | Goes to | Allocation |
|---|---|---|---|
| 1 | 1, 2, 3 | 2 | (0, 0, 1) |
| 2 | 1, 2, 1.5 | 1 | (0, 1, 1) |
| 3 | 1, 1, 1.5 | 2 | (0, 1, 2) |
| 4 | 1, 1, 1 | 0 (tie, lowest index) | (1, 1, 2) |
| 5 | 0.5, 1, 0.75 | 1 | (1, 2, 2) |
| 6 | 0.5, 0.67, 0.75 | 2 | (1, 2, 3) |

Result `(1, 2, 3)`: agents in proportion to intake, each earning 1 per second (input matching).

## 6. Metrics (`explRL/team_refs.py`)

The ledger is turned into arrays once: `L = ledgerArrays(world.ledger)` with fields `agent, t, dt, kind, location, patch, harvest, reward, s0, s1`.

| Function | Definition |
|---|---|
| `welfare(L, nAgents, Ttot)` | `(total, perAgentSecond)` of `sum(harvest)` |
| `gini(x)` | `sum_ij |x_i - x_j| / (2 n^2 mean(x))`; 0 if all zero |
| `occupancy(L, nAgents, P, Ttot, step=1.0)` | `(times, counts)`, counts `(len(times), P + 1)`; a stay row with patch `p` adds 1 at grid times in `[s0, s1)`; last column = outside |
| `coverage(counts)` | mean over times of the share of patches with at least one agent |
| `dangerShare(L, danger, nAgents, Ttot)` | time in stays at danger locations / `(nAgents * Ttot)` |
| `ifdDistance(counts, alloc, nAgents)` | `0.5 * sum |counts - [alloc, N - sum(alloc)]| / N` per time |
| `timeToIFD(times, d, moveTimes, delta=0.2, w=10)` | per move: seconds from the move until the mean of `d` over the last `w` grid points (all at or after the move) first is `<= delta`; measured at the window's last point (`nan` if this does not happen before the next move) |
| `welfareLoss(total, soYield, Ttot)` | `1 - total / (soYield * Ttot)` |

## 7. Determinism

World streams come from `spawnRngs(seed, 3)` (sites, moves, noise); agent streams from `spawnRngs(agentSeed, n)`. `banditAgent` draws no random numbers. Same seeds give the same `TeamHistory` and ledger (AC-10).

## 8. Speed

Per event: `banditAgent.act` is O(L) numpy; `_claim` loops over agents (O(N)); `team` scheme sums `P` yields. A 64-agent, 600 s run has about 64 x 600 / 1.5 = 26 000 events. Target under 30 s (NFR-2). If too slow: keep per-patch lists of current stays instead of scanning all agents. **Measured (T8): 64 `banditAgent`s, ring, 600 s: about 4 s**, so the fix is not needed.

## 9. Demo (`nbs/demo_team.ipynb`)

`MAIN` is the layout chosen by T1. Artifacts under `results/multiagent/demo_team/{quick,full}/` with `demo_name='multiagent/demo_team'`.

| Section | Content | Artifact | Quick | Full |
|---|---|---|---|---|
| Layouts | ring and torus with patch (sized by intake) and danger sites | `layouts.png` | yes | yes |
| References | IFD and SO allocations and yields, both patch models, default world, `N` = 4, 16, 64 | in `metrics.json` | yes | yes |
| Team run | 8 `banditAgent`s and 8 `randomAgent`s, two runs on the same world seed, `MAIN`, moving patches: team welfare rate (harvest per second in 10 s bins, by event start, with the SO yield line) and IFD distance over time (1 s grid), move times marked; Gini, coverage, danger share, time-to-IFD | `team_run.png`, `team.jsonl` (bandit run) | 300 s, seed 0 | 600 s, seed 0 |
| Circuit team | 4 `CircuitPatchMember`s, `zoneConfig(symmetric=False, intake=1.0)`: PI (via `historyFromRecords`, which ignores the extra `harvest` field) and harvest per agent | `circuit_team.png` | 300 s | 1200 s |
| Scaling preview | welfare per agent-second vs team size {1, 4, 16, 64}, bandit vs random, 95% bootstrap CI; SO and IFD yield per agent as lines; prototype checks (1) and (2) re-run on the package world (AC-12): (1) the first-quarter team harvest rate of both teams is below 0.9 x SO yield, (2) the bandit and random CIs of welfare per agent-second do not overlap | `scaling.png` | no | 10 seeds, 600 s |
| Sanity | AC-1 result printed and stored | `metrics.json` | yes | yes |
| Summary | plain-language conclusions and figure guide | `report.md` | yes | yes |

`metrics.json` keys: `mode`, `seed`, `layout`, `model`, `scheme`, `scene_symmetric` (circuit team, as in `demo_multi`), `Tmove`, `references`, `team_run` (per agent type: welfare, perAgentSecond, gini, coverage, dangerShare, timeToIFD, welfareLoss), `circuit_team`, `sanity`, and in full mode `scaling` (with `check1`, `check2` pass flags).

## 10. Prototype (T1, `tools/phase6_prototype.py`)

Throwaway, numpy only, under 200 lines, does not import `explRL`. It writes `results/multiagent/phase6_prototype/{report.md, metrics.json}`.

- **World**: the section 3 rules in simplified form, with the section 3 defaults (layouts, 4 patches, 4 danger locations, intake, `K`, `g`, `Smin`, `c`, `dangerCost`, `Tmove`; noise 0): synchronous 1 s steps; a stay lasts one step; travel lasts `ceil(T[loc, j])` steps and the agent counts at its destination; agents staying at the same patch in a step split its harvest (fixed: `min(c, I_p / n)` each; logistic: `min(c n, S_p - Smin)` shared, stock regrows each step in closed form); a stay at a danger location earns `-dangerCost`. Each seed gives one world (sites, moves) shared by all harnesses, so comparisons are paired.
- **Agents**: `banditAgent` (section 4 rules, `K = None`; every stay is learned, including 0 at empty locations and `-dangerCost` at danger), `randomAgent` (uniform over all locations, its own included, FR-14).
- **Channels** (simplified Phase 7): `none`; `blackboard` (latest reward per location from any agent's stay); `messages` (every 10 s each agent with data sends its best location and mean reward to `k = 2` other random agents; range `inf`). Shared values are used only where an agent has no stays of its own, counted as one stay.
- **Grid**: 2 layouts x 2 models x (3 channels + random) x team sizes {1, 4, 16, 64} x 10 seeds, 600 s.
- **Check** (AC-11), per layout and model, on team harvest per second: (1) no ceiling: every channel's first-quarter rate is below 0.9 x the SO yield for that team size; (2) no floor: the 95% bootstrap CI of `none` lies above that of `randomAgent` at every team size; (3) per team size, take the best and worst channel by mean, and the per-seed difference between them: its 95% bootstrap CI excludes 0 for at least two team sizes, and "its size differs between team sizes" means the CI at the team size with the largest mean gap lies above the CI at the size with the smallest.
- **Choice**: among the passing pairs, `MAIN` and the model are the pair that "passes most clearly": the largest weakest gap, that is the highest minimum over team sizes > 1 of the gap CI's lower bound.
- **Output**: a pass/fail table per (layout, model) with the gap per team size. Settings are tried in order from a list (first the defaults) until one passes; every attempt is written to `report.md`. If nothing passes, change the difficulty settings (patch count, `Tmove`, travel scale, patch richness `intake` / `K` / `g`, noise, communication range, `cUCB`) and rerun.
- **Result (2026-10-11, about 15 s)**: attempt 1 (defaults) passes for all four pairs. Gap CI lower bound at team sizes 4 / 16 / 64: ring-fixed 0.12 / 0.73 / 1.46, ring-logistic 0.11 / 0.24 / 3.46, torus-fixed 0.17 / 0.10 / 0.67, torus-logistic 0.09 / 0.55 / 1.25 (team harvest per second; at size 1 all channels are identical). **`MAIN` = ring, model = fixed intake**; defaults unchanged.
- **Known gap**: the prototype steps all agents together every second, while the package world is event-based with claims at the start of stays. So the demo's full run re-runs checks (1) and (2) on the package world (AC-12).
