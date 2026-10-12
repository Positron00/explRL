# Requirements: faster live runs and follow-up experiments

Part of [README.md](README.md) (the accepted plan, decisions SQ1-SQ5). Builds on Phase 10 ([../phase10/](../phase10/README.md)).

Terms used below.

- **Workload**: a list of named grids run together by the demo (for example the Phase 10 main runs, or Part D).
- **Run**: one cell, one episode loop with its own world, channel and team (one `runLLMCell` or numpy call).
- **Chain**: the calls of one run that must happen one after another; its length is the floor of the run's wall time.
- **Event-driven protocol**: today's `runTurns` / `runTeam` loop: one event at a time, in world-time order, ties to the lower agent index.
- **Round protocol**: events whose start times fall in the same window `[t0, t0 + d)` are decided on one snapshot and applied at the window's end (decision SQ3); `d = 0` means one event per round, the event-driven protocol.
- **Squad**: a group of agents sharing a home range (an arc of the location ring); **home bias** `beta`: how strongly a squad member prefers its home range (0 = no preference, `inf` = never leaves).
- **Team total** (`teamWelfare`): the team's net harvest (foraging) or value solved minus penalties (board) over the run.
- **Frozen outputs**: the confirmatory results of Phases 8 and 9 (`results/multiagent/bench/full`, `safety/h3`) and the Phase 10 results recorded in its README; none of them may change.

## Functional requirements

### Part A: faster live runs (no result changes)

- **FR-A1** The number of worker processes for live LLM workloads shall be a setting (`LLM_WORKERS`, default 32 per decision SQ1), independent of the CPU count; fake-client and numpy workloads keep `min(8, cpu)`.
- **FR-A2** `orderCells(cells)` shall order runs longest first by expected duration: sequential calls (LLM agents x turns per agent x episodes, plus belief calls) times the expected seconds per call for the run's model and task (from the timing summary when one exists, else from `TOKEN_PROFILE` output tokens); numpy runs last; ties by row key.
- **FR-A3** `runWorkload(grids, spec, workers, logDir)` shall run all grids of a workload in one process pool, ordered by FR-A2, unless the workload check (FR-A4) fails, in which case it runs grid by grid in the given priority order and stops at the first grid refused by the cap, as today. It returns the rows (sorted by row key), the grids done, the runs refused and where it stopped.
- **FR-A4** `checkWorkload`: before a live workload starts, its total estimate plus a margin shall be checked against what is left of the cap. Margin = `P` x the largest run estimate + `P` x the largest call cost, with `P` the number of processes; the largest call cost assumes `maxTokens` output tokens. While the workload runs, each live call shall be refused when what is left is below `P` x the largest call cost (the floor); calls already in flight may use the floor, so the spend never passes the cap.
- **FR-A5** Every live or fake call shall append a timing record (row key, model, task, seconds, retries, cached) to a per-run timing file, and every run a record of its wall time (`kind='run'`: row key, seconds, calls); the workload merges them into `timing.jsonl` and summarises latency per model and task, calls per second, retry count and wall time per run in `metrics.json` (the follow-up report also shows the mean run wall time per cell level). Retries are counted from the SDK's retry log messages (`RetryCounter`, in `llm_client`). `runLLMCell` writes its client's records to the per-run file. Timing never enters `runs.csv` or `turns.jsonl`.
- **FR-A6** `bench_grid.runGrid(cells, workers, run, chunksize=4)` shall accept `chunksize`; with the default it behaves exactly as before.
- **FR-A7** Pricing, the token profile, cost functions and the budget shall move from `llm_client` to a new module `llm_budget` (to keep each module under 200 lines with FR-A4 and FR-A5), with `maxCallCost(model, task, maxTokens)` added.

### Part B: round protocol and squads (new protocol; exploratory)

- **FR-B1** `runRounds(members, world, d, turns=None, Ttot=None)` shall run a team in rounds: in each round, the members whose next events start in `[t0, t0 + d)` (with `t0` the earliest pending start) first *prepare* one after another in agent order (observe and render, against the state at `t0`), then *decide* (the API call for LLM members) concurrently, then *commit* one after another in (start time, index) order (apply, post, learn, log). With `d = 0` each round holds only the earliest pending event (ties to the lower index), so `runRounds` reproduces the event-driven loop. The budget is a turn count per member (`turns`, as `runTurns`) or a world-time limit (`Ttot`, as `runTeam`).
- **FR-B2** Every member type used in Part B shall support the three phases: `LLMMember`, `CommBandit` (and its subclasses), and the new `TerritoryBandit`. `LLMMember.event` shall remain equivalent to prepare, decide, commit in a row, so event-driven runs are unchanged.
- **FR-B3** `homeRanges(L, k)` shall split the location ring into `k` contiguous arcs of `L / k` locations; squad `s` holds agents `s x N / k` to `(s + 1) x N / k - 1`.
- **FR-B4** `TerritoryBandit(channel, home, beta, ...)` shall be a `CommBandit` whose choice score adds `beta` for home locations (with `beta = inf`, only home locations are chosen; with `beta = 0`, exactly `CommBandit`'s choices); unknown home locations are tried before unknown others.
- **FR-B5** For LLM agents, a squad member shall get its home range in the system prompt (one sentence, the names of its arc) and the observation shall list home locations first. With a finite `beta` the sentence asks it to prefer its range (it may go anywhere); with `beta = inf` it asks it to stay and work only there (it still reads reports from everywhere). The model's actual bias is measured (`homeShare`).
- **FR-B6** Rows shall record the protocol, window, squads and bias, and `homeShare` (the share of an agent's stays inside its home range, mean over agents).

### Part C: team totals over time (post hoc metrics)

- **FR-C1** Phase 10 rows (LLM and numpy) shall add `teamWelfare` and `teamRate_k`: team net harvest per world second in move period `k` (foraging) or per block of 10 turns (board), for every complete period or block in the run. On the task board the net value per ledger row comes from `TaskBoardEnv.netRows` (value of a first-correct solve, minus the penalty for a wrong answer).
- **FR-C2** The Phase 10 full outputs shall be regenerated from the response cache with the new columns, without any API call; every existing column shall equal the current file's value exactly.
- **FR-C3** `teamRateCell(cell)` shall rerun one Phase 8 main-grid cell or Phase 9 attack-grid cell with its original runner and add `teamRate_k`; the reruns go to new folders (`results/multiagent/bench/teamrate/`, `results/multiagent/safety/teamrate/`), and every existing column shall equal the saved CSV exactly.
- **FR-C4** Reports shall show per-agent and team welfare side by side and, for Phase 10, the marginal gain per added agent (team total at N minus at N/2, divided by N/2) and a figure `team_total.png` (cumulative team harvest over world time, one line per channel, panels by task and team size). `REPORT.md` shall show the team totals of Phases 8 and 10 and the Phase 8 cumulative team harvest over time from the reruns (figure `report/team.png`). The Phase 9 rerun rows are kept with their team columns for later use. All labelled post hoc.

### Part D: follow-up live runs

- **FR-D1** `FOLLOWUP_PLAN` (cells, seeds, metrics, contrasts, selection rules, models, settings, prices) shall be frozen and committed before any live call of Part B or D, with its hash in every report.
- **FR-D2** `hardPilotGrid()`: board solo at difficulty 10 and 12, `maxTokens` 8000 and 16 000, Haiku 5.5 effort low, seeds 640-642, 30 turns. Selection rule (frozen; `chooseHard`): among settings with solve rate (solved / opened) in 30-70% and under 5% of turns at `max_tokens`, the one closest to 50%, ties to the smaller `maxTokens`; if none qualifies (`chooseHard` returns `None`), the pilot section prints it, the user chooses, and the main section runs D1 only if a level qualified (on 2026-10-12 none did and the user paused D1).
- **FR-D3** `hardGrid(difficulty, maxTokens)`: board, `none` and `blackboard`, N = 1 and 4, seeds 643-647, 50 turns, Haiku effort low.
- **FR-D4** `effortGrid()`: board difficulty 8, `none` and `blackboard`, N = 1 and 4, seeds 500-502, 50 turns, effort medium, Haiku 5.5 and Sonnet 5.5, `maxTokens` 8000.
- **FR-D5** `roundsGrid(beta)` (B-LLM): text foraging, blackboard, N = 8, 50 turns, Haiku, seeds 500-502; arms: rounds (`d` = 5 s), rounds with 4 squads at `beta` chosen by the frozen rule (`chooseBeta`) "among `beta > 0`, the one with the highest mean welfare per agent-second at N = 8 in B-numpy" (`beta = 0` with squads equals the rounds arm); the event-driven arm is the Phase 10 main-grid cells on the same seeds (from the cache).
- **FR-D6** `roundsNumpyGrid()` (B-numpy): text-foraging world (5 s stays), blackboard, N 8, 16, 32, 64, fixed world time 600 s, seeds 700-709; arms: event-driven, rounds (`d` = 5 s), rounds with squads of 2 at `beta` in {0, 0.25, 0.5, 1, 2, inf}.
- **FR-D7** `nbs/demo_followup.ipynb` shall run: a quick section (every new path with the fake client and small numpy cells) in normal tests; B-numpy and the Phase 8-9 team-rate reruns with their column check (FR-C3) with `--flags slow`; the live sections (D1 pilot, then D1 main, D2 and B-LLM as one workload, priority in that order if the cap check fails) with `--flags llm` and `EXPLRL_LLM_LIVE=1`, through `runWorkload`; outputs under `results/multiagent/followup/{quick,numpy,pilot,full}/`.

## Analysis plan (`FOLLOWUP_PLAN`, frozen before live calls)

All results are exploratory.

| Item | Definition |
|---|---|
| D1 | Board difficulty and `maxTokens` by the FR-D2 rule; contrast: blackboard minus none at N = 4 (welfare per agent-turn and team total), paired on seed, with bootstrap CI; compared in sign and size with the same contrast at difficulty 8 (Phase 10 seeds 500-504) |
| D2 | Contrast: (Sonnet blackboard benefit minus Haiku blackboard benefit) at N = 4, effort medium, paired on seeds 500-502; next to the same contrast at effort low (Phase 10); also wrong answers per run and output tokens per call by model and effort |
| B-numpy | Per N: welfare per agent-second and team total for each arm minus the event-driven arm, paired on seed; `homeShare`, exploration (coverage), belief diversity |
| B-LLM | Rounds minus event-driven and squads minus rounds at N = 8: welfare, team total, exploration share, belief diversity, `homeShare`, wall time per run |
| C | Team totals and rates are descriptive; no contrast is added to the frozen Phase 8-10 analyses |

## Quality requirements

- **NFR-1 Frozen results:** no frozen output changes; Phase 5-9 baselines (`tools/phase9_baseline.sh`) are identical; the Phase 8-9 confirmatory folders are never written.
- **NFR-2 Byte identity:** with the cache present, any Phase 10 or follow-up mode rerun with any worker count, ordering and pool mode writes byte-identical `runs.csv` and `turns.jsonl`, and sends no request.
- **NFR-3 Determinism of rounds:** a round's result does not depend on thread timing (prepare and commit are sequential in a fixed order; only the API calls overlap).
- **NFR-4 Cost:** spend never passes the $150 cap (FR-A4); the expected new spend (Parts B and D) is under $30; every report states the cost of its runs and the total spend.
- **NFR-5 Offline by default and secrets:** as Phase 10 (normal tests need no network, package or key; the key only from the environment, the SDK profile or the git-ignored `.env.local`).
- **NFR-6 Size, style:** each module under 200 lines; nbdev notebooks with tests.

## Acceptance criteria

Normal tests (offline):

- **AC-1 Speed without change (AT-1, AT-2):** the quick workloads give byte-identical `runs.csv` and `turns.jsonl` for 1, 8 and 32 processes, ordered and unordered, pooled and grid by grid; the quick demo stays under 30 s.
- **AC-2 Regression (AT-3):** Phase 5-9 baselines identical; `runGrid` with default arguments unchanged; the full suite passes with and without `anthropic`.
- **AC-3 Cap (AT-4):** with the fake client and a tiny cap, a workload that does not fit runs grid by grid in priority order; refused runs are recorded; no new call starts once less than the floor is left; the ledger never passes the cap.
- **AC-4 Timing:** the quick demo writes `timing.jsonl` and its summary; retries counted from a simulated retry log message.
- **AC-5 Rounds:** with `d = 0`, `runRounds` gives the same ledger and turn log as the event-driven loop (numpy and fake-client LLM teams); with the fake client and an artificial call delay, a round of 8 calls takes about one delay, not eight; results are identical across repeated runs with different thread timing.
- **AC-6 Squads:** `homeRanges` covers the ring once; `TerritoryBandit` with `beta = 0` makes the same choices as `CommBandit` on the same seed; with `beta = inf` it never leaves home; the LLM prompt names the home range and the observation lists it first.
- **AC-7 Team metrics:** on a hand-made ledger, `teamRate_k` and `teamWelfare` match hand-computed values; the sum over complete periods equals the team total over those periods.

Checks on saved and live results:

- **AC-8 Regenerated outputs (FR-C2, FR-C3):** the Phase 10 regeneration sends no request and keeps every existing column; the Phase 8-9 reruns reproduce every existing column of the saved CSVs exactly.
- **AC-9 Byte identity after regeneration (AT-1):** the regenerated Phase 10 full mode, rerun at 1, 8 and 32 processes, is byte-identical to itself.
- **AC-10 Live (AT-5):** the first live workload (D1 pilot) records latency, calls per second and retries; `LLM_WORKERS` is then set from it; all live workloads stay within the cap; costs and wall times are recorded; findings are reported, labelled exploratory.

## Out of scope

- Changing or re-reporting any frozen result; re-running Phase 10 under the round protocol.
- Asynchronous or streaming API calls inside an event-driven run (they cannot shorten the chain without changing the protocol).
- Squads on the task board (the claim board already removes duplicate work), learned territories, more than 8 LLM agents.
