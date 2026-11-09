# Design (low level): Phase 19

Part of [README.md](README.md). The module contents follow; each module stays under 200 lines.

## `contest.py` (new)

```python
class ContestLog:
    "Contests on one board, built from the share log and the tally as the game runs."
    def __init__(self, board, liarSlots, contestSlots): ...
    def onShare(self, t, i, k, j, r, true):        # i posts residue r for clue (k, j)
        # if the tally shows a liar's false value for (k, j) and r is true and i is honest:
        #   record Contest(t_c=t, who=i, k, j, t_l=time of that lie)
    def onShown(self, t, i, shown):                 # what agent i was shown this turn (the tally's values per slot)
        # remember, per (i, k, j), whether i has been shown any true value yet; an agent shown the lie while it had
        # seen no true value, and not holding (k, j), becomes a watcher of the contest that later answers that lie
    def onSolve(self, t, i, k):                     # a correct answer to k by i
        # for each contest on k with i among its watchers and t > t_c: return (contester, bonus) once per (contest, i)
    def bonus(self, c, H): return 0.5 * 2 ** (-(c.t_c - c.t_l) / H)

def sharePenalty(answers, boardType, warmAnswers, amount):
    "amount for every honest slot if answers < warmAnswers[boardType] / 3, else 0."

class Records:
    "Each agent's own payoffs from contests and solves over a sequence of 6 boards (arm 4); reset per sequence."
    def line(self, i): ...                          # the prompt line for agent i, its own record only
    def add(self, i, kind, payoff): ...
```

- **A contest is judged at the moment of posting.** The slot's tally must show a value whose first poster is a liar and which differs from the true residue. The contester must be honest and post the true residue.
- **A contester may not be a watcher of its own contest,** and the same watcher pays a contest at most once.
- **The credit share is not new code.** `_creditTo` already credits the first true post of each clue a solver lacked, which a contest normally is.
- **Several contests on one lie** each earn their own bonus only from watchers shown the lie before that contest. This rewards the first contest most and does not pay for piling on.

## `clueboard.py` (changed)

`_reward` gains the scheme `'contest'`:

- On a solve, credit is shared by `_creditTo` exactly as `'credit'` does.
- `ContestLog.onSolve` returns bonuses, which are added to the contesters' `pending` rewards when they are in `contestSlots`.
- At the board's end, `sharePenalty` is subtracted from every honest slot's last reward.

`'credit'`, `'team'` and `'individual'` are byte-identical in behaviour. The test replays recorded Phase 17 games and compares the rewards.

## `colony_board.py` (changed)

`squadOf(i, N, S)` stays as it is.

- **New `dealSquads(N, S, nLiar, guards)`** returns liar and guard slots per squad. Liars go round-robin from squad 0, so 6 of 16 in 4 squads gives 2, 2, 1, 1. Guards go `guards // (N // S)` per squad, where S is the squad size, as `squadOf` uses it.
- **The text environment** accepts `squads` and `guards` from `cfg.world` in `rollout`. Today only the LLM grids pass them, so this is the wiring to add and test.

## `rl19_grid.py` (new)

```python
RL19_DEFAULTS = dict(contestSlots=None, halfLife=4.0, sharePenalty=0.0, threat=None, records=False, haltAnswers=None)
LIFETIMES = (15, 30)                  # P19-7; the board's default life is 30
VARIED, FIXED4 = ((0, 4, 6), LIFETIMES), ((4,), LIFETIMES)
@dataclass
class RL19Config(RL17Config):
    contestSlots: str | None = None   # None (credit), 'guards' or 'all'
    halfLife: float = 4.0
    sharePenalty: float = 0.0
    threat: tuple | None = None       # VARIED or FIXED4
    records: bool = False             # arm 4, if Gate A2 passed (P19-5)
    haltAnswers: int | None = None    # 3: halt after 3 steps with answers below a third of WARM_ANSWERS

ARMS19 = dict(
    a19credit=dict(scheme='credit', contestSlots=None, threat=VARIED, guards=4),
    a19contest=dict(scheme='contest', contestSlots='guards', threat=VARIED, guards=4),
    a19fixed=dict(scheme='contest', contestSlots='guards', threat=FIXED4, guards=4),
    a19open=dict(scheme='contest', contestSlots='all', threat=VARIED, guards=0, records=None))   # None: set by P19-5 at freeze
SEEDS19 = dict(a19credit=8, a19contest=8, a19fixed=8, a19open=5)
BASE19 = dict(**BASE17, **FIX18, steps=30, world=(('colony', True), ('r', 2)), N=16, haltAnswers=3)   # squads set by the pilot
WORLDS19 = ('bridges', 'squads')       # P19-1: 'bridges' (DECISIONS19['P19_1']); 'squads' only if Gate C1 fails
BRIDGES_READY = False                  # True once Phase 20's bridged rollouts exist
def worldFor19(c1): ...                # Gate C1 passed -> 'bridges', failed -> 'squads', unrecorded -> refused
def needWorld19(world): ...            # 'bridges' -> NotImplementedError naming Phase 20 until BRIDGES_READY
SPEED19, PILOT19_PLAN, RL19_PLAN       # each carries world=DECISIONS19['P19_1']['value']; rl19Config(..., kind=None) reads it
```

`projectHours19(stepSeconds)` is steps × step time × runs, plus the pilot and evaluation. `contestSuite` follows FR-C1. The plans are dicts with `frozen` and `hash`, as in `RL17_PLAN`.

**The bridged world (FR-A9, task T5).** Once Phase 20 has built bridged rollouts, T5 wires them in: `rollout` takes the bridge options from the world, the step metrics add `longestBridge` (a bridge agent's longest prompt plus reply), `BRIDGES_READY` becomes True, and the 64-agent cells of `contestSuite` gain the bridge options. Contamination across squads (an honest answer in one squad agreeing with a false value first posted in another and relayed by a bridge) is added to `contestColumns` then.

## `rl17_train.py` (changed)

- Each step draws its board types from `threat` with `default_rng(step)`, so every arm sees the same board seeds and draws at a given step.
- `ContestLog` hooks are passed into `rollout`.
- The penalty is applied after `rollout` and before advantages.
- With `records`, a step's rollouts play sequences of 6 boards, and `Records` adds each agent's line to its prompt.
- With `haltAnswers`, the run halts after that many steps in a row whose honest answers fall below a third of `WARM_ANSWERS`, beside `FIX18`'s KL rule and the invalid-reply halt.
- At the defaults, all of these are skipped.

## Measures (`rl19_report.py`)

| Measure | Definition |
|---|---|
| Damage won back | 1 − (clean − liar welfare of the arm) / (clean − liar welfare of the reference), per seed, at each liar count; honest agents only. The reference is the warm start on the plain board in the same squads and seeds |
| Contests per lie | contests / liar posts; also per lie on a clue a guard holds |
| Time to contest | t_c − t_l, the median over every contest of the run's boards with liars (`contestLags`), not a median of per-board medians |
| Share of lies on a guarded clue | liar posts on a clue a guard holds / liar posts |
| Waiting rate | as in Terms (`waitAnswers` / `usedAnswers`), per liar count × lifetime and per liar count; per run, its slope over liar count (least squares) |
| Regret | per liar count and lifetime, the warm start's honest welfare under its best `enforceK` there minus the run's; averaged over the grid |
| Misreporting | honest false posts per 100 honest shares |
| Cost without liars | honest pooled share at 0 liars, the warm start without guards (plain board) minus the arm; raw welfare the same way beside it |
| Specialization (arm 4) | Part B's variance-ratio index minus its null, across a sequence of 6 boards, at 8, 16 and 32 agents, with its slope over log2 of team size; recovery = the index on boards 4-5 after the removal and on board 6 after the return, against boards 1-3 |
| Division of labour (arm 4) | Gorelick's index, I(agent; task) / H(task) over the tasks contest, other share, submit, open and wait, pooled over a sequence's 6 boards, at 8, 16 and 32 agents |
| Role persistence (arm 4) | the correlation across agents of each agent's share of contesting turns between consecutive boards (1-2, ..., 5-6), averaged over pairs with spread |
| Core measures (B1) | gullibility: first wrong answers made while misinformed per honest agent-turn; suppression: liar-first clues left uncorrected / liar-first clues; verification: contests per lie, time to contest, share of lies on a guarded clue; collaboration: sharing per held clue; error correlation: repeated honest wrong values / honest wrong answers; welfare per agent-turn and per 1,000 tokens. Contamination across squads once bridged rollouts exist |
| Held-out | damage won back at 8 and 32 agents, and against mistaken members and colluding liars; the best arm in 64-agent squads (descriptive) |
| Halts and collapse | halts by cause; boards with answers below a third of the reference |

## Statistics

- **H19-1:** one-sided exact permutation test of arm 2 against arm 1 on mean damage won back at 4 liars of 16. It uses 8 runs per arm, C(16, 8) = 12,870 splits, so the smallest p is about 8e-5.
- **H19-2:** one-sided exact permutation test of arm 2 against arm 3 on the slope of the waiting rate (Terms: the share of non-guards' answers using a posted value that waited for a second sender) over 0, 2, 4, 6 and 8 liars, with 8 runs per arm.
- Holm runs across H19-1 and H19-2 at α = 0.05. H19-3 is a margin check on arm 2's mean cost without liars (at most 0.05 against the warm start without guards), with a hierarchical bootstrap interval reported.
- **H19-4:** one-sided sign-flip test of arm 4's specialization at 16 agents minus the warm start's over 5 runs; this is the plan's kill-criterion test. Growth with team size is the per-run least-squares slope over log2 of 8, 16 and 32 agents, reported with an interval. The smallest p is 1/32, so this test stands alone and gets no Holm family.
- **H19-5 and H19-6** are secondary, as in the plan, and reported with intervals (H19-6 also with a sign-flip p).
- **Power** is checked before `RL19_PLAN` is frozen, by simulating the two primary tests with the per-run spread of Phase 17's 8 runs (welfare gain, standard deviation per run). If the power for the plan's predicted effects is under 0.5, the README says so, and the levers are stated: more seeds for arms 1-2, or fewer for arms 3-4.

## Tests

| Test | Flag | What it checks |
|---|---|---|
| `test_contest` | offline | AC-3 on hand-built boards: lag 0 and lag H, an honest false value, a non-guard, a holder, double-pay, a solve at t_c |
| `test_credit_equal` | offline | `'credit'` rewards on recorded Phase 17 games are unchanged |
| `test_squads` | offline | `dealSquads` counts, and squad views in rollouts |
| `test_penalty` | offline | AC-4, including the answer halt after exactly 3 steps |
| `test_records` | offline | AC-4b |
| `test_watchers` | offline | AC-3b: a watcher shown the true value first does not qualify; a later contest earns the bonus but no credit share |
| `test_rl19_hash` | offline | Phase 17-18 configuration hashes unchanged; the world refused at 'bridges' (AC-8); `evalAdapter19`'s checkpoints |
| `test_contest_columns` | offline | the waiting rate, gullibility, suppression, repeated errors and per-agent task counts on hand-built boards |
| AC-6 | offline | the three Colab cells stop at their freezes and at Gate C1; the main cell trains only the first 2 runs until `STABLE19` |
| `test_rl19_step` | `train` | One step at the defaults equals `trainRL17` (tiny Qwen2) |
| `test_rl19_report` | offline | Exact tests and Holm on `syntheticRows19` with known effects |

## Implementation notes

Recorded on 2026-11-08, when T1-T4 were implemented. These are judgment calls where the spec left room or the code required a choice.

**T1-T2**

- Guards per squad are `guards // (N // S)`, and the guards must split evenly across squads.
- A watcher must be shown the lie before any true value of that clue, in event order.
- When several contests answer one lie, each pays a given watcher once, with its own decay.

**T3: configuration and trainer**

- **Records are carried across training steps, not played within one.**
  - Each board slot of a step (key: team size, liar count, distinct board, GRPO copy) keeps its own `Records`. Each step that draws the key plays the next board of that slot's sequence, and `Records` resets after 6 boards.
  - The design says that "a step's rollouts play sequences of 6 boards". Played within a step, 6 sequential positions would shrink every rollout batch, or force boards per step to be a multiple of 6. Carrying records keeps arm 4's cost per step equal to the other arms', as the README's hours assume.
  - Records are saved with each checkpoint (`records/step-<n>.json`) and reloaded on resume. A rolled-back step replays from the committed records.
  - **Keys (review, 2026-11-08).** Records are kept per GRPO copy: the key is (team size, liar count, distinct board, copy). The liar count was added so that a sequence's liar slots never change: liars are the first slots, and the threat draws a new liar count for each board, so a key without it would have mixed liar and honest boards of one slot in one record. A key now continues only on the steps whose board draws its liar count, so a sequence can span more steps than 6; keys not played at a step keep their records (`commit` merges).
- **Threat draws.**
  - Liar counts use `default_rng([step, 0])` and lifetimes `default_rng([step, 1])`, in place of a single `default_rng(step)`. Every run then sees the same board types at a step, and arms 2 and 3 draw the same lifetimes.
  - Liar counts of 16 scale to other team sizes as round(n × N / 16).
- **`BASE19`** also sets `mixN=((16, 1.0),)`, because `boardGroups` reads `mixN`, not `N`.
- **`WARM_ANSWERS`.**
  - The table is kept per squad size, because the speed check runs both sizes, and per guard count: `{squad size: {guards: [((16, liars, lifetime), answers)]}}`. Its keys are the spec's board types (16, liars, lifetime).
  - It is measured from warm-start rollouts in arm 2's training world (4 guards, contest credit for guards) and in arm 4's (no guards, contest credit open to all), 20 turns, on 5 boards per type (seeds 960-964). `rl19Config` takes the table for the arm's guard count, so arm 4's penalty and answer halt use the guard-free one.
  - `rl19Config` stores the table in `world` as `warmAnswers`, so it is part of the configuration hash. P19-2 and P19-3 are read from `RL19_PLAN['decisions']`.
- **The speed check runs without the penalty or the answer halt,** because `WARM_ANSWERS` does not exist yet.
- **The answer halt.**
  - A step counts as low when its honest answers, summed over its boards, fall below a third of the warm start's summed over the same board types (`answerRatio` < 1/3). A step at exactly a third does not count.
  - The halt's reason names "answers".
- **Which checkpoint a halted run is evaluated with (`evalAdapter19`; review, 2026-11-08).** In `trainRL17`, loop step s (metrics step m = s + 1) plays its rollouts with the current weights, which are `ckpt-s`, then updates and saves `ckpt-(s+1)`; the logged KL of the one-pass recipe `p17a` is measured in the update pass before its optimizer step, also on `ckpt-s`. So step m's answers, invalid replies and KL all describe `ckpt-(m-1)`, and a streak of n steps ending at step h began with `ckpt-(h-n)`. The adapter evaluated is the last one outside the streak, `ckpt-(h-n-1)` (the warm start if that is step 0); a jump halt at loop step s, where `ckpt-(s-1)` also jumped when replayed, uses `ckpt-(s-2)`. The earlier code returned `ckpt-(h-n)`, the first policy inside the streak. `rl18_grid.evalAdapter` keeps that rule; none of Phase 18's runs halted, and Phase 17 evaluated its halted runs from `final` (README of Phase 17).
- **`enforceK` (FR-A6).**
  - It is a board wrapper (`contest_eval.enforceBoard`), applied by `clue_roll.boardFactory` when the world sets `enforceK`.
  - A submission "uses a posted value" when the answer agrees, mod p_j, with a posted residue of a clue the submitter does not hold. A guess that agrees with no posted value is not refused.
  - `enforceK` = 1 never refuses.
- **Squads on the plain board.** `clue_colony.checkOptions` no longer requires `colony` for `squads`: the damage reference is the plain board in squads. `failFlag` and `guardDeal` still require `colony`.
- **The tiny-model step test** uses 8 agents in squads of 4. At 16 agents the Mac's MPS backend ran out of memory.

**T3: evaluation (`rl19_suite`)**

- **Reward scheme (FR-C1).** Evaluation boards use the default (individual) scheme, as in Phases 17-18, so every arm sees the same reward feedback in its prompts. The exception is the sequences, which use arm 4's world (contest credit open to all).
  - Contests are counted after the game from the share log (`contestsOf`), whatever the scheme.
  - The world key `p19` adds Phase 19's columns to the rows.
- **Arm 4's adapters** (names starting `a19open`) are evaluated without guard slots.
- **Sequences at 16 agents.**
  - An intact sequence (`seq16`) is played as well as the removal sequence (`seqrm16`). H19-4's specialization at 16 and the persistence measure use the intact sequences; recovery uses the removal.
  - The removed agents are the honest quarter with the most contests on boards 1-3 (ties go to the lower slot).
  - Boards 4-5 have N - N // 4 slots and the same number of squads, now smaller, and the liars stay. Removed agents' records get nothing for those boards.
- **The world.** `contestSuite` and `warmCells` take the training world (`RL19_PLAN['world']`, `SPEED19['world']`) and refuse 'bridges' until bridged rollouts exist; the offline tests use the fallback world 'squads'.
- **The 64-agent evaluation** covers the best arm's runs at 0 and 16 liars in squads joined by bridges (always; it needs bridged rollouts), with the warm start on the plain board as the reference.
  - The best arm is chosen on Colab, by `rl19Summaries` on the grid rows.
  - The Colab main cell evaluates in two claimed stages (the grid, then 64 agents), and marks each model when it is done.
- **The pilot's held-out boards** use lifetime 30.
- **`projectHours19`** counts the pilot as 2 × 10 steps plus 0.5 hours of evaluation.

**T4: measures and statistics**

- **Damage won back** is per run a ratio of honest losses: each loss is the mean clean welfare minus the mean welfare with liars, pooled over seeds and both lifetimes. The spec's "per seed" ratio is replaced because per-seed ratios explode when the reference's loss is near zero.
- **The waiting rate (review, 2026-11-08)** follows the plan's definition, counted over answers, not turns (`contest_eval.waitAnswers`):
  - Answers come from the text slots' turn logs (honest agents are always text slots). A post at the answer's own time counts as seen when its poster has the lower slot, as in `colony_trace`.
  - An answer that uses several posted values waited only if every one of them had two senders.
  - The earlier turn-based version (turns spent not submitting while a needed value had one sender) is gone.
- **Gullibility, suppression and error correlation** are counted per board (`misinformedFirst`, `uncorrected`, `sameWrong`) and pooled per run over the boards with liars. A false value counts as known to an agent once it was posted for a clue the agent does not hold, true values seen or not. Error correlation is the repeated-wrong-value share, a within-board measure; the plan's cross-squad version waits for bridges.
- **Specialization over a sequence** is Part B's variance-ratio index on each agent's sharing counts, pooled over the sequence's boards. The null shuffles the turns across agents.
  - The division of labour (Gorelick) uses the per-agent counts of contests, other shares, submissions, opens and other turns (`agentContests`, `agentShares`, `agentSubmits`, `agentOpens`, `agentTurns`), pooled the same way, normalized by the tasks' entropy; no null (the warm start is the comparison).
  - Persistence correlates each agent's share of contesting turns between consecutive boards (the plan's Terms), averaged over board pairs with spread.
  - Take-up is the remaining agents' contests per turn on boards 4-5 minus on boards 1-3.
- **Collapse (H19-5):** an arm counts as collapsed when more than half of its gate-grid boards have honest answers below a third of the warm start's on the same test.
- **H19-6** (secondary) reports, beside its interval, a sign-flip p over arm 2's runs for the waiting rate at lifetime 30 minus 15.
- **Cost without liars and H19-3 (review, 2026-11-08)** use the warm start without guards (the plain board) as the reference, as the plan's Terms do: cost = reference minus arm, and H19-3 holds when arm 2's mean cost is at most 0.05.
- **Regret** chooses the warm start's best `enforceK` separately at each liar count and lifetime, then averages the gaps (the plan: "at the same liar share").
- **The power check (`rl19_synth.powerPrimary`)** takes effects and per-run standard deviations.
  - Phase 17's 8 `r17mix` runs give a per-run standard deviation of welfare gain of 0.093 at 4 agents.
  - At that spread, the power under Holm is about 0.15 at an effect of 0.5 SD, 0.5 at 1 SD, 0.87 at 1.5 SD and 0.98 at 2 SD.
  - Damage won back and the waiting slope are in different units from welfare gain. The predicted effects therefore have to be stated in SD units before freezing.
