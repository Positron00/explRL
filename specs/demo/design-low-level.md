# Low-level design: explRL full demo

Conventions: heading `theta` is a float in radians, kept in `[0, 2*pi)`; clockwise (CW) means `theta` increases; `nx` is the number of basis columns (arena positions) used for lookup and evaluation; time is counted in samples of `delT`. Equation numbers refer to the paper's SI.

## 1. `explRL/params.py`

```python
@dataclass
class Params:
    nx: int = 96            # basis columns (arena positions) around 360 deg
    delT: float = 0.001     # fixation sample length, s (delta t)
    tS: float = 0.32        # saccade duration, s (Table 1)
    sigF: float = 1.0       # spread of drift diffusion (eta_F)
    aF: float = 0.79        # fixation threshold
    muS: float = 3.89       # lognormal saccade size, deg (phi_S)
    sigmaS: float = 0.54    # lognormal saccade size spread
    Ttot: float = 240.0     # run length, s
    nb: int = 16            # number of basis functions
    kappa: float = 8.0      # basis concentration
    wParams: tuple = (1.0, 10.0, -0.01, 1.0, 0.98, -0.01)  # kF, fMF, f0F, kS, fMS, f0S
    omegaF0: float = 0.1    # initial fixation weights
    omegaS0: float = 0.0    # initial saccade weights
    lr: float = 1.0         # extra learning-rate factor (paper: 1)

    @property
    def dtS(self) -> int: return round(self.tS / self.delT)   # saccade length in samples (320)
```

- Field names `nx, delT, sigF, aF, muS, sigmaS, dtS` match what `flexibleAgent` already reads, so existing code keeps working.
- `wParams` order matches the existing `sigmoid(x, k, fmax, offset)`: `f(x) = fM / (1 + exp(-k x)) - f0`. With `f0 = -0.01` the drift rate stays in `(0.01, 10.01)` and `pR` in `(0.01, 0.99)`.
- `__post_init__` checks: `nx, nb > 0`, `delT, tS, sigF, aF, Ttot > 0`, `len(wParams) == 6`.

## 2. `explRL/basis.py`

```python
def vonMisesBasis(nb: int, nx: int, kappa: float) -> np.ndarray:
    "Returns an (nb, nx) matrix; row i is a von Mises bump centred at 2*pi*i/nb, peak value 1."
```

- `mu_i = 2*pi*i/nb`, `theta_j = 2*pi*j/nx`, `g[i, j] = exp(kappa * (cos(theta_j - mu_i) - 1))` (peak 1; decided in Q1).
- Tests: shape; `g.max() == 1`; the peak of row `i` is at column `round(i * nx / nb)`; shifting by `nx/nb` columns maps row `i` onto row `i+1` (even tiling).

## 3. `explRL/agents.py`

### `Step` record

```python
@dataclass
class Step:
    theta: float      # heading before the step, radians
    ind: int          # basis column used for this step
    xi: float         # integrator before the step
    dxi: float        # integrator change drawn this step
    saccade: bool
    direction: int    # +1 CW, -1 CCW, 0 for a fixation
    dx: float         # heading change in radians (0.0 for a fixation)
    dt: int           # duration in samples (1 or dtS)
```

### `flexibleAgent` changes

- `__init__(self, theta, goal, policy, rl, params, rng=None)`: `theta` is any real number (radians) and is stored wrapped as `theta % (2*pi)`; `self.rng = rng if rng is not None else np.random.default_rng()`. Keep the Phase 1 shape checks, but require `len(wParams) == 6` (was `>= 6`) to match `Params`.
- Keep the Phase 1 `_heading_index(nx)` (nearest basis column by wrapped angular distance); the basis column is `policy.fk[:, ind]`.
- `samplePolicy(self) -> Step`, following Algorithm 2:
  1. `ind = _heading_index(nx)`; `g = fk[:, ind]`; `nu, pR = convertParams(omega, g, wParams)`.
  2. `dxi = rng.normal(nu * delT, sigF * sqrt(delT))`; `xi0 = policy.integ`.
  3. If `xi0 + dxi > aF`: saccade. `direction = +1 if flipCoin(pR) else -1`; `dx = direction * deg2rad(rng.lognormal(muS, sigmaS))` (no rounding; replaces the Phase 1 `* 96/360` and `round(dx)`); `dt = dtS`; reset `policy.integ = 0`.
  4. Otherwise: fixation. `dx = 0.0`, `dt = 1`, `policy.integ = xi0 + dxi`.
  5. Set `self.dx`, `self.dt`; return `Step(theta, ind, xi0, dxi, saccade, direction, dx, dt)`.
- The agent does not move itself; `train_agent` sets `agent.theta` from the arena's answer.
- `flipCoin` uses `self.rng`. `convertParams` and `sigmoid` stay the same.
- New `sigmoidGrad(x, k, fmax)`: `fmax * k * e / (1 + e)**2` with `e = exp(-k x)`. Use the stable form `fmax * k * s * (1 - s)` with `s = 1 / (1 + exp(-k x))`.

### `PolicyGradientRL(RL)`

```python
class PolicyGradientRL(RL):
    def __init__(self, policy, lr=1.0, eps=1e-12): ...
    def chooseAction(self, agent) -> Step: return agent.samplePolicy()
    def logPi(self, agent, step, omega=None) -> float: ...   # log-probability of step; omega defaults to the current weights
    def gradLogPi(self, agent, step) -> np.ndarray: ...   # shape (2*nb,)
    def updateParams(self, agent, step, reward) -> None:
        self.policy.omega = self.policy.omega + self.lr * reward * self.gradLogPi(agent, step)
```

A private helper `_terms(agent, step, omega)` computes the shared, clamped quantities below once, so `logPi` and `gradLogPi` cannot drift apart.

`gradLogPi` (Eqs. 13-16, 18). With `g = fk[:, step.ind]`, `nb = len(g)`, `kF, fMF, f0F, kS, fMS, f0S = wParams`:

```
xF = omegaF . g                    xS = omegaS . g
nu = f(xF; kF, fMF, f0F)           dS = f(xS; kS, fMS, f0S)
gradNu = f'(xF; kF, fMF) * g       gradDS = f'(xS; kS, fMS) * g
s   = sigF * sqrt(delT)            m = step.xi + nu * delT
PF  = Phi((aF - m) / s)            # probability of continuing the fixation (Eq. 7)
phi = exp(-(aF - m)^2 / (2 s^2)) / (s * sqrt(2 pi))
```

| Step type | gradient for `omegaF` | gradient for `omegaS` |
|-----------|----------------------|-----------------------|
| Fixation | `-delT * phi * gradNu / PF` | `0` |
| CW saccade | `+delT * phi * gradNu / (1 - PF)` | `+gradDS / dS` |
| CCW saccade | `+delT * phi * gradNu / (1 - PF)` | `-gradDS / (1 - dS)` |

- `Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))` using `math.erf` (no SciPy).
- Clamp `PF`, `1 - PF`, `dS`, `1 - dS` to at least `eps` before dividing (NFR-7).
- Return `np.concatenate([gradOmegaF, gradOmegaS])`.
- The lognormal size term and the fixed saccade duration do not depend on `omega`, so they drop out of the gradient.

Finite-difference test (AC-2): for hand-built fixation, CW-saccade and CCW-saccade `Step`s with the integrator just below threshold, compare the central difference of `logPi` (`log PF` for a fixation; `log(1 - PF) + log(dS or 1 - dS)` for a saccade; `h = 1e-6`) with `gradLogPi`.

## 4. `explRL/envs.py`

```python
class HeadingArena(World):
    def __init__(self, goal: float = pi): ...         # goal heading in radians, stored as goal % (2*pi)
    def distance(self, theta) -> float:               # wrapped distance to goal, radians, in [0, pi]
        return abs((theta - self.goal + pi) % (2*pi) - pi)
    def reward(self, theta) -> float: return (pi/10) * (0.5 - self.distance(theta))   # Eq. 19
    def step(self, theta: float, dx: float) -> tuple[float, float]:
        new = (theta + dx) % (2*pi)
        return new, self.reward(new)
```

- `World.__init__(self, size=None)` gains a `size` argument; `HeadingArena.__init__` calls `super().__init__(2*pi)` (the arena is one full circle).
- Tests: `reward(goal) == pi/20`; the reward at the opposite heading is the minimum `(pi/10)(0.5 - pi)`; it is symmetric around the goal; `step(2*pi - 0.1, 0.2)` returns a heading close to `0.1`; a negative `dx` wraps the other way.

## 5. `explRL/train.py`

```python
@dataclass
class History:
    t: np.ndarray        # time in samples at the start of each step
    theta: np.ndarray    # heading before each step
    saccade: np.ndarray  # bool
    dt: np.ndarray       # duration of each step in samples (1 or dtS)
    reward: np.ndarray

def train_agent(agent, env, Ttot=None) -> History: ...    # Ttot defaults to agent.params.Ttot
def evaluatePolicy(agent) -> dict: ...                     # keys: nu, pR, fixDur, turnBias; arrays of length nx
def residency(history, env, nBins=8, halfWidthDeg=45) -> np.ndarray: ...   # fraction of time near goal per bin
def runMany(params, goal, nRuns, seed=0, Ttot=None) -> list[dict]: ...
    # one dict per run: {"eval": evaluatePolicy(...), "residency": residency(...), "omega": final weights}
```

`train_agent` (Algorithm 1):

```
nSteps = round(Ttot / delT); t = 0
while t < nSteps:
    step = agent.rl.chooseAction(agent)
    newTheta, r = env.step(agent.theta, step.dx)
    agent.rl.updateParams(agent, step, r)
    record (t, step.theta, step.saccade, step.dt, r)
    agent.theta = newTheta; t += step.dt
```

- Store records in preallocated NumPy arrays sized `nSteps` and trim at the end (a run has at most 240 000 steps).
- The loop stops at the first step that reaches `nSteps`, so a run can overshoot `Ttot` by up to one saccade (`dtS` samples).
- `residency` splits the run into `nBins` equal time bins (from 0 to the end of the last step) and counts each step for the part of its duration (1 or `dtS` samples) that falls inside each bin, so a saccade spanning two bins is split between them.
- `evaluatePolicy` evaluates `convertParams` for every column of `fk`; `fixDur = aF / nu`; `turnBias = 2 * pR - 1`.
- `runMany` uses `seed + i` for run `i`, builds objects with `loadAgent` / `loadEnv`, trains, evaluates, computes residency, and then drops the `History` so memory stays small (one full `History` is about 240 000 rows).

## 6. `explRL/core.py`

```python
def loadAgent(params=None, goal=None, seed=None) -> flexibleAgent:
    "Build a flexiblePolicy (omegaF = omegaF0, omegaS = omegaS0, basis from vonMisesBasis), a PolicyGradientRL, and an agent at a random heading."
    # rng = np.random.default_rng(seed); theta = 2*pi * rng.integers(params.nx) / params.nx  (one of nx evenly spaced headings, as in the paper)
    # rl = PolicyGradientRL(policy, lr=params.lr); the same rng is passed to the agent, so one seed fixes the start heading and every later step
def loadEnv(params=None, goal=None) -> HeadingArena:
    "Build an arena; goal (radians) defaults to pi."
```

## 7. `nbs/demo.ipynb`

| Section | Content | Test flag |
|---------|---------|-----------|
| Setup | `Params()`, seed, goal = `pi` (180 degrees); basis plot | normal |
| Quick run | `train_agent` with `Ttot = 5`, stored as `agent, hist` | normal |
| Full run | same with `Ttot = 240`, overwriting `agent, hist` | `#| slow` |
| Trajectory | heading-vs-time plots for the first and last `min(20 s, run length / 2)` of `hist` | normal |
| Learned policy | drift rate, fixation duration, turn bias versus heading for `agent` | normal |
| Many runs | `runMany(nRuns = 20)`; mean and standard error, x axis = heading minus goal in degrees (Fig 2d-e analogue) | `#| slow` |
| Residency | `residency` per run, averaged | `#| slow` |
| Acceptance | asserts for AC-5 to AC-8 | `#| slow` |
| Summary | markdown: measured AC-5 to AC-8 values and any tuning applied (none was needed) | normal |

The quick-then-full pattern means normal tests plot a barely trained 5 s agent, while a full run (`nbdev-test --flags slow`, or running the notebook by hand) replaces it with the 240 s agent before the same plotting cells run.

## 8. Configuration

- `pyproject.toml`: `[tool.nbdev] tst_flags = "notest slow"` (plus explicit `lib_path`, `nbs_path`, `doc_path`); `matplotlib` added to `[project.optional-dependencies] dev` next to `nbdev` and `fastcore`.
- `Params.__post_init__` also requires `aF > 0`, so tests that need frequent saccades use a small positive threshold (for example `1e-6`) rather than a negative one.
- `nbs/sidebar.yml` is regenerated with `nbdev-sidebar` after the new notebooks are added.
