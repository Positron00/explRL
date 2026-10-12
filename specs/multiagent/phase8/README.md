# Spec: Phase 8, benchmark and eval suite

Status: **implemented** (2026-10-11). Results below; how to run: [RUN.md](RUN.md). Part of the multi-agent plan: [../README.md](../README.md). Builds on Phase 7: [../phase7/README.md](../phase7/README.md).

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
| [RUN.md](RUN.md) | How to run the tests, the benchmark modes and the regression checks |

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
| B5 | H1 statistic | **Restricted mean recovery time:** after each patch move, the time until the 10 s rolling mean of the tie-invariant distance first reaches `delta`, censored at the next move (a period that never reaches it counts as `Tmove`); averaged over the run's full move periods. `delta = 0.5`, calibrated on pilot seeds in T6 before the analysis plan was frozen |
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


## Results (2026-10-11)

### Confirmatory (T9; main grid, seeds 100-129, run once on the frozen `PREREG`)

1 680 runs in 280 s on 8 processes. Each test: blackboard minus `none`, fixed compute, per-seed mean over the listed sizes, 30 seeds.

| Test | Mean difference [95% CI] | dz | Holm p | Verdict |
|---|---|---|---|---|
| P: welfare per agent-second (sizes 2-64) | +0.091 [0.088, 0.093] | 10.9 | 0.0003 | **supported** |
| H1: restricted mean recovery time, s (sizes 4-64) | -7.5 [-8.1, -7.0] | -5.0 | 0.0003 | **supported** (faster) |
| H2: belief diversity (sizes 4-64) | -0.109 [-0.111, -0.108] | -25.1 | 0.0003 | **supported** (lower) |

0.0003 is the smallest Holm-adjusted p the 10 000-flip test can give. The CSV re-analysis reproduces these numbers exactly. No deviations from the pre-registration.

### Exploratory

- **Scaling (welfare per agent-second; fixed compute / fixed world time):** with one or two agents all channels are equal. At fixed compute, independent bandits collapse as the team grows (`none`: 0.48 at N = 4 to 0.07 at N = 64; each agent's run is short and early exploration, which now pays the danger cost, dominates), while the blackboard holds up (0.48 to 0.27). At fixed world time the blackboard rises to 0.46 at N = 16 while `none` slowly declines (0.27 to 0.20). `messages` tracks `none` within 0.02 everywhere. The lead is worst at small sizes (up to 16 agents at fixed compute, up to 8 at fixed world time) and lies between `none` and the blackboard at larger sizes.
- **Study A (team-optimal exploration):** best `cUCB` for the blackboard is 1.0, 0.5 and 2.0 at N = 4, 16, 64; for `none` 1.0, 0.5, 0.5. With 64 agents sharing a board, more exploration than the default pays (2.0: 0.298 vs 0.279); without sharing, less does (0.5: 0.129 vs 0.070).
- **Reward schemes:** team reward breaks bandit learning at every size (negative welfare at N = 64); difference reward is equal to or slightly above individual at N = 4-16 (blackboard 0.500 vs 0.473 at N = 4) and mostly slightly below at 64.
- **Evaporation:** the blackboard does best at `lam` 0.01-0.03 for 16-64 agents and collapses at 0.1 for large teams (N = 64: 0.042); the lead prefers little or no fading (`lam` 0.003 at N = 4, 0 at 16 and 64).
- **Memory:** a window of one entry (`K = 1`) hurts bandit teams at N = 4 and 16 (blackboard, N = 4: 0.250 vs 0.473) but helps independent bandits at N = 64 (`none` 0.090 vs 0.070, `messages` 0.078 vs 0.065) and the lead at small sizes (N = 4: 0.387 vs 0.246); `K = 10` helps independent bandits at N = 16 (0.390 vs 0.349), because the world moves and old stays mislead.
- **Communication range:** no effect on `messages` (all within 0.01).
- **Torus layout:** slightly better for small teams, worse for the blackboard at N = 64 (0.203 vs 0.279).
- **Circuit teams (zone ring, fixed world time):** channels do not help (`none` is best at N = 4 and 16) and, unlike bandits, they raise the spread of goal headings (N = 4: 1.13 rad without a channel, 1.46 with the blackboard).
- **Study B (persistence and credit, 12 episodes, last 4):** at N = 64 the best fixed level is 2.0 (0.311 vs 0.275 at 1.0). Learning the level across episodes **with** discovery credit closes 45% of that gap (0.291); without credit it ends below the default (-29%, 0.264). Persisting the map as well hurts (-69% and -97%), as the negative control predicted. At N = 16 the default level is already best (no gap to close). Level stability is higher with credit (0.68 vs 0.23 at N = 64). The mechanism is visible in `studyB.png`: with credit the agents' learned level rises to about 2.4, near the team optimum of 2.0; without credit it drifts below 1, the level each agent prefers for itself.

### Figure guide in plain language

The figures are written by `nbs/demo_bench.ipynb` to `results/multiagent/bench/full/` (main grid) and `results/multiagent/bench/sweeps/` (side sweeps and study B); that folder is not in git, so rebuild it with the commands in [RUN.md](RUN.md).

**The setup.** A team of simple learning agents forages on a ring of 64 spots: 16 hold food, 8 are dangerous, and the food jumps to new spots every 40 seconds. Each agent learns from experience where food is. They can share what they find in four ways: **none** (each learns alone), **blackboard** (a shared notice board everyone writes to and reads), **messages** (now and then an agent tells two others its best find) and **hierarchical** (a lead collects reports and tells each agent where to go). *Welfare* is food collected minus danger penalties; *per agent-second* divides by team size and time, so a higher number means each agent's time was used better.

**`scaling.png`: does a bigger team help?** One line per sharing method; team size doubles from 1 to 64 along the bottom. *Left, fixed total effort* (every team gets the same total agent-time, so a team of 64 runs only briefly): without sharing, output per agent collapses beyond 4-8 agents, because each agent spends its short run searching and stumbling into danger; the blackboard holds up far longer. *Right, same running time for everyone:* the blackboard gets better as the team grows up to 16; teams without sharing slowly get worse. In both, the lead does badly in small teams, since it keeps sending single agents to unexplored (sometimes dangerous) spots. The legend gives the change in output per doubling of team size.

**`confirmatory.png`: the three tests fixed in advance.** Each panel shows the blackboard team minus the no-sharing team at each team size (dots); the orange band is the average over sizes, the number the test judged; the black line is "no difference". All three came out as predicted: the blackboard team collects more food (from 16 agents up), re-organises up to 16 seconds faster after the food moves (below zero means faster), and its agents disagree far less about which spots are good (below zero means more agreement; the "crowd becomes of one mind" effect known from human groups).

**`recovery.png`: re-organising after the food moves.** *Left:* average seconds until the team spreads sensibly over the new food (40 means it never did before the next move). The blackboard gets faster as teams grow; teams without sharing get slower and, at 64 agents, never manage it. *Right:* the share of moves after which a team re-organised at all: 90% or more for large blackboard teams, falling to 0 without sharing.

**`beliefs.png`: what the agents believe.** *Left:* how much agents disagree about each spot. With the blackboard this collapses toward zero in large teams (everyone reads the same board); without sharing it stays high. *Right:* how wrong the team's average belief is. It falls with team size for every method, and the blackboard is about as accurate as independent agents, so here agreement did not come at the cost of being wrong. The lead has no per-agent beliefs and is not shown.

**`secondary.png`: six supporting measures.** (1) *Discoveries:* how often someone is first to find a moved patch; small lead teams score highest because they are told to explore. (2) *Free riding:* whether agents who harvest most are also those who find patches; it is positive, so no sign of agents living off others' finds (uncertainty is wide). (3) *Find time:* seconds until a moved patch is found; shorter in bigger teams. (4) *Overlap:* how much agents visit the same spots; teams without sharing crowd together more and more, blackboard and lead teams spread out. (5) *Follow time:* seconds until a second agent joins a new find. (6) *Communication per unit of food:* the lead uses by far the most.

**`sweeps.png` (exploratory): changing one setting at a time.** Solid lines are 16-agent teams, dashed lines 64-agent teams; colours mean the same in every panel. *K (memory):* remembering about the last 10 visits per spot helps, because old memories of food that has moved mislead. *cUCB (curiosity):* for 16 agents moderate curiosity is best; for 64 agents sharing a board, more curiosity (2) is best, which agents would not choose for themselves because the exploring mostly benefits others. *lam (fading of board notes):* gentle fading works best; fast fading erases useful information and large teams collapse. *radius (how far messages reach):* no difference. *scheme (how agents are rewarded):* rewarding everyone with the group average ("team") wrecks learning, because agents can no longer tell which of their choices paid; rewarding each agent's own contribution ("difference") is about as good as plain individual reward. *shape (ring or grid):* small differences.

**`studyB.png` (exploratory): can agents learn to explore for the team over many rounds?** Teams play 12 rounds, each in a new world. Dashed lines are agents locked at one curiosity level, for comparison; solid lines learn their level across rounds, keeping either only that strategy ("strategy") or also their old food maps ("all"), with or without a bonus whenever others harvest food they found first ("beta=1.0"). *Top:* food per agent per round. At 64 agents the best fixed level is 2; learners with the finder's bonus get close to it, learners without it end below the default, and keeping old maps gets worse round after round. *Middle:* the curiosity level chosen. With the bonus, agents settle near 2.4, close to the team's best; without it they drift below 1, which is better for each agent but worse for the team. At 16 agents the default is already about right. *Bottom:* how often agents keep last round's level; rewarded agents settle into stable choices, unrewarded ones keep switching.

**In one sentence:** a shared notice board makes large teams much more productive and more of one mind, and rewarding agents for discoveries that others use teaches them to explore for the team, closing about half the gap to the best setting at 64 agents.
