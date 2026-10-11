# Requirements: pre-structured (setpoint) policy

Terms used below (radians everywhere in code; degrees only in plots and text):

- **Arena heading** `thetaA`: the agent's true orientation in the arena. Reward depends on it. Clockwise (CW) turns increase it.
- **Compass heading** `thetaC`: the agent's internal estimate of its heading (the heading bump). It moves with `thetaA` during saccades, but can **jump** by 180 degrees.
- **Offset**: `thetaC - thetaA`, wrapped. Starts at 0 and is always 0 or pi.
- **Goal heading** `thetaG`: an internal heading, in compass coordinates, around which the policy is built. It is fixed in Fig 2h runs and learned in learning runs.
- **Reward goal**: the arena heading where Eq. 19 reward is highest (the arena's `goal`). Not the same thing as `thetaG`.
- **Event**: one fixation (duration drawn whole) followed by one saccade (fixed duration `tS`), then a possible bump jump, then a possible goal update.
- **Readout**: mean fixation duration and turn bias as a function of **arena** heading relative to the reward goal. Each event is placed at its arena heading before the saccade, which is where its fixation happened.
- **Relative heading** `rel = angdiff(thetaA, goal)` in degrees, in `[-180, 180)`; positive means CW of the goal.
- **Toward the goal**: turn bias with the opposite sign to `rel` (CCW when CW of the goal, and the reverse).
- **Windows** used by the acceptance checks: *goal* `|rel| <= 30`, *anti-goal* `|rel| >= 150`, *side* `60 <= |rel| <= 120` (both sides pooled).

## Functional requirements

### Parameters
- **FR-1** `Params` shall gain the Table 1 "setpoint policy" values as defaults: `GS = 0.9`, `BS = 0`, `GF = 0.8`, `BF = 0.05`, `GJ = 0.7`, `BJ = 0.05`, `thetaJ = pi` (180 degrees), plus a goal learning-rate factor `lrG = 1` (Q4).
- **FR-2** `Params` shall reject values that make a probability leave `[0, 1]` or a drift rate non-positive (see design-low-level section 1).

### Policy curves
- **FR-3** The package shall compute the turn probability `dS(thetaC; thetaG)` and drift rate `nuF(thetaC; thetaG)` of Eq. 20, element-wise on arrays.
- **FR-4** The package shall compute the jump probability `pJ(thetaC; thetaG)` with the sign decided in Q1.
- **FR-5** The package shall compute the effective readout of Eq. 23 for an array of arena headings: drift rate, turn probability, mean fixation duration `aF / nu` and turn bias `2 dS - 1`.

### Agent
- **FR-6** `prestructuredAgent` shall hold an arena heading, a compass heading (starting equal to the arena heading) and its own seeded random number generator.
- **FR-7** Each call to `samplePolicy` shall produce one event: (i) a fixation duration drawn from the inverse Gaussian `IG(mean = aF / nuF, shape = aF^2 / sigF^2)`; (ii) a saccade direction (CW with probability `dS`) and size (lognormal in degrees, converted to radians); (iii) the post-saccade compass heading; (iv) a jump draw with probability `pJ` at the post-saccade compass heading, adding `thetaJ` if it jumps. All policy terms use the compass heading **before** the saccade, except the jump.
- **FR-8** Each event shall be returned as a record with everything the learning rule and the readout need (see design-low-level section 4).
- **FR-9** The random draws shall happen in a fixed order, so the same seed always gives the same events.

### Learning
- **FR-10** `GoalHeadingRL` shall compute the gradient of the log saccade-direction probability with respect to `thetaG` (Eqs. 24-25, sign from Q2, saccade term only per Q3).
- **FR-11** After each event, the goal heading shall be updated as `thetaG <- wrap(thetaG + lrG * r * grad)`, where `r` is the Eq. 19 reward at the post-saccade **arena** heading.
- **FR-12** Setting `lrG = 0` shall give a fixed-goal run (used for the Fig 2h simulations).

### Training and evaluation
- **FR-13** `train_prestructured` shall run events until simulated time reaches `Ttot` (each event lasts its fixation duration plus `tS`) and return a history with, per event: start time, arena and compass heading before the saccade, fixation duration, saccade direction, whether the bump jumped, reward and the goal heading after the update.
- **FR-14** `readout` shall bin a history by relative heading (arena heading before the saccade) and return, per bin, the plain mean fixation duration (comparable with `aF / nu` in Eq. 23), the turn bias (mean saccade direction) and the event count, with `nan` for empty bins.
- **FR-15** `runManyPrestructured` shall run several independent seeded runs and return, for each, its history, its readout, its starting goal heading `thetaG0` and its observed jump rate.
- **FR-15a** `heldGoal` shall return the goal heading in effect at given times: `thetaG0` until the first update, then the value after the latest update, where each event's update happens at its end (`t + fixDur + tS`).
- **FR-16** `loadPrestructuredAgent` in `explRL.core` shall build a ready-to-run agent from a parameter object, a reward goal, a seed, an optional starting goal heading (default per Q6) and a flag that turns learning off (`lrG = 0`).

### Demo notebook
- **FR-17** `nbs/demo_prestructured.ipynb` shall show, in order:
  1. the parameters and the three policy curves (Eqs. 20-21) against compass minus goal heading;
  2. the effective readout of Eq. 23 against arena minus goal heading, with jumps on and off (the analytic Fig 2h);
  3. the simulated readout of fixed-goal runs with jumps, over several runs (the simulated Fig 2h);
  4. the goal heading over time in learning runs without jumps, and then with jumps;
  5. a short written summary with the measured acceptance values.
- **FR-18** The notebook shall save its figures and a `metrics.json` under `results/demo_prestructured/` (deterministic plots at the top level, simulation plots and metrics in `quick/` or `full/`) using the existing artifact helpers with the folder name `demo_prestructured` (file list in design-low-level section 11).

## Quality requirements

- **NFR-1 Reproducibility**: the same seed and parameters give the same events.
- **NFR-2 Fast tests**: all normal (non-slow) tests, including the existing ones, finish in under 60 s.
- **NFR-3 Demo run time**: the full demo notebook finishes in under 5 minutes on a laptop (measured: about 1 s).
- **NFR-4 Dependencies**: library code uses only `numpy` (the inverse Gaussian is `numpy.random.Generator.wald`); `matplotlib` only in the demo.
- **NFR-5 nbdev workflow**: all code lives in notebooks and is exported.
- **NFR-6 Readability**: exported files stay under about 200 lines; every public function has a docstring; bad inputs raise clear `ValueError` / `TypeError`.
- **NFR-7 Numerical safety**: probabilities used in divisions are clamped away from 0 and 1; no run produces `nan` or `inf` goal headings.
- **NFR-8 No regressions**: the flexible-policy demo and its tests keep passing unchanged (apart from the artifact helper's new optional argument).

## Acceptance criteria

Normal tests:

- **AC-1** Every FR has at least one test cell.
- **AC-2** With default parameters, the Eq. 23 readout is bimodal: mean fixation duration at `rel = 0` and at `rel = 180` is higher than at `rel = ±90`; the turn bias points toward the goal for `0 < |rel| < 100` and away from it for `115 < |rel| < 180` (expected values in design-low-level section 7).
- **AC-3** With `GJ = BJ = 0` the Eq. 23 readout equals the Eq. 20 curves evaluated at the arena heading (unimodal, one fixation peak at the goal).
- **AC-4** The analytic goal gradient matches a central finite-difference estimate of `logPiS` to within 1e-6 absolute error, for a CW and a CCW saccade at several headings.
- **AC-5** With a small step (`lr * |r| <= 0.01`), a positive reward after a CW saccade moves `thetaG` so that `dS` at that compass heading increases, and a negative reward makes it decrease.
- **AC-6** Over 20 000 seeded calls of `samplePolicy` from one fixed compass heading and goal: the observed CW rate is within 0.01 of `dS` at that heading, and the observed jump rate is within 0.01 of the mean predicted `pJ` at the post-saccade compass headings of those calls (the jump is drawn after the saccade, so its probability varies from call to call).
- **AC-7** Same seed gives identical histories; different seeds give different histories; the offset is always 0 or pi.

Slow tests (`#| slow`, 20 runs of 240 s, reward goal at pi). AC-8 window means pool all events of all runs:

- **AC-8** Fixed-goal runs with jumps (`thetaG0 = goal`, `learn=False`): the mean fixation duration in the *goal* window and in the *anti-goal* window are both larger than in the *side* window (simulated Fig 2h; measured: 11.5 s, 10.6 s, 2.5 s).
- **AC-9** Learning runs without jumps (`GJ = BJ = 0`): averaged over runs, the time average of `|angdiff(thetaG, goal)|` over the last quarter of the run (using `heldGoal` on a 1 s grid) is smaller than `|angdiff(thetaG0, goal)|` (measured: 0.51 vs 1.67 rad). Time, not events, because some runs have no event in the last quarter (heavy-tailed fixations).
- **AC-10** Learning runs with jumps (defaults): no `nan` / `inf` in any run; the same comparison, using the distance from the goal heading to the nearer of {goal, anti-goal}, is **reported** in the summary and in `metrics.json`, not asserted (decided in T9: measured 0.84 to 0.74 rad, no clear convergence).

## Out of scope

- The circuit model (compass and goal weight vectors, ring neurons, Hebbian rules; Eqs. 26-39, Algorithms 3-4, Figs 3-5).
- Compass and arena headings moving in opposite directions during saccades (Q8).
- Safe and danger zones with ±1 reward and PI scores (Eq. 40).
- The "visual pattern" variant of Eq. 19 (preference for a pattern with two orientations).
- Variable saccade durations (Eq. 11); `tS` stays fixed.
- Learning the gains and baselines (`GS`, `GF`, `GJ`, `BS`, `BF`, `BJ`); only `thetaG` is learned.
- Matching MATLAB output (no scripts available).
