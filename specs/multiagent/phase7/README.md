# Spec: Phase 7, harness configurations (communication and memory)

Status: **implemented** (2026-10-11). All tests and both demo runs pass, and the harness check (AC-11) passes on the benchmark world chosen in attempt 3 (see the attempt log below), so Phase 8 can start. Part of the multi-agent plan: [../README.md](../README.md). Builds on Phase 6: [../phase6/README.md](../phase6/README.md). How to run: [RUN.md](RUN.md).

## Goal

Give the team ways to share what it learns, and make every sharing setting a knob that the Phase 8 benchmark can turn. Phase 6 built a world where agents affect each other only through crowding; each agent learns alone. Phase 7 adds the **harness**: the communication channel, how agents read it, how long information is kept, and how much compute a team gets.

1. **Four channels**, one per team: `none`; `blackboard` (a shared value map per location that fades over time, a form of stigmergy); `messages` (each agent sends a few short reports per period to agents within a communication range); `hierarchical` (a lead collects reports and assigns agents to locations, taking crowding into account; a simple greedy baseline).
2. **Reading the channel:** a `banditAgent` treats reports as extra observations with a weight `w` (1 = as good as its own); the circuit agent turns a report into extra reward-gated goal updates toward the reported heading.
3. **Memory:** how many entries are kept per location, for an agent's own experience, its stored reports and the blackboard.
4. **Evaporation:** blackboard entries lose weight with age at a set rate (0 = never).
5. **Two compute budgets:** fixed compute (total agent-seconds `N x T` held constant) and fixed world time (every team runs the same `T`).
6. **One run function** that builds a team from a configuration, runs it on the benchmark world and returns its history, ledger, channel statistics and metrics, for team sizes 1 to 64. Phase 8 builds its grid on it.

Phase 7 adds no new reward schemes, no bad agents (Phase 9) and no statistics beyond what the demo needs (Phase 8).

**Main acceptance tests:** (a) with no channel, or with report weight 0, the new agents give exactly the Phase 6 histories (bandit and circuit), and the Phase 6 demo metrics are unchanged; (b) each channel matches hand-checked examples (fading, range, message limits, the lead's greedy assignment); (c) the dynamic-range check from Phase 6 passes on the real harness with the real channels, which gates Phase 8.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions and rejected alternatives, risks |
| [design-low-level.md](design-low-level.md) | Classes, signatures, formulas (estimates, fading, message timing, lead assignment, budgets), defaults, demo layout |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks |
| [RUN.md](RUN.md) | How to run the tests, the demo and the regression checks |

## What Phase 6 gives us (the facts the design depends on)

| Piece | Fact | Consequence for Phase 7 |
|---|---|---|
| `TeamPatchWorld` | Generic world protocol with `apply(i, target, t)`; `neighbours(i, radius)` by layout distance; stays claim harvest at their start; `info` holds `harvest`, `observed`, `nHere`, `dur` | Channels need no world change: members write after `apply` returns and read before acting. The communication range uses `neighbours` |
| `banditAgent` | Per-location window of the last `K` stay reward rates; UCB score discounted by travel time; unvisited locations first; draws no random numbers | Reports enter the same estimate as weighted extra observations; with weight 0 the arithmetic must be exactly Phase 6's (a small refactor exposes the estimate) |
| `CircuitPatchMember` | Learns from the sign of its own net harvest through `CircuitMember.reward`; goal learning is `goalStep(wG, c, R, p)` at its compass heading `c`; `world.loc` is not updated for it | A report at world location `j` maps to the internal heading `c + (j - a)`; `fixate` must set `world.loc` (and the run sets it before the first fixation) for the communication range to work |
| `runTeam` / `Clock` | Events in start-time order; members stop once their start time reaches `t0 + Ttot` | Fixed compute is just a shorter `Ttot` for larger teams; channels see non-decreasing times |
| Phase 6 findings | Bandits nearly saturate the default world at 64 agents (about 94% of the social optimum over 600 s) | The harness check must confirm there is still room for channels to matter; difficulty is tuned in a separate benchmark-world configuration, not by changing Phase 6 defaults |
| Phase 6 T1 prototype | Simplified channels separated harnesses in a synchronous world | The real channels differ (fading mean instead of latest value, real message timing, a lead), so the check is re-run on the package harness |

## Decisions

| ID | Question | Answer |
|----|----------|--------|
| H1 | Where does the channel live | **Recommended: a shared channel object outside the world**, passed to every member of the team. Members read it before acting and write after `apply` returns. The world does not change, so Phase 6 results cannot change. External agents (Phase 10) can call the same channel methods |
| H2 | How a `banditAgent` uses reports (plan Q8) | **Recommended: weighted pseudo-observations.** Estimate per location = (own sum + `w` x report sum) / (own count + `w` x report count). Messages are stored when received (each is a one-time event). The blackboard is read as a view at act time and never copied into the agent, and the agent's own entries are left out of its view, so nothing is counted twice. `w = 0` gives exactly Phase 6 |
| H3 | What agents write and send | **Recommended: only their own experience.** Each stay writes its reward rate (reward / duration) to the blackboard or the lead. A message carries the sender's best location by its own estimate (own stays only), never a relayed report, so information cannot echo around the team. Phase 9 liars break this rule on purpose |
| H4 | Evaporation | **Recommended: an entry's weight is `exp(-lam x age)`**, applied at read time. `lam = 0` never fades. The same fading applies to the lead's table. With full memory the blackboard keeps running faded sums, so reads stay cheap however long the run |
| H5 | Memory | **Recommended: a per-location window `K`** (the last `K` entries) for the agent's own stays (Phase 6 S7), its stored message reports, and the blackboard. `K = None` keeps everything; the plan's "no memory" setting is `K = 1` (only the latest entry per location). The circuit agent's memory is its weights; `K` does not apply to it |
| H6 | Message timing and range | **Recommended: per-agent periods.** An agent may send once per window `[m period, (m + 1) period)`, at its first stay (fixation, for circuit members) in that window; it sends to `k` recipients drawn uniformly from the agents within `radius` (excluding itself), using its own seeded generator. A message is delivered at once and used from the recipient's next event |
| H7 | The hierarchical lead | **Recommended: a coordinator object, not a forager.** It earns nothing, uses no agent-seconds and ignores the communication range. Followers report each stay (reward rate and how many agents shared the patch); the lead estimates each location's total rate and assigns each follower, at each of its events, by a greedy crowding-aware score with an exploration bonus. Labelled as a baseline (plan: no hand-coded rules presented as findings) |
| H8 | How the circuit agent uses reports (plan Q8) | **Recommended: each report becomes `w` extra goal-learning steps** at the internal heading that matches the reported location from where the agent stands (`c + (j - a)`), with `R = sign(value)`. From the blackboard it reads one report per event: the best location in its view. It writes and sends like a bandit. It does not join `hierarchical` (it cannot follow an assignment with its native saccades) |
| H9 | Compute budgets (plan Q5) | **Recommended: agent-seconds.** Fixed compute: `T = B / N` with `B = 64 x 240 = 15 360` agent-seconds, so every run has about the same number of events and the 64-agent team still sees patch moves (sized for two moves at the Phase 6 `Tmove` of 120 s; the benchmark world's 40 s gives five). Fixed world time: `T = 600 s` |
| H10 | The benchmark world | **Recommended: a `benchWorld()` configuration** in the harness module, starting from the Phase 6 defaults (ring, fixed intake) and changed because the harness check (AC-11) needed it. Attempt 3 (adopted): a 64-location ring with travel scale 0.48, **16 patches** with intake (0.8, 1.6, 2.4, 3.2) repeated four times (total 32, so the social optimum keeps rising up to 64 agents), 8 danger sites, random sites per seed, `Tmove` 40 s, harvest noise 0.45, `dangerCost` 2.6, `c` 0.85. `L` and `travelScale` are plain overrides so configurations stay JSON. Phase 6 defaults and results stay as they are |

Defaults that were marked *(check)* (`B`, `benchWorld()`) were fixed by the harness check (AC-11, attempt 3); the low-level design lists them.

### Harness check (AC-11, 2026-10-11)

Check (1) uses each channel's first-quarter team rate averaged over seeds, as the Phase 6 prototype and demo did; (2) and (3) use the whole-run team rate (team harvest per second). Attempts 1 and 2 were first scored with a per-seed ceiling and per-agent rates, which did not match that definition; both were re-scored after the fix. Every row: 10 seeds, team sizes 1/4/16/64, 600 s, the four channels and `randomAgent`.

| Attempt | `benchWorld()` settings | ceiling | floor | gap | Notes |
|---------|------------------------|---------|-------|-----|-------|
| 1 | Phase 6 ring defaults (32 locations, 4 patches, travel scale 0.1, `Tmove` 120 s, intake 0.5–2, no noise, random sites) | fail | pass | pass | ceiling failures (first-quarter / SO): hierarchical N=16 0.92; blackboard N=64 1.03; hierarchical N=64 1.04 |
| 2 | 32 locations, 4 patches, travel scale 0.48, `Tmove` 40 s, intake 0.4–1.6 (total 4), noise 0.45, `dangerCost` 2.6, `c` 0.85, fixed sites | fail | pass | pass | blackboard N=64 0.905 (limit below 0.90). Cause: the social optimum is capped at the total intake of 4, reached with only 6 agents, so a big team saturates at once |
| **3 (adopted)** | as 2, but **64 locations, 16 patches, intake ×2 (total 32)**, 8 danger sites, random sites | **pass** | pass | pass | highest first-quarter / SO: blackboard N=64 0.52. Gap (team harvest/s, mean [95% CI]): N=1 0.20 [0.18, 0.22]; N=4 0.36 [0.32, 0.39]; N=16 2.99 [2.90, 3.08]; N=64 3.65 [3.34, 3.93] |

Larger maps were also tried (exploratory, not adopted); all pass, but small teams earn little:

| World | ceiling (max first-quarter / SO) | floor | gap | N=1 / N=4 first-quarter / SO |
|---|---|---|---|---|
| attempt 3 capacity, 128 locations | pass (0.44) | pass | pass | 0.08 / 0.08–0.09 |
| attempt 3 capacity, 256 locations | pass (0.24) | pass | pass (gap CI at N=1 includes 0) | 0.04 / 0.03–0.04 |
| attempt 2 capacity (4 patches), 128 locations | pass (0.64) | pass | pass | 0.02 / 0.02 |
| attempt 2 capacity (4 patches), 256 locations | pass (0.34) | pass | pass | 0.01 / 0.01 |

**Re-run on net welfare (2026-10-11):** after welfare started charging the danger cost (see Terms in [requirements.md](requirements.md)), attempt 3 still passes all three checks: highest first-quarter / SO is blackboard N=64 at 0.51; gap N=1 0.26 [0.24, 0.28], N=4 0.36 [0.32, 0.39], N=16 3.32 [3.22, 3.42], N=64 5.08 [4.72, 5.42]. Independent bandits (`none`, `messages`) earn about 0 net in the first quarter, because exploring unvisited locations includes the danger sites.

Attempt 3 was adopted because it passes with every gap CI above 0, keeps small teams learning (18-25% of the optimum in the first quarter), makes large teams spread over many patches (the ideal free distribution matters at every size) and is the cheapest to run. The bigger maps mostly reward having more searchers.

Channel findings on the adopted world (welfare net of danger cost, team rate per second, seed means of the net re-run): the blackboard is best from N = 4 (N=16: 7.39 vs 4.20 for `none`; N=64: 17.7 vs 13.0); `messages` stays at or slightly below `none` at every size; the lead is far worst at N = 1 (0.01 vs 0.28: a single follower keeps being sent to unknown locations, danger sites included). Full demo (8 bandits, 600 s, 10 seeds; welfare per agent-second): blackboard 0.391, `none` 0.274, lead 0.272, `messages` 0.256. Evaporation: λ = 0 gives 0.447, the default 0.01 gives 0.391 and 0.1 gives 0.060, so with 16 patches slow fading does not pay off within 600 s; Phase 8's evaporation sweep tests this. Fixed compute at 64 agents (240 s each): `none` 0.067 per agent-second vs blackboard 0.266, because a short run is dominated by the early exploration that the danger cost now charges. **Time to the ideal free distribution** (within 0.2, Phase 6 `timeToIFD`) is undefined for every channel: no team gets that close between 40 s moves, so Phase 8's first hypothesis test needs a censoring rule or another threshold.

**Correction from Phase 8 (2026-10-11):** the benchmark world's patches come in four groups of equal intake, so the ideal free distribution is not unique, and the Phase 6 distance (one fixed allocation) overstated the distance for small teams (N = 4: 0.90 instead of 0.64). `harnessMetrics` and the demo's IFD series now use the tie-invariant distance (`team_refs.ifdDistanceTies`). Re-running `demo_harness` against the Phase 7 baseline (`results/multiagent/baseline_phase7`) changes exactly one field: blackboard with `lam = 0` now has a defined time to IFD (25 s, was undefined); the quick run is unchanged. Phase 8 replaces time to IFD with a censored recovery time (Phase 8 decision B5).

**Measured (AC-10, adopted benchmark world, 64 agents, 600 s):** blackboard 1.6 s (39k events, 42 µs/event); `messages` 2.1 s (50 µs/event); `hierarchical` 0.8 s (23 µs/event); `none` 5.1 s (122 µs/event, the Phase 6 `banditAgent` recomputes each location's mean over its full history at every event, which grows with 64 locations). **Q5 / H9:** agent-seconds; `B = 15 360` (the 64-agent team sees five moves). **Q8 / H2, H8:** as in the table above.
