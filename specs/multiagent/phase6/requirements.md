# Requirements: Phase 6, team environment with incentives

Terms used below.

- **Location**: a place in the world, numbered `0..L-1`. On the ring, location `a` is grid heading `a` (`L = N = 32` by default). On the torus, location `y * side + x`.
- **Layout**: how locations are placed. It gives each location a position, the **travel-time matrix** `T[j, k]`, and the distance used by the **communication range**.
- **Patch**: a location with a resource. Each patch has an identity (`0..P-1`) that stays the same when the patch moves.
- **Danger location**: costs `dangerCost` reward per second spent there.
- **Stay**: an event in which an agent remains at its location for `tStay` seconds and claims harvest.
- **Travel**: an event in which an agent moves to another location; it lasts the travel time, earns nothing and occupies no location.
- **Claim**: the harvest an agent takes at the start of a stay (decision S3).
- **Occupancy** `n_p(t)`: the number of agents whose current stay at patch `p` covers time `t`.
- **Yield model** `E_p(n)`: total harvest rate of patch `p` in steady state with `n` agents on it, ignoring travel. Used by the team and difference rewards and by the references.
- **Ideal free distribution (IFD)**: an allocation of agents to patches (or "outside") in which no agent can raise its own payoff `E_p(n_p) / n_p` by moving alone.
- **Social optimum (SO)**: an allocation with the largest total yield `sum_p E_p(n_p)`.

## Functional requirements

### Layouts
- **FR-1** `ringLayout(N, travelScale)` and `torusLayout(side, travelScale)` shall return the positions, the distance matrix and the travel-time matrix. Ring travel time is `travelScale` times the circular step distance; torus travel time is `travelScale` times the Euclidean distance with wrap-around (S8). Matrices are symmetric with a zero diagonal.

### World
- **FR-2** `TeamPatchWorld(layout, ...)` shall hold the patches (site, model parameters, stock), the danger locations, each agent's location and current stay interval, and its own seeded generators (one each for site draws, patch moves and observation noise). It shall implement the generic world protocol `reset(seed, nAgents)`, `observe(i)` and `apply(i, action, t) -> (reward, dt, location, info)`, with time in seconds. `reset` draws the patch and danger sites (unless given) and then each generic agent's start location, uniformly; as in Phase 5, the caller runs `reset` before `runTeam`.
- **FR-3** An action is a target location `j`. If `j` is the agent's location, the event is a **stay** of `tStay` seconds; otherwise a **travel** of `T[loc, j]` seconds that ends at `j`. A target outside `0..L-1` raises `ValueError`.
- **FR-4** Patch models (S2): **fixed intake**: patch `p` offers `I_p` per second, and a claim takes `min(c, I_p / n) * dur`; **logistic stock**: stock `S_p` regrows as `dS/dt = g S (1 - S / K)` between calls (closed form), never drops below `Smin`, and a claim takes `min(c * dur, (S_p - Smin) / n)`, which is removed from the stock. Here `n` is 1 plus the number of other agents whose stay at `p` covers the claim's start time. Fixed intake with `I_p = inf` gives a constant claim `c * dur` (no crowding cost).
- **FR-5** Before handling any call at time `t`, the world shall advance to `t`: regrow stocks and apply every patch move at `k * Tmove <= t` in order (S9). Calls arrive with non-decreasing `t`; an earlier `t` raises `ValueError`.
- **FR-6** Rewards (S5), for stays. **Individual**: observed harvest (FR-7) minus `dangerCost * dur` at a danger location. **Team**: `(sum_p E_p(n_p(t)) - dangerCost * nDanger(t)) / nAgents * dur`, where `nDanger(t)` is the number of agents whose stay at a danger location covers `t`. **Difference**: `(E_p(n) - E_p(n - 1)) * dur` at patch `p` (`n` from the claim), `-dangerCost * dur` at a danger location, 0 elsewhere. Travel earns 0 under all schemes.
- **FR-7** Observations: `observe(i)` returns the agent's location, the row `T[loc, :]` of travel times (agents know the layout), and the reward and observed harvest of its last event. Observed harvest is the true claim times `max(0, 1 + noise * z)`, `z` standard normal from the world's generator (noise 0 by default). Agents do not see where patches are.
- **FR-8** `info` from `apply` shall hold `kind` (`'stay'` or `'travel'`), the true `harvest`, the observed harvest, `nHere` (the claim's `n`; 0 for travel or no patch), the patch identity or `None`, `danger` (bool) and `dur` (the event duration). The world keeps a **ledger**: one row per event with `(agent, t, dt, kind, location, patch, harvest, reward, s0, s1)`, where `[s0, s1)` is the stay interval (`nan` for travel).
- **FR-9** `neighbours(i, radius)` shall return the other generic agents within `radius` of agent `i` (layout distance between their locations; an agent in transit counts at its destination; `inf` = everyone). Phase 6 only provides it; Phase 7 uses it.
- **FR-10** On the ring, the world shall also offer the native methods the circuit agent uses: `ringActivity(a)` (asymmetric or symmetric scene, as `ZoneArena`), `valence(a)` (`+1` at a patch, `-1` at a danger location, `0` elsewhere), and `fixate(i, a, tStart, dur, t) -> (harvest, net)` for patch-aware circuit members (advance, claim, ledger row; `harvest` is the true claim, `net` the observed harvest minus any danger cost).
- **FR-11** `TeamPatchWorld.zoneConfig(symmetric=True, N=32, intake=inf)` shall build the ring world that mirrors `ZoneArena`: one patch on every safe-zone location (constant claim when `intake = inf`), danger on every other location, no moves. A finite `intake` gives the same layout with crowding.

### Members and agents
- **FR-12** `Member.event` and `TeamEnv.step` shall pass the event start time to `world.apply` (S4). The Phase 5 toy world accepts it.
- **FR-13** A `PatchMember` base shall record `kind` from `info` and extras `('target', 'harvest', 'nHere', 'patch')`, so the team history holds the true harvest.
- **FR-14** `randomAgent` shall choose a target uniformly among all locations (its own included) with its own generator.
- **FR-15** `banditAgent(K=None, cUCB, H)` shall keep, per location, the reward rates (reward / duration) of its last `K` stays there (`n_j` stored values, `nStays = sum_j n_j`); score each location as `(mean_j + cUCB * sqrt(ln(1 + nStays) / n_j)) * H / (H + T[loc, j])`; go first to unvisited locations (nearest first, then lower index); otherwise choose the best score (ties to the lower index) (S7). It draws no random numbers.
- **FR-16** `CircuitMember` shall get a `reward(world, t, fix)` hook, called after the fixation draw, returning `world.valence(a)` by default; nothing else changes. `CircuitPatchMember` shall override it to call `world.fixate` for the fixation interval `[t + tS, t + tS + fix)` and return the sign of `net` (`+1`, `-1` or `0`), and shall add `harvest` to its extras (S6). The world's `scheme` does not apply to circuit members: they always learn from the sign of their own net harvest.

### References and metrics
- **FR-17** `yieldModel(world, p, n)` shall give `E_p(n)` (0 for `n = 0`): fixed intake `min(n c, I_p)`; logistic `n c` if `n c <= g K / 4`, else `g Smin (1 - Smin / K)` (the stock collapses to its floor).
- **FR-18** `idealFree(world, N)` shall add agents one at a time to the patch with the highest `E_p(n_p + 1) / (n_p + 1)` while that value is above 0 (ties to the lower index; the rest stay outside), and return the allocation and its total yield. `socialOptimum(world, N)` shall maximise `sum_p E_p(n_p)` with `sum_p n_p <= N` by dynamic programming over patches, and return the allocation and its total yield.
- **FR-19** Metrics from a ledger: welfare (total true harvest; per agent-second), Gini of agents' total harvest, coverage (time share of patches with at least one agent), danger time share, the IFD distance over time (`0.5 * sum |n_p(t) - n_p^IFD| / N` over patches and "outside", on a 1 s grid, built from the ledger's stay intervals; agents in transit or at a non-patch location count as "outside"), the time after each patch move until the IFD distance (mean over a window `w`) drops below `delta` (`nan` if not before the next move), and welfare loss `1 - welfare / (SO yield * Ttot)`, with the SO for the team's size.

### Demo and prototype
- **FR-20** `tools/phase6_prototype.py` (throwaway, numpy only) shall run the dynamic-range check from the plan and write a short report (T1).
- **FR-21** `nbs/demo_team.ipynb` shall show: the two layouts with patches and danger; the references for the default world in both patch models; a `banditAgent` team and a `randomAgent` team (two runs on the same world seed) in the main layout with moving patches (welfare and IFD distance over time, move times marked, Gini, coverage, danger share, time to IFD); circuit agents with crowding on the ring; the sanity check result; and, in the full run, a scaling preview over team sizes that re-runs prototype checks (1) and (2) on the package world.

## Quality requirements

- **NFR-1 Exactness:** the Phase 5 golden fixtures and the six demo `metrics.json` hashes stay identical (the `CircuitMember` hook moves a pure function call only).
- **NFR-2 Speed:** quick demo under 10 s; a 64-agent `banditAgent` team in a 600 s run under 30 s on a laptop.
- **NFR-3 Size and style:** each new module under 200 lines; nbdev notebooks with tests; naming as in the existing code.
- **NFR-4 Dependencies:** none added.
- **NFR-5 Determinism:** the same seeds give the same team history and ledger. The world's site draws, patch moves and observation noise, and each agent, use separate generators from `spawnRngs`, so adding an agent does not change the patch sites or moves.

## Acceptance criteria

Normal tests (`nbdev-test --n-workers 0`):

- **AC-1 Sanity bridge:** with `zoneConfig(symmetric)` for both scenes, one `CircuitPatchMember` (seeds 0, 1, 2; 300 s) gives the same `t`, `dt`, `location`, `reward` and the same `CircuitMember` extras as `CircuitMember` in `ZoneArena(symmetric)`.
- **AC-2 Phase 5 intact:** golden fixtures pass after the hook and the `apply(..., t)` change; the Phase 5 toy-world tests pass.
- **AC-3 Layouts:** symmetric matrices, zero diagonal, triangle inequality on random triples; ring distance equals circular steps; on the torus, opposite edges are neighbours; `neighbours` with radius 0, 1 step and `inf` give the expected sets.
- **AC-4 Harvest:** at one fixed-intake patch, a lone agent takes `min(c, I) * tStay`; when two agents start a stay at the same time, the first to be processed (lower index) is still alone and takes `min(c, I) * tStay`, the second takes `min(c, I / 2) * tStay`; a third arriving while both stay takes `min(c, I / 3) * tStay`; logistic regrowth matches a fine Euler integration within 1e-6 relative; the stock never drops below `Smin`; `I = inf` gives constant claims `c * tStay`.
- **AC-5 Moves and time:** patches move exactly at multiples of `Tmove`, never onto another patch or a danger location, keep their stock, and repeat with the same seed; a call with an earlier `t` raises `ValueError`; a target outside `0..L-1` raises `ValueError`.
- **AC-6 Rewards and observations:** hand-checked values of the three schemes at a crowded patch, an empty patch, a danger location and during travel; noise 0 gives observed = true harvest; noise > 0 is reproducible by seed.
- **AC-7 References:** fixed intake `I = (1, 2, 3)`, large `c`, `N = 6`: IFD `(1, 2, 3)` (input matching); on 50 random small worlds, IFD has no profitable single-agent move and SO equals brute force; with logistic stocks and `N` larger than the number of agents the patches can sustain (`sum_p floor(g K / (4 c))`), SO yield is larger than IFD yield.
- **AC-8 Agents:** `randomAgent` target frequencies are within 3 standard errors of uniform over 10 000 draws; `banditAgent` visits unvisited locations first; alone on a ring of 8 locations with one patch (intake 1), no danger and no moves, with `cUCB = 0.2`, it spends more than 80% of the last quarter of a 600 s run at that patch; `K` limits the stored stays.
- **AC-9 Metrics:** Gini 0 for equal harvests and `(n - 1) / n` when one agent has everything; IFD distance 0 at the IFD allocation; coverage and time-to-IFD on hand-built ledgers.
- **AC-10 Determinism and export:** the same seed gives identical histories and ledgers; `toJSONL` works with the new extras; `TeamEnv` driving a `TeamPatchWorld` with the actions a `runTeam` team of `PatchMember`s chose gives the same ledger (the view Phase 10 will use).

Slow and manual checks:

- **AC-11 Prototype gate (T1):** the dynamic-range check passes for at least one (layout, patch model), over team sizes {1, 4, 16, 64} and 10 seeds: (1) no ceiling: every harness's first-quarter welfare rate is below 0.9 times the SO yield for that team size; (2) no floor: the no-communication team beats `randomAgent` at every team size (95% bootstrap confidence intervals do not overlap); (3) the best-minus-worst harness gap (paired over seeds) has a 95% confidence interval that excludes 0 for at least two team sizes, and its size differs between team sizes. The result fixes S1, S2 and the *(T1)* defaults. Exact check and selection rules: [design-low-level.md](design-low-level.md) section 10.
- **AC-12 Demo:** `nbs/demo_team.ipynb` runs in normal tests (quick) and with `--flags slow`, writing `results/multiagent/demo_team/{quick,full}/`. Its findings (bandit vs random welfare, and checks (1) and (2) re-run on the package world in the full run) are reported, not asserted. If checks (1) or (2) fail on the package world, that is recorded in the README and the defaults are revisited before Phase 7.
- **AC-13 Everything else:** all tests pass; the six Phase 5 demo hashes are unchanged; module line counts under 200; no new dependencies.

## Out of scope

- Communication channels, memory sweeps, evaporation, compute budgets: Phase 7 (Phase 6 only provides `neighbours` and the `K` setting; the T1 prototype uses simplified throwaway channels to check dynamic range).
- The benchmark grid, statistics and report: Phase 8.
- Bad agents and defences: Phase 9.
- The circuit agent on the torus (its goal weights encode a direction, not a place).
- Flexible and pre-structured agents in the patch world (they stay in the Phase 5 regression only).
- 3-D layouts; travel costs inside the references (the SO is an upper bound).
- Mixed teams of circuit and generic agents as an experiment (allowed by the code, not tested beyond determinism).
