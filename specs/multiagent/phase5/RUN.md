# Running Phase 5 (shared multi-agent loop)

This guide runs the Phase 5 tests and demo: one event-queue loop (`runTeam`) for teams of agents, adapters for the three existing agents, and the one-agent-at-a-time view (`TeamEnv`). Design and acceptance criteria live in [README.md](README.md); the plan is in [../README.md](../README.md).

## Prerequisites

Same as the other demos: Python 3.9+, clone [explRL](https://github.com/Positron00/explRL), then:

```sh
pip install -e ".[dev]"
nbdev-export
```

## Tests

From the repo root. If `nbdev-test` hits a multiprocessing error, keep `--n-workers 0`.

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/multi.ipynb` | event order and ties, errors, `TeamEnv`, `TeamEnv` = `runTeam`, JSONL, seeds (AC-3 to AC-7) | ~1 s |
| `nbdev-test --n-workers 0 nbs/members.ipynb` | adapter units and names, import rule, agents sharing a world equal their solo runs (AC-2) | ~2 s |
| `nbdev-test --n-workers 0 nbs/train.ipynb` (and `prestructured_train`, `circuit_train`) | golden fixtures: the old functions give exactly the pre-Phase-5 histories (AC-1) | ~1 s each |
| `nbdev-test --n-workers 0 nbs/demo_multi.ipynb` | four circuit agents in one arena; writes the quick demo artifacts | ~3 s |
| `nbdev-test --n-workers 0 --flags slow nbs/demo_multi.ipynb` | same team for 1200 s; writes `full/` artifacts | ~15 s |
| `nbdev-test --n-workers 0` | all notebooks, quick | ~10 s |

## Demo artifacts

Under `results/multiagent/demo_multi/{quick,full}/` (gitignored): `timeline.png` (events per agent over time), `learning.png` (PI, goal distance, jump rate per agent), `team.jsonl` (one record per event, extras keyed by name) and `metrics.json` (`mode`, `seed`, `nAgents`, `Ttot_s`, `scene_symmetric`, `events_per_agent`, `independent`, `learning_outcomes`). The demo uses a **symmetric** `ZoneArena` (high compass jump rate); see [../README.md](../README.md) for when to use asymmetric scenes in later phases.

## Checking that nothing changed (AC-8, AC-9)

The fixtures and the baseline come from the commit **before** Phase 5, run in its own git worktree with that worktree first on `PYTHONPATH`, so they can never be overwritten by output of the new code. To rebuild the baseline and compare (about 2.5 minutes):

```sh
git worktree add --detach /tmp/explRL_base 905a48d
tools/phase5_demo_hashes.sh /tmp/explRL_base "$PWD/results/multiagent/baseline_phase5"   # old code
tools/phase5_demo_hashes.sh "$PWD" /tmp/explRL_new                                       # new code
diff <(cut -d' ' -f1,3 results/multiagent/baseline_phase5/sha256.txt) <(cut -d' ' -f1,3 /tmp/explRL_new/sha256.txt) && echo identical
cat results/multiagent/baseline_phase5/timing.txt /tmp/explRL_new/timing.txt
git worktree remove --force /tmp/explRL_base
```

To regenerate the golden fixtures (only on purpose; the script refuses to overwrite), delete `nbs/fixtures/phase5/*.npz`, copy `tools/make_phase5_fixtures.py` into the old worktree, run `PYTHONPATH=/tmp/explRL_base python tools/make_phase5_fixtures.py` there, and copy the three files back.

## What success looks like

- All notebooks pass, including the golden-fixture cells in the three training notebooks.
- The six demo hashes are identical to the baseline; the full flexible demo is at most 25% slower (measured +4.6%).
- `demo_multi` prints `each agent equals its solo run: True`.

## Related demos

- Phase 6 team world: [phase6/RUN.md](../phase6/RUN.md)
- Phase 7 harness: [phase7/RUN.md](../phase7/RUN.md)
- Phase 8 benchmark: [phase8/RUN.md](../phase8/RUN.md)
- Phase 9 safety: [phase9/RUN.md](../phase9/RUN.md)
- Flexible-policy demo (Fig 2d-e): [specs/demo/RUN.md](../../demo/RUN.md)
- Pre-structured setpoint policy (Fig 2h): [specs/prestructured/RUN.md](../../prestructured/RUN.md)
- Circuit model (Figs 3-5): [specs/circuit/RUN.md](../../circuit/RUN.md)
