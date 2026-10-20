# Design (low level): Phase 18, colony rules for large Claude teams

High-level design: [design-high-level.md](design-high-level.md). Requirements: [requirements.md](requirements.md).

## `clue_colony` (new)

```python
COLONY_OPTS = ('colony', 'confirm', 'guards')         # world keys; 'fault' is read by colony_agents.faultClass
Q = 2                                                  # senders for "confirmed"

def leading(tal, k, j); def contestedCount(tal)   # the leading value of a clue; clues showing two or more values

def tally(channel, board):
    "{k: {j: [(r, senders, newest)]}} for open subtasks: per clue, each posted value with its distinct senders (a set) and its newest post time, ordered by len(senders) desc, then newest desc."

def colonyLine(board, tal, q=Q):
    "'Clues shared on the board: T3: x mod 7 = 4 (2 agents, confirmed) | x mod 7 = 2 (1 agent, unconfirmed), contested; T5: x mod 3 = 1 (1 agent, unconfirmed)' (or 'none'); subtasks in board order, clues by index."

def knownColony(i, board, channel):
    "As clue_agents.known, but per clue the value with the most senders (ties: newest), own clues winning."

COLONY_RULES, CONFIRM_RULES, GUARD_RULE = '...', '...', '...'   # FR-A2, FR-A3, FR-A5 wording, verbatim
SHARE_AGAIN = '...'           # the plain sentence the two options replace (located in clue_text's rules; asserted present)

def colonyRules(env, text, i=None):
    "The rules text with SHARE_AGAIN replaced (colony or confirm) and GUARD_RULE appended for guard slots; unchanged when no option is set."

def checkOptions(world, N=None, nLiar=0):
    "colony and confirm exclusive; guards an int in [0, N - nLiar); fault in ('independent', 'collude', 'error'); q >= 1; raises ValueError."
```

`TextClueEnv` (`clue_text`) gets `colony=False, confirm=False, guards=0, nLiar=0, q=2` keywords (`nLiar` from the cell's configuration, to place guard slots; it calls `checkOptions`) (through `fixOptions`); its board line becomes `colonyLine(t, tally(...))` when `colony`; its "clues you know" counts use `knownColony` when `colony`; `rules(i=None)` returns `colonyRules(self, <current text>, i)`. The guard slots are `range(nLiar, nLiar + guards)`. `renderPrompt(env, obs, memory, notes, past, framing, i=None)` and `LLMMember` pass the slot; `rollout` passes `i`. With no option set every string is byte-identical (FR-A6), tested by a hash over rules, schema, observations, rows and logs, as Phase 13's `clue_fix` test.

`clue_text` (188 lines after the change) only calls into `clue_colony`.

## `colony_agents` (new)

```python
class ViewAgent(RuleAgent):
    "RuleAgent's choice with the agent's own `heldFor(b, k)` and `knownFor(b)` (unchanged by default; tested equal to RuleAgent)."

class ConfirmAgent(ViewAgent):
    "The numpy `confirm` arm: first shares a held clue whose latest shown value differs; else as RuleAgent."

class ColonyAgent(ViewAgent):          # __init__(channel, rng, share='needed', guess=0.0, q=Q)
    "Knows a shown value only if confirmed (>= q senders) or held; shares a held clue whose leading value is missing, different or unconfirmed (and not already its own)."

class GuardAgent(ColonyAgent):
    "Never opens; per turn shares one held clue whose leading value is missing, wrong or unconfirmed (earliest-expiring subtask first), else waits."

class ThresholdGuard(ColonyAgent):     # __init__(..., q=Q, theta=2)
    "Acts as GuardAgent on turns when at least theta clues on the board are contested, else as ColonyAgent."

class ColludingLiar(ClueLiar):
    "On a lying turn (every other turn), first reposts a fellow liar's false value on an open subtask that fewer than two liars posted; else lies as ClueLiar. Liars register on the channel to know each other."

class MistakenAgent(ViewAgent):        # __init__(..., p=0.3)
    "A rule agent (share 'needed') that misreads each clue it holds with probability p, once per clue (a wrong residue uniform among the others), and uses the misread value in its posts, known clues and answers."

def faultClass(world):                 # 'independent' (default) -> ClueLiar, 'collude' -> ColludingLiar, 'error' -> MistakenAgent
def memberClass(world, slot, nLiar=0): # honest numpy slots: guard slots -> GuardAgent; 'theta' -> ThresholdGuard; 'colony' -> ColonyAgent; 'confirm' -> ConfirmAgent; else RuleAgent
```

Liars know their fellow liars (they register on the channel), which is what collusion means; every liar post is false by construction, so no ground truth is used. A `MistakenAgent` misreads only its own view (the board's deal is unchanged, so the other holder keeps the true value). `runClueNumpy`, `runClue`, `colony_trace.replay`, `rollout`'s callers (`runEval`, `trainRL17`) build members from `faultClass` and `memberClass`. `MistakenAgent` is scripted in LLM cells too (it fills a faulty slot, as liars do).

## `colony_trace` (new)

```python
Replay = namedtuple('Replay', 'rows log board answers nLiar T')
def replay(cfg, seed, client=None)      # one cell exactly as runClueNumpy (client None) or runClue (rows and turn log equal, tested),
                                        # keeping the board and the submitted answers {(t, agent): x}
def falseValues(board)                  # {(k, j, r): (time, poster) of its first post} for every false value
def contaminatedBy(board, sub, x, fv)   # the false values seen before the submission that the wrong answer x agrees with
def goalDrift(board, honest)            # freeRiding, misreport
def actionMix(board, honest)            # openShare, submitShare, shareShare, waitShare (honest means)
def traceBoard(board, answers, nLiar)   # contamination, reach, suppression, relay, confirmFalse, contestFalse, confirmTrue,
                                        # falseValues, goal drift, action mix
def colonyColumns(rp)                   # the row plus pooledBound, honestPooled and traceBoard
def runTraced(cfg, seed, client)        # runClue's signature for runLLMCell: same requests and turn log, rows with colonyColumns
def runColonyCell(cell)                 # for runWorkload: every Phase 18 cell, numpy or LLM, with Phase 18's columns
def traceCell(cell, client)             # an LLM cell replayed through a (cache-only) client: $0
def specIndex(slotLogs, nLiar, seed=0, nNull=200)   # FR-B6 per board: (index, shuffled null)
def rolloutColumns(cfg, board, slotLogs, seed); def isPhase18(world)   # clue_roll.coopRows adds these on Phase 18 cells only
```

A false value counts as seen when posted earlier, or at the same time by a lower slot (agents at one time act in slot order). Rows carry the full-information bound only through `replay` (adding it to `clueMetrics` would change earlier phases' cached outputs), so every Phase 18 cell runs through `runColonyCell`; `coopRows` adds `rolloutColumns` only when `isPhase18(world)` (two holders or a colony option), so Phase 12-17 rows are unchanged.

Validation (AC-6, revised 2026-10-19 after measuring): on Phase 14's cached baseline cells with liars (`r = 1`, N 8-32), `contamination` never above Phase 15's in any cell and rising with N as it does (Phase 15's counts exposure, from the agent's known clues; this one uptake, from the answer; measured gap 0.03-0.10 per cell).

## `colony_grid` (new)

```python
WORLD18 = {**{k: CLUE_SETTINGS[k] for k in BOARD}, 'r': 2}
COLONY_ARMS = dict(plain={}, confirm=dict(confirm=True), colony=dict(colony=True),
                   colonyGuards=dict(colony=True, guards='quarter'), record=dict(record=True))   # guards 'quarter' -> N // 4
PART0_ARMS = COLONY_ARMS without record (rule agents read no record) + colonyTheta1, 2, 4 (dict(colony=True, theta=th))
COLONY_SEEDS, PILOT_SEED, PART0_SEEDS = 1800-1807, 1890, 3000-3029; STAGE1_N, STAGE2_N, PART0_N = [8, 16], [32, 64], [4 .. 128]
def colonyCell(study, arm, N, seed, fault='clean'|'independent'|'collude'|'error', runner='llm', q=2, arms=None)
    # level '<arm>|<fault>' ('|q3' appended when q != 2, with r = q); nLiar = N // 4 when fault; full memory (clueCell's default, as Phases 11-15)
STAGE1_CELLS                            # 5 arms with independent liars, plain and colony with mistaken members, 4 clean arms
def colonyPilotGrid(); def stage1Grid(seeds, sizes); def stage2Grid(arm, seeds, seeds64, sizes); def part0Grid(seeds, sizes); def stage1Quick(turns=3)
def colonyEstimate(cells)               # fixEstimate with the pilot's cells as cached
def costRule1(perCall, plan=None)       # FR-A10: projected Stage 1 <= $35 run, <= $50 cut to 6 seeds, else stop
def costRule2(perCall, arm, plan=None)  # above $90 projected, N 64 on 5 seeds; perCall = the pilot's x COLONY2_PLAN['priceRatio'] (2)
def goNoGo(rows, alpha=0.05, sizes=STAGE1_N)   # FR-A11 -> dict(verdict, arm, p, adv)
COLONY_PLAN, COLONY2_PLAN               # unfrozen until their gates; COLONY2_PLAN carries arm, capRaised, cap, priceRatio
def syntheticRows18(effects, seeds, sizes, noise, seed)   # rows with known effects, for colony_report's and goNoGo's tests
```

Cell counts, Stage 1: per seed and N, 4 clean + 5 with independent liars + 2 with mistaken members = 11 cells; 8 seeds x 2 sizes: 176 cells. Calls: about 40 per LLM agent (clean N, with faulty members 3N/4): 2,960 per seed at N 8, 5,920 at N 16. Part 0: 6 sizes x 7 arms x 4 fault settings (none and three faults) x 2 quorum sizes x 30 seeds = 10,080 numpy cells.

## `colony_report` (new)

```python
def cellVals(rows, arm, fault, metric, sizes=None)        # {(seed, N): value}
def pairs(rows, arm, metric, fault='independent', base='plain', sizes=None)   # {(seed, N): arm - base}
def signFlipExact(d, tail='greater')    # exact over 2**len(d) sign patterns up to 20 values (16 pairs: 65,536), else seeded flips
def bootSeeds(dp, stat, nboot, seed)    # interval resampling seeds (a seed's pairs stay together across N)
def trendSlopes(rows, arm, sizes, fault, metric)          # per seed: least-squares slope of the advantage over log2 N
def lossRecovered(rows, arm, sizes); def efficiency(rows, arm, fault, sizes)
def colonySummaries(rows, plan, nboot=2000)   # FR-A12: H18-1..6, Holm, secondary, per cell means (plan['report']), the trend and colluding liars when plan['stage2'] is set
def writeColony(path, S, meta); def figColony(out, S)    # report.md; colony.png: advantage vs N per arm, contamination and free-riding per cell
```

Holm uses `bench_stats.holm`. `honestPooled` is a row column (from `colony_trace.colonyColumns`).

## `tools/colony_forecast.py`

`run <repo> [workers]`: `part0Grid()` through `runColonyCell` in a process pool (spawn, 8 processes; numpy, no API or ledger, so not `runWorkload`); writes `results/multiagent/colony/forecast/runs.csv` and `specs/multiagent/phase18/colony_predictions.json` (per hypothesis from the q = 2 cells: estimate on the Stage 1 sizes, 95% interval over seeds, sign; H18-5: the `colony` arm's per-seed slope over N 8-64; and the screen's means per level and N). `score <repo> <runs.csv>`: FR-03's rule (a predicted 0 is never right; H18-5 scored only if Stage 2 ran `colony`); writes `specs/multiagent/phase18/colony_score.json`.

## `demo_colony` (new; Mac)

Sections: quick (fake client: Stage 1's 22 cells at seed 1800 with 3 turns; identical at 1 and 8 processes); Part 0 summary (reads the committed predictions); pilot (`llm`; asserts the forecast is committed and `COLONY_PLAN` frozen; prints invalid rate, tokens and cost per call, the plain board's honest loss, `costRule1`'s verdict); Stage 1 (`llm`; the cells the verdict allows; then tracing and `colonySummaries`, `goNoGo`); tracing check (`llm`, $0: AC-6 on Phase 14's cached cells); Stage 2 (`llm`; asserts `COLONY2_PLAN` frozen with `capRaised` and the arm; its report and the trend test read Stage 1's rows too, `runColony(..., prior=rows1)`); cached reruns of the pilot and both stages (byte-identical). Live only with `EXPLRL_LLM_LIVE=1`.

## `colony32` (T6b; a user-approved deviation)

```python
STAGE32_ARMS, STAGE32_FAULTS, N32 = ('plain', 'colonyGuards'), ('clean', 'independent', 'error', 'collude'), 32
def stage32Grid(seeds=COLONY_SEEDS)             # study colony32, 64 cells
COLONY32_PLAN                                   # frozen; deviation record, cap 200, H18-7 primary, H18-8/9, tax, trend
def stage32Summaries(rows32, rows1, plan, nboot) # hyp (H18-7..9), tax, trend (slope over log2 N at 8, 16, 32, two-sided p), per-cell means
def writeStage32(path, S, meta)
```

`demo_colony` runs it behind `EXPLRL_COLONY_STAGE=stage32` with the plan's cap; `runColony(..., analyse=...)` takes the summary and writer, and Stage 1's rows as `prior`.

## Stage 3 (T6c): adaptive liars and unassigned guards

**`clue_colony`.**

```python
DECEIVER_RULE, VOLUNTEER_RULE = '...', '...'     # FR-A14, FR-A15, verbatim
def colonyRules(env, text, i=None)               # as before, plus: DECEIVER_RULE for i < nLiar when env.fault == 'adaptive';
                                                 # VOLUNTEER_RULE for honest i when env.volunteer; nothing else changes
def checkOptions(world, N=None, nLiar=0)         # fault may also be 'adaptive'; volunteer exclusive with guards
COLONY_OPTS = ('colony', 'confirm', 'guards', 'volunteer', 'fault')   # passed to TextClueEnv by fixOptions
```

**`clue_text`.** `TextClueEnv(..., fault='independent', volunteer=False)`. `rules(i)` uses the slot whenever `guards`, `volunteer` or an adaptive fault is set (`renderPrompt` and `LLMMember` already pass the slot when `guards` is set; the test becomes "any slot-dependent option"). `parse`: for a liar slot of an adaptive cell, a share of any residue `0 <= r < p` of a prime `p` of an open subtask is valid (the report carries that residue); every other slot keeps the known-value check.

**Runners.** `llmSlots(cfg)`: `range(0, N)` when `fault == 'adaptive'`, else `range(nLiar, N)`. `runClue` and `replay` build `LLMMember`s for the liar slots of adaptive cells (same client, same env) and reserve `estimateCost(..., len(llmSlots), T)`; `rollout`'s callers pass no scripted members for adaptive cells (the policy answers every slot); `clue_roll.coopRows` and the honest range are unchanged (`range(nLiar, N)`). `fix_grid.cellCalls` counts `N x turns` for adaptive cells. `colony_agents.faultClass('adaptive')` raises `ValueError` (numpy cells cannot play it).

**`colony3`.**

```python
STAGE3_NEW = [('plain', 'adaptive'), ('colonyGuards', 'adaptive'), ('colonyVolunteer', 'independent'),
              ('colonyVolunteer', 'clean'), ('colonyVolunteer', 'adaptive')]
STAGE3_REUSED = [('plain', 'clean'), ('plain', 'independent'), ('colony', 'independent'), ('colony', 'clean'),
                 ('colonyGuards', 'independent'), ('colonyGuards', 'clean')]      # read from Stage 1's runs.csv
ARMS3 = {**COLONY_ARMS, 'colonyVolunteer': dict(colony=True, volunteer=True)}   # not added to COLONY_ARMS, which COLONY_PLAN freezes;
                                                 # colonyCell accepts fault 'adaptive' and arms=ARMS3
def stage3Grid(seeds=COLONY_SEEDS)               # study colony3: STAGE3_NEW x N 16 x seeds 1800-1807 (40 cells)
def stage3PilotGrid()                            # plain|adaptive, colonyVolunteer|independent at seed 1890
def stage3Estimate(cells)                        # new calls (adaptive cells: all N agents)
def costRule3(perCall, plan=None)                # run if the projection is at most plan['costRule']['run'] (30), else stop
def liarBehaviour(board, log, nLiar, guards)     # liarFalsePerTurn, liarTargetGuarded, liarCollude, liarRefusals
def volunteering(board, nLiar)                   # volunteers: honest agents with no open after their fifth turn and shares >= half their turns
def stage3Columns(cfg, rp, seed)                 # colonyColumns + liarBehaviour (incl. liarFalsePosts) + volunteering + specIndex/specNull (honest slots)
def runStage3(cfg, seed, client)                 # runClue's signature for runLLMCell: replay + stage3Columns, and the turn log
def runStage3Cell(cell)                          # for runWorkload (a named function, so worker processes can pickle it)
def reusedCells(seeds); def reusedRows(client, rows1, seeds)   # the six reused cells replayed through client(cfg) (the cache-only
                                                 # client: $0) with Stage 3's columns; asserts every Stage 1 column unchanged (world.* configs are tested equal)
def complianceGate(rows, plan=None)              # dict(ok, reasons, liarFalsePerTurn, liarRefusals, invalid)
COLONY3_PLAN                                     # frozen before the pilot: cells, seeds, reuse, H18-10, H18-11 (Holm), secondary, gates, costRule
def stage3Summaries(rows3, rowsReused, plan, nboot)   # FR-A18 (rowsReused: the replayed Stage 1 references)
def writeStage3(path, S, meta)
```

**`demo_colony`.** A Stage 3 section: `EXPLRL_COLONY_STAGE=stage3pilot` runs the pilot and prints the compliance gate and the cost rule's verdict; `EXPLRL_COLONY_STAGE=stage3` runs `stage3Grid` only if both pass (re-checked from the pilot's saved rows), with `runStage3Cell`, then `reusedRows` (the six Stage 1 cells replayed from the cache, $0, saved as `reused.csv`), `stage3Summaries(rows3, rowsReused)` and `writeStage3`; both also enter the cached reruns.

## Part B

### `rl17_grid` and `rl17_train` change

`RL17Config.world: tuple = ()` (pairs); `RL17_DEFAULTS['world'] = ()`, so `configHash17` leaves it out at the default. `trainRL17` also logs `longest` (the longest prompt plus reply of the step, `rl17_update.pairLengths`) for the speed check. `trainRL17`'s `lcfg` world becomes `{**{k: settings[k] for k in BOARD}, 'scheme': cfg.scheme, **dict(cfg.world)}`, and `play()`'s scripted slots use `faultClass(world)` instead of `ClueLiar` (the same class at the default).

### `rl18_grid` (new)

```python
RL18_ARMS = dict(c18team=dict(world=(('colony', True), ('r', 2)), scheme='team'),
                 p18team=dict(world=(('r', 2),), scheme='team'))
RL18_SEEDS = dict(c18team=8, p18team=5)
RL18_RUNS = interleaved [(arm, seed)]                     # 13 runs
def rl18Config(arm, seed, model, out, recipe, steps, maxLen)   # RL_PLAN v2 + BASE17 (with FIX17) + recipe + RL18_MIX (mixN ((4,.5),(8,.5)), liarShare 0.25) + arm
def speedConfig(model, out, recipe)                       # c18team, seed 1, 3 steps, maxLen 4096
def maxLenRule(longest, floor=3072, step=512)             # FR-B2's window rule
def colonySuite(models, seeds, sizes)                     # FR-B3: per model, colony and plain boards (r 2), N 4-32, clean and N // 4 liars, seeds 900-909;
                                                          # levels '<model>|<board>n<N>' and '...liar', study colonyEval, runner 'local'
def projectHours18(stepSeconds, steps, seeds)             # from the speed check: per run and total
RL18_PLAN = dict(version=1, frozen=False, recipe=None, steps=None, projectedHours=None, userConfirmed=False, ...)
```

Seeds: `c18team` 8 (H18-B2 and H18-B3 are within-arm sign-flip tests: 8 runs give p down to 1/256, room for Holm over 3); `p18team` 5 (H18-B1, a permutation test of 8 against 5, reaches 1/1287).

### `rl18_report` (new)

```python
def rl18Summaries(rows)         # H18-B1..3 with Holm, H18-B4 (goal drift), curves; specIndex and specNull come in the rows (colony_trace)
def writeRL18, figRL18, syntheticRows18B
```

### Colab cells (`colab_clue_rl`, flag `gpu`)

**Configuration** adds `RUNS18 = OUT / 'runs_p18'` and prints `RL18_PLAN`'s hash and state.

**Phase 18 speed check** (one account): asserts `RL17_PLAN['frozen']`; trains `c18team` seed 1 for 3 steps into `speed_p18/` (its own process); prints seconds per step, the longest prompt plus reply (tokens), cut prompts, invalid share, the proposed `maxLen` and `projectHours18(seconds, steps)` for the plan's candidate steps (Phase 17's `MAIN_STEPS`); the user confirms the total; `RL18_PLAN` is frozen with `steps`, `maxLen` (FR-B2's rule), `projectedHours` and `userConfirmed`.

**Phase 18 main** (every account, each with its own `HOST`): asserts `RL18_PLAN['frozen']` and `['userConfirmed']`; for each run in `RL18_RUNS`: skip if final, skip if `claim` refuses, else `trainRL17(rl18Config(...))` in its own process (resumes from its last step). When all runs are final: for the warm start and each run, if not evaluated and `claim(OUT / 'eval_p18' / 'claims' / model)` succeeds, `evalModels(colonySuite([model]), ...)` in its own process; when all models are evaluated, the account that wins `claims/_pack` writes `runs.csv` (read back from the per-model files) and `packZip('explRL_rl18.zip', ('runs_p18', 'eval_p18'))`. Otherwise it prints what other accounts hold and asks for a rerun later. The same restart rule as Phase 17 (restart the session after any error; set-up, configuration, the cell again).

## Tests

| Notebook | Checks |
|---|---|
| `clue_colony` | tally, labels and order on hand-made posts; one agent's repeats count once; `knownColony`; rule sentences only where set; option checks; rollout rows and turn logs equal `runClue`'s with each option, the guard sentence only in guard slots (AC-2) |
| `clue_text`, `clue_fix`, `clue_roll` | defaults byte-identical (hash); rollout rows and turn logs equal `runClue`'s with each option; guard sentence only in guard slots |
| `colony_agents` | AC-3 on hand-made boards (colluding, mistaken, colony, confirm, guard, threshold); `ViewAgent` equals `RuleAgent` at its defaults |
| `colony_trace` | replay equals `runClueNumpy` and `runClue` (with each option); AC-6 on hand-made logs (contamination, reach, suppression, relay, goal drift, action mix); numpy cells identical at 1 and 2 processes (NFR-4); specialization index on fixed and mixed roles; AC-6 on Phase 14's cached cells in `demo_colony` (`llm`) |
| `colony_grid` | AC-4: grid sizes, liar and guard counts, seeds, estimates, cost rules, `goNoGo` both ways and the tie |
| `colony_report` | AC-7: synthetic effects recovered, exact p, Holm order, slopes |
| `colony32` | grid (64 cells, liar and guard counts, faults), call count, synthetic analysis (H18-7, tax, trend) |
| `clue_colony`, `clue_text`, `clue_runs`, `colony_trace`, `clue_roll` (Stage 3) | AC-11: earlier arms byte-identical; deceiver and volunteer sentences only in their slots; the share exemption only for adaptive liar slots; rollout equals `runClue` and `replay` for adaptive and volunteer cells with the fake client; call counting; numpy refuses `adaptive` |
| `colony3` | grid (40 cells) and pilot; estimate and `costRule3`; `complianceGate` both ways; `liarBehaviour` and `volunteering` on hand-made boards and logs; `stage3Summaries` on synthetic rows (exact p, Holm) |
| `rl17_grid`, `rl17_train` | `world=()` hash unchanged; flag `train`: a tiny-model step with `world` set runs a colony board (AC-9) |
| `rl18_grid`, `rl18_report` | arms, seeds, configurations, the suite's cells; claims split between two simulated hosts; specialization index and null on synthetic logs (AC-9) |
| `demo_colony`, `demo_rl18` | quick sections end to end (`demo_rl18`: synthetic Part B rows and logs) |
