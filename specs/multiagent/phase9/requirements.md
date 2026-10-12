# Requirements: Phase 9, safety and mechanism design

Terms used below.

- **Bad agent**: a liar, free-rider or saboteur (decision C1). **Bad slots**: agent indices `0 .. b-1`; **honest agents**: the others.
- **Clean run**: the same seed, size, channel and defence with honest agents in the bad slots.
- **Honest welfare** `W_h`: harvest minus danger cost of honest agents, per honest agent-second. **Team welfare** `W_t`: the same over all agents (Phase 8's welfare per agent-second).
- **Relative loss**: `1 - W_h(attacked) / W_h(clean)`, paired as above.
- **Check**: a stay at a location for which other agents have a current report; it compares each such report with the rate the checker observed. **Incidental** checks happen during foraging; **deliberate** checks are spot-check trips (rate `q`).
- **Trust** `tau_i[s]`: what agent `i` thinks of sender `s` (private). **Reputation** `rho[s]`: the shared record. **Strike**: a check whose error exceeds `theta`. **Sanction level**: the number of a sender's strikes in the last 120 s, capped at 3: 0 none, 1 warning, 2 half weight, 3 revoked.
- **Monitoring cost**: agent-seconds spent on deliberate check trips (travel and the checking stay), as a share of all agent-seconds.
- **White-box score**: how far an agent's reports are from its own beliefs. **Black-box score**: how badly others' checks rate it. **Detection AUC**: probability that a random liar scores above a random honest agent.
- **Pre-registration (`PREREG_H3`)**: the frozen definition of H3 (cells, statistic, seeds, alpha).

## Functional requirements

### Amendments to earlier phases
- **FR-1** `Blackboard` shall have `blocked` (a set, empty by default): writes by a blocked writer are dropped and counted as `rejected` in its `stats`. `Blackboard.viewBy(i, t, weights)` shall return the view with each writer's sums scaled by `weights[writer]` (running-sum mode only; `ValueError` otherwise), leaving out writer `i`.
- **FR-2** `MessageBus` shall have `blocked`: `send` from a blocked sender delivers nothing and counts as `rejected`.
- **FR-3** `bench_grid.runGrid(cells, workers, run=runCell)` shall run cells with the given (importable) runner; `confirm` shall select rows with `study == prereg.get('study', 'main')`. Phase 8's `PREREG`, its hash and its results shall not change.

### Bad agents (`explRL/adversary.py`)
- **FR-4** `Liar(channel, ...)` (a `CommBandit`) shall learn from its own stays like an honest agent and report, for each stay, `-dangerCost` if it harvested and `c` otherwise (blackboard and lead); with messages it shall send, when due, its lowest own-estimate location with value `c`.
- **FR-5** `FreeRider(channel, ...)` shall choose, among locations whose reported value (others' reports only) is positive, the one with the highest combined estimate (no exploration bonus), stay put if there is none, and never write or send. `Saboteur(channel, ...)` shall always go to the location with the highest reported value and never write or send.
- **FR-6** `LeadLiar`, `LeadFreeRider`, `LeadSaboteur` (`LeadFollower` variants) shall report the liar's lie, follow assignments without reporting, and go to the location with the most assigned followers, respectively.
- **FR-7** `makeTeam9(cfg, N, seed, channel, monitor)` shall build the team: bad slots `0 .. nBad-1` of `cfg.kind`, honest `DefendedBandit`s elsewhere (`LeadFollower`s and lead variants for `hierarchical`), with check generators `spawnRngs(seed + 3000, N)`. An unknown kind, or a defence or `q > 0` on the `none` or `hierarchical` channel, raises `ValueError`.

### Defences (`explRL/defence.py`)
- **FR-8** `DefendedBandit(channel, defence, monitor, q, rng, ...)` shall extend `CommBandit`. With `defence = 'none'` and `q = 0` its choices shall equal `CommBandit`'s. Otherwise it reads reports with per-sender weights (`tau` for `'trust'`, the monitor's weights for `'reputation'` and `'sanctions'`), runs a check after each own stay, and makes a deliberate check trip with probability `q` per event (C5). It creates its trust, message store, last-stay times and observation store before its first decision, since a spot check can come first.
- **FR-9** `Monitor(n, sanctions, theta, window, alpha, sigma, channel)` shall keep `rho[s]` and the times of each sender's strikes, update them from `record(s, error, t)`, give `weights(t)` (`rho` times 1, 1, 0.5 or 0 by sanction level when sanctions are on) and keep the channel's `blocked` set equal to the senders at level 3.
- **FR-10** Liars and honest `DefendedBandit`s shall log their reports as `(location, value, own belief, t)` for the white-box score (one shared helper in `adversary.py`); logging never changes a choice.

### Runs and metrics (`explRL/safety_runs.py`, `explRL/safety_grid.py`)
- **FR-11** `SafetyConfig` shall extend the Phase 7 configuration with `kind`, `nBad`, `defence`, `q`, `theta`; it shall round-trip through a plain dict. `runSafety(cfg, N, seed)` shall build the benchmark world, channel, monitor and team, run it for `worldTime(N, cfg)` and return world, history, channel and a flat row (FR-12). With `nBad = 0`, `defence = 'none'` and `q = 0` its history shall equal `runHarness`'s.
- **FR-12** The row shall hold the run's keys (seed, size, run time and the configuration's channel, budget, kind, number of bad agents, defence, `q`, `theta`; the grid runner adds `study`, `factor` and `level`), `W_h`, `W_t`, the number of events, discoveries and the free-riding index (Phase 8 functions), monitoring cost and check counts, sanctions (bad and honest agents ever at level 2 and at level 3, time of the first revocation of a bad agent), white-box and black-box detection AUC (liar runs), mean trust or reputation of bad and of honest agents at the end.
- **FR-13** `safety_grid.attackGrid(mode)`, `defenceGrid(mode)`, `monitorGrid(mode)` and `h3Grid(mode)` shall return cells, with `factor` = the grid and `level` = kind, number of bad agents, defence and `q` (decisions C1-C9 and C14, design-low-level section 5); `safety_runs.lossRows(rows)` shall pair each attacked row with its clean row (same study, channel, defence, `q`, size, seed) and return rows with the relative loss; a defence's cost without attack is its clean `W_h` relative to the attack grid's clean, undefended run on the same seed, channel and size.
- **FR-14** `safety_grid.PREREG_H3` shall be a constant; `confirm(lossRows(rows), PREREG_H3)` shall give H3's mean, CI, dz, p and verdict.

### Report and demo
- **FR-15** `explRL/safety_report.py` and `explRL/safety_figures.py` shall summarise the rows (honest and team welfare vs number of bad agents per channel, kind and defence; defence cost without attack; monitoring cost vs benefit; detection AUC; the Phase 8 free-riding index in free-rider runs, as a check of that metric; H3) and write `report.md` and figures.
- **FR-16** `nbs/demo_safety.ipynb` shall run a quick grid in normal tests, H3 with `--flags slow`, and the exploratory grids with `--flags sweeps` (long modes with `--cell-timeout 0`), writing `runs.csv`, `metrics.json`, `report.md` and figures under `results/multiagent/safety/{quick,h3,full}/`.

## Pre-registered analysis (frozen in T7)

| Test | Contrast (paired over seeds 300-329) | Cells | Statistic per seed | Expected sign |
|---|---|---|---|---|
| H3 | blackboard minus messages | fixed compute, no defence, sizes 8, 16, 32; one liar (slot 0) vs clean | mean over sizes of relative honest-welfare loss | + |

Two-sided sign-flip test with 10 000 flips, alpha 0.05, a family of one; 95% bootstrap CI and `cohenDz` reported. Nothing else in Phase 9 is confirmatory.

## Quality requirements

- **NFR-1 Exactness:** Phase 5 golden fixtures, the paper-demo hashes, the Phase 6 `demo_team` hashes, the Phase 7 `demo_harness` hashes recorded after Phase 8, and Phase 8's quick `runs.csv` stay identical.
- **NFR-2 Speed:** quick grid under 30 s in normal tests; H3 under 5 minutes; exploratory grids under 30 minutes on 8 processes. Measured times are recorded.
- **NFR-3 Determinism:** a cell's row depends only on the cell; the CSV is byte-identical for 1 and 4 workers. Deliberate checks use generators `spawnRngs(seed + 3000, N)`, so they do not change the world's or members' other draws.
- **NFR-4 Size, style, dependencies:** each new module under 200 lines; nbdev notebooks with tests; no new dependencies.
- **NFR-5 Integrity:** H3's seeds are run once, after `PREREG_H3` is committed; any later change is reported as a deviation.

## Acceptance criteria

Normal tests (`nbdev-test --n-workers 0`):

- **AC-1 Regression and bridge:** NFR-1 holds; `runSafety` with no bad agents, no defence and `q = 0` (honest `DefendedBandit`s) gives `runHarness`'s history (blackboard, messages, hierarchical, none; seeds 0-2).
- **AC-2 Channels:** a blocked writer's blackboard writes and messages are dropped and counted; `viewBy` with all weights 1 equals `view`, and with one weight 0 equals the view without that writer.
- **AC-3 Bad agents:** on hand-built worlds, a liar writes `-dangerCost` after harvesting and `c` after an empty or danger stay, and its own estimates stay honest; a free-rider never visits an unreported location and never writes; a saboteur goes to the top reported location; the lead variants report, stay silent and crowd as specified.
- **AC-4 Defences:** one trust update matches the formula; a sender whose reports are always wrong loses weight; with sanctions, three quick strikes revoke a sender, the channel then drops its writes, and once its strikes leave the 120 s window it is reinstated; deliberate check trips happen, never more often than `q` per event, and their agent-seconds and checks are counted.
- **AC-5 Metrics:** honest and team welfare on a hand-built ledger; relative loss pairs the right rows; AUC is 1 for perfectly separated scores, 0.5 for equal scores; the white-box score is 0 for an agent that reports its own beliefs.
- **AC-6 Grid:** cell counts per grid; quick grid under 30 s; CSV identical for 1 and 4 workers; `confirm` on synthetic loss rows gives the expected verdict.

Slow and manual checks:

- **AC-7 Calibration (T7):** `theta` chosen by the C11 rule on pilot seeds and recorded with the false-sanction rates (done: 2.5); `PREREG_H3` committed.
- **AC-8 H3 (T9):** run once with `--flags slow`; verdict, mean, CI and per-size losses recorded in the README whatever they are.
- **AC-9 Exploratory grids (T10):** run with `--flags sweeps`; the report shows welfare vs number of bad agents per channel, kind and defence, defence cost without attack, monitoring cost vs benefit at equal `q`, and detection AUC; findings reported, not asserted.
- **AC-10 Everything else:** all tests pass; module line counts under 200; no new dependencies.

## Out of scope

- Defences for the hierarchical lead; bad circuit agents and circuit belief readout (Phase 8 found that channels do not help circuit teams, so there is little for an attack to break).
- Adaptive or colluding adversaries (liars that learn to evade checks, coordinated groups), and bad agents that change type during a run.
- Learning the report weight `w` other than through trust; persistence of trust across episodes (a possible extension of Phase 8 study B).
- Language-model agents: Phase 10 reuses the bad-agent roles as prompts.
