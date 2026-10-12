# Running Phase 6 (team environment with incentives)

This guide runs the Phase 6 prototype, tests and demo: `TeamPatchWorld` (ring and torus layouts, fixed or logistic patches, three reward schemes), the references and metrics, and the bandit, random and patch-aware circuit agents. Design and acceptance criteria live in [README.md](README.md); the plan is in [../README.md](../README.md).

## Prerequisites

Same as the other demos: Python 3.9+, clone [explRL](https://github.com/Positron00/explRL), then:

```sh
pip install -e ".[dev]"
nbdev-export
```

## Prototype gate (T1, AC-11)

A throwaway numpy script (does not import `explRL`) checks that the benchmark can tell harnesses apart before any package code depends on the defaults. About 15 s:

```sh
python tools/phase6_prototype.py
```

It writes `results/multiagent/phase6_prototype/report.md` (one pass/fail table per attempt) and `metrics.json` (gitignored). Outcome on 2026-10-11: attempt 1 (the spec defaults) passes for all four (layout, model) pairs; the ring with fixed intake passes most clearly and is the main configuration (decisions S1, S2).

## Tests

From the repo root. If `nbdev-test` hits a multiprocessing error, keep `--n-workers 0`.

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/patchworld.ipynb` | layouts, harvest and regrowth, moves and time, hand-checked rewards of the three schemes, observations, `neighbours`, `zoneConfig` (AC-3 to AC-6) | ~1 s |
| `nbdev-test --n-workers 0 nbs/team_refs.ipynb` | IFD and SO (worked example, 50 random worlds vs brute force, logistic gap), metrics on a hand-built ledger (AC-7, AC-9) | ~1 s |
| `nbdev-test --n-workers 0 nbs/team_agents.ipynb` | sanity bridge to `ZoneArena`, random and bandit agents, determinism, JSONL, `TeamEnv` replay (AC-1, AC-8, AC-10) | ~1 s |
| `nbdev-test --n-workers 0 nbs/multi.ipynb` and `nbs/members.ipynb` | Phase 5 loop with `apply(..., t)` and the `CircuitMember.reward` hook | ~1 s each |
| `nbdev-test --n-workers 0 nbs/train.ipynb` (and `prestructured_train`, `circuit_train`) | Phase 5 golden fixtures unchanged (AC-2) | ~1 s each |
| `nbdev-test --n-workers 0 nbs/demo_team.ipynb` | quick demo; writes `quick/` artifacts | ~2 s |
| `nbdev-test --n-workers 0 --flags slow nbs/demo_team.ipynb` | full demo with the scaling preview; writes `full/` artifacts (AC-12) | ~1 min |
| `nbdev-test --n-workers 0` | all notebooks, quick | ~10 s |

## Demo artifacts

Under `results/multiagent/demo_team/{quick,full}/` (gitignored):

- `layouts.png`: ring and torus with patches (sized by intake) and danger locations.
- `team_run.png`: 8 bandit vs 8 random agents on the ring with moving patches: team harvest rate (10 s bins, SO line) and IFD distance over time, move times dashed.
- `circuit_team.png`: harvest and PI of 4 patch-aware circuit agents sharing the `zoneConfig` ring (asymmetric, intake 1, so they crowd).
- `scaling.png` (full only): welfare per agent-second vs team size 1 to 64, bandit vs random with 95% CIs, SO and IFD yield per agent.
- `team.jsonl`: the bandit run, one record per event, extras keyed by name.
- `metrics.json`: `mode`, `seed`, `layout`, `model`, `scheme`, `scene_symmetric`, `Tmove`, `references`, `team_run`, `circuit_team`, `sanity`, and in full mode `scaling` with `check1_pass`, `check2_pass`.
- `report.md`: plain-language summary and main takeaways (written automatically after each run).

## Checking that nothing changed (AC-13)

The six paper-demo `metrics.json` hashes must still equal the Phase 5 baseline. With the baseline in `results/multiagent/baseline_phase5/` (see [../phase5/RUN.md](../phase5/RUN.md) to rebuild it):

```sh
tools/phase5_demo_hashes.sh "$PWD" /tmp/explRL_new
diff <(cut -d' ' -f1,3 results/multiagent/baseline_phase5/sha256.txt) <(cut -d' ' -f1,3 /tmp/explRL_new/sha256.txt) && echo identical
```

## What success looks like

- The prototype report ends with a `Result:` line naming the main layout and model.
- All notebooks pass; the six demo hashes are identical.
- `demo_team` prints `sanity bridge: {'True': True, 'False': True}`, and the full run prints `check (1) no ceiling: True  check (2) no floor: True`.
- `patchworld.py`, `team_refs.py` and `team_agents.py` are each under 200 lines.

## Related demos

- Phase 7 harness: [../phase7/RUN.md](../phase7/RUN.md)
- Phase 8 benchmark: [../phase8/RUN.md](../phase8/RUN.md)
- Phase 5 multi-agent loop: [../phase5/RUN.md](../phase5/RUN.md)
- Flexible-policy demo (Fig 2d-e): [specs/demo/RUN.md](../../demo/RUN.md)
- Pre-structured setpoint policy (Fig 2h): [specs/prestructured/RUN.md](../../prestructured/RUN.md)
- Circuit model (Figs 3-5): [specs/circuit/RUN.md](../../circuit/RUN.md)
