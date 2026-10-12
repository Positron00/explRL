# Low-level design: Phase 8, benchmark and eval suite

Defaults that were marked *(check)* were calibrated on pilot seeds in task T6 (README) before `PREREG` was frozen.

## 1. Amendments to earlier phases

`explRL/team_refs.py` (FR-1). Sorting occupancy and target within each intake group gives the minimum L1 distance over relabellings (matching two sorted lists is optimal for L1).

```python
def ifdDistanceTies(counts, alloc, intake, nAgents):
    "IFD distance minimised over relabelling patches of equal intake."
    out = np.abs(counts[:, -1] - (nAgents - alloc.sum()))
    for v in np.unique(intake):
        g = np.flatnonzero(intake == v)
        out = out + np.abs(-np.sort(-counts[:, g], axis=1) + np.sort(-alloc[g])).sum(1)
    return 0.5 * out / nAgents
```

`explRL/harness_runs.py` (FR-2, FR-4): `harnessMetrics` calls `ifdDistanceTies(counts, n_ifd, world.intake, N)` where it called `ifdDistance`, and circuit estimates become `{**goalStats(wG), 'a': ag.a, 'c': ag.c, 'nCirc': p.nCirc}`; `demo_harness`'s `bandit_series` uses `ifdDistanceTies` for its plotted series; `benchWorld` reads `shape`:

```python
L, travel, shape = overrides.pop('L', 64), overrides.pop('travelScale', 0.48), overrides.pop('shape', 'ring')
layout = ringLayout(L, travel) if shape == 'ring' else torusLayout(int(round(L ** 0.5)), travel)
```

`explRL/harness.py` (FR-3):

```python
def rebase(self, t):
    "Move the time origin to t: entries keep their ages; later calls may start again from 0."
    if self.K is None:
        self._age(t)                      # sums now refer to time t
    else:
        if t < self.tRef: raise ValueError('time went backwards')
        self.Tw = self.Tw - t
    self.tRef = 0.0
```

Before any change, T1 records the Phase 7 `demo_harness` `metrics.json` hashes (quick and full) with `tools/phase7_demo_hashes.sh` (same layout as the Phase 6 script).

## 2. Metrics (`explRL/bench_metrics.py`)

All functions take `L = ledgerArrays(world.ledger)` (columns `agent, t, dt, kind, location, patch, harvest, reward, s0, s1`). A row's time is its stay (or fixation) start `s0`, which equals `t` for stays. Move periods: `k = floor(s0 / Tmove)`; period `k` spans `[k Tmove, (k + 1) Tmove)`; **full periods** are those with `k >= 1` and `(k + 1) Tmove <= T`.

**Recovery (FR-5).** On the 1 s occupancy grid, `d = ifdDistanceTies(counts, idealFree(world, N)[0], world.intake, N)`. For each full period, with `r_i` the mean of `d` over grid points `i-9 .. i` of the period (`i >= 9`): recovery = the first `i` with `r_i <= delta` (seconds after the move), or `Tmove` if none. `RMRT` = mean over full periods; `reached` = share of periods with a finite time. `nan` without full periods.

**Beliefs (FR-6).** Estimates `M[a, j]`, counts `n[a, j]` (from `harnessMetrics['estimates']`). Known: `n > 0`. True solo rate `v_j`: `min(c, intake_p)` at patch `p`'s current site, `-dangerCost` at a danger site, 0 elsewhere.

```
diversity = mean over j with #known >= 2 of std_a(M[a, j] | known)      (population std)
error     = mean over j with #known >= 1 of |mean_a(M[a, j] | known) - v_j|
```

Not defined (`nan`) for `hierarchical` and random teams (no per-agent estimates).

**Goal spread (circuit teams).** An agent's goal heading `thetaG` is in its own compass frame; its world-frame goal is `phi = thetaG - 2 pi (c - a) / nCirc`. `goalSpread = sqrt(-2 ln R)` with `R = |mean_a exp(i phi_a)|` (circular standard deviation, radians); it goes into the row as `diversity` for circuit teams, with `beliefError` `nan`.

**Discoveries (FR-7).** Rows with `kind != 'travel'` (stays, and circuit fixations), `patch >= 0`, `harvest > 0`, in ledger (time) order, period `floor(s0 / Tmove)`; the first row per `(location, k)` is a discovery by its agent. This is the `Credit` rule: a stay at exactly `k Tmove` belongs to period `k`, as `TeamPatchWorld.advance` moves patches when `nextMove <= t`.

```
hShare_a = harvest_a / sum(harvest),  dShare_a = disc_a / sum(disc)
freeRiding = pearson(hShare, dShare)          (nan if N < 4 or either has zero variance)
```

**Find time, overlap, follow time (FR-8).**
- `findTime(world, L, T)`: for each full period `k` and patch index `p`, the first harvesting row with `patch == p` and `s0` in the period gives `s0 - k Tmove`; `Tmove` if there is none. Mean over `(k, p)`.
- `overlap(world, L, N, T)`: for each full period, `S_a` = locations agent `a` stayed (or fixated) at; mean over agent pairs with a non-empty union of `|S_a & S_b| / |S_a | S_b|`; mean over periods (`nan` for N = 1).
- `followTime(world, L, T)`: for each discovery at `(j, k)` by agent `a` at time `t0`, the first positive harvest at `j` in period `k` by another agent gives `s0 - t0`; `min((k + 1) Tmove, T) - t0` if none. Mean over discoveries.

**Row (FR-9).** `benchMetrics(cell, world, hist, m, delta)` (`m` = the `harnessMetrics` dict) returns the cell keys (`study`, `factor`, `level`, `seed`, `N`, `Trun` = the run's world time, and the flattened `HarnessConfig`, whose `T` is the configured fixed world time; world overrides as `world.<name>`, `None` as an empty string), the Phase 7 scalars (`welfare`, `perAgentSecond`, `harvest`, `dangerCost`, `firstQuarterRate`, `gini`, `coverage`, `dangerShare`, `ifdMean`, `soYield`, `welfareLoss`), `written`, `sent`, `received`, `commPerWelfare` (`(written + sent) / welfare`, `nan` if welfare <= 0), `events` (`len(hist)`), `rmrt`, `reached`, `diversity`, `beliefError`, `discoveries`, `freeRiding`, `findTime`, `overlap`, `followTime`. Wall-clock times never go into rows (they would break NFR-3).

## 3. Statistics (`explRL/bench_stats.py`)

```python
def bootCI(x, n=2000, seed=0):       # percentile 2.5 / 97.5 of resampled means; nan entries dropped
def signFlipP(d, n=10000, seed=0):   # two-sided; exact over all 2^m sign vectors when 2^m <= n,
                                     # else (1 + #{|mean(s d)| >= |mean(d)|}) / (1 + n) with seeded random signs
def holm(p):                         # adj_(i) = max_{j <= i} min(1, (m - j + 1) p_(j)), returned in input order
def cohenDz(d):                      # mean(d) / std(d, ddof=1); nan if std = 0
def scalingFit(N, y, seeds, n=2000): # OLS of y on log2 N; slope CI by resampling seeds (all sizes of a seed together)
```

## 4. Grid (`explRL/bench_grid.py`)

A cell is a plain dict: `study`, `factor`, `level`, `cfg` (a `HarnessConfig.asDict()`), `N`, `seed`, and `runner` (`'harness'` or `'episodes'`, with `arm`, `beta`, `episodes` and `T` for the latter, whose `cfg` is `HarnessConfig(channel='blackboard')`, `factor` `'studyB'` and `level` `f"{arm}|beta={beta}"`). Its sort key is `f"{study}|{factor}|{level}|{cfg['channel']}|{cfg['budget']}|{N:03d}|{seed:05d}"`; a row's key (`rowKey`) appends `|{episode:02d}` (00 for rows that are not episodes).

| Grid | Cells |
|---|---|
| `mainGrid('full')` | channels (none, blackboard, messages, hierarchical) x N (1, 2, 4, 8, 16, 32, 64) x budget (compute `B` 15 360, time `T` 600) x seeds 100-129 = 1 680 |
| `mainGrid('quick')` | the same channels and budgets, N (1, 4, 16), seeds 1000-1001, `B` 1 536, `T` 60 = 48 |
| `sideSweeps('quick')` | one cell per sweep factor and level-1 baseline (N = 4, seed 1000, `B` 1 536, `T` 60) and one study B sequence (`strategy`, `beta` 1, N = 4, seed 1000, 2 episodes of 60 s) |
| `sideSweeps('sweeps')`, fixed compute, N (4, 16, 64), seeds 200-209 | `baseline`: 4 channels (120); `scheme` team, difference: 4 channels (240); `lam` 0, 0.003, 0.03, 0.1: blackboard, hierarchical (240); `radius` 0, 2, 8: messages (90); `K` 1, 10: 4 channels (240); `shape` torus: 4 channels (120); `cUCB` 0.25, 0.5, 2, 4: none, blackboard (240); `circuit`: agent circuit, channels none, blackboard, messages, N (4, 16), fixed world time 600 s (60). Total 1 350 |
| study B (`runner='episodes'`), N (16, 64), seeds 200-209 | arms `fixed-0.5`, `fixed-1` (= fresh), `fixed-2`, `fixed-4`, `strategy` x beta (0, 1), `all` x beta (0, 1): 8 arms x 2 x 10 = 160 sequences of 12 episodes |

```python
def runCell(cell):                        # in a worker process
    if cell['runner'] == 'episodes':
        return runEpisodes(cell['arm'], cell['N'], cell['seed'], cell['episodes'], cell['T'], cell['beta'])   # rows
    cfg = HarnessConfig.fromDict(cell['cfg'])
    world, hist, channel, m = runHarness(cfg, cell['N'], cell['seed'])
    return [benchMetrics(cell, world, hist, m, PREREG['delta'])]

def runGrid(cells, workers=None):
    workers = workers or min(8, os.cpu_count() or 1)
    if workers == 1: out = map(runCell, cells)
    else:
        with multiprocessing.get_context('spawn').Pool(workers) as p: out = p.map(runCell, cells, chunksize=4)
    return sorted((r for rows in out for r in rows), key=rowKey)
```

`'spawn'` is used on every platform so runs match on macOS and Linux. Phase 9 added `runGrid(..., run=runCell)` (any importable runner) and made `confirm` select `study == prereg.get('study', 'main')`; Phase 8's `PREREG`, its hash and its results are unchanged. `writeCSV` writes the union of keys as columns in sorted order, numbers with `repr`, `nan` and missing as empty; `readCSV` reverses it.

**PREREG (FR-13), frozen in T6:**

```python
PREREG = dict(
    version=1, seeds=list(range(100, 130)), budget='compute', alpha=0.05, nflip=10000, delta=0.5,  # delta: T6
    tests=dict(
        P=dict(metric='perAgentSecond', a='blackboard', b='none', sizes=[2, 4, 8, 16, 32, 64], sign=+1),
        H1=dict(metric='rmrt', a='blackboard', b='none', sizes=[4, 8, 16, 32, 64], sign=-1),
        H2=dict(metric='diversity', a='blackboard', b='none', sizes=[4, 8, 16, 32, 64], sign=-1)))
```

`confirm(rows, prereg, seeds=None)`: with `seeds = seeds or prereg['seeds']`, for each test and seed, `d_s` = mean over the listed sizes of `row(a, s, N)[metric] - row(b, s, N)[metric]` (sizes where either value is `nan` are dropped for that seed; the number dropped is reported). Then `mean(d)`, `bootCI(d)`, `cohenDz(d)`, `signFlipP(d, nflip)`; Holm over the three p-values; verdict `supported` (adjusted p < alpha and `sign(mean) == sign`), `contradicted` (adjusted p < alpha, opposite sign) or `not significant`. `preregHash = sha256(json.dumps(PREREG, sort_keys=True))[:12]`.

## 5. Study B (`explRL/episodes.py`)

```python
class LevelBandit(CommBandit):
    def __init__(self, levels=(0.5, 1.0, 2.0, 4.0), cLevel=0.1, fixed=None, w=1.0, K=None, H=10.0):
        super().__init__(None, w, K, 1.0, H)
        self.levels, self.cLevel, self.fixed = levels, cLevel, fixed
        self.S, self.n = np.zeros(len(levels)), np.zeros(len(levels), int)   # value sums and uses per level
        self.e, self.k, self.credit, self.epReward = 0, 0, None, 0.0

    def beginEpisode(self, channel, credit):
        self.channel, self.credit, self.epReward = channel, credit, 0.0
        E = len(self.levels)
        if self.fixed is not None: self.cUCB = self.fixed; return
        if self.e < E: self.k = (self.e + self.id) % E                       # round robin, offset per agent
        else: self.k = int(np.argmax(self.S / self.n + self.cLevel * np.sqrt(np.log1p(self.e) / self.n)))
        self.cUCB = self.levels[self.k]

    def event(self, world, t):
        self._takeCredit(); return super().event(world, t)

    def learn(self, obs, target, reward, info):
        super().learn(obs, target, reward, info)
        self.epReward += reward
        if self.credit is not None and info['kind'] == 'stay':
            self.credit.stay(self._world, self.id, obs['location'], info['harvest'], self.k)

    def endEpisode(self, T):
        self._takeCredit()
        if self.fixed is None: self.S[self.k] += self.epReward / T; self.n[self.k] += 1
        self.e += 1

    def reset(self, keep):           # 'none' | 'strategy' | 'all'
        if keep != 'all': self.rates, self.reports = None, None
        if keep == 'none': self.S[:], self.n[:], self.e = 0, 0, 0
```

`_takeCredit` adds every credit taken from `self.credit` to `epReward`. `runEpisodes(arm, N, seed, episodes=12, T=600.0, beta=0.0, lam=0.01, cLevel=0.1)`:

```python
keep = {'strategy': 'strategy', 'all': 'all'}.get(arm.split('-')[0], 'none')
fixed = float(arm.split('-')[1]) if arm.startswith('fixed') else None
members = [LevelBandit(fixed=fixed) for _ in range(N)]
for i, m in enumerate(members): m.id = i
board, rows = None, []
for e in range(episodes):
    world = benchWorld(); world.reset(10_000 + 100 * seed + e, N)
    if keep == 'all' and board is not None: board.rebase(T)
    else: board = Blackboard(world.L, None, lam, N)
    credit = Credit(N, beta) if beta > 0 else None
    for m in members:
        if e: m.reset(keep)
        m.beginEpisode(board, credit)
    hist = runTeam(members, world, T)
    for m in members: m.endEpisode(T)
    rows.append(episodeRow(arm, beta, N, seed, e, world, hist, members, credit, T))
```

`episodeRow` holds the keys (`study`, `factor`, `level`, `arm`, `beta`, `seed`, `N`, `episode`, `Trun`, `channel` = blackboard, `budget` = `'episode'`) plus `perAgentSecond` (net welfare), `levelMean` and `levelStd` (the `cUCB` used, across agents), `levelStable` (share of agents whose level equals their level in the previous episode; `nan` in episode 0), `discoveries` (ledger rule), `credited`, `freeRiding`, `events`. **Gap closed** (report): per N, with `W(arm)` the mean `perAgentSecond` over episodes 8-11 and seeds, `(W(arm) - W(fixed-1)) / (max_l W(fixed-l) - W(fixed-1))`; reported only when the denominator's 95% CI excludes 0.

| Setting | Default | Meaning |
|---|---|---|
| `levels` | 0.5, 1, 2, 4 | `cUCB` values an agent can choose; 1 is the Phase 7 default |
| `cLevel` | 0.1 (T6) | UCB bonus over levels (value scale: welfare per agent-second, about 0.2-0.5) |
| episodes, `T` | 12, 600 s | 4 round-robin episodes, then 8 learned |
| world seeds | `10 000 + 100 seed + e` | a new world every episode, disjoint from all other seeds |
| `beta` | 0 or 1 | credit off or on |

## 6. Report (`explRL/bench_report.py`, `explRL/bench_figures.py`)

`bench_report`: `byN`, `perSize`, `slopes`, `sweepTable`, `circuitTable`, `teamOptimal`, `studyB` (summaries from rows) and `report(meta, conf, slope, table, opt, sb, sizes, circ) -> str`. `bench_figures`: `mainFigures(rows, conf, prereg)` (scaling, confirmatory, recovery, beliefs, secondary) and `sweepFigures(table, opt, sb)` (sweeps, study B; study A's numbers are the `cUCB` and `scheme` panels of `sweeps.png` and the report's tables):

| Figure | Content |
|---|---|
| `scaling.png` | welfare per agent-second vs N (log2), one line per channel, 95% CIs; panels fixed compute and fixed world time; `scalingFit` slopes (per doubling) in the legend |
| `confirmatory.png` | per test: per-size paired differences with CIs, the averaged contrast and its CI |
| `recovery.png` | RMRT and `reached` vs N per channel (fixed compute) |
| `beliefs.png` | diversity and belief error vs N per channel |
| `secondary.png` | discoveries per run (fixed compute keeps agent-seconds equal across sizes), free-riding index, find time, overlap, follow time, communication per welfare vs N |
| `sweeps.png` | one panel per side-sweep factor: welfare per agent-second vs level, per channel, N = 16 and 64 |
| `studyB.png` | per arm and N, one row each: welfare, level mean and level stability per episode (the level spread and gap closed are in the report) |

`report.md` sections: cells, workers and wall time, `PREREG` hash, git commit, deviations and seeds; **confirmatory results** (table: test, contrast, mean [CI], dz, p, Holm p, verdict); per-size estimates; scaling slopes; side sweeps; circuit teams (welfare and goal spread); study A (team-optimal `cUCB` per channel and size); study B (last-4 welfare, gap closed, level stability); figure guide. Each section appears when its data are in the rows. Everything but the confirmatory table is labelled exploratory.

## 7. Demo (`nbs/demo_bench.ipynb`)

| Section | Flag | Content | Output |
|---|---|---|---|
| Quick grid | none (normal tests) | `mainGrid('quick')` and `sideSweeps('quick')`, `confirm` on its rows (pipeline check only, verdicts not meaningful), all figures and report sections | `bench/quick/` |
| Main grid | `slow` | `mainGrid('full')`, timed; `confirm`; scaling, confirmatory, recovery, beliefs, secondary figures | `bench/full/` |
| Sweeps and studies | `sweeps` | `sideSweeps('sweeps')` (side sweeps, which also give study A, and study B), timed; sweeps and study B figures | `bench/sweeps/` |

`metrics.json` keys: `mode`, `prereg` (the dict), `preregHash`, `gitCommit`, `deviations`, `seeds`, `figures`, `cells`, `wallSeconds`, `workers`; in quick and full mode `confirmatory` (per test: mean, ci, dz, p, pHolm, verdict, n, dropped) and `scaling` (per channel and budget: slope, intercept, ci); in every mode `sweeps` (the side-sweep table), `teamOptimalCUCB` and `studyB` (per arm and N: welfare, level and stability curves, last-4 welfare, gap closed, level stability), empty when the rows have none.

## 8. Determinism and speed

Every cell seeds its world, members and message generators from its own seed (Phase 7 rules); study B also from `10 000 + 100 seed + e`. Rows are sorted by key, and floats are written with `repr`, so the CSV is identical for any worker count (AC-5).

Measured on pilot seeds 1000-1001 (8 processes): 112 main-grid runs in 23 s wall, 124 CPU-seconds, 1.48 M events, 84 µs per event on average. Expected: main grid about 31 CPU-minutes, about 4-5 minutes on 8 processes; side sweeps and study B about 12 minutes on 8 processes. **Measured (T9, T10):** main grid 280 s, side sweeps and study B 690 s on 8 processes. The sweeps cell runs longer than nbdev's default 600 s cell limit, so the long modes use `--cell-timeout 0`.
