# Spec: pre-structured (setpoint) policy with bump jumps

Status: implemented (2026-10-10); tasks T1-T10 done. **How to run:** [RUN.md](RUN.md). Quick: `nbdev-test --n-workers 0 nbs/demo_prestructured.ipynb`; full AC-8–AC-10: add `--flags slow`. Each takes about a second.

## Goal

Add the paper's second model variant and a demo notebook (`nbs/demo_prestructured.ipynb`) that:

1. Builds an agent whose fixations and saccades depend on the difference between its **compass heading** and a single **goal heading**, through fixed sinusoidal curves (no basis functions, no weight vector).
2. Lets the compass heading **jump by 180 degrees** after saccades, with a jump probability that depends on the compass heading relative to the goal (the instability caused by a two-fold symmetric visual scene).
3. Shows the **bimodal behavioural readout** in arena coordinates that this produces (the paper's Fig 2h).
4. Learns the **goal heading** itself by policy gradient after each saccade, and shows it moving toward the rewarded arena heading.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | What the variant and demo must do, quality requirements, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions, risks |
| [design-low-level.md](design-low-level.md) | Equations, function signatures, data records, numerics, expected values |
| [RUN.md](RUN.md) | How to run the demo via `nbdev-test` or Jupyter |
| [tasks.md](tasks.md) | Ordered implementation tasks with "done when" checks |

## Results

20 runs of 240 s (seeds 0-19), reward goal at 180°, Table 1 setpoint parameters, `lrG = 1`, no tuning:

| Check | Result |
|-------|--------|
| AC-8 mean fixation in the goal / anti-goal / side windows | 11.5 s / 10.6 s / 2.5 s |
| AC-9 `|thetaG − goal|`, start vs time average over the last quarter (no jumps) | 1.67 rad → 0.51 rad |
| AC-10 distance to the nearer of {goal, anti-goal}, with jumps | 0.84 → 0.74 rad (reported; no assert) |
| Run time, all three conditions | about 1 s |

One change from the original plan (T9): AC-9 and AC-10 average over **time** in the last quarter, not over events. Fixations near the goal are heavy-tailed (one lasted 223 s), so 7 of the 20 no-jump runs had no event at all in the last quarter. The goal heading is held between updates, and `heldGoal` gives its value at any time.

## Source of the model

From the SI section "Reinforcement learning framework", subsection "Pre-structured policy tethered to a single goal heading" of Dan, Hulse, Kappagantula, Jayaraman, Hermundstad, *A neural circuit architecture for rapid learning in goal-directed navigation* (Neuron 2024, https://doi.org/10.1016/j.neuron.2024.04.036):

- Policy: Eq. 20 (drift rate and turn probability as sinusoids of compass minus goal heading).
- Bump jumps: Eqs. 21-22 (jump probability, 180 degree jump).
- Effective readout in arena coordinates: Eq. 23 (Fig 2h).
- Training: Eqs. 24-25 (policy-gradient update of the goal heading after each saccade), with the saccade distribution of Eq. 12 and the reward of Eq. 19.
- Parameters: Table 1, "General policy parameters" and "Parameters for setpoint policy".

The text was read from the 2022 manuscript (`Dan_Hermundstad 2022 MS.pdf`). Two printed signs look like typos (Q1, Q2). If you have the published SI, check those two equations there first.

## Relation to the existing code

| Already there (flexible-policy demo) | Reused as is | New for this variant |
|---|---|---|
| `Params` | yes, plus 8 new fields | setpoint gains and baselines, jump size, goal learning rate |
| `HeadingArena` (Eq. 19 reward, arena coordinates) | yes, unchanged | - |
| `Policy`, `Agent`, `RL` base classes | yes, as parents | `prestructuredPolicy`, `prestructuredAgent`, `GoalHeadingRL` |
| `vonMisesBasis`, `flexibleAgent`, `PolicyGradientRL` | not used | - |
| `train_agent` (1 ms steps) | not used | event-based loop: one fixation plus one saccade per iteration |
| `demo_artifact_dir`, `save_demo_figure`, `save_demo_metrics` | yes, with a new folder argument (`name` on the first, `demo_name` on the other two) | artifacts go to `results/demo_prestructured/` |
| `loadEnv` | yes, unchanged | `loadPrestructuredAgent` |

## Decisions (formerly open questions)

| ID | Question | Answer |
|----|----------|----------------|
| Q1 | Eq. 21 is printed as `pJ = GJ/2 (1 + cos(thetaC - thetaG)) + BJ`, which makes jumps **most** likely at the goal. The text, the Methods ("least likely to occur at the preferred heading"), and Fig 4i data say the opposite. With the printed sign the readout is not bimodal (longest fixations at ±90 degrees). Use `1 - cos` instead? | **Decided: `1 - cos`.** Gives fixation peaks at the goal (8.8 s) and anti-goal (3.2 s) with troughs at ±90 degrees (1.8 s), matching Fig 2h |
| Q2 | Eq. 25 is printed with a leading minus sign, but differentiating Eq. 20 gives `d dS / d thetaG = +GS/2 cos(thetaC - thetaG)`. Which sign? | **Decided: follow the derivative**, and prove it with a finite-difference test (as done for the flexible demo) |
| Q3 | Eq. 24 uses only the saccade term, although the fixation drift rate also depends on `thetaG`. Add the fixation-duration term? | **Decided: saccade term only**, as in the paper |
| Q4 | Eq. 24 has no learning rate; the reward is the step size. One update can move `thetaG` by several radians (reward down to -0.83, gradient up to 9). Add a factor `lrG`? | **Decided: add `lrG`, default 1** (paper behaviour). Lower it only if AC-9 fails, and record why |
| Q5 | Run length. Fixations average about 16 s near the goal (no jumps), so a 240 s run has only about 25 events (prototype: 26), and only that many goal updates. Keep `Ttot = 240 s`? | **Decided: keep 240 s as the default**; the slow learning tests may use a longer `Ttot` if needed (decided in T9 and recorded) |
| Q6 | Starting goal heading for learning runs | **Decided: random uniform from the run's seed** (like the starting arena heading); `thetaG0` overrides it |
| Q7 | Scope of the demo: Fig 2h only (fixed goal, jumps), or Fig 2h plus learning of the goal heading? | **Decided: both.** The learning rule is part of this variant in the SI |
| Q8 | Saccade direction in compass vs arena coordinates. This SI section assumes they move together; the circuit section (Figs 3-5) has them move in opposite directions | **Decided: move together**, as in this section. Opposite motion belongs to the circuit-model spec |

## Prototype check (2026-10-10, before implementation)

Kept for history; the measured results above supersede it. A throwaway numpy script of the design (not committed; 20 runs, reward goal at 180 degrees, all decisions above; AC-9/AC-10 measured over events, see above) gave:

| Check | Result | Meaning |
|---|---|---|
| AC-8, fixed goal with jumps, 240 s | mean fixation 11.5 s within ±30 degrees of the goal, 10.6 s within ±30 degrees of the anti-goal, 2.5 s within ±30 degrees of goal ± 90 degrees | bimodal, passes clearly |
| AC-9, learning without jumps, 240 s | mean `|thetaG - goal|` 1.61 rad at the start, 0.64 rad over the last quarter | passes at 240 s |
| AC-10, learning with jumps, 240 s / 2400 s | distance to the nearer of goal / anti-goal 0.76 to 0.79 rad / 0.76 to 0.68 rad | no clear convergence; stays reported only |
| Events per 240 s run | about 26 | Q5 estimate |

The simulated anti-goal peak (10.6 s) is much higher than Eq. 23 predicts (3.16 s), because in simulation the compass offset persists between jumps (design D4). Only the bimodal shape is required.

## Naming

The paper calls this variant both "pre-structured policy" (text) and "setpoint policy" (Table 1). The spec and code use **prestructured**; Table 1 parameter names (`GS`, `BS`, ...) are kept as is.
