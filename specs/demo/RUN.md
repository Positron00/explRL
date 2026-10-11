# Running the demo

This guide runs the flexible-policy demo from Dan et al. (Neuron 2024): [`nbs/demo.ipynb`](../../nbs/demo.ipynb). Design and acceptance criteria live in [README.md](README.md) and the other spec files.

## Prerequisites

- Python 3.9+
- A clone of [explRL](https://github.com/Positron00/explRL)

From the repository root:

```sh
pip install -e ".[dev]"
```

The `dev` extra installs `nbdev`, `fastcore`, and `matplotlib`, which the demo notebook and tests need.

## Export after editing notebooks

If you change any notebook under `nbs/`, export to `explRL/` before running Python or tests:

```sh
nbdev-export
```

## Option A: Tests (recommended)

nbdev runs the demo notebook as a test suite. Cells marked `#| slow` are skipped unless you pass `--flags slow`.

| Command | What it does | Time (typical) | Outputs |
|---------|----------------|----------------|---------|
| `nbdev-test --n-workers 0 nbs/demo.ipynb` | 5 s training, plots, quick checks | ~2 s | `results/demo/quick/` |
| `nbdev-test --n-workers 0 --flags slow nbs/demo.ipynb` | 240 s × 20 runs, AC-5–AC-8 asserts | ~35–40 s | `results/demo/full/` plus shared `results/demo/basis.png` |

Run the full suite (all notebooks, quick demo only):

```sh
nbdev-test --n-workers 0
```

Full demo acceptance only:

```sh
nbdev-test --n-workers 0 --flags slow nbs/demo.ipynb
```

### Troubleshooting

- **`PermissionError` / `SC_SEM_NSEMS_MAX` during `nbdev-test`:** use `--n-workers 0` so tests run in the main process.
- **Missing `matplotlib`:** install with `pip install -e ".[dev]"`.

## Option B: Jupyter

1. Install as above.
2. Start Jupyter (or VS Code / Cursor with the notebook kernel pointing at the same environment).
3. Open [`nbs/demo.ipynb`](../../nbs/demo.ipynb).
4. Run all cells. Cells tagged `#| slow` hold the 240 s run and multi-run figures; run them for the full paper-style result.

Figures are shown in the notebook and also saved under `results/demo/` (see below).

## Outputs

Artifacts are written under `results/demo/` (this directory is gitignored):

| Path | When |
|------|------|
| `basis.png` | Every run (basis plot) |
| `quick/` | Quick test or notebook without slow cells |
| `full/` | Slow test or notebook with slow cells |

Each mode folder contains PNG figures and `metrics.json`. The full run adds acceptance fields (`AC5_*`, `AC6_*`, etc.) in `full/metrics.json`.

## What success looks like

The slow run asserts:

- Longer mean fixation duration near the goal than near the opposite heading (AC-5).
- Turn bias toward the goal on CCW vs CW sides of the goal (AC-6).
- Higher residency near the goal in the last quarter than the first (AC-7).
- Finite policy weights in every run (AC-8).

Recorded values for the default 20-run setting are in [README.md — Results](README.md#results).

## Related demos

- Pre-structured setpoint policy (Fig 2h): [specs/prestructured/RUN.md](../prestructured/RUN.md)
- Circuit model (Figs 3-5): [specs/circuit/RUN.md](../circuit/RUN.md)
