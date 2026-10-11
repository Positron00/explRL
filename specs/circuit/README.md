# Spec: circuit model with Hebbian compass and goal weights

Status: implemented (2026-10-10); tasks T1-T10 done. **How to run:** [RUN.md](RUN.md). Quick: `nbdev-test --n-workers 0 nbs/demo_circuit.ipynb`; full AC-8–AC-10: add `--flags slow` (about 21 s). Code: `explRL/circuit.py`, `circuit_agent.py`, `circuit_train.py`, `circuit_runs.py`, `ZoneArena` in `envs.py`, `loadCircuitAgent` in `core.py`.

## Goal

Add the paper's third model variant: a circuit of heading-tuned neuron populations that implements the pre-structured policy, and learns with Hebbian plasticity instead of policy gradient. A demo notebook (`nbs/demo_circuit.ipynb`) shall:

1. Build the policy from **goal weights** `wG` (32 values): saccade direction and fixation length depend on how the compass bump overlaps the goal weights (Fig 3a-d).
2. Learn the goal weights with reward-gated Hebbian plasticity in an arena with two **safe** and two **danger** zones, and show the goal moving into a safe zone and getting stronger (Fig 3g-i).
3. Learn **compass weights** `wC` (32 ring neurons x 32 compass neurons) with anti-Hebbian plasticity during saccades, and show that a two-fold symmetric scene makes the compass unstable (bump jumps of 180 degrees), while an asymmetric scene does not (Fig 4).
4. Let both weight sets learn together, starting with the goal in a danger zone, and show the goal moving to a safe zone and the PI score rising, with large differences between model flies (Fig 5).

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | What the model and demo must do, quality requirements, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions, risks |
| [design-low-level.md](design-low-level.md) | Equations, function signatures, data records, expected values |
| [tasks.md](tasks.md) | Ordered implementation tasks with "done when" checks |
| [RUN.md](RUN.md) | How to run the demo via `nbdev-test` or Jupyter |

## Results

20 flies per set-up (seeds 0–19), Table 1 circuit parameters, no tuning:

| Check | Result |
|-------|--------|
| AC-8 goal distance to safe (start → time average over the last quarter) | 45.2° → 11.0° |
| AC-8 goal strength (start → end) | 0.39 → 0.82 |
| AC-9 asymmetric mean map `pJ` / probe jump rate | 0.057 / 0.088 (about 0.5 with random weights) |
| AC-9 symmetric probe jump rate | 0.418 |
| AC-10 goal distance (start → end) | 90° → 10.9° |
| AC-10 probe PI (0 s → 1200 s of training) | −0.23 → 0.24 (single flies −0.20 to 0.64, reported) |
| Goal minus most stable compass heading at the end (Fig 5, reported) | 28° on average |
| Run time | full demo about 21 s; quick version about 4 s |

## Source of the model

From Dan, Hulse, Kappagantula, Jayaraman, Hermundstad, *A neural circuit architecture for rapid learning in goal-directed navigation* (Neuron 2024, https://doi.org/10.1016/j.neuron.2024.04.036), read from the 2022 manuscript (`Dan_Hermundstad 2022 MS.pdf`):

- SI "Reinforcement learning framework", subsection "Circuit Model": Eqs. 26-40, Algorithms 3-4.
- Methods "Circuit model summary" and the paragraphs on Figs 3, 4 and 5 (zone layout, ring receptive fields, run set-up).
- Table 1, "Parameters for circuit implementation of setpoint policy": `N = 32`, `kappa = pi`, `alphaC = 0.01`, `alphaG = 0.001`; plus the general policy parameters.

Several printed details disagree with each other or with the text (Q2-Q7 below). If you have the published SI, check those equations there first.

## Relation to the existing code

| Already there | Reused | New for this variant |
|---|---|---|
| `Params` | yes, plus 6 fields | grid size, bump width, two learning rates, `nuMax`, goal update step |
| `Policy`, `Agent`, `RL` base classes | yes, as parents | `circuitPolicy`, `circuitAgent`, `CircuitRL` (the Hebbian RL class planned in `specs/demo/design-high-level.md`) |
| `World`, `HeadingArena` (Eq. 19 reward) | `World` as parent; `HeadingArena` not used | `ZoneArena`: safe/danger zones (Eq. 40) and a visual scene for ring neurons |
| `prestructured_train.heldGoal` (value held between updates) | idea only | `circuit_train.heldValue` for any recorded value |
| `prestructured` event loop (fixation + saccade per iteration) | idea only | grid-based loop of Algorithm 3 with weight updates inside saccades and fixations |
| `numpy.random.Generator.wald` fixation draws | yes (Q5) | - |
| Artifact helpers with `demo_name` | yes | `results/demo_circuit/` (gitignored) |

## Decisions

All twelve were decided on 2026-10-10 as recommended. The prototype numbers below use these answers.

| ID | Question | Decided |
|----|----------|-------------|
| Q1 | Scope: Fig 3 (goal learning) only, Figs 3-4 (plus compass learning), or Figs 3-5 (plus both together)? | **Figs 3-5.** Fig 5 is the paper's main result; run it with 20 model flies by default instead of 1000 |
| Q2 | Saccade sign. Algorithm 3 moves the compass **up** and the arena heading **down** for a positive saccade. Combined with Eq. 33 (most CW saccades when the compass is 90 degrees CW of the goal), saccades would push the compass **away** from the goal. The text says saccades drive the compass toward the goal | **Follow the text:** a CW saccade (probability `dS`) increases the arena heading and decreases the compass heading by the same number of grid steps |
| Q3 | Eq. 33 is printed as `dS = 1/2 + (rG/D) cos(thetaC - 90 - thetaG)`. Working it out from Eqs. 30 and 32 gives `rG/(2D)`. With `rG/D`, strong goals push `dS` outside `[0, 1]` | **Compute Eqs. 30-33 literally from the population sums.** That gives `rG/(2D)`; the closed form is only used in tests |
| Q4 | Fixation drift rate. Eq. 34 has no baseline; Algorithm 4 adds `BF`. For some legal weights (all ones), Eq. 34 is negative (-0.23) | **`nuF = max(rF, 0) + BF`** with `BF = 0.05` (Table 1), so the mean fixation is at most `aF / BF` = 15.8 s |
| Q5 | Fixation length. Algorithm 4 uses a fixed `1 / nuF`; the pre-structured agent draws an inverse Gaussian | **Inverse Gaussian with mean `aF / nuF`** (same sampler and general parameters as the pre-structured agent) |
| Q6 | Where the fixation length is evaluated. Algorithm 4 takes `nuF` at the compass heading **before** the saccade, then fixates at the heading **after** it. In the prototype this makes the fly fixate long away from its goal (PI -0.12 after goal learning, even though the goal sits in a safe zone) | **At the heading where the fixation happens** (after the saccade and any jump). Prototype PI: +0.23 |
| Q7 | Compass rule sign. Eqs. 38-39 as printed move `wC` **toward** the bump. The text calls it anti-Hebbian ("weakens synapses from active ring neurons onto active compass neurons"), and Eq. 27 needs low weights at the current heading for a stable compass | **Anti-Hebbian: move `wC` toward `1 - rEB`.** Prototype: after learning, a frozen probe jumps after 9% of saccades in the asymmetric scene and 42% in the symmetric scene (50% with random weights) |
| Q8 | Ring neuron activity. Ring neurons fire 1 at the center of their receptive field and 0.5 one step to each side. Use these activities as weights in the compass rule and in the net weight of Eq. 27, or treat all active ring neurons the same? | **Weight by activity** (1 or 0.5) in both places |
| Q9 | Saccade velocity in `v^2`. Saccade sizes are in degrees in Table 1; `v^2` in degrees squared is about 2400, so one update would jump past the `[0, 1]` limits | **Radians** (about 0.73), and clip weights to `[0, 1]` after every update |
| Q10 | Heading grid. Algorithm 3 moves both headings in steps of one grid unit (11.25 degrees) | **Integer headings on the 32-step grid**; a saccade of size `s` takes `ceil(s / 11.25 degrees)` steps (at least 1), as in the loop of Algorithm 3 |
| Q11 | Bump and goal-strength scales. Eq. 26 normalizes the bump's area; the text and Methods say "normalized to [0, 1]". Goal strength in Fig 5 is a number between 0 and 1, not defined in the text | **Bump scaled to `[0, 1]`** (min 0, max 1); **goal strength = `rG / (N / pi)`**, the fraction of the largest possible `rG` (a square wave) |
| Q12 | Run lengths (not given in the text) | **Goal learning 1200 s; compass learning 2400 s (asymmetric) and 4800 s (symmetric); Fig 5: 2400 s asymmetric pre-training, then 1200 s of training; PI probes 240 s with frozen weights, at 0, 300, 600, 900 and 1200 s of Fig 5 training.** Recorded, and adjustable by name in `runManyCircuit`. Normal tests use the same lengths with 2 flies (about 1 s) |

## Prototype check (2026-10-10, before implementation)

Kept for history; the measured results above supersede it. A throwaway numpy script of the design (not committed; 20 model flies, all decisions above) gave:

| Check | Result | Meaning |
|---|---|---|
| Policy, sinusoidal goal (`g = 0.5`) | `dS` 0.167-0.833, largest 90 degrees CW of the goal; fixation 5.3 s at the goal, 1.0 s opposite | matches Fig 3c-d in shape |
| Goal learning, perfect compass (Fig 3i) | distance from goal to nearest safe-zone center 40 degrees at the start, 22 degrees (240 s) and 10 degrees (1200 s) over the last quarter; strength 0.49 to 0.84; PI 0.23 at 1200 s | learns |
| Same, with Algorithm 4 read literally (Q6) | distance 41 to 14 degrees, but PI -0.12 | goal moves, behavior does not follow |
| Compass learning, asymmetric scene, no jumps (Fig 4b) | mean jump probability along the learned map about 0.5 with random weights, 0.079 after 1200 s and 0.057 after 2400 s; frozen-probe jump rate 0.505 to 0.088 (single flies 0-0.19) | stable compass |
| Compass learning, symmetric scene, jumps (Fig 4c), 4800 s | frozen-probe jump rate 0.499 to 0.418 (single flies 0.25-0.51); training jump rate 0.44. The mean jump probability along a map is always exactly 0.5 here (opposite headings share ring activity), so it is not used as a measure | unstable compass |
| Both together (Fig 5) | goal 90 degrees from safe at the start, 13 degrees after 1200 s; probe PI -0.24 to 0.35 (single flies -0.14 to 1.0); strength 0.85 | matches Fig 5 in shape, with large fly-to-fly differences |
| Run time, 20 flies per set-up | goal 1.9 s, compass asymmetric 1.5 s, compass symmetric 3.5 s, both 3.8 s (about 11 s in total, probes included) | fast enough for a slow test; 2 flies (normal tests) take about 1 s |
## Naming

The paper calls this the "circuit implementation of the setpoint policy". The code uses **circuit**; Table 1 names are kept where they exist (`alphaC`, `alphaG`, `kappa` becomes `kappaEB` to avoid clashing with the flexible policy's `kappa`).
