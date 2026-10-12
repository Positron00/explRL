# Requirements: Phase 8, benchmark and eval suite

Terms used below.

- **Cell**: one run of the grid: a `HarnessConfig` (as a plain dict), a team size `N` and a seed.
- **Main grid**: the cells of decision B1 (1 680 runs).
- **Welfare**: harvest minus danger cost (Phase 7). **Primary metric**: welfare per agent-second at fixed compute.
- **Tie-invariant IFD distance**: the share of agents that would have to move to reach the ideal free distribution, minimised over relabelling patches of equal intake.
- **Recovery time**: after a patch move, the seconds until the 10 s rolling mean of the tie-invariant distance first reaches `delta`, censored at the next move. **Restricted mean recovery time (RMRT)**: its mean over the run's full move periods (from a move to the next one, both within the run), with censored periods counted as `Tmove`.
- **Belief**: an agent's estimated reward rate per location at the run's end (`CommBandit.estimates`). **Belief diversity**: the mean over locations known to at least two agents of the standard deviation of their beliefs; for circuit teams, the circular standard deviation of the agents' goal headings in world coordinates. **Belief error**: the mean over locations of the absolute difference between the team's average belief and the true solo rate.
- **True solo rate** of a location: `min(c, intake)` at a patch, `-dangerCost` at a danger site, 0 elsewhere, at the run's end.
- **Discovery**: the first stay with positive harvest at a patch site in one move period (the `Credit` rule). **Free-riding index**: Pearson correlation across agents between an agent's share of the team's harvest and its share of the team's discoveries.
- **Episode**: one run of `T` seconds on one world seed; a **sequence** is several episodes played by the same team on new world seeds.
- **Pre-registration (`PREREG`)**: the frozen definition of the confirmatory tests (cells, contrasts, statistics, `delta`, seeds, alpha).

## Functional requirements

### Amendments to earlier phases
- **FR-1** `team_refs.ifdDistanceTies(counts, alloc, intake, nAgents)` shall return the tie-invariant distance per time step. `ifdDistance` and every Phase 6 result shall not change.
- **FR-2** `harnessMetrics` shall compute `ifdMean` and `timeToIFD` with the tie-invariant distance, and `demo_harness`'s IFD series shall use it too. For circuit teams, each agent's `estimates` entry shall also hold its heading `a`, compass reading `c` and `nCirc`, so its goal heading can be put in world coordinates. Phase 7's `demo_harness` `metrics.json` changes only in its IFD-derived fields (`timeToIFD`); the change is recorded in the Phase 7 README.
- **FR-3** `Blackboard.rebase(t)` shall move the time origin to `t`: every entry keeps its age, and the next call may use times from 0. It is used only when a blackboard persists across episodes.
- **FR-4** `benchWorld(shape='torus', ...)` shall build an 8 x 8 torus (64 locations) with the same travel scale per unit distance, patch, danger and move settings; `shape='ring'` (default) is unchanged.

### Metrics (`explRL/bench_metrics.py`)
- **FR-5** `recovery(world, L, N, T, delta)` (`L` = ledger arrays) shall return the RMRT and the share of move periods that reach `delta`.
- **FR-6** `beliefs(world, estimates)` shall return belief diversity and belief error from the per-agent `(mean, n)` estimates; locations an agent has never seen (n = 0) are not part of its beliefs. `goalSpread(estimates)` shall return the circular standard deviation of circuit agents' world-frame goal headings.
- **FR-7** `discoveries(world, L)` shall return, per agent, its discovery count, using the patch sites recorded in the ledger (stays and circuit fixations) and move periods `floor(s0 / Tmove)`; `freeRiding(L, disc, N)` shall return the free-riding index (`nan` below 4 agents or without variance).
- **FR-8** `findTime(world, L, T)` shall return the mean time from a patch move until the first positive harvest at each new site (censored at the next move); `overlap(world, L, N, T)` the mean pairwise Jaccard overlap of the sets of locations agents stayed at, per move period; `followTime(world, L, T)` the mean time from a discovery until a second agent harvests at that site (censored).
- **FR-9** `benchMetrics(cell, world, hist, m, delta)` (with `m` the Phase 7 metrics dict, which holds the per-agent estimates) shall return one flat dict of scalars: the Phase 7 scalar metrics, the FR-5 to FR-8 metrics, communication per unit welfare, and the cell's keys. No lists, so a row fits a CSV.

### Statistics (`explRL/bench_stats.py`)
- **FR-10** `bootCI(x, n=2000, seed=0)`: 95% percentile bootstrap interval of the mean. `signFlipP(d, n=10000, seed=0)`: two-sided p-value of a paired mean difference by random sign flips (exact enumeration when `2^len(d) <= n`). `holm(p)`: Holm-adjusted p-values. `cohenDz(d)`: mean over standard deviation of paired differences. `scalingFit(N, y, seeds, n=2000)`: least-squares slope and intercept of `y` on `log2 N`, with a bootstrap interval of the slope from resampling seeds.

### Grid (`explRL/bench_grid.py`)
- **FR-11** `mainGrid(mode)` shall return the B1 cells (`'full'`) or a small grid with the same factors (`'quick'`: sizes 1, 4, 16, 2 pilot seeds, budgets scaled by 1/10). `sideSweeps(mode)` shall return the B9 cells (which also serve study A) and the B11 study B sequences (`'sweeps'`), or one cell per sweep factor and one short study B sequence (`'quick'`), so every runner path is exercised in normal tests.
- **FR-12** `runGrid(cells, workers)` shall run every cell (`runHarness`, which also covers circuit teams, or `runEpisodes` for study B), compute `benchMetrics` in the worker, and return rows sorted by cell key. `writeCSV(rows, path)` / `readCSV(path)` round-trip the rows (numbers as floats, `nan` as empty).
- **FR-13** `PREREG` shall be a constant dict holding the confirmatory contrasts, sizes, budget, metric names, `delta`, seeds and alpha; `confirm(rows, prereg, seeds=None)` shall use `prereg['seeds']` unless `seeds` is given (the quick grid passes its pilot seeds; its verdicts are a pipeline check only) and return, per test, the per-seed differences' mean, bootstrap CI, `cohenDz`, raw and Holm-adjusted p-values and a verdict (`supported`, `contradicted` if significant in the opposite direction, or `not significant`).

### Study B (`explRL/episodes.py`)
- **FR-14** `LevelBandit(levels=(0.5, 1, 2, 4), cLevel=0.1, fixed=None, w=1.0, K=None, H=10.0)` shall extend `CommBandit`. At `beginEpisode(channel, credit)` it takes the episode's channel and `Credit` (or `None`) and chooses its level: `fixed` if given; else, with `e` the number of episodes it has played, the level at index `(e + id) mod len(levels)` while `e < len(levels)`, and afterwards the level with the highest value plus `cLevel x sqrt(ln(1 + e) / n_l)` (`n_l` = episodes that used level `l`). A level's value is the mean over the episodes that used it of (episode reward + credit received) / episode length. Within an episode it acts as `CommBandit` with `cUCB` = its level.
- **FR-15** `reset(keep)` shall clear map-level state (own stays, stored reports) when `keep` is `'strategy'`, keep everything when `'all'`, and clear everything including level statistics when `'none'`.
- **FR-16** `runEpisodes(arm, N, seed, episodes=12, T=600.0, beta=0.0, lam=0.01, cLevel=0.1)` (`arm` one of `fixed-0.5`, `fixed-1`, `fixed-2`, `fixed-4`, `strategy`, `all`) shall play a sequence: world seed `10 000 + 100 x seed + e` for episode `e`; a new `Credit` each episode when `beta > 0`; the blackboard kept and rebased (`all`) or rebuilt; and return one row per episode: welfare per agent-second, mean and standard deviation across agents of the level used, `levelStable` (share of agents using the same level as in the previous episode; the plan's "persistent scouts and foragers"), discoveries, credit paid and the free-riding index.

### Demo
- **FR-17** `nbs/demo_bench.ipynb` shall run the quick grid in normal tests, the main grid and confirmatory analysis with `--flags slow`, and the side sweeps and studies with `--flags sweeps`, writing `runs.csv`, `metrics.json`, `report.md` and figures under `results/multiagent/bench/{quick,full,sweeps}/` (the long modes with `--cell-timeout 0`). The report states every confirmatory verdict, the `PREREG` hash and the git commit, and labels everything else exploratory.

## Pre-registered analysis (frozen in T6)

| Test | Contrast (paired over seeds 100-129) | Cells | Statistic per seed | Expected sign |
|---|---|---|---|---|
| P | blackboard minus none | fixed compute, sizes 2-64 | mean over sizes of welfare per agent-second | + |
| H1 | blackboard minus none | fixed compute, sizes 4-64 | mean over sizes of RMRT (`delta` from T6) | − (faster) |
| H2 | blackboard minus none | fixed compute, sizes 4-64 | mean over sizes of belief diversity | − (lower) |
| H3 (Phase 9) | (welfare loss with one liar) blackboard minus messages | defined in the Phase 9 spec | | + |

Two-sided sign-flip test with 10 000 flips; Holm over P, H1 and H2 at alpha 0.05; 95% bootstrap CIs and `cohenDz` reported for each. Nothing else is confirmatory.

## Quality requirements

- **NFR-1 Exactness:** Phase 5 golden fixtures, the paper-demo hashes and the Phase 6 `demo_team` hashes stay identical.
- **NFR-2 Speed:** quick grid under 30 s in normal tests; full main grid under 10 minutes with the default workers; side sweeps and studies under 60 minutes. Measured times are recorded.
- **NFR-3 Determinism:** a cell's row depends only on the cell; the CSV is byte-identical for 1 and 4 workers.
- **NFR-4 Size, style, dependencies:** each new module under 200 lines; nbdev notebooks with tests; no new dependencies (numpy, matplotlib, standard library).
- **NFR-5 Integrity:** the confirmatory seeds are run once, after `PREREG` is committed; any later change to `PREREG` is reported as a deviation in the report.

## Acceptance criteria

Normal tests (`nbdev-test --n-workers 0`):

- **AC-1 Regression:** NFR-1 holds; Phase 7 tests pass; `demo_harness` `metrics.json` differs from the T1 baseline only in its IFD-derived fields.
- **AC-2 Tie-invariant distance:** on a hand-built world with two equal-intake patches, occupancy (1, 0) and (0, 1) both have distance 0 against target (1, 0); with distinct intakes the value equals `ifdDistance`.
- **AC-3 Metrics:** hand-built ledgers give the expected RMRT (including a censored period), discoveries (one per site and period; none for zero harvest or non-patch stays), free-riding index, find time, overlap and follow time; `beliefs` gives the expected diversity and error for three agents with known estimates; `goalSpread` is 0 for agents whose world-frame goals agree although their compass readings differ.
- **AC-4 Statistics:** `bootCI` of a constant is that constant; `signFlipP` is 1 for all-zero differences and equals the exact enumeration for 8 values; `holm` matches a worked example; `scalingFit` recovers slope 0.1 on noise-free data.
- **AC-5 Grid:** `mainGrid('full')` has 1 680 cells with the B1 factors and `sideSweeps('sweeps')` 1 350 cells plus 160 sequences; `mainGrid('quick')` runs in under 30 s; its CSV round-trips and is byte-identical for 1 and 4 workers; `sideSweeps('quick')` runs every runner path.
- **AC-6 Study B pieces:** `LevelBandit` uses the round-robin levels in the first episodes and the UCB choice afterwards; credit received adds to the episode's value; `reset` clears exactly the right state; `Blackboard.rebase` keeps ages (a view after rebasing equals the view before at the same ages).
- **AC-7 Confirm:** on synthetic rows with a known effect, `confirm` returns the expected verdicts and Holm-adjusted p-values.

Slow and manual checks:

- **AC-8 Calibration (T6):** on pilot seeds 1000-1009, `delta` is the smallest (strictest) of (0.3, 0.4, 0.5, 0.6) that `none` at N = 16 reaches in at least 25% of move periods, so H1 is neither all-censored nor trivial (seeds 1000-1002 gave 0.5: reached in 42% of periods, 0.4 in 13%); recorded in the README; then `PREREG` is committed.
- **AC-9 Main grid:** with `--flags slow`, the main grid runs in under 10 minutes and writes its outputs; the report lists the three confirmatory verdicts. Findings are reported, not asserted.
- **AC-10 Sweeps and studies:** with `--flags sweeps`, B9 to B11 run and write their outputs; the report shows the team-optimal `cUCB` per channel and size, the reward-scheme comparison and the study B learning curves with the share of the gap to the team optimum closed.
- **AC-11 Everything else:** all tests pass; module line counts under 200; no new dependencies.

## Out of scope

- Bad agents, defences and the H3 run: Phase 9 (only its definition is here).
- Language-model agents, prompt framing and notes files: Phase 10.
- Changing `banditAgent`'s arithmetic for speed.
- Crossing side-sweep factors with each other; confirmatory claims from side sweeps or studies.
- Learning the report weight `w` (trust) across episodes: Phase 9 trust weighting.
