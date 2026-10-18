# Requirements: Phase 16, more training seeds for the incentive result

Part of [README.md](README.md) (plan and decisions P16-1 to P16-5). Builds on Phase 12 (`RL_PLAN` v2, `evalSuite`) and Phase 13 Track B (`RL13_ARMS`, `rl13Config`, `rl13Suite`, the Colab batch and evaluation cells, `rl_report`).

Terms: as Phase 13 ([../phase13/requirements.md](../phase13/requirements.md)); in addition:

- **Run:** one RL training run (an arm and a seed); its adapter is named `<arm>_s<seed>`; `trainSeed = seed - 1`.
- **Run value:** a run's mean of a metric over the 15 main boards.
- **Gain:** a run's mean over the main boards of its welfare minus the warm start's on the same board seed.
- **Sharing metrics:** `sharePerHeld` (clues shared per clue held) and `soloShare` (share of solves with no shared clue used), as Phase 12. A board with no solves has no `soloShare` (nan); run values and bootstrap draws skip nan boards.
- **Drift replicated:** at least 3 of the 4 `individual` runs have a `soloShare` run value above 0.5.

## Functional requirements

### Part A: grid and plan
- **FR-A1** `RL16_ARMS = dict(individual=dict(scheme='individual'), indpen=RL13_ARMS['indpen'])`; `RL16_RUNS` = (`individual`, 2-4), (`indpen`, 3-5); `rl16Config(arm, seed, model, out)` = `RL_PLAN` v2's settings with the arm's overrides and `trainSeed = seed - 1`.
- **FR-A2** `RL16_REUSED`: `individual_s1` = Phase 12's v2 individual run (rows from `rl/eval/runs.csv`, model `local:individual`, levels `individual|*`), `indpen_s1`, `indpen_s2` (from `rl/eval_p13/runs.csv`) and the warm start (`rl/eval/runs.csv`).
- **FR-A3** `rl16Suite(models=None)`: `evalSuite`'s main-board cells (N 4, blackboard, 40 turns, seeds 900-904 and 930-939) for the six new adapters.
- **FR-A4** `RL16_PLAN`: the runs, the reuse, the evaluation, the analyses and hypotheses below, the claim rules; frozen and committed before the first Phase 16 run; its hash recorded in the README.

### Part B: Colab (one automatic batch)
- **FR-B1** One section in `nbs/colab_clue_rl.ipynb`, "Phase 16: runs, evaluation and pack in one session", whose single cell, after set-up and configuration, with no manual step in between: (1) trains `RL16_RUNS` in the interleaved order of the README, each run in its own Python process (finished or halted runs skipped, both having `final/`; an unfinished run resumes from its last checkpoint), output `runs_p16/<name>/`; (2) evaluates the six adapters, `evalModels(rl16Suite(), ...)` into `eval_p16/`, in its own process (adapters already evaluated are read back); (3) packs `runs_p16` (configs, metrics, final adapters) and `eval_p16` into its own zip, `MyDrive/explRL_rl/explRL_rl16.zip` (Phase 13's `explRL_rl.zip` is left as it is); and prints each adapter's main-board welfare, `sharePerHeld` and `soloShare`. It asserts `RL16_PLAN['frozen']` first; a failed step stops the batch with a message saying how to resume (restart, set-up, configuration, the same cell).
- **FR-B2** The configuration cell defines `RUNS16 = OUT / 'runs_p16'` and prints `RL16_PLAN`'s version, hash and frozen state; the notebook's header lists the Phase 16 section.
- **FR-B3** The existing Pack cell's list of directories gains `eval_p16` (`runs_p16` is covered by its `runs*` rule), so a manual Pack's `explRL_rl.zip` also holds the Phase 16 outputs (with everything else).

### Part C: analysis on the Mac
- **FR-C1** `boardValues(rows12, rows13, rows16, metric)` and `runValues(rows12, rows13, rows16, metric)`: per run its board values and its run value, from the evaluation rows (`<model>|main` levels; `rows12` = `rl/eval/runs.csv`, `rows13` = `rl/eval_p13/runs.csv`, `rows16` = the Phase 16 rows), the reused runs under their `RL16_REUSED` names.
- **FR-C2** `permTest(a, b)`: exact one-sided permutation test of mean(a) - mean(b) > 0 over all relabelings of the pooled runs; returns the difference and p.
- **FR-C3** `signFlip(x)`: exact one-sided sign-flip test of mean(x) > 0 over all 2^n sign patterns; returns the mean and p.
- **FR-C4** `hierBoot(groups, stat, nboot=2000, seed=0)`: 95% interval resampling runs within each group, then boards within each resampled run.
- **FR-C5** `rl16Summaries(rows12, rows13, rows16, nboot=2000)`: per run, the run values of `sharePerHeld`, `soloShare`, `welfare` and the gain; H16-1 to H16-4 with their tests, Holm-adjusted p over the primary family, hierarchical intervals, the claim verdicts; descriptive: drift count (`individual` runs with `soloShare` above 0.5) and whether the drift replicated (Terms), the seed-to-seed standard deviation per arm and metric.
- **FR-C6** `writeRL16(path, S, meta)` (report.md) and `figRL16(out, S)` (each run a point per arm and metric, the warm start as a reference); `tools/incentive_figure.py` gains the new runs (each seed its own row).
- **FR-C7** New `demo_rl16`: quick (synthetic runs, `syntheticRows`, into `results/multiagent/rl/quick_p16/`), full (flag `train`: `rl/eval/runs.csv`, `rl/eval_p13/runs.csv` and the unzipped `rl/colab/eval_p16/runs.csv`; GPU hours from the runs' per-step seconds), report and figure.

### Part D: docs
- **FR-D1** Results in this README, `REPORT.md` (a Phase 16 section), the preprint's RL section and contributions, and the claim wording everywhere it appears, as the claim rules decide.

## Analysis plan (`RL16_PLAN`; frozen before the first run; exploratory)

Runs: `individual` s1-s4, `indpen` s1-s5; the warm start. Run values over the 15 main boards.

| ID | Test | Family |
|---|---|---|
| H16-1 | `permTest(sharePerHeld[indpen], sharePerHeld[individual])` | primary |
| H16-2 | `permTest(soloShare[individual], soloShare[indpen])` | primary |
| H16-3 | `permTest(welfare[indpen], welfare[individual])` | primary |
| H16-4 | `signFlip(gain[indpen])` | secondary |

Holm over H16-1 to H16-3 at 0.05. Intervals: `hierBoot` of each difference (H16-1 to H16-3) and of the mean gain (H16-4). Claim rules: README. Descriptive: each run's values; drift count; per-arm seed standard deviation against the between-arm difference.

## Quality requirements

- **NFR-1** Phase 5-15 reference outputs unchanged (cached reruns byte-identical); `rl13Config` and every Phase 13 configuration hash unchanged.
- **NFR-2** Offline tests need no network, key, GPU, `anthropic` or `torch`.
- **NFR-3** No API spend; GPU about 20 A100 hours (README).
- **NFR-4** Seeds fixed; a rerun of the analysis on the same rows is byte-identical.
- **NFR-5** Each module under 200 lines; `coop_grid` and `rl_report` unchanged except imports where needed.

## Acceptance criteria

- **AC-1** Regression: NFR-1; the full suite passes.
- **AC-2** Configurations: `rl16Config('individual', 1, ...)` has hash `542eb4f99c29` (Phase 12's v2 individual run); `rl16Config('indpen', s, ...)` equals `rl13Config('indpen', s, ...)` for s = 1, 2; the six new runs have `trainSeed` 1-3 (`individual`) and 2-4 (`indpen`).
- **AC-3** Grid: `rl16Suite()` has 6 x 15 cells on the main boards; the reused rows map to `individual_s1`, `indpen_s1`, `indpen_s2` and `warm`.
- **AC-4** Statistics on synthetic runs: complete separation of 4 against 5 runs gives p = 1/126; five positive gains give p = 1/32; identical groups give p = 1; `hierBoot` intervals contain the true difference in simulated data in about 95% of draws (checked once: 200 simulations, 500 bootstrap draws each, coverage between 0.85 and 0.99; measured 0.90: the percentile bootstrap undercovers with 4-5 runs per arm, so the exact tests carry the inference and the intervals are descriptive); Holm as `fix_stats`.
- **AC-5** Gates: the Phase 16 batch cell refuses to run before `RL16_PLAN` is frozen; the full analysis refuses rows without all nine runs and the warm start (15 main boards each).
- **AC-6** Every `RL16_PLAN` item reported, labelled exploratory; the claim wording in the preprint and `REPORT.md` follows the claim rules.

## Out of scope

More `credit` or `credturn` seeds (the optional extension); generalisation, liar and cross-play cells; other model sizes; changes to the Phase 12-13 runs or results.
