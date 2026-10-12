# Plan: faster live runs and follow-up experiments (after Phase 10)

Status: **plan accepted by the user (2026-10-12); spec drafted**, not implemented. Part of the multi-agent plan: [../README.md](../README.md). Builds on [Phase 10](../phase10/README.md) (its frozen results are not changed; everything new here is exploratory and labelled so).

## Files in this spec

| File | What it covers |
|------|----------------|
| README.md (this file) | The accepted plan: goal, parts A-D, decisions SQ1-SQ5 |
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the follow-up analysis plan, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions, risks |
| [design-low-level.md](design-low-level.md) | Signatures, algorithms, grids and costs, demos and reports |
| [tasks.md](tasks.md) | Ordered tasks T1-T13 with "done when" checks |
| RUN.md | Written in the last task |

## Goal and parts

| Part | What | Changes results? | Live API spend |
|---|---|---|---|
| A | Make live runs faster: more processes, longest runs first, one pool for all grids, timing log | No: same requests, same cached replies, byte-identical outputs | none by itself |
| B | Synchronous rounds and squads with soft territories: faster episodes and a new harness | Yes: a new protocol, compared with the event-driven runs on the same seeds | about $2 |
| C | Team-total metrics over time, next to the per-agent ones | Adds columns; existing values unchanged | none |
| D | Two small follow-up runs: a hard board in the 30-70% solve band, and model size at matched effort | New exploratory cells | about $20-25 |

Target for A: the Phase-10-sized workload (about 48 000 calls) in about 1-2 h instead of 10.6 h. Spent so far: $33.50 of the $150 cap; B and D together are estimated under $30, leaving the cap far away.

## Why rescaling world time does not help

Every agent action is one event, and every LLM event is one API call. Scaling all world-time constants together (`tStay`, `Tmove`, travel times, run length) leaves the number of events, and so the number of calls and the cost, unchanged. Cutting calls (fewer turns, an easier board) changes what is measured. The numpy runs are already short (Phase 8 confirmatory grid: 280 s; Phase 9 exploratory grids: 570 s; full test suite: about 1 min); only the live LLM runs are slow, and their time is set by API latency and scheduling.

## Where the time went (Phase 10 main runs)

| Fact | Value | Consequence |
|---|---|---|
| Calls | 47 988 (45 809 live) in 38 136 s | about 1.3 calls/s overall |
| Throughput while 8 processes were busy | about 2.7 calls/s | about 3 s per call per process (board calls at difficulty 8 are longer: about 900 output tokens) |
| Longest sequential chain | 400 calls (8 agents x 50 turns on the board; persistence: 4 agents x 4 episodes x 25 turns) | about 35-45 min per such run: the floor for any schedule that keeps the event order |
| Processes | `min(8, cpu)` = 8 on this 16-core machine | tied to the CPU count, although the work is waiting on the network |
| Grid order | grids one after another (priority order, for the cap) | the small arm grids (6-24 runs) left most processes idle |
| Dispatch | `runGrid`: `Pool.map(chunksize=4)` in grid order | long runs often started late, leaving a long tail |

Wall time is roughly `max(longest chain x latency, total calls x latency / processes)`. With 3-6 s per call: 400 x 3-6 s = 20-40 min for the chain; 48 000 x 3-6 s / 32 = 1.3-2.5 h, or 0.6-1.3 h with 64 processes.

## Part A: result-preserving speedups

| ID | Change | Effect | Result impact |
|---|---|---|---|
| A1 | `LLM_WORKERS` setting for live runs, separate from the CPU count: 32 to start (decision SQ1), raised after the A5 probe | 4x on the large grids, up to 8x at 64, within rate limits | none: requests and replies unchanged |
| A2 | Longest-first ordering: `llm_sched.orderCells` sorts runs by their expected duration, the number of sequential calls (`(N - nLiar) x turns per agent x episodes`, plus belief calls) times the expected latency per call for the run's model and task (from the A4 timing log; until then, output tokens from `TOKEN_PROFILE`); numpy runs last; dispatch with `chunksize=1` | removes the tail where one long run starts late | none: rows are sorted by key after the run |
| A3 | One pool for all grids instead of one grid after another | keeps processes busy through the small arms | none. The cap is kept by A3a and A3b |
| A3a | Before a workload starts, its whole estimate (`estimateGrid`) is checked against what is left of the cap, with a margin (below); a workload that does not fit runs grid by grid in priority order instead, as today | priority order is kept exactly when the cap is close | none |
| A3b | Margin for runs in flight: per-run reservations (`LLMClient.reserve`) and the per-call check are not shared across processes, so with `P` processes up to `P` runs can start against the same remaining budget, and up to `P` calls can be in flight when the cap is reached. A3a's margin is `P x` (the largest run estimate) `+ P x` (the largest call cost), and the per-call check refuses a new call when less than `P x` (the largest call cost) is left (64 Sonnet calls at `maxTokens` 8000 cost under $6) | spend cannot pass the cap | none |
| A4 | Timing log: wall time, model, task and retries per call, to a separate `timing.jsonl` (not part of `runs.csv` or `turns.jsonl`); summary in `metrics.json` (latency per model and task, calls/s, 429 count) | sizes A1 and A2 with measured latencies | none: the compared outputs are untouched |
| A5 | Rate-limit probe: the first minutes of the next live workload (Part D) run at the chosen concurrency and record 429s and retry waits | picks the largest safe `LLM_WORKERS` | none: the probe calls are part of a workload that is wanted anyway |
| A6 | `bench_grid.runGrid(..., chunksize=4)` gains an optional `chunksize` argument (default unchanged) | needed by A2 | none: Phase 8-9 calls keep the default; their baselines are re-checked |

**Why 64 processes on 16 cores is safe (measured 2026-10-12).** The work is waiting, not computing: one 8-agent, 400-turn episode needs 0.1-0.2 s of CPU in total (measured with the fake client), against 20-40 min of API waiting live, so 64 processes keep the CPUs under 1% busy; the operating system wakes each process when its reply arrives. Memory: about 45 MB per process (measured peak), about 3 GB for 64, of 48 GB. Open files: each process holds one network connection and briefly one cache or ledger file (limit 1 048 576). Shared files are safe for concurrent writers: cache entries are written once through a hard link (first writer wins), the spend ledger is appended under a file lock, and each run writes its own turn-log file. A thread pool in one process would use less memory and is an alternative, but processes reuse `runGrid` unchanged.

**Rate limits are the main risk of A1.** At 64 processes and about 3 s per call the team sends about 20 requests/s: about 1 300 requests, about 3.2 M input tokens (about 90% of them cache reads, which may not count toward input limits on current models; check the rate-limit documentation) and about 0.8 M output tokens per minute. The SDK retries 429 and 5xx (`max_retries=6`), so too high a setting slows down rather than fails; A5 finds the knee.

### Acceptance tests (Part A)

- **AT-1:** with the response cache present, the full Phase 10 mode run with 1, 8 and 32 processes, ordered and unordered, in one pool and grid by grid, writes byte-identical `runs.csv` and `turns.jsonl` and sends no request. The reference is the current `results/multiagent/llm/full/` output, or, once Parts B and C have added their columns, the output regenerated then (task T5).
- **AT-2:** the quick demo gives the same `runs.csv` for every worker setting and ordering, in under 30 s.
- **AT-3:** Phase 5-9 baselines unchanged (`tools/phase9_baseline.sh` on a clean worktree); `runGrid` with its default arguments behaves as before.
- **AT-4:** the cap holds: with the fake client, a tiny cap and the single pool, a workload that does not fit falls back to priority order (A3a), refused runs are recorded, no new call starts once less than the A3b floor is left, and the recorded spend never passes the cap.
- **AT-5 (live):** the next live workload (Part D) reports wall time, calls per second and 429 count from the timing log.

## Part B: synchronous rounds and squads (new protocol; decision SQ3)

These shorten the sequential chain inside an episode, the floor Part A cannot go below, but they change what agents see, so their results are not comparable with the frozen Phase 10 results. Each is a new, labelled protocol compared with the event-driven runs on the same seeds.

**Where the speedup comes from.** Writing to the blackboard takes microseconds. What makes an episode sequential is that every API call (seconds) waits until the events before it in world time are done, because its observation includes their reports. A synchronisation window lets calls in the same window read one snapshot and run concurrently; the board updates are still applied one after another at the window's end, which costs nothing. Without a window, splitting agents into squads gains nothing, shared board or not.

### B1. Synchronous rounds

All agents whose next events start in the same window `[t, t + d)` act at once on a snapshot of the world and the channel taken at `t`; their actions, reports and world updates are applied at the end of the window in event order (start time, then agent index). With `d = 0` a round holds exactly one event, which is the event-driven protocol. On the task board every action takes one turn, so a round is one turn and the chain shrinks from `N x turns` to `turns` (8x for N = 8). In foraging, events have different lengths (5 s stays, travel 0.5-15 s), so `d` is a setting (default: the stay length, 5 s).

What changes: today, agents acting at the same time act in index order, and agent 1 sees agent 0's report from that same moment. In rounds nobody sees same-round reports, so collisions on the same subtask or patch become more likely. This is the standard simultaneous-move setting of multi-agent RL, a reasonable protocol in its own right, but a different one. Code: a `runRounds(members, world, d, turns=None, Ttot=None)` next to `runTurns`, with the round's calls made concurrently (a thread pool inside the run: the SDK client is thread-safe, the cache and ledger are already safe for concurrent writers, and `LLMClient`'s call counters become per-call results instead of shared counts).

### B2. Squads with soft territories and a shared blackboard (user questions, 2026-10-12)

**Wall time.** Squads need a window too. With the window between squads only (exact event order kept inside each squad) the chain is `(N / k) x turns` for `k` squads; with B1's window for all agents it is `turns`, squads or not. Squads are therefore a question of performance, not speed.

**Performance.** Territorial division of labour is a new harness worth testing. The Phase 10 results suggest why: in text foraging with 8 agents the blackboard *lowered* exploration (32% of turns vs 53% without a channel) and belief diversity (0.12 vs 0.17) and cost welfare (-0.34 per agent-turn): herding, as Phase 8's H2 found for numpy agents. A home range per squad forces coverage while the shared board keeps the information. The trade-off is flexibility: a squad bound to its range cannot exploit a rich patch elsewhere. On the task board, where the claim board already removes duplicate work (under 1% duplicate turns), territories would add little, so B2 is for foraging.

**Soft territories.** Each squad has a home range (an arc of the 64-location ring, `64 / k` locations); agents read reports from everywhere and may go anywhere, with a bias toward home. One parameter covers the range from today's agents (bias 0) to hard borders (infinite bias):

- numpy (`CommBandit`): add `beta` to the UCB score of home locations (equivalently, scale the others by `exp(-beta)` for the softmax view); about 10 lines; sweep `beta` in {0, 0.25, 0.5, 1, 2, inf};
- LLM: the prompt names the agent's home range and asks it to prefer it, and the observation lists home locations first; the bias is the model's own, measured as the share of turns at home.

### Tests (Part B)

| Step | Cells | Cost |
|---|---|---|
| B-numpy | foraging, blackboard, N 8, 16, 32, 64; arms: event-driven, rounds (B1), rounds with squads of 2 at `beta` in {0, 0.25, 0.5, 1, 2, inf}; 10 seeds (700-709), the Phase 10 world (5 s stays), fixed world time T = 600 s | none |
| B-LLM | foraging, blackboard, N = 8, 50 turns, Haiku; arms: event-driven (the existing main-grid cells, seeds 500-502, from the cache), rounds, rounds with 4 squads at the best `beta > 0` from B-numpy (the highest welfare per agent-second at N = 8; `beta = 0` is the rounds arm itself); seeds 500-502 | 2 x 3 x (400 + 8 belief) calls, about $1-2 |

Measures: team and per-agent welfare (Part C), exploration share (LLM) or coverage (numpy), belief diversity, share of turns at home, and wall time per run. **Acceptance:** `runRounds` with `d = 0` gives the same ledger and turn log as the event-driven loop; with the fake client, rounds run the calls of one round concurrently (wall time about `turns x latency`); `beta = 0` gives the same choices as `CommBandit`.

## Part C: team-total metrics over time (decision SQ4)

Per-agent welfare falls as teams grow whenever resources are limited: patches have a fixed intake, so more agents share the same food. That dip is not a failure; the question is whether the team's total rises toward what the world can give. Today the Phase 10 rows carry per-agent welfare and `soShare` (team net harvest over the social-optimum yield, the normalised total); the team total appears only in the tokens figure.

| Metric | Definition | Where |
|---|---|---|
| `teamWelfare` | team net harvest (foraging) or value solved minus penalties (board), in total | Phase 10 rows (LLM and numpy). Phase 8-9 rows already carry it as `welfare`, next to `perAgentSecond`; Phase 10's `welfare` is per agent-turn (the frozen plan's name), so reports label both explicitly |
| `teamRate_k` | team net harvest per world second in move period `k` (foraging, `k` = 0, 1, ...) or per block of 10 turns (board) | row columns |
| capacity share | `soShare` (exists): team total over the social-optimum yield for the same time | row |
| marginal gain | team total at N minus at N/2, per added agent | report |
| curve | cumulative team harvest vs world time, one line per channel, panels by N | new figure `team_total.png` |

Which view answers which question: at **fixed compute** (Phase 8's headline budget, Phase 10's equal-budget arm) per-agent welfare is the team total divided by a constant, so both rank the same; at **fixed turns per agent** (Phase 10's main grid) the team total and `soShare` show whether more agents still add food, and per-agent welfare shows how efficiently each is used. Reports show both side by side.

**How it is computed, without touching frozen results.**

- Phase 10: rows are recomputed by rerunning from the response cache (about 10 s, no API call). The new columns change `runs.csv`; existing columns must stay value-identical (checked), and the new files become the reference for AT-1 and Phase 10's AC-9 (recorded in Phase 10 `RUN.md`).
- Phases 8-9: totals per run already exist (`welfare`). The per-period rates and curves need the ledger, which the CSVs do not keep, so the Phase 8 main grid and the Phase 9 attack grid are rerun deterministically into new folders (`results/multiagent/bench/teamrate/`, `results/multiagent/safety/teamrate/`); every existing column must equal the saved CSVs exactly, which also re-confirms their determinism. The confirmatory outputs (`bench/full`, `safety/h3`) are not overwritten, and no confirmatory result is re-reported.
- All Part C metrics are post hoc (added after the frozen plans) and are labelled so.

## Part D: two small follow-up runs (user decision, 2026-10-12)

Both use Part A's speedups, and the D1 pilot serves as A5's rate-limit probe. One follow-up analysis plan (`FOLLOWUP_PLAN`: cells, seeds, metrics, contrasts, and the selection rules for the D1 level and the B-LLM bias) covers B-LLM and D; it is frozen and committed before any live call, as in Phase 10; results are exploratory.

### D1. Hard board: coordination when solving is hard

The Phase 10 board turned out easy (Haiku 5.5 solve rate 0.89 at difficulty 8), so it tested duplicate work, not division of hard labour. At a 30-70% solve rate a second agent on the same subtask can add value (another attempt) as well as waste it, so the claim board's benefit may change sign.

| Step | Cells | Calls | Cost (about) |
|---|---|---|---|
| D1-pilot | board solo, difficulty 10 and 12, Haiku effort low, `maxTokens` 8000 and 16000, seeds 640-642, 30 turns | 2 x 2 x 3 x 30 = 360 | $0.5 |
| D1-main | at the difficulty and `maxTokens` with a solve rate in 30-70% and under 5% `max_tokens` stops, closest to 50% (ties to the smaller `maxTokens`; the user's call if none qualifies): board, `none` and `blackboard`, N = 1 and 4, seeds 643-647, 50 turns | 2 x 5 x 5 x 50 = 2 500 | $2-3 |

Measures: welfare per agent-turn and team total, solve rate, duplicate turns, wrong answers, `max_tokens` stops; contrast: blackboard minus none at N = 4, compared with the same contrast at difficulty 8 (Phase 10).

### D2. Model size at matched effort

In Phase 10, Claude Sonnet 5.5 at `effort = low` gave far more wrong answers than Haiku 5.5 (5.7 vs 0.7 per solo run), so the size contrast was confounded by how much each model reasoned. D2 runs both models at `effort = medium` on the cells that carried the contrast.

| Cells | Calls | Cost (about) |
|---|---|---|
| board, difficulty 8, `none` and `blackboard`, N = 1 and 4, seeds 500-502, 50 turns, effort medium, Haiku 5.5 and Sonnet 5.5 | 2 models x 2 x 5 x 3 x 50 = 3 000 (1 500 each) | Sonnet $15-20 (output per call at medium effort is not yet measured; low effort gave about 800 tokens), Haiku about $1 |

Measures: welfare, wrong answers, solve rate, output tokens per call; contrast: (Sonnet blackboard benefit minus Haiku's) at N = 4, now at matched effort, next to the low-effort result. Seeds 500-502 reuse the Phase 10 worlds, so effort low vs medium is paired for both models.

## Order of work

Details and checks in [tasks.md](tasks.md):

1. Offline first: baselines and references (T1), team metrics (T2), the budget split and client hooks (T3), rounds and territories (T4).
2. One regeneration of the Phase 10 outputs from the cache, after every change to row shape (T5); Phase 8-9 team-rate reruns into new folders (T6).
3. Scheduling (T7), byte identity of the full mode at 1, 8 and 32 processes (T8), regression (T9).
4. Follow-up grids, reports, the quick demo and B-numpy; then `FOLLOWUP_PLAN` frozen and committed (T10, the gate).
5. Live: D1 pilot and rate-limit probe (T11); D1 main, D2 and B-LLM in one workload (T12).
6. Reports and docs, including `REPORT.md` with team totals (T13).

## Decisions

| ID | Question | Decision (user, 2026-10-12) |
|---|---|---|
| SQ1 | Concurrency for live runs | 32 processes to start; raise after the A5 probe |
| SQ2 | Adopt Part A | Yes: no result changes, verified by AT-1 to AT-4 |
| SQ3 | Part B | Not for re-running Phase 10; rounds and soft-territory squads as a new exploratory arm, numpy first |
| SQ4 | Part C | Yes: team-total metrics and the over-time curve for Phases 8-10, labelled post hoc, without overwriting frozen outputs |
| SQ5 | Part D | Yes: the hard-board run and the matched-effort size check, about $20-25 within the $150 cap |
