# High-level design: faster live runs and follow-up experiments

## Components

| Module | New / changed | Contents |
|---|---|---|
| `nbs/llm_budget.ipynb` -> `explRL/llm_budget.py` | new (split from `llm_client`) | `PRICES`, `TOKEN_PROFILE`, `costOf`, `estimateCost`, `maxCallCost`, `Budget`, `BudgetExceeded` |
| `nbs/llm_client.ipynb` -> `explRL/llm_client.py` | changed | `LLMClient` (now with a call floor for FR-A4, a timing hook for FR-A5 and a `tag`), `RetryCounter`, `LLMReply`, `ResponseCache`, `requestKey`, `loadEnvFile`; imports pricing and budget from `llm_budget` |
| `nbs/llm_sched.ipynb` -> `explRL/llm_sched.py` | new | `cellKey`, `seqCalls`, `orderCells`, `checkWorkload`, `runWorkload`, `mergeTiming`, `timingSummary` |
| `nbs/bench_grid.ipynb` -> `explRL/bench_grid.py` | changed | `runGrid(..., chunksize=4)` |
| `nbs/team_time.ipynb` -> `explRL/team_time.py` | new | `teamRates`, `teamColumns`, `marginalGain`, `teamRateCell`, `teamRateGrids` (Phase 8-9 reruns) |
| `nbs/taskboard.ipynb` -> `explRL/taskboard.py` | changed | `TaskBoardEnv.netRows`: net value per ledger row (for Part C) |
| `nbs/rounds.ipynb` -> `explRL/rounds.py` | new | `runRounds`, the three-phase adapters for numpy members (`prepare`, `decide`, `commit`) |
| `nbs/territory.ipynb` -> `explRL/territory.py` | new | `homeRanges`, `squadHomes`, `TerritoryBandit`, `homeShare` |
| `nbs/llm_agent.ipynb` -> `explRL/llm_agent.py` | changed | `LLMMember.prepare / decide / commit` (its `event` calls the three); home-range sentence in `system()` |
| `nbs/llm_env.ipynb` -> `explRL/llm_env.py` | changed | `TextForagingEnv.home`: home locations listed first in the observation |
| `nbs/llm_runs.ipynb` -> `explRL/llm_runs.py` | changed | `LLMConfig` gains `protocol`, `window`, `squads`, `beta`; `runLLM` picks `runTurns` or `runRounds`; `taskMetrics` adds Part C and `homeShare` columns; `makeClient` passes the workload's floor; `runLLMCell` sets the client's `tag` and writes the per-run timing file |
| `nbs/llm_compare.ipynb` -> `explRL/llm_compare.py` | changed | `runNumpy` adds Part C columns (and the round protocol for numpy cells) |
| `nbs/followup_grid.ipynb` -> `explRL/followup_grid.py` | new | `FW`, `BETAS`, `SEEDS`, `FOLLOWUP_PLAN`, `followupHash`, `hardPilotGrid`, `chooseHard`, `hardGrid`, `effortGrid`, `roundsNumpyGrid`, `chooseBeta`, `roundsGrid`, `followupQuick`, `runFollowupCell` |
| `nbs/followup_report.ipynb` -> `explRL/followup_report.py` | new | `hardTable`, `effortTable`, `roundsNumpyTable`, `roundsLLMTable`, `summaries`, `writeReport`, `figBars`, `figRounds`, `writeFigures` (`hard.png`, `effort.png`, `rounds.png`, and Phase 10's `team_total.png`) |
| `nbs/llm_report.ipynb`, `nbs/llm_figures.ipynb` | changed | team totals and marginal gain next to per-agent welfare; `figTeamTotal` (`team_total.png`) for Phase 10 |
| `nbs/demo_llm.ipynb` | changed | `run()` uses `runWorkload`; `LLM_WORKERS`; timing outputs |
| `nbs/demo_followup.ipynb` | new | quick (fake); B-numpy and the Phase 8-9 team-rate reruns with their check (`slow`); live D1 pilot, then D1 main (only if a level qualified), D2 and B-LLM (`llm`) |
| `nbs/demo_multiagent.ipynb` | changed | `REPORT.md` gains a team-totals section (figure `report/team.png`: Phase 8 totals by size and over time from the reruns, Phase 10 totals) and a follow-up section |
| `nbs/sidebar.yml` | changed | the new notebooks |

Import rule: `llm_budget` imports nothing from the package; `llm_client` imports `llm_budget`; `llm_sched` imports `bench_grid`, `llm_budget`, `llm_grid` (`estimateGrid`, `runAnyCell`, `withClient`), `llm_runs` (`LLMConfig`) (the client does not import it: `RetryCounter` lives in `llm_client`, which avoids an import cycle); `team_time` imports `team_refs`, `bench_metrics`, `bench_grid`, `harness_runs`, `safety_runs`, `safety_grid`; `rounds` imports `multi`, `harness`, `harness_agents`, `team_agents` (the numpy adapters); `territory` imports `harness_agents`; `llm_runs` and `llm_compare` also import `team_time`, `rounds` and `territory` (`llm_compare` also `bench_grid`, `bench_metrics` for the fixed-time rows); `llm_report` imports `team_time` (`marginalGain`); `followup_grid` imports `llm_grid` and `llm_budget`; `followup_report` imports `llm_report`, `llm_figures` and `matplotlib`. Only `llm_client` imports `anthropic` (unchanged). No module imports a demo.

## Data flow

```mermaid
flowchart LR
  G[grids] --> CW{checkWorkload<br/>estimate + margin vs cap}
  CW -->|fits| PO[one pool, orderCells longest first,<br/>LLM_WORKERS processes]
  CW -->|does not fit| SQ[grid by grid, priority order]
  PO --> RUN[runAnyCell / runFollowupCell]
  SQ --> RUN
  RUN --> P{protocol}
  P -->|events| RT[runTurns / runTeam]
  P -->|rounds| RR[runRounds:<br/>prepare in order, decide concurrently, commit in order]
  RT --> C[LLMClient: cache, budget floor, timing]
  RR --> C
  RUN --> ROW[row + Part C columns + turn log + timing]
  ROW --> REP[reports, team_total.png, REPORT.md (team.png)]
```

## Main decisions

**H1. Speed comes from scheduling, not from the simulation (Part A).** Processes wait on the network, so their number is set by rate limits, not cores (measured: 0.1-0.2 s CPU per 400-call run, 45 MB per process). Ordering longest first and one pool remove idle time; neither changes a request, so cached reruns stay byte-identical. Rejected: rescaling world time (same number of events and calls), streaming or async calls inside a run (the chain stays sequential).

**H2. Cap safety without shared reservations (FR-A4).** Processes do not share reservations, so the workload is checked up front with a margin for runs and calls in flight, and falls back to today's priority order when the cap is close. Rejected: a lock-held reservation server (more moving parts for a cap that is far away; $33.50 of $150 spent).

**H3. Rounds by three phases (Part B).** Splitting an event into prepare (serial, agent order), decide (concurrent) and commit (serial, event order) makes rounds deterministic whatever the thread timing, keeps every channel's semantics except the delay within a window (including the lead, whose assignment reads earlier assignments), and leaves the event-driven path unchanged (`event` = the three in a row). Threads, not processes, run a round's calls: the client is thread-safe, and the cache and ledger already handle concurrent writers.

**H4. Soft territories by one bias (Part B).** A single `beta` spans free movement (0) to hard borders (`inf`), so one sweep answers whether any home bias helps; for LLM agents the bias is in the prompt and measured (`homeShare`), not set.

**H5. Post hoc metrics without touching frozen outputs (Part C).** Phase 10 rows are recomputed from the cache (free, exact); Phases 8-9 are rerun deterministically into new folders and checked column by column against the saved CSVs, which also re-confirms their determinism. Nothing frozen is overwritten or re-reported.

**H6. Pilot-then-freeze with rules, not choices (Part D).** `FOLLOWUP_PLAN` freezes the selection rules (difficulty and `maxTokens` for D1, `beta` for B-LLM) before any live call, so the pilot's outcome cannot shape the analysis after the fact.

**H7. Split `llm_budget` from `llm_client`.** `llm_client` is at 197 lines; FR-A4 and FR-A5 add to it. Pricing and the budget are a separate concern (also used by `llm_sched` and the grids), so they move out; imports in tests and modules are updated, with no re-exports.

## Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Rate limits at 32-64 processes | 429s, retries, slower runs | SDK retries (`max_retries=6`); the D1 pilot is the probe; `LLM_WORKERS` set from measured retries |
| Thread-safety of `LLMClient` in rounds | Lost counter updates | Counters become per-call results (timing records); budget and cache are file-based and safe |
| Large `maxTokens` (16 000) without streaming | SDK refuses long non-streaming requests above its time limit | Kept below the SDK's limit for these models; if refused, the pilot drops that setting and records it |
| Hard board fails at the interface again (`max_tokens`) | No usable D1 level | Selection rule requires under 5% `max_tokens` stops; otherwise the user decides (FR-D2) |
| Sonnet medium effort costs more than estimated | D2 over $20 | Workload check against the cap (if the workload does not fit, it runs in priority order D1, D2, B-LLM and stops at the cap); D2 can be cut to `blackboard` only before the run |
| Phase 8-9 reruns differ from the saved CSVs | Would mean nondeterminism | Column-by-column check (AC-8); stop and investigate before using any rate |
| Rows gain columns (Part C, LLMConfig fields) | Phase 10 `runs.csv` changes | Planned: existing columns checked identical, the new file recorded as the AC-9 reference |
