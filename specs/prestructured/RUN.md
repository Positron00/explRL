# Running the pre-structured policy demo

This guide runs the setpoint-policy demo (Fig 2h) from Dan et al. (Neuron 2024): [`nbs/demo_prestructured.ipynb`](../../nbs/demo_prestructured.ipynb). Design and acceptance criteria live in [README.md](README.md).

## Prerequisites

Same as the flexible demo: Python 3.9+, clone [explRL](https://github.com/Positron00/explRL), then:

```sh
pip install -e ".[dev]"
nbdev-export
```

## Tests

| Command | What it does | Time (typical) | Outputs |
|---------|----------------|----------------|---------|
| `nbdev-test --n-workers 0 nbs/demo_prestructured.ipynb` | Policy plots; 2 runs of 240 s for each of the three conditions | ~1 s | `results/demo_prestructured/` and `quick/` |
| `nbdev-test --n-workers 0 --flags slow nbs/demo_prestructured.ipynb` | 20 runs of 240 s per condition; AC-8 and AC-9 asserts, AC-10 reported | ~1 s | adds `results/demo_prestructured/full/` |

Full library test suite (all notebooks):

```sh
nbdev-test --n-workers 0
```

Use `--n-workers 0` if multiprocessing fails in your environment.

## Jupyter

Open [`nbs/demo_prestructured.ipynb`](../../nbs/demo_prestructured.ipynb) and run all cells, including `#| slow` cells for the full acceptance checks.

## Outputs

Under `results/demo_prestructured/` (gitignored):

| Path | Contents |
|------|----------|
| `policy_curves.png`, `fig2h_analytic.png` | Deterministic plots, written on every run |
| `quick/` or `full/` | `fig2h_simulated.png`, `learning_nojump.png`, `learning_jump.png`, `metrics.json` |

`full/metrics.json` adds the acceptance values (`AC8_*`, `AC9_*`, `AC10_*`) and the jump rate of the fixed-goal runs.

## What success looks like

The slow run asserts:

- Fixations are longer near the goal and near the opposite heading than at 60-120 degrees from the goal (AC-8, the two peaks of Fig 2h).
- Without jumps, the goal heading ends closer to the reward goal than it started (AC-9).
- Goal headings stay finite with jumps (AC-10; how close they get is reported, not asserted).

Measured values are in [README.md — Results](README.md#results).

## Related

- Flexible-policy demo (Fig 2d-e): [specs/demo/RUN.md](../demo/RUN.md)
- Circuit model (Figs 3-5): [specs/circuit/RUN.md](../circuit/RUN.md)
