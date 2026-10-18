# Design (low level): Phase 16

Part of [README.md](README.md); see [design-high-level.md](design-high-level.md).

## `rl16_grid`

```python
from explRL.coop_grid import RL_PLAN, RL13_ARMS, RL13_PLAN, coopHash, evalSuite
from explRL.clue_rl import RLConfig

RL16_ARMS = dict(individual=dict(scheme='individual'),          # Phase 12 v2's individual run at seed 1 (hash 542eb4f99c29)
                 indpen=RL13_ARMS['indpen'])                      # Phase 13's arm
RL16_RUNS = (('individual', 2), ('individual', 3), ('individual', 4), ('indpen', 3), ('indpen', 4), ('indpen', 5))
RL16_REUSED = dict(individual_s1=('eval', 'individual'),          # (evaluation directory, model name in its rows)
                   indpen_s1=('eval_p13', 'indpen_s1'), indpen_s2=('eval_p13', 'indpen_s2'), warm=('eval', 'warm'))
RL16_ALL = dict(individual=['individual_s1', ..., 'individual_s4'], indpen=['indpen_s1', ..., 'indpen_s5'])   # every run per arm

def rl16Name(arm, seed) -> str                                   # f'{arm}_s{seed}'
def rl16Config(arm, seed, model, out) -> RLConfig                # RLConfig(model, out, **{**RL_PLAN['rl'], **RL16_ARMS[arm], 'trainSeed': seed - 1})
def rl16Suite(models=None) -> list                               # [c for c in evalSuite(models or new names) if c['level'].endswith('|main')]
RL16_PLAN = dict(version=1, frozen=False, base=dict(RL_PLAN=coopHash(RL_PLAN), RL13_PLAN=coopHash(RL13_PLAN)),
                 arms=RL16_ARMS, runs=[...], reused=..., evaluation=..., analyses=..., hypotheses=..., claimRules=...,
                 nboot=2000, ci=0.95, alpha=0.05, exploratory=True)
```

`rl16Suite` checks that the main level has 15 board seeds (900-904, 930-939) and raises otherwise.

## `rl16_report`

```python
def runValues(rows12, rows13, rows16, metric) -> {name: value}   # mean over the run's main boards; names as RL16 (individual_s1, ...)
def boardValues(rows12, rows13, rows16, metric) -> {name: {board seed: value}}
def permTest(a, b) -> dict(diff, p)                              # exact; itertools.combinations over the pooled runs
def signFlip(x) -> dict(mean, p)                                 # exact; itertools.product over signs
def hierBoot(groups, stat, nboot=2000, seed=0) -> [lo, hi]       # groups: {arm: {run: {board: value}}}
def rl16Summaries(rows12, rows13, rows16) -> S
def writeRL16(path, S, meta) -> path
def figRL16(out, S) -> path                                      # rl16.png
def syntheticRows(seed=0, ...) -> (rows12, rows13, rows16)      # known effects, for tests and the quick demo
```

**Missing values.** Boards with no solves have `soloShare` nan; run values use the nan-aware mean, and the bootstrap skips nan boards.

**Rows and names.** `rows12` = `rl/eval/runs.csv` (models `warm`, `individual` at levels `<model>|main`); `rows13` = `rl/eval_p13/runs.csv` (`indpen_s1`, `indpen_s2`); `rows16` = `rl/eval_p16/runs.csv` (the six new adapters). `runValues` renames `individual` to `individual_s1` (as `rl_report.renameModel`) and refuses to proceed unless all nine runs and the warm start have 15 boards each.

**Permutation test.** Pool the run values of a (n_a) and b (n_b); for every subset of size n_a as "a", compute mean(a') - mean(b'); p = share of subsets with a statistic at least the observed one (ties count), so complete separation of 5 against 4 gives 1/126.

**Sign flip.** For gains x_1..x_n, p = share of the 2^n sign patterns whose mean is at least the observed mean; five positive gains give 1/32.

**Hierarchical bootstrap** (measured coverage 0.90 for a nominal 0.95 with 4-5 runs per arm; descriptive). For each draw: within each arm, resample its runs with replacement; within each resampled run, resample its boards with replacement and take the mean; compute `stat` on the resulting run values (a difference of arm means, or a mean gain). Percentile interval, 2000 draws, `default_rng(seed)`.

**Summaries.** `S['runs'][name] = {sharePerHeld, soloShare, welfare, gain}`; `S['hyp']['H16_k'] = dict(diff or mean, p, pHolm (H16-1..3), ci, supported)`; `S['claims']` = the claim-rule verdicts (`sharingTested`: H16-1 and H16-2 pass after Holm; `scoreContrastTested`: H16-3 does; `beatsImitation`: H16-4 passes and its interval excludes 0; `driftReplicated`: at least 3 of 4 `individual` run values of `soloShare` above 0.5); `S['spread']` = per arm and metric, the standard deviation over runs and the between-arm difference. Holm via `fix_stats.holmFamily` semantics on the three primary p-values.

**Report.** Provenance (plan hash, commit, GPU hours from the run metrics), the hypotheses table, the per-run table, the claim verdicts in words, descriptive spread; labelled exploratory.

**Figure.** Three panels (`sharePerHeld`, `soloShare`, `welfare`): each run a dot at its arm's row (jittered), the arm mean as a bar, the warm start as a dashed line.

## Colab notebook sections (`nbs/colab_clue_rl.ipynb`)

- **"Phase 16: runs, evaluation and pack in one session"** (`gpu`), one cell:
  ```python
  assert RL16_PLAN['frozen'], 'freeze, commit and push RL16_PLAN before the Phase 16 runs'
  ORDER = list(RL16_RUNS)          # already interleaved: individual_s2, indpen_s3, individual_s3, indpen_s4, individual_s4, indpen_s5
  # 1. training: for each (arm, seed) without final/ or halted.json: stream(trainRL(rl16Config(arm, seed, WARM, RUNS16 / name)))
  #    in a fresh process (Phase 13's `stream` helper); a non-zero exit stops with the resume message
  # 2. evaluation: stream(evalModels(rl16Suite(names), {name: (WARM, RUNS16 / name / 'final')}, OUT / 'eval_p16', ...)
  #    and writeCSV) in a fresh process; adapters already evaluated are read back by evalModels
  # 3. pack: zip runs_p16 (no ckpt-*) and eval_p16 into OUT / 'explRL_rl16.zip' (OUT is MyDrive/explRL_rl on Colab;
  #    Phase 13's explRL_rl.zip is left as it is)
  # 4. print per adapter: main-board welfare, sharePerHeld, soloShare; total GPU hours
  ```
  A halted run is evaluated like any other: the trainer saves `final` at the halt (after a jump halt, the restored weights), as Phase 12's team run; `halted.json` records the step and reason for the report.
- **Configuration cell:** `RUNS16 = OUT / 'runs_p16'`; prints `RL16_PLAN`'s version, `coopHash` and frozen state.
- **Header (first cell):** a Phase 16 item ("one cell, about 20 hours, no manual steps; resumes after a disconnect").
- **Pack cell:** its directory list gains `eval_p16` (`runs_p16` already matches `runs*`); a manual Pack writes the full `explRL_rl.zip`.
- The `stream` helper of Phase 13's batch cell is reused: the Phase 16 cell defines it again if Phase 13's cell was not run in the session.

## `demo_rl16`

- **Quick** (normal tests): synthetic rows for nine runs and the warm start (known effects), through `rl16Summaries`, `writeRL16`, `figRL16`; asserts the report and figure exist and the verdicts match the synthetic truth.
- **Full** (flag `train`): reads `results/multiagent/rl/eval/runs.csv`, `results/multiagent/rl/eval_p13/runs.csv` (the curated copies the preprint uses) and `results/multiagent/rl/colab/eval_p16/runs.csv`; asserts `RL16_PLAN['frozen']`; GPU hours from `runs_p16/*/metrics.jsonl` (rollout plus update seconds); writes `results/multiagent/rl/eval_p16/{report.md, rl16.png, summary.json}`; reruns `tools/incentive_figure.py`. Quick output: `results/multiagent/rl/quick_p16/`.

## `tools/incentive_figure.py`

`ROWS` gains `individual_s2-s4` and `indpen_s3-s5` (read from `eval_p16` when present); the title and caption unchanged except "each training seed shown separately".

## Tests

| Notebook | Checks |
|---|---|
| `rl16_grid` | AC-2 (hashes, `trainSeed`s), AC-3 (6 x 15 cells, main boards only), `RL16_PLAN` keys and hypotheses |
| `rl16_report` | AC-4 (exact p-values on synthetic runs, identical groups p = 1, Holm, bootstrap coverage on simulated data: 200 simulations x 500 draws), the refusal on incomplete rows (AC-5), per-run values on a hand-made row set including a board with no solves |
| `demo_rl16` | quick end to end |
| `colab_clue_rl` | offline parts only (the new cells are `gpu`) |
