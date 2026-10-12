# Running Phase 7 (harness configurations)

Design and acceptance criteria: [README.md](README.md). Builds on Phase 6: [../phase6/RUN.md](../phase6/RUN.md).

## Prerequisites

Python 3.9+, dev install from the repo root:

```sh
pip install -e ".[dev]"
nbdev-export
```

## Tests

From the repo root (`nbdev-test --n-workers 0` if multiprocessing fails):

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/harness.ipynb` | Blackboard, MessageBus, Lead (AC-3–AC-5) | ~1 s |
| `nbdev-test --n-workers 0 nbs/harness_agents.ipynb` | CommBandit, LeadFollower, CircuitCommMember (AC-1–AC-2, AC-6–AC-7) | ~7 s |
| `nbdev-test --n-workers 0 nbs/harness_runs.ipynb` | budgets, determinism, a tiny `rangeCheck`, speed (AC-8–AC-10) | ~4 s |
| `nbdev-test --n-workers 0 nbs/demo_harness.ipynb` | quick demo artifacts (AC-12) | ~4 s |
| `nbdev-test --n-workers 0 --flags slow nbs/demo_harness.ipynb` | full demo + range check (AC-11) + budgets | ~7 min (6.5 min measured) |
| `nbdev-test --n-workers 0` | full suite (quick) | ~30 s |

**AC-10 (2026-10-11, benchmark world):** 64-agent blackboard team, 600 s world time: about **1.6 s** wall time, **~42 µs/event** (~39k events). Other channels: `messages` 50 µs, `hierarchical` 23 µs, `none` 122 µs per event.

## Demo artifacts

Under `results/multiagent/demo_harness/{quick,full}/` (gitignored):

- `channels.png` — four channels, eight bandits: welfare rate and IFD distance.
- `evaporation.png` — blackboard with λ = 0, 0.01, 0.1.
- `circuit_channels.png` — four circuit agents with none / blackboard / messages.
- `range_check.png`, `scaling_budgets.png` (full only).
- `metrics.json`, `report.md`.

## Regression (AC-13)

Phase 6 `demo_team` hashes (recorded before Phase 7 amendments):

```sh
tools/phase6_demo_hashes.sh "$PWD" results/multiagent/check_phase6
diff results/multiagent/baseline_phase6/sha256.txt results/multiagent/check_phase6/sha256.txt && echo identical
```

Phase 5 paper demos: [../phase5/RUN.md](../phase5/RUN.md).

## Harness check (AC-11)

`benchWorld()` uses the settings of attempt 3: a 64-location ring, 16 patches (total intake 32), travel scale 0.48, `Tmove` 40 s, harvest noise 0.45, `dangerCost` 2.6. The check follows the Phase 6 prototype: team harvest per second, ceiling on the mean over seeds. **All three checks pass** (highest first-quarter rate: blackboard at N=64, 0.52× the social optimum); it takes about 2 min. See [README.md](README.md) for all attempts, including the larger maps tried. To re-run only the check:

```python
from explRL.harness_runs import HarnessConfig, rangeCheck
rc = rangeCheck({ch: HarnessConfig(channel=ch) for ch in ('none', 'blackboard', 'messages', 'hierarchical')})
```

## Related

- Phase 6 team world: [../phase6/RUN.md](../phase6/RUN.md)
- Multi-agent plan: [../README.md](../README.md)
