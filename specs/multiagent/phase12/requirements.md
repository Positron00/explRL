# Requirements: Phase 12, training agents to work together

Part of [README.md](README.md) (plan and decisions P12-1 to P12-8). Builds on Phase 11 (the clue board, its channels, text interface, runs and training package).

Terms used below.

- **Track A:** better instructions and channels for Claude Haiku 5.5 (API, no training).
- **Track B:** RL training of a small open-weight model so that a team of copies of it shares and uses clues.
- **Policy:** anything that turns a batch of prompts into reply texts: a scripted function (tests), Claude through the Phase 10 client, or a local open-weight model (`LocalPolicy`).
- **Slot:** an agent position on a board (agent 0 to N - 1); a slot is driven by a policy or by a scripted member (a liar).
- **Notes memory:** each turn's prompt holds the rules, the agent's latest note and the current observation (Phase 10 memory `'notes'`); **full memory** holds every past turn's summary instead of the note (Phase 10 `'full'`, used by Haiku in Phase 11).
- **Warm start:** supervised fine-tuning on the rule agent's moves before RL; the **warm-start model** is the base model with that adapter merged in.
- **Group:** the G rollouts of one board seed within an RL step; a slot's **advantage** is its return minus the group's mean return for that slot, divided by the group's standard deviation.
- **Solo solve:** a first correct answer submitted while the solver's known clues left more than one candidate (a solve by trial and error, not by information).
- **Follow share:** among an agent's opens under the coordinator, the share that opened the subtask the coordinator suggested in that turn's observation.

## Functional requirements

### Part A: instructions and channels (Track A)
- **FR-A1** `TextClueEnv(board, hint=None, showOpen=False)`: `hint='follow'` adds to the rules that the coordinator sees every shared clue and that its suggestion is usually the best subtask to open; `showOpen=True` adds an observation line listing each teammate's open subtask. Defaults leave the rules and observations unchanged.
- **FR-A2** `ClueLead(n, passPooled=False)`: with `passPooled=True`, `suggest(i, board)` also passes agent `i` every clue the coordinator has pooled for the suggested subtask (as routed clues, so they are known and shown). Default unchanged.
- **FR-A3** The options travel in `cfg.world` (`hint`, `passPooled`, `showOpen`); `clueSetup` and `runClue` pass them on; cells without them are unchanged, so all Phase 11 outputs stay byte-identical.
- **FR-A4** `trackAGrid()` (study `coopA`): A1 (`hint='follow'`) and A2 (`passPooled=True`) on the coordinator channel, A3 (`showOpen=True`) on the blackboard and the coordinator, each at N {4, 8} x seeds 900-904, 40 turns, Haiku, the Phase 11 settings (9 600 calls); `trackAPilotGrid()` (study `coopAPilot`): the same four (variant, channel) pairs at N = 4, seed 1100, 30 turns (480 calls). Cells run through `runWorkload(..., run=runClueAny)`; `TRACKA_PLAN` is frozen before the Track A main runs.

### Part B: rollouts and policies (Track B)
- **FR-B1** `ClueEpisodes` gains `seeds=None` (an explicit board seed per batch entry, repeats allowed, so a group plays the same board), `scripted=None` (a map slot -> member factory; scripted slots act on the board directly, as in Phase 11, and are skipped in the returned turns), `text=None` (the `TextClueEnv` options), `passPooled=False` (the coordinator option) and a per-board record of the last text turn (`last`); defaults unchanged. `teacherAction` gains `share='needed'` (default unchanged).
- **FR-B2** `renderPrompt(env, obs, memory='notes', notes='', past=(), framing='own')` returns `(system, blocks)` identical to what `LLMMember` sends for the same state (memory `'notes'` or `'full'`); `parseReply(text)` returns the first JSON object in a reply, or `None`.
- **FR-B3** `rollout(cfg, seeds, policies, scripted=None, memory='notes', keepPrompts=False)` plays a batch of boards to the end with one policy per slot (a dict slot -> policy, or one policy for all) and a memory per slot (`'notes'` or `'full'`, one for all or a dict); framing comes from `cfg.framing`, the reward scheme and the Track A options from `cfg.world`; batching all pending turns of the same policy in one call; it returns the boards, per-board turn logs in the Phase 10 log format (with `usage` and `cost`), per-slot returns under the board's reward scheme (delivered plus pending at the end) and, with `keepPrompts`, each turn's prompt (for training). With the same replies, its boards and rows equal those of `runClue`.
- **FR-B4** Policies: `scriptedPolicy(fn)`; `claudePolicy(client)` (the Phase 10 `LLMClient` with the clue schema; requests of one batch sent concurrently; cache and budget as Phase 10); `LocalPolicy(model, adapter=None, device='auto', maxNew=160, temperature=1.0, seed=0, cache=None, ...)` (Hugging Face model, LoRA adapter optional; device cuda, mps or cpu; batched generation; vLLM on cuda when installed; every request sampled independently, so repeated prompts in one batch give different replies; an optional response cache keyed by model, adapter hash, prompt, sampling seed and the prompt's occurrence in the batch). GPU libraries are imported only inside `LocalPolicy` and the training functions.
- **FR-B5** `coopRows(cfg, ro, honest)` (`ro` a rollout's result): one row per board with the Phase 11 columns (`clueMetrics` and `llmStats`) plus `soloSolves`, `soloShare` (solo solves / solves), `wrongPerSolve`, and `followShare` (coordinator runs).

### Part C: warm start (Track B)
- **FR-C1** `sftExamples(seeds, sizes=(1, 2, 4), turns=20)`: plays boards through `ClueEpisodes` with the rule agent in every slot (`teacherAction`, `share='always'`, blackboard for N >= 2, no channel for N = 1), renders each turn's prompt with `renderPrompt` (notes memory), and returns chat examples (system, user, assistant) for every turn; the assistant reply is the teacher's action with its note first: for a submit, the candidate list from the known clues (the rules' method); otherwise a short reason.
- **FR-C2** `trainSFT(cfg, examples)` fine-tunes a LoRA adapter on those examples (loss on the reply only) and saves it; `mergeAdapter` writes the warm-start model.
- **FR-C3** `warmCheck(policy, seeds=range(1200, 1220), turns=30)`: N = 1 boards; returns the solve rate (solved / opened) and the invalid-reply rate; it passes with solve rate >= 0.8 and invalid < 0.05.

### Part D: RL (Track B)
- **FR-D1** `RLConfig`: model (the warm-start model's path), scheme (`individual`, `team`, `credit`), N = 4, channel blackboard, turns = 10, seeds per step = 8, group size G = 4, steps = 40, learning rate, KL weight, LoRA rank, `maxNew`, temperature, format penalty, training seed, board seeds from 10 000, checkpoint interval, output directory, device, `perRole` (one adapter per agent slot instead of one shared adapter; the optional ablation), `gradCkpt` (gradient checkpointing), `turnFraction` (the share of each step's turns with a nonzero advantage that the update trains on, drawn with a seed per step; P12-9) and the stopping rule's thresholds (`haltInvalid`, `haltRun`, `haltKL`).
- **FR-D2** `groupAdvantages(returns)`: per board seed and slot, (return - group mean) / (group std + 1e-6), zero when the group's returns are equal.
- **FR-D3** `trainRL(cfg)`: per step, roll out seeds x G boards with the current policy, add the format penalty to invalid turns (training reward only), compute advantages, draw `turnFraction` of the turns with a nonzero advantage (an unbiased, cheaper estimate of the same gradient), and take one policy-gradient step on their reply tokens (each turn weighted by its slot's advantage, mean over tokens) with a KL penalty to the warm-start model (the same weights with the RL adapter off); log metrics per step (mean training return, welfare, shares per held clue, invalid rate, solo share, loss, KL, samples, tokens, rollout and update time) and, at checkpoint steps, that step's turn logs.
- **FR-D4** Checkpoints every `ckptEvery` steps and at the end (adapters, optimizer state, step, configuration hash); `trainRL` resumes from the latest checkpoint in its output directory and refuses one written by another configuration. Sampling seeds follow from the step, so no random state needs saving. Each run records its configuration and library versions.
- **FR-D5** Stopping rule (P12-9): a run stops, saves a checkpoint and writes `halted.json` (step, reason) when the invalid-reply rate exceeds `haltInvalid` (0.10) for `haltRun` (3) steps in a row, or the mean KL exceeds `haltKL` (0.5); a halted run is never resumed silently, and the report states where it stopped.

### Part E: evaluation and report
- **FR-E1** `evalSuite(models)` returns the evaluation cells of `RL_PLAN`; `runEval(cells, policyFor)` runs them with `rollout` and `coopRows`, rows in the Phase 11 columns plus the Part B columns, keyed with `cellRow`.
- **FR-E2** `coop_report`: Track A summaries and figures (follow share and solo solves from the turn logs, since Track A rows keep the Phase 11 columns). `rl_report`: Track B summaries (main, information use, solo solves, generalisation, follow share, cross-play, liar; paired on board seed) against the saved Phase 11 Haiku and rule-agent rows; training curves; `report.md` with provenance first (plan hash, commit, models, adapters, GPU time, API cost).
- **FR-E3** Notebooks: `demo_coop.ipynb` (Track A: quick with the fake client; pilot and main with `--flags llm`), `colab_clue_rl.ipynb` (Colab: set-up, pilot, warm start, RL runs; `--flags gpu`), `demo_rl.ipynb` (Mac: quick offline checks; debug run with the 0.5B model, warm-start check, evaluation, cross-play and report with `--flags train`). The module notebooks' own `train` cells use a tiny random model (`tiny_model`, no download).

### Packaging
- **FR-F1** A `[train]` extra: `torch`, `transformers`, `peft`, `accelerate`, `tokenizers`, and `vllm` on Linux only (environment marker). The core package and normal tests need none of them; on the Mac, the extra goes into a separate environment so the project environment stays without `torch` (AC-1).
- **FR-F2** The Colab notebook installs the package from GitHub, mounts Google Drive for outputs, needs no API key and nothing from the repo's `results/`; outputs are zipped for download to `results/multiagent/rl/` on the Mac.

## Analysis plans (frozen; exploratory)

`TRACKA_PLAN` (frozen before the Track A main runs):

| Item | Definition |
|---|---|
| Variant effect | Per variant, channel, N: welfare minus the Phase 11 cell (same channel, N, seed), paired on seed, bootstrap CI |
| Coordinator gap | Per coordinator variant and N: welfare minus the Phase 11 blackboard cell, paired |
| Mechanism | Follow share (A1, A2 on the coordinator), shares per held clue, redundant shares, solo solves |

`RL_PLAN` (frozen after the Colab pilot and the warm-start check, before the main RL runs):

| Item | Definition |
|---|---|
| Main | N = 4, blackboard, seeds 900-904 and 930-939, 40 turns: welfare and pooled-bound share of the untrained, warm-start and three RL models |
| RL gain | Each RL model minus the warm-start model, paired on board seed |
| Reward schemes | credit - individual, team - individual, credit - team, paired on board seed |
| Against Phase 11 | Each model minus Haiku and minus the rule agents on seeds 900-904 (saved rows) |
| Information use | Shares per held clue, redundant shares, share-to-use time, guesses, solo share, wrong per solve |
| Generalisation | N = 8 blackboard; N = 4 messages; N = 4 coordinator (seeds 900-904): welfare vs the Phase 11 Haiku cells; follow share |
| Cross-play | N = 4 blackboard, seeds 900-904: one model agent with three Haiku agents, and one Haiku agent with three model agents: welfare vs all-Haiku |
| Liar | N = 4, blackboard and messages, seeds 900-902, one scripted liar: honest welfare lost against the same model's clean main boards (seeds 900-902), and its blackboard-minus-messages sign (H3) |
| Per-role ablation (optional) | Credit reward, main boards: per-role adapters minus the shared adapter, paired on board seed |

Generalisation, cross-play and liar run for the warm-start and RL models; training-seed spread is reported when a second seed exists.

## Quality requirements

- **NFR-1 Frozen results:** Phase 5-9 baselines identical; Phase 10, follow-up and Phase 11 cached reruns byte-identical.
- **NFR-2 Offline by default:** normal tests need no network, API key, `anthropic`, `torch` or GPU; model runs sit behind the `gpu` and `train` flags; live API sections behind `llm`.
- **NFR-3 Cost:** API spend through `runWorkload` or the Phase 10 client with the existing $150 API cap; GPU spend under the separate $150 cap, each Colab run a few hours (P12-1); GPU hours and costs recorded per run.
- **NFR-4 Reproducibility:** fixed board seeds, sampling seeds and training seeds; API and local replies cached, so evaluation reruns are byte-identical; training runs are reproducible up to GPU non-determinism (recorded, not required).
- **NFR-5 Secrets:** as Phase 10; on Colab no key is needed; cross-play runs on the Mac with the key from `.env.local`.
- **NFR-6 Data:** Claude's outputs are never used as training data (P12-6).
- **NFR-7 Size, style:** each module under 200 lines; nbdev notebooks with tests.

## Acceptance criteria

Normal tests (offline):

- **AC-1 Regression:** NFR-1; the full suite passes with and without `anthropic` and without `torch`.
- **AC-2 Track A options:** defaults leave rules, observations and rows unchanged; `hint` adds the sentence; `showOpen` lists teammates' open subtasks; `passPooled` passes pooled clues with the suggestion and they become known; a fake-client run works for each variant; grid sizes and call estimates.
- **AC-3 Rollouts:** explicit seeds (repeated within a batch) give identical boards; scripted slots act as in Phase 11; prompts equal `LLMMember`'s for notes and full memory; with a scripted reply function, `rollout` rows equal `runClue` rows for the same seed; returns include pending credit; batching calls each policy once per round of pending turns.
- **AC-4 Warm-start data:** every example's reply parses to the teacher's action; submit notes list exactly the candidates; replaying the examples' replies solves every N = 1 board the teacher solves.
- **AC-5 RL logic:** advantages on hand-made returns (including equal returns -> 0); the format penalty only in the training reward; zero-advantage turns skipped; the share of turns trained on is a seeded subset of the right size; the stopping rule on hand-made histories; `RL_PLAN` and `TRACKA_PLAN` hashes; evaluation cells; report on synthetic rows.

Model checks (flags `train` on the Mac, `gpu` on Colab):

- **AC-6 Mac debug:** the 0.5B model runs as `LocalPolicy` on mps; a warm start of a few steps and two RL steps run with finite loss; resuming from a checkpoint continues at the next step with the same adapter; a checkpoint of another configuration is refused (`demo_rl`). The same paths also pass on the tiny random model on cpu and mps (`train` cells of `local_policy`, `clue_sft`, `clue_rl`).
- **AC-7 Colab pilot:** from a clean runtime the notebook installs, runs a few warm-start and RL steps with the 3B model, and records step time and memory; with the final settings (the RL speed check, P12-9), the step time keeps each main run to a few hours, before `RL_PLAN` is frozen.

Checks on runs:

- **AC-8 Track A:** pilot invalid rate under 5%; `TRACKA_PLAN` frozen and committed before the main runs; runs within the API cap; a cached rerun is byte-identical and free.
- **AC-9 Warm start:** the 3B warm-start model passes `warmCheck` (on the Mac); else the 7-8B check (P12-2) or the user decides.
- **AC-10 RL runs:** `RL_PLAN` frozen and committed first; three reward schemes trained, each in one Colab session of a few hours; curves, GPU hours and cost recorded; total GPU spend under $150.
- **AC-11 Evaluation:** every `RL_PLAN` item reported, labelled exploratory; a cached rerun of the evaluation is byte-identical.

## Out of scope

- Training Claude, or training on Claude's outputs.
- Changing the clue board's settings or scoring.
- Full-weight fine-tuning; more than one training seed per scheme unless the first shows a difference; models above 8B.
- LLM coordinators or LLM liars.
