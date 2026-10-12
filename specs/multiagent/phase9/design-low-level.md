# Low-level design: Phase 9, safety and mechanism design

Defaults that were marked *(check)* (`theta`) were calibrated on pilot seeds in task T7 (README) before `PREREG_H3` was frozen.

## 1. Amendments to earlier phases

`explRL/harness.py` (FR-1, FR-2). `blocked` is an attribute set after construction (empty by default), so no existing call changes.

```python
class Blackboard:
    blocked = frozenset()                      # instance attribute replaces it when a Monitor is attached

    def write(self, i, loc, value, t):
        if i in self.blocked:
            self.stats[i]['rejected'] = self.stats[i].get('rejected', 0) + 1
            return
        ...                                    # unchanged

    def viewBy(self, i, t, weights):
        "View with each writer's sums scaled by weights[writer]; writer i left out (running-sum mode only)."
        if self.K is not None: raise ValueError('viewBy needs K = None')
        self._age(t)
        w = np.asarray(weights, float).copy(); w[i] = 0.0
        return self._clean(w @ self.Si, w @ self.Ci)
```

`MessageBus.send` returns `[]` and counts `rejected` when the sender is in `blocked`.

`explRL/bench_grid.py` (FR-3): `runGrid(cells, workers=None, run=runCell)` maps `run` instead of `runCell`; `confirm` selects `r['study'] == prereg.get('study', 'main')`. `PREREG` is not touched, so its hash stays `8a59293847ae`.

Before any change, T1 records the Phase 7 `demo_harness` hashes (as they are after Phase 8) and the hash of Phase 8's quick `runs.csv` in `results/multiagent/baseline_phase8/` with `tools/phase8_baseline.sh`.

## 2. Bad agents (`explRL/adversary.py`)

All report through a shared mixin, `ReportLog` (also used by `DefendedBandit`), that logs `(loc, value, ownBelief, t)` (`ownBelief` = mean of the agent's own stays at `loc`, after this stay; 0 if none) for the white-box score.

```python
class Liar(CommBandit):
    def learn(self, obs, target, reward, info):
        banditAgent.learn(self, obs, target, reward, info)              # honest own beliefs
        if info['kind'] != 'stay': return
        w, loc = self._world, obs['location']
        lie = -w.dangerCost if info['harvest'] > 0 else w.c
        if isinstance(self.channel, Blackboard): self.channel.write(self.id, loc, lie, self._t); self._log(loc, lie)
        elif isinstance(self.channel, MessageBus) and self.channel.due(self.id, self._t):
            own = [(np.mean(r), j) for j, r in enumerate(self.rates) if len(r)]
            if own: j = min(own)[1]; self.channel.send(w, self.id, j, w.c, self._t); self._log(j, w.c)   # worst place, sold as best

class FreeRider(CommBandit):
    def act(self, obs):                        # reported-positive locations only, best combined estimate, no bonus
        rep = self._reported()                 # others' reports: mean per location (nan if none)
        mean, _ = self._stats(obs)
        ok = np.flatnonzero(rep > 0)
        return int(ok[np.argmax(mean[ok])]) if len(ok) else obs['location']
    def learn(self, obs, target, reward, info): banditAgent.learn(self, obs, target, reward, info)

class Saboteur(FreeRider):
    def act(self, obs):
        rep = self._reported()
        return int(np.nanargmax(rep)) if np.isfinite(rep).any() else obs['location']
```

`_reported()` reads the blackboard `view` (others' entries) or the stored messages; for `none` it is all `nan`, so free-riders and saboteurs stay put. Lead variants subclass `LeadFollower`: `LeadLiar.learn` calls `lead.report(i, loc, lie, 1, t)`; `LeadFreeRider.learn` does nothing; `LeadSaboteur.act` returns the location with the most entries in `lead.assigned` (its own excluded; its current location if none).

## 3. Defences (`explRL/defence.py`)

```python
class Monitor:
    def __init__(self, n, sanctions=False, theta=1.0, window=120.0, alpha=0.1, sigma=0.5, channel=None):
        self.rho, self.strikes = np.ones(n), [deque() for _ in range(n)]       # strike times per sender
        self.maxLevel, self.firstRevoke = np.zeros(n, int), np.full(n, np.nan)
        ...                                    # stores the settings and the channel

    def record(self, s, error, t):
        self.rho[s] = (1 - self.alpha) * self.rho[s] + self.alpha * np.exp(-error / self.sigma)
        if self.sanctions:
            if error > self.theta: self.strikes[s].append(t)
            self._sync(t)

    def level(self, s, t):                     # strikes count for `window` seconds (sliding window)
        while self.strikes[s] and self.strikes[s][0] <= t - self.window: self.strikes[s].popleft()
        return min(len(self.strikes[s]), 3)

    def weights(self, t):
        if not self.sanctions: return self.rho
        self._sync(t)
        return self.rho * np.array([(1, 1, 0.5, 0)[self.level(s, t)] for s in range(len(self.rho))])
```

`_sync(t)` sets `channel.blocked` to the senders at level 3 (reinstating those whose strikes have faded) and updates `maxLevel` and `firstRevoke`.

```python
class DefendedBandit(CommBandit):
    def __init__(self, channel=None, defence='none', monitor=None, q=0.0, rng=None, alpha=0.1, sigma=0.5, **kw):
        super().__init__(channel, **kw)
        ...                                    # tau (private trust, ones), report log, check counters, trip state

    def _weights(self):                        # None means plain CommBandit reading
        if self.defence == 'none': return None
        return self.tau if self.defence == 'trust' else self.monitor.weights(self._t)

    def _stats(self, obs):
        wts = self._weights()
        if wts is None: return super()._stats(obs)
        S, n = own stays (sum, count)
        S, n += w * sum over stored messages (sender s, value v) of wts[s] * (v, 1)
        if blackboard: Sv, Cv = channel.viewBy(id, t, wts); S, n += w * (Sv, Cv)
        return mean, n

    def act(self, obs):
        if self._trip == obs['location']: self._trip = None; self._onTrip = True; return obs['location']   # checking stay
        self._onTrip = False
        if self.q > 0 and self.rng.random() < self.q:
            j = self._checkTarget()            # highest reported value among locations not stayed at in the last Tmove
            if j is not None and j != obs['location']:
                self._trip, self._onTrip = j, True; self.deliberate += 1; return j
        return super().act(obs)

    def learn(self, obs, target, reward, info):
        super().learn(obs, target, reward, info)                       # honest write or send, logged
        if self._onTrip: self.checkSeconds += info['dur']
        if info['kind'] == 'stay' and self.defence != 'none': self._check(obs['location'], reward / info['dur'])
```

`_check(j, r)`: for each other sender `s` with a current report at `j` (blackboard: faded `Ci[s, j] > 0.05`, report `Si[s, j] / Ci[s, j]`; messages: the latest stored report from `s` about `j` within the last `Tmove`), `error = |report - r|`; with `'trust'` update `tau[s]` by the C6 rule; with `'reputation'` and `'sanctions'` call `monitor.record(s, error, t)`. With `defence = 'none'` and `q = 0` no generator is drawn and no weight is applied, so choices equal `CommBandit`'s (AC-1). `_setup(world)` (called at every event, effective once) creates `tau`, the per-location message store, the last-stay times and the observation store (`rates`), because a spot check on the first event skips `banditAgent.act`, which would otherwise create the store. `DefendedBandit.event` stores each message twice: in `CommBandit`'s value store (read when `defence = 'none'`, which keeps AC-1 exact) and as `(sender, value, t)` per location (read by the defences). It also records the time of its last own stay per location (for `_checkTarget`) and, after `CommBandit.learn` has written or sent, logs that report through `ReportLog`.

| Setting | Default | Meaning |
|---|---|---|
| `alpha`, `sigma` | 0.1, 0.5 | trust and reputation update rate and error scale (pilot) |
| `theta` | 2.5 (T7) | error above which a check is a strike (C11) |
| `window` | 120 s | a strike counts for 120 s (three patch moves), then is forgiven |
| `q` | 0.05 | deliberate spot-check probability per event in the defence grid (D2, D3); D1 uses 0 there; the monitoring grid sweeps 0, 0.02, 0.05, 0.1 |

## 4. Runs and metrics (`explRL/safety_runs.py`)

```python
@dataclass
class SafetyConfig(HarnessConfig):
    kind: str = 'none'          # 'none' | 'liar' | 'freerider' | 'saboteur'
    nBad: int = 0
    defence: str = 'none'       # 'none' | 'trust' | 'reputation' | 'sanctions'
    q: float = 0.0
    theta: float = 2.5          # T7

def runSafety(cfg, N, seed):
    world = benchWorld(**cfg.world); world.reset(seed, N)
    channel = makeChannel(cfg, world.L, N, seed)
    monitor = Monitor(N, cfg.defence == 'sanctions', cfg.theta, channel=channel) if cfg.defence in ('reputation', 'sanctions') else None
    members = makeTeam9(cfg, N, seed, channel, monitor)   # slots 0..nBad-1 bad; check generators spawnRngs(seed + 3000, N)
    T = worldTime(N, cfg)
    hist = runTeam(members, world, T)
    return world, hist, channel, safetyRow(cfg, world, hist, channel, monitor, members, N, T, seed)
```

`makeTeam9` always uses `DefendedBandit` for honest agents (with `defence = 'none'` and `q = 0` its choices equal `CommBandit`'s, AC-1, and its reports are still logged for the white-box score); `LeadFollower`s and lead variants for `hierarchical`.

**Row (FR-12).** Cell keys (`study`, `factor`, `level`, `seed`, `N`, `Trun`, `channel`, `budget`, `kind`, `nBad`, `defence`, `q`, `theta`); `Wh`, `Wt` (from `netHarvest`, honest slots vs all); `monitorCost` (sum of `checkSeconds` / `N T`), `checks`, `deliberate`; `badLevel2`, `badRevoked`, `honestLevel2`, `honestRevoked` (shares of bad and honest agents whose `maxLevel` reached 2 and 3), `firstRevoke` (earliest revocation of a bad agent, `nan` if none); `aucWhite` (liar runs on blackboard and messages), `aucBlack` (liar runs with a defence); `trustBad`, `trustHonest` (mean weight given to bad and honest senders at the end); `events`, `discoveries`, `freeRiding` (Phase 8 functions).

```
white_a = mean over agent a's logged reports of |value - ownBelief|
black_a = 1 - mean over honest observers o != a of tau_o[a]       ('trust')
        = 1 - rho[a]                                              ('reputation', 'sanctions')
auc(scores, isBad) = P(score of a random bad agent > score of a random honest agent), ties count 1/2
```

**Loss rows (FR-13).** `lossRows(rows)` pairs every row with `nBad > 0` with the row of the same `study`, `channel`, `defence`, `q`, `N`, `seed` and `nBad = 0`, and returns rows with those keys plus `kind`, `nBad`, `budget`, `loss = 1 - Wh / Wh_clean` and `lossTeam = 1 - Wt / Wt_clean`.

## 5. Grids and H3 (`explRL/safety_grid.py`)

**H3 (FR-14), frozen in T7:**

```python
PREREG_H3 = dict(version=1, study='h3', seeds=list(range(300, 330)), budget='compute', alpha=0.05, nflip=10000,
                 tests=dict(H3=dict(metric='loss', a='blackboard', b='messages', sizes=[8, 16, 32], sign=1)))
```

`confirm(lossRows(rows), PREREG_H3)` reuses Phase 8's statistics: per seed, the mean over sizes of `loss(blackboard) - loss(messages)`; sign-flip p; Holm over a family of one (no change); verdict.

Fixed compute (`B = 15 360`), benchmark world, Phase 7 channel defaults, `theta` from T7.

| Grid | Cells |
|---|---|
| `attackGrid('full')`, seeds 400-409 | channels (none, blackboard, messages, hierarchical) x N (16, 64) x (clean + kinds (liar, free-rider, saboteur) x counts (1, 10%, 25%)), no defence = 4 x 2 x 10 x 10 = 800 |
| `defenceGrid('full')`, seeds 400-409 | channels (blackboard, messages) x defences (trust `q = 0`; reputation and sanctions `q = 0.05`) x N (16, 64) x (clean + 3 kinds x 3 counts) = 2 x 3 x 2 x 10 x 10 = 1 200 |
| `monitorGrid('full')`, seeds 400-409 | blackboard x defences (trust, reputation, sanctions) x `q` (0, 0.02, 0.05, 0.1) x N (16, 64) x (clean, liars 25%) = 3 x 4 x 2 x 2 x 10 = 480 |
| `h3Grid('full')`, seeds 300-329 | channels (blackboard, messages) x N (8, 16, 32) x (clean, one liar), no defence = 360 |
| `quick` (each grid), seeds 1000-1001, `B / 10` | attack: blackboard and messages x N 8 x (clean + each kind x 1); defence: blackboard x each defence x (clean, one liar), `q = 0.05`; monitor: blackboard x sanctions x `q` 0.05 x (clean, 25% liars); H3: both channels x N 8 x (clean, one liar) |

Counts: `round(0.10 N)` and `round(0.25 N)` with a minimum of 1 (N = 16: 2 and 4; N = 64: 6 and 16). A cell is a plain dict with `runner='safety'`, `study` and `factor` = its grid, `level = f"{kind}x{nBad}|{defence}|q={q}"` and a `SafetyConfig.asDict()`; `runSafetyCell(cell)` runs it. Because `level` carries the attack and defence, Phase 8's `rowKey` keeps every row distinct and `runGrid`'s sort stays deterministic. A defence's cost without attack is read against the attack grid's clean, undefended run on the same seed, channel and size.

## 6. Report (`explRL/safety_report.py`, `explRL/safety_figures.py`)

`safety_report.summaries(rows)` builds every table (`group` by keys with mean and bootstrap CI per metric; `costBenefit` pairs defended clean runs with the attack grid's clean, undefended runs, and defended 25%-liar runs with undefended ones); `report(meta, conf, tabs)` writes the text; `safety_figures.safetyFigures(tabs)` draws each figure whose table has data.

| Figure | Content |
|---|---|
| `attack.png` | honest welfare per honest agent-second vs number of bad agents; one panel per kind and size, one line per channel; no defence |
| `team.png` | the same for team welfare |
| `defence.png` | blackboard and messages: honest welfare vs number of liars (and of free-riders, saboteurs) per defence |
| `cost.png` | each defence's cost without attack (relative to no defence) next to its benefit under 25% liars |
| `monitor.png` | honest welfare under 25% liars and without attack vs monitoring cost (the `q` sweep), per defence |
| `detection.png` | detection AUC, white-box vs black-box, per defence and size |
| `h3.png` | relative loss from one liar per size for both channels, and the contrast with its CI |

`report.md`: settings and seeds, `PREREG_H3` hash, git commit and deviations; the H3 table (contrast, mean [CI], dz, p, verdict) and per-size losses; then, labelled exploratory: attack tables (honest and team welfare and relative loss per channel, kind, count, size; the free-riding index in free-rider runs), defences (benefit under attack, cost without, false-sanction rates, time to revoke), monitoring sweep, detection AUC; figure guide.

## 7. Demo (`nbs/demo_safety.ipynb`)

| Section | Flag | Content | Output |
|---|---|---|---|
| Quick | none | all four grids in quick mode; `confirm` on quick loss rows (pipeline check only) | `safety/quick/` |
| H3 | `slow` | `h3Grid('full')`, timed; `confirm(lossRows(rows), PREREG_H3)`; `h3.png` | `safety/h3/` |
| Exploratory | `sweeps` | attack, defence and monitor grids, timed; the other figures | `safety/full/` |

Long modes use `nbdev-test --cell-timeout 0`. `metrics.json`: `mode`, `cells`, `workers`, `wallSeconds`, `seeds`, `preregHash`, `gitCommit`, `prereg` (`PREREG_H3`), `deviations`, `theta`, `figures`, `h3` (the `confirm` result in quick and h3 modes, else null) and `tables` (every summary table, keys joined with `/`).

## 8. Determinism and speed

Every cell seeds its world, members, message generators (`seed + 2000`) and check generators (`seed + 3000`); rows are sorted by key, so the CSV does not depend on the number of workers. Pilot cost (seeds 1000-1011): about 1.7 CPU-seconds per run with private trust. Estimate: exploratory grids about 2 480 runs, roughly 70-90 CPU-minutes, about 10-12 minutes on 8 processes; H3 360 runs at sizes up to 32, about 1 minute. T5 measures the cost per event of `DefendedBandit` (the weighted read adds one `(n x L)` product per event). **Measured:** 64 agents with sanctions and `q = 0.05`, fixed compute: 63 µs per event; H3 (360 runs) 59 s; exploratory grids (2 480 runs) 570 s on 8 processes.
