# Spec: explRL full demo

Status: implemented (2026-10-10); all tasks T0-T13 done. **How to run:** [RUN.md](RUN.md). Quick checks: `nbdev-test` (about 2 s); full demo and AC-5 to AC-8: `nbdev-test --flags slow` (about 40 s).

## Results

With the paper's Table 1 parameters and no tuning, 20 runs of 240 s (seeds 0-19, goal at 180 degrees):

| Check | Result |
|-------|--------|
| AC-5 mean fixation duration, within ±30 degrees of goal vs near the opposite heading | 0.68 s vs 0.11 s |
| AC-6 turn bias, 10-90 degrees CCW of goal / CW of goal | +0.91 / -0.92 (saccades point toward the goal) |
| AC-7 residency near goal, first vs last quarter of the run | 0.49 vs 0.78 |
| AC-8 weights finite in every run | yes |
| NFR-3 run time for the 20 runs | about 35 s |

## Artifacts on disk

Running the demo writes under [`results/demo/`](../../results/demo/README.md):

- `nbdev-test` → `quick/*.png` and `quick/metrics.json` (5 s run)
- `nbdev-test --flags slow` → also `full/*.png` and `full/metrics.json` (20 × 240 s, AC-5–AC-8 fields)

`basis.png` lives in `results/demo/` (shared).

## Goal

Ship one notebook (`nbs/demo.ipynb`) that runs the paper's **flexible policy** model end to end:

1. Build an agent whose fixations and saccades depend on its heading through 16 von Mises basis functions.
2. Put it in a 96-position circular arena that rewards being near a goal heading.
3. Train its weights online with the policy-gradient rule from the paper.
4. Show that it learns the expected behaviour: long fixations at the goal, and saccades biased toward the goal (the paper's Fig 2d-e).

## Files in this spec

| File | What it covers |
|------|----------------|
| [RUN.md](RUN.md) | How to install dev deps, run quick/full demo via `nbdev-test` or Jupyter, outputs, troubleshooting |
| [requirements.md](requirements.md) | What the demo must do, quality requirements, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions |
| [design-low-level.md](design-low-level.md) | Equations, function signatures, array shapes, numerics |
| [tasks.md](tasks.md) | Ordered implementation tasks with "done when" checks |

## Source of the model

All equations and parameter values come from the SI section "Reinforcement learning framework" of
Dan, Hulse, Kappagantula, Jayaraman, Hermundstad, *A neural circuit architecture for rapid learning in goal-directed navigation*
(Neuron 2024, https://doi.org/10.1016/j.neuron.2024.04.036):

- Policy: Eqs. 12 and 17 (fixation drift-diffusion, saccade direction bias, sigmoid bounds).
- Training: Eqs. 13-16 and 18 (policy gradient), Eq. 19 (reward), Algorithms 1-2.
- Parameters: Table 1 ("General policy parameters" and "Parameters for flexible policy").

The numbers were read from the 2022 manuscript. Check them against the published version before final tuning.

## Scope decision

The paper has three model variants. This demo covers only the first one.

| Variant | Paper figures | In this demo? |
|---------|---------------|---------------|
| Flexible policy (basis functions + policy gradient) | Fig 2d-e | Yes |
| Pre-structured policy tethered to a goal heading, with bump jumps | Fig 2h, SI | No; see [specs/prestructured/](../prestructured/README.md) |
| Circuit model with Hebbian goal and compass weights | Figs 3-5 | No (future) |

The current code (`flexibleAgent`, `flexiblePolicy`) already implements most of the flexible policy's sampling step, so this variant needs the least new work.

## Changes to Phase 1 code

Phase 1 is described in the plan doc (`explrl_issue_scan` plan). This spec deliberately changes three things from it:

| Phase 1 behaviour | Change in this spec | Why |
|-------------------|---------------------|-----|
| saccade `dx` is converted to arena units (`* 96/360`) and rounded, while `theta` is in radians | `dx` is in radians and not rounded; `theta` and `_heading_index` stay as they are | design decision D1 |
| `samplePolicy()` returns `(dx, dt, integ)` | returns a `Step` record | design decision D4 |
| `wParams` needs at least 6 values | exactly 6 values | match `Params` |

The README example in `nbs/index.ipynb` changes with these (task T3).

## Decisions (formerly open questions)

| ID | Question | Answer |
|----|----------|--------|
| Q1 | How are the basis functions normalized? (GETBASISFUNCTIONS from the MATLAB code is not available) | **Decided: peak of 1**, `exp(kappa * (cos(theta - mu) - 1))` |
| Q2 | Saccade duration: text says 300 ms, Table 1 says 320 ms | **Decided: 320 ms** (Table 1) |
| Q3 | Drift-rate range: text says 0.01-1.01, but Table 1 (fM,F = 10) gives 0.01-10.01 | **Decided: Table 1 values** (fixation durations about 79 ms to 79 s) |
| Q4 | Heading state: radians (current Phase 1 code) or integer arena position 0-95 | **Decided: radians**, with nearest-column basis lookup (design D1) |
| Q5 | Reward is given on every 1 ms fixation step (Algorithm 1). Keep that, or reward only after saccades? | **Decided: every step**, as in Algorithm 1 |
| Q6 | Do we have access to the original MATLAB scripts to check results against? | **Decided: no.** Success is judged only by the qualitative shape of Fig 2d-e (AC-5 to AC-8) |
| Q7 | How many training runs to average (the paper uses 100)? | **Decided: 20 by default**, `nRuns` adjustable for a 100-run reproduction |
