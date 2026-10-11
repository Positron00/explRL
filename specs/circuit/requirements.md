# Requirements: circuit model

Terms used below. Headings are integer grid indices `0..N-1` (`N = 32`, one step = 11.25 degrees) unless stated; degrees only in plots and text.

- **Arena heading** `a`: the model fly's true orientation. Reward depends on it.
- **Compass heading** `c`: the position of the heading bump. During a saccade it moves by the same number of steps as `a`, in the **opposite** direction (Eq. 26 text); after a saccade it may **jump** by `N/2` (180 degrees).
- **Mirror sum** `s = (a + c) mod N`: constant during saccades, changes by `N/2` on a jump. It links compass and arena coordinates: compass heading `c` corresponds to arena heading `s - c`.
- **Goal weights** `wG`: `N` values in `[0, 1]`, one per goal neuron (Eq. 29). Their circular mean has angle `thetaG` (the **goal heading**, compass coordinates) and length `rG`; their sum is `|wG|`.
- **Goal strength**: `rG / (N / pi)`, in `[0, 1]` (Q11).
- **Goal in the arena**: `s - thetaG`, wrapped. Because the two safe zones are 180 degrees apart, its distance to the nearest safe-zone center does not change when the bump jumps.
- **Compass weights** `wC`: `N x N` values in `[0, 1]`, from ring neuron `j` (receptive field at arena heading `j`) onto compass neuron `k`.
- **Scene**: *asymmetric* (ring neurons see one view per arena heading) or *symmetric* (two-fold: views at `a` and `a + N/2` are identical).
- **Ring activity** at arena heading `a`: 1 at `j = a`, 0.5 at `j = a +- 1`; for a symmetric scene also at `a + N/2` and its neighbors.
- **Map**: a fixed mirror sum `s`, pairing each arena heading `a` with compass heading `s - a`. **`pJ` along a map** is the jump probability at each such pair, using the ring activity of `a`; its mean over all `a` measures how stable that map is in an asymmetric scene. In a symmetric scene, headings `a` and `a + N/2` have the same ring activity, so their `pJ` values always add up to 1 and the mean is exactly 0.5 for any weights; there, stability is measured by the jump rate of a probe.
- **Probe**: a separate run of a copy of the agent with frozen weights, jumps on and learning off (Fig 5c). Its **jump rate** is the fraction of saccades followed by a jump.
- **Zones**: safe zones span 90 degrees centered at 90 and 270 degrees, danger zones the rest. A heading `d` (degrees) is safe if it lies in `[center - 45, center + 45)` for either center, which gives 16 safe and 16 danger grid steps. Valence `R = +1` (safe) or `-1` (danger) (Eq. 40).
- **PI score**: `(time in safe - time in danger) / total time`, counting fixation time.
- **Iteration**: one saccade, a possible jump, then one fixation (Algorithm 3).

## Functional requirements

### Parameters
- **FR-1** `Params` shall gain `nCirc = 32`, `kappaEB = pi`, `alphaC = 0.01`, `alphaG = 0.001`, `nuMax = 1.1`, `dtG = 0.1` (goal update step in seconds), with the checks in design-low-level section 1 (`nCirc` even and at least 4; `kappaEB`, `nuMax`, `dtG` positive; learning rates not negative). `BF`, `aF`, `sigF`, `muS`, `sigmaS`, `tS`, `Ttot` are reused.

### Populations and policy (Eqs. 26-37)
- **FR-2** The package shall give the EB bump profile `rEB(c)` (von Mises with `kappaEB`, scaled to `[0, 1]`; Q11) and the FB profile `rFB(c) = (cos(theta - theta_c) + 1) / 2`, as length-`N` arrays.
- **FR-3** The package shall compute goal statistics from `wG`: `thetaG`, `rG`, `|wG|` and goal strength.
- **FR-4** The package shall compute the left, fixation and right outputs from the population sums of Eqs. 30 and 32 (phase shifts +90, 180, -90 degrees; `BC = nuMax - |wG| / D`), then `dS = (1 + rR - rL) / 2` and `nuF = max(rF, 0) + BF` (Q3, Q4).
- **FR-5** The package shall build a sinusoidal goal `wG = g cos(theta - theta0) + 1/2` for `0 <= g <= 1/2`, and raise `ValueError` for other `g` (Fig 3d, 3i, 5).

### Compass stability (Eq. 27)
- **FR-6** The package shall return ring activity for an arena heading and a scene type.
- **FR-7** The package shall compute the jump probability `pJ = net(c) / (net(c) + net(c + N/2))`, where `net = activity @ wC` (Q8); `pJ = 0.5` if both are 0.

### Plasticity (Eqs. 38-39)
- **FR-8** The compass update for one saccade step shall be `wC[j, :] += alphaC * v^2 * act[j] * ((1 - rEB(c)) - wC[j, :])`, clipped to `[0, 1]`, with `v` the saccade size in radians (Q7-Q9).
- **FR-9** The goal update for one `dtG` step shall follow Eq. 39 with target `rFB(c)`: toward the target when `R > 0`, away from it when `R < 0`, no change when `R = 0`; with the Heaviside limits of Eq. 39 and a clip to `[0, 1]`.

### Arena
- **FR-10** `ZoneArena` shall hold `N`, the scene type and the zone layout, and give `isSafe(a)`, `valence(a)` and `ringActivity(a)`.

### Agent and learning rule
- **FR-11** `circuitAgent` shall hold `a`, `c`, `wC`, `wG` (on its `circuitPolicy`) and a seeded random generator; `c` starts equal to `a` (Algorithm 3). `circuitPolicy` shall reject weights of the wrong shape or outside `[0, 1]` (`ValueError`), and the agent shall reject other policy types (`TypeError`).
- **FR-12** Each iteration shall: (i) choose the saccade direction (CW with probability `dS` at the current `c`) and size (lognormal in degrees, then converted to radians); (ii) move `a` up and `c` down by one step per grid step for CW (the reverse for CCW; Q2, Q10), updating `wC` with the ring activity and compass heading of the current step, before moving, when compass learning is on; (iii) when jumps are on, draw a jump with probability `pJ` at the new `c`, using the ring activity of the new `a`; (iv) read the valence `R` at the new `a`; (v) draw the fixation length from `IG(mean = aF / nuF, shape = aF^2 / sigF^2)` with `nuF` at the new `c` (Q5, Q6); (vi) apply `ceil(fixDur / dtG)` goal updates when goal learning is on and `R != 0`. Simulated time grows by `tS + fixDur`.
- **FR-13** `CircuitRL` shall choose the next saccade (from the agent's policy), hold the two updates (FR-8, FR-9) and hold the switches for compass learning, goal learning and jumps.
- **FR-14** The random draws shall happen in a fixed order (direction, size, jump, fixation), so the same seed gives the same run.

### Training and evaluation
- **FR-15** `train_circuit` shall run iterations from an optional start time `t0` (default 0) until `t0 + Ttot`, so a run can continue the clock of an earlier one, and return a history with, per iteration: start time, `a` and `c` after the saccade and any jump, direction, steps, jumped, valence, fixation length, `thetaG` and goal strength after that iteration's goal updates, and the mirror sum.
- **FR-16** The package shall compute from a history: the goal in the arena and its distance (degrees) to the nearest safe-zone center; any recorded value held over time on a time grid (as `heldGoal` in the pre-structured demo); the PI score; and the readout (mean fixation length and turn bias per heading relative to the goal in the arena, where the turn bias at a heading uses the next saccade, which starts there). From compass weights and a map it shall compute `pJ` along the map and the most stable compass heading (circular mean of `1 - pJ` over compass headings, Fig 5).
- **FR-17** `probe` shall copy an agent, freeze its weights, run it with its own seed for a given time (default 240 s) with jumps on and learning off, and return its history, PI score and jump rate (Fig 5c). The original agent, its weights and its generator shall not change.
- **FR-18** `runManyCircuit` (in `explRL.circuit_runs`) shall run several seeded model flies for one of four named set-ups: `'goal'` (Fig 3i), `'compass_asym'` and `'compass_sym'` (Fig 4), and `'both'` (Fig 5, including the probes at 0, 300, 600, 900 and 1200 s of training), with the scenes, starting weights, phases and run lengths in design-low-level section 8b. In `'both'`, the joined training history shall have increasing times. Run lengths shall be adjustable by name (Q12); an unknown set-up or length name raises `ValueError`. It shall return, per fly, the history, final weights and that set-up's summary numbers.
- **FR-19** `loadCircuitAgent` in `explRL.core` shall build an agent (with its policy and `CircuitRL`) from parameters, a seed, optional starting weights and the three switches. Defaults: random uniform `wC`, sinusoidal `wG` with random `g` in `(0.05, 0.5)` and random `theta0`, all switches on. One seed shall fix the starting heading, the starting weights and all later draws.

### Demo notebook
- **FR-20** `nbs/demo_circuit.ipynb` shall show, in order: (1) policy curves for a weak and a strong goal (Fig 3c-d); (2) one goal update after reward and after punishment, and repeated reward at one heading (Fig 3g-h); (3) goal learning over time with a perfect compass: distance to safe and strength (Fig 3i); (4) compass weights and jump probability after learning in an asymmetric and a symmetric scene, and the fixation readout with frozen weights (Fig 4b-d); (5) both systems together: goal distance, strength and probe PI over time, the spread of final PI scores, and the angle between the goal heading and the most stable compass heading at the end (Fig 5); (6) a short summary with the measured acceptance values.
- **FR-21** The notebook shall save figures and `metrics.json` under `results/demo_circuit/` with the existing helpers (`demo_name='demo_circuit'`): deterministic plots at the top level, simulation plots and metrics in `quick/` or `full/` (file list in design-low-level section 11). Normal tests run the quick version (2 model flies); the full version (`#| slow`) uses 20.

## Quality requirements

- **NFR-1 Reproducibility**: the same seed and parameters give the same run.
- **NFR-2 Fast tests**: all normal tests, including the existing ones, finish in under 60 s.
- **NFR-3 Demo run time**: the full demo finishes in under 5 minutes on a laptop (measured: about 21 s; normal tests run the quick version in about 4 s).
- **NFR-4 Dependencies**: library code uses only `numpy`; `matplotlib` only in the demo.
- **NFR-5 nbdev workflow**: all code lives in notebooks and is exported.
- **NFR-6 Readability**: exported files stay under about 200 lines; every public function has a docstring; bad inputs raise clear `ValueError` / `TypeError`.
- **NFR-7 Numerical safety**: weights always in `[0, 1]`; `dS` and `pJ` always in `[0, 1]`; `nuF >= BF`.
- **NFR-8 No regressions**: the flexible and pre-structured demos and their tests keep passing.

## Acceptance criteria

Normal tests:

- **AC-1** Every FR has at least one test cell.
- **AC-2** For `wG = 0.5 cos(theta - theta_8) + 1/2`: `dS` from the sums equals `1/2 + rG/(2D) sin(theta_c - thetaG)` to within 1e-9 at every `c`; `dS` is largest at `c = 16` (90 degrees CW of the goal) and lies in `[0.167, 0.833]`; `nuF` is smallest at `c = 8`; `D = 12`.
- **AC-3** Goal statistics of a sinusoidal goal: `thetaG = theta0` and `rG = g N / 2` to within 1e-9.
- **AC-4** Goal plasticity at a fixed compass heading: reward moves `thetaG` toward that heading and raises the strength; punishment moves `thetaG` away; `R = 0` changes nothing; weights stay in `[0, 1]` (Fig 3g-h).
- **AC-5** Compass plasticity: 1000 random saccades (direction 50/50) on a fixed map (no jumps) in an asymmetric scene, from random weights, lower the mean `pJ` along that map from about 0.5 to below 0.15 (prototype: 0.49-0.53 to 0.053); weights stay in `[0, 1]`.
- **AC-6** Over 20 000 seeded draws at one compass heading, the CW rate is within 0.01 of `dS`; `pJ` is 0.5 for equal net weights.
- **AC-7** Same seed gives identical histories; different seeds differ; without jumps the mirror sum never changes; with jumps it only changes by `N/2`.

Slow tests (`#| slow`, 20 model flies, seeds 0-19, set-ups from FR-18). Values are averaged over flies:

- **AC-8** `'goal'` (perfect compass: no compass learning, no jumps, 1200 s): the time average of the goal's distance to the nearest safe center over the last quarter (held values on a 1 s grid) is smaller than at the start, and the final strength is larger than at the start (measured: 45.2 to 11.0 degrees, 0.39 to 0.82).
- **AC-9** `'compass_asym'` (fixed goal, no jumps, 2400 s): mean `pJ` along the final map below 0.15, and the probe jump rate after training below 0.2. `'compass_sym'` (fixed goal, jumps, 4800 s): the probe jump rate after training above 0.3 (measured: asymmetric map `pJ` 0.057 and probe jump rate 0.088, from about 0.5 with random weights; symmetric probe jump rate 0.418).
- **AC-10** `'both'`: goals start at a danger center (90 degrees from safe). At the end of the 1200 s of training, the goal distance is smaller than at the start, and the probe PI at 1200 s is higher than at 0 s and above 0 (measured: 90 to 10.9 degrees; PI -0.23 to 0.24). The spread of single-fly final probe PI scores is reported, not asserted (measured: -0.20 to 0.64).

## Out of scope

- The flexible ring-to-compass mapping with variable offsets beyond 0 and 180 degrees.
- Learning the policy's fixed structure (phase shifts, `nuMax`, `BC`).
- 1000-fly runs, and the time alignment to the weakest goal in Figs 5e-g (`nRuns` stays adjustable).
- Fig 5's five starting goal strengths and goals at both danger centers: every fly starts with strength 0.67 at arena 0 degrees (both danger centers are 90 degrees from safe).
- A switch for the literal Algorithm 4 order (Q6); the prototype result is recorded in the README instead.
- Matching MATLAB output (no scripts available).
- Variable saccade durations; `tS` stays 0.32 s (Methods say 300 ms; Table 1 and the earlier demos use 320 ms).
