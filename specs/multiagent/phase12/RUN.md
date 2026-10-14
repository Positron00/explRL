# Running Phase 12 (training agents to work together)

Plan, decisions and results: [README.md](README.md). Builds on Phase 11: [../phase11/RUN.md](../phase11/RUN.md).

Status 2026-10-13: Track A done (pilot and main); the Mac debug run done; the Colab runs next. Measured times and costs are added here as the runs happen.

## Prerequisites

- **Offline tests and Track A:** as Phase 11 (`pip install -e ".[dev]"`, `nbdev-export`; for Track A's live runs also `pip install -e ".[llm]"` and the API key in the environment or the git-ignored `.env.local`).
- **Model work on the Mac:** a separate environment, so the project's stays without `torch` and the offline suite keeps proving that (AC-1): `python -m venv .venv-train && .venv-train/bin/pip install -e ".[train,dev,llm]"` (PyTorch, Transformers, PEFT; no vLLM on macOS); run the `train` sections with `.venv-train/bin` first on `PATH`. About 30 GB of free disk (the 3B model is about 6 GB, the 0.5B about 1 GB, plus PyTorch and the merged warm-start model).
- **Colab:** an A100 runtime (paid plan); the notebook installs the package from GitHub, so push the code first.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command; none needs a network, a key, `anthropic` or `torch`:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/clue_text.ipynb` | Track A options in the rules and observations; pooled clues passed with a suggestion (AC-2) | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_runs.ipynb` | Track A options from `cfg.world`; rows without them unchanged (AC-2) | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_train.ipynb` | episodes with explicit seeds and scripted slots, the teacher | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_policy.ipynb` | prompts equal `LLMMember`'s (notes and full memory), reply parsing, policies | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_roll.ipynb` | rollout rows and turn logs equal `runClue`'s for the same replies (every channel, liars, options); batching; pending credit; `coopMetrics` (AC-3) | ~2 s |
| `nbdev-test --n-workers 0 nbs/local_policy.ipynb` | device choice, cache keys, prompt encoding, cache replay and independent samples with stubs | ~1 s |
| `nbdev-test --n-workers 0 nbs/clue_sft.ipynb` | warm-start examples: replies parse, notes list the candidates, replaying them reproduces the teacher; the warm-start check (AC-4) | ~3 s |
| `nbdev-test --n-workers 0 nbs/clue_rl.ipynb` | group advantages, format penalty, samples, seeds, run identity, per-role micro-batches (AC-5) | ~1 s |
| `nbdev-test --n-workers 0 nbs/coop_grid.ipynb` | Track A grids and call counts; the evaluation suite's turn counts; plan hashes | ~1 s |
| `nbdev-test --n-workers 0 nbs/coop_report.ipynb` | Track A summaries on synthetic rows; log-based metrics agree with the board's | ~2 s |
| `nbdev-test --n-workers 0 nbs/rl_report.ipynb` | Track B summaries on synthetic rows with known differences; report and figures | ~2 s |
| `nbdev-test --n-workers 0 nbs/demo_coop.ipynb` | quick: every Track A variant with the fake client, identical at 1 and 8 processes, key scan | ~3 s |
| `nbdev-test --n-workers 0 nbs/demo_rl.ipynb` | quick: the evaluation and report pipeline with scripted policies | ~3 s |
| `nbdev-test --n-workers 0` | full suite (also without `anthropic`; the project venv has no `torch`) | ~2 min |

From the training environment, `nbdev-test --n-workers 0 --flags train nbs/{tiny_model,local_policy,clue_sft,clue_rl}.ipynb` runs the model code on a tiny random model (no download, under a minute): generation on cpu and the Apple GPU, a warm start whose loss falls, RL steps with per-role adapters, resume and refusal.

## Runs, in order

| Step | Where | Command | Cost |
|------|-------|---------|------|
| T4 Track A pilot (480 calls) | Mac | `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --flags llm nbs/demo_coop.ipynb` (the pilot section runs; the main section stops until `TRACKA_PLAN` is frozen) | measured: $0.11, 389 s |
| T4 freeze | Mac | set `TRACKA_PLAN['frozen'] = True` in `nbs/coop_grid.ipynb`, export, commit; record the commit and hash in the README | none |
| T5 Track A main (9 600 calls) | Mac | the same command, `--cell-timeout 0` | measured: $2.17, 1 027 s at 32 processes |
| T7-T9 debug (0.5B) | Mac | from `.venv-train`: `nbdev-test --n-workers 0 --cell-timeout 0 --flags train nbs/demo_rl.ipynb` (debug section; the later sections need the Colab results) | measured: 903 s, peak GPU memory about 8 GB |
| T10 pilot | Colab | open [colab_clue_rl](https://colab.research.google.com/github/Positron00/explRL/blob/main/nbs/colab_clue_rl.ipynb), run set-up, configuration and pilot; record step time, memory and GPU hours | measured: 0.58 GPU hours; RL 631 s per step at the first settings (decision P12-9) |
| T11 warm start | Colab | the warm-start section; then download the zip (pack section) to `results/multiagent/rl/colab/` | $1-3 |
| T11 warm-start check | Mac | `demo_rl` warm-check section (`--flags train`, from `.venv-train`) | measured: passed (solve rate 0.93, invalid 0), 661 s |
| T10 RL speed check | Colab, start of session 2 (after Runtime -> Restart session; never rerun the pilot) | set-up, configuration, the RL speed-check cell; send the printout; the step count is set in `RL_PLAN`, which is then frozen, committed and pushed | measured: 166 s per step, 50.3 GB; 60 steps chosen; `RL_PLAN` frozen at `d8467f2` (hash `708dfc435c1f`) |
| T12 RL runs, v1 | Colab | one session per scheme | measured: 2.26, 2.72, 2.71 GPU hours; the policy barely moved (P12-10) |
| T12 learning-rate pilot | Colab, session 3 (restart first) | set-up, configuration, the learning-rate pilot cell; send the printout; the rates are set in `RL_PLAN` v2, which is then frozen, committed and pushed | measured: about 1.6 GPU hours; `RL_PLAN` v2 frozen at `304b955` (hash `4d1ea0078a6e`) |
| T12 RL runs, v2 | Colab | one session per scheme (restart first): set `SCHEME`, run the RL section (writes `runs_v2/`; a progress bar with the ETA and one line per step: learning rate, step KL, KL to the warm start, welfare, invalid replies, undone or not); pack and download after the last | about 8.5 GPU hours |
| T13 evaluation and report | Mac | `EXPLRL_LLM_LIVE=1 nbdev-test --n-workers 0 --cell-timeout 0 --flags train nbs/demo_rl.ipynb`, with GPU hours and cost in `results/multiagent/rl/gpu.json` | API under $1 |

API spend goes through the Phase 10 client and ledger (`results/multiagent/llm/`) under the $150 API cap; GPU spend has its own $150 cap (decision P12-1).

## Artifacts

- `results/multiagent/coop/{quick,pilot,full}/` (Track A): `runs.csv`, `turns.jsonl`, `timing.jsonl`, `metrics.json` (and `_live` copies after the live run), `report.md`, `coopA.png`.
- `results/multiagent/rl/` (Track B): `colab/` (the unpacked Colab zip: warm-start adapter, RL adapters, training metrics, configurations with library versions, turn logs of the checkpoint steps), `debug/`, `warm/check.json`, `eval/` (`runs.csv`, `turns/`, `report.md`, `coop_main.png`, `coop_info.png`, `coop_gen.png`, `coop_curves.png`), `cache/` (local replies), `gpu.json`.
- Google Drive `MyDrive/explRL_rl/`: everything Colab writes, including checkpoints and the merged warm-start model (kept there, not downloaded).

## Regression

```sh
tools/phase9_baseline.sh "$WORKTREE" /tmp/explRL_p9   # on a worktree of the code: identical to results/multiagent/baseline_phase9
```

Phase 10, follow-up and Phase 11 full workloads rerun from the response cache only give byte-identical `runs.csv` and `turns.jsonl` (checked 2026-10-13 against the T1 reference hashes, with the Track A options in place).

## Related

- Phase 11 run guide: [../phase11/RUN.md](../phase11/RUN.md)
- Multi-agent plan: [../README.md](../README.md)
- Notebooks: [nbs/demo_coop.ipynb](../../../nbs/demo_coop.ipynb), [nbs/colab_clue_rl.ipynb](../../../nbs/colab_clue_rl.ipynb), [nbs/demo_rl.ipynb](../../../nbs/demo_rl.ipynb)
