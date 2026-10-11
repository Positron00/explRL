# Requirements: explRL full demo

Terms used below:

- **Heading**: the agent's orientation in the arena, a continuous angle in radians in `[0, 2*pi)`. Clockwise turns increase it.
- **Basis column**: one of `nx = 96` evenly spaced headings at which the basis functions are tabulated; the policy uses the column nearest the current heading.
- **Goal heading**: the heading where reward is highest.
- **Fixation**: holding the heading still for one sample of `delT = 1 ms`.
- **Saccade**: a fast turn of random size, lasting `tS = 320 ms`.
- **Drift rate** `nu(theta)`: how fast the fixation integrator rises; a low drift rate means long fixations.
- **Turn bias** `2*pR(theta) - 1`: +1 means always turn clockwise, -1 always counter-clockwise.
- **Run**: one training session of `Ttot = 240 s` simulated time from fresh weights.

## Functional requirements

### Parameters
- **FR-1** The package shall provide one parameter object holding all fixed values from Table 1 of the paper (see design-low-level.md for the full list), with those values as defaults.
- **FR-2** The user shall be able to override any parameter when creating the object.

### Basis functions
- **FR-3** The package shall build a matrix of `nb = 16` von Mises basis functions with concentration `kappa = 8`, evenly spaced around the circle and evaluated at all `nx` headings. Shape: `(nb, nx)`.

### Agent and policy
- **FR-4** The agent's heading shall be a continuous angle in radians, always wrapped into `[0, 2*pi)`.
- **FR-5** On each step the agent shall either fixate (heading unchanged, duration 1 sample) or saccade (heading changes by a lognormal turn drawn in degrees and converted to radians without rounding, duration `tS`), following Algorithm 2 of the paper.
- **FR-6** Each step shall return a record with everything the learning rule needs: heading before the step, integrator before the step, integrator change, fixation or saccade, turn direction, heading change and duration.
- **FR-7** The agent shall use its own random number generator, created from a seed, so that runs can be repeated exactly.

### Environment
- **FR-8** The package shall provide a circular arena (one full turn, in radians) with a goal heading.
- **FR-9** The arena shall compute reward with Eq. 19: `R = (pi/10) * (1/2 - d)`, where `d` is the wrapped angular distance to the goal in radians.
- **FR-10** The arena shall apply a heading change and return the new (wrapped) heading and its reward.

### Learning
- **FR-11** The package shall compute the gradient of the log-probability of the step just taken, with respect to all `2 * nb` weights (Eqs. 13-16 and 18).
- **FR-12** After each step, the weights shall be updated as `omega <- omega + lr * r * grad`, where `r` is the reward at the new heading and `lr` defaults to 1 (the paper uses the reward itself as the step size).
- **FR-13** `RL.chooseAction` and `RL.updateParams` shall be implemented by a policy-gradient subclass. The base `RL` class keeps raising `NotImplementedError`.

### Training and evaluation
- **FR-14** `train_agent` shall run Algorithm 1 for `Ttot` seconds of simulated time and return a history of start times, headings, step types, step durations and rewards.
- **FR-15** `evaluatePolicy` shall return, for every basis column, the drift rate, the rightward-saccade probability, the mean fixation duration `aF / nu` and the turn bias `2*pR - 1`.
- **FR-16** A helper shall run several independent training runs (different seeds; 20 by default in the demo, adjustable up to the paper's 100) and return, for each run, its policy evaluation, its residency and its final weights.
- **FR-17** A helper shall compute residency: the fraction of time spent within +/-45 degrees of the goal, in equal time bins across a run, weighting each step by its duration.
- **FR-18** `loadAgent` and `loadEnv` in `explRL.core` shall build a ready-to-train agent (weights start at `omegaF = 0.1`, `omegaS = 0`, random starting heading, learning rate from `Params.lr`) and arena from a parameter object and a seed. One seed shall fix both the starting heading and all later random draws.

### Demo notebook
- **FR-19** `nbs/demo.ipynb` shall show, in order:
  1. the parameters and a plot of the basis functions;
  2. one training run: heading over time for the first and last 20 s (or half the run, if shorter), with saccades marked;
  3. the learned drift rate, fixation duration and turn bias for that run;
  4. the average over several runs of fixation duration and turn bias versus heading relative to the goal (the analogue of Fig 2d-e);
  5. residency near the goal over training time;
  6. a short written summary of what the plots show.

## Quality requirements

- **NFR-1 Reproducibility**: the same seed and parameters shall give the same results.
- **NFR-2 Fast tests**: all normal (non-slow) notebook tests shall finish in under 60 s on a laptop and in CI.
- **NFR-3 Demo run time**: the full demo notebook, with default settings, shall finish in under 10 minutes on a laptop.
- **NFR-4 Dependencies**: the library shall depend only on `numpy`. `matplotlib` is needed only for the demo and goes in the `dev` extras.
- **NFR-5 nbdev workflow**: all code is written in notebooks and exported; generated `.py` files are not edited by hand.
- **NFR-6 Readability**: files stay under about 200 lines, every public function has a docstring, and bad inputs raise clear `ValueError` / `TypeError` messages.
- **NFR-7 Numerical safety**: probabilities used in divisions shall be clamped away from 0 and 1, and no step shall produce `nan` or `inf` weights.

## Acceptance criteria

Checks that run in normal tests:

- **AC-1** Every FR above has at least one test cell.
- **AC-2** The analytic gradient (FR-11) matches a finite-difference estimate to within 1e-4 relative error, for both a fixation and a saccade step.
- **AC-3** A positive reward after a clockwise saccade increases `pR` at that heading; a negative reward decreases it.
- **AC-4** Two runs with the same seed give identical histories; different seeds give different histories.

Checks that run in slow tests (averaged over at least 20 runs of 240 s, goal at `pi` = 180 degrees):

- **AC-5** Mean fixation duration within +/-30 degrees of the goal is larger than within +/-30 degrees of the opposite heading.
- **AC-6** Mean turn bias is positive for headings 10-90 degrees counter-clockwise of the goal, and negative for headings 10-90 degrees clockwise of the goal (saccades point toward the goal).
- **AC-7** Residency near the goal in the last quarter of a run is higher than in the first quarter, on average.
- **AC-8** No run produces `nan` or `inf` weights.

## Out of scope

- The pre-structured goal-heading policy and bump jumps (Fig 2h, SI).
- The circuit model with compass and goal weights and Hebbian learning (Figs 3-5).
- Safe and danger zones with +1 / -1 reward (Eq. 40), and PI scores.
- The reflexive heat-escape drift process (Eqs. 8-9).
- Graphics or interactive environments; a command-line tool; publishing to PyPI.
- Matching the MATLAB output number for number (we do not have the scripts).
