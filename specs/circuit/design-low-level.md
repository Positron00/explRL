# Low-level design: circuit model

Indices are integers `0..N-1` with `N = p.nCirc` (or `len(wG)`); `grid(N) = 2*pi*arange(N)/N`; one step is `2*pi/N` radians (11.25 degrees). Arrays are numpy. Each formula follows the decided answer of the README question named next to it.

## 1. Parameters (`Params`)

| Field | Default | Meaning | Check |
|---|---|---|---|
| `nCirc` | 32 | grid size `N` (Table 1) | even, >= 4 |
| `kappaEB` | `pi` | EB bump concentration (Table 1 `kappa`) | > 0 |
| `alphaC` | 0.01 | compass learning rate | >= 0 |
| `alphaG` | 0.001 | goal learning rate | >= 0 |
| `nuMax` | 1.1 | fixation output ceiling (Eq. 32) | > 0 |
| `dtG` | 0.1 | goal update step, s (Algorithm 3) | > 0 |

Reused: `BF = 0.05`, `aF = 0.79`, `sigF = 1`, `muS = 3.89`, `sigmaS = 0.54`, `tS = 0.32`, `Ttot = 240`.

## 2. Populations and goal statistics (`explRL.circuit`)

```python
def grid(N): return 2*pi*np.arange(N)/N
def rEB(c, N, kappa):                       # Eq. 26 shape, scaled to [0, 1] (Q11)
    e = np.exp(kappa * np.cos(grid(N) - grid(N)[c % N]))
    return (e - e.min()) / (e.max() - e.min())
def rFB(c, N): return 0.5 * (np.cos(grid(N) - grid(N)[c % N]) + 1)     # Eq. 28
def fbNorm(N): return float((rFB(0, N)**2).sum())                      # D in Eq. 30; 3N/8 = 12 for N = 32
def goalStats(wG) -> dict:                  # Eq. 31 terms
    N = len(wG); z = (wG * np.exp(1j*grid(N))).sum()
    return dict(thetaG=np.angle(z) % (2*pi), rG=abs(z), total=wG.sum(), strength=abs(z)/(N/pi))
def sinGoal(g, theta0, N):                  # ValueError unless 0 <= g <= 0.5
    return g*np.cos(grid(N) - theta0) + 0.5
```

## 3. Policy outputs (Eqs. 30-34; Q3, Q4)

```python
def outputs(wG, c, p) -> dict:
    N = len(wG); q = N // 4; D = fbNorm(N)
    rO = lambda shift: float((rFB(c + shift, N) * wG).sum()) / D
    rL, rR = rO(+q), rO(-q)                  # phase shifts +90 and -90 degrees
    rF = rO(N // 2) + p.nuMax - wG.sum()/D   # 180 degrees; BC = nuMax - |wG|/D
    dS = 0.5 * (1 + rR - rL)
    return dict(dS=dS, nuF=max(rF, 0.0) + p.BF, rF=rF)
```

Closed forms used only in tests: `dS = 1/2 + rG/(2D) * sin(theta_c - thetaG)` and `rF = nuMax - |wG|/(2D) - rG/(2D) * cos(theta_c - thetaG)`.

## 4. Ring activity and jump probability (Eq. 27; Q8)

```python
def ringActivity(a, N, symmetric) -> np.ndarray:
    act = np.zeros(N)
    for b in ([a, a + N//2] if symmetric else [a]):
        act[b % N] = 1.0
        for k in (b - 1, b + 1): act[k % N] = max(act[k % N], 0.5)
    return act
def jumpProb(wC, act, c) -> float:
    net = act @ wC                           # net inhibition onto each compass neuron
    N = len(net); x, y = net[c % N], net[(c + N//2) % N]
    return 0.5 if x + y == 0 else float(x / (x + y))
```

## 5. Plasticity (Eqs. 38-39; Q7, Q9)

```python
def hebb(target, w):                         # Eq. 39, R > 0 branch: toward target
    return np.maximum(target - w, 0)*(w < 1) - np.maximum(w - target, 0)*(w > 0)
def antiHebbGoal(target, w):                 # Eq. 39, R < 0 branch: away from target
    return -np.maximum(target - w, 0)*(w > 0) + np.maximum(w - target, 0)*(w < 1)
def compassStep(wC, act, c, size, p):        # one saccade grid step; size in radians
    target = 1 - rEB(c, len(wC), p.kappaEB)  # anti-Hebbian (Q7)
    dw = p.alphaC * size**2 * act[:, None] * hebb(target[None, :], wC)
    return np.clip(wC + dw, 0, 1)
def goalStep(wG, c, R, p):                   # one dtG step of fixation
    if R == 0: return wG
    t = rFB(c, len(wG))
    return np.clip(wG + p.alphaG * (hebb(t, wG) if R > 0 else antiHebbGoal(t, wG)), 0, 1)
```

## 6. Arena (`explRL.envs.ZoneArena`)

```python
class ZoneArena(World):
    def __init__(self, N=32, symmetric=True, centers=(90, 270), width=90): ...   # World size = N
    def isSafe(self, a) -> bool          # degree of a in [center - width/2, center + width/2) for any center
    def valence(self, a) -> int          # +1 safe, -1 danger
    def ringActivity(self, a) -> np.ndarray   # circuit.ringActivity(a, N, self.symmetric)
    def safeDistance(self, theta) -> float    # degrees from arena angle theta (radians) to the nearest center
```

## 7. Agent and learning rule (`explRL.circuit_agent`)

```python
class circuitPolicy(Policy):
    def __init__(self, wG, wC): ...          # float copies; ValueError unless wG has shape (N,), wC (N, N), all in [0, 1]
@dataclass
class Saccade:
    direction: int                           # +1 CW (a up, c down), -1 CCW
    size: float                              # radians (drawn in degrees, then converted)
    steps: int                               # max(1, ceil(size / (2*pi/N)))
class circuitAgent(Agent):
    def __init__(self, a, policy, rl, params, rng=None):
        # TypeError unless policy is a circuitPolicy; super().__init__(None, None, policy, rl, params)
        # self.a = a % N; self.c = self.a; self.rng = rng or default_rng()
    def sampleSaccade(self) -> Saccade:      # draw 1: direction (CW if rand < dS at c); draw 2: lognormal(muS, sigmaS) degrees
    def move(self, d): self.a = (self.a + d) % N; self.c = (self.c - d) % N
    def maybeJump(self, act) -> bool:        # draw 3: jump if rand < jumpProb(wC, act, c); then c += N/2
    def sampleFixation(self) -> float:       # draw 4: wald(aF / nuF(c), aF**2 / sigF**2)
class CircuitRL(RL):
    def __init__(self, policy, learnC=True, learnG=True, jumps=True): ...
    def chooseAction(self, agent): return agent.sampleSaccade()
    def updateCompass(self, agent, act, size): ...   # policy.wC = compassStep(...)
    def updateGoal(self, agent, R, nSteps): ...      # nSteps x goalStep(...)
```

The base `Agent.theta` and `Agent.goal` are unused here (`None`); the circuit agent uses `a` and `c`. `updateParams` is not used and keeps the base `NotImplementedError`. Draws happen in the fixed order 1-4 (FR-14); draw 3 is skipped when jumps are off.

## 8. Training loop and measures (`explRL.circuit_train`)

```python
@dataclass
class CircuitHistory:                        # one entry per iteration
    t: np.ndarray          # start time of the iteration
    a: np.ndarray          # arena heading after the saccade and jump (where the fixation happens)
    c: np.ndarray          # compass heading after the saccade and jump
    direction: np.ndarray  # saccade direction (+1 CW, -1 CCW)
    steps: np.ndarray      # saccade grid steps
    jumped: np.ndarray     # bool
    valence: np.ndarray    # R at a
    fixDur: np.ndarray     # fixation length, s
    thetaG: np.ndarray     # goal heading after this iteration's goal updates (compass, radians)
    strength: np.ndarray   # goal strength after the updates
    mirror: np.ndarray     # (a + c) mod N after the jump

def concatHistory(parts) -> CircuitHistory    # join histories run one after another (times already continue)
def endTime(history, tS) -> float              # end of the last iteration: t[-1] + tS + fixDur[-1] (nan if empty)

def train_circuit(agent, env, Ttot=None, t0=0.0) -> CircuitHistory:
    rl, p, t = agent.rl, agent.params, t0     # Ttot defaults to p.Ttot; runs until t0 + Ttot
    while t < t0 + Ttot:
        sac = rl.chooseAction(agent)
        for _ in range(sac.steps):
            if rl.learnC: rl.updateCompass(agent, env.ringActivity(agent.a), sac.size)
            agent.move(sac.direction)
        jumped = rl.jumps and agent.maybeJump(env.ringActivity(agent.a))
        R = env.valence(agent.a)
        fix = agent.sampleFixation()
        if rl.learnG and R != 0: rl.updateGoal(agent, R, ceil(fix / p.dtG))
        record(...); t += p.tS + fix
```

`t0` lets a run continue the clock of an earlier one, so `concatHistory` gives increasing times (used by `'both'`, section 8b). An empty history (for `Ttot <= 0`) has arrays of length 0.

Measures:

```python
def goalArena(history, N) -> np.ndarray        # grid(N)[mirror] - thetaG, wrapped to [-pi, pi)
def goalSafeDistance(history, env) -> np.ndarray   # env.safeDistance(goalArena) in degrees
def heldValue(history, values, start, times, tS)   # value in effect at each time: start before the first
                                                   # iteration ends, then the value after the latest one
                                                   # (iteration i ends at t + tS + fixDur); like prestructured.heldGoal
def piScore(history) -> float                  # sum(valence * fixDur) / sum(fixDur): (safe - danger) / total fixation time
def readout(history, N) -> dict                # per relative-heading bin (a minus goal in the arena, N bins):
                                               # mean fixDur of iteration i, and turn bias = mean direction of
                                               # the next saccade (i + 1), which starts at that heading
def mapJumpProb(wC, env, mirror) -> np.ndarray # pJ at compass c = mirror - a for every arena heading a ("pJ along a map")
def stablestCompass(wC, env, mirror) -> float  # circular mean over compass headings of (1 - pJ) from mapJumpProb
def probe(agent, env, T=240, seed=0) -> dict       # deep copy; learnC = learnG = False, jumps on; new generator
                                                   # from seed; dict(history=..., PI=piScore, jumpRate=jumped.mean())
```

## 8b. Named set-ups (`explRL.circuit_runs`)

A separate module keeps `circuit_train.py` under 200 lines; it imports the loader from `explRL.core`.

```python
LENGTHS = dict(goal=1200, compass_asym=2400, compass_sym=4800, pretrain=2400, train=1200, probe=240, probeEvery=300)
SETUPS = ('goal', 'compass_asym', 'compass_sym', 'both')
def runLengths(lengths=None) -> dict                 # LENGTHS with named overrides; ValueError for unknown names
def goalDistanceNow(agent, env) -> float             # degrees from the agent's current goal in the arena to safe
def lastQuarterMean(history, values, start, T, tS) -> float   # time average over [0.75 T, T) of held values,
                                                              # grid step min(1 s, T / 100)
def runManyCircuit(setup, params, nRuns, seed=0, lengths=None) -> list[dict]
```

Fly `i` uses seed `seed + i`. Probes use seeds `1000 + seed + i` and `2000 + seed + i` (compass set-ups, before and after), or `1000 k + seed + i` for the `k`-th probe (`'both'`, `k = 1..5`). `ValueError` for an unknown set-up.

| `setup` | Arena scene | Starting weights | Phases | Returned per fly (besides `history`, `wG`, `wC`) |
|---|---|---|---|---|
| `'goal'` (Fig 3i) | symmetric (unused) | loader defaults | 1200 s: goal learning on, compass learning off, jumps off | `distStart`, `distLastQ` (`lastQuarterMean`), `strStart`, `strEnd`, whole-run `PI` |
| `'compass_asym'` (Fig 4b) | asymmetric | random `wC`; fixed `wG = sinGoal(0.4, grid[8])` | 2400 s: compass learning on, goal learning off, jumps off | `mirror` (final), `mapPJ` and `mapPJmean` along the final map (constant without jumps), `probeBefore`, `probeAfter`, `trainJumpRate` (0 without jumps) |
| `'compass_sym'` (Fig 4c) | symmetric | same | 4800 s: compass learning on, goal learning off, jumps on | same |
| `'both'` (Fig 5) | asymmetric, then symmetric | random `wC`; `wG` replaced after pre-training | pre-training 2400 s (compass learning only, asymmetric); then `wG = sinGoal(0.43, grid[mirror])` (strength 0.67, goal at arena 0 degrees, a danger center); then 1200 s with everything on (symmetric), run in segments that end at each probe time (`t0` continues the clock). The same agent continues, keeping `a`, `c` and `wC` | `distStart`, `distEnd`, `strStart`, `strEnd`, `probeTimes` (`0, probeEvery, 2 probeEvery, ...` below `train`, then `train`: 0, 300, 600, 900, 1200 s), `probePIs`, whole-training `PI`, `stablest` and `goalMinusStablest` (degrees, signed) at the end |

## 9. Loader (`explRL.core`)

```python
def loadCircuitAgent(params=None, seed=None, wG0=None, wC0=None, learnC=True, learnG=True, jumps=True):
    p = params or Params(); N = p.nCirc
    rng = np.random.default_rng(seed)
    a = int(rng.integers(N))                                   # draws in this order
    wC0 = rng.uniform(0, 1, (N, N)) if wC0 is None else wC0
    wG0 = sinGoal(rng.uniform(0.05, 0.5), rng.uniform(0, 2*pi), N) if wG0 is None else wG0
    policy = circuitPolicy(wG0, wC0)
    return circuitAgent(a, policy, CircuitRL(policy, learnC, learnG, jumps), p, rng)   # agent keeps using rng
```

## 10. Expected values (checked with the prototype)

| Goal | `rG` | `dS` range | `rF` range | Mean fixation at goal / opposite |
|---|---|---|---|---|
| `g = 0.25` | 4 | 0.333-0.667 | 0.267-0.600 | 2.49 s / 1.22 s |
| `g = 0.5` | 8 | 0.167-0.833 | 0.100-0.767 | 5.27 s / 0.97 s |
| all ones | 0 | 0.5 | -0.233 (so `nuF = BF`) | 15.8 s everywhere |

Largest possible `rG` (square wave of 16 ones) is `N/pi` = 10.19. Then `dS` lies in about 0.08-0.92.

## 11. Demo layout and artifacts

| Section | Content | File under `results/demo_circuit/` | When |
|---|---|---|---|
| Policy | `dS` and mean fixation `aF / nuF` vs compass minus goal, weak (`g = 0.25`) and strong (`g = 0.5`) goal | `policy_curves.png` | every run |
| Goal plasticity | goal weights before and after one 5 s fixation (`ceil(5 / dtG)` updates) at compass heading 90 degrees with reward and with punishment; goal heading and strength over 50 rewarded fixations in a row at that heading | `goal_plasticity.png` | every run |
| Goal learning | `'goal'`: distance to safe and strength vs time (`heldValue` on a 1 s grid), mean over flies | `quick/` or `full/goal_learning.png` | quick and full |
| Compass learning | `'compass_asym'` and `'compass_sym'`: `wC` heat map of fly 0, `mapJumpProb` vs arena heading, mean fixation from `readout` of the after-training probe (both mean over flies), probe jump rate before and after | `quick/` or `full/compass_learning.png` | quick and full |
| Both | `'both'`: goal distance and strength vs training time (mean over flies), mean probe PI at the probe times, histogram of single-fly final probe PI | `quick/` or `full/both.png` | quick and full |
| Metrics | `mode`, `seed`, `nRuns`, `lengths_s`; full adds `AC8_*` (distance and strength, start and end), `AC9_*` (asymmetric map `pJ` and probe jump rate, symmetric probe and training jump rate), `AC10_*` (distance and probe PI at start and end, final probe PI min and max, mean absolute goal minus most stable compass heading) | `quick/` or `full/metrics.json` | quick and full |

Deterministic plots go to the top level (`mode=None`). Quick runs (normal tests) use 2 flies with the same run lengths (about 4 s); full runs (`#| slow`) use 20 flies and assert AC-8 to AC-10 (about 21 s). The summary cell lists the measured values.
