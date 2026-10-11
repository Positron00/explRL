# Requirements: Phase 5, shared multi-agent interface

Terms used below.

- **Team**: one or more agents running in one world. A single agent is a team of size 1.
- **Member**: an object that wraps one agent and can run one **event** of it in a world. Members are numbered `0..N-1` in the order given (the **agent index**).
- **Event**: the unit of behaviour a member runs at once; its meaning depends on the agent (see the README table). Each event has a start time `t`, a duration `dt > 0`, a reward, and the **location** where that reward was earned (the location at the end of the event).
- **Time unit**: `'sample'` (the flexible agent's integer 1 ms samples) or `'s'` (seconds). Time values are never converted.
- **Native world**: an existing world (`HeadingArena`, `ZoneArena`), used through its own methods by the adapter of the agent that knows it.
- **Generic world**: a world implementing the small protocol in FR-9 (`reset`, `observe`, `apply`). None exists in Phase 5 except a toy world used in tests; Phase 6 adds the first real one.
- **Golden fixture**: arrays saved from short seeded runs of the old code, before any change, and compared exactly after the change.

## Functional requirements

### Records and history
- **FR-1** Each event shall produce one `Record` with: `agent` (index), `t`, `dt`, `kind` (a short string naming the event type), `location`, `reward`, and `extras` (a tuple with the member's native per-event fields, in the member's declared order `extraNames`).
- **FR-2** `TeamHistory` shall keep records in the order they ran, return the records of one agent, and export all records as JSONL: one JSON object per line, with `extras` written as an object keyed by `extraNames`, and numpy scalars converted to plain numbers or booleans.

### Running a team
- **FR-3** `runTeam(members, world, Ttot, t0=0)` shall run every member from time `t0` until `t0 + Ttot`, always running next the member whose next event starts earliest, with ties broken by the lower agent index. A member runs an event only if its start time is less than `t0 + Ttot` (the same rule as the old `while t < tEnd` loops). Each member's next start time is its current start time plus the event's `dt`. `runTeam` does not reset the world: native worlds have no state to reset, and for a generic world the caller calls `world.reset(seed, len(members))` first (`TeamEnv.reset` does this itself).
- **FR-4** `runTeam` shall raise `ValueError` for an empty team, for members with different time units, and for an event with `dt <= 0` (which would otherwise loop forever).
- **FR-5** `runTeam` shall not convert, round or recompute any time value: start times are `t0`, then repeated `t + dt` sums, in the members' own unit.
- **FR-6** `runTeam` shall give each member its agent index before the first event, and return a `TeamHistory`.

### Members
- **FR-7** The base `Member` shall provide a default `event(world, t)` for members of generic worlds: observe, choose an action (`act`), apply it to the world, learn from the result (`learn`), and return the outcome. Subclasses for new agents implement only `act` and, optionally, `learn`.
- **FR-8** There shall be one adapter per existing agent: `FlexibleMember` (time unit `'sample'`), `PrestructuredMember` and `CircuitMember` (`'s'`). Each adapter's `event` shall perform exactly the same operations, in the same order, with the same random draws, as one pass of the body of the old loop, and return the old loop's per-event row (without its time field) as `extras`.

### One-agent-at-a-time view
- **FR-9** A generic world shall provide `reset(seed, nAgents)`, `observe(i)` and `apply(i, action) -> (reward, dt, location, info)`.
- **FR-10** `TeamEnv(world, nAgents, Ttot, t0=0)` shall provide `reset(seed)`, `next_agent()` (the agent index whose next event is earliest, ties to the lower index, or `None` when every agent is done), `observe(i)`, `step(action)` (applies the action for `next_agent()`, records it, reschedules that agent, and returns `(reward, done)` where `done` means that agent has no more events), and the `history` so far. Calling `step` when `next_agent()` is `None` raises `RuntimeError`.
- **FR-11** For the same world, seed and actions, `TeamEnv` driven from outside and `runTeam` with members using the default `event` (after `world.reset(seed, n)`) shall give identical histories.

### Seeds
- **FR-12** `spawnRngs(seed, n)` shall return `n` independent numpy generators from one seed (via `numpy.random.SeedSequence(seed).spawn(n)`): the same seed gives the same streams, and different members get different streams.

### Old functions
- **FR-13** `train_agent`, `train_prestructured` and `train_circuit` shall keep their signatures, defaults and return types (`History`, `EventHistory`, `CircuitHistory`, with the same field dtypes), and shall be implemented by running a one-member team through `runTeam` and converting the records back. `probe`, `runMany`, `runManyPrestructured`, `runManyCircuit` and all demos shall work without change.

## Quality requirements

- **NFR-1 Exactness:** with the same seeds, every array returned by the old functions is identical (same values, same dtype, same length) before and after the change.
- **NFR-2 Speed:** the full flexible demo (`nbdev-test --flags slow nbs/demo.ipynb`, 20 runs of up to 240 000 events each) takes at most 25% longer than before; the other two demos at most 10% longer. Times are measured on the same machine in the same session.
- **NFR-3 Size and style:** new modules under 200 lines each; nbdev notebooks with tests; naming follows the existing code (`runTeam`, `TeamHistory`, camelCase methods).
- **NFR-4 Dependencies:** none added.
- **NFR-5 Imports:** the new modules import the model modules, never the training modules, so no import cycle is possible.

## Acceptance criteria

Normal tests (`nbdev-test --n-workers 0`):

- **AC-1 Golden fixtures:** for each of the three old functions, the short seeded runs saved before the change (flexible 2 s in `HeadingArena`; pre-structured 240 s in `HeadingArena`, with and without learning; circuit 300 s in a symmetric `ZoneArena`, then a second segment from `t0 = 500` on the same agent, then a `probe`) give identical arrays and identical final weights / goal headings after the change.
- **AC-2 Independence:** three circuit agents with seeds 0, 1, 2 in one `ZoneArena` team give, for each agent, records identical to that agent's run alone (same `t`, `dt`, `extras`), and the team history is ordered by start time. The same holds for three pre-structured agents in one `HeadingArena`.
- **AC-3 Order:** toy members with fixed durations (for example 1.0, 1.5 and 1.0 s) produce the expected interleaving, with ties going to the lower index, and start times never decrease.
- **AC-4 Errors:** an empty team, mixed time units and `dt <= 0` each raise `ValueError`; `TeamEnv.step` after the end raises `RuntimeError`.
- **AC-5 One-at-a-time view:** on a toy world, `TeamEnv` gives the right `next_agent()` sequence, `done` flags and final `None`; the same seed gives the same history; and it matches `runTeam` with default-`event` members taking the same actions (FR-11).
- **AC-6 JSONL:** one line per record, each valid JSON with the seven keys and `extras` keyed by name; values read back equal the originals.
- **AC-7 Seeds:** `spawnRngs` gives the same streams for the same seed and different streams for different members.

Slow and manual checks:

- **AC-8 Byte-identical demos:** the SHA-256 of all six `metrics.json` files (quick and full for `demo`, `demo_prestructured`, `demo_circuit`) equals the hash recorded before the change.
- **AC-9 Speed:** NFR-2 holds.
- **AC-10 Everything else:** all existing tests pass; each new module is under 200 lines; `nbs/demo_multi.ipynb` runs in normal tests and writes `results/multiagent/demo_multi/quick/` (`team.jsonl`, `timeline.png`, `learning.png`, `metrics.json` with `learning_outcomes`); the slow cell writes the same artifacts under `full/` for a 1200 s run.

## Out of scope

- Any interaction between agents (crowding, shared rewards, communication): Phases 6 and 7.
- New agents (`banditAgent`, `randomAgent`) and new worlds (`TeamPatchWorld`): Phase 6.
- Running a team that mixes time units, or converting the flexible agent to seconds.
- Changing any model, parameter or random draw order.
- Parallel or multi-process execution of teams.
- Byte-identical PNG figures (matplotlib output can vary with metadata); only `metrics.json` and arrays are compared.
