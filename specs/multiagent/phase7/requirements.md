# Requirements: Phase 7, harness configurations

Terms used below.

- **Harness**: everything around an agent's learning rule that the benchmark varies: the channel, how reports are read (`w`), memory (`K`), evaporation (`lam`), communication range and compute budget.
- **Channel**: the one shared means of communication of a team: `none`, `blackboard`, `messages` or `hierarchical`.
- **Report**: one piece of shared information: a location and a value (a reward rate, in reward per second), with the time it was made and who made it.
- **Entry**: a report stored on the blackboard or in the lead's table.
- **View**: what one agent reads from the blackboard at time `t`: for each location, the faded sum of the other agents' entry values and their faded total weight.
- **Report weight `w`**: how much one report counts compared with one of the agent's own stays (1 = the same, 0 = ignored).
- **Memory `K`**: the number of most recent entries kept per location (`None` = all).
- **Evaporation rate `lam`**: entries lose weight as `exp(-lam x age)`, age in seconds.
- **Communication range `radius`**: messages reach only agents within this layout distance (`inf` = everyone).
- **Agent-seconds**: team size times world time, `N x T`; the compute unit (plan Q5).
- **Welfare**: the team's true harvest minus `dangerCost` x the time its agents spent at danger locations (`netHarvest`). Phase 6 counted harvest only; Phase 7 on charges danger, so a team that wanders into danger loses welfare. Phase 6's `welfare()` and its demo are unchanged.
- **Fixed compute**: `N x T = B` held constant across team sizes. **Fixed world time**: `T` held constant.
- **Benchmark world**: the `TeamPatchWorld` configuration the harness runs use (`benchWorld()`).

## Functional requirements

### Channels (`explRL/harness.py`)
- **FR-1** A channel shall be an object shared by all members of a team and created with the team. `none` is represented by `None`. Channels shall not change the world, its generators or its ledger.
- **FR-2** `Blackboard(L, K=None, lam=0.0, n=None)` (`n` = team size, needed when `K = None`) shall provide `write(i, loc, value, t)` (add an entry; with `K` set, only the last `K` per location count) and `view(i, t) -> (S, C)`: for each location, the sum of `value x exp(-lam (t - t_e))` and of `exp(-lam (t - t_e))` over the counted entries written by agents other than `i` (`i = -1`: all agents), with both set to 0 where `C < 1e-12`. With `K = None` every entry counts, and the cost of a read shall not grow with the number of entries. Calls come with non-decreasing `t`; an earlier `t` raises `ValueError`.
- **FR-3** `MessageBus(n, k=2, period=10.0, radius=inf, rngs)` shall provide `due(i, t)` (true at the agent's first call in each window `[m period, (m + 1) period)`, false at later calls in the same window), `send(world, i, loc, value, t)` (deliver one report to each of `min(k, m)` recipients drawn uniformly without replacement from the `m` agents returned by `world.neighbours(i, radius)`, using generator `rngs[i]`), and `take(i)` (return and clear the reports delivered to `i`, oldest first).
- **FR-4** `Lead(L, n, K=None, lam=0.01, cUCB=1.0, H=10.0)` shall keep its table as a blackboard with the same `K` and `lam`, and provide `report(i, loc, value, nHere, t)` (store an entry with the location's estimated total rate `value x max(nHere, 1)`) and `assign(i, loc, travel, t) -> target`: choose the nearest unknown location (view weight 0: no entries, or all faded below 1e-12; ties to the lower index) while any exists; otherwise the location with the highest score `(Ihat_j / (a_j + 1) + cUCB x sqrt(ln(1 + n_total) / n_j)) x H / (H + travel_j)` (ties to the lower index), where `Ihat_j` is the faded mean of the entries at `j`, `n_j` their faded weight, `n_total` the sum over locations, and `a_j` the number of other followers currently assigned to `j`. It shall remember each follower's current assignment.
- **FR-5** Every channel shall count, per agent, the reports it wrote, sent and received (`stats`), for the Phase 8 communication-cost metric.

### Members (`explRL/harness_agents.py`)
- **FR-6** `banditAgent` (Phase 6) shall compute its per-location estimate through one helper that returns `(mean, n)`; `act` shall use it. `CircuitPatchMember.reward` shall keep the net harvest it computes. Behaviour and the Phase 6 results shall not change.
- **FR-7** `CommBandit(channel=None, w=1.0, K=None, cUCB=1.0, H=10.0)` shall extend `banditAgent`. At each event, before choosing, it shall add the reports from `take` (messages) to a per-location store of the last `K` report values, and read the blackboard `view` at the event time. Its estimate per location shall be `mean_j = (S_own + w (S_rep + S_view)) / n_j` with `n_j = n_own + w (n_rep + C_view)` (0 where `n_j = 0`), and it shall use `n_j` wherever `banditAgent` uses its stay count (unvisited test, UCB bonus, total count). After a stay it shall write its reward rate to the blackboard, and if `due`, send its best location by its own estimate (own stays only; nothing if it has none). Reads and writes use the event start time. `w` scales only what the agent reads: a member with `w = 0` still writes and sends (Phase 9's free-rider is the opposite case). `estimates(t)` shall return `(mean, n)` with the blackboard read at `t`.
- **FR-8** With `channel = None`, or with any channel and `w = 0`, `CommBandit` shall choose exactly as `banditAgent` with the same `K`, `cUCB` and `H`.
- **FR-9** `LeadFollower(lead)` shall be a `PatchMember` whose target is `lead.assign(...)` and which reports every stay (`value` = reward / duration, `nHere` from `info`) to the lead.
- **FR-10** `CircuitCommMember(agent, channel=None, w=1)` shall extend `CircuitPatchMember`. After its own goal update, for each report taken (messages) and for the best location of its blackboard view (highest `S / C` among locations with `C > 0`, if any), it shall apply `w` calls of `goalStep(wG, (c + j - a) mod N, sign(value), p)` when `rl.learnG` and `value != 0`. It shall write its fixation's net rate (net / fixation length) to the blackboard at the event start time and send its best visited location by its own net rates when `due`. With `channel = None` or `w = 0` its history shall equal `CircuitPatchMember`'s. It shall not accept a `Lead`.
- **FR-11** `TeamPatchWorld.fixate` shall set the circuit member's location (`loc[i] = a`) so that `neighbours` works for circuit members. Nothing else in Phase 6 changes.

### Runs (`explRL/harness_runs.py`)
- **FR-12** `HarnessConfig` shall hold the channel name, `w`, `K`, `lam`, `k`, `period`, `radius`, the agent type (`'bandit'`, `'circuit'`, `'random'`), the budget (`'compute'` or `'time'`) with `B` and `T`, `cUCB` and `H` (bandit and lead), and the world settings; it shall convert to and from a plain dict for `metrics.json`.
- **FR-13** `benchWorld(**overrides)` shall build the benchmark `TeamPatchWorld` (Phase 6 defaults on the ring unless AC-11 changes them; the settings in use, from AC-11 attempt 3, are in design-low-level section 7; `L` and `travelScale` overrides rebuild the ring layout, so every override is a plain value), and `circuitWorld(**overrides)` the ring world for circuit teams (`zoneConfig(symmetric=False, intake=1.0)` by default).
- **FR-14** `worldTime(N, cfg)` shall return `cfg.B / N` for fixed compute and `cfg.T` for fixed world time. `N < 1` or a budget that is not positive shall raise `ValueError`.
- **FR-15** `runHarness(cfg, N, seed)` shall build the world (reset with `seed`), the channel (none for a random team) and `N` members (member generators from `spawnRngs(seed + 1000, N)`, message generators from `spawnRngs(seed + 2000, N)`; circuit members' world locations set to their headings before the run), run them with `runTeam` for `worldTime(N, cfg)`, and return the world, the history, the channel and a metrics dict: the configuration, welfare (net of danger cost) total and per agent-second, gross harvest and danger cost, first-quarter team rate (net), Gini, agent-seconds used, channel `stats` totals and per agent-second (present for every channel, zeros for `none`); for generic agents also coverage, danger share, mean IFD distance, time to IFD after each move, SO yield and welfare loss (Phase 6 metrics; occupancy metrics use stay rows, so they are left out for circuit teams); and final estimates for the Phase 8 belief-diversity metric (bandits: `(mean, n)` read at the run's end; circuit: goal heading and strength).
- **FR-16** `rangeCheck(cfgs, sizes, seeds, ...)` shall run the Phase 6 dynamic-range checks (1)-(3) on the package harness with the given channel configurations and `randomAgent`, and return the pass flags and the per-size numbers. As in the Phase 6 prototype and demo, check (1) uses each channel's mean over seeds. All configurations share one world (the first configuration's `world` overrides), and the random team and the social optimum use that world too.

### Demo
- **FR-17** `nbs/demo_harness.ipynb` shall show: the four channels on the benchmark world with 8 bandits (welfare rate and IFD distance over time, move times marked, time to IFD, communication cost); an evaporation example (blackboard, `lam` = 0, 0.01, 0.1); circuit teams with `none`, `blackboard` and `messages`; and in the full run, the harness check (AC-11) and scaling previews under both budgets for team sizes 1 to 64. It shall save its figures, `metrics.json` and a plain-language `report.md` under `results/multiagent/demo_harness/{quick,full}/`.

## Quality requirements

- **NFR-1 Exactness:** Phase 5 golden fixtures, the six paper-demo hashes and the Phase 6 `demo_team` `metrics.json` hashes (quick and full) stay identical.
- **NFR-2 Speed:** quick demo under 15 s; full demo under 20 min; a 64-agent `CommBandit` team with a blackboard (`K = None`) for 600 s under 30 s; the cost per event is measured and recorded, because the Phase 8 main grid (about 1 700 runs of about 10 000 events each) depends on it.
- **NFR-3 Size and style:** each new module under 200 lines; nbdev notebooks with tests; naming as in the existing code.
- **NFR-4 Dependencies:** none added.
- **NFR-5 Determinism:** the same configuration and seed give the same history, ledger and channel statistics. Message recipients use their own generators, so turning messages on does not change the world's draws or the members' other draws.

## Acceptance criteria

Normal tests (`nbdev-test --n-workers 0`):

- **AC-1 Phase 6 bridge (bandit):** on the benchmark world with 8 agents, seeds 0-2, 300 s, `CommBandit` with `channel = None`, and with a blackboard or messages and `w = 0`, gives the same history and ledger as `banditAgent`; the Phase 6 tests pass; the Phase 6 `demo_team` metrics hashes are unchanged.
- **AC-2 Phase 6 bridge (circuit):** with `channel = None`, and with a blackboard and `w = 0`, `CircuitCommMember` gives the same history as `CircuitPatchMember` (both scenes, seeds 0-2, 300 s); Phase 6 AC-1 still passes after the `fixate` change.
- **AC-3 Blackboard:** hand-built entries give the expected `view` sums; an agent's own entries are left out; with `lam > 0` an entry's weight halves after `ln 2 / lam` seconds (to 1e-12); `lam = 0` never fades; `K` counts only the last `K` entries per location; with `K = None`, 1 000 writes all count, and the view equals the windowed mode's view with `K = 1000` for the same writes (both modes, `lam` = 0 and 0.05); weights below 1e-12 read as 0; a call with an earlier `t` raises `ValueError`.
- **AC-4 Messages:** a sender is `due` at most once per period and sends to at most `k` recipients; recipients are within `radius` (radius 0: only agents at the same location; `inf`: anyone but the sender); `take` returns delivered reports once, oldest first; a message carries the sender's own best estimate even when it holds better reports; recipients repeat with the same seed and the world's patch sites do not change when messages are on.
- **AC-5 Lead:** with entries giving estimated totals (2, 1) at two locations, every other location known to pay 0, no travel difference and `cUCB = 0`, three followers asked in turn are assigned (0, 0, 1), which equals `idealFree` for intakes (2, 1) and `c` large; while some location has no entries, a follower is sent to the nearest such location; a follower's own previous assignment is not counted against it.
- **AC-6 Estimates:** hand-checked `(mean, n)` with own stays, stored reports and a blackboard view at `w = 0.5`; a location known only from reports counts as visited; `K` limits own stays and stored reports separately.
- **AC-7 Circuit reports:** one positive report at location `j` changes the goal weights exactly as `w` direct `goalStep` calls at heading `(c + j - a) mod N` with `R = +1`; a negative report as with `R = -1`; no change when `rl.learnG` is false.
- **AC-8 Budgets:** fixed compute gives `T = B / N` and fixed world time gives `T`; the metrics' agent-seconds equal `N x T`; no member starts an event at or after `T`; bad `N` or budgets raise `ValueError`.
- **AC-9 Determinism and export:** the same configuration and seed give identical histories, ledgers and channel statistics for each channel; `toJSONL` works; `HarnessConfig` round-trips through a dict.
- **AC-10 Speed:** the NFR-2 timing passes, with the measured time per event recorded in the README.

Slow and manual checks:

- **AC-11 Harness check (gate for Phase 8):** `rangeCheck` on the benchmark world, fixed world time 600 s, team sizes {1, 4, 16, 64}, 10 seeds, `CommBandit` with the four channels at their defaults (`hierarchical` through `LeadFollower`) and `randomAgent`: checks (1) no ceiling, (2) no floor and (3) a channel gap, as defined in Phase 6 design-low-level section 10 and implemented in its prototype (team harvest per second; check (1) on the mean over seeds), with the four channels as the harnesses. If it fails, the benchmark-world settings (not the Phase 6 defaults) are changed and the check rerun; every attempt is recorded in the README, and the *(check)* defaults are fixed by the passing attempt. If nothing passes after a few rounds, stop and review the plan before Phase 8.
- **AC-12 Demo:** `nbs/demo_harness.ipynb` runs in normal tests (quick) and with `--flags slow`, writing its figures, `metrics.json` and `report.md`; findings are reported, not asserted.
- **AC-13 Everything else:** all tests pass; the paper-demo and Phase 6 demo hashes are unchanged; module line counts under 200; no new dependencies.

## Out of scope

- The benchmark grid, confirmatory tests, Holm correction, belief diversity and herding metrics, free-riding index: Phase 8 (Phase 7 only exposes the estimates and channel statistics they need).
- Liars, free-riders, saboteurs, trust weighting, monitoring and sanctions: Phase 9.
- Relaying reports, learned communication, message content beyond (location, value), channel bandwidth limits beyond `k` per period.
- The circuit agent with the lead, or on the torus.
- Mixing channels within one team, or mixing agent types as an experiment (allowed by the code, tested only for determinism).
- Language-model agents and context management: Phase 10 (the channel methods are usable by external agents, so Phase 10 can reuse them).
