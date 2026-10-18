# Design (high level): Phase 16

Part of [README.md](README.md); requirements in [requirements.md](requirements.md); details in [design-low-level.md](design-low-level.md).

## Components

| Component | New / changed | Role |
|---|---|---|
| `nbs/rl16_grid.ipynb` -> `explRL/rl16_grid.py` | new | `RL16_ARMS`, `RL16_RUNS`, `RL16_REUSED`, `rl16Name`, `rl16Config`, `rl16Suite`, `RL16_PLAN` |
| `nbs/rl16_report.ipynb` -> `explRL/rl16_report.py` | new | `runValues`, `permTest`, `signFlip`, `hierBoot`, `rl16Summaries`, `writeRL16`, `figRL16` |
| `nbs/colab_clue_rl.ipynb` | changed | one new section, "Phase 16: runs, evaluation and pack in one session" (one cell, fully automatic); configuration cell and header updated; the Pack cell's list gains `eval_p16` |
| `nbs/demo_rl16.ipynb` | new | quick (synthetic), full (Colab outputs, flag `train`): summaries, report, figure |
| `tools/incentive_figure.py` | changed | every run of `individual` and `indpen` as its own row |
| `nbs/demo_multiagent.ipynb` | changed (T7) | a Phase 16 section in `REPORT.md` |

Unchanged: `clue_rl` (the trainer already takes `trainSeed` and every override used), `coop_grid`, `rl_report`, `clue_roll.evalModels`.

## Data flow

```
Mac: freeze RL16_PLAN -> commit -> push (Colab installs from GitHub)
Colab (A100), one cell, no manual steps: warm_model -> 6 runs (rl16Config, trainRL; one process each, interleaved)
              -> runs_p16/<name>/final -> evalModels(rl16Suite) in its own process -> eval_p16/runs.csv
              -> explRL_rl16.zip on Google Drive (MyDrive/explRL_rl/)
Mac: download the zip from Drive; unzip into results/multiagent/rl/colab/ -> demo_rl16 full:
     rl/eval/runs.csv (warm, individual_s1) + rl/eval_p13/runs.csv (indpen_s1, s2) + rl/colab/eval_p16/runs.csv (6 new)
     -> runValues -> rl16Summaries (tests, intervals, claim verdicts) -> report.md, rl16.png
     -> incentive figure, REPORT.md, preprint
```

## Key decisions

- **Exact reuse.** The new `individual` arm reproduces Phase 12's v2 individual configuration byte for byte (same hash), so that run is seed 1 and only three new `individual` seeds are trained. `indpen` reuses `RL13_ARMS['indpen']`, so seeds 1-2 carry over.
- **Run-level statistics.** Every test treats the training run as the unit; exact permutation and sign-flip tests suit 4-5 runs per arm, and their smallest attainable p-values are stated in the plan. Boards enter only through the hierarchical interval.
- **Claims decided by rules written before the runs.** The plan states which wording each outcome allows, including the outcome that the Phase 12 drift does not replicate.
- **One automatic batch.** Training, evaluation and packing run from one cell, each step in a fresh process (GPU memory, vLLM's engine included, is freed between steps); every step skips what is already done, so a disconnect costs one restart and no lost work. The interleaved order keeps both arms balanced if the batch is cut short.
- **Main boards only.** The claims concern main-board behaviour; skipping the generalisation, liar and cross-play cells keeps the evaluation under an hour.
- **Separate modules.** `coop_grid` and `rl_report` stay as they are; the new modules import from them.

## Gates

1. `RL16_PLAN` frozen and committed, then pushed, before any Phase 16 run (the Phase 16 cell asserts it).
2. The Mac analysis runs only on the full set of nine runs plus the warm start.
3. No API calls; no key on Colab.
