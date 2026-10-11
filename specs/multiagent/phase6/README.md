# Spec: Phase 6, team environment with incentives

Status: **implemented** (2026-10-11). How to run: [RUN.md](RUN.md). Code: `explRL/patchworld.py`, `explRL/team_refs.py`, `explRL/team_agents.py`; Phase 5 amendments in `multi` and `members`. Part of the multi-agent plan: [../README.md](../README.md). Builds on Phase 5: [../phase5/README.md](../phase5/README.md).

**Measured results.**
- **T1 prototype (AC-11):** passes for all four (layout, model) pairs with the default settings, so no default changed; the ring with fixed intake passes most clearly (S1, S2; design-low-level section 10).
- **Package world, full demo (AC-12), ring, fixed intake, moving patches:** prototype checks (1) no ceiling and (2) no floor both pass. Bandit welfare per agent-second is 0.66 / 0.59 / 0.24 / 0.074 at team sizes 1 / 4 / 16 / 64, against about 0.004 for random. In the 64-agent team the bandits' first-quarter team rate (4.0 /s) is close to the 0.9 x SO ceiling (4.5 /s), and over the whole run they reach about 94% of the SO yield (the synchronous prototype gave about 50%). So the package world leaves little headroom at 64 agents; Phase 7 should check this before relying on the largest team size (harder settings: more locations, faster moves, noise).
- **Team run (8 agents, 600 s):** bandit vs random per agent-second 0.40 vs 0.004, Gini 0.06 vs 0.35, welfare loss against the SO 0.36 vs 0.99; the bandit team gets back near the IFD within 33-90 s after three of the four patch moves.
- **Sanity bridge (AC-1):** holds for both scenes.
- **Speed:** a 64-agent bandit team runs 600 s in about 4 s (NFR-2); the quick demo takes about 2 s and the full demo about 1 minute.
- **Phase 5 regression:** the six demo hashes are unchanged.

## Goal

Give the team something to coordinate about. Phase 5 put several agents in one world, but they could not affect each other. Phase 6 adds a world where they do:

1. **`TeamPatchWorld`**: a set of locations with travel times between them. Some locations are **resource patches**; agents at the same patch **split** the harvest, so crowding hurts. Some locations are **danger** zones that cost reward. Patches can **move** every `Tmove` seconds, so old knowledge goes stale.
2. **Two layouts** for the same world: a **ring** (the paper's heading ring; the circuit agent can live here) and a **2-D torus** (a grid whose edges wrap). The plan expected the torus to be the main layout; the T1 prototype chose the ring (S1), and the torus stays as a configuration.
3. **Two baseline learners**: `banditAgent` (a general learner: UCB over locations, discounted by travel time) and `randomAgent` (the floor). The **circuit agent** joins on the ring through a small patch-aware adapter.
4. **Three reward schemes**: individual, team (mean), difference reward.
5. **Two references**, computed exactly for each world: the **ideal free distribution** (where selfish agents should settle) and the **social optimum** (the best total harvest), plus the metrics that compare a team with them.

Phase 6 adds no communication between agents. That is Phase 7 (the T1 prototype uses simplified throwaway channels only to check that the benchmark can tell harnesses apart).

**Main acceptance tests:** (a) the prototype's dynamic-range check passes, so the benchmark can tell harnesses apart; (b) on the ring configured like `ZoneArena`, one circuit agent gives the same history as in `ZoneArena` (sanity bridge to Phase 5); (c) all Phase 5 checks (golden fixtures, six demo hashes) still pass.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions and rejected alternatives, risks |
| [design-low-level.md](design-low-level.md) | Classes, signatures, formulas (layouts, harvest, regrowth, rewards, references, metrics), defaults, demo layout |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks; T1 is the prototype gate |
| [RUN.md](RUN.md) | How to run the prototype, tests and demo, and what success looks like |

## What Phase 5 gives us (the facts the design depends on)

| Piece | Fact | Consequence for Phase 6 |
|---|---|---|
| `runTeam` / `Clock` | Runs events in order of start time, ties to the lower agent index; time never goes backwards | The world can update stocks lazily ("advance to time t") on each call |
| `Member.event` default | `observe -> act -> world.apply(i, action) -> learn`; the reward must be known when `apply` returns | Harvest is **claimed at the start of a stay** (S3) |
| Generic world protocol | `reset(seed, nAgents)`, `observe(i)`, `apply(i, action)`; no time argument | Small amendment: pass `t` to `apply` (S4) |
| `CircuitMember` | Reads `world.valence(a)` before the fixation draw; goal learning uses only the **sign** of `R` | Move the valence read after the fixation draw (no random draw depends on it) behind a hook; a subclass claims harvest instead (S6) |
| Time units | Generic and circuit members use seconds | One team unit: `'s'` |

## Decisions

| ID | Question | Answer |
|----|----------|--------|
| S1 | Main layout: ring or 2-D torus | **Decided by T1 (2026-10-11): ring.** All four (layout, model) pairs pass the dynamic-range check with the default settings; ring with fixed intake passes most clearly (largest weakest gap between channels; design-low-level section 10). Both layouts are built |
| S2 | Default patch model: fixed intake or logistic stock | **Decided by T1: fixed intake.** Both are built. Fixed intake is the simple case (ideal free distribution = social optimum in welfare); logistic stock can be over-harvested, so the two references differ |
| S3 | When harvest is paid in an event-based world | **Decided: claim at the start of a stay.** The agent takes its share of what the patch offers, split among itself and the agents whose stays cover that start time. Exact within the event queue, so the reward is known when `apply` returns. Agents arriving later do not reduce a claim already made, so the first to arrive is favoured; short stays (1 s) keep this small |
| S4 | How the world learns the time | **Decided: `apply(i, action, t)`.** `Member.event` and `TeamEnv.step` pass the start time. Paper adapters do not use `apply`, so Phase 5 results cannot change |
| S5 | Team and difference rewards in an asynchronous world | **Decided: computed from the world's yield model at the current occupancy** (the same model the references use), times the event duration. Individual reward is the actual claim |
| S6 | How the circuit agent sees crowding | **Decided: a `reward` hook in `CircuitMember`** (default `world.valence(a)`, called after the fixation draw); `CircuitPatchMember` overrides it to claim harvest and returns its sign. Ring only |
| S7 | `banditAgent` value estimate | **Decided: mean reward rate of the last `K` stays at each location** (`K = None`: all), UCB bonus, score discounted by `H / (H + travel time)`. `K` is the Phase 7 "memory" setting; `cUCB` and `H` are tuned by T1 |
| S8 | Distance on the torus | **Decided: Euclidean distance with wrap-around**, so travel time and communication range do not depend on direction |
| S9 | How patches move | **Decided: every `Tmove` seconds, each patch jumps to a random free location (world's own seeded generator) and keeps its stock** |
