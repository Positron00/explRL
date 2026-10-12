# Spec: Phase 8, benchmark and eval suite

Status: **in progress** (2026-10-11). T1-T5, T7 and T6 (calibration, pre-registration frozen) done; the confirmatory run (T9) comes next. Part of the multi-agent plan: [../README.md](../README.md). Builds on Phase 7: [../phase7/README.md](../phase7/README.md).

## Goal

Answer the plan's headline question with numbers that survive scrutiny: **at a fixed compute budget, how does team performance change with team size under each communication harness?** Phase 7 built the harnesses and a benchmark world in which they differ. Phase 8 measures them, once, with a pre-registered analysis.

1. **Main grid:** the 4 channels x 7 team sizes (1-64) x 2 budgets x 30 seeds on the benchmark world, with bandit agents and individual reward. Output: one tidy CSV row per run, figures and an auto-written `report.md`.
2. **Confirmatory tests, fixed before running:** the primary metric (blackboard vs no channel, welfare per agent-second at fixed compute) and the plan's hypotheses H1 (the blackboard recovers the ideal free distribution faster after patches move) and H2 (the blackboard lowers belief diversity). Holm correction over the three. H3 (liar robustness): its contrast and expected sign are fixed here; its cells and its run belong to Phase 9.
3. **Exploratory side sweeps, one factor at a time:** reward scheme, evaporation, communication range, memory, layout (torus), agent type (circuit), exploration level.
4. **Two studies the plan added after Phase 7:** (A) group vs individual reward, with the team-optimal exploration level as the reference; (B) persisting learned strategy across episodes, with discovery credit tuning each agent's exploration level.
5. **Secondary metrics** for Phases 9-10: discoveries, free-riding index, time to find a moved patch, exploration overlap, information spread, communication cost per unit of welfare, belief diversity and herding.

Phase 8 adds no new channels and no bad agents (Phase 9), and no language models (Phase 10).

**Main acceptance tests:** (a) every existing result is unchanged except Phase 7's IFD-based metrics, which the tie-invariant distance corrects (recorded); (b) every new metric and statistic matches hand-checked examples; (c) the grid's CSV is byte-identical whatever the number of worker processes; (d) the full main grid runs in under 10 minutes; (e) the confirmatory analysis runs once, on unseen seeds, after the analysis plan is committed.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the pre-registered analysis, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions and rejected alternatives, risks |
| [design-low-level.md](design-low-level.md) | Classes, signatures, metric and statistic formulas, grid definitions, defaults, demo layout |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks |
| RUN.md | Written in the last task (T11), same layout as the other RUN files |

## What Phase 7 gives us (the facts the design depends on)

| Piece | Fact | Consequence for Phase 8 |
|---|---|---|
| `runHarness(cfg, N, seed)` / `HarnessConfig` | One call builds the benchmark world, a channel and a team, runs it and returns world, history, channel and metrics; configurations round-trip through a plain dict | A grid cell is a `HarnessConfig` dict plus `N` and `seed`; workers get plain dicts and return plain rows |
| `benchWorld()` | 64-location ring, 16 patches with intake (0.8, 1.6, 2.4, 3.2) x 4, 8 danger sites, random sites per seed, patches move every 40 s; welfare is harvest minus danger cost | Patches with equal intake make the ideal free distribution non-unique; the Phase 6 `ifdDistance` compares with one allocation and overstates the distance (pilot, N = 4: 0.90 instead of 0.64). Phase 8 uses a tie-invariant distance |
| Phase 7 time to IFD | Undefined for every channel (no team gets within 0.2 between moves) | H1 needs a statistic that is always defined: restricted mean time to a calibrated distance, censored at the next move |
| Cost | Pilot on seeds 1000-1001: the main grid costs about 62 CPU-seconds per seed, so 30 seeds take about 31 CPU-minutes; a 64-agent run at fixed world time has about 39 000 events (the plan assumed 10 000) | Seeds run in parallel processes (standard library); `banditAgent` is not changed, so Phase 6 hashes stay exact |
| Phase 7 findings | Blackboard best from 4 agents up; `messages` about equal to `none`; the lead worse than independent bandits at most sizes; Phase 7 used seeds 0-9 | Confirmatory runs use seeds never looked at (100-129) |
| Phase 7 reward-scheme pilot | Team reward breaks bandit learning; difference reward about equal to individual; with a blackboard at N = 64 the team does best at exploration level `cUCB` 2 (0.315) vs the default 1 (0.277) | Study A measures this properly; study B tests whether credit and persistence close the gap |
| `explRL/credit.py` | `Credit` (discovery credit) works; `ScoutBandit` lowered welfare in every pilot | Study B uses `Credit` with a new learner whose exploration level is fixed within an episode and learned across episodes |

## Decisions

| ID | Question | Answer |
|----|----------|--------|
| B1 | Main grid | **As the plan:** `benchWorld()`, `CommBandit` (`LeadFollower` for `hierarchical`), channels `none` / `blackboard` / `messages` / `hierarchical` at their Phase 7 defaults, team sizes 1, 2, 4, 8, 16, 32, 64, budgets fixed compute (`B = 15 360` agent-seconds) and fixed world time (600 s), individual reward (plan Q9), 30 seeds: 1 680 runs |
| B2 | Which seeds | **Confirmatory seeds 100-129**, never used before. Pilot and calibration seeds 1000-1099. Side sweeps and studies use seeds 200-209 (exploratory) |
| B3 | Run time | **Parallel processes** (`multiprocessing`, standard library), `min(8, cpu_count)` workers; rows sorted by cell key so the CSV does not depend on scheduling. `banditAgent` keeps its Phase 6 arithmetic (running sums would change floating-point results). Target under 10 minutes for the main grid |
| B4 | IFD distance with ties | **Tie-invariant distance:** the Phase 6 distance minimised over relabelling patches of equal intake (sort occupancy and target within each intake group). Added to `team_refs` as a new function; Phase 7's `harnessMetrics` switches to it (its IFD metrics change; recorded) |
| B5 | H1 statistic | **Restricted mean recovery time:** after each patch move, the time until the 10 s rolling mean of the tie-invariant distance first reaches `delta`, censored at the next move (a period that never reaches it counts as `Tmove`); averaged over the moves of a run. `delta = 0.5`, calibrated on pilot seeds in T6 before the analysis plan was frozen |
| B6 | Confirmatory family | **Three tests:** P (welfare per agent-second, blackboard minus none, fixed compute, mean over sizes 2-64), H1 (recovery time, blackboard minus none, fixed compute, mean over sizes 4-64), H2 (belief diversity, blackboard minus none, fixed compute, mean over sizes 4-64). Paired over the 30 seeds; two-sided sign-flip permutation test; Holm at 0.05. H3 (liar) is defined here and tested in Phase 9 as its own family |
| B7 | Belief diversity and herding | **Diversity:** for each location known to at least two agents, the standard deviation across agents of their estimated reward rate at the run's end, averaged over locations. **Error:** mean absolute difference between the team's average estimate and the true solo rate. Herding = lower diversity together with higher error than `none` (exploratory). For circuit teams, diversity is the circular standard deviation of the agents' goal headings in world coordinates (the plan's "spread of goal headings"; error is not defined). `hierarchical` has no per-agent beliefs and is left out of H2 |
| B8 | Discoveries and free riding | **From the ledger, after the run**, with the `Credit` rule (first positive harvest at a patch site in each move period), so every team gets them without changing its behaviour. Free-riding index: correlation across agents of harvest share and discovery share |
| B9 | Side sweeps | **One factor at a time** from the main settings, fixed compute, sizes 4, 16, 64, seeds 200-209: reward scheme, evaporation, communication range, memory, layout (torus), exploration level (`cUCB`), and circuit teams on their own world (fixed world time 600 s, as fixed compute across worlds means nothing). Exploratory; reported without p-values |
| B10 | Study A (group vs individual reward) | Reward scheme (individual, team, difference) x channel (`none`, `blackboard`) x sizes 4, 16, 64, plus the `cUCB` sweep, which gives the **team-optimal exploration level** per channel and size. Both come from the B9 side-sweep cells (seeds 200-209), so study A needs no runs of its own |
| B11 | Study B (persistence and credit) | **`LevelBandit`:** a `CommBandit` whose `cUCB` level is fixed within an episode and chosen across episodes by UCB over levels (0.5, 1, 2, 4), valued by episode reward plus discovery credit. 12 episodes of 600 s, each on a new world seed; 8 arms: four **fixed levels** (0.5, 1, 2, 4; `fixed-1` is the fresh Phase 7 behaviour, and the best fixed arm is the team-optimal reference on the same worlds), **strategy persists** and **strategy and map persist** (negative control), each with credit `beta` 0 and 1; blackboard; sizes 16, 64; seeds 200-209. The report weight `w` is not learned, so there is nothing of it to persist |
| B12 | Outputs | `results/multiagent/bench/{quick,full,sweeps}/`: `runs.csv` (standard-library `csv`), `metrics.json`, `report.md`, figures. The frozen analysis plan (`PREREG`) is a constant in code; its hash and the git commit are written into `metrics.json` and the report |
| B13 | Torus layout | `benchWorld(shape='torus')` builds an 8 x 8 torus (64 locations) with the same travel scale; ring stays the default |

Defaults that were marked *(check)* (`delta`, `cLevel`) were fixed by task T6 on pilot seeds; the analysis plan was frozen (committed) after that and before any confirmatory run.

### Calibration (T6, AC-8, 2026-10-11)

Share of move periods in which the 10 s rolling tie-invariant IFD distance reaches `delta`, fixed compute, pilot seeds 1000-1009 (restricted mean recovery time in brackets, seconds):

| channel, N | 0.3 | 0.4 | 0.5 | 0.6 |
|---|---|---|---|---|
| none, 4 | 0.19 [37.3] | 0.23 [36.1] | 0.66 [27.9] | 0.75 [24.2] |
| none, 16 | 0.00 [40.0] | 0.13 [38.2] | **0.42** [32.7] | 0.66 [25.7] |
| none, 64 | 0.00 [40.0] | 0.00 [40.0] | 0.00 [40.0] | 0.00 [40.0] |
| blackboard, 4 | 0.19 [37.2] | 0.25 [36.0] | 0.64 [28.3] | 0.75 [24.6] |
| blackboard, 16 | 0.14 [38.4] | 0.48 [33.1] | 0.84 [24.3] | 0.96 [17.8] |
| blackboard, 64 | 0.04 [39.7] | 0.40 [35.4] | 0.92 [24.5] | 1.00 [15.2] |

AC-8 rule (smallest `delta` that `none` at N = 16 reaches in at least 25% of periods): **`delta = 0.5`**, unchanged from the provisional value.

`cLevel` (study B, `strategy` arm, N = 16, seeds 1000-1002, 12 episodes; episodes 4-11): at 0.03 the levels lock in (with `beta` 0 every agent ends on the same level, spread 0.00); at 0.3 agents keep switching (level stability 0.14 with `beta` 0, 0.34 with `beta` 1); at **0.1** they settle (stability 0.48 and 0.63) while still differing (last-episode spread 0.18 and 0.47). Kept at 0.1.

Pre-registration frozen: `PREREG` hash `8a59293847ae`, commit `e98e238`.
