# Spec: Phase 11, a distributed-information task board (and the road to RL training)

Status: **implemented; pilot done, `CLUE_PLAN` frozen** (2026-10-12; commit `20a60e8`, hash `050a825d7bae`); the main live runs are next. Part of the multi-agent plan: [../README.md](../README.md). Builds on [Phase 10](../phase10/README.md) and the [follow-ups](../speedup/README.md); replaces their paused hard-board run (D1).

## Goal

Make communication load-bearing. On the Phase 10 board Claude Haiku 5.5 solved 89-98% of the puzzles it opened at any difficulty we tried, so the board measured duplicate work and could not measure division of hard labour; harder single puzzles only buy longer reasoning. In this phase **no agent holds enough information to solve a subtask alone**: each subtask's clues are dealt out to different agents, so a team solves it only if the right clues reach the right agent. That gives real failure rates without artificial difficulty and a genuine incentive problem: under individual reward, sharing a clue costs you a turn and lets a teammate score.

1. **The clue board** (Part A): subtasks fixed by modular clues ("x mod 3 = 2", ...), dealt to different agents; a **share** action; the four Phase 7 channels carrying clues; information-pooling metrics.
2. **Numpy check first** (Part B): rule-based agents at 1-64 agents confirm the board's dynamic range and fix its settings before any API spend.
3. **Live runs with Claude Haiku 5.5** (Part C, about $6-8): pilot, main grid (4 channels x N 2, 4, 8 x 5 seeds), a framing arm (scored on own result vs team total) and a false-clue liar; optional arms specified but off by default (model size at matched effort, 16 agents).
4. **Ready to train on** (Part D): individual, team and credit rewards, batched episodes, trajectory exports including chat format, and a scripted teacher policy for warm-starting.
5. **RL training** (Part E) is the next phase, not this one (decision K10).

**Main acceptance tests:** (a) the board's checker, dealing and scoring pass hand-checked cases; (b) the numpy sweep shows the dynamic range the rule requires, or the phase stops before any spend; (c) normal tests are offline (fake client); (d) the analysis plan is frozen before the main live runs; (e) cached reruns are byte-identical and free; (f) the training exports round-trip and the teacher policy solves boards when it holds all clues.

## How it maps to the role (multi-agent research, Anthropic)

| Role item | What this phase adds |
|---|---|
| Environments to train groups of Claudes to solve problems together | A task groups can solve and individuals cannot, with checkable rewards, training exports and a teacher policy (Part D); RL training next (Part E) |
| Harness configurations (communication architectures) | Channels carry information (clues), so blackboard, messages and coordinator become information-routing architectures |
| Incentives and mechanism design | Individual vs team vs credit reward when sharing helps others score; a framing arm; a liar posting false clues |
| Novel eval of how teams interact | Clues shared per clue held, share-to-use time, redundant shares, assisted solves, against a pooled-information upper bound |
| Bitter Lesson | Optional matched-effort arm: does a channel's benefit shrink with a stronger model when effort is matched? |

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the analysis plan, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions and rejected alternatives, risks |
| [design-low-level.md](design-low-level.md) | Clue generation and dealing, the board, channels, agents, text interface, runs, grids, costs, training packaging, demo |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |
| RUN.md | Written in the last task |

## What earlier phases give us

| Piece | Fact | Consequence |
|---|---|---|
| Phase 10 `TaskBoardEnv`, `TextBoardEnv`, `BoardBandit` | Subtasks that appear and expire, first correct answer scores, wrong answers cost a penalty, ledger in the Phase 6 format, claim channels | The clue board reuses this structure (and its scoring), adding dealing, sharing and knowledge |
| Phase 10 `LLMMember`, `runTurns`, `runLLM`, caching, budget | One API call per event through any text adaptor with `rules / observe / parse / post / explored / summary` | A new adaptor `TextClueEnv` plugs into the same member and run machinery |
| Follow-ups `runWorkload`, `LLM_WORKERS`, timing, team totals | 3x the live call rate, cap check with margins, per-run wall time, `teamWelfare` and `teamRate_k` | Live runs go through `runWorkload`; rows carry team totals |
| Phase 10 and follow-up results | Channels cut duplicate work on the easy board; numpy predicted the LLM ranking there (rho 0.75) but not in foraging; framing prompts did nothing in foraging; at matched effort Sonnet's harness benefit equals Haiku's | The questions in the analysis plan |
| Claude Haiku 5.5 | Combines small modular facts reliably (the Phase 10 puzzles used `%` and `^`) | The pilot checks the solve rate when all clues are known (K3) |

## Decisions

| ID | Question | Answer |
|----|----------|--------|
| K1 | Clue type (P11-1) | **Modular clues** (decided 2026-10-12, following the plan's recommendation): a hidden `x` in `[0, R)` and `m` clues "x mod p = r" for distinct small primes whose product is at least `R`, so all `m` clues determine `x` (Chinese remainder theorem) and `m - 1` leave several candidates. Exact, seedable, combinable mentally; checked by our code |
| K2 | Dealing | Each clue goes to `r` agents (redundancy), spread so that no agent holds all clues of a subtask whenever that is possible (`r x m <= N x (m - 1)`; otherwise some agents necessarily hold all, which the sweep records); with fewer agents, agents hold several; a solo agent holds all (the information-free baseline). Clues are dealt when a subtask appears |
| K3 | Settings | Fixed by the Part B numpy sweep with a frozen rule (requirements FR-B2), then checked by the live pilot: Haiku must solve at least 80% of subtasks for which it knows all clues, with under 5% invalid actions; otherwise the user decides before the main runs |
| K4 | Share action | `share`: post one clue you know (held, or seen through your channel: relaying is allowed) for an open subtask to the channel; costs the turn (as `open`); sharing is voluntary, as in Phase 10. A share of a clue that anyone already shared counts as redundant. The share carries the residue posted, so a scripted liar can post a false one (the board flags it) |
| K5 | Channels | `none`; `blackboard` (all shared clues per subtask, visible to all); `messages` (a share goes to 2 random teammates); `hierarchical` (a numpy coordinator routes each shared clue to every agent with that subtask open, and suggests the open subtask with the most pooled clues) |
| K6 | Live scope (P11-2) | **Main grid, framing arm and liar arm** (decided 2026-10-12): about 15 000 Haiku calls, $6-8. The matched-effort arm (Haiku and Sonnet at medium effort, about $6-8) and the 16-agent scale arm (about $2) are specified and off unless the user asks |
| K7 | Analysis (P11-3) | **Exploratory with a frozen analysis plan** (decided 2026-10-12, as Phase 10): `CLUE_PLAN` frozen and committed before the main live runs, its hash in every report; no new confirmatory test |
| K8 | Rewards | Experiments use individual reward (the incentive problem is the point); the training package offers individual, team (each solve and penalty shared equally) and **credit** (the solver keeps `1 - c` of the value; `c` is split equally among the agents whose true shares first supplied clues the solver did not hold; false shares earn nothing; default `c = 0.5`) |
| K9 | Seeds | Part B sweep 800-819; pilot 1100-1101; main 900-904; framing 910-912; liar 900-902 (its clean cells are the main grid's); matched effort 900-902; scale 920-922 |
| K10 | Part E compute (P11-4) | **A rented GPU** (decided 2026-10-12, following the recommendation) for the next phase's RL training; nothing is trained in this phase |
| K11 | Budget | Spent so far $40.60 of the $150 cap; this phase about $6-8 (up to about $16 with the optional arms); the follow-ups' scheduler and cap checks apply |

## Sweep results (T5, 2026-10-12)

The numpy sweep (22 400 runs, 242 s on 8 processes; `results/multiagent/clue/sweep/runs.csv`) ran rule agents over every setting. At N = 4 with `needed` sharing, every setting met both conditions of the frozen rule (FR-B3): the blackboard reached 0.39-0.58 of the pooled bound and no channel 0.00-0.06 (only guessing scores without clues). The rule picks the largest gap: **m = 2, r = 1, R = 30, guess = 0** (blackboard 0.57 of the bound vs 0.00; R = 60 ties and loses on the smaller-R tie-break). This is now `CLUE_SETTINGS`.

| N | none | blackboard | messages | hierarchical |
|---|---|---|---|---|
| 1 | 1.15 | 1.15 | 1.15 | 1.12 |
| 2 | 0.00 | 0.76 | 0.76 | 0.75 |
| 4 | 0.00 | 0.60 | 0.46 | 0.55 |
| 8 | 0.00 | 0.53 | 0.13 | 0.50 |
| 16 | 0.00 | 0.44 | 0.04 | 0.48 |
| 32 | 0.00 | 0.35 | 0.02 | 0.46 |
| 64 | 0.00 | 0.27 | 0.01 | 0.46 |

Welfare per agent-turn at the chosen settings (rule agents, seeds 800-819). Without a channel nothing is solved once the clues are split (N >= 2): the board does force sharing. Two messages per share collapse as the team grows (a clue rarely reaches whoever needs it). The blackboard declines slowly, because more agents spread over more subtasks. The coordinator, which routes clues to the agents working on that subtask, holds up best. Incentives (`sweepIncentives`, N = 4, blackboard): team welfare 0.60 with `needed` sharing vs 0.00 with `never`. Under individual reward, every rule agent shared at least once, so the sharer vs non-sharer comparison is empty (mean sharer reward 24.1 over the run).

## Pilot (T9, 2026-10-12) and the frozen plan

Live, Haiku, 540 calls, $0.13, 378 s (6 runs at once: 1.4 calls/s, 0 retries); `results/multiagent/clue/pilot/`. **AC-9 met**: with every clue held (N = 1) Haiku solved 30 of the 30 subtasks it opened, with no invalid actions. Measured token profile (uncached input, cache read, output per call): (369, 1548, 364), now `TOKEN_PROFILE[('claude-haiku-5-5', 'clue')]`; output is far below the provisional 901, so the main scope is now estimated at about $3.5 (main $2.6, framing $0.7, liar $0.2).

| channel | N | welfare | pooled share | shares per held clue | wrong | guesses |
|---|---|---|---|---|---|---|
| none | 1 | 0.97, 1.10 | 1.00, 0.89 | 0 | 0 | 0 |
| blackboard | 4 | 0.49, 0.56 | 0.40, 0.45 | 0.42, 0.40 | 4, 4 | 6, 5 |
| none | 4 | 0.15, 0.08 | 0.12, 0.06 | 0.93, 0.84 | 4, 12 | 12, 18 |

(seeds 1100, 1101). With the blackboard, every solve used a shared clue; Haiku reached about 0.4 of the pooled bound against the rule agents' 0.57. With no channel, Haiku still "shared" about 40 times per run (the shares go nowhere and cost a turn), and its few solves came from guessing among the 2-15 candidates left by one clue: these count as assisted under the requirements' definition (the solver did not hold all clues), so `assisted` reads as "solved without holding every clue" in the no-channel cells.

`CLUE_PLAN` was frozen and committed before any main-scope call: commit `20a60e8`, `clueHash()` = `050a825d7bae`.
