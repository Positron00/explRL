# Plan: Phase 17, RL that makes larger teams pay off

Status: **main runs done and analysed** (2026-10-22; results below: training on 4- and 8-agent teams helped small teams, +0.078 welfare at N 4, exact p 0.035, not significant after Holm, but the gain shrank with size and pooling at N 32 did not rise; trained teams lost less to liars at N 32, secondary, p 0.023; 5 of 8 runs halted, 4 on KL outliers). Earlier: **pilot v2 failed, diagnosed** (2026-10-19): T1-T3 done and tested; pilot v1 ran (results and the deviation below) and found that constrained decoding forced a key order the model never writes; the user chose to re-pilot the same recipes with the constraint in the model's own order (`PILOT17_PLAN` v2, frozen at `8b17f72`, `coopHash` = `52b7cfa582fb`); pilot v2 ran and every recipe halted on KL (diagnosis below: forced and near-certain tokens used as a log-probability sink, and 8-agent prompts cut by the training window); the user approved the fix (2026-10-19): implemented and tested, `PILOT17_PLAN` v3 frozen at `8f3a506` (`coopHash` = `2d3565364f29`; `runs_p17pilot3/`); pilot v3 ran (2026-10-20): `p17a` (one pass) chosen; the user amended the main runs to 8 mixed-team runs of 60 steps (about 86 A100 hours), `RL17_PLAN` frozen at `74699a6` (hash `8e28b5fdfb1f`); step 0 done (below); `RL17_PLAN` not frozen.

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
| P17-4 | Format failures | **Constrained decoding in the model's own key order** (`guided='model'`: notes, action, target, answer, clue, as in 99.9% of the warm start's replies). Revised 2026-10-19 after pilot v1, whose schema-order constraint forced a first key the model never writes (below); the remaining bias from sampling under the constraint is accepted and reported |
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

## Pilot v1 and the deviation (2026-10-19)

`PILOT17_PLAN` v1 (frozen at `626bead`, hash `f4b4bd036996`) ran on two Colab accounts (about 9 GPU hours in all; `results/multiagent/rl/colab/runs_p17pilot/`).

| Pilot | Outcome | Seconds per step | Training welfare, steps 21-30 |
|---|---|---|---|
| `p17a` (1 pass) | 30 steps; its first three updates were undone (per-step change 0.34, 0.14, 0.03 against a target of 0.003) | 586 | 0.031 |
| `p17b` (4 clipped passes, KL 0.01) | halted at step 2: KL to the warm start 12.8 | 1,499 | n/a |
| `p17c` (4 clipped passes, no KL) | halted at step 1: KL 23,720 | 1,421 | n/a |
| `p17d` | not trained (neither `p17b` nor `p17c` passed the rule) | | |

The frozen rule picked `p17a`. **Cause, found in the turn logs:** the warm start writes `{"notes": ..., "action": ..., "target": ..., "answer": ..., "clue": ...}` in 99.9% of 10,880 unconstrained replies; the constrained decoder followed the schema's order and forced `action` first, a token the model almost never produces there. The trainer scores sampled tokens without the constraint, so these forced tokens carry huge negative log-probabilities: the first updates jump (undone by the controller), repeated clipped passes amplify the jump into the KL halts, some constrained replies drift into gibberish, and invalid replies stayed at 1-2% (Phase 16's unconstrained runs started near 0%).

**Deviation, chosen by the user (2026-10-19):** not to train the main runs on `p17a` (about 370 A100 hours on a recipe with the same flaw), but to re-pilot the same four recipes with the constraint in the model's own key order (`guided='model'`, `local_policy.GUIDED_SCHEMA`): `PILOT17_PLAN` v2, the same selection rule, runs in `runs_p17pilot2/` (v1's stay), zip `explRL_rl17pilot2.zip`. The configuration hash includes the new setting, so no v2 run can resume a v1 checkpoint.

## Pilot v2 and its diagnosis (2026-10-19)

`PILOT17_PLAN` v2 ran on two Colab accounts (about 7 GPU hours; `results/multiagent/rl/colab/runs_p17pilot2/`). The rule chose nothing.

| Pilot | Outcome | Seconds per step |
|---|---|---|
| `p17a` (1 pass) | halted at step 28: KL to the warm start 0.65 (0.01-0.04 before; one step jumped) | 560 |
| `p17b` (4 clipped passes, KL 0.01) | halted at step 1: KL 0.64 | 1,416 |
| `p17c` (4 clipped passes, no KL) | halted at step 2: KL 4.6 million | 1,377 |

**Diagnosis on the Mac** (no GPU run; the logged replies replayed through the real rollout rebuild every training prompt exactly, then the 3B model scores them with and without the run's adapter):

1. **Log-probability sink.** The KL is carried by single tokens the warm start writes with probability about 1, pushed down by 4-16 nats: in `p17a` before its halt, the key `target` after `"action": "submit", "` (12 of 40 sampled 8-agent replies), a token the constrained decoder forces anyway; in `p17c`, the empty value `""` after `"target":` and `"clue":`. Lowering such a token lowers the probability of the penalized submit replies without changing what is sampled, so the gradient takes this free route. The reply-level ratio clip does not stop it: it bounds the mean log-ratio over about 50 tokens, so one token can fall about 10 nats inside a 0.2 clip.
2. **Cut prompts.** The training window (`maxLen` 1,536 tokens) cuts prompts from the left: 89% of 8-agent prompts (median 1,810 tokens, up to 2,169) lost the start of the system message (the rules), so the trainer scored replies on prompts the policy never saw. Phases 13 and 16 trained on 4 agents only (about 4% cut). With the full prompt, the per-sample KL of `p17c`'s adapter on 8-agent replies fell from 43,000 to 73 (mean of 40): a real bug and an amplifier, not the root cause.

**Fix, approved by the user (2026-10-19), pilot v3 (`FIX17` in every Phase 17 run; `PILOT17_PLAN` v3, the same recipes and selection rule plus: a recipe that cuts any prompt fails):** loss and KL only on value tokens (keys and punctuation are fixed by the schema: no decision, so no gradient), a per-token clipped ratio (standard PPO) instead of the reply-level one, and a training window that holds the longest prompt, with cut samples counted (must be 0).

## Step 0: every existing adapter against team size (2026-10-19, descriptive)

All 15 adapters on `teamSizeSuite` (account B, about 16 hours on Colab; `results/multiagent/rl/eval_p17s0/report.md`). Pooled share, clean boards (Claude Haiku 5.5's references from Phases 11-14 in the last row):

| model | N 4 | N 8 | N 16 | N 32 |
|---|---|---|---|---|
| warm start | 0.22 | 0.24 | 0.11 | 0.07 |
| credit_s2 (best at N 4) | 0.31 | 0.20 | 0.12 | 0.07 |
| credturn_s2 | 0.31 | 0.23 | 0.11 | 0.04 |
| indpen_s4 (best at N 32) | 0.23 | 0.21 | 0.15 | 0.11 |
| individual (Phase 12) | 0.14 | 0.07 | 0.06 | -0.01 |
| Claude Haiku 5.5 | 0.45 | 0.41 | 0.38 | 0.34 |

Every trained 3B team loses most of its pooling as the team grows (the warm start keeps 0.30 of its N 4 pooled share at N 32; Haiku keeps 0.76), so the gap to Haiku widens with size: the problem Phase 17's training mix targets. Invalid replies rise with N for every adapter (warm 0.000 at N 4 to 0.031 at N 32; credturn_s1 to 0.13, indpen_s3 to 0.49). Honest loss to liars is mostly smaller than Haiku's at N 16-32 because there is less to lose. Individual-reward adapters stay selfish at every size (shares per held clue 0.06-0.39 against the warm start's 0.84-0.94).

## Pilot v3 (2026-10-20)

`PILOT17_PLAN` v3 (frozen at `8f3a506`, hash `2d3565364f29`) ran on two Colab accounts (`results/multiagent/rl/colab/runs_p17pilot3/`; selection reproduced on the Mac, `results/multiagent/rl/pilot_p17/selection.json`).

| Pilot | Outcome | Training welfare, steps 21-30 | Seconds per step |
|---|---|---|---|
| `p17a` (1 pass) | 30 steps, no halt; KL to the warm start 0.008-0.017 at the end (value tokens; 0.01-0.02 over all tokens); 2 steps undone; no prompt cut | 0.284 (0.226 over steps 1-5) | 644 |
| `p17b` (4 clipped passes, KL 0.01) | halted at step 21: invalid replies above 0.1 for 3 steps; KL had climbed to 0.34-0.40 | 0.149 | 1,716 |
| `p17c` (4 clipped passes, no KL) | halted at step 4: KL 1.28 | n/a | 1,675 |
| `p17d` | not trained (neither `p17b` nor `p17c` passed) | | |

The fix worked for the single-pass recipe (pilot v2's `p17a` halted at step 28 on KL 0.65; v3's stayed near 0.01) but not for repeated passes, which still drift (p17b) or blow up (p17c). **The rule chose `p17a`.** Projected main runs (`projectHours` from its 644 s per step, 200 steps): 35.8 A100 hours per `r17mix` run, 23.8 per `r17four` run, **about 405 A100 hours in all** (8 + 5 runs; about half the earlier four-pass estimate). Next: the user confirms these hours; then `RL17_PLAN` is frozen with `p17a`'s recipe (`FIX17` included) and the main runs start on both accounts.

## Main runs, amended and frozen (2026-10-20)

The user confirmed a shorter main run instead of the projected 405 A100 hours: **`r17mix` only (mixed 4- and 8-agent teams with liars), 8 seeds, 60 steps** (as Phases 13-16; the pilot was still improving at step 30), with pilot v3's `p17a` recipe (one pass, `FIX17`). `r17four` (5 seeds) and its hypothesis H17-5 (does the mix itself matter?) are dropped; H17-1 to H17-4 are unchanged. Projected: 10.7 A100 hours per run, about 86 for training plus about 9 for evaluation. `RL17_PLAN` frozen at `74699a6` (`coopHash` = `8e28b5fdfb1f`) with `recipe`, `projectedHours`, `userConfirmed` and an `amended` record. Next: the "Phase 17 main" cell on both accounts.

**Main runs, training (2026-10-22; read from the runs' `metrics.jsonl` on Colab before the evaluation finished).**
- **Halts:** 3 of the 8 `r17mix` runs finished 60 steps (s4, s5, s8; welfare about 0.21 → 0.29). The other 5 halted:
  - s1 at step 7, s6 at 11, s7 at 35 and s3 at 50, all on the KL rule;
  - s2 at step 43 on invalid replies (10-12% for 3 steps).
- **The KL halts were mostly measurement outliers, not policy blow-ups:**
  - In s1, s3 and s6 the logged KL to the warm start jumped in one step (to 0.66, 3.54, 1.02) while the probe measured a step change of 0.0008-0.005 and welfare and invalid replies did not move. The per-token k3 estimate has no upper bound when the policy scores a sampled token far below the reference, so one token can move the mean.
  - In s7 the same term made one update go wrong (step change 103). The controller undid it, but the KL rule halted the run anyway.
  - The halted adapters are the weights at the halt step: s1, s3 and s6 are healthy but trained for only 7, 50 and 11 steps.
- **Analysis:** `RL17_PLAN` is analysed as frozen, with these halts reported.
- **The fix:** Phase 18 Part B uses a fix (a KL cap and a two-step KL halt, `FIX18`, [../phase18/README.md](../phase18/README.md)); Phase 17's configurations are unchanged.

**Main results (2026-10-22; `explRL_rl17.zip`, 8 runs evaluated by account A; `RL17_PLAN` analysed as frozen; `results/multiagent/rl/eval_p17/report.md`).**

| hypothesis (8 runs; Holm within each family) | estimate [95% CI] | exact p | Holm | verdict |
|---|---|---|---|---|
| H17-1 welfare gain over the warm start at N 4 | +0.078 [0.008, 0.136] | 0.035 | 0.106 | not supported (7 of 8 runs positive) |
| H17-2 the gain grows with team size (N 32 minus N 4) | −0.072 [−0.140, −0.012] | 0.98 | 0.98 | not supported: the gain *shrinks* |
| H17-3 more pooling than the warm start at N 32 | +0.006 [−0.052, 0.057] | 0.42 | 0.84 | not supported |
| H17-4 (secondary) less loss to liars at N 32 | +0.061 [0.012, 0.108] | 0.023 | 0.023 | supported |

| welfare | N 4 | N 8 | N 16 | N 32 |
|---|---|---|---|---|
| warm start | 0.258 | 0.283 | 0.133 | 0.083 |
| trained, mean of 8 | **0.336** | 0.295 | 0.198 | 0.089 |
| Claude Haiku (reference) | 0.546 | 0.506 | 0.495 | 0.438 |

- **Training on 4- and 8-agent teams helped small teams but did not carry over to large ones.** The welfare gain was +0.078 at 4 agents, +0.065 at 16 and +0.006 at 32. Invalid replies rose with size (0.086 at 32, against 0.031 for the warm start).
- **Liars did less damage at 32 agents** after training: honest loss 0.27 against 0.33.
- **Halts barely mattered for the small-team gain.** The two runs stopped by KL outliers after 7 and 11 steps gained +0.083 and +0.085 at N 4, against +0.135 to +0.141 for the three full runs. Most of the small-team gain comes early.
- **s2, halted on invalid replies, was the only run that lost** (−0.144 at N 4).
- **The full runs alone (post hoc, three runs):** +0.137 at N 4 and +0.056 at N 32.

