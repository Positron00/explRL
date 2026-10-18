# Running Phase 16 (more training seeds for the incentive result)

Plan, decisions and results: [README.md](README.md). Builds on Phase 13: [../phase13/RUN.md](../phase13/RUN.md).

Status 2026-10-17: T1-T3 implemented and tested offline; next T4 (freeze `RL16_PLAN`, commit, push), then the Colab batch.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command; none needs a network, a key, a GPU, `anthropic` or `torch`:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/rl16_grid.ipynb` | configuration hashes and seeds (AC-2), the evaluation grid (AC-3), the plan | ~2 s |
| `nbdev-test --n-workers 0 nbs/rl16_report.ipynb` | exact tests, Holm, hierarchical bootstrap, refusal on incomplete rows (AC-4, AC-5) | ~10 s |
| `nbdev-test --n-workers 0 nbs/demo_rl16.ipynb` | quick: synthetic runs end to end | ~5 s |
| `nbdev-test --n-workers 0` | full suite | ~95 s |

## Runs, in order

| Step | Where | Command | Cost |
|------|-------|---------|------|
| T4 freeze | Mac | `RL16_PLAN['frozen'] = True` in `nbs/rl16_grid.ipynb`, export, commit, **push** (Colab installs from GitHub); record the commit and `coopHash(RL16_PLAN)` in the README | none |
| T5 batch | Colab (A100), one session, Pro+ background execution or a connected tab | open [colab_clue_rl](https://colab.research.google.com/github/Positron00/explRL/blob/main/nbs/colab_clue_rl.ipynb); run set-up (mounts Drive) and configuration; then the one cell "Phase 16: runs, evaluation and pack in one session": six runs, evaluation and packing with no manual step in between. After a disconnect: restart, set-up, configuration, the same cell (finished runs and evaluated adapters are skipped) | about 20 GPU hours, about $26 |
| T6 analysis | Mac | download `MyDrive/explRL_rl/explRL_rl16.zip`; `unzip -o explRL_rl16.zip -d results/multiagent/rl/colab/`; `nbdev-test --n-workers 0 --cell-timeout 0 --flags train nbs/demo_rl16.ipynb` | none |

## Artifacts

- Colab (Google Drive, `MyDrive/explRL_rl/`): `runs_p16/<arm>_s<seed>/` (config, metrics, final adapter), `eval_p16/runs.csv` and turn logs, all in `explRL_rl16.zip`.
- Mac: `results/multiagent/rl/colab/{runs_p16, eval_p16}/`; `results/multiagent/rl/eval_p16/{report.md, rl16.png, summary.json}` (quick: `quick_p16/`); `results/multiagent/report/incentives.png`.
