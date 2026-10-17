# Requirements: Phase 15, the mechanism behind liar damage at scale

Part of [README.md](README.md) (plan and decisions P15-1 to P15-5). Builds on Phase 14 (`scale_grid`, `scale_report`, `tools/scale_forecast.py`) and the clue board (`clueboard`, `clue_agents`, `clue_runs`, `clue_text`, `llm_client`).

Terms: as Phase 14 ([../phase14/requirements.md](../phase14/requirements.md)); in addition:

- **False clue:** a posted residue that differs from the board's true one (the `shareLog` false flag). Liars (agents `0 .. nLiar - 1` in both runners) post only false clues.
- **Known clues:** what `known(i, board, channel)` returns for agent i at the start of its turn (own clues win; otherwise the latest sighting); for the `first` variant, its own rule.
- **Contaminated submission:** an honest agent's submission on subtask k while its known clues for k include a false one.
- **False relay:** an honest agent's share of a false residue that a liar posted earlier for the same slot. Other false honest shares are **errors**.
- **Liar-held clue:** a clue whose holder is a liar (the board deals each clue to one agent, `r = 1`).
- **Trace:** per honest turn (an `Entry`): time, agent, open subtask, its known clues with their truth, whether one is false, the number of open subtasks showing a false post, and the number of open subtasks.
- **Round:** one unit of board time (each agent takes one turn per round).

## Functional requirements

### Part A: tracing
- **FR-A1** `traceRun(cfg, seed, client=None, variant=None)` runs one clue-board cell exactly as `runClueNumpy` (client None) or `runClue` (client given) does, with a tracer around each honest member that records the trace before the member acts; returns a `TraceRun` (rows, turn log, trace, board, nLiar, turns per agent). It changes no member state, random draw or prompt. `variant` applies to numpy honest agents only.
- **FR-A2** `cacheOnlyClient(cfg, cacheDir)`: the Phase 10 client over the response cache, with an offline stand-in for the API that raises on any call (a cache miss); no key, network, `anthropic` or `EXPLRL_LLM_LIVE` needed.
- **FR-A3** `traceCells(cells, cache=None, workers=1)` traces a list of cells (LLM cells with the cache-only client over `cache`, else the fake client; a numpy variant from `cfg.world['variant']`); the full run traces `traceGrid()` (Phase 14's Part B `baseline` cells: clean and N // 4 liars, N 8, 16, 32, seeds 900-904) with the cache-only client and `forecastCells()` (numpy: N 4, 8, 16, 32, 64, clean and N // 4 liars, seeds 2000-2019, 40 turns, as `tools/scale_forecast.py`).
- **FR-A4** `mechanics(trace, board, nLiar)`: the measures M1-M6 of the README for one run with liars.

### Part B: accounting
- **FR-B1** `lossAccount(clean, liar)`: for one board (same N and seed; each a `TraceRun`), the honest loss split into terms (a)-(h) of the README, each per honest agent-turn, summing exactly to welfareHonest clean minus with liars. Precedence when a subtask fits several value terms: (e) liar solved, then (c) false post, then (d) liar-held clue, then (f).
- **FR-B2** `traceSummaries(...)` per runner and N: mean and bootstrap CI of each measure and term; each one's change from N 8 to 32 with the Phase 14 forecast rule (`nChange` in `liar_grid`: unpaired bootstrap within N; sign + / - / 0); Haiku's change minus numpy's, with a bootstrap CI; secondary: N 16 and 32 pooled against N 8.

### Part C: numpy variants
- **FR-C1** `VariantAgent(RuleAgent)` with `variant` in (None, 'relay', 'first', 'repost') as in the README; `variant=None` is byte-identical to `RuleAgent`.
- **FR-C2** Each variant on `forecastCells()`; its honest-loss and pooled-share changes N 8 -> 32 with the forecast rule; agreement with Haiku's signs, labelled retrodiction.

### Part D: fresh forecast (optional)
- **FR-D1** `liarShareGrid()` (study `liarD`): `baseline`, N 8 and 32, `nLiar = N // 8`, seeds 900-904; the clean rows are Phase 14's `scaleB` baseline rows at the same N and seed. `liarForecast(variant)`: the honest-loss change N 8 -> 32 at that share (numpy, seeds 2000-2019) for the chosen variant and for the unchanged rule agent; `demo_liar` writes it to `specs/multiagent/phase15/liar_predictions.json`, which is committed before any Part D LLM cell runs; the Part D cells are rerun from cache (byte-identical, free) and scored with the forecast rule.
- **FR-D2** The variant for Part D: among those passing H15-4, the one whose predicted honest-loss change is closest to Haiku's observed one; if none passes, Part D is not run.

### Part E: report
- **FR-E1** New `demo_liar`: quick (fake client and numpy, short turns), full traces (cache-only replay, flag `llm`), accounting, variants, optional Part D (only with `EXPLRL_PHASE15_D=1`, `EXPLRL_LLM_LIVE=1` and the committed forecast); report and figure.
- **FR-E2** Results in this README (summary numbers copied to `specs/multiagent/phase15/trace_summary.json`), `REPORT.md` (a Phase 15 section), and the preprints where a claim changes (paper: the scaling subsection; paper2: the forecast's failure and its explanation).

## Analysis plan (frozen before the first full trace; exploratory)

`TRACE_PLAN`: per runner and N (8, 16, 32; numpy also 4 and 64): M1-M6 and the terms (a)-(h) with bootstrap CIs over seeds; each one's change N 8 -> 32 with the forecast rule, and Haiku's change minus numpy's. H15-1 (M1 `contaminated`: Haiku sign + or 0, numpy sign -); H15-2 (Haiku false relays per liar post above 0 at every N, change sign + or 0); H15-3 (Haiku's change in (a + c) over its change in the total above 0.5, with a bootstrap CI); H15-4 (each variant's honest-loss sign against Haiku's +); H15-5 (Part D, if run). The variants' definitions are part of the plan. Secondary: N 16 and 32 pooled against N 8.

## Quality requirements

- **NFR-1** Phase 5-14 reference outputs unchanged (cached reruns byte-identical); traced Haiku runs give rows equal to Phase 14's `runs.csv` and turn logs equal to the stored ones; traced numpy runs give the pooledShare, welfare and welfareHonest stored in `results/multiagent/forecast/scale_numpy.json`.
- **NFR-2** Offline tests need no network, key, `anthropic` or `torch`.
- **NFR-3** Parts A-C spend $0 (cache-only client); Part D about $3.20, only with approval; API under the $150 cap ($79.14 spent).
- **NFR-4** Seeds fixed; reruns byte-identical.
- **NFR-5** Each module under 200 lines; `clue_agents` (199 lines), `clue_runs`, `clueboard` and `llm_client` unchanged: new code in new modules.

## Acceptance criteria

- **AC-1** Regression: NFR-1; the full suite passes.
- **AC-2** Tracer: on hand-made boards and the fake client, the trace's known clues equal `known(...)` at each turn; a traced run's rows and logs equal the untraced run's (numpy and fake LLM; with and without liars); the cache-only client returns cached replies and raises on a miss.
- **AC-3** Measures and accounting on hand-made traces with known answers; the eight terms sum to the honest loss to 1e-12 on every traced pair; `nChange` equals `tools/scale_forecast.py`'s `change` on the same input.
- **AC-4** Replay: all 30 Haiku cells traced with the cache-only client (no miss); NFR-1's equalities hold.
- **AC-5** Variants: `variant=None` byte-identical to `RuleAgent` on the forecast cells; each variant's behaviour on a hand-made board.
- **AC-6** Every `TRACE_PLAN` item reported, labelled exploratory (variants: retrodiction); Part D only after its forecast is committed and approved.

## Out of scope

The `record` and `request` arms' traces; LLM liars; new team sizes with LLM agents (beyond Part D); changing the Phase 14 results.
