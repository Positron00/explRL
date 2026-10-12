# Low-level design: Phase 7, harness configurations

Defaults that were marked *(check)* were fixed by the harness check (AC-11, task T9, attempt 3).

## 1. Phase 6 amendments

`explRL/team_agents.py` (FR-6): the estimate moves into one helper, so `CommBandit` can extend it. The arithmetic is the same as before (counts as floats change no result: `n` only enters as a divisor and in a sum).

```python
class banditAgent(PatchMember):
    def _stats(self, obs):
        n = np.array([len(r) for r in self.rates], float)
        mean = np.array([np.mean(r) if len(r) else 0.0 for r in self.rates])
        return mean, n

    def act(self, obs):
        T = obs['travel']
        if self.rates is None:
            self.rates = [deque(maxlen=self.K) for _ in T]
        mean, n = self._stats(obs)
        if (n == 0).any():
            idx = np.flatnonzero(n == 0); return int(idx[np.argmin(T[idx])])
        score = (mean + self.cUCB * np.sqrt(np.log1p(n.sum()) / n)) * self.H / (self.H + T)
        return int(np.argmax(score))
```

`CircuitPatchMember.reward` keeps the net harvest it already computes (`self._lastNet = net`), so the Phase 7 circuit member can share it; its return value is unchanged.

`explRL/patchworld.py` (FR-11): `fixate` adds `self.loc[i] = int(a)` as its first line. Rewards, ledger rows and random draws are unchanged.

Before either change, task T1 records the Phase 6 `demo_team` `metrics.json` hashes (quick and full) in `results/multiagent/baseline_phase6/sha256.txt` with `tools/phase6_demo_hashes.sh`, in the same way as the Phase 5 baseline.

## 2. Blackboard (`explRL/harness.py`)

Two storage modes give the same view (AC-3 checks this when `K` is at least the number of writes):

- **`K = None` (all entries count): running faded sums.** Totals `S[L]`, `C[L]` and per-writer parts `Si[n, L]`, `Ci[n, L]`, all kept at a reference time `tRef`. Moving to a later time `t` multiplies every array by `exp(-lam (t - tRef))`. A read is `O(L)`, a write `O(n L)`, independent of how many entries were written. (A buffer would grow with the run: a busy patch in a 64-agent, 600 s run collects about 12 000 entries.)
- **`K` set: a ring buffer** `(L, K)` of values, times and writers; a read is one `(L, K)` numpy pass.

```python
class Blackboard:
    def __init__(self, L, K=None, lam=0.0, n=None):
        self.L, self.K, self.lam, self.tRef = L, K, float(lam), 0.0
        if K is None:
            self.S, self.C = np.zeros(L), np.zeros(L)
            self.Si, self.Ci = np.zeros((n, L)), np.zeros((n, L))   # n = team size (writers 0..n-1)
        else:
            self.V, self.Tw = np.zeros((L, K)), np.zeros((L, K)); self.Wr = np.full((L, K), -1)
            self.count = np.zeros(L, int)                           # entries ever written per location
        self.stats = defaultdict(lambda: dict(written=0, sent=0, received=0))

    def _age(self, t):                       # running-sum mode: fade everything to time t
        if t < self.tRef: raise ValueError('time went backwards')
        f = np.exp(-self.lam * (t - self.tRef))
        self.S *= f; self.C *= f; self.Si *= f; self.Ci *= f; self.tRef = t

    def write(self, i, loc, value, t):
        if self.K is None:
            self._age(t)
            self.S[loc] += value; self.C[loc] += 1; self.Si[i, loc] += value; self.Ci[i, loc] += 1
        else:
            if t < self.tRef: raise ValueError('time went backwards')
            s = self.count[loc] % self.K
            self.V[loc, s], self.Tw[loc, s], self.Wr[loc, s] = value, t, i
            self.count[loc] += 1; self.tRef = t
        self.stats[i]['written'] += 1

    def view(self, i, t):
        if self.K is None:
            self._age(t)
            if i < 0: return self.S.copy(), self.C.copy()
            return self.S - self.Si[i], self.C - self.Ci[i]
        if t < self.tRef: raise ValueError('time went backwards')
        valid = np.arange(self.K)[None, :] < np.minimum(self.count, self.K)[:, None]
        wt = np.exp(-self.lam * (t - self.Tw)) * valid * (self.Wr != i)
        return (wt * self.V).sum(1), wt.sum(1)
```

`view(-1, t)` reads every entry (used by the lead). Calls must come with non-decreasing `t`, which `runTeam` guarantees because every member reads and writes at its event start time; an earlier `t` raises `ValueError`. In both modes `view` finally sets `S` and `C` to 0 wherever `C < 1e-12`: this removes rounding residue in running-sum mode (`S - Si[i]` where only agent `i` wrote) and makes "faded away" mean the same in both modes (weight below 1e-12, an age of about 2 800 s at `lam = 0.01`).

## 3. MessageBus

```python
class MessageBus:
    def __init__(self, n, k=2, period=10.0, radius=np.inf, rngs=None):
        self.k, self.period, self.radius, self.rngs = int(k), float(period), radius, rngs
        self.window = [-1] * n                # last window index in which agent i was due
        self.inbox = [deque() for _ in range(n)]
        self.stats = ...                       # as Blackboard

    def due(self, i, t):
        m = int(t // self.period)
        if m > self.window[i]:
            self.window[i] = m; return True
        return False

    def send(self, world, i, loc, value, t):
        near = sorted(world.neighbours(i, self.radius))
        if not near: return []
        to = self.rngs[i].choice(near, min(self.k, len(near)), replace=False)
        for r in to:
            self.inbox[r].append((i, int(loc), float(value), float(t)))
            self.stats[r]['received'] += 1
        self.stats[i]['sent'] += len(to)
        return [int(r) for r in to]

    def take(self, i):
        out = list(self.inbox[i]); self.inbox[i].clear(); return out
```

`world.neighbours` excludes the sender and counts an agent in transit at its destination (Phase 6 FR-9). Recipients use only `rngs[i]`, which no other code draws from.

## 4. Lead

```python
class Lead:
    def __init__(self, L, n, K=None, lam=0.01, cUCB=1.0, H=10.0):
        self.table = Blackboard(L, K, lam, n)
        self.assigned = [None] * n
        self.cUCB, self.H = cUCB, H
        self.stats = self.table.stats

    def report(self, i, loc, value, nHere, t):
        self.table.write(i, loc, value * max(int(nHere), 1), t)   # estimated total rate of the location

    def assign(self, i, loc, travel, t):
        S, C = self.table.view(-1, t)
        unknown = C == 0
        if unknown.any():
            idx = np.flatnonzero(unknown); j = int(idx[np.argmin(travel[idx])])
        else:
            a = np.bincount([x for k, x in enumerate(self.assigned) if k != i and x is not None],
                            minlength=len(C))
            Ihat = S / C
            score = (Ihat / (a + 1) + self.cUCB * np.sqrt(np.log1p(C.sum()) / C)) * self.H / (self.H + travel)
            j = int(np.argmax(score))
        self.assigned[i] = j
        return j
```

A location is unknown while its view weight is 0: it has no entries, or they have faded below 1e-12 (section 2); it is then re-explored. Worked check (AC-5): `Ihat = (2, 1, 0, ...)`, `cUCB = 0`, equal travel. Follower 0: scores `2/1, 1/1` -> 0. Follower 1: `2/2, 1/1` (tie) -> 0. Follower 2: `2/3, 1/1` -> 1. Allocation (2, 1), equal to `idealFree` for intakes (2, 1) with `c` large.

## 5. Bandit members (`explRL/harness_agents.py`)

```python
class CommBandit(banditAgent):
    def __init__(self, channel=None, w=1.0, K=None, cUCB=1.0, H=10.0):
        super().__init__(K=K, cUCB=cUCB, H=H)
        self.channel, self.w, self.reports = channel, float(w), None

    def event(self, world, t):
        self._world, self._t = world, t
        if isinstance(self.channel, MessageBus):
            for _, j, v, _ in self.channel.take(self.id):     # always taken; stored only when read
                if self.w != 0:
                    self._store()[j].append(v)
        return super().event(world, t)                       # observe -> act -> apply -> learn

    def _store(self):
        if self.reports is None:
            self.reports = [deque(maxlen=self.K) for _ in range(self._world.L)]
        return self.reports

    def _stats(self, obs):
        if self.channel is None or self.w == 0:
            return super()._stats(obs)                       # exactly Phase 6 (FR-8)
        S = np.array([sum(r) for r in self.rates]); n = np.array([len(r) for r in self.rates], float)
        rep = self._store()
        S = S + self.w * np.array([sum(r) for r in rep]); n = n + self.w * np.array([len(r) for r in rep])
        if isinstance(self.channel, Blackboard):
            Sv, Cv = self.channel.view(self.id, self._t)
            S, n = S + self.w * Sv, n + self.w * Cv
        return np.where(n > 0, S / np.where(n > 0, n, 1), 0.0), n

    def learn(self, obs, target, reward, info):
        super().learn(obs, target, reward, info)
        if info['kind'] != 'stay': return
        rate, loc = reward / info['dur'], obs['location']
        if isinstance(self.channel, Blackboard):
            self.channel.write(self.id, loc, rate, self._t)
        elif isinstance(self.channel, MessageBus) and self.channel.due(self.id, self._t):
            own = [(np.mean(r), j) for j, r in enumerate(self.rates) if len(r)]
            if own:
                v, j = max(own, key=lambda x: (x[0], -x[1]))         # best own mean, ties to the lower index
                self.channel.send(self._world, self.id, j, v, self._t)

    def estimates(self, t):
        self._t = t                                          # read the blackboard at t (the run's end)
        return self._stats(None)


class LeadFollower(PatchMember):
    def __init__(self, lead): self.lead = lead
    def event(self, world, t):
        self._t = t; return super().event(world, t)
    def act(self, obs):
        return self.lead.assign(self.id, obs['location'], obs['travel'], self._t)
    def learn(self, obs, target, reward, info):
        if info['kind'] == 'stay':
            self.lead.report(self.id, obs['location'], reward / info['dur'], info['nHere'], self._t)
```

`w` only scales what the agent reads: a member with `w = 0` still writes to the blackboard and sends messages (FR-7), so the bridge test (AC-1) also shows that sharing alone changes nothing. Unvisited test, UCB bonus and total count all use `n` from `_stats`, so a location known only from reports counts as visited (AC-6), and reports shrink the exploration bonus in proportion to `w`.

## 6. Circuit member

```python
class CircuitCommMember(CircuitPatchMember):
    def __init__(self, agent, channel=None, w=1):
        if isinstance(channel, Lead): raise TypeError('circuit members cannot follow a lead')
        super().__init__(agent)
        self.channel, self.w, self.own = channel, int(w), {}   # own: location -> [sum, count] of net rates

    def reward(self, world, t, fix):
        R = super().reward(world, t, fix)                     # fixate; sets self._harvest and self._lastNet
        self._net, self._fix = self._lastNet, fix
        return R

    def event(self, world, t):
        out = super().event(world, t)                         # own saccade, jump, fixation, goal update
        if self.channel is not None:
            self._share(world, t)
            if self.w > 0: self._read(t)
            elif isinstance(self.channel, MessageBus): self.channel.take(self.id)   # drop unread reports
        return out
```

`CircuitPatchMember.reward` gets a one-line change to keep `net` (`self._lastNet = net`); its return value and the history are unchanged. `_share` writes `net / fix` at location `a` with the event start time `t` (blackboard; the harvest is claimed during this event, and channels need non-decreasing times), or, when `due`, sends the best location by the member's own mean net rate (messages); `own` is updated first. `_read` collects reports (messages: `take`; blackboard: the location with the highest `S / C` among `C > 0`, one report) and, for each with `value != 0` and `rl.learnG`, applies:

```python
cRep = (ag.c + j - ag.a) % p.nCirc
for _ in range(self.w):
    ag.policy.wG = goalStep(ag.policy.wG, cRep, np.sign(value), p)
```

While one location stays best on the blackboard, it nudges the goal at every event; `w` sets how hard. The row's `thetaG` and `strength` are computed before these updates, so they record the agent's own learning of that event; reports show up from the next row. With `channel = None` or `w = 0` no goal update happens, and message recipients use only the bus's generators, so the history equals `CircuitPatchMember`'s (AC-2).

## 7. Runs (`explRL/harness_runs.py`)

```python
@dataclass
class HarnessConfig:
    channel: str = 'none'          # 'none' | 'blackboard' | 'messages' | 'hierarchical'
    agent: str = 'bandit'          # 'bandit' | 'circuit' | 'random'
    w: float = 1.0
    K: Optional[int] = None
    lam: float = 0.01
    k: int = 2
    period: float = 10.0
    radius: float = np.inf
    budget: str = 'time'           # 'time' | 'compute'
    B: float = 15360.0
    T: float = 600.0
    cUCB: float = 1.0
    H: float = 10.0
    world: dict = field(default_factory=dict)   # overrides for benchWorld / circuitWorld
    def asDict(self): ...
    @classmethod
    def fromDict(cls, d): ...
```

| Setting | Default | Meaning |
|---|---|---|
| `w` | 1.0 | report weight (bandit); integer goal steps per report (circuit) |
| `K` | `None` | entries kept per location (own stays, stored reports, blackboard, lead table); "no memory" = 1 |
| `lam` | 0.01 /s | evaporation, half-life `ln 2 / lam` = 69 s; chosen when patches moved every 120 s; the benchmark world now moves them every 40 s, so the half-life is longer than a patch's stay (the evaporation demo compares 0, 0.01, 0.1) |
| `k`, `period`, `radius` | 2, 10 s, `inf` | messages per send, send window, communication range |
| `B` | 15 360 agent-s | fixed compute; 64 agents get 240 s (five moves at `Tmove` 40 s; two at Phase 6's 120 s), one agent 15 360 s |
| `T` | 600 s | fixed world time |
| `cUCB`, `H` | 1.0, 10 s | as Phase 6 (bandit and lead) |
| `benchWorld()` | AC-11 attempt 3: `ringLayout(L=64, travelScale=0.48)`, 16 patches with fixed intake (0.8, 1.6, 2.4, 3.2) x 4 (total 32), 8 danger sites, random sites per seed, `c` 0.85, `Tmove` 40 s, noise 0.45, `dangerCost` 2.6; any `TeamPatchWorld` argument, `L` and `travelScale` can be overridden | the benchmark world (Phase 6 defaults were `travelScale` 0.1, intake (0.5, 1, 1.5, 2), `c` 1, `Tmove` 120 s, no noise, `dangerCost` 1, random sites) |
| `circuitWorld()` | `zoneConfig(symmetric=False, intake=1.0)` | ring world for circuit teams (asymmetric, plan guidance) |

```python
def worldTime(N, cfg):
    if N < 1: raise ValueError('team needs at least one agent')
    v = cfg.B / N if cfg.budget == 'compute' else cfg.T
    if not v > 0: raise ValueError('budget must be positive')
    return float(v)

def makeChannel(cfg, L, N, seed): ...      # None for 'none' or a random team / Blackboard(L, K, lam, N) /
                                           # MessageBus(N, k, period, radius, spawnRngs(seed + 2000, N)) /
                                           # Lead(L, N, K, lam, cUCB, H)
def makeTeam(cfg, N, seed, channel): ...   # bandit: CommBandit or LeadFollower; random: randomAgent(rng);
                                           # circuit: CircuitCommMember(loadCircuitAgent(seed=s_i)), s_i drawn
                                           # from spawnRngs(seed + 1000, N)[i]; 'hierarchical' with circuit
                                           # agents raises ValueError

def runHarness(cfg, N, seed):
    world = circuitWorld(**cfg.world) if cfg.agent == 'circuit' else benchWorld(**cfg.world)
    world.reset(seed, N)
    channel = makeChannel(cfg, world.L, N, seed)
    members = makeTeam(cfg, N, seed, channel)
    if cfg.agent == 'circuit':
        world.loc = [m.agent.a for m in members]           # range is right before the first fixation
    T = worldTime(N, cfg)
    hist = runTeam(members, world, T)
    return world, hist, channel, harnessMetrics(cfg, world, hist, channel, members, N, T)
```

`harnessMetrics` returns: `config` (dict), `N`, `T`, `agentSeconds = N x T`, `welfare` (sum of `netHarvest`: true harvest minus `dangerCost` x `(s1 - s0)` for stay and fixation rows at danger locations), `perAgentSecond` (`welfare / (N T)`), `harvest` (gross), `dangerCost`, `firstQuarterRate` (net welfare of rows with `t < T / 4`, divided by `T / 4`), `gini` (of gross harvest per agent, since net totals can be negative), and for generic agents `coverage`, `dangerShare`, `ifdMean` (mean IFD distance on the 1 s grid), `timeToIFD` (after each move before `T`), `soYield` and `welfareLoss` (Phase 6 functions; IFD and SO for team size `N`); `comm` (totals of `written`, `sent`, `received`, and per agent-second); and `estimates` (bandits: `(mean, n)` per agent from `estimates(T)`, read at the run's end; lead followers: none, the lead's table instead; circuit: final `thetaG` and `strength` per agent). The occupancy metrics use `'stay'` rows only, so they are omitted for circuit teams.

`rangeCheck(cfgs, sizes=(1, 4, 16, 64), seeds=range(10), T=600.0)` runs each named configuration in `cfgs` and a random team (`agent='random'`) at fixed world time `T` for every size and seed, then applies the Phase 6 section 10 checks to `firstQuarterRate` and the whole-run team rate (`welfare / T`), both in team harvest per second, exactly as the Phase 6 prototype and demo did: (1) every channel's first-quarter rate, averaged over seeds, below `0.9 x soYield`; (2) the 95% bootstrap CI of `none` above that of random at every size; (3) per size, the paired best-minus-worst channel difference has a CI excluding 0 for at least two sizes, and the CI at the size with the largest mean gap lies above the CI at the size with the smallest. All configurations run on one world, the first configuration's `world` overrides; the random team and the social optimum use the same world. It returns the flags, the gaps, the social optimum per size and a table `table[str(N)][name] = [whole-run, first-quarter]` (seed means; `name` includes `'random'`).

## 8. Demo (`nbs/demo_harness.ipynb`)

Artifacts under `results/multiagent/demo_harness/{quick,full}/` with `demo_name='multiagent/demo_harness'`, through `save_demo_figure`, `save_demo_metrics` and `save_demo_report`.

| Section | Content | Artifact | Quick | Full |
|---|---|---|---|---|
| Channels | 8 `CommBandit`s (hierarchical: `LeadFollower`s), benchmark world, fixed world time: team welfare rate (10 s bins, mean over seeds), IFD distance, move times; time to IFD and communication cost per channel | `channels.png` | 300 s, seeds 0-2 | 600 s, seeds 0-9 |
| Evaporation | blackboard with `lam` = 0, 0.01, 0.1: time to IFD after moves and welfare | `evaporation.png` | 300 s, seeds 0-2 | 600 s, seeds 0-9 |
| Circuit channels | 4 `CircuitCommMember`s on `circuitWorld()`, channels `none`, `blackboard`, `messages`: harvest and PI per agent | `circuit_channels.png` | 300 s | 1200 s |
| Harness check | AC-11 (`rangeCheck`) with the four channels | `range_check.png`, in `metrics.json` | no | yes |
| Budgets | welfare per agent-second vs team size {1, 2, 4, 8, 16, 32, 64} for the four channels, fixed compute and fixed world time, 95% bootstrap CIs | `scaling_budgets.png` | no | 5 seeds |
| Summary | plain-language takeaways and a figure guide | `report.md` | yes | yes |

`metrics.json` keys: `mode`, `seeds`, `world` (benchWorld settings), `defaults` (a `HarnessConfig` dict), `channels` (per channel: mean and CI of welfare per agent-second, time to IFD, communication cost), `evaporation`, `circuit` (`scene_symmetric: false`, harvest and PI per channel), and in full mode `range_check` (flags and table) and `budgets`.

## 9. Determinism and speed

World streams: `spawnRngs(seed, 3)` inside the world (Phase 6). Member streams: `spawnRngs(seed + 1000, N)` (random agents' choices; circuit agents' seeds). Message streams: `spawnRngs(seed + 2000, N)`. `CommBandit`, `LeadFollower` and `Lead` draw no random numbers. Same configuration and seed give the same history, ledger and channel `stats` (AC-9).

Per event, `CommBandit` adds one blackboard view (`O(L)` with `K = None`, `O(L K)` with a window) and, after a stay, one write (`O(N L)` with `K = None`), or a few deque appends for messages. T8 times a 64-agent blackboard team for 600 s (target under 30 s) and records the cost per event; the Phase 8 main grid (about 1 700 runs x 10 000 events) needs roughly 50 µs per event to stay near 15 minutes. Phase 6 already measured about 150 µs per event for plain bandits (64 agents, 600 s, about 4 s), so a single process would take about 45 minutes before channel costs. The measured number decides whether Phase 8 runs seeds in parallel processes (standard library), trims the grid, or speeds up the event loop.

**Measured (T8, adopted benchmark world, 64 agents, 600 s):** blackboard 1.6 s, 42 µs per event; `messages` 50 µs; `hierarchical` 23 µs; `none` 122 µs, because Phase 6's `banditAgent._stats` recomputes `np.mean` over each location's full history at every event (`K = None`), now over 64 locations. At these costs the Phase 8 main grid (about 1 700 runs x 10 000 events, a quarter of them `none`) takes roughly 15-20 minutes in one process; parallel seeds, or running sums in `banditAgent` (checked against the Phase 6 hashes), bring it under 10.
