# Design: Phase 15 (high and low level)

Phase 15 is small, so one design document covers both levels.

## Components

| Module | New / changed | Contents |
|---|---|---|
| `nbs/liar_trace.ipynb` -> `explRL/liar_trace.py` | new | `Tracer` (wraps a member), `TraceRun`, `Entry`, `traceRun(cfg, seed, client=None, variant=None)`, `traceCells(cells, cache=None, workers=1)`, `cacheOnlyClient(cfg, cacheDir)`, `CacheMiss`, `VariantAgent(RuleAgent)`, `knownFirst` |
| `nbs/liar_grid.ipynb` -> `explRL/liar_grid.py` | new | `TRACE_PLAN`, `traceGrid()`, `forecastCells(variant=None, share=4, sizes, seeds)`, `liarShareGrid()`, `liarForecast(variant)`; the changes with team size: `nChange` (the Phase 14 forecast rule), `numpyChanges` (curves and changes of pooled share and honest loss from rows) |
| `nbs/liar_report.ipynb` -> `explRL/liar_report.py` | new | `mechanics(trace, board, nLiar)` (M1-M6), `lossAccount(clean, liar)`, `traceSummaries(haiku, numpy, variants)`, `writeTrace`, `figTrace` |
| `nbs/demo_liar.ipynb` | new | quick (fake client, numpy, short turns); full traces (cache-only replay, flag `llm`); accounting; variants; optional Part D |
| `nbs/demo_multiagent.ipynb` | changed | a Phase 15 section in `REPORT.md` |

`clue_agents` (199 lines), `clue_runs`, `clueboard` and `llm_client` stay unchanged. `traceRun` repeats the set-up lines of `runClue` and `runClueNumpy` (`clueSetup`, the liars and their random streams, the members, `runTurns`, `clueMetrics`, `llmStats`) instead of adding a hook to them; a test pins the copies to the same rows and logs.

## The tracer (`liar_trace`)

```python
Entry = namedtuple('Entry', 't i k knownK contam falseVisible nOpen')    # knownK: {j: (r, true?)} for the open subtask k
TraceRun = namedtuple('TraceRun', 'rows log trace board nLiar T')
class Tracer:                      # wraps one honest member
    # forwards attribute reads and writes (the `id` that runTurns assigns) to the member
    def event(self, world, t):     # world.advance(t), append an Entry, then the member's event
        ...
def traceRun(cfg, seed, client=None, variant=None) -> TraceRun
def traceCells(cells, cache=None, workers=1) -> {row key: TraceRun}   # rows as cellRow, logs keyed as runLLMCell's;
                                   # LLM cells: cacheOnlyClient(cache), else the fake client; variant from cfg.world['variant']
```

`known(...)` is pure (no state, no random draws), so recording it leaves the run unchanged. For a `first` variant agent, the tracer records that agent's own known clues (`knownFor`). Liars are not wrapped. Phase 15 traces only `baseline` cells, which have no checks; `traceRun` refuses cells with Phase 13-14 options other than defaults. The LLM observation text is not re-rendered or parsed: the turn log already holds it (`obs`) for reading.

**Cache-only client.** `cacheOnlyClient(cfg, cacheDir) = LLMClient(cfg.model, cfg.effort, cfg.maxTokens, ResponseCache(cacheDir), None, client=FakeClient(miss))`, where `miss` raises `CacheMiss`. `LLMClient.complete` looks in the cache before touching the client, so every hit replays exactly as the live run's cached rerun does, and a miss raises before anything is spent. Passing a client object means `anthropic` is never imported; no key and no `EXPLRL_LLM_LIVE` are needed. The cache is Phase 10's (`results/multiagent/llm/cache`, git-ignored, on this Mac).

## Measures (`liar_report.mechanics`)

From the trace and the board's logs (`shareLog`: time, agent, subtask, slot, residue, redundant, false; `submits`: time, agent, subtask, candidates, result; `solveLog`: time, agent, subtask, assisted; `tasks[k]`: value, holders, solvedBy):

| ID | Definition |
|---|---|
| M1 | `falseVisible`: per honest turn, open subtasks showing a false post / open subtasks, averaged; `contaminated`: honest submissions whose traced known clues for the subtask include a false residue / honest submissions |
| M2 | `wrongContam`, `wrongClean`: results `wrong` / submissions, for contaminated and uncontaminated honest submissions |
| M3 | `suppressed`: slots whose first post was a liar's and whose true residue no honest agent posted later / slots a liar posted first |
| M4 | `relayPerLie`: false relays / liar posts; `relayAny`: liar posts relayed at least once / liar posts; `honestErrors`: other false honest shares / honest shares |
| M5 | `liarHeld`: subtasks with a liar-held clue / subtasks that existed; `solvedLiarHeld`, `solvedOther`: their solve rates |
| M6 | `recoverRounds`: mean rounds from an honest wrong answer to the subtask's solve (solved subtasks only); `contamUnsolved`: subtasks with a contaminated submission never solved / subtasks with one |

## Accounting (`lossAccount`)

On one board, welfareHonest = (value of subtasks honest agents solved - 0.5 x their wrong answers) / (honest agents x turns), with N honest agents in the clean cell and N - N // 4 in the liar cell. Write `nC T` and `nL T` for the two denominators and `v_k` for subtask k's value. The board draws each new subtask from its own random streams in serial order (`rng` for the puzzle and value, `rngDeal` for the holder), so subtask k has the same value, puzzle and holder in both cells; only its birth and expiry differ (a subtask is replaced when solved or expired).

- (a) = 0.5 x the liar cell's contaminated wrong answers / `nL T`
- (b) = 0.5 x the liar cell's other wrong answers / `nL T` - 0.5 x the clean cell's wrong answers / `nC T`
- (c), (d), (e), (f) = sum of `v_k / nC T` over subtasks honest agents solved in the clean cell and no honest agent solved in the liar cell, assigned in this order: (e) a liar solved k in the liar cell; (c) k showed a false post in the liar cell; (d) k has a liar-held clue; (f) the rest (including subtasks the liar cell never reached)
- (g) = - sum of `v_k / nL T` over subtasks honest agents solved only in the liar cell
- (h) = sum of `v_k (1 / nC T - 1 / nL T)` over subtasks honest agents solved in both cells

The eight terms sum to welfareHonest clean minus with liars by construction; a test checks it on every traced pair.

## Variants (`VariantAgent`)

`VariantAgent(channel, rng, share, guess, variant=None)` subclasses `RuleAgent` and overrides `choose` and `_shareable` only when `variant` is set (`variant=None` defers to `RuleAgent` unchanged: byte-identical rows on the forecast cells). The override of `choose` is `RuleAgent.choose` with its `known` call replaced by `self.known(b)`.

- `relay`: `_shareable` first as `RuleAgent`; if nothing, a clue the agent knows from the board but does not hold, for a subtask a teammate has open, whose (slot, residue) it has not posted itself.
- `first`: `self.known(b)` is `known`'s loop with the earliest sighting winning (own clues still win).
- `repost`: in `_shareable`, the agent's own slot counts as already shared only when some post of it carries the agent's own residue.

## Grids and plan (`liar_grid`)

```python
TRACE_PLAN                                 # frozen before the first full trace (commit and coopHash in the README)
def traceGrid()                            # [c for c in scaleGrid() if baseline arm], clean and N // 4 liars: 30 cells, Phase 14's keys
def forecastCells(variant=None, share=4)   # numpy: N 4-64, clean and N // share liars, seeds 2000-2019, 40 turns (tools/scale_forecast.py's cells)
def liarShareGrid()                        # Part D: study 'liarD', baseline, N 8 and 32, nLiar = N // 8, seeds 900-904
def liarForecast(variant)                  # Part D forecast: forecastCells(variant, 8) and forecastCells(None, 8) at N 8 and 32 -> signs
```

## Summaries and report

`traceSummaries(haiku, numpy, variants)`: per runner and N, `_stat` (mean, bootstrap CI over seeds) of every measure, term, `loss` and the clean `pooledShare`; `change` (N 8 -> 32, `nChange`), `pooled` (secondary: N 16 and 32 pooled against N 8), `diff` (Haiku's change minus numpy's, bootstrap within each runner and N), `variants` (`numpyChanges` per variant), `hyp` (H15-1 to H15-4). The demo checks the exact sum of the eight terms on every pair before writing.


`results/multiagent/liar/{quick,full}/`: `trace_summary.json`, `accounting.csv`, `variants.json`, `report.md`, `liar.png` (per N: contaminated share, false relays per lie, and the accounting terms, Haiku and numpy side by side). All of `results/multiagent/` is git-ignored; the traces themselves stay in `full/traces/`. `trace_summary.json` and `variants.json` are copied to `specs/multiagent/phase15/` with the results. Optional Part D output: `results/multiagent/liarD/` (`runs.csv`, per-run turn logs in `turns/`, `score.json`).
