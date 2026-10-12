# Requirements: Phase 10, language-model agents (Claude API)

Terms used below.

- **LLM agent**: a team member whose action at each event is chosen by one Messages API request to a Claude model.
- **Turn**: one event of one LLM agent (one request, unless replayed from the cache).
- **Text foraging**: the Phase 8 benchmark world with named locations, observed and acted on through text.
- **Task board**: a world whose locations are subtasks (seeded puzzles with checkable answers) that appear and expire; harvest = solving a subtask first.
- **Report**: what an agent chooses to share: a location (or subtask) and a value (or a claimed answer).
- **Response cache**: the on-disk store of every live response, keyed by a hash of the full request; a cache hit costs nothing and returns exactly the stored response.
- **Cost**: dollars computed from the response's `usage` (input, cache write, cache read, output) and the price table in config. **Cap**: the most a session may spend, set by the user.
- **Invalid action**: a response that cannot be turned into a legal action (unknown name, schema failure, `max_tokens` stop, refusal); it is replaced by "stay" (foraging) or "wait" (task board) and counted.
- **Analysis plan (`ANALYSIS_PLAN`)**: the pre-specified metrics, cells, seeds and comparisons, committed before the main runs.

## Functional requirements

### API client (`explRL/llm_client.py`)
- **FR-1** `LLMClient(model, effort, maxTokens, cacheDir, budget, prices, client=None)` shall send one request per call (`complete(system, blocks, schema) -> LLMReply`) through the Anthropic SDK, with adaptive thinking (the model default), `output_config` holding the effort and the JSON-schema format, prompt-cache breakpoints on the system prompt and the last history block, no sampling parameters and no refusal fallback. It shall never read or log the API key itself (the SDK resolves credentials).
- **FR-2** Every request shall be keyed by `sha256` of its canonical JSON (model, system, messages, output config, max tokens). A key found in the cache returns the stored reply with `cached = True` at zero charge to the budget (the reply keeps the cost of the call that produced it, so rows do not depend on the cache); otherwise the live reply is stored before it is returned.
- **FR-3** `Budget(cap)` shall keep the session's spend; `LLMClient` shall refuse a live call when the budget is exhausted (`BudgetExceeded`), and the run's expected cost (below) shall be checked against what is left, so a run is refused before it starts if the estimate exceeds what is left. `estimateCost(model, task, agents, turns)` shall give that estimate from a per-model, per-task token profile (`TOKEN_PROFILE`, measured in the pilot).
- **FR-4** `LLMReply` shall hold the parsed JSON (or `None`), the stop reason, the refusal category if any, the usage, the cost and whether it came from the cache. A `FakeClient` with the same interface shall return scripted replies, so normal tests never touch the network.

### Text worlds and agents (`explRL/llm_env.py`, `explRL/taskboard.py`, `explRL/llm_agent.py`)
- **FR-5** `TextForagingEnv(world, names)` shall wrap a `TeamPatchWorld` (default `benchWorld()`), name its locations from a seeded word list, render an agent's observation as text (location, last reward, travel time to every location, channel contents) and map a parsed action back to `apply`; the ledger and every Phase 8 metric work unchanged. `TextBoardEnv(board)` shall give the task board the same text interface (rules, observation with the open puzzle and the channel contents, parsing, voluntary claims).
- **FR-6** `TaskBoardEnv(seed, nAgents, ...)` shall implement the world protocol for the task board: a schedule of subtasks (value, difficulty, appearance and expiry time), actions `open <task>`, `submit <answer>`, `wait`; the first correct answer to a subtask scores its value, later ones nothing; a wrong answer costs `penalty`; opening a subtask takes a turn; rewards are individual (default), team (each solve's value shared equally) or difference (equal to individual here). `makePuzzle(rng, difficulty)` shall return the subtask text, the answer range and a checker; answers are checked by evaluating the generated function, never model code.
- **FR-7** `TaskBoardEnv` shall offer the best assignment of agents to open subtasks from values and solve rates (social optimum per turn, an upper bound), first solves (discoveries), duplicate work (turns spent on subtasks another agent solved), and a ledger in the Phase 6 format, so welfare, discoveries and the liar loss carry over; IFD distance and recovery time apply to text foraging only. A claim board, a numpy lead and a numpy board agent (`board_agents.py`) shall provide the task board's channels and its numpy team.
- **FR-8** `LLMMember(client, env, channel, memory, framing, ...)` shall be a Phase 5 `Member`: at each event it renders the prompt (decision L4), calls the client, parses the reply with the task's `parseAction`, applies the action, posts its report to the channel (if any), records the turn (observation, response, action, reward, tokens, cost, cache hit) and keeps its history according to `memory` (`'full'`, `'last8'`, `'notes'`).
- **FR-9** `elicitBeliefs(member)` (text foraging only) shall make one extra request asking the agent for its estimate of each location's value, returning the per-agent estimates the Phase 8 belief metrics take.

### Runs (`explRL/llm_runs.py`)
- **FR-10** `LLMConfig` shall hold the task, channel, team size, turns per agent, equal-budget total, model, effort, `maxTokens`, memory, framing, liar count, persistence episodes and lessons, task-board difficulty and world settings; it round-trips through a plain dict.
- **FR-11** `runLLM(cfg, seed, client)` shall build the world, channel and team (scripted liar in slot 0 when asked), run it with the Phase 5 event queue until every agent has used its turns (`runTurns`), elicit beliefs, and return the turn log and one flat row per episode: welfare, honest welfare, Phase 8 metrics where they apply, invalid-action and refusal counts, tokens (input, cache write, cache read, output), cost (the cache hit rate goes to the mode's `metrics.json`, so rows do not depend on the cache), share of turns with a report, exploration share per agent (mean and spread of each agent's share of turns spent going to a location with no current report), the free-riding index, and belief diversity (foraging).
- **FR-12** `mainGrid`, `sonnetGrid`, `budgetGrid`, `framingGrid`, `persistGrid`, `memoryGrid`, `liarGrid` and `pilotGrid` shall return cells (design-low-level section 7); `runLLMCell` shall run one cell for `bench_grid.runGrid(cells, run=runLLMCell)` (`runAnyCell` dispatches LLM and numpy cells); `quickGrid` shall give every grid's quick cells and `estimateGrid` the expected calls and cost of any cells.
- **FR-13** `numpyGrid(task)` shall give the matching numpy cells (decision L12) and `runNumpyCell` (`explRL/llm_compare.py`) shall run one with the same turn-limited loop (`runNumpy`); `compareNumpy(llmRows, numpyRows)` shall return, per task, Spearman's rho over the 16 (channel, size) cells and a bootstrap CI over seeds.

### Report and demo
- **FR-14** `explRL/llm_report.py` and `explRL/llm_figures.py` shall summarise the rows (welfare vs team size per channel and task; harness benefit per model; welfare vs total tokens; numpy vs LLM scatter with rho; framing, persistence, memory and liar arms; invalid actions, cost and cache hit rate) and write `report.md` with the analysis-plan hash, git commit, models, prices used and total cost.
- **FR-15** `nbs/demo_llm.ipynb` shall run a quick demo with the fake client in normal tests, the pilot with `--flags llm_pilot`, and the main grids and arms with `--flags llm` (long cells with `--cell-timeout 0`), writing `runs.csv`, `turns.jsonl`, `metrics.json`, `report.md` and figures under `results/multiagent/llm/{quick,pilot,full}/`. Live modes run only when `EXPLRL_LLM_LIVE=1` is set and a cap is configured.

## Analysis plan (frozen in T7)

All Phase 10 results are exploratory; this fixes what is computed before any main run:

| Item | Definition |
|---|---|
| Main comparison | Team welfare per agent-turn vs team size, per channel and task (Haiku 5.5, seeds 500-504) |
| Harness benefit | Per (channel, size): welfare minus the `none` cell, paired on seed |
| Model-size contrast | Task board, sizes 1 and 4: harness benefit with Sonnet 5.5 minus with Haiku 5.5, paired on seeds 500-502; mean and bootstrap CI ("shrinks" if the CI lies below 0) |
| Numpy vs LLM | Spearman's rho over the 16 (channel, size) cells per task; 95% bootstrap CI resampling seeds |
| Tokens as compute | Team welfare vs total tokens per run; equal-budget arm: welfare per agent-turn vs team size at 200 agent-turns |
| Arms | Framing, persistence, memory, liar: differences from their control cells with bootstrap CIs; the liar arm's blackboard-minus-messages loss compared in sign with H3 |

## Quality requirements

- **NFR-1 Exactness:** every earlier result is unchanged (Phase 5 golden fixtures, paper-demo, Phase 6, Phase 8 and Phase 9 hashes, the Phase 8 and 9 frozen pre-registrations).
- **NFR-2 Offline by default:** normal tests and the quick demo run without the `anthropic` package, without network access and without credentials; `anthropic` is an optional extra (`pip install -e ".[llm]"`).
- **NFR-3 Cost control:** no live request beyond the cap; the cost of every run is in its row and in `metrics.json`; prices carry the date they were checked.
- **NFR-4 Reproducibility:** with the response cache present, rerunning any mode gives byte-identical CSV and JSONL output and costs nothing.
- **NFR-5 Secrets:** the API key comes only from the environment, the SDK's credential profile, or the git-ignored `.env.local` at the repo root (loaded into the environment by the live client only, never overriding a variable already set); it never appears in code, tracked config, logs, the cache or results.
- **NFR-6 Size, style:** each new module under 200 lines; nbdev notebooks with tests.

## Acceptance criteria

Normal tests (`nbdev-test --n-workers 0`, offline):

- **AC-1 Regression:** NFR-1 holds; the package imports and the full suite passes without `anthropic` installed.
- **AC-2 Client:** with a fake transport, a request is built with the model, effort, schema, cache breakpoint and `max_tokens`, and with no sampling parameters or fallback; identical requests hit the cache (zero cost, identical reply); the budget refuses a call past the cap and a run whose estimate exceeds what is left; cost from a hand-made usage matches the price table.
- **AC-3 Text foraging:** the rendered observation lists every location by name with its travel time; "go <name>" and "stay" map to the right `apply`; unknown names, schema failures, `max_tokens` stops and refusals become "stay" and are counted; a scripted team's ledger equals the same moves made directly on `TeamPatchWorld`.
- **AC-4 Task board:** puzzles from the same seed are identical; the checker accepts exactly the answers with `f(x) == y`; only the first correct answer scores; wrong answers pay the penalty; subtasks appear and expire on schedule; opening costs a turn.
- **AC-5 Members and channels:** a fake-client team posts reports to the blackboard, sends messages and receives the lead's suggestions as specified; memory settings render the history as specified; with full memory, prompts are append-only across turns (each turn's history blocks start with the previous turn's, and the system prompt never changes).
- **AC-6 Runs and grids:** cell counts per grid; the quick demo (fake client) runs in under 30 s and writes all artifacts; the CSV is byte-identical for 1 worker and for several (up to 8); `compareNumpy` on synthetic rows recovers a known rho.

Live and manual checks:

- **AC-7 Pilot (T7):** with `--flags llm_pilot`, the single-agent task board picks a difficulty with a Haiku 5.5 solve rate of 30-70% (not reachable: the user chose difficulty 8, solve rate 0.89, with `max_tokens` 8000; README, Pilot results); per-turn tokens, cache hit rate, invalid-action rate and cost are recorded; effort is fixed; prices are re-checked; `ANALYSIS_PLAN` is committed.
- **AC-8 Main runs (T9):** with `--flags llm`, every grid runs within the cap; cost and timing recorded; findings reported, not asserted.
- **AC-9 Rerun:** a second run of any mode is served fully from the cache (zero cost) and its outputs are byte-identical.

## Out of scope

- Training any model (plan part 4: the environments are packaged ready for RL; a fine-tuning demo needs a GPU and is a later option).
- LLM coordinators (the lead stays the numpy baseline), LLM liars (the liar is scripted), free-text messages between agents.
- Team sizes above 8 (the numpy model covers large teams), models other than Claude Haiku 5.5 and Claude Sonnet 5.5, providers other than the Claude API.
- Batch processing: turns depend on each other within an episode, so they cannot be submitted as one batch.
