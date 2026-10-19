# Requirements: Phase 17, RL that makes larger teams pay off

Part of [README.md](README.md) (plan and decisions P17-1 to P17-7). Builds on Phases 12-16: `clue_rl` (trainer, `RLConfig`), `rl_adv` (returns, advantages, samples), `rl_torch` (update, checkpoints), `rl_control` (controller, stopping rules), `local_policy` (vLLM/HF sampling), `clue_roll` (`rollout`, `evalModels`), `coop_grid` (`evalCell`, `RL_PLAN`), `rl16_report` (exact tests, hierarchical bootstrap).

Terms: as Phase 16 ([../phase16/requirements.md](../phase16/requirements.md)); in addition:

- **Recipe:** the training settings chosen by the pilot (constrained replies, updates per batch, clip, KL penalty, per-step target, turns).
- **Training mix:** for `r17mix`, each step's 8 board seeds: the first 4 with 4 agents, the last 4 with 8; within each team size, `round(liarShare x 4)` boards (the first ones; 1 of 4 at `liarShare` 0.25) carry `N // 4` scripted liars in the first slots. Scripted liars write no text turns, so they are never trained; their returns enter no advantage group that matters (an honest slot is compared only with itself across replays).
- **Gain at N:** a run's mean welfare at team size N minus the warm start's, on the same boards (clean boards unless stated).
- **Honest loss at N:** welfare of honest agents on clean boards minus with liars, same N and board seed (as Phase 14).
- **Claim:** a file `runs_p17/<run>/claim.json` naming the Colab account (`HOST`) that trains the run.

## Functional requirements

### Part A: evaluation grid and step 0
- **FR-A1** `teamSizeSuite(models)`: per model, clean boards at N 4 (the 15 main seeds), N 8, 16, 32 (seeds 900-909), and liar boards (`nLiar = N // 4`) at N 4, 8, 16, 32 (seeds 900-909); 40 turns, blackboard, notes memory; levels `<model>|n<N>` and `<model>|n<N>liar`.
- **FR-A2** Step 0 (models not yet on Drive are skipped with a message and added on a rerun; the zip is written when all 15 are evaluated): `teamSizeSuite` for the warm start and every Phase 12-16 adapter (Phase 12 `individual`, `team`, `credit`; Phase 13 `credit_s2`, `indpen_s1-2`, `credturn_s1-2`; Phase 16 `individual_s2-4`, `indpen_s3-5`); a Colab cell (A100 or L4) writing `eval_p17s0/`, resumable per model.

### Part B: the new trainer
- **FR-B1** `RL17Config(RLConfig)` adds, with defaults that reproduce `trainRL`'s algorithm: `guided` (constrained replies), `epochs` (updates per batch), `clip` (ratio clip; None = no ratio), `mixN` (team sizes and their shares per step, a tuple of pairs, default `((4, 1.0),)`), `liarShare` (share of boards per team size with `N // 4` liars), `lrFixed` (no controller). `configHash17` leaves these fields out at their defaults (as `runFields` does for Phase 13's fields), so an `RL17Config` at defaults has the same hash as the equal `RLConfig`; Phase 12-16 hashes unchanged.
- **FR-B2** `trainRL17(cfg)` (`rl17_train`, with the step's pieces in `rl17_update`): per step, the training mix's rollouts (one `rollout` per team size, the same board seeds for every configuration at a given step), returns and group advantages per team size (as `rl_adv`, honest slots only), `epochs` passes of the clipped-ratio policy-gradient update with the KL penalty, the per-step controller (unless `lrFixed`), the stopping rules and checkpoints as `trainRL`.
- **FR-B3** Constrained replies: `LocalPolicy(..., guided='model')` samples replies under the reply JSON schema in the model's own key order (`GUIDED_SCHEMA`: notes, action, target, answer, clue; vLLM structured outputs); `guided=True` keeps the schema's order (pilot v1 only); the HF engine refuses both.
- **FR-B4** At the defaults, one `trainRL17` step gives the same samples and the same update as `trainRL` (flag `train`: a tiny randomly initialised Qwen2 model built locally with the warm start's tokenizer from `results/multiagent/rl/warm_model`, HF engine, CPU or MPS; no download).

### Part C: plans, grids, claiming
- **FR-C1** `PILOT17_PLAN` (frozen before the pilot): the four configurations, 30 steps, seed 1, the training mix of `r17mix`, the selection rule (README), the measures (invalid share, halts, training welfare, seconds per step).
- **FR-C2** `RL17_PLAN` (frozen after the pilot, before the main runs): the chosen recipe (`chosenRecipe(choice, p17dBase)` from the pilot's `selection.json`, printed by `demo_rl17`), arms `r17mix` (seeds 1-8) and `r17four` (seeds 1-5), 200 steps, the projected hours and the user's confirmation, the evaluation grid, hypotheses H17-1 to H17-5 with tests and families, claim rules, the rule for cutting boards per size if evaluation runs out of memory.
- **FR-C3** Run claiming (main runs, pilot runs, step-0 models, the pilot's selection and the packing; a folder with progress but no claim counts as held): before training a run the batch cell writes its claim (atomic write, then read back); it skips runs claimed by another `HOST`; `TAKEOVER = [names]` (set by the user) lets a host take over a claimed run; evaluation and packing run only when every run has `final/` (halted runs have it too), and only on the host that wins the evaluation claim (`eval_p17/claim.json`, the same mechanism), so two accounts never evaluate at once. `claim` refuses an empty `HOST`.

### Part D: Colab
- **FR-D1** Sections in `nbs/colab_clue_rl.ipynb`: "Phase 17 step 0" (evaluation only), "Phase 17 pilot" (one cell: four configurations, then the selection printout), "Phase 17 main" (one cell: claimed runs, then evaluation and packing when all runs are done), each resumable; the configuration cell sets `HOST` and `RUNS17`.
- **FR-D1b** Each section is one cell that runs to its end without manual steps (Pro+ background execution); Phase 17 runs checkpoint every step (`ckptEvery` 1, outside the hash), so a session that ends after Colab's limit (about 24 hours) costs at most one step.
- **FR-D2** Zips `explRL_rl17s0.zip`, `explRL_rl17pilot.zip`, `explRL_rl17.zip` on Drive.

### Part E: analysis and docs
- **FR-E1** `rl17Summaries` (refuses rows unless the warm start and every run cover the whole grid, liar boards included): per model and N, welfare, pooled share, honest loss, sharing metrics and invalid share; per run the gains; H17-1 to H17-5 (`signFlip`, `permTest` from `rl16_report`), Holm within families, hierarchical intervals; the scaling curves; references (Haiku from Phases 11 and 14, labelled as a different memory setting).
- **FR-E2** `writeRL17`, `figRL17` (`rl17.png`: welfare, pooled share and honest loss against N for the warm start, each arm's runs and mean, and Haiku as reference; also the summary page's figure); `demo_rl17` (quick: synthetic; full: flag `train`).
- **FR-E3** Results in this README, `REPORT.md`, the preprint where a claim changes, the summary figure and page.

## Analysis plans

`PILOT17_PLAN`: README, pilot table and selection rule. `RL17_PLAN`: README, hypotheses table; Holm within the primary family (H17-1 to H17-3) and the secondary family (H17-4, H17-5) at 0.05; exploratory.

## Quality requirements

- **NFR-1** Phase 5-16 reference outputs and configuration hashes unchanged; `trainRL` untouched.
- **NFR-2** Offline tests need no network, key, GPU or `anthropic`; `torch` only in tests flagged `train`.
- **NFR-3** No API spend.
- **NFR-4** Seeds fixed; resumes exact (as `trainRL`); two hosts never train the same run.
- **NFR-5** Each module under 200 lines.

## Acceptance criteria

- **AC-1** Regression: NFR-1; full suite passes.
- **AC-2** Grid: `teamSizeSuite` sizes, seeds, liar counts and levels; step 0 covers every listed adapter.
- **AC-3** Trainer: FR-B4's equivalence (flag `train`, tiny model); clipped-ratio update matches a hand computation; mixed rollouts give advantages within each team size only; liars' slots never trained.
- **AC-4** Claiming: two simulated hosts on one folder never both train a run; takeover only when listed; evaluation waits for all runs and runs on one host only.
- **AC-5** Plans: `PILOT17_PLAN` frozen before the pilot cell runs; `RL17_PLAN` frozen, with the projected main-run hours recorded and confirmed by the user, before the main cell runs (cells assert the freeze).
- **AC-6** Analysis: exact tests and Holm on synthetic runs with known effects; every `RL17_PLAN` item reported, labelled exploratory.

## Out of scope

Models other than Qwen2.5-3B-Instruct; LLM liars; channels other than the blackboard; Claude runs (Haiku curves are reused); Phase 18's ideas.
