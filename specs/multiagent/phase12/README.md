# Plan: Phase 12, training agents to work together (RL on the clue board)

Status: **code implemented and tested offline** (2026-10-13); no run yet (the user asked to wait until disk space is cleared). Next: the Track A pilot (T4), the Mac debug run, then Colab. Part of the multi-agent plan: [../README.md](../README.md). Builds on [Phase 11](../phase11/README.md), whose clue board was packaged for this phase. Two machines (P12-7, P12-8): **this Mac** (M4 Max) for writing and debugging the training loop with a tiny model, the warm-start check, evaluation and reports; **a standalone Google Colab notebook** for the GPU runs (warm start and RL with a 3B model), each a few hours, under a $150 GPU cap (P12-1).

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

- **Install:** the core package needs only numpy, and the clue-board modules (`cluetask`, `clueboard`, `clue_agents`, `clue_text`, `clue_train`) import nothing else, so the training environment comes with the package. A new optional extra `[train]` adds `torch`, `transformers` and `peft`, plus `vllm` on Linux only (an environment marker, so the extra also installs on the Mac). In Colab: `pip install "explRL[train] @ git+https://github.com/Positron00/explRL"`.
- **Code:** `clue_policy` (prompts as `LLMMember` renders them, reply parsing, scripted and Claude policies), `local_policy` (`LocalPolicy`: a Hugging Face model with a LoRA adapter on cuda, mps or cpu, vLLM on cuda, cached replies), `clue_roll` (batched rollouts over `ClueEpisodes` with a policy per agent slot, scripted liars, turn logs, returns, rows in the Phase 11 columns plus solo solves and follow share, evaluation), `clue_sft` (warm-start data, training, merging, the warm-start check), `clue_rl` (`RLConfig`, group advantages, the training loop; `rl_torch` holds its PyTorch side: reply log-probabilities and checkpoints), `coop_grid` (Track A grids, both frozen plans, the evaluation suite), `coop_report` (Track A) and `rl_report` (Track B), and `tiny_model` (a tiny random model for download-free smoke tests). GPU libraries are imported only inside the functions that need them, so the normal offline tests import the modules without them and test the logic with a scripted policy.
- **Notebooks:** `nbs/demo_coop.ipynb` (Track A). `nbs/colab_clue_rl.ipynb` (with an "Open in Colab" link): set-up (GPU check, install, Google Drive mounted for outputs), a config cell, then the pilot, warm start and one RL run per reward scheme; it reads nothing from the repo's `results/` and needs no API key. `nbs/demo_rl.ipynb` (Mac): a debug run with the 0.5B model, the warm-start check, evaluation, cross-play and the report. Sections that need a model download or a GPU are behind new test flags (`gpu` for Colab, `train` for the Mac runs), so normal tests stay offline; the module notebooks' `train` cells use the tiny model, the 0.5B debug run is in `demo_rl`.
- **Survives disconnections:** on Colab the adapter, optimizer state and metrics go to Drive every few steps; rerunning a section resumes from the last checkpoint. Each reward scheme is its own session.
- **Results come home as files:** adapters, training curves and turn logs, zipped on Drive, then copied to `results/multiagent/rl/` on the Mac (gitignored), where evaluation and the report run.
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
| P12-8 | What runs on the Mac | **Debugging with a 0.5B model, the warm-start check, evaluation, cross-play and reports** (the user); PyTorch on the Apple GPU, same code as Colab |

## Deliverables

Track A results; a package extra and a Colab notebook that train from a clean runtime; a trained adapter per reward scheme with its training curves; an evaluation report (run on the Mac) comparing the untrained, warm-start and RL models with rule agents and Haiku; a section in `results/multiagent/REPORT.md`; and the answer to the headline question of this phase: does learning beat better instructions at teaching agents to cooperate, and which reward teaches it?
