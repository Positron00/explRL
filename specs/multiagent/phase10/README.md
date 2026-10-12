# Spec: Phase 10, language-model agents (Claude API)

Status: **pilot done, analysis plan frozen** (2026-10-12): tasks T1-T8 done (offline parts, then the live pilot, see Pilot results); main runs (T9) next. Part of the multi-agent plan: [../README.md](../README.md). Builds on Phases 5-9: [../phase9/README.md](../phase9/README.md).

## Goal

Repeat the key experiments with real language-model agents, on a small API budget, and ask whether what the numpy agents showed carries over.

1. **Two text tasks with the same structure:** *text foraging* (the Phase 8 benchmark world described in words, with named locations) and a *task board* (each "patch" is a seeded puzzle with a checkable answer; crowding = duplicate work, travel = switching cost, moving patches = expiring subtasks, danger = penalty for a wrong answer).
2. **The four Phase 7 channels, mapped one to one,** with Claude Haiku 5.5 agents: team sizes 1, 2, 4, 8, five seeds, about 50 turns per agent.
3. **Bitter Lesson test:** the same harness comparison on the task board with Claude Sonnet 5.5 (sizes 1 and 4, three seeds): does a channel's benefit shrink with a stronger model?
4. **Tokens as compute:** team welfare against total tokens, plus an equal-budget arm (the same total agent-turns split across team sizes).
5. **Numpy predicts LLM?** Spearman correlation between numpy and LLM team welfare over the 16 (channel, size) cells of each task, with a bootstrap interval over seeds.
6. **Prompt-only tests of Phases 8-9:** incentive framing (scored on own result, on the team's, or own plus discovery credit), persistent notes across episodes, memory settings as context management, and one scripted liar among the agents.
7. **Ready to train on:** both tasks behind the Phase 5 interface, with checkable rewards, individual / team / difference reward options and JSONL trajectory logs. No training is done (plan part 4).

Phase 10 adds the `anthropic` SDK as an optional extra; the core package and every normal test run without it and without network access.

**Main acceptance tests:** (a) normal tests use a scripted fake client and never call the API; (b) every live response is cached on disk, so a rerun is exact and free; (c) a run stops before it can exceed the spending cap, and its cost is recorded; (d) both tasks pass hand-checked examples and the Phase 5 world protocol; (e) the pilot fixes the task-board difficulty and the per-turn settings before the main runs, and the analysis plan is committed before them.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the analysis plan, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions and rejected alternatives, risks |
| [design-low-level.md](design-low-level.md) | Classes, signatures, prompt and action formats, the API client, cache and budget, grids, costs, demo layout |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks, including the user's spending-cap confirmation |
| RUN.md | Written in the last task, same layout as the other RUN files |

## What Phases 5-9 and the API give us (the facts the design depends on)

| Piece | Fact | Consequence for Phase 10 |
|---|---|---|
| Phase 5 `runTeam` / world protocol | Event queue; a world offers `reset`, `observe`, `apply`; members act one at a time | An LLM agent is a `Member` whose `act` is one API call; text worlds implement the same protocol, so the logs and the ledger carry over |
| Phase 8 `benchWorld`, metrics, `runGrid` | 64-location ring, 16 patches moving every 40 s; welfare, IFD distance, belief diversity; deterministic parallel runner with CSV output | Text foraging wraps `benchWorld`; metrics are reused; episodes run in parallel processes through `runGrid` |
| Phase 7 channels, Phase 9 agents | `Blackboard`, `MessageBus`, `Lead`; scripted `Liar` | Same channel objects behind the text; the lead stays the numpy baseline coordinator; the liar is scripted, not prompted |
| Phase 8-9 results | Blackboard best from 4 agents up; `messages` adds nothing; one liar costs 4-7% on the blackboard (H3) | The numpy cells to compare against exist; the LLM liar arm asks whether H3's direction holds |
| Models (Claude API, cached 2026-10-06) | Smallest current: **Claude Haiku 5.5** (`claude-haiku-5-5`, $0.10 / $0.50 per million input / output tokens for prompts up to 100K); mid-size: **Claude Sonnet 5.5** (`claude-sonnet-5-5`, $2 / $10). Both: adaptive thinking on by default (billed as output), `effort` low to max, **non-default sampling parameters (temperature) rejected with a 400**, no assistant prefill, forced tool choice rejected on Sonnet 5.5, 512-token minimum cacheable prefix, editing earlier turns invalidates replayed thinking. Haiku 5.5 has no server-side refusal fallback | Temperature 0 is not available: the response cache is what makes reruns exact; actions come back as structured JSON (`output_config.format`), not forced tool calls; each turn is a fresh single-message prompt (no replayed assistant turns), so memory settings cannot trip the history-editing check; prices are re-checked before any live run |

## Decisions

| ID | Question | Answer |
|----|----------|--------|
| L1 | Models (plan Q6) | **Claude Haiku 5.5** (`claude-haiku-5-5`) for every grid; **Claude Sonnet 5.5** (`claude-sonnet-5-5`) for the reduced Bitter Lesson grid and its pilot. Adaptive thinking on (the default), `effort = 'low'` for both (pilot: medium effort did not raise Haiku's solve rate and once ran to the token limit), the same per-turn `max_tokens` (8000, pilot) for both |
| L2 | Spending cap (plan Q6) | **Decided by the user (2026-10-11): $150.** Confirmed before any live run (the gate before T7 checks credentials); the estimate in design-low-level section 8 is about $50-70 for everything. A hard cap in config: a run is refused if its estimate exceeds what is left, and stopped when its recorded cost reaches the cap |
| L3 | Reproducibility | Sampling parameters cannot be set on these models, so **the on-disk response cache is the only source of exact reruns**: every request is keyed by a hash of its full parameters; a cached response is replayed at no cost. Seeds control the world, the puzzles and every scripted draw; live reruns are not expected to match |
| L4 | Turn format | Each turn is **one request**: the static rules and world description in the cached `system` prompt, then one user message whose content blocks are the agent's rendered history (append-only, one block per past turn, the cache breakpoint on the last) and the current observation. No assistant turns are replayed, so thinking blocks are never resent and the history-editing check cannot fire |
| L5 | Actions | **Structured output** with one fixed JSON schema per task (`output_config.format`): an action name, a target (location or subtask name), an optional report (a location and a value; on the task board, a subtask and a `working` or `solved` claim), and a short `notes` field the memory settings can use. Names are free strings checked in code (a fixed schema keeps the cached prefix stable); an unknown name, a `max_tokens` stop or a refusal becomes "stay" (or "wait") and is counted as an invalid action |
| L6 | Refusal fallbacks | **Off** (confirmed by the user, 2026-10-11), deliberately: a server-side fallback would answer with another model, which confounds the model-size comparison. Refusals are rare in these tasks; each is recorded (`stop_details`) and treated as an invalid action |
| L7 | Text foraging | `benchWorld(tStay=5)` (Phase 8, with 5 s stays: a deviation decided by the user after the pilot, 2026-10-12, applied to the numpy comparison too) with its 64 locations renamed from a seeded word list; each turn shows the agent its location, last reward, the travel time to every location and the channel contents; actions "stay" or "go <name>". About 50 turns per agent (events, as in Phase 5) |
| L8 | Task board (plan Q7) | Subtasks are **seeded "find x" puzzles**: a short generated integer function `f` and a target `y`; the answer is an `x` in a stated range with `f(x) == y`, checked by evaluating `f` (our generated code, never model code). The board holds more subtasks than agents; subtasks appear and expire on a schedule; only the first correct answer scores its value; opening a subtask costs a turn (switching cost); a wrong answer costs a penalty. Difficulty (function depth, range) was to be set in the pilot so Claude Haiku 5.5 alone solves 30-70%; the pilot found no such level (see Pilot results), and the user chose the harder board with a larger `max_tokens`: **difficulty 8** (9 operations, answers below 12 800), solve rate 0.89 |
| L9 | Channels | `none`; `blackboard` (reports the agents choose to post, shown per location or subtask with their age, faded as in Phase 7); `messages` (an agent's report goes to 2 random teammates, at most once per period); `hierarchical` (a numpy coordinator, the Phase 7 `Lead` for foraging and a greedy `BoardLead` for the task board, shows each agent a suggested target; the agent is free to follow it). Reporting is voluntary, so whether agents share is itself measured |
| L10 | Memory (context management) | Default **full history** (append-only, cache-friendly); exploratory settings: last 8 turns, notes only (the agent's own running `notes` field instead of history) |
| L11 | Budgets | Main grids: **50 turns per agent** (the fixed-world-time analogue). Equal-budget arm (the plan's "equal token budgets"): 200 agent-turns per team, split across team sizes (200, 100, 50, 25 turns), with tokens per turn capped by `max_tokens`, so total tokens are roughly equal; text foraging, `none` and `blackboard`, 3 seeds. Actual team tokens are recorded per run and plotted |
| L12 | Numpy comparison | For text foraging, the Phase 8 `CommBandit` / `LeadFollower` teams on the same worlds, sizes and turn budgets; for the task board, numpy bandits on a simulated board whose solve probabilities are the pilot's measured solve rates. Numpy cells run with the same turn-limited loop (`runNumpy`). Spearman correlation over the 16 (channel, size) cells per task, bootstrap CI over seeds |
| L13 | Analysis plan | Fixed and committed before the main runs (`ANALYSIS_PLAN` in code, its hash in every report). Phase 10 has no new confirmatory test (the plan's confirmatory family ended with H3); its results are exploratory but pre-specified: metrics, cells, seeds, the Spearman comparison and the model-size contrast |
| L14 | Belief diversity | Text foraging only (on the task board every subtask's value is shown, so there is nothing to estimate): elicited once per agent at the end of each run (one extra call: "your estimate of each location's value"), so Phase 8's diversity and herding metrics carry over at small cost. IFD distance and recovery time also apply to text foraging only; welfare, discoveries and liar robustness apply to both tasks |
| L15 | Liar arm | One **scripted** liar (the Phase 9 rule; on the task board it posts false `solved` claims on open subtasks and `working` claims it does not follow) among 3 LLM agents, blackboard and messages, both tasks, 3 seeds: does one liar cost the LLM team more on the blackboard, as H3 found for numpy agents? |
| L16 | Framing and persistence | Text foraging, blackboard, 4 agents, 3 seeds. Framing: three prompt variants of the scoring sentence (prompt only; rewards stay individual); measured by welfare, exploration share per agent, report share and the free-riding index (with Phase 9's caveat that the index does not flag free-riders as defined). Persistence: 4 episodes of 25 turns, episode `e` on world seed `10 000 + 100 seed + e` (as in Phase 8 study B); agents keep or do not keep a `lessons` note: an agent's last `notes` of an episode, shown in its system prompt in the next (no extra call) |
| L17 | Execution | Episodes run in parallel processes through Phase 8's `runGrid` (synchronous client per process, `min(8, cpu)` processes); the SDK retries 429 and 5xx; concurrency is a config value to respect the organisation's rate limits |
| L18 | Training-ready packaging | `TextForagingEnv` and `TaskBoardEnv` implement the Phase 5 world protocol with text observations and a `parseAction`; individual / team / difference rewards (foraging: the Phase 6 schemes; task board: team = each solve's value shared equally, difference = individual, since only the first correct answer scores); all experiments use individual reward; JSONL logs of every turn (observation text, response text, parsed action, reward, tokens, cache hit) |
| L19 | Seeds | LLM main grids 500-504; Sonnet grid 500-502 (the same worlds as the Haiku cells it is compared with); arms 600-699; pilot 1000-1099 |
| L20 | Plan deliverable | **Part of this phase (user, 2026-10-11):** task T10 writes `nbs/demo_multiagent.ipynb` and `results/multiagent/REPORT.md` around the headline question, from the saved Phase 8-10 results (no rerun) |

The pilot (task T7) fixed the provisional settings; the analysis plan was committed after the pilot and before the main runs.

## Notes from the offline implementation (for the pilot)

- **Turn budget vs world time.** With 50 turns per agent and 1 s stays a text-foraging run spans under two of `benchWorld`'s 40 s patch-move periods (the numpy teams are also still exploring at 50 turns). The pilot confirmed it (LLM runs covered 19-32 s in 30 turns), and the user chose 5 s stays (see Pilot results).
- **Module split.** To stay under 200 lines per file, the board's channels and numpy agent are in `board_agents.py`, the text board in `llm_board.py`, the numpy comparison in `llm_compare.py` and the figures in `llm_figures.py` (design-high-level).
- **Costs on cache hits.** A cached reply keeps the cost of the call that produced it (rows do not depend on the cache, so reruns are byte-identical) and is not charged to the budget; `cacheHit` in each row says how much came from the cache.
- **Provisional estimate.** With the provisional token profile, the main runs were estimated at about $34 (Haiku about $12, Sonnet about $22).

## Pilot results (task T7, 2026-10-12)

Prices re-checked against the pricing page on 2026-10-12: Haiku 5.5 unchanged ($0.10 / $0.50, cache write $0.125, cache read $0.01 per million tokens, prompts up to 100K); Claude Sonnet 5.5 cache reads are now $0.10 (0.05x input; was $0.20), the rest unchanged ($2 / $10, cache write $2.50). Model IDs `claude-haiku-5-5` and `claude-sonnet-5-5` confirmed. A one-call smoke test per task returned valid structured actions and wrote the prompt cache.

| Round | Cells (30 turns) | Finding |
|---|---|---|
| 1 (`maxTokens` 2000) | board solo, difficulty 1-4 x 5 seeds; foraging N 1 and 4 | Haiku solved every puzzle it opened at difficulty 1-3 (15 per run, 0 wrong) and 98.7% at 4: no level in the 30-70% band. Effort medium: 100%. Sonnet (effort low): 93.9%, with 9-10 wrong answers per run. Foraging runs covered only 19-32 s of world time |
| Probe (`maxTokens` 2000) | board difficulty 6, 8, 10 x 3 seeds | Harder puzzles did not bring wrong answers; Haiku reasoned until the 2000-token limit instead (up to 26 of 30 turns invalid on one seed): failure at the interface, not at the task |
| User decision | | Harder board with a larger `max_tokens`; 5 s stays in text foraging |
| 2 (`maxTokens` 8000) | board difficulty 6 and 8 x 5 seeds; foraging with 5 s stays; then effort medium and Sonnet at difficulty 8 | Solve rate (solved / opened): difficulty 6 0.99, **difficulty 8 0.89** (chosen: closest to the band; invalid turns under 1%, 1 `max_tokens` stop in 150 turns), effort medium 0.99 (one seed ran to the limit on 11 turns), Sonnet 0.92. Foraging: 30 turns now span 60-79 s (so 50 turns cover about 2-3 patch moves); no invalid actions |

Fixed settings (`llm_grid.SETTINGS`): effort low, `maxTokens` 8000, difficulty 8, numpy board solve rate 0.889 (Haiku's at difficulty 8), foraging `tStay = 5`. Token profile per call (uncached input / cache-read input / output): Haiku board 208 / 1 771 / 901, Haiku foraging 840 / 1 824 / 433, Sonnet board 214 / 1 743 / 805; about 90% of input tokens come from the prompt cache. Invalid actions: Haiku under 1% at the chosen settings (2.7% over all of round 2's board cells), Sonnet 3.3%; refusals: none. Re-estimate of the main grids: about **$43** (main $12.2, Sonnet $26.0, equal budget $1.6, liar $1.7, framing $0.6, memory $0.4, persistence $0.8), plus $1.56 spent on the pilot, against the $150 cap. The pilot's outputs are in `results/multiagent/llm/pilot/` and `pilot_probe/` (round 1's rows are in the response cache).

**Analysis plan frozen in commit `ce9d661` (2026-10-12), `planHash()` = `83df7591d1de`**; every report prints the hash.

Deviations from the plan, all decided before the analysis plan was frozen: plan Q7's 30-70% solo solve rate was not reachable (Haiku 5.5 either solves these puzzles or runs out of tokens), so the board's channels are tested at a high solve rate where coordination shows mainly as duplicate work; `max_tokens` 8000 instead of 2000; text foraging uses 5 s stays.
