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

## `colony64` (T6d; a second user-approved deviation, lean)

```python
N64, STAGE64_ARMS, SIZES64 = 64, ('plain', 'colonyGuards'), [8, 16, 32, 64]
def stage64Grid(seeds=COLONY_SEEDS)              # study colony64: STAGE64_ARMS x independent liars x N 64 (16 cells; no clean boards)
def stage64PilotGrid()                           # one colonyGuards|independent board at seed 1890 (not analysed)
stage64Estimate                                  # fixEstimate with the pilot cached
def costRule64(perCall, plan); def pilotCheck64(rows, plan)   # run if projected <= $35; pilot ok if invalid < 5%
COLONY64_PLAN                                    # frozen before the pilot; deviation record, cap 250 (raised by the user), H18-12 primary, trend descriptive
def stage64Summaries(rows64, rowsPrior, plan, nboot)   # H18-12, advantage per N, per-seed slope over log2 N (8-64), per-cell means
def writeStage64(path, S, meta)
```

`demo_colony` runs the pilot behind `EXPLRL_COLONY_STAGE=stage64pilot` and the 16 boards behind `stage64` (re-checking the pilot's saved rows), with Stage 1's and the 32-agent rows as `prior`; both join the cached reruns.

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

## Stage 4 (T6e): guards that scale

Plan: [stage4.md](stage4.md). Requirements FR-A20 to FR-A24, AC-13.

**`colony_board` (new).**

```python
def squadOf(i, N, S)                             # slot i's squad: i mod (N // S)
class ColonyBoardEnv(ClueBoardEnv):
    def __init__(self, seed, nAgents, guardSlots=range(0), guardDeal=False, squads=None, failFlag=False, **kw)
        # sets its own attributes, then super().__init__ (reset deals the first 2N + 2 subtasks through _deal); raises
        # if N is not a multiple of S, or guardDeal without two guard slots and r = 2
    def _new(self, t)                            # picks the new subtask's squad (squadOfTask): the squad furthest below its
                                                 # target count (the 2N + 2 first subtasks round-robin), so a replacement joins
                                                 # the squad of the subtask it replaces; then the base _new
    def _deal(self)                              # per clue j: candidates = the subtask's squad (all slots without squads) minus
                                                 # slots already holding a clue of this subtask; guardDeal: one copy from the
                                                 # guard candidates, one from the rest; else r copies as the base deal; every draw
                                                 # uniform from self.rngDeal (the base deal's rule: fewest clues of the subtask)
    def apply(self, i, action, t)                # super().apply; with failFlag, a new 'wrong' submit appends (t, i, k, x) to
                                                 # self.failed; with squads, an open or share of another squad's subtask raises
                                                 # (parse and the squad view prevent it; the raise is a test guard)
def failures(board)                              # {(k, j, r): n}: for each (t, i, k, x) in board.failed and each clue j of k with
                                                 # i not in holders[j], every posted (shareLog) value (k, j, r) with x % p_j == r
                                                 # gets one; {} without failFlag
def squadView(board, i)                          # SquadView, a proxy: open and observe(i)['open'] restricted to i's squad;
                                                 # everything else (apply, tasks, shareLog, m, R, ...) delegates to board;
                                                 # the board itself when it has no squads
class InSquad:                                   # wraps a numpy member: id and extraNames forward; event(world, t) calls
    def event(self, world, t)                    # member.event(squadView(world, self.id), t)
def stage4Members(world, members)                # failFlag: colony rule agents get a flag-aware knownFor (their class becomes a
                                                 # cached subclass, FlagColonyAgent ...); squads: numpy members (RuleAgent,
                                                 # scripted liars included) wrapped in InSquad; Claude members unchanged
STAGE4_KEYS = ('guardDeal', 'failFlag', 'squads')
```

**`clue_runs`.** `clueSetup(cfg, seed)`: when any `STAGE4_KEYS` is in the world, the board is `ColonyBoardEnv(seed, N, guardSlots=range(nLiar, nLiar + guards), guardDeal=..., squads=..., failFlag=..., **board keys)`; otherwise `ClueBoardEnv` exactly as before. `runClue` and the numpy runner pass their members through `stage4Members`.

**`clue_colony`.**

```python
FAIL_RULE = "A value marked 'in a failed answer' agreed with an answer that was wrong; treat it as doubtful."
SQUAD_RULE = ("Your team works in squads of {S}: you see, open and share only your squad's subtasks (about {n} of the {M} on "
              "the board), and only your squad sees your posts.")
def colonyLine(board, tal, q=Q, fails=None)      # with fails, a value with n >= 1 failures reads '(2 agents, confirmed, in n failed answer(s))'
def knownColony(i, board, channel)               # with board.failFlag, the leading value per clue among those with no failure
                                                 # (own clues still win); unchanged otherwise
def colonyRules(env, text, i=None)               # as before, plus FAIL_RULE when env.failFlag and SQUAD_RULE when env.squads
def checkOptions(world, N=None, nLiar=0)         # guardDeal needs colony and guards > 0 (r == 2 and two guard slots: ColonyBoardEnv); failFlag needs colony; squads
                                                 # needs colony, N % S == 0, and nLiar and guards divisible by N // S
COLONY_OPTS += ('failFlag', 'squads')            # passed to TextClueEnv (guardDeal is a board key only)
```

**`clue_text`.** `TextClueEnv(..., failFlag=False, squads=None)`. `observe` and `parse` use `b = squadView(self.world, i)` when `squads` is set (`self.world` otherwise), so the open list, own clues, board line, known clues and valid targets cover the squad. The board line passes `fails=failures(self.world)` when `failFlag` is set. The rules include `FAIL_RULE` and `SQUAD_RULE` through `colonyRules`. All agents get the same sentences, so `slotRules` is unchanged.

**`colony_trace` and `clue_roll`.** `replay` builds the board through `clueSetup` (so `ColonyBoardEnv` comes for free) and passes its members through `stage4Members` (imported through `clue_runs`, so the module stays at 199 lines). `rollout` raises `ValueError` when a world has any `STAGE4_KEYS` (Part B does not use them).

**`colony_mech` (new).**

```python
def lieTiming(board, answers, nLiar, guards)     # guardHeldLies; contestRate/LagGuarded/Unguarded; usesPerLieGuarded/Unguarded;
                                                 # usesPerUser; openersPerLie (the scratchpad replay's measures, FR-A23)
def flagMeasures(board, answers, nLiar)          # flagsPerLie, flagsOnTrue, usesAfterFlag (NaN without failFlag)
def guardLoad(board, nLiar, guards)              # guardPostsPerTurn, guardUnposted (guard-held clues of opened subtasks no
                                                 # guard holding them posted)
def stage4Columns(cfg, rp)                       # colonyColumns(rp) + the three above + inTokPerCall (inputTokens / calls)
def runStage4(cfg, seed, client)                 # runClue's signature for runLLMCell: replay + stage4Columns, and the turn log
def runStage4Cell(cell)                          # for runWorkload (a named function, picklable)
def reusedRows4(client, prior, cells)            # the reference cells replayed through client(cfg) (cache-only: $0) with
                                                 # stage4Columns; asserts every column of the matching prior row unchanged
def replayCheck(cells, rows, cache)              # the regression gate: each cell with a saved row through traceCell and the
                                                 # cache-only client (a miss raises) -> dict(checked, mismatches)
```

**`colony4` (new).**

```python
ARMS4 = {**COLONY_ARMS,                          # COLONY_ARMS itself unchanged (COLONY_PLAN freezes it)
         'guardDeal': dict(colony=True, guards='quarter', guardDeal=True),
         'failFlag': dict(colony=True, guards='quarter', failFlag=True),
         'squads': dict(colony=True, guards='quarter', squads=8),
         'guardDealFlag': dict(colony=True, guards='quarter', guardDeal=True, failFlag=True),
         'squadsAll': dict(colony=True, guards='quarter', guardDeal=True, failFlag=True, squads=8)}
STAGE4_CELLS = {16: [('guardDeal', 'clean'), ('guardDeal', 'independent'), ('failFlag', 'clean'), ('failFlag', 'independent'),
                     ('squads', 'independent'), ('guardDealFlag', 'independent')],
                64: [('guardDeal', 'independent'), ('failFlag', 'independent'), ('squads', 'independent'), ('squadsAll', 'independent')]}
REUSED4 = {8: [('colonyGuards', 'independent')], 16: [('colonyGuards', 'clean'), ('colonyGuards', 'independent'),
           ('plain', 'clean'), ('plain', 'independent')], 64: [('colonyGuards', 'independent'), ('plain', 'independent')]}
def stage4Grid(seeds=COLONY_SEEDS)               # study colony4: colonyCell(..., arms=ARMS4) for STAGE4_CELLS (80 cells, 87,040 calls)
def stage4PilotGrid()                            # guardDeal|independent and squads|independent at 64, failFlag|independent at 16, seed 1890
def reusedCells4(seeds=COLONY_SEEDS)             # REUSED4 as cells (56): Stage 1's colony1 and the 64-agent run's colony64 studies
def stage4Estimate(cells, perCall)               # calls x cost per call, per call measured in the pilot by kind (squads, 16, 64)
def costRule4(projected, plan=None)              # run if projected <= plan['costRule']['run'] (60)
def boardKind(c)                                 # 'squads' for squad boards, else N (the pilot's cost per call by kind)
def ref8Tokens(rows1)                            # mean inputTokens / calls of Stage 1's colonyGuards|independent boards at N 8
def pilotCheck4(rows, ref8Tokens, plan=None)     # dict(ok, reasons, ...): the FR-A24 gates (a NaN value fails its gate); ref8Tokens = mean inputTokens / calls of Stage 1's
                                                 # colonyGuards|independent boards at N 8 (read from Stage 1's runs.csv)
STAGE4_PLAN                                      # frozen before the pilot: arms, cells, seeds, reuse, H18-13 to H18-15 (Holm),
                                                 # robustness rule, secondary list with expected directions, gates, costRule,
                                                 # cap 250, forecast file hash
```

**`colony4_report` (new).**

```python
def stage4Summaries(rows4, rowsReused, plan=STAGE4_PLAN, nboot=2000)
    # hyp: H18_13..15 (arm - colonyGuards at 64, honestPooled, one-sided exact sign-flip, Holm) and robust (the same on
    # welfareHonest; flag when the sign differs); did: per arm, mean over seeds of (arm - colonyGuards)@64 - (arm - colonyGuards)@16
    # with bootstrap interval and two-sided sign-flip p (arms run at both sizes only); adv: arm - plain at 16 and 64; squads8: squads@64 - colonyGuards@8; cleanCost: guardDeal and failFlag
    # clean - colonyGuards clean at 16; cells: per-cell means of the FR-A23 columns, honestPooled, welfareHonest
def writeStage4(path, S, meta)                   # report.md: tests, robustness, difference-in-differences, mechanisms, gates' values
```

The difference-in-differences is computed only for arms run at both sizes: `guardDeal`, `failFlag` and `squads`. `guardDealFlag` (16 only) and `squadsAll` (64 only) are reported as cell means and differences at their own size.

**`tools/colony_forecast.py stage4`.** Numpy cells: `plain`, `colonyGuards` and the `ARMS4` arms with independent liars, N 8, 16, 32, 64, 128, seeds 3000-3029, through `runColonyCell`. It writes `results/multiagent/colony/forecast4/` and `specs/multiagent/phase18/colony4_predictions.json`, which holds:
- the signs of H18-13 to H18-15 (an interval excluding 0);
- each arm's difference-in-differences from 16 to 64;
- each arm's advantage curve over 8-128.

`score4` scores the predictions against `stage4Summaries`.

**Regression gate.** A `demo_colony` cell (`llm`, run without `EXPLRL_LLM_LIVE`) replays every earlier live cell (pilot, Stage 1, 32 agents, Stage 3 and its reused cells, 64 agents) through `cacheOnlyClient`, so a miss raises and nothing is spent, and compares the rows with the saved `runs.csv`. The live-flag cached reruns follow.

**`demo_colony`.** `EXPLRL_COLONY_STAGE=stage4pilot` runs the pilot and prints `pilotCheck4`, the projection and `costRule4`. `stage4` runs `stage4Grid` only if both pass (re-checked from the pilot's saved rows), with `runStage4Cell`, then:
- `reusedRows4`: the 56 references replayed from the cache, $0, saved as `reused.csv`;
- `stage4Summaries`;
- `writeStage4`.

Both stages join the cached reruns.

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
| `colony64` | AC-12: grid, call count, pilot check and cost rule both ways, synthetic analysis (H18-12, trend over four sizes) |
| `colony3` | grid (40 cells) and pilot; estimate and `costRule3`; `complianceGate` both ways; `liarBehaviour` and `volunteering` on hand-made boards and logs; `stage3Summaries` on synthetic rows (exact p, Holm) |
| `colony_board` | AC-13: no options, the base deal exactly; `guardDeal` holder sets (one guard, one non-guard per clue; never both clues) over many subtasks; squad deals and squad make-up at N 16 and 64; `failures` on hand-made boards (only false values when submitters hold one clue; the counts); `squadView` hides other squads; `InSquad` members never act outside their squad (`stage4Members`, a 30-turn run); squads keep their target subtask counts; no Stage 4 key leaves members unchanged |
| `colony_mech` (Stage 4 end to end, for `clue_colony`, `clue_text`, `clue_runs`, `colony_trace`, `clue_roll`) | AC-13: no Stage 4 key, byte-identical (hash); the failure label, `knownColony`'s skip, `FAIL_RULE` and `SQUAD_RULE` only when set; `parse` rejects other squads' subtasks; `replay` equals `runClue` per option with the fake client; `rollout` refuses the keys |
| `colony_mech` | FR-A23 measures on hand-made boards; on the 64-agent run's cached cells (`llm`), guard-held lies 0.375 and unguarded uses per lie 1.49 on the guard board (the README's replay diagnosis); `reusedRows4` leaves earlier columns unchanged |
| `colony4`, `colony4_report` | grid (80 cells, 87,040 calls), pilot grid, reused cells (56); `pilotCheck4` and `costRule4` both ways; `stage4Summaries` on synthetic rows (exact p, Holm, the robustness flag, difference-in-differences, squads against 8) |
| `rl17_grid`, `rl17_train` | `world=()` hash unchanged; flag `train`: a tiny-model step with `world` set runs a colony board (AC-9) |
| `rl18_grid`, `rl18_report` | arms, seeds, configurations, the suite's cells; claims split between two simulated hosts; specialization index and null on synthetic logs (AC-9) |
| `demo_colony`, `demo_rl18` | quick sections end to end (`demo_rl18`: synthetic Part B rows and logs) |
