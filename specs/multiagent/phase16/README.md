# Plan: Phase 16, more training seeds for the incentive result (core)

Status: **done** (2026-10-18): six runs trained and evaluated (`RL16_PLAN` frozen at `0d0b7dc`, hash `082b3b7c9a31`); no hypothesis supported after Holm: the incentive effect's direction holds on average but varies from seed to seed, and the selfish drift replicated in 2 of 4 runs (results below). Part of the multi-agent plan: [../README.md](../README.md). Builds on Phases 12-13 (RL of a 3B team on the clue board; [../phase13/README.md](../phase13/README.md), Track B).

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the frozen analysis plan, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Components, data flow, decisions |
| [design-low-level.md](design-low-level.md) | Module contents, signatures, statistics, notebook sections, tests |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |
| [RUN.md](RUN.md) | Tests, the runs in order, artifacts |

## Why

Our headline incentive result is about information sharing. With RL on the clue board, individual reward taught agents to stop sharing and guess (0.15 clues shared per clue held; 74% of solves made alone); the same reward with a training-only cost per wrong answer (`indpen`) kept both training seeds sharing (0.83 and 1.00; 0% and 5% alone) and scored +0.27 [0.20, 0.34] and +0.18 [0.08, 0.28] per agent-turn above the unfixed reward. Two weaknesses: individual reward was trained **once**, and every interval resamples boards, not training runs. Welfare gains over the imitation warm start were seed-dependent (claims reworded on 2026-10-17, commit `43e2e7b`).

Phase 16 (core) adds training seeds so the sharing contrast, and its score contrast, are tested with the training run as the unit.

## Runs

Same warm start, RL settings, training boards and evaluation boards as Phases 12-13 (`RL_PLAN` v2 with each arm's overrides; `trainSeed = seed - 1`; Qwen2.5-3B-Instruct, four agents sharing one LoRA adapter, 60 GRPO steps, one A100 on Colab).

| Arm | Overrides of `RL_PLAN` v2 | Existing runs | New seeds | Runs after Phase 16 |
|---|---|---|---|---|
| `individual` | `scheme='individual'` (none else: Phase 12's v2 run reproduces this configuration exactly, hash `542eb4f99c29`) | seed 1 (Phase 12 v2) | 2, 3, 4 | 4 |
| `indpen` | `scheme='individual'`, `wrongPenalty=2.5`, `haltJump=0.15` (as Phase 13) | seeds 1, 2 (Phase 13) | 3, 4, 5 | 5 |

Six new runs, trained in an interleaved order (`individual_s2`, `indpen_s3`, `individual_s3`, `indpen_s4`, `individual_s4`, `indpen_s5`) so that a batch cut short still leaves both arms balanced. **One automatic batch:** after set-up and configuration, a single Colab cell trains the six runs one after another (each in its own process), evaluates the six adapters and packs the results to Google Drive (`explRL_rl16.zip`), with no manual step in between; after a disconnect the same cell resumes where it stopped. Evaluation: each new adapter on the 15 held-out main boards (seeds 900-904 and 930-939; N 4, blackboard, 40 turns), as Phases 12-13; existing rows are reused. No generalisation, liar or cross-play cells.

**Optional extension (not in this spec):** three more `credit` seeds (to five) to decide whether RL beats imitation on welfare; about 10 more GPU hours.

## Hypotheses (directions frozen in `RL16_PLAN`; exploratory)

| ID | Prediction | Family |
|---|---|---|
| H16-1 | `indpen` runs share more clues per clue held than `individual` runs | primary |
| H16-2 | `individual` runs make a larger share of their solves alone than `indpen` runs | primary |
| H16-3 | `indpen` runs score higher welfare per agent-turn than `individual` runs | primary |
| H16-4 | `indpen` runs gain welfare over the warm start | secondary |

Tests: exact permutation tests over runs (4 against 5; smallest one-sided p = 1/126) for H16-1 to H16-3, Holm over the three; an exact sign-flip test over the five `indpen` gains (smallest one-sided p = 1/32) for H16-4. Intervals: hierarchical bootstrap (runs, then boards).

**Claim rules, fixed in advance.** The sharing result is called tested if H16-1 and H16-2 pass after Holm; the score contrast if H16-3 does. "RL beats imitation" is said for `indpen` only if H16-4 passes and its hierarchical interval excludes 0; otherwise it stays "seed-dependent". The drift counts as replicated if at least 3 of the 4 `individual` runs make more than half their solves alone (solo share above 0.5); if not, that is reported as the main result: the Phase 12 drift was seed luck.

## Time and cost

Measured in Phase 13: 2.4-3.0 A100 hours per 60-step run (mean 2.8); the full Phase 13 evaluation took about 0.3 hours per adapter on 36 boards, so about 0.13 hours on the 15 main boards; about $1.3 per A100 hour.

| Item | Estimate |
|---|---|
| Training: 6 runs x 2.8 h | 16.8 GPU hours |
| Evaluation: 6 adapters, main boards | about 0.8 GPU hours |
| Overhead (model loading, restarts), about 15% | about 2.6 GPU hours |
| **Total** | **about 20 GPU hours, about $26** |
| Colab sessions | one automatic batch (training, evaluation, packing; each step in its own process, resumable); a disconnect needs one restart: set-up, configuration, the same cell. A 20-hour batch needs a plan with background execution (Colab Pro+) or a session that stays connected |
| Wall time on Colab | about 1 day |
| Engineering on the Mac (T1-T3) | about half a day |
| Analysis and docs after the runs (T6-T7) | about half a day |

No API spend.

## Decisions

| ID | Question | Recommendation |
|---|---|---|
| P16-1 | Reuse Phase 12's individual run as seed 1? | **Yes**: its configuration hash equals the new arm's at seed 1 (checked 2026-10-17) |
| P16-2 | Unit of analysis | **The training run** (its mean over the 15 boards); boards enter only the hierarchical interval |
| P16-3 | Which boards | **The 15 main boards only**: the claims are about main-board behaviour; generalisation is out of scope |
| P16-4 | Halted runs | As Phases 12-13: the trainer saves `final` at the halt (as Phase 12's team run, halted at step 56); evaluate it, report the halt, no replacement seed |
| P16-5 | New code placement | New modules `rl16_grid` and `rl16_report` (`coop_grid` is at 151 lines, `rl_report` at 160) |

## Risks

| Risk | Mitigation |
|---|---|
| A run halts | P16-4 |
| `individual` seeds do not drift | Reported as the main result (claim rule above: fewer than 3 of 4 runs with solo share above 0.5) |
| The permutation tests cannot reach significance with 4 against 5 runs unless the groups separate almost completely | Known in advance (smallest p 0.008; Holm needs p at most 0.017 for the smallest); report effect sizes and intervals regardless |
| Colab disconnects | Runs resume from checkpoints; the batch cell skips finished runs and evaluated adapters; outputs are on Google Drive, so nothing is lost with the runtime |

## Results (2026-10-18; exploratory)

Six new runs on Colab (an A100 for the first three, a G4 after the restart; 12.7 GPU hours of training, about $17), resumed across sessions exactly as designed; two halted under the frozen stopping rules and were evaluated from their final adapters (`individual_s2`: invalid replies above 10% for 3 steps at step 43; `indpen_s3`: the jump rule at step 40). Frozen analysis: `results/multiagent/rl/eval_p16/report.md`, summary copied here ([summary.json](summary.json)).

| Run | Clues shared per held | Solo share | Welfare | Guesses per board* | Invalid replies* |
|---|---|---|---|---|---|
| warm start | 0.92 | 0.00 | 0.273 | 0.7 | 0.000 |
| individual s1 (Phase 12) | 0.15 | 0.74 | 0.102 | 90.3 | 0.005 |
| individual s2 (halted) | 0.11 | 0.79 | 0.007 | 50.5 | 0.298 |
| individual s3 | 0.38 | 0.25 | 0.140 | 57.7 | 0.015 |
| individual s4 | 0.41 | 0.40 | 0.131 | 49.2 | 0.024 |
| indpen s1 (Phase 13) | 1.00 | 0.00 | 0.371 | 0.1 | 0.006 |
| indpen s2 (Phase 13) | 0.83 | 0.05 | 0.283 | 6.9 | 0.010 |
| indpen s3 (halted) | 0.47 | 0.14 | 0.136 | 14.7 | 0.214 |
| indpen s4 | 0.75 | 0.07 | 0.277 | 11.4 | 0.033 |
| indpen s5 | 0.10 | 0.53 | 0.043 | 14.6 | 0.018 |

\* Descriptive, added after the freeze (not in `RL16_PLAN`).

| Hypothesis | Estimate [95% CI] | Exact p | Holm p | Supported |
|---|---|---|---|---|
| H16-1: indpen shares more per held clue | +0.37 [0.04, 0.68] | 0.056 | 0.111 | no |
| H16-2: individual solves alone more | +0.39 [0.07, 0.66] | 0.032 | 0.095 | no |
| H16-3: indpen scores higher | +0.13 [0.00, 0.24] | 0.064 | 0.111 | no |
| H16-4: indpen beats the warm start | -0.05 [-0.16, 0.05] | 0.78 | n/a | no |

**Claim verdicts (rules fixed in advance):** the sharing result is **not tested** (H16-1 and H16-2 fail after Holm), the score contrast **not tested**, RL beating imitation **seed-dependent**, and the selfish drift **not replicated** (2 of 4 individual runs above 0.5 solo share).

- **The direction holds on average; it is not established.** Priced-loophole runs shared more (0.63 against 0.26 per held clue), solved alone less (16% against 55%) and scored higher (0.22 against 0.10), but run-to-run variance is as large as the effect: one priced run (`s5`) drifted selfish (0.10 shared, 53% solo, with few invalid replies), and two individual runs drifted only partly.
- **Individual reward cost welfare in every run** (gain over the warm start -0.13 to -0.27 in all four); priced runs ranged from -0.23 to +0.10.
- **Post hoc, guessing separates the arms completely:** every individual run guessed 49-90 times per board, every priced run 0.1-15. Pricing wrong answers reliably suppressed the behaviour it priced, but whether that kept agents sharing depended on the seed. This was not a planned test and is hypothesis-generating only.
- **Format collapse in the halted runs** (21-30% invalid replies) confounds their sharing numbers; Phase 17's constrained replies address this.
- **Consequences:** the preprint, `REPORT.md` and the summary page drop "pricing the loophole kept agents sharing" as a headline; it becomes "direction consistent, seed-dependent". The variance itself supports Phase 17's design (the training run as the unit, 8 seeds for the main arm).
