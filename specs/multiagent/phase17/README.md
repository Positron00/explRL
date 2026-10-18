# Plan: Phase 17, RL that makes larger teams pay off

Status: **implemented, not run** (2026-10-18): T1-T3 done and tested offline (the trainer equals `trainRL` at its defaults on the tiny model); no plan frozen; step 0 waits for Phase 16. Part of the multi-agent plan: [../README.md](../README.md). Builds on Phases 12-16 (RL of a 3B team on the clue board) and Phase 14 (team size with Claude Haiku). Next idea in line: [Phase 18](../phase18/README.md) (stub).

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the two frozen plans, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Components, data flow, decisions |
| [design-low-level.md](design-low-level.md) | Module contents, the new trainer, run claiming across Colab accounts, statistics, tests |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |
| [RUN.md](RUN.md) | Tests, the runs in order, artifacts |

## Why

More agents is a way to spend more compute at test time, but on our clue board it pays less as teams grow: Claude Haiku teams pooled less information (pooled share 0.41 at 8 agents, 0.34 at 32) and built on false clues more often (0.79 to 0.91 of answers) as they grew (Phases 14-15). Prompting and harness fixes helped only in part. Our RL so far changed behaviour (incentives decided whether agents shared) but did not clearly raise team performance over imitation: 60 steps, 10-turn games, one update per batch, format failures that ended runs.

Phase 17 asks: **can RL with the right incentive, a stronger recipe and training on larger and adversarial teams make bigger teams pay off?** The headline is a curve: team performance and information pooling against team size (4 to 32 agents), for RL-trained teams against the imitation start, clean and with a quarter of the agents liars.

## Parts

**Step 0, evaluation only.** Every existing adapter (15 models: the warm start; Phase 12 `individual`, `team`, `credit`; Phase 13 `credit_s2`, `indpen_s1-2`, `credturn_s1-2`; Phase 16 `individual_s2-4`, `indpen_s3-5`) on the team-size grid below. Gives the baseline scaling curve for trained 3B teams and tests the larger-team evaluation code before any new training.

**Pilot (frozen `PILOT17_PLAN`).** Four 30-step configurations of the new recipe, one seed each, on the main arm's training mix, compared on the same training boards:

| Pilot | Constrained replies | Updates per batch | KL penalty | Per-step change target | Turns per agent |
|---|---|---|---|---|---|
| `p17a` | yes | 1 (as Phases 12-16) | 0.04 | 0.003 | 20 |
| `p17b` | yes | 4, clipped ratio (epsilon 0.2) | 0.01 | 0.01 | 20 |
| `p17c` | yes | 4, clipped ratio | 0 | none (fixed learning rate 1e-4) | 20 |
| `p17d` | yes | as the better of `p17b` and `p17c` by the rule below | as that one | as that one | 40 |

Selection rule (fixed before the pilot): drop a configuration that halted or whose invalid-reply share over its last 10 steps exceeds 5%; among the rest, pick the highest mean training welfare over steps 21-30 (the same board seeds for every configuration at each step, so the comparison is paired); within 0.02 of the best, pick the cheaper per step. `p17d`'s base (`p17b` or `p17c`) is chosen by the same rule applied to those two only, after they finish; the final choice is among all four. One seed per configuration: the choice is a screen, not a test. The pilot also measures rollout and update seconds per step, from which the main runs' cost is projected.

**Main runs (frozen `RL17_PLAN`, after the pilot; the recipe is `chosenRecipe` of the pilot's choice).** The chosen recipe, credit reward with the guessing loophole priced (Phase 13), 200 steps, two arms (`r17mix` 8 seeds, `r17four` 5 seeds; see the hypotheses for why 8):

| Arm | Training boards | Purpose |
|---|---|---|
| `r17mix` | half the boards with 4 agents, half with 8; a quarter of all boards with a quarter of the agents scripted liars | the main arm: trained on larger and adversarial teams |
| `r17four` | 4 agents, no liars (as Phases 12-16) | ablation: does training on larger, adversarial teams matter, or does any stronger RL scale? |

The imitation warm start is the control (it exists; no new run).

**Evaluation (every model).** Team sizes 4, 8, 16, 32; clean boards (15 at N 4, 10 at each larger N) and boards with `N // 4` liars (10 at each N); 40 turns; blackboard; notes memory (as Phases 12-16). References, not tests: Claude Haiku's curve from Phases 11 and 14 (full memory; a different harness setting).

## Hypotheses (directions to freeze in `RL17_PLAN`; exploratory)

Unit: the training run; gain = a run's mean welfare minus the warm start's on the same boards.

| ID | Prediction | Test | Family |
|---|---|---|---|
| H17-1 | `r17mix` gains welfare over the warm start at N 4 | sign-flip over 8 runs (smallest p 1/256) | primary |
| H17-2 | `r17mix`'s gain grows with team size: gain at N 32 minus gain at N 4 above 0 | sign-flip over 8 runs | primary |
| H17-3 | `r17mix` pools more information than the warm start at N 32 (pooled share) | sign-flip over 8 runs | primary |
| H17-4 | `r17mix` loses less to liars than the warm start at N 32 (honest loss) | sign-flip over 8 runs | secondary |
| H17-5 | `r17mix`'s gain at N 32 exceeds `r17four`'s | permutation test, 8 against 5 (smallest p 1/1287) | secondary |

Holm within each family. **Why 8 seeds for `r17mix`:** with 5, an exact sign-flip test cannot go below p = 1/32 = 0.031, so Holm over the three primary hypotheses (at least 0.094) and over the two secondary ones (0.0625 for H17-4) could never reach 0.05, whatever the runs showed (found by the synthetic tests); with 8 the floors are 3/256 = 0.012 and 2/256 = 0.008. `r17four` only enters H17-5, whose permutation test of 8 against 5 reaches 1/1287. Intervals: hierarchical bootstrap (runs, then boards), descriptive (Phase 16 found it undercovers with 4-5 runs).

## Compute (no cap; estimates to be replaced by the pilot's measurements)

Measured in Phase 13 (A100, 4 agents, 10 turns, one update pass): about 52 s of rollout and 115 s of update per step, with about 280 trained replies. The update dominates and scales with the trained replies times the passes. Projected per step, with 20-turn games: `r17mix` plays about 3x the replies (half the boards with 8 agents) and `r17four` about 2x; four clipped passes cost about 3.5x one pass (the reference and old log-probabilities computed once per step, then four forward-backward passes).

| Item | A100 hours (rough) |
|---|---|
| Step 0: 15 adapters on the evaluation grid (about 44,000 replies each, about 25 replies a second) | about 8 |
| Pilot: `p17a` (one pass) about 4; `p17b`, `p17c` about 11 each; `p17d` (40 turns) about 23 | about 50 |
| Main, with 4 passes and 20 turns: `r17mix` about 1,360 s per step, about 75 h per run; `r17four` about 900 s, about 50 h | about 850 for 13 runs (8 x 75 + 5 x 50) |
| Main evaluation: 13 adapters | about 7 |
| **Total** | **about 915** |

If the pilot picks one pass per batch, the main runs cost about a third of this. The levers, fixed in `RL17_PLAN` after the pilot and before any main run: passes per batch, the share of turns trained (`turnFraction`), steps. At roughly 12 compute units per A100 hour, about 915 hours is about 11,000 units: buy extra units, or run two Pro+ accounts in parallel (the main cell claims runs, so two accounts never train the same run; wall time about 18 days with two accounts). **Gate:** after the pilot, the projected main-run hours are reported and the main runs start only after the user confirms them. Engineering on the Mac: about 2-3 days.

## Decisions

| ID | Question | Recommendation |
|---|---|---|
| P17-1 | Control | **The existing warm start** (imitation); the Phase 12-16 runs are reported in step 0 as references |
| P17-2 | Reward | **Credit with the loophole priced** (`wrongPenalty` 2.5): the incentive that kept sharing intact; board-level advantages (per-turn added nothing in Phase 13) |
| P17-3 | Recipe choice | **A frozen pilot with a fixed selection rule**, on training boards only; held-out evaluation boards are never used to choose |
| P17-4 | Format failures | **Constrained decoding** (replies forced into the reply schema during sampling); the small bias from sampling under the constraint is accepted and reported |
| P17-5 | New trainer | **Separate modules** (`rl17_train` for the loop, `rl17_update` for the step's pieces: one module would pass 200 lines), so Phase 12-16 training is untouched and byte-identical |
| P17-9 | Long runs on Colab | **One cell per step of the work, run in the background; a checkpoint every step.** Training, evaluation and packing run from one cell each (as Phase 16), with Pro+ background execution. Colab ends a session after about 24 hours while a main run takes days, so runs checkpoint every step (the interval is outside the configuration hash) and the same cell resumes them; the gates between step 0, the pilot and the main runs (freezes, cost confirmation) are deliberate |
| P17-8 | Seeds | **`r17mix` 8, `r17four` 5**: the exact tests' smallest p must leave room for Holm (above) |
| P17-6 | Several Colab accounts | **Shared Drive folder at the identical path** (`MyDrive/explRL_rl`, a shortcut on the second account) and a claim file per run; a claimed run is taken over only when the user says so |
| P17-7 | Phase 16 | **Unchanged (frozen); its six adapters join step 0**, which evaluates the models already on Drive and adds Phase 16's on a rerun. The pilot depends on neither and may run on a second Colab account while Phase 16 finishes (revised 2026-10-18) |

## Risks

| Risk | Mitigation |
|---|---|
| The stronger recipe is unstable (collapse, reward hacking) | The pilot screens it; the stopping rules stay; a halted main run is evaluated and reported, not replaced |
| Training welfare in the pilot is noisy | Paired boards across configurations; 10-step means; ties go to the cheaper configuration |
| 32-agent evaluation is slow or runs out of memory | Step 0 tests it on existing adapters first; boards per size can be cut by a rule fixed in `RL17_PLAN` |
| Constrained decoding changes what the policy learns | Pilot `p17a` isolates it against Phases 12-16; reported as a design choice |
| The gain does not grow with N | A clear negative answer to the posting's central question is still a result; H17-5 tells whether training size mattered |
