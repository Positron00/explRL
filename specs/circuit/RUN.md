# Running the circuit model demo

This guide runs the Hebbian circuit demo (Figs 3-5) from Dan et al. (Neuron 2024): [`nbs/demo_circuit.ipynb`](../../nbs/demo_circuit.ipynb). Design and acceptance criteria live in [README.md](README.md).

## Prerequisites

Same as the other demos: Python 3.9+, clone [explRL](https://github.com/Positron00/explRL), then:

```sh
pip install -e ".[dev]"
nbdev-export
```

## Tests

| Command | What it does | Time (typical) | Outputs |
|---------|----------------|----------------|---------|
| `nbdev-test --n-workers 0 nbs/demo_circuit.ipynb` | Policy and plasticity plots; 2 flies per set-up (goal, compass asymmetric/symmetric, both) | ~4 s | `results/demo_circuit/` and `quick/` |
| `nbdev-test --n-workers 0 --flags slow nbs/demo_circuit.ipynb` | 20 flies per set-up; AC-8 to AC-10 asserts | ~21 s | adds `results/demo_circuit/full/` |

Full library test suite (all notebooks):

```sh
nbdev-test --n-workers 0
```

Use `--n-workers 0` if multiprocessing fails in your environment.

## Jupyter

Open [`nbs/demo_circuit.ipynb`](../../nbs/demo_circuit.ipynb) and run all cells, including `#| slow` cells for the full acceptance checks.

## Outputs

Under `results/demo_circuit/` (gitignored):

| Path | Contents |
|------|----------|
| `policy_curves.png`, `goal_plasticity.png` | Deterministic plots, written on every run |
| `quick/` or `full/` | `goal_learning.png`, `compass_learning.png`, `both.png`, `metrics.json` |

Both `metrics.json` files hold the run settings (`mode`, `seed`, `nRuns`, `lengths_s`); `full/metrics.json` adds the acceptance values (`AC8_*`, `AC9_*`, `AC10_*`), including the reported spread of final probe PI scores.

## What success looks like

The slow run asserts:

- Goal learning with a perfect compass (AC-8): over 1200 s, the goal's distance to the nearest safe-zone center falls and goal strength rises.
- Compass learning (AC-9): the asymmetric scene makes the compass stable (mean map `pJ` below 0.15, probe jump rate below 0.2); the symmetric scene keeps it unstable (probe jump rate above 0.3).
- Both systems (AC-10): the goal moves from a danger center toward a safe zone, and the probe PI rises and ends above zero.

Measured values are in [README.md — Results](README.md#results).

## Related

- Flexible-policy demo (Fig 2d-e): [specs/demo/RUN.md](../demo/RUN.md)
- Pre-structured setpoint policy (Fig 2h): [specs/prestructured/RUN.md](../prestructured/RUN.md)
- Shared multi-agent loop (Phase 5): [specs/multiagent/phase5/RUN.md](../multiagent/phase5/RUN.md)
