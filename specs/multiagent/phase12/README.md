# Plan: Phase 12, training agents to work together (RL on the clue board)

Status: **code implemented; runs in progress** (2026-10-13). Track A done (pilot, `TRACKA_PLAN` frozen at commit `23ee080`, hash `45258d8a34da`, main runs $2.17; cached rerun byte-identical). Mac debug run done (AC-6). Colab pilot done (RL too slow: 631 s per step; decision P12-9); Colab warm start done; warm-start check passed on the Mac (AC-9). RL speed check done; `RL_PLAN` v1 frozen (commit `d8467f2`, hash `708dfc435c1f`, 60 steps) and run: the three v1 runs barely moved the model, so the plan is amended (P12-10, version 2). Learning-rate pilot done; `RL_PLAN` v2 frozen (commit `304b955`, hash `4d1ea0078a6e`). The three v2 runs done (team halted at step 56). Next: the evaluation on Colab, then cross-play on the Mac (P12-11). Part of the multi-agent plan: [../README.md](../README.md). Builds on [Phase 11](../phase11/README.md), whose clue board was packaged for this phase. Two machines (P12-7, P12-8): **this Mac** (M4 Max) for writing and debugging the training loop with a tiny model, the warm-start check, evaluation and reports; **a standalone Google Colab notebook** for the GPU runs (warm start and RL with a 3B model), each a few hours, under a $150 GPU cap (P12-1).

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the two frozen analysis plans, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions, risks |
| [design-low-level.md](design-low-level.md) | Track A options, episodes, prompts and policies, local models, rollouts, warm start, RL, grids and plans, report, notebooks, packaging |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |
| [RUN.md](RUN.md) | Tests, the runs in order (Mac and Colab), artifacts, regression |

## Goal

Phase 11 measured how Claude Haiku 5.5 teams share information when no agent can solve a subtask alone: a shared board roughly tripled earnings over no sharing, messages faded as teams grew, and a coordinator failed because Haiku ignored it. This phase asks whether cooperation can be **improved**, by two different routes:

- **Track A, better instructions and channels (no training):** change what Claude agents are told and how channels route clues, through the API. This is the only lever for Claude itself, whose weights we cannot train.
- **Track B, learning (weight training):** train a small open-weight model with reinforcement learning (RL) so that a team of copies of it learns to share and use clues.

Together they answer one question: **how much teamwork can good instructions buy, and how much needs learning?**

## How it maps to the role (multi-agent research, Anthropic)

| Role item | What this phase adds |
|---|---|
| Environments and methods to train groups of models to solve problems together | RL on a task no single agent can solve, with checkable rewards |
| Incentives and mechanism design | Individual vs team vs credit reward as training signals: which one teaches agents to share? |
| Harness configurations | Track A: coordinator and channel variants, compared with trained cooperation |
| Novel evals of how teams interact | Held-out boards, unseen team sizes and channels, and playing with unfamiliar teammates (Haiku) |
| Bitter Lesson | Learning vs hand-designed coordination, on the same board and metrics |

## What Phase 11 gives us

| Piece | Fact | Use here |
|---|---|---|
| `ClueBoardEnv`, settings `m = 2, r = 1, R = 30` | Answers checked exactly; no agent holds both clues of a subtask (N >= 2); one clue leaves 2-10 candidates | The training environment, unchanged |
| Reward schemes | `individual`, `team`, `credit` (solver keeps half; the agents whose true shares first supplied its missing clues split the rest; false and repeated shares earn nothing) | The training signal, compared across runs |
| `ClueEpisodes` | A batch of boards stepped one agent-turn at a time; per board, whose turn and its text observation; rewards per scheme | Rollouts for RL and evaluation, extended with explicit board seeds (so a group replays one board) and scripted slots (liars); the rollout code adds the prompt around the observation and collects rewards still pending at the end |
| `TextClueEnv` | Rules text, observations, parsing of JSON replies | The prompt and the action parser, unchanged |
| `teacherAction` | The rule agent's move as a valid JSON reply; it solves every subtask it has all clues for | Supervised warm start |
| `exportTrajectories` | Turn logs as per-agent steps or chat records | Data plumbing for both tracks |
| Results (saved, seeds 900-904) | At N = 4 with the blackboard: rule agents 0.57 of the pooled bound, Haiku 0.45; no channel about 0.13 | Baselines, compared paired on the same boards at no cost |

## Track A: instructions and channels (Claude, API)

Variants run on the Phase 11 main cells (N 4 and 8, seeds 900-904, 40 turns; the coordinator variants on the coordinator channel, A3 on the blackboard and the coordinator), compared paired on seed with the saved Phase 11 rows:

| Variant | Change | Question |
|---|---|---|
| A1 Follow the coordinator | The rules say the coordinator sees all shared clues and its suggestion is usually best | Is the coordinator's failure an instruction problem? |
| A2 Coordinator passes pooled clues | When the coordinator suggests a subtask, it also passes every clue it has pooled for it (a channel change) | Is it a routing problem? |
| A3 Show who works on what | The observation lists the subtasks teammates have open | Do targeted shares replace untargeted ones? |

Each variant is an option whose default leaves Phase 11 unchanged, so the Phase 11 outputs stay byte-identical. Four (variant, channel) pairs x 12 agents (N 4 + 8) x 5 seeds x 40 turns = 9 600 Haiku calls, about **$2.3**, after a pilot of 480 calls (about $0.12), run locally through the existing scheduler and cache, under the existing API cap ($150 in all; $44.29 spent). The API cap and the GPU cap (P12-1) are separate budgets. As in Phase 11, the pilot checks the invalid-reply rate (under 5%), and the comparisons are frozen as an analysis plan (`TRACKA_PLAN`) before the main runs.

## Track B: RL training (open model)

### Model and shared weights

- **Model:** a current small open-weight instruction model of about 3 billion parameters for the main runs (P12-2), and one of about 0.5 billion parameters from the same family for debugging on the Mac (P12-8). Training updates a LoRA adapter (a small add-on layer), not the full weights.
- **One model for all agents (parameter sharing),** as is standard in multi-agent RL. Agents behave differently because they see different things (their own clues, their open subtask, what reached them). Every agent's turns train the same weights, so the model learns both halves of cooperation: share what a teammate needs, and use what teammates posted.
- **Ablation:** a separate adapter per role (agent slot) instead of one shared adapter, to test whether specialisation helps (P12-5).

### Prompt and memory

Each turn's prompt is the Phase 11 rules text (system), the agent's own latest note, and the observation, rendered exactly as Phase 10's `LLMMember` does (tested); the reply is the Phase 11 JSON action, with its note written first so that a short reply can work out the answer before giving it. The full history of past turns is left out to keep prompts short (Phase 10 found notes-only memory hurt Haiku somewhat, so the comparison with Haiku is reported with that caveat). Haiku agents in the cross-play test keep their Phase 11 set-up (full history, effort low), so they behave as in Phase 11.

### Warm start (supervised, before RL)

RL from scratch would spend its budget learning the reply format and the arithmetic. First, fine-tune on the rule agent's moves (`teacherAction`, unlimited and free) on boards with N 1, 2 and 4 (about 14 000 turns). The teacher shares every clue it holds that nobody has shared, so each of its moves depends only on what the prompt shows; its notes list the candidates the known clues leave (the rules' method). The **warm-start check** (the Phase 11 pilot's bar): under 5% invalid replies, and at least 80% of opened subtasks solved on boards where the agent holds every clue (N = 1). The warm-start adapter is then merged into the model's weights, so RL trains a fresh adapter on top of a competent model.

**Haiku's logs are not used as training data** (P12-6): Anthropic's terms restrict using Claude's outputs to train other AI models. They serve for evaluation and analysis only.

### The RL algorithm

- **GRPO (group-relative policy optimisation):** play the same board (same seed) G times; for each agent slot, compare its return with the group's mean for that slot; push up the turns of agents that did better than average and push down those that did worse. No separate value or reward model.
- **Return per agent:** the sum of its rewards in the episode under the chosen scheme, including credit still pending when the episode ends. Each of its turns takes that advantage; the loss covers only generated tokens.
- **KL penalty to the warm-start model:** the reference is the merged warm-start weights with the RL adapter switched off, so it costs no extra memory.
- **Training-only format penalty:** an invalid reply costs a small amount in the training reward (never in reported welfare).
- **Short replies:** output capped at 160 tokens (a JSON action with its note first).
- **Generation:** vLLM on Colab, reloading the RL adapter after each update; plain Hugging Face generation on the Mac (vLLM does not support Apple GPUs), with the same code otherwise.
- **A small purpose-built loop, not a general RL library:** RL libraries' GRPO trainers expect one prompt and one reply per sample, while here each sample is one agent's turn inside a multi-agent game. The loop is: roll out, score each agent slot, compute group advantages, take a policy-gradient step with the KL penalty, checkpoint.

### The main experiment: which reward teaches cooperation?

| Training reward | Expected effect |
|---|---|
| Individual | Under-sharing: a share costs the sharer a turn and pays a teammate |
| Team | Sharing pays, but each agent's contribution is diluted as teams grow (free-riding) |
| Credit | The clearest signal: the agent that supplied a missing clue is paid directly; repeats and lies earn nothing |

All three train from the same warm start, with the same steps, rollouts and training seeds, and are evaluated on the same boards with the same scoring (welfare = value solved minus penalties, independent of the training reward).

### Training set-up

Training at N = 4 with the blackboard, 10 turns per agent per episode, on board seeds 10 000 and up (never the evaluation seeds). N = 8, messages and the coordinator are never trained on; they are the generalisation tests.

### Evaluation

All evaluation episodes use the Phase 11 length (40 turns per agent) so they compare directly with the saved Haiku and rule-agent rows. Models compared: the untrained 3B model, the warm-start model and the three RL models on the main boards; the warm-start and RL models on the other tests.

| Test | Boards | Measure |
|---|---|---|
| Main | N = 4, blackboard, seeds 900-904 (paired with the saved Haiku and rule-agent rows) and 930-939 (more held-out boards) | Welfare per agent-turn, pooled-bound share |
| Information use | as Main | Shares per held clue, redundant shares, share-to-use time, guesses, solves without all clues known |
| Generalisation | N = 8 blackboard; N = 4 messages and coordinator; seeds 900-904 | Welfare, compared with the saved Phase 11 rows |
| Does it follow the coordinator? | N = 4 coordinator | Share of opens that follow its suggestion (Haiku: 61 of 161, 38%) |
| Unfamiliar teammates (cross-play) | N = 4 blackboard, seeds 900-904: one trained agent with three Haiku agents, and one Haiku agent with three trained agents | Welfare of the mixed team; about 3 200 Haiku calls in all, under $1 |
| Liar | N = 4, blackboard and messages, seeds 900-902, one scripted false-clue liar (the Phase 11 arm) | Honest welfare lost against the same model's clean boards |
| Per-role adapters (optional ablation) | as Main, credit reward | Per-role minus shared adapters |

Before the main Colab runs (after the pilot and the warm-start check), these comparisons, the models, the training settings and the seeds are written down as a frozen analysis plan (`RL_PLAN`), its hash in every report (P12-3).

### Reward hacking and failure checks

Read turn logs, not only scores. The main risk is **solving alone by trial and error:** a wrong answer costs 0.5 and a subtask can be answered again while it is open, so with one clue known (2-10 candidates), working through the candidates pays on its own when there are up to about 4 of them, with no teamwork at all. Its signs are solves without all clues known and many wrong answers per solve; the board settings stay as in Phase 11 (for comparability), and the rate of such solves is reported for every model. Other checks: share patterns that farm credit, collapse to always waiting, and replies that game the parser.

## Machines and workflow (P12-7, P12-8)

| Step | Where | Model | Why there |
|---|---|---|---|
| Track A | Mac (API) | Claude Haiku 5.5 | Existing scheduler, cache and API key |
| Write and debug `clue_sft`, `clue_rl` | Mac (PyTorch on the Apple GPU) | about 0.5B | Minutes per debug run; a full RL step at 3B would take 20-30 minutes here |
| Pilot: install, a few warm-start and RL steps, step time and memory | Colab A100 | 3B | Checks the GPU path and the cost estimate |
| Warm start (training) | Colab | 3B | Training a 3B model is about 10 times faster on an A100 |
| Warm-start check | Mac | 3B (merged warm-start adapter) | Inference only; a few hundred turns |
| Main RL runs (3 reward schemes) | Colab, one session per run | 3B | The few-hours-per-run budget |
| Evaluation, cross-play, report | Mac | 3B adapters | Inference only (about 31 000 turns, estimated 2-4 hours); the API key is already here; reports use the existing code |

The Mac needs about 15 GB more free disk before Track B starts (it has 15 GB free; the 3B model is about 6 GB, the 0.5B about 1 GB, plus PyTorch). If evaluation on the Mac proves too slow, the same evaluation code runs on Colab.

## Compute and cost (rough; measured in the pilot)

Decided: **$150 GPU cap, each run a few hours** (P12-1). Assumptions for Colab: the 3B model with LoRA, vLLM generation on one A100 (about $1-3 per GPU-hour depending on the plan); per RL step 8 board seeds x 4 rollouts of N = 4 agents x 10 turns (1 280 agent-turns, about 100 000 generated tokens), about 2-3 minutes per step.

| Stage | Where | Time | Cost |
|---|---|---|---|
| Debug runs (0.5B) | Mac | minutes each | none |
| Pilot | Colab | about 1 h | $1-3 |
| Warm start | Colab | about 1 h | $1-3 |
| Warm-start check | Mac | under 1 h | none |
| Main: 3 reward schemes x 1 training seed, about 40 steps each | Colab | 1.5-2 h per run, 5-6 h in all | $8-18 |
| Second training seed per scheme (if the first shows a difference) | Colab | 5-6 h | $8-18 |
| Evaluation and cross-play | Mac | 2-4 h | API under $1 |
| Ablations (per-role adapters; a 7-8B check only if 3B fails the warm-start check): optional | Colab | a few hours each | $5-15 each |
| Track A (pilot and main) | Mac (API) | about 1 h | API about $2.4 |

Expected GPU spend about $20-50, well inside the cap, which leaves room for reruns after Colab disconnections and for the ablations. Forty RL steps is a short run: the realistic target is a clear gain over the warm-start model, with the reward schemes compared on that budget; if the pilot shows slower steps, the number of steps or rollouts per step is cut to keep each run to a few hours.

## Packaging: one code path, two machines

- **Install:** the core package needs only numpy and matplotlib (for the report modules), and the clue-board modules (`cluetask`, `clueboard`, `clue_agents`, `clue_text`, `clue_train`) import nothing else, so the training environment comes with the package. A new optional extra `[train]` adds `torch`, `transformers`, `peft`, `accelerate` and `tokenizers`, plus `vllm` on Linux only (an environment marker, so the extra also installs on the Mac, in a separate environment so that the project's stays without `torch`). In Colab: `pip install "explRL[train] @ git+https://github.com/Positron00/explRL"`.
- **Code:** `clue_policy` (prompts as `LLMMember` renders them, reply parsing, scripted and Claude policies), `local_policy` (`LocalPolicy`: a Hugging Face model with a LoRA adapter on cuda, mps or cpu, vLLM on cuda, cached replies), `clue_roll` (batched rollouts over `ClueEpisodes` with a policy per agent slot, scripted liars, turn logs, returns, rows in the Phase 11 columns plus solo solves and follow share, evaluation), `clue_sft` (warm-start data, training, merging, the warm-start check), `clue_rl` (`RLConfig`, group advantages, the training loop; `rl_torch` holds its PyTorch side: reply log-probabilities and checkpoints), `coop_grid` (Track A grids, both frozen plans, the evaluation suite), `coop_report` (Track A) and `rl_report` (Track B), and `tiny_model` (a tiny random model for download-free smoke tests). GPU libraries are imported only inside the functions that need them, so the normal offline tests import the modules without them and test the logic with a scripted policy.
- **Notebooks:** `nbs/demo_coop.ipynb` (Track A). `nbs/colab_clue_rl.ipynb` (with an "Open in Colab" link): set-up (GPU check, install, Google Drive mounted for outputs), a config cell, then the pilot, warm start and one RL run per reward scheme; it reads nothing from the repo's `results/` and needs no API key. `nbs/demo_rl.ipynb` (Mac): a debug run with the 0.5B model, the warm-start check, evaluation, cross-play and the report. Sections that need a model download or a GPU are behind new test flags (`gpu` for Colab, `train` for the Mac runs), so normal tests stay offline; the module notebooks' `train` cells use the tiny model, the 0.5B debug run is in `demo_rl`.
- **Watching a run:** every RL run (and the learning-rate pilot) shows a progress bar with the time remaining and, below it, one line per step: the learning rate used, the per-step policy change, the drift from the warm start, welfare, invalid replies and whether the step was undone.
- **Survives disconnections:** on Colab the adapter, optimizer state and metrics go to Drive every few steps; rerunning a section resumes from the last checkpoint. Each reward scheme is its own session.
- **Results come home as files:** adapters, training curves, configurations and the turn logs of checkpoint steps, zipped on Drive (no merged weights or checkpoints), then unpacked to `results/multiagent/rl/colab/` on the Mac (gitignored), where the warm-start model is rebuilt by merging and evaluation and the report run.
- **Track A code:** a coordinator option in `ClueLead` (pass pooled clues), two prompt options in `TextClueEnv`, both off by default; the grid in `coop_grid`.
- As before: each module under 200 lines, nbdev notebooks with offline tests, a `RUN.md` covering the Mac and Colab steps.

## Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Sparse reward: a small model rarely solves early | Little learning signal | Warm start on teacher moves (N 1, 2, 4) until it passes the check; RL starts from a competent model |
| Solving alone by trial and error instead of sharing | Scores without cooperation | Solves without all clues known and wrong answers per solve reported for every model; log reading |
| Other reward hacking (credit farming, parser games) | Misleading scores | Credit only for true first shares; log reading |
| Long prompts | Slow, costly rollouts | Note instead of full history; 160-token replies |
| GPU cost or time runs over | Unfinished comparison | Pilot measures step time; $150 cap and a few hours per run (P12-1); fewer steps or rollouts per step |
| Colab disconnects or lacks an A100 | Lost progress, slow steps | Checkpoints to Drive with resume; a paid plan; any Linux GPU machine runs the same notebook |
| Mac disk full, or Mac evaluation too slow | Track B blocked locally | Free 15 GB first; run evaluation on Colab instead |
| Forty RL steps are too few | Small or no gains | Compare with the warm-start model, not only the untrained one; report training curves |
| One or two training seeds per scheme are too few | Differences not trustworthy | Many held-out boards; a second training seed when the first shows a difference; exploratory label (P12-3) |
| Shared weights fail to specialise | Agents act alike | Distinct observations; the per-role adapter ablation |

## Decisions

| ID | Question | Decision (2026-10-13) |
|---|---|---|
| P12-1 | GPU budget | **$150 cap, each run a few hours** (the user; expected spend about $20-50); separate from the API cap |
| P12-2 | Model size | **3B for the main runs**; a 7-8B check only if 3B cannot pass the warm-start check |
| P12-3 | Exploratory or pre-registered? | **Exploratory with a frozen analysis plan** (as Phases 10-11): with one or two training seeds per scheme, a confirmatory test would be weak |
| P12-4 | Order | **Track A first:** cheap (about $2.4), uses existing machinery, and its results shape what Track B is compared against; Track B code can be written on the Mac meanwhile |
| P12-5 | Shared adapter vs per-role adapters | **Shared** in the main runs; per-role as an ablation |
| P12-6 | Use Haiku's logs as training data? | **No** (terms of use); the teacher's moves only |
| P12-7 | Where the GPU runs happen | **A standalone Google Colab notebook** (the user; an A100 runtime on a paid plan), runnable on any Linux GPU machine |
| P12-9 | RL run length after the Colab pilot (631 s per step, 7 hours per run) | **Keep the steps, make each step cheaper** (the user, 2026-10-13): train on a quarter of each step's turns with a nonzero advantage (an unbiased estimate of the same gradient), gradient checkpointing off on the A100, a stopping rule (invalid replies above 10% for 3 steps in a row, or KL above 0.5), and 40 steps, or 60 if the RL speed check fits them in a few hours. Rejected: fewer boards per step and fewer steps (too little signal per scheme) |
| P12-10 | The version 1 RL runs barely moved the model (learning rate 1e-5) | **Amend the plan (version 2) and rerun** (the user, 2026-10-14): steer each step's policy change to a target (per-step KL, measured on 32 re-scored replies; 0.003 after the pilot) by adjusting the learning rate, undo runaway steps (above 4 x the target), warm up over 3 steps, gradient checkpointing on from the start; the starting and maximum learning rates from a pilot (10 steps at 3e-5, 1e-4, 3e-4 under `credit`). The version 1 runs are kept and reported as a failed first attempt |
| P12-11 | Where the evaluation runs (the Mac estimate: about 10 hours of local generation for five 3B models) | **On Colab, except cross-play** (the user, 2026-10-15): the Colab evaluation cell runs every cell without Haiku, one model at a time with vLLM (`evalModels`; each model's rows saved as soon as it is done, so a disconnect loses at most one model); the Mac runs only the cross-play cells (the API key never goes to Colab) and merges them with Colab's rows. Same code, same cells, cached replies, so the rows are those the Mac would have produced |
| P12-8 | What runs on the Mac | **Debugging with a 0.5B model, the warm-start check, evaluation, cross-play and reports** (the user); PyTorch on the Apple GPU, same code as Colab |

## Deliverables

Track A results; a package extra and a Colab notebook that train from a clean runtime; a trained adapter per reward scheme with its training curves; an evaluation report (run on the Mac) comparing the untrained, warm-start and RL models with rule agents and Haiku; a section in `results/multiagent/REPORT.md`; and the answer to the headline question of this phase: does learning beat better instructions at teaching agents to cooperate, and which reward teaches it?

## Track A pilot (T4, 2026-10-13)

Live, Haiku, 480 calls, $0.11, 389 s; `results/multiagent/coop/pilot/`. **AC-8 met:** 3 invalid replies in 480 (0.6%). Each change reached the agents: with the follow hint (A1) Haiku opened the coordinator's suggestion in 21 of 22 opens (Phase 11: 61 of 161, 38%); with pooled clues passed on (A2), routed clues appeared in 90 of 120 observations (Phase 11: 74 of 800 at N = 4); the teammates line (A3) appeared in every observation. One board per variant (seed 1100), so the welfare figures (A1 0.14, A2 0.38, A3 blackboard 0.63, A3 coordinator 0.19) are not yet comparisons.

`TRACKA_PLAN` was frozen and committed before any main-run call: commit `23ee080`, `coopHash(TRACKA_PLAN)` = `45258d8a34da`.

## Track A results (T5, 2026-10-13; exploratory)

Live, Claude Haiku 5.5, 9 600 calls, $2.17, 1 027 s at 32 processes; total API spend $46.55 of the $150 cap. A rerun from the cache gives byte-identical `runs.csv` and `turns.jsonl` and makes no request (AC-8). Full tables: `results/multiagent/coop/full/report.md`.

| variant | channel | N = 4 | N = 8 |
|---|---|---|---|
| A1 follow the coordinator | coordinator | -0.13 [-0.16, -0.10] | -0.16 [-0.19, -0.13] |
| A2 coordinator passes pooled clues | coordinator | +0.12 [+0.07, +0.16] | +0.07 [+0.02, +0.11] |
| A3 show who works on what | blackboard | +0.03 [+0.01, +0.05] | +0.00 [-0.02, +0.03] |
| A3 show who works on what | coordinator | -0.10 [-0.13, -0.07] | -0.02 [-0.06, +0.03] |

Welfare per agent-turn minus the Phase 11 cell (same channel, N and seed; seeds 900-904; 95% bootstrap intervals).

- **Telling Haiku to follow the coordinator makes the team worse.** Haiku then followed it 95-97% of the time (Phase 11: 27-38%), but welfare fell by 0.13-0.16. The turn logs (N = 4) show why: following meant opening subtasks it knew nothing about (half of its opens with no known clue, against 10% in Phase 11) and then waiting for clues that the coordinator does not pass on: waiting rose from 29% to 57% of turns, and sharing halved.
- **Passing the pooled clues is what helps.** When the coordinator also hands over the clues it has collected for the subtask it suggests, welfare rises by 0.12 at N = 4 and 0.07 at N = 8, and many opens start with both clues known. The coordinator still trails the blackboard (by 0.17-0.20), so routing alone does not close the gap.
- **Showing who works on what does little:** a small gain on the blackboard at N = 4, none at N = 8, and a loss with the coordinator at N = 4.
- **Takeaway for Track B:** a coordinator's value lies in moving information, not in directing agents; obedience without information is harmful. The trained models are compared with these instruction-only results.

## Mac debug run (T7-T9, AC-6, 2026-10-13)

The whole training loop with `Qwen/Qwen2.5-0.5B-Instruct` on the Apple GPU (M4 Max), in a separate environment (`.venv-train`), 903 s:

- **Warm start, 50 steps:** about 14 s per step (16 examples of about 1 300 tokens), peak GPU memory about 8 GB. The first attempt ran out of memory (more than 60 GB): the loss was computed over the logits of every prompt position (a 152 000-word vocabulary). Fixed for both trainers before any GPU spend: the loss now uses the reply positions only (`replyLogps`), with gradient checkpointing (`gradCkpt`, on by default).
- **Warm-start check (3 boards, every clue held):** solve rate 0.45, invalid replies 1%. No pass is required at 0.5B; the 3B model must pass after its full warm start (about 875 steps).
- **RL:** two steps (2 boards x 2 rollouts x 4 agents x 4 turns, about 70 s per step), resume at step 3, a checkpoint of another configuration refused. The KL at the first step is 6e-4 rather than exactly 0 (bf16 rounding on the Apple GPU; it is exactly 0 on cpu in float32).
- **A warning sign, as planned:** the 0.5B model's few solves were nearly all by trial and error (solo share 0.83-1.0), the reward-hacking risk the plan names; the solo-solve figures are reported for every model.

## Colab pilot (T10, 2026-10-13)

A100, `Qwen/Qwen2.5-3B-Instruct`, 0.58 GPU hours: warm start 6.5 s per step (875 steps for the full warm start, about 1.6 hours); RL 631 s per step at the planned size (8 boards x 4 rollouts x 4 agents x 10 turns, every turn trained on, gradient checkpointing on), so 7 hours per 40-step run, against the plan's 1.5-2; peak GPU memory 11.9 GB. The update over about 1.8 million tokens per step is most of it (the warm start trains about 3 200 tokens per second). Decision P12-9: keep the steps, train on a quarter of each step's turns, gradient checkpointing off, and a stopping rule; the RL speed check at the start of session 2 fixes the step count before `RL_PLAN` is frozen.

## Colab session 1 and the warm-start check (T10-T11, 2026-10-13)

- **GPU and cost:** one A100-SXM4-80GB; peak memory about 20 GB of 80; about 2.1 GPU hours in all (pilot 0.58, warm start 1.4, set-up), roughly $2-4 (the user: under $20), far inside the $150 GPU cap. With 80 GB, gradient checkpointing off has ample room.
- **Warm start (Colab A100):** 875 steps (about 14 000 teacher turns), 1.4 hours, 5.8 s per step; the loss fell from 1.31 to about 0.005 (the model reproduces the teacher's replies almost exactly).
- **Pilot RL, per step** (the first settings: every turn trained on, gradient checkpointing on): rollout 296 s in step 1 (vLLM's start-up), then about 59 s; update about 490 s every step. The update is the bottleneck, as estimated; training on a quarter of the turns with checkpointing off should bring a step to about 155-185 s (40 steps in about 2 hours), to be confirmed by the RL speed check.
- **Warm-start check (Mac, AC-9): passed.** On 20 boards where one agent holds every clue (seeds 1200-1219, 30 turns), the 3B warm-start model solved 192 of the 206 subtasks it opened (93%), with no invalid replies (bar: 80%, under 5%). Run time 661 s, including merging the adapter into the base model.
- **Mac speed for the evaluation:** about 1.2 turns per second for the 3B model, so the evaluation's 31 000 local turns would take about 6-8 hours on the Mac (the estimate was 2-4); the same code can run on Colab instead (decision when the RL runs are done).

## Colab session 2, first attempt (2026-10-13)

Rerunning the pilot in session 2 ran out of GPU memory at its first step (loading the model): an earlier attempt in the same session still held about 47 GB in the notebook's process and 31 GB in vLLM's engine process (a failed cell keeps its models alive through its traceback, and vLLM runs in a separate process). Nothing was trained. Fixes, before any further run: each training stage now releases its models, vLLM engine and cached memory when it ends (`freeGPU`); the out-of-memory fallback retries outside the `except` block, so the failed attempt's memory is freed first; the notebook marks the pilot as session 1 only and tells to restart the session after any error. Session 2 restarts with the RL speed check.

## RL speed check and the frozen plan (T10-T11, 2026-10-13)

Colab session 2 (after a restart), from the warm-start model with the final settings (a quarter of the turns trained on, gradient checkpointing off): **166 s per step** in steady state (step 1 excluded: vLLM's start-up), so 1.8 hours for 40 steps or 2.8 hours for 60; peak GPU memory 50.3 GB of 80 (no out-of-memory fallback). Following P12-9, the step count is **60** (within a few hours per run; about 8.4 GPU hours, roughly $10-15, for the three schemes).

`RL_PLAN` was frozen and committed before any main RL run: commit `d8467f2`, `coopHash(RL_PLAN)` = `708dfc435c1f` (models `Qwen/Qwen2.5-3B-Instruct` and `Qwen/Qwen2.5-0.5B-Instruct`, 60 steps, 8 boards x 4 rollouts x 4 agents x 10 turns per step, a quarter of the turns with signal trained on, gradient checkpointing off, the stopping rule).

## RL runs, version 1 (T12, 2026-10-13 to 14): the policy barely moved

Three Colab sessions (individual 2.26, team 2.72, credit 2.71 GPU hours; all 60 steps, none halted; each fell back to gradient checkpointing at step 1 after running out of memory, so the steps took 130-160 s). Learning rate 1e-5, fixed.

| run | weight change from the warm start (norm) | largest KL to the warm start | training welfare, steps 1-10 / 51-60 |
|---|---|---|---|
| individual | 0.46 | 0.016 | 0.248 / 0.261 |
| team | 0.43 | 0.0003 | 0.245 / 0.253 |
| credit | 0.47 | 0.0006 | 0.248 / 0.260 |
| (warm start, for scale) | 9.13 | | |

The RL adapters moved the weights about 5% as far as the warm start did and the policy hardly at all (KL near 0); training welfare rose by about 0.01 in all three, within the noise. No instability (no invalid replies, no trial-and-error solves). Why: Adam moves each weight by about one learning rate per step whatever the gradient, so 60 steps at 1e-5 cannot move a LoRA adapter far, and noisy step directions cancel part of that. One genuine difference: under individual reward fewer turns carry a learning signal (874 against about 1 200 per step), as more groups tie. Decision P12-10 (the user): amend the plan to steer each step's policy change rather than fix the learning rate, set the rates from a pilot, and rerun; these runs are kept (`runs/`) and reported as a failed first attempt.

## Learning-rate pilot and RL_PLAN version 2 (T12, 2026-10-14)

Colab session 3, 10 steps under `credit` at three fixed learning rates (controller off), about 1.6 GPU hours:

| learning rate | per-step KL, mean / max | KL to the warm start after 10 steps | invalid | welfare, first 3 / last 3 steps |
|---|---|---|---|---|
| 3e-5 | 0.0000 / 0.0001 | 0.0001 | 0.1% | 0.238 / 0.252 |
| 1e-4 | 0.0007 / 0.0056 | 0.017 | 0% | 0.246 / 0.243 |
| 3e-4 | 0.018 / 0.092 | 0.012 | 1.0% | 0.222 / 0.210 |

3e-5 does not move the model; 1e-4 moves it steadily without harm; at 3e-4 steps already swing (one at 0.09), invalid replies appear and welfare falls. The planned per-step target of 0.01 sits in that harmful range, so the target is lowered to **0.003**, with a starting rate of **1.5e-4** (the per-step change grows roughly with the square of the rate) and a maximum of **2.5e-4** (below where harm appeared); a step above 4 x 0.003 = 0.012 is undone. The ten-step welfare changes are within the noise and are not evidence about RL's effect.

`RL_PLAN` version 2 was frozen and committed before any version 2 run: commit `304b955`, `coopHash(RL_PLAN)` = `4d1ea0078a6e` (60 steps, a quarter of the turns trained on, gradient checkpointing on, learning rate from 1.5e-4 within [1e-6, 2.5e-4] steered to a per-step KL of 0.003, warm-up 3, runaway steps above 0.012 undone, the stopping rule).
