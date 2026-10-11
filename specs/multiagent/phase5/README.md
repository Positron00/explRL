# Spec: Phase 5, shared multi-agent interface and training loop

Status: **implemented** (2026-10-11). Tasks T0–T10 done. **How to run:** [RUN.md](RUN.md). Code: `explRL/multi.py`, `explRL/members.py`; wrappers in `train`, `prestructured_train`, `circuit_train`. Part of the multi-agent plan: [../README.md](../README.md).

## Results

Checked against the pre-Phase-5 commit `905a48d`, run in a separate git worktree in the same session:

| Check | Result |
|-------|--------|
| AC-1 golden fixtures (every field and dtype, final weights / goal headings, probe PI and jump rate) | identical |
| AC-8 SHA-256 of all six demo `metrics.json` (quick and full, three demos) | identical |
| AC-9 slow demo wall time, old to new: flexible / pre-structured / circuit | 39.5 to 41.3 s (+4.6%) / 0.9 to 1.0 s (within run-to-run noise; repeats 0.97-1.19 s old, 0.93-0.96 s new) / 21.5 to 21.6 s |
| Peak memory, one 240 s flexible run (seed 0, 106 658 events) | 49.8 MB |
| One-member fast path | not added: it would save about 2% (1.64 vs 1.68 s per 240 s flexible run) |
| AC-10 module sizes | `multi.py` 177 lines, `members.py` 77 lines |
| `demo_multi` | quick + full runs; `independent: true`; `learning.png` and per-agent `learning_outcomes` in `metrics.json` |

## Goal

Replace the three separate training loops (flexible, pre-structured, circuit) with **one event-queue loop** that runs a *team* of agents in one world, without changing any existing result:

1. One loop (`runTeam`) that always runs the agent whose next event is earliest. A single agent is a team of size 1.
2. Adapters ("members") that wrap the three existing agents, so they run through the new loop unchanged.
3. One history format for every agent (one record per event), exportable as JSONL for analysis and as training data.
4. A one-agent-at-a-time view (`TeamEnv`, in the style of PettingZoo's "agent-environment cycle") for later phases, where actions come from outside the package (for example from an LLM in Phase 10).
5. The old functions (`train_agent`, `train_prestructured`, `train_circuit`) keep their names, arguments and return types, and become thin wrappers over the new loop.

**Main acceptance test:** all three existing demos produce **byte-identical** `metrics.json` files (quick and full) before and after the change, and short seeded runs match saved "golden" histories exactly.

Phase 5 adds no interaction between agents. Agents in one team share a world but do not affect each other until Phase 6 (crowding) and Phase 7 (communication).

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Functional and quality requirements, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Components, data flow, main decisions and rejected alternatives, risks |
| [design-low-level.md](design-low-level.md) | Classes, function signatures, the exact event bodies of each adapter, numerics, test fixtures |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks |
| [RUN.md](RUN.md) | How to run the tests and demo, and how to rebuild the fixtures and baseline from the old commit |

## What the existing loops do (the facts the design depends on)

| Loop | One event | Time unit | Where learning happens |
|---|---|---|---|
| `train_agent` (flexible) | one 1 ms fixation sample **or** one saccade | integer samples (`delT` = 1 ms; a saccade is `dtS` = 320 samples) | after the world step, every event (up to 240 000 events per 240 s run, since each saccade replaces 320 samples; 106 658 for seed 0) |
| `train_prestructured` | one fixation, then one saccade and a possible jump | seconds | after the world step |
| `train_circuit` | one saccade (grid step by grid step), a possible jump, then one fixation | seconds, with a start time `t0` | compass learning **during** the saccade, at each grid step; goal learning after the fixation draw |

The circuit agent's mid-saccade learning, and the jump draw that depends on the weights just learned, are why the design gives each member a single `event` method instead of a strict act-then-learn split (design decision D2).

## Decisions

The two plan-level decisions for this phase are settled: **event queue** (plan Q1) and **old loops kept as thin wrappers** (plan Q4). Decisions specific to this phase:

| ID | Question | Answer |
|----|----------|--------|
| P1 | Member interface: strict `act` / `learn`, or one `event(world, t)` method? | **Decided: one `event` method.** Existing agents move their loop bodies into it unchanged. New agents (Phase 6+) inherit a default `event` that calls `act` and `learn` (D2) |
| P2 | Time units: convert everything to seconds, or keep native units? | **Decided: keep native units.** The loop never converts time; each member declares its unit (`'s'` or `'sample'`) and all members of a team must share it (D3) |
| P3 | Order of events that start at exactly the same time | **Decided: lower agent index first** (D5) |
| P4 | How the regression is checked | **Decided: golden fixtures plus SHA-256 hashes of every demo `metrics.json`** (D8) |
| P5 | Include `TeamEnv` (one-agent-at-a-time view) now, or wait for Phase 10? | **Decided: now** (D6) |
| P6 | Depend on the PettingZoo package? | **Decided: no** (D6) |
