# Low-level design: pre-structured (setpoint) policy

All angles are radians in `[0, 2*pi)` unless stated. `wrap(a) = a % (2*pi)`; `angdiff(a, b) = (a - b + pi) % (2*pi) - pi` (in `[-pi, pi)`). `D = angdiff(thetaC, thetaG)`.

## 1. `Params` additions (`nbs/params.ipynb`)

| Field | Default | Table 1 meaning |
|---|---|---|
| `GS` | 0.9 | gain of saccades (heading dependence) |
| `BS` | 0.0 | baseline direction of saccades |
| `GF` | 0.8 | gain of fixations |
| `BF` | 0.05 | baseline drift rate of fixations |
| `GJ` | 0.7 | gain of bump jumps |
| `BJ` | 0.05 | baseline jump probability |
| `thetaJ` | `pi` | jump size (180 degrees) |
| `lrG` | 1.0 | extra factor on the goal update (Q4; paper: 1) |

New checks in `__post_init__` (raise `ValueError`):

- `abs(GS) / 2 + abs(BS) <= 0.5` so `dS` stays in `[0, 1]`.
- `BF > 0` and `GF >= 0` so `nuF >= BF > 0`.
- `GJ >= 0`, `BJ >= 0`, `GJ + BJ <= 1` so `pJ` stays in `[0, 1]`.
- `lrG >= 0`.

Existing fields used: `aF`, `sigF` (eta_F), `muS`, `sigmaS`, `tS`, `Ttot`.

## 2. Policy curves (`explRL/prestructured.py`)

All accept scalars or arrays and broadcast.

```python
def turnProb(thetaC, thetaG, p):   # Eq. 20, probability of a CW saccade
    return -p.GS / 2 * np.sin(D) + p.BS + 0.5
def driftRate(thetaC, thetaG, p):  # Eq. 20
    return p.GF / 2 * (1 - np.cos(D)) + p.BF
def jumpProb(thetaC, thetaG, p):   # Eq. 21 with the sign decided in Q1 (1 - cos; printed: 1 + cos)
    return p.GJ / 2 * (1 - np.cos(D)) + p.BJ
```

Effective readout, Eq. 23, for arena headings `thetaA` (array) and goal `thetaG`, assuming no offset before the jump draw and `pJ` evaluated at the heading itself (see design-high-level D4 for how this differs from the simulation):

```python
def effectivePolicy(thetaA, thetaG, p) -> dict:
    pj = jumpProb(thetaA, thetaG, p)
    nu = (1 - pj) * driftRate(thetaA, thetaG, p) + pj * driftRate(thetaA + p.thetaJ, thetaG, p)
    dS = (1 - pj) * turnProb(thetaA, thetaG, p)  + pj * turnProb(thetaA + p.thetaJ, thetaG, p)
    return dict(nu=nu, dS=dS, fixDur=p.aF / nu, turnBias=2 * dS - 1)
```

Closed form (useful for tests), with `D = thetaA - thetaG`:
`turnBias = 2*BS - GS * sin(D) * (1 - 2*pJ(D))`.

## 3. `prestructuredPolicy(Policy)`

```python
class prestructuredPolicy(Policy):
    def __init__(self, thetaG): self.thetaG = float(thetaG) % (2*pi)
```

## 4. `Event` record

```python
@dataclass
class Event:
    thetaA: float       # arena heading before the saccade
    thetaC: float       # compass heading before the saccade
    fixDur: float       # fixation duration, s
    direction: int      # +1 CW, -1 CCW
    dx: float           # saccade size with sign, radians
    jumped: bool        # bump jumped after the saccade
    thetaC_next: float  # compass heading after saccade and jump (wrapped)
```

## 5. `prestructuredAgent(Agent)`

```python
def __init__(self, theta, goal, policy, rl, params, rng=None, thetaC=None):
    # theta = arena heading (stored wrapped); thetaC defaults to theta (offset 0)
    # TypeError if policy is not a prestructuredPolicy
def samplePolicy(self) -> Event:
    p, g, c, rng = self.params, self.policy.thetaG, self.thetaC, self.rng
    nu = driftRate(c, g, p)
    fixDur = rng.wald(p.aF / nu, p.aF**2 / p.sigF**2)        # draw 1
    direction = 1 if rng.random() < turnProb(c, g, p) else -1  # draw 2
    dx = direction * deg2rad(rng.lognormal(p.muS, p.sigmaS))   # draw 3
    c1 = wrap(c + dx)
    jumped = bool(rng.random() < jumpProb(c1, g, p))           # draw 4
    return Event(self.theta, c, fixDur, direction, dx, jumped, wrap(c1 + p.thetaJ * jumped))
```

Draw order 1-4 is fixed (FR-9). `samplePolicy` does not change `self.theta` or `self.thetaC`; the training loop does. `thetaC` is stored wrapped, like `theta`.

Fixation durations are heavy-tailed: with `aF = 0.79`, `sigF = 1` the shape is 0.62, so the standard deviation is `sqrt(mean^3 / 0.62)`: about 1.1 s at the anti-goal (mean 0.93 s) but about 80 s at the goal (mean 15.8 s, no jumps). Tests that check the mean of many draws use the anti-goal heading.

Inverse Gaussian check: the 1 ms drift-diffusion in the flexible demo, `dxi ~ N(nu*dt, sigF^2*dt)` with threshold `aF`, has first-passage time `IG(mean = aF/nu, shape = aF^2/sigF^2)`, which is what `wald(mean, scale)` samples.

## 6. `GoalHeadingRL(RL)`

```python
def __init__(self, policy, lr=1.0, eps=1e-12)
def chooseAction(self, agent): return agent.samplePolicy()
def logPiS(self, agent, ev, thetaG=None) -> float:
    g = self.policy.thetaG if thetaG is None else thetaG     # not `thetaG or ...`: 0.0 is a valid heading
    dS = clamp(turnProb(ev.thetaC, g, agent.params), eps, 1 - eps)
    return log(dS) if ev.direction > 0 else log(1 - dS)   # lognormal size term does not depend on thetaG
def gradLogPiS(self, agent, ev) -> float:
    p, g = agent.params, self.policy.thetaG
    dS = clamp(turnProb(ev.thetaC, g, p), eps, 1 - eps)      # same clamp as logPiS
    ddS = p.GS / 2 * cos(angdiff(ev.thetaC, g))          # d dS / d thetaG (Q2: printed Eq. 25 has the opposite sign)
    return ddS / dS if ev.direction > 0 else -ddS / (1 - dS)
def updateParams(self, agent, ev, reward):
    self.policy.thetaG = wrap(self.policy.thetaG + self.lr * reward * self.gradLogPiS(agent, ev))
```

Derivation of `ddS`: `dS = -GS/2 sin(thetaC - thetaG) + BS + 1/2`, and `d/dthetaG sin(thetaC - thetaG) = -cos(thetaC - thetaG)`, so `d dS/d thetaG = +GS/2 cos(thetaC - thetaG)`.

Size of one update with defaults: `|reward| <= 0.83`, `|grad| <= 0.45 / 0.05 = 9`, so one step can be up to about 7.5 rad when `lr = 1` (Q4).

## 7. Expected values with defaults (for AC-2 and AC-3)

With `pJ = 0.35 (1 - cos D) + 0.05` (Q1 decision), `aF = 0.79`, and `D = rel` (arena minus goal):

| Arena minus goal | `pJ` | Effective `nu` | Fixation duration | Without jumps |
|---|---|---|---|---|
| 0 | 0.05 | 0.09 | 8.78 s | 15.8 s |
| ±90 degrees | 0.40 | 0.45 | 1.76 s | 1.76 s |
| 180 degrees | 0.75 | 0.25 | 3.16 s | 0.93 s |

Turn bias: `-0.9 sin(D) (0.2 + 0.7 cos(D))`. It is zero at `D = 0`, `D = 180 degrees` and `|D| = arccos(-2/7) = 106.6 degrees`; it points toward the goal for `|D| < 106.6 degrees` and toward the anti-goal beyond. AC-2 uses windows that stay clear of 106.6 degrees.

With the printed sign (`1 + cos`), fixation durations would be 1.22 s at the goal, 0.98 s at the anti-goal and 1.76 s at ±90 degrees: longest at ±90, not bimodal. This is the main evidence for Q1.

All values in this section were checked numerically on 2026-10-10. Simulated values (for AC-8 to AC-10) are in the README's prototype table.

## 8. `explRL/prestructured_train.py`

```python
@dataclass
class EventHistory:
    t: np.ndarray          # event start time, s
    thetaA: np.ndarray     # before the saccade
    thetaC: np.ndarray     # before the saccade
    fixDur: np.ndarray
    direction: np.ndarray  # int
    jumped: np.ndarray     # bool
    reward: np.ndarray
    thetaG: np.ndarray     # after the update

def train_prestructured(agent, env, Ttot=None) -> EventHistory:
    # Ttot defaults to agent.params.Ttot; t starts at 0
    # loop while t < Ttot: ev = agent.rl.chooseAction(agent); thetaA1, r = env.step(agent.theta, ev.dx)
    # agent.rl.updateParams(agent, ev, r); record (thetaG after the update)
    # agent.theta = thetaA1; agent.thetaC = ev.thetaC_next; t += ev.fixDur + p.tS
def relHeading(thetaA, goal) -> np.ndarray:
    # np.rad2deg(angdiff(thetaA, goal)), in [-180, 180)
def readout(history, goal, nBins=24) -> dict:
    # bin edges -180 + k * 360 / nBins; events placed by relHeading(history.thetaA, goal)
    # returns dict(centers=..., fixDur=plain mean per bin, turnBias=mean(direction) per bin, count=...); nan if empty
def heldGoal(history, thetaG0, times, tS) -> np.ndarray:
    # update i happens at history.t[i] + history.fixDur[i] + tS (end of event i)
    # value at each time: thetaG0 before the first update, else thetaG after the latest update (searchsorted)
def runManyPrestructured(params, goal, nRuns, seed=0, Ttot=None, learn=True, thetaG0=None) -> list[dict]:
    # run i uses seed + i, loadPrestructuredAgent and loadEnv
    # each: dict(history=..., readout=readout(history, goal), thetaG0=..., jumpRate=history.jumped.mean())
```

`readout` uses the plain mean so it can be compared with `aF / nu` from Eq. 23 and with the paper's "average duration of fixations". AC-8 pools events from the run histories directly, using `relHeading` and the windows defined in the requirements, rather than averaging bins. AC-9 and AC-10 use `heldGoal` on a 1 s grid and average over the last quarter of time, because heavy-tailed fixations leave some runs with no event in that quarter.

## 9. `loadPrestructuredAgent` (`nbs/00_core.ipynb`)

```python
def loadPrestructuredAgent(params=None, goal=pi, seed=None, thetaG0=None, learn=True):
    p = params if params is not None else Params()
    rng = np.random.default_rng(seed)
    thetaA0 = rng.uniform(0, 2*pi)
    thetaG0 = rng.uniform(0, 2*pi) if thetaG0 is None else thetaG0   # Q6
    policy = prestructuredPolicy(thetaG0)
    rl = GoalHeadingRL(policy, lr=p.lrG if learn else 0.0)
    return prestructuredAgent(thetaA0, goal, policy, rl, p, rng=rng)   # thetaC starts = thetaA0
```

The arena is built with the existing `loadEnv(goal=goal)`. Draw order in the loader (starting arena heading, then starting goal heading if not given) is fixed, so one seed fixes the whole run. The flexible `loadAgent` and `loadEnv` are unchanged.

## 10. Artifact helpers (`nbs/train.ipynb`)

Add a folder argument, default `'demo'`: `demo_artifact_dir(mode, name='demo')`, and `demo_name='demo'` on `save_demo_figure` and `save_demo_metrics` (their `name` argument is already the file name). The new demo passes `demo_name='demo_prestructured'`. Existing calls keep working. `.gitignore` gets `results/demo_prestructured/`.

## 11. `nbs/demo_prestructured.ipynb`

Same quick-then-full pattern as the flexible demo: a normal cell runs all three conditions with 2 runs of 240 s; a `#| slow` cell sets `artifact_mode = 'full'`, `nRuns = 20` and reruns them, overwriting the results before the same plotting and metrics cells run.

| Section | Content | Saved as | Test flag |
|---|---|---|---|
| Setup | `Params()`, `Params(GJ=0, BJ=0)`, goal = pi, seed = 0, `nRuns = 2`, `artifact_mode = 'quick'` | - | normal |
| Policy curves | `dS`, `nuF`, `pJ` vs compass minus goal (degrees) | `policy_curves.png` (top level) | normal |
| Analytic Fig 2h | `effectivePolicy` fixation duration and turn bias vs arena minus goal, jumps on vs off | `fig2h_analytic.png` (top level) | normal |
| Simulated runs | three conditions: fixed goal with jumps, learning without jumps, learning with jumps | - | quick normal, full `#| slow` |
| Measures | AC-8 window means; AC-9 / AC-10 start and last-quarter distances (printed) | - | normal |
| Simulated Fig 2h | fixed-goal runs; `readout` fixation duration and turn bias, mean over runs, with Eq. 23 overlaid | `quick/` or `full/fig2h_simulated.png` | normal |
| Learning, no jumps | mean `|angdiff(thetaG, goal)|` vs time over runs | `learning_nojump.png` | normal |
| Learning, jumps | mean distance to the nearer of goal / anti-goal vs time | `learning_jump.png` | normal |
| Metrics | quick: mode, seed, goal_rad, nRuns, Ttot_s; full adds `AC8_fix_goal_s`, `AC8_fix_antigoal_s`, `AC8_fix_side_s`, `AC9_dist_start_rad`, `AC9_dist_last_quarter_rad`, `AC10_nearer_start_rad`, `AC10_nearer_last_quarter_rad`, `jump_rate_fixed_goal` | `metrics.json` | normal |
| Acceptance | asserts AC-8, AC-9, finiteness for AC-10 in every run | - | `#| slow` |
| Summary | measured values; no tuning was needed | - | normal |

Goal-heading traces have different event times in each run, so the learning plots evaluate each run's goal heading with `heldGoal` on a common 1 s grid before averaging.

## 12. Files and size budget

| File | Expected lines | Actual |
|---|---|---|
| `explRL/prestructured.py` | about 150 | 124 |
| `explRL/prestructured_train.py` | about 100 | 85 |
| `explRL/params.py` | about 60 (from 42) | 58 |
| `explRL/core.py` | about +20 | 53 (+14) |
| `explRL/train.py` | about +3 (the folder argument) | 3 signatures changed, no new lines |
