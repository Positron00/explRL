# Design (low level): Phase 21

Part of [README.md](README.md). The module contents follow; each module stays under 200 lines.

## `clue_colony.py` (changed)

```python
COLONY_OPTS = (..., 'squads', 'dropShare', 'slotLines')     # appended; absent keys change nothing

def colonyRules(env, text, i=None):
    if getattr(env, 'dropShare', False):                    # plain board only (checkOptions)
        assert SHARE_AGAIN in text, 'the plain sentence about sharing again moved'
        text = text.replace(' ' + SHARE_AGAIN, '', 1)       # "... or nowhere." then the paragraph break
    ...                                                     # colony / confirm, failFlag, squads: unchanged
    if i is None:
        return text
    ...                                                     # guard, deceiver, volunteer sentences: unchanged
    line = (getattr(env, 'slotLines', None) or {}).get(i)
    text = text + '\n\n' + line if line else text         # A2: before C1's final return
    from explRL.bridge_agents import bridgeRules            # Phase 20 (C1), as built: stays last
    return text + bridgeRules(env, i)

def checkOptions(world, N=None, nLiar=0):
    ...                                                     # earlier checks: unchanged
    if world.get('dropShare') and (world.get('colony') or world.get('confirm')):
        raise ValueError(...)                               # A2: before C1's final return
    return checkBridge(world, N, nLiar)                     # Phase 20 (C1), as built: stays last
```

- **After C1.** C1 (Phase 20, built 2026-11-10) ends `colonyRules` with `return text + bridgeRules(env, i)` and `checkOptions` with `return checkBridge(world, N, nLiar)`. A2's `slotLines` text is added before that final return, so `bridgeRules` stays last, and the `dropShare` check goes before `return checkBridge(...)`. `clue_colony` is at 150 lines.
- **`checkOptions`** raises if `dropShare` is set with `colony` or `confirm`.
- **`slotLines`** is stored in `cfg.world` as a tuple of `(slot, text)` pairs, so it serializes and hashes. `TextClueEnv` turns it into a dict.
- In `SHARE_AGAIN`'s paragraph the sentence follows "...; or nowhere." after one space. Removing `' ' + SHARE_AGAIN` leaves "...; or nowhere." followed by the paragraph break, which is what E4 calls the drop-only prompt.

## `clue_text.py` (changed, option passing only)

- **`TextClueEnv.__init__`** gains `dropShare=False` and `slotLines=None`.
- `self.slotRules` also turns true when `slotLines` is set.
- `checkOptions` receives both.

`clue_text` is at 196 lines after C1 (Phase 20), so about 3 lines leave it at 199. If it would reach 200, the new code moves elsewhere (`_rules` to `clue_fix`'s pattern, `fixRules`).

## `liar_trace.py` (changed, one guard)

`traceRun` refuses cells with Phase 13-14 options. The guard becomes `any(v for k, v in fixOptions(cfg.world).items() if k != 'dropShare')`, so drop-only cells are traced. Baseline cells trace exactly as before (Phase 15's `trace_summary.json` is unchanged; this is checked by test).

## `a2_seq.py` (new)

```python
HONEST, GUARDS, LIARS, BOARDS = 12, 4, 4, 6                 # per team of 16 (P21-1)

def seating(team, b):
    "[identity per slot 4..15] for board b: default_rng([team, b]).permutation(12); on boards 1-2 the guard identities first."
def guardIds(team):   return sorted(default_rng([team, 0]).choice(HONEST, GUARDS, replace=False))
def successIds(team): return sorted(default_rng([team, 99]).choice(guardIds(team), 2, replace=False))

class TargetedLiar(ClueLiar):
    "ClueLiar's cadence; lies on a clue a `hit` slot holds and no `avoid` slot holds, else on any clue no `avoid` slot holds."
    def __init__(self, channel, rng, hit=(), avoid=()): ...
    def choose(self, b, t): ...                              # candidates (k, j) over b.open; never a clue an avoid slot holds

def runBoard21(cfg, seed, client):
    "runClue, with TargetedLiars when cfg.world has 'targets' ({'hit': slots, 'avoid': slots}); + a2_cols.a2Columns."

def followed(board, nLiar, log):     # shown values parsed from each turn's `obs` text
    "[(t_c, contester, k, j, correctAfter, watchers)]: contestsOf plus, per contest, the correct honest answers to k after t_c"
    "by agents other than the contester, and ContestLog's watcher count replayed from the share log and the shown values."

def recordLines(arm, history, b, team):
    "((slot, text), ...) for board b of `team` in `arm` (P21-4); history: the finished boards 1..b-1 with their seatings."

def runSequences21(teams, arms, spec, workers=8):
    "Six waves; boards 1-2 once per team (identical cells in every arm); boards 3-6 per arm; resumable from runs.csv."
```

- **Seating.** Slots 0-3 are the liars. On boards 1-2, slots 4-7 take the guard identities in a seeded random order and slots 8-15 the other 8. On boards 3-6 all 12 are permuted. Seeds depend on the team and board only, never on the arm.
- **`targets` on boards 1-2:** `hit` = the slots of the two success guards, `avoid` = the slots of the two failure guards.
- **Watchers.** `followed` rebuilds ContestLog's watchers on a finished board by replaying the share log with each honest agent's shown values from the turn log. If that replay disagrees with a live `ContestLog` on a recorded board (test), the watcher count is dropped from the report, since it is secondary.
- **Waves.** Waves 1-2 run one cell per team, keyed without the arm, and copy its rows and record history into each arm; wave b ≥ 3 collects board b of every team and arm whose board b-1 has finished, and runs them through `runWorkload(..., run=runBoard21Cell)`. Rows are appended to `runs.csv` and record lines to `records.jsonl`, keyed by team, arm and board, so a resume rebuilds `history` from disk.

### Record texts (P21-4)

Board b ≥ 3, for an honest agent. `n_c` is a contest count and `n_a` a count of correct answers that followed:

| Arm | Line (appended after the role sentence) |
|---|---|
| none | `This is board b of 6 played by the same team.` |
| shared | `This is board b of 6 played by the same team. Team record on the earlier boards: board 1: teammates contested n_c false values, and teammates then answered those subtasks correctly n_a times; board 2: ...` |
| own | `This is board b of 6 played by the same team. Your record on the earlier boards: board 1: you contested n_c false values, and teammates then answered those subtasks correctly n_a times; board 2: ...` |

Boards 1-2 in every arm carry only the first sentence. The texts are frozen in `A2_PLAN`. The pilot shows them rendered, and P21-12 checks them.

## `a2_grid.py` (new)

```python
ARMS21 = ('none', 'shared', 'own')
TEAMS21, PILOT21, P2_SEEDS, P2_PILOT = list(range(2100, 2108)), 2190, list(range(900, 908)), 990
boardSeed = lambda team, b: 10 * team + b                   # 21001 .. 21076; pilot 21901 .. 21906

def boardCell21(team, b, arm, history):
    "Built as colonyCell('a2', ...) builds a cell: WORLD18 + colony; b <= 2: guards 4, targets, board line; b >= 3: volunteer, ClueLiar, arm's record."
def p2Grid(seeds=P2_SEEDS):
    "fixCell('scaleB', 'baseline', N, s, N // 4) and the same with world dropShare=True (study 'a2drop'), N in (8, 32)."
def pilotGrid21(): ...                                       # team 2190 'own' (6 boards); a2drop N 32 seed 990

A2_PLAN = dict(version=1, frozen=False, model=HAIKU, world=WORLD18, turns=40, memory='full', channel='blackboard',
               teams=TEAMS21, arms=ARMS21, boards=6, sharedBoards=(1, 2), seating='seating(team, b)', texts=..., p2=...,
               hypotheses=dict(H21_1=..., H21_2=..., H21_3=..., H21_4=...), effort='low', maxTokens=8000, holm=dict(p2=['H21_3_8', 'H21_3_32']), alpha=0.05,
               manipulation=dict(teams=6, of=8), pilotGate=dict(maxInvalid=0.05), costRule=dict(ceiling=50.0, rule='report and wait'),
               approved=dict(pilot=None, main=None), cap=250.0, capNote='per calendar month (the user, 2026-11-09)', forecasts=dict(file='specs/multiagent/phase21/a2_predictions.json', sha256=None), nboot=2000,
               exploratory=True)   # forecasts filled at the freeze (P21-8); cap as decided (P21-10)
```

- **`estimate21(cells)`** counts new calls. Boards 1-2 count once per team, and the original P2 cells at seeds 900-904 count zero (cached).
- **`costRule21(perCall)`** multiplies those calls by the pilot's measured cost per call, per board type (16-agent colony boards; plain boards at 8 and at 32), and reports the total beside the $50 ceiling for the user to approve (P21-10).
- **`pilotCheck21(rows)`** checks:
  - invalid replies;
  - both success guards contest at least once on boards 1-2, and at least one correct answer follows a success guard's contest (P21-12);
  - lies on failure-guard clues, which must be 0;
  - that the rendered record lines match `texts`.

## Measures (`a2_report.py`)

| Measure | Definition |
|---|---|
| Guarding | per identity and board: turns posting a residue of a clue it holds / its turns (P21-5) |
| Contrast | per team and arm: mean over boards 3-6 of (success pair's mean guarding − failure pair's) |
| Gate statistic | per team: contrast(own) − contrast(shared) |
| Contests, followed | per identity and board: contests; the correct answers that followed; watchers (secondary) |
| Manipulation | per team: both success guards have at least one contest on boards 1-2 followed by a correct answer; lies on failure-guard clues (must be 0) |
| Role persistence | per team and arm: the correlation of honest identities' shares of contesting turns between consecutive boards, averaged over the 5 pairs; also over boards 3-6 only. The rule of Phase 19's `rl19_spec.persistence` |
| Division of labour | Gorelick's index per team and arm on boards 3-6: `rl19_spec.dolIndex(rs, 4, positions=range(2, 6))`, from `contestColumns`' per-slot counts mapped to identities by `agents`; the arm's mean with a bootstrap interval over teams; descriptive (H21-4) |
| Volunteers, specialization | Stage 3's `volunteering` and `specIndex` minus its null, on boards 3-6 |
| Team outcomes | honest pooled share, contamination, contests per lie, time to contest, sharing per held clue, by arm and board |
| Core measures (B1) | from `contest_eval.contestColumns` per board, pooled per arm with `rl19_measures.ratio`: gullibility `misinformedFirst` / `honestTurns`; suppression `uncorrected` / `liarFirst`; contests per lie `contests` / `liarPosts`; time to contest, median of `rl19_measures.lags`; share of lies on a guarded clue `guardLies` / `liarPosts` (boards 1-2); error correlation `sameWrong` / `wrongHonest` |
| Welfare and tokens | welfare per agent-turn (`welfare`, `welfareHonest`); per 1,000 tokens, as `welfarePerKTok` in `rl19_measures.runMeasures` with the board's N in place of 16; tokens per solved task, (`inputTokens` + `outputTokens`) / `solved` |
| Not measured | cost without liars and damage won back: no A2 board is clean (P21-6 chose liar boards only; P1's boards always have liars), a recorded gap. Contamination across squads: no squads |
| P2: suppression | `suppressed` (Phase 15) and `suppressedHeld` per board; liar-first slots with and without an honest holder |
| P2: other | first wrong answers per honest agent-turn without the misinformed flag (E4's primary measure), with `misinformedFirst` beside it, `contaminated`, honest pooled share, sharing per held clue, and the core measures above |

`a2Summaries` reads the rows through an index in `rl19_spec`'s layout: level `<arm>|seq16`, `seqId` the team, `pos` = b − 1, and `agents` per slot (the liar's slot 0-3, or the honest identity + 4, so identities pass `rl19_spec`'s honest filter `a >= nLiar`). The shared boards 1-2 are copied into each arm's sequence.

## Statistics

- **H21-1 (Gate A2):** one-sided exact sign-flip of the 8 per-team gate statistics, greater than 0, α = 0.05. With 2^8 = 256 sign patterns, the smallest p is 1/256 ≈ 0.004. It is a single test, so it has no Holm family.
- **H21-2:** one-sided exact sign-flip of the own-record contrasts over 8 teams, reported with a bootstrap interval over teams. Secondary, uncorrected. It is reported beside the gate (P21-5): the shared record cannot tell success guards from failure guards, so its contrast is expected near 0 and the gate in effect tests whether the own-record contrast is above 0. The shared arm still controls for "any record makes guarding salient".
- **H21-3:** per size, drop-only minus original `suppressedHeld`, paired on seed. One-sided exact sign-flip, less than 0, over 8 seeds, with Holm across N 8 and 32 at α = 0.05. The pooled 16-pair estimate and Phase 15's `suppressed` are reported beside it.
- **H21-4:** estimates with bootstrap intervals over teams; the no-record and shared contrasts are reported against 0. The division of labour on boards 3-6 is reported per arm the same way, with no test.
- **Power, stated before the freeze.** Only the own-record arm can tell success guards from failure guards. If Haiku ignores the record, every contrast is about 0 and the test reads "not shown". With 8 pairs, p ≤ 0.05 typically needs 7 of the 8 gate statistics positive, or 6 when the negative ones are small. Stage 3 gives no spread for the contrast, so power is estimated from the pilot team's per-identity guarding variance by simulation (`syntheticRows21`), and the README reports it before the main run.
- **Claim rules.**
  - Gate A2 passes only if H21-1 passes and the manipulation check passed.
  - An H21-1 pass with an own-record contrast that is not above 0 (H21-2 fails) is reported as "records changed guarding but not as predicted", and the gate is still read as frozen.

## Cost

Unit costs are measured per board in `results/multiagent/colony/*/runs.csv` and `results/multiagent/scale/full/runs.csv` (Claude Haiku 5.5, low effort, 40 turns; mean of 8 boards, or of the 5 `baseline` boards for `scaleB`, seeds 900-904; that file also holds the `record` arm's rows, which are left out):

| Board | Source cell | Calls per board | $ per board |
|---|---|---|---|
| 16 agents, counting board, 4 guards, 4 liars (P1 boards 1-2) | Stage 1 `colonyGuards\|independent` | 480 | 0.198 |
| 16 agents, counting board, volunteer rule, 4 liars (P1 boards 3-6) | Stage 3 `colonyVolunteer\|independent` | 480 | 0.213 |
| 8 agents, plain board, one holder, 2 liars (P2) | Phase 14 `scaleB` `baseline\|liar` | 240 | 0.110 |
| 32 agents, plain board, one holder, 8 liars (P2) | Phase 14 `scaleB` `baseline\|liar` | 960 | 0.637 |
| Clean plain boards (option, P21-6) | `scaleB` `baseline`, 8 and 32 | 320, 1,280 | 0.080, 0.541 |

The projection:

| Item | Derivation | $ |
|---|---|---|
| P1 boards 1-2 | 8 teams × 2 boards × $0.198 (once per team, shared by the 3 arms) | 3.17 |
| P1 boards 3-6 | 3 arms × 8 teams × 4 boards × $0.213 | 20.45 |
| P2 drop-only | 8 seeds × ($0.110 + $0.637) | 5.98 |
| P2 originals 905-907 | 3 seeds × ($0.110 + $0.637); seeds 900-904 replay from the cache at $0 | 2.24 |
| Pilot | one team: 2 × $0.198 + 4 × $0.213 = $1.25; one drop-only board at 32 agents: $0.64 | 1.89 |
| Record lines | at most about 150 more input tokens per call × 480 calls × 64 record-arm boards × $0.10 per million (uncached input; an upper bound) | 0.46 |
| **Total** | | **34.19** |
| With a 15% margin | | about 39 |

- Without the shared boards 1-2, P1 would cost $6.34 more.
- With P2's clean boards (P21-6) it would cost $6.83 more: drop-only 8 × ($0.080 + $0.541) = $4.97, plus originals 905-907 3 × $0.621 = $1.86. Not taken, so cost without liars is a recorded gap; that option would cover P2 only, since P1's boards always have liars.
- Both fit the plan's $35-50. A2 freezes `maxTokens=8000` (P21-13), so E4's reply-limit contingency cannot force a rerun of seeds 900-904.

**Cap.** $250 of total spend per calendar month, shared with C1 (P21-10, Phase 20 P20-9). The ledger (`results/multiagent/llm/spend.jsonl`) holds $233.18 in 491,301 undated entries, all from before November 2026. Once `Budget` counts by month (NFR-7), they count as earlier months, and A2's $34-39 plus C1's $27-33 (with its clean boards, Phase 20 P20-14), about $61-72, fit November's cap. The user approves the pilot's estimate and the main grid's projection before each is spent, and may raise the cap then.

## Tests

| Test | Flag | What it checks |
|---|---|---|
| `test_dropshare` | offline | AC-2: the exact sentence and space removed; refused with `colony` and `confirm`; a `scaleB` request key unchanged without the option |
| `test_slotlines` | offline | AC-3 |
| `test_hashes21` | offline | NFR-1: Phase 11-19 configuration hashes and Stage 3 and `scaleB` request keys unchanged |
| `test_targeted` | offline | AC-4 on recorded Stage 1 boards and hand-built ones |
| `test_seating` | offline | AC-5 |
| `test_records21` | offline | AC-6, including `followed` against hand-counted contests and answers; watchers against a live `ContestLog` |
| `test_sequences21` | offline | AC-7 with the fake client: waves, shared boards, resume |
| `test_trace_drop` | offline | `traceRun` admits `dropShare`; Phase 15's baseline trace unchanged; `suppressedHeld` equals Phase 15's `suppressed` on a recorded trace where every liar-first slot has an honest holder (FR-C2) |
| `test_budget_month` | offline | NFR-7, in `nbs/llm_budget.ipynb` (shared with Phase 20): a month boundary, undated legacy entries, `spentAll()` |
| `test_a2_report` | offline | AC-9 on `syntheticRows21`, including `partial='stopped'` and `a2TeamEstimates` on pilot-sized rows |
| `test_p2grid` | offline | FR-B5: `p2Grid`'s originals at 900-904 replay from the cache at $0, byte-identical requests to Phase 14's |
| `test_grid21` | offline | FR-B7: `estimate21`'s counts, `costRule21` never returns `run`, `pilotCheck21` on hand-built rows |
| `test_board21` | offline | FR-A4: without `targets`, `runBoard21` equals `runClue`'s rows and log |
| `test_a2_measures` | offline | AC-10: `dolIndex` on boards 3-6 and the persistence rule on a hand-built team, through the `rl19_spec` layout |
| cached rerun | `llm` | Stage 3 and `scaleB` cells through the cache-only client, byte-identical ($0) |
