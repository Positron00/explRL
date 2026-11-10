# Design (low level): Phase 22

Part of [README.md](README.md). The module contents follow; each module stays under 200 lines.

## `b3_agents.py` (new)

```python
B3_KNOBS = dict(trustOne=(0.0, 1.0), spread=(0.0, 1.0), shareAll=(0.0, 1.0), guess=(0.0, 0.5))

def b3Rng(seed, slot):                     # np.random.default_rng([seed, 22, slot]); made only for non-default knobs
def isDefault(b3, world): ...              # True if world has no 'b3' key, or every knob is 0 (guess: the world's own value)

class TrustOne:                            # mixin for ColonyAgent, GuardAgent, ThresholdGuard, RuleBridge
    "knownFor: super().knownFor(b) (so failFlag's flag-aware _flagKnown is kept), then for each clue absent from it, the leading
    value among values with no failures (failFlag boards) with < q senders, when the draw cached for (k, j, value) < trustOne."
class Spread:                              # mixin for RuleAgent and ViewAgent; does not re-implement choose (that would bypass
                                           # RuleBridge.choose's relays and GuardAgent's / ThresholdGuard's choose)
    "choose: act = super().choose(b, t); if act is an open and the b3 draw < spread, retarget it to the least-crowded live subtask
    (the fewest openers; ties: most known clues, then value, then at random on the b3 generator)."
class ShareAll:                            # mixin for RuleAgent and ViewAgent
    "_shareable(self, b, kn, t, *a) (GuardAgent calls _shareable(b, None, t, ks)): with probability shareAll on this turn, sets
    self.share = 'always', calls super()._shareable(b, kn, t, *a) and restores it after, so it works for RuleAgent (plain arms,
    Phase 14) and ViewAgent alike."

def b3Members(world, members, seed):
    """Wrap each honest numpy member (not liars or mistaken members) with the mixins whose knob is non-default, by building a
    subclass of its class on the fly (for an `InSquad` wrapper, of its inner `m.m`); guess goes to RuleAgent's own argument. Identity when isDefault."""
```

- **Draw order.** `trustOne`, `spread` and `shareAll` draw from `b3Rng`; `guess` uses `RuleAgent`'s existing draw, which is made at every guess step today, so default runs are unchanged. A mixin draws from `b3Rng` only when its knob is non-default, and never from the member's own `rng` or the board's streams. So θ_default runs are draw for draw today's (AC-2), and a non-default run changes only what its knob changes.
- **`trustOne` is a belief, not a coin per turn.** The draw for (k, j, value) is made the first time the agent sees that value leading with fewer than q senders, then cached for the board. An agent that trusted a value keeps trusting it until another value leads.
- **`spread` targets crowding.** The board keeps 2N + 2 subtasks open. Rule agents open the subtask with the most known clues and the highest value, so as N grows more of them pile onto the same few. Phase 18 measured more openers per lied subtask as teams grew. Whether this or sharing (`shareAll`) or guessing (`guess`; Haiku's wrong answers on clean boards rose from 0.09 to 0.18 of answers, 8 to 32 agents, in Phase 15's traces, against 0 for rule agents) drives behaviour 1 is what `chooseKnob` decides.
- **Mirror posts (P22-12)** are Phase 20's (its FR-A4): structure, present at θ_default too, and only on bridge boards. B3 adds no mixin for them.

## Fit cells (`b3_fit.FIT_CELLS`)

Clean cells, target `pooledShare` (15). Claude means from the cached `runs.csv`; numpy means from Part 0 (`colony/forecast/runs.csv`, seeds 3000-3029) where it ran the same arm, for comparison.

| Study (folder) | Board | Arm | N | Claude seeds | Claude mean | Numpy today |
|---|---|---|---|---|---|---|
| Phase 14 (`scale/full`, `baseline`) | plain, one holder per clue (`CLUE_SETTINGS`) | plain | 8, 16, 32 | 900-904 | 0.406, 0.384, 0.341 | 0.512, 0.435, 0.356 (Phase 15's numpy, seeds 2000-2019) |
| Stage 1 (`colony/stage1`) | `WORLD18` | plain | 8, 16 | 1800-1807 | 0.455, 0.422 | 0.464, 0.386 |
| Stage 1 | `WORLD18` | confirm | 8, 16 | 1800-1807 | 0.378, 0.371 | |
| Stage 1 | `WORLD18` | colony | 8, 16 | 1800-1807 | 0.363, 0.361 | 0.383, 0.342 |
| Stage 1 | `WORLD18` | colonyGuards | 8, 16 | 1800-1807 | 0.366, 0.359 | 0.325, 0.284 |
| 32-agent run (`colony/stage32`) | `WORLD18` | plain, colonyGuards | 32 | 1800-1807 | 0.357, 0.314 | 0.309, 0.246 |
| Stage 4 (`colony/stage4`) | `WORLD18` | failFlag, guardDeal | 16 | 1800-1807 | 0.359, 0.230 | |

Counting-board cells with independent scripted liars, target `contamination` (17). Numpy means from Part 0 and Stage 4's forecast (`forecast4/runs.csv`).

| Study | Arm | N | Claude mean | Numpy today |
|---|---|---|---|---|
| Stage 1 | colony | 8, 16 | 0.522, 0.669 | 0.095, 0.198 |
| Stage 1 | colonyGuards | 8, 16 | 0.250, 0.368 | 0.000, 0.111 |
| 32-agent run | colonyGuards | 32 | 0.449 | 0.324 |
| 64-agent run (`colony/stage64`) | colonyGuards | 64 | 0.554 | 0.389 |
| Stage 4 | failFlag | 16, 64 | 0.205, 0.284 | 0.023, 0.047 |
| Stage 4 | guardDeal | 16, 64 | 0.375, 0.491 | 0.252, 0.508 |
| Stage 4 | guardDealFlag | 16 | 0.218 | 0.064 |
| Stage 4 | squads | 16, 64 | 0.256, 0.289 | 0.084, 0.127 |
| Stage 4 | squadsAll | 64 | 0.173 | 0.038 |
| Stage 4b (`colony/stage4b`) | failFlag, guardDeal, squads | 32 | 0.224, 0.428, 0.284 | 0.038, 0.361, 0.114 |

All Claude cells have 8 boards (seeds 1800-1807) except Phase 14's 5. Left out (P22-3): `record` and `colonyVolunteer` cells, Stage 3's Claude liars, the `error` and `collude` faults (reported as held-out checks of the fitted simulator), `confirm` with liars, and plain-board liar cells (rule agents take the newest value there, contamination 0.94-0.99 against Claude's 0.72-0.85; no knob changes it, and the misfit is reported).

**Both targets inform both knobs.** On a clean counting board, `trustOne` lets agents use true one-sender values sooner, which raises clean pooled share. So the two knobs are fit jointly.

## Folds (`b3_fit.FOLDS`)

| Fold | Scores | Drops (fit cells) | Left: clean, contamination |
|---|---|---|---|
| `S1` | Stage 1's forecast: H18-1 to H18-4, H18-6, colony against confirm | all Stage 1 cells | 7, 13 |
| `S4` | Stage 4's: H18-13 to H18-15, `did_*` | Stage 4's cells; 64-agent `colonyGuards`; Stage 1's 16-agent `colonyGuards` liar cell | 13, 7 |
| `S4b` | Stage 4b's: H18-16 to H18-18 | Stage 4b's cells; 32-agent `colonyGuards` liar cell | 15, 13 |
| `P14` (secondary) | Phase 14's two team-size calls | Phase 14's 3 clean cells | 12, 17 |
| `all` | (θ0 for forward forecasts) | the experiment's reused cells only (C1: Stage 4 `squads` 64, 64-agent `colonyGuards`) | 15, 15 for C1 |

## `b3_fit.py` (new)

```python
SIM_SEEDS = tuple(range(3000, 3030))                 # Part 0's seeds, as every Phase 18 forecast
COARSE = dict(trustOne=np.arange(0, 1.01, 0.2), spread=..., shareAll=..., guess=np.arange(0, 0.51, 0.1))
FINE_STEP = dict(trustOne=0.1, spread=0.1, shareAll=0.1, guess=0.05)

def claudeTargets(rows): ...                         # {cell: (mean, se >= 0.01, n)} over Claude boards
def simCell(cell, theta, seeds=SIM_SEEDS): ...      # colonyCell(..., 'numpy'), bridge_grid.c1Cell(study, arm, seed, fault, runner='numpy')
                                                     # for C1 cells (colonyCell has no bridge arms unless arms=ARMS20), or clueCell
                                                     # for Phase 14; world['b3'] = theta, through b3Replay
def b3Replay(cfg, seed): ...                         # colony_trace.replay's numpy branch with members -> stage4Members (which applies
                                                     # Phase 20's bridgeMembers) -> b3Members; row = stage4Columns, and on bridge
                                                     # boards bridge_mech.c1Columns(cfg, rp) (as runC1Cell's numpy rows: stage4Columns
                                                     # + bridgeColumns with the replay's answers + contestColumns; crossContamination
                                                     # needs rp.answers); Phase 14: runClueNumpy's row. At θ_default it equals replay.
def gridSim(cells, grid, workers=8): ...            # every (theta, cell, seed) once; cached in results/multiagent/b3/grid/
def loss(theta, cells, sims, targets):               # sum over cells of ((sim mean - claude mean) / se) ** 2
def fit(cells, sims, targets, drop=()): ...          # argmin loss over the grid
def heldOut(fold, sims, targets): ...                # loss on the fold's dropped cells at fit(drop=fold), and at θ_default
def chooseKnob(sims, targets): ...                   # summed heldOut over S1, S4, S4b on COARSE; lowest wins; ties -> 'spread'
def bootTau(cells, sims, rows, n=200, seed=0): ...   # SD of the fit over resamples of Claude boards within cells; floor 0.1
def refit(theta0, tau, pilot, sims): ...             # P22-6, below
def fitHealth(fits, folds): ...                      # bound hits; H22-3 (held-out loss < θ_default's in >= 2 of 3 folds)
```

## The pilot refit (`refit`)

For each grid point θ (the refit varies only parameters with a pilot measure; the others are held at θ0):

J(θ) = Σ over pilot measures t of ((sim_t(θ) − pilot_t) / s_t)² + Σ over refit parameters p of ((θ_p − θ0_p) / τ_p)²

- `sim_t(θ)`: the simulator's mean of measure t on the pilot's own cells (same arm, N and fault, seeds 3000-3029).
- `pilot_t`: the pilot's mean over its boards of that cell.
- `s_t`: the cached Claude per-board standard deviation of measure t, pooled over the fit cells of that measure, over √(pilot boards). One pilot board has no spread of its own.
- `τ_p`: `bootTau`, at least 0.1, so one pilot board can move a parameter about one grid step when it disagrees by one standard deviation.

**What each pilot informs:**

| Experiment | Pilot | Measures | Refit |
|---|---|---|---|
| C1 | seed 1890: `coupled`, `bridge1`, `bridgeGuard`, 64 agents, liars | `contamination` per board | `trustOne`; the behaviour-1 knob keeps θ0 (no clean board) |
| A2 | team 2190, own records; drop-only at 32 | none represented | nothing (no simulator forecast) |
| C2, C4 part b | their specs | `contamination` on liar boards, clean pooled share on clean boards | as available |
| Retrospective | Stage 1: 4 boards at 16 (colony, plain; clean, liars); Stage 4: 3; Stage 4b: 3 (all seed 1890) | Stage 1: both; Stage 4, 4b: `contamination` | as available |

C1's relays per bridge turn and mirror posts per holder are compared, simulated against the pilot, in the forecast file, and not fitted (P22-6).

## `b3_forecast.py` (new)

```python
@dataclass(frozen=True)
class Effect:
    id: str; hyp: str; measure: str; fault: str; N: int
    terms: tuple                     # ((coef, arm), ...): the effect is sum(coef * mean(arm)), paired on seed where seeds match
    naive: str                       # '+' or '-': the sign meaning "the design is better" (P22-8)
    represented: bool = True
    note: str = ''

def estimate(rows, e, seeds=None): ...              # per-seed values and their mean, rows levelled '<arm>|<fault>'
def forecastSim(effects, cellFn, theta, seeds=SIM_SEEDS):   # represented effects: estimate, 95% bootSeeds interval, sign
def forecastPilot(effects, pilotRows, priorRows, estimateFn=estimate):
    # each arm from the pilot if it has it, else from priorRows; unpaired arm means; sign of the point estimate; 0 if missing
def forecastNaive(effects): ...                     # {id: e.naive}
def forecastExperiment(exp, effects, cellFn, pilotRows, priorRows, pilotMap, reused, estimateFn=estimate):
    # θ0 = fit(all fit cells minus reused); τ = bootTau; θ_pilot = refit(θ0, τ, pilotMap(pilotRows)); then the five lines
def writeForecast(f, path) -> str: ...              # json.dumps(sort_keys=True, indent=1) + '\n'; returns SHA-256
def scoreExperiment(predPath, observed): ...        # paper2's rule per item and forecaster; counts on the common set and all
```

A forecast file holds `exp`, `b3Plan` (the `B3_PLAN` hash), `commit`, `seeds`, `rule`, `theta` (`default`, `prior`, `pilot`), `tau`, `pilot` (boards, measures, simulated against observed, relays and mirror posts for C1) and `items`: per effect id, `hyp`, `terms`, `naive`, `represented`, and per forecaster `estimate`, `ci` (simulators) and `sign`.

## Effects (`b3_effects.py`)

**C1** (Phase 20; `measure` `honestPooled` unless stated; liars = `independent`; N 64). "Boards" are the Claude boards the outcome uses.

| ID | Hypothesis | Terms (+ = design better) | Fault | Boards | Naive | Pilot-only can compute |
|---|---|---|---|---|---|---|
| `C1-1` | H20-1 | `bridge1` − `colonyGuards` | liars | 1800-1807 | + | yes (`colonyGuards` from the cache) |
| `C1-2` | H20-2 | `bridge1` − 0.5 `colonyGuards` − 0.5 `squads` | liars | 1800-1807 | + | yes |
| `C1-3` | H20-3 | `bridge1` − 0.5 `coupled` − 0.5 `squads` | liars | 1800-1804 | + | yes |
| `C1-4` | H20-4 | `bridge2` − `bridge1` − 0.25 `squads` + 0.25 `coupled` | liars | 1800-1804 | + (the hypothesis expects −) | no: 0 |
| `C1-5` | H20-5 | false-relay share: `bridge1` − `bridgeGuard` | liars | 1800-1804 | + | yes |
| `C1-6` | H20-5 (second measure) | `bridgeGuard` − `bridge1` | liars | 1800-1804 | + | yes |
| `C1-7` | H20-8 | `bridge1` − `squads` | clean | 1800-1804 | + | no: 0 (no clean pilot board) |
| `C1-8` | H20-8 | `squads` − `coupled` | clean | 1800-1804 | + | no: 0 |

Margins are written as linear terms, so H20-2's "keeps at least half the lead" is `C1-2` > 0, and H20-3's win-back above 0.5 is `C1-3` > 0. The false-relay share is Phase 20's FR-D1 column. Not forecast: H20-6 (3B part b) and H20-7 (per-arm contamination, descriptive).

**A2** (Phase 21; none represented; `estimateFn` reads `a2Summaries`' per-team values).

| ID | Hypothesis | Effect (+ = design better) | Naive | Pilot-only can compute |
|---|---|---|---|---|
| `A2-1` | H21-1 | own-record contrast − shared-record contrast | + | no: 0 (pilot has no shared arm) |
| `A2-2` | H21-2 | own-record contrast | + | yes (team 2190) |
| `A2-3` | H21-3 at 8 | `suppressedHeld`: original − drop-only | + | no: 0 |
| `A2-4` | H21-3 at 32 | the same at 32 | + | yes: drop-only seed 990 against Phase 14's originals, seeds 900-904 |

**Retrospective** (`RETRO_EFFECTS`; each study's frozen estimate rule from `tools/colony_forecast.py`; Haiku results from the saved score files).

| Study | Item | Effect | Haiku | Unfitted (today) | Naive | Pilot-only can compute |
|---|---|---|---|---|---|---|
| Stage 1 | H18-1 | colony − plain, liars | + | + right | + right | yes |
| Stage 1 | H18-2 | contamination, plain − colony | + | + right | + right | yes |
| Stage 1 | H18-3 | colony − plain, clean | − | − right | + wrong | yes |
| Stage 1 | H18-4 | colonyGuards − colony, liars | + | − wrong | + right | no (no guards in the pilot) |
| Stage 1 | H18-6, colony against confirm | | no call | | | |
| Stage 4 | H18-13 | guardDeal − colonyGuards, 64 | + | − wrong | + right | yes |
| Stage 4 | `did_guardDeal` | its change 16 to 64 | + | + right | + right | no |
| Stage 4 | H18-14 | failFlag − colonyGuards, 64 | + | + right | + right | no (pilot has failFlag at 16) |
| Stage 4 | H18-15 | squads − colonyGuards, 64 | + | + right | + right | yes |
| Stage 4 | `did_squads` | its change 16 to 64 | + | + right | + right | no |
| Stage 4 | `did_failFlag` | | no call | | | |
| Stage 4b | H18-17, H18-18 | failFlag, squads − colonyGuards, 32 | +, + | +, + right | + right | yes |
| Stage 4b | H18-16 | | no call | | | |
| **11 conclusive** | | | | **9 right** | **10 right** | |

For the retrospective, `priorRows` are the Claude cells that had run before each study's pilot (Phase 18 README's dates): none of the counting board for Stage 1; Stage 1, the 32-agent run, Stage 3 and the 64-agent run for Stage 4; those and Stage 4 for Stage 4b. Phase 14's two team-size calls (`P14` fold; pooled share −, right; honest loss −, wrong against Haiku's +) are scored for the two simulators only: team size is not a design, so every-design-helps and pilot-only do not apply.

## Scoring and the gate (`b3_report.py`)

- **Per item:** right, wrong or no call, by paper2's rule, for each forecaster. Claude's interval is the experiment's own `bootSeeds` interval over its boards (2,000 resamples), for C1 from `c1Summaries`.
- **Per experiment:** counts on the common set (represented items) and on all items (an unrepresented item is a 0 for both simulators).
- **Pooled:** sums over experiments with a frozen forecast.
- **Beside the gate (P22-17):** fitted against pilot-only on only the items pilot-only computes (no fallback), right and wrong counts.
- **Gate B3 (H22-1):** with at least 8 conclusive items in the pooled common set, it passes if fitted right > unfitted right, fitted right > pilot-only right and fitted right > every-design-helps right. Beside it: wrong counts, and an exact two-sided McNemar p for fitted against each alternative (a binomial test on the items where exactly one of the two is right).
- **H22-4:** fitted against prior-only, the same counts, descriptive.

## `B3_PLAN`

| Item | Definition |
|---|---|
| knobs | `B3_KNOBS`, defaults θ_default; the behaviour-1 candidates and `chooseKnob`'s rule (ties to `spread`) |
| fit | `FIT_CELLS` (15 clean, 17 contamination), `claudeTargets`, `loss` (se floor 0.01), `COARSE`, `FINE_STEP`, `SIM_SEEDS` 3000-3029 |
| folds | `S1`, `S4`, `S4b`, `P14`, `all` minus reused cells |
| fit health | stop and ask on a bound hit or H22-3 failing; H22-3 and the retrospective reported for all three candidates, with the caveat that the knob was chosen on the same folds (P22-18) |
| refit | J(θ) above; τ = `bootTau` (200 resamples, floor 0.1); parameters without a pilot measure keep θ0 |
| forecasters | fitted, unfitted, pilot-only, every-design-helps; prior-only descriptive; simulator signs by the 95% interval over 30 seeds |
| effects | `C1_EFFECTS`, `A2_EFFECTS`, `RETRO_EFFECTS`; C2's and C4 part b's added by their own frozen plans before their pilots |
| scoring | paper2's rule; a predicted 0 on a conclusive outcome is wrong; common set primary, all items secondary |
| gate | H22-1 strict counts on the pooled common set, at least 8 conclusive items; McNemar reported; no downstream effect |
| experiments | C1, C2, C4 part b (simulated); A2 (two lines) |
| exploratory | True |

## Runtime derivation

- **Rate.** Stage 4's numpy forecast played 1,050 boards (7 arms × 5 sizes, 8-128 agents, 30 seeds) in 2 minutes on 8 workers: about 8.75 boards a second. Part 0's 10,080 boards (4-128 agents) took 10 minutes, faster because of its small boards. The fit cells run at 8-64 agents, so 8.75 a second is conservative.
- **Boards per grid point.** 32 fit cells (15 clean, 17 with liars) × 30 seeds = 960 boards.
- **Coarse grid.** 3 candidates × 6 × 6 = 108 points, 96 distinct (the 6 points with the knob at 0 are shared): about 92,000 boards, about 2.9 hours.
- **Fine grid.** The chosen candidate's 11 × 11 = 121 points, 85 new: about 82,000 boards, about 2.6 hours.
- **Folds and bootstraps** reuse the grid cache: no new boards.
- **Retrospective.** The default check reruns Part 0's Stage 1 cells at 8 and 16 and Stage 4's cells at 16, 32 and 64 (about 1,400 boards). Each of 3 folds needs two settings (θ0 and θ_pilot), about 2,800 boards each: about 10,000 boards, 20-30 minutes.
- **C1's forecast.** The refit: 11 values of `trustOne` × 3 pilot cells × 30 seeds = 990 boards at 64 agents. The forecasts: 9 cells × 30 seeds × 3 settings (θ_default, θ0, θ_pilot) = 810. At an assumed 2 seconds per 64-agent board per worker, about 8 minutes; under 30 with margin.
- A 1-seed timing probe of the slowest fit cell (64 agents) replaces the rate before the fit (T4).

## Tests

| Test | Flag | What it checks |
|---|---|---|
| `test_b3_defaults` | offline | AC-2: at θ_default, cells at 8-64 agents equal today's rows and turn logs; no `b3Rng` is made |
| `test_b3_behaviours` | offline | AC-3: `trustOne`, `spread` and `shareAll` on hand-built boards; only honest members change |
| `test_b3_mirror` | offline | AC-4 (needs Phase 20's board): an honest holder posts on its mirror and a `RuleBridge` relays it; with `spread` = 1 a `RuleBridge` still relays |
| `test_b3_fit` | offline | AC-5: a planted θ is recovered within one grid step on a tiny grid; folds drop the listed cells; `chooseKnob`'s rule and tie |
| `test_b3_refit` | offline | AC-6: θ_pilot = θ0 for a pilot equal to θ0's simulation; untouched parameters; the large-τ limit |
| `test_b3_forecasters` | offline | AC-7 on a fake experiment: the five lines, pilot-only's fallback to every-design-helps' sign for a missing arm, unrepresented effects |
| `test_b3_retro_counts` | offline | AC-8: the unfitted and naive lines give 9 and 10 of 11, item by item, from the saved score files |
| `test_b3_files` | offline | AC-9: `writeForecast` byte-identical; `scoreExperiment` on hand-made cases; `gateB3`'s rule, minimum and refusal |
| `test_b3_c1` | offline | AC-10 (needs Phase 20): `c1Forecast` with a fake pilot writes 8 effects with five lines each, and the file's `note` states the two sign conventions of P22-19 |
| `test_b3_hashes` | offline | NFR-1: Phase 5-21 hashes; the SHA-256 of the committed Phase 13-18 prediction and score files |
| regression | `slow` | NFR-1: θ_default reruns of Part 0's and Stage 4's forecast cells equal `forecast/runs.csv` and `forecast4/runs.csv` |

## Handoffs

- **Phase 20 (C1).**
  - Honest rule agents post on mirrors (P22-12, in Phase 20's FR-A4): one rule in `bridge_agents`, tested by `test_b3_mirror`.
  - Bridge cells run with the numpy runner: `bridge_grid.c1Cell(study, arm, seed, fault, runner='numpy')` builds them, `stage4Members` applies `bridgeMembers` (Phase 20's hook in `colony_board`), and Phase 20's `runC1Cell` gives numpy rows with `bridge_mech.c1Columns(cfg, rp)`; B3's `b3Replay` uses the same pieces (`test_c1_numpy` in Phase 20).
  - Relays in the unfitted simulator (P20-17, P22-20): scripted `ClueLiar`s trust single posts, so relays feed liars' coupled solves; honest coupled solves are 0 at θ_default (numpy `bridge1`, seed 1890: 32 coupled solves, all by liars). The B3 report states this beside C1's forecast.
  - Phase 20's `C1_PLAN` forecast row names `C1_EFFECTS`' 8 items and the five lines (done, 2026-11-10).
  - T9 calls `c1Forecast()` with the pilot's rows and commits `c1_predictions.json`.
- **Phase 21 (A2).** At T5's second freeze, `a2Forecast(pilotRows)` writes `a2_predictions.json`, and its SHA-256 goes into `A2_PLAN`. If B3's code does not exist then, A2 writes the two lines by hand by the rules above, and B3 later checks them with `forecastPilot` and `forecastNaive`. The fitted line reads "not represented" either way, which is not a deviation.
- **C2 and C4 part b.** Their specs write their effect lists (with `naive` and `represented`), a numpy `cellFn`, `pilotMap` and `reused`, and freeze them before their pilots (P22-15).
