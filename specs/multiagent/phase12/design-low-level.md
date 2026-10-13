# Low-level design: Phase 12, training agents to work together

Section numbers are referred to by [tasks.md](tasks.md). Phase 10 and 11 names (`LLMMember`, `FRAMING`, `LLMClient`, `LLMReply`, `ResponseCache`, `LLMConfig`, `llmStats`, `cellRow`, `llmCell`, `runWorkload`, `ClueBoardEnv`, `TextClueEnv`, `ClueLead`, `ClueLiar`, `ClueEpisodes`, `teacherAction`, `clueMetrics`, `clueCell`, `CLUE_SETTINGS`) are as in [../phase10/design-low-level.md](../phase10/design-low-level.md) and [../phase11/design-low-level.md](../phase11/design-low-level.md).

## 1. Track A options (`clue_text`, `clue_agents`, `clue_runs`)

- `TextClueEnv(board, hint=None, showOpen=False)`.
  - `hint='follow'` appends to `rules()`, after the paragraph on the channels: "The coordinator sees every clue anyone shares. Its suggestion is usually the best subtask to open: follow it unless you know a better one."
  - `showOpen=True` adds a line after the channel lines of `observe`: `Teammates working on: agent 0: T3; agent 2: none` (every teammate, in id order; `none` when nothing is open).
- `ClueLead(n, passPooled=False)`.
  - `post` also records each pooled clue's author.
  - With `passPooled=True`, `suggest(i, board)` appends to `routed[i]` every pooled clue of the suggested subtask not already routed to `i`, as `(author, k, (j, p, r), board.tWorld)`. They are then known and shown like routed clues.
  - `TextClueEnv.observe` calls `suggest` before computing the agent's known clues. This makes no difference when `passPooled` is off; the Phase 11 tests and cached reruns check that.
- `clueSetup` builds `ClueLead(cfg.N, passPooled=cfg.world.get('passPooled', False))`; `runClue` builds `TextClueEnv(b, hint=cfg.world.get('hint'), showOpen=cfg.world.get('showOpen', False))`. The board still receives only its own settings (`BOARD_KEYS`).

## 2. Episodes and the teacher (`clue_train`)

```python
class ClueEpisodes:
    def __init__(self, batch, nAgents, settings=None, scheme='individual', turns=40, seed=0, channel='blackboard',
                 seeds=None, scripted=None, text=None, passPooled=False)
    # seeds: board seed per batch entry (default seed + b; repeats allowed); channel rngs seeded per board seed
    # scripted: {slot: factory(channel, rng)} -> a Member acting on the board (ClueLiar); rngs from
    #           spawnRngs(boardSeed + 3000, len(scripted)) in slot order, as runClue
    # text: TextClueEnv options (hint, showOpen); passPooled: the coordinator option (Track A, A2)
    last: list       # per board, after step(): dict(agent, t, obs, action, report, valid, reward, info, explore, summary)
def teacherAction(board, i, channel, rng=None, share='needed') -> dict
```

The exploration flag and the summary line are computed in `step`, before the next observation can overwrite the agent's channel state. When a scripted slot is next on a board, `_next` runs its `event(board, t)` directly, records its outcome, re-queues it and moves on, so `reset` and `step` only ever return text slots. Event order, observation times and channel state match `runTurns` with the same members, so the same replies give the same board as `runClue` (tested in section 5).

## 3. Prompts and policies (`clue_policy`)

```python
def historyBlocks(memory='notes', notes='', past=()) -> list   # the memory part of the blocks
def renderPrompt(env, obs, memory='notes', notes='', past=(), framing='own') -> (system, blocks)
def userText(blocks) -> str                     # the blocks as one user message (local models)
def parseReply(text) -> dict | None            # json.loads, else the first decodable {...} object; dicts only
def asReply(text, usage=None, stop='end_turn') -> LLMReply   # parsed by parseReply; cost 0
def scriptedPolicy(fn)                          # fn(system, blocks) -> text; for tests and the teacher replay
def claudePolicy(client, workers=8)             # client.complete(system, blocks, CLUE_SCHEMA, task='clue'), threads
# a policy: policy(requests: list[(system, blocks)]) -> list[LLMReply]
```

`renderPrompt` reproduces `LLMMember.system()` and `LLMMember.prepare()` exactly:
- **System:** `env.rules() + '\n\n' + FRAMING[framing].format(u=env.unit)`.
- **Blocks:** the history (notes: `Your notes so far: {notes}` when there is a note; full: `Your past turns, oldest first:\n` + the first summary, then one block per later summary), then `Now:\n{obs}`.
- **Cache breakpoint:** on the last history block.

The test compares it with a live `LLMMember` on the same board and history.

## 4. Local models (`local_policy`)

```python
def pickDevice(pref='auto') -> str             # 'cuda' if available, else 'mps', else 'cpu'
class LocalPolicy:
    def __init__(self, model, adapter=None, device='auto', maxNew=160, temperature=1.0, seed=0, cache=None,
                 engine='auto', gpuShare=0.35, batch=32, hf=None, tokenizer=None, adapterName=None, share=None)
    # hf, tokenizer: reuse a loaded (training) model; adapterName: one of its adapters; share: another policy's vLLM engine
    def __call__(self, requests) -> list[LLMReply]
    def setAdapter(self, path)                 # after each RL step (a new, globally unique LoRA id)
def promptText(tok, system, blocks) -> str
def encodePair(tok, prompt, reply, maxLen=1536, eos=True) -> (ids, replyStart)
def adapterHash(path) -> str
```

- **Prompt text:** the tokenizer's chat template with a system message and one user message (the blocks' texts joined by blank lines), generation prompt added.
- **Engine:** `'vllm'` when the device is cuda and vLLM is installed (LoRA through `LoRARequest`, `gpu_memory_utilization = gpuShare`), else `'hf'` (batched `generate` with left padding).
- **Dtype:** bf16 on cuda and mps, float32 on cpu.
- **Reply:** `usage` has the prompt and generated token counts; `stopReason` is `'max_tokens'` when the cap is hit; cost is 0.
- **Independent samples:** every request in a batch is sampled separately (vLLM: one seed per request; Hugging Face: one random stream per batch), so the copies of one board in a GRPO group differ. The sampling seed of a call is `seed * 1 000 003 + calls * 10 007` plus the request's position.
- **Cache:** with a cache (a `ResponseCache` directory), a reply is looked up or stored under `sha256(json([model, adapterHash, promptText, temperature, maxNew, seed + calls, occurrence]))`, where `adapterHash` is the sha256 of the adapter's weight files (empty without one) and `occurrence` counts repeats of the same prompt within the call.
- **Lazy imports:** `torch`, `transformers`, `peft` and `vllm` are imported in `__init__` and the methods, never at module import.

## 5. Rollouts and rows (`clue_roll`)

```python
def rollout(cfg, seeds, policies, scripted=None, memory='notes', keepPrompts=False) -> Rollout
# cfg: LLMConfig (task 'clue', channel, N, turns, framing; world = board settings, 'scheme', Track A options)
# policies: one policy for all text slots, or {slot: policy}; memory: 'notes' | 'full', or {slot: memory}
# Rollout: cfg, seeds, boards, logs (per board, per slot: LLMMember-format turn records), returns (batch x N array),
#          prompts (per board, per slot: (system, blocks) per turn, only with keepPrompts=True, for training)
def coopRows(cfg, ro, honest=None) -> list[dict]     # one row per board (honest: the non-liar slots by default)
def runEval(cells, policyFor, logDir=None) -> list[dict]
```

**The `rollout` loop.**
1. `ClueEpisodes(len(seeds), cfg.N, board settings, cfg.world.get('scheme', 'individual'), cfg.turns, channel=cfg.channel, seeds=seeds, scripted=scripted, text={hint, showOpen from cfg.world})`; prompts use `cfg.framing` and each slot's memory.
2. Each round, every active board has one pending text turn. Render its prompt with the slot's memory state, then group the requests by policy and call each policy once.
3. Step all boards with the parsed replies. Read `last` to write the turn record (`kind`, `agent`, `t`, `obs`, `response`, `action`, `valid`, `reward`, `report`, `explore`, `stop`, `refusal`, `usage`, `cost`), the note (`notes[:1000]` of the parsed reply) and the summary line (`env.summary`).
4. Returns are the per-slot sums of delivered rewards, plus `board.pending` at the end.

**Rows.** `coopRows` builds each row as:
- `dict(episode=0, **clueMetrics(cfg, b, None, honest, T), **llmStats(text slots' logs))`;
- `soloSolves`: first correct answers whose noted candidate count was above 1;
- `soloShare = soloSolves / solved`;
- `wrongPerSolve = wrong / solved`;
- `followShare`: opens whose target equals the observation's `The coordinator suggests: T<k>.` line, over opens with such a line; nan without a coordinator.

**Fidelity check (test).** With `scriptedPolicy` replaying a fixed reply function, `coopRows` minus its new columns equals `runClue`'s row for the same `LLMConfig` and seed. The fake client must return the same text.

**`runEval`.**
1. Group the cells by their config without the seed, and run one `rollout` per group over its seeds.
2. Policies and memories come from `policyFor(cell)` -> `(policies, memory)` (one policy, or `{slot: policy}` with Haiku slots on full memory for cross-play). Liars come from `cfg.nLiar` (`ClueLiar` in the first slots, as `runClue`). Haiku slots use `claudePolicy` with a client built as in Phase 11 (`makeClient` with the live spec: effort low, `maxTokens` 8000, the shared cache and the $150 API budget); `demo_rl` reserves the estimated Haiku cost on that client before the evaluation starts.
3. Rows are keyed with `cellRow(cell, cfg, row)`; turn logs are written one file per cell, as Phase 11.

## 6. Warm start (`clue_sft`)

```python
def sftExamples(seeds, sizes=(1, 2, 4), turns=20, settings=CLUE_SETTINGS, boards=False) -> list[dict]   # system, user, assistant, key
def teacherNote(board, i, channel, reply) -> str
def teacherReply(board, i, channel, rng) -> str     # notes first, then action, target, answer, clue
@dataclass
class SFTConfig: model; out; loraR=16; loraAlpha=32; dropout=0.05; lr=1e-4; epochs=1; batch=16; microBatch=4; maxLen=1536; maxSteps=0; device='auto'; seed=0
def loadModel(model, device, dtype=None) -> (tokenizer, model); def loraConfig(r, alpha, dropout=0.0); def batchTensors(seqs, pad, device)
def trainSFT(cfg, examples) -> path            # LoRA adapter; loss on the assistant tokens only
def mergeAdapter(model, adapter, out) -> path  # merged weights (the warm-start model)
def warmCheck(policy, seeds=range(1200, 1220), turns=30, settings=CLUE_SETTINGS) -> dict  # solveRate, invalid, passed
```

**Examples.** `sftExamples` runs `ClueEpisodes` (blackboard for N >= 2, none for N = 1) with `teacherAction(..., share='always')` for every slot. Each turn's prompt is rendered by `renderPrompt` with notes memory (the teacher's previous note). The reply is `json.dumps` of the teacher's action, with `notes` as the first key:
- **Submit:** the rules' method, e.g. `x mod 7 = 2 below 30: 2, 9, 16, 23; of these x mod 5 = 3: 23`.
- **Open:** e.g. `open T4: 1 of 2 clues known, value 3`.
- **Share:** `share my clue for T3`.
- **Wait:** `nothing to do`.

Seeds 20 000-20 099 for each size give about 14 000 examples (N = 1: 2 000, N = 2: 4 000, N = 4: 8 000).

**Check.** `warmCheck` runs `rollout` on N = 1 boards with no channel and reports `solveRate = solved / opens` and `invalid = invalid turns / turns`. It passes at solve rate >= 0.8 and invalid < 0.05.

## 7. RL (`clue_rl`)

```python
@dataclass
class RLConfig:
    model: str; out: str; scheme: str = 'credit'; N: int = 4; channel: str = 'blackboard'; turns: int = 10
    seedsPerStep: int = 8; group: int = 4; steps: int = 40; lr: float = 1e-5; kl: float = 0.04
    loraR: int = 16; loraAlpha: int = 32; maxNew: int = 160; temperature: float = 1.0; formatPenalty: float = 0.1
    trainSeed: int = 0; boardSeed0: int = 10_000; ckptEvery: int = 5; microBatch: int = 8; maxLen: int = 1536
    device: str = 'auto'; perRole: bool = False          # one adapter per agent slot (the optional ablation)
def configHash(cfg) -> str                      # identity of a run: all but out, device, ckptEvery, microBatch, steps
def stepSeeds(cfg, s) -> list; def trainingReturns(ro, penalty) -> array
def groupAdvantages(returns) -> array           # returns: (seeds x group x N) -> same shape
def stepSamples(ro, adv) -> list                # slot, prompt, reply text, eos (not cut), advantage; nonzero advantage only
def microBatches(samples, cfg) -> list          # per-role: one slot per chunk
def trainRL(cfg, settings=CLUE_SETTINGS) -> path
# rl_torch: replyLogps(model, tok, samples, maxLen, device); saveCheckpoint(model, opt, step, out, config);
#           loadCheckpoint(model, opt, out, config, names) -> step
```

**Per step `s`:**
1. Board seeds `boardSeed0 + s * seedsPerStep + j` (`j < seedsPerStep`), each repeated `group` times.
2. `rollout` with the current policy (vLLM with the latest adapter on cuda; the training model itself on mps or cpu) and the configured reward scheme (`cfg.world['scheme']` of the rollout's `LLMConfig`, built from `RLConfig` and `CLUE_SETTINGS`).
3. Training returns: the rollout returns minus `formatPenalty` per invalid turn of the slot.
4. Advantages per (seed, slot) over the group: `(R - mean) / (std + 1e-6)`, zero when all equal.
5. One optimizer step (AdamW, gradient clipping 1.0, gradient accumulation over micro-batches) on the mean over samples of `-A * mean_t log pi(y_t) + kl * mean_t k3_t`. Here `k3_t = exp(d_t) - d_t - 1` with `d_t = log pi_ref(y_t) - log pi(y_t)`, and `pi_ref` is the same model with the RL adapter disabled (`peft` `disable_adapter`). Turns with zero advantage are skipped. `replyLogps` left-pads the batch so the replies end together and asks the model only for the reply positions' logits (`logits_to_keep`), with position ids from the attention mask.
6. Append to `metrics.jsonl`: step, seconds (rollout and update), mean training return, welfare per agent-turn, shares per held clue, invalid rate, solo share, mean KL, loss, samples, tokens.

**Checkpoints** go to `out/ckpt-<step>/` every `ckptEvery` steps and at the end: adapter, optimizer state, `state.json` (step, config hash). `trainRL` resumes from the newest checkpoint whose config hash matches, and refuses one that does not; the step count is not part of the hash, so a run can be extended. Sampling seeds depend only on the step (the policies' call counter is set to `step x 100 000` before each rollout), so a resumed run continues as the uninterrupted one would, up to GPU non-determinism.

**Defaults:** 40 steps x 8 seeds x 4 rollouts x 4 agents x 10 turns = 51 200 training turns per run, the Colab estimate of 2-3 minutes per step. They are fixed in `RL_PLAN` after the pilot (AC-7). The training seed sets the adapter initialisation and the sampling; the board seeds are the same for every scheme and training seed.

**Per-role adapters (`perRole=True`, optional ablation):** one adapter per slot (`slot0` ... `slot3`), each initialised the same way; generation uses each slot's adapter (a `LoRARequest` per slot with vLLM, `set_adapter` per slot batch otherwise); each turn's loss updates its slot's adapter; advantages unchanged. Run under the credit reward only, after the main runs, if the GPU cap allows.

## 8. Grids and plans (`coop_grid`)

| Grid | Cells | Calls | Cost (about) |
|---|---|---|---|
| `trackAGrid()` (study `coopA`, seeds 900-904, 40 turns) | A1 `hint='follow'`, coordinator; A2 `passPooled`, coordinator; A3 `showOpen`, blackboard and coordinator; N {4, 8} | 9 600 | $2.3 |
| `trackAPilotGrid()` (study `coopAPilot`, seed 1100, 30 turns) | the four (variant, channel) pairs at N = 4 | 480 | $0.12 |

`MODELS` holds the candidate models (`Qwen/Qwen2.5-3B-Instruct`, `Qwen/Qwen2.5-0.5B-Instruct`; confirmed in T7, fixed when `RL_PLAN` is frozen). `trackAQuick()`: the pilot cells at 3 turns. `TRACKA_PLAN` and `RL_PLAN` are dicts: version, `frozen`, models, settings (`CLUE_SETTINGS`, the Track A options, `RLConfig` and `SFTConfig` defaults), seeds, analyses (the requirements' tables), prices, `nboot = 2000`, exploratory. `coopHash(plan)` gives 12 hex digits.

**Seeds in `RL_PLAN`:**
- training boards from 10 000;
- warm-start examples 20 000-20 099;
- warm-start check 1200-1219;
- evaluation: main 900-904 and 930-939; generalisation and cross-play 900-904; liar 900-902.

`evalSuite(models=LOCAL, extra=())` returns cells made by `evalCell(model, test, channel, N, seed, **cfg)` (study `coopEval`, level `<model>|<test>`, runner `'local'`, model `'local:<model>'`, notes memory, 40 turns, the Phase 11 board settings); `LOCAL` = untrained, warm, individual, team, credit; `extra` adds models evaluated on the main boards only (the per-role model). Local-model turns per model (Haiku calls in brackets):

| Test | Cells | Turns per model | Models |
|---|---|---|---|
| main | N = 4, blackboard, 15 seeds | 2 400 | 5 (untrained, warm start, 3 RL) |
| gen8, genMsg, genLead | N = 8 blackboard; N = 4 messages; N = 4 coordinator; 5 seeds each | 3 200 | 4 (warm start, 3 RL) |
| cross1, cross3 | N = 4 blackboard, 5 seeds: one model agent + three Haiku; three model agents + one Haiku | 800 (+ 800 Haiku) | 4 |
| liar | N = 4, blackboard and messages, 3 seeds, one scripted liar | 720 | 4 |
| per-role (optional) | as main, the per-role model | 2 400 | 1 |

That is about 31 000 local turns and 3 200 Haiku calls (about $0.8). On the Mac this is estimated at 2-4 hours, measured in T7; the same code runs on Colab if that is too slow.

## 9. Reports (`coop_report`, `rl_report`)

- **`logMetrics(records, m)`** (`coop_report`): per row key, follow share and solo solves from turn logs (scoring answers submitted with fewer than `m` known clues). Track A rows come from `runClue` and keep the Phase 11 columns (so Phase 11's outputs stay byte-identical), so these two metrics are read from the logs, for the variants and the Phase 11 baseline alike; a test checks that they agree with `coopRows` on rollouts.
- **`trackASummaries(rows, p11, logm, p11logm, study='coopA')`**, **`writeTrackA`**, **`figTrackA`** (`coop_report`): variant effects, coordinator gap and mechanism (the `TRACKA_PLAN` table), paired on seed with the Phase 11 rows of `results/multiagent/clue/full/runs.csv`.
- **`rlSummaries(evalRows, p11, numpyRows)`** (`rl_report`): the `RL_PLAN` table; Phase 11 Haiku and rule-agent rows from the same file.
- **`writeRL(path, S, meta)`** and **`writeRLFigures(out, S, curves, refs)`** (`rl_report`; curves per scheme from `metrics.jsonl`): provenance first: plan hashes, commit, base and debug model ids, adapter hashes, GPU hours and cost per run, API cost and total spend.
- **Figures:**
  - `coopA.png`: variant effects;
  - `coop_main.png`: welfare and pooled share per model, with Haiku and rule-agent lines;
  - `coop_info.png`: shares per held clue, solo share, wrong per solve;
  - `coop_gen.png`: generalisation, cross-play, liar;
  - `coop_curves.png`: training curves.

## 10. Notebooks and outputs

| Notebook | Sections (flags) | Outputs |
|---|---|---|
| `demo_coop` | setup as `demo_clue` (`run(mode, grids, spec, workers)`); quick: one cell of each variant with the fake client, identical at 1 and 8 processes, key scan; pilot (`llm`): invalid rate; main (`llm`): asserts `TRACKA_PLAN` frozen, `_live` copies | `results/multiagent/coop/{quick,pilot,full}/` |
| `colab_clue_rl` | set-up (GPU check, `pip install`, Drive mount, `OUT`); config (models and `RL_PLAN` defaults); pilot (`gpu`): 20 warm-start steps and 3 RL steps on the 3B model, step time and peak memory; warm start (`gpu`): `sftExamples`, `trainSFT` (the adapter only); RL run (`gpu`): asserts `RL_PLAN` frozen, merges the warm-start model once, `SCHEME` set at the top, one scheme per session, resumes; pack (`gpu`): zip of adapters, metrics and configurations (no merged weights, no checkpoints) | Drive: `explRL_rl/{pilot,warm,runs/<scheme>}/` |
| `demo_rl` | quick (normal tests): scripted-policy rollout, rows and report on synthetic data; debug (`train`): 0.5B on mps, 50 warm-start steps, `warmCheck` on 3 boards, 2 RL steps, resume at step 3, refusal of another configuration (AC-6); warm check (`train`): rebuilds the 3B warm-start model by merging the downloaded adapter into the base model (needed anyway as the untrained baseline), then `warmCheck`; evaluation (`train`, cross-play needs `EXPLRL_LLM_LIVE=1`): one model at a time, `runEval` with cached local replies; report (GPU hours from `results/multiagent/rl/gpu.json`) | `results/multiagent/rl/{quick,debug,warm,eval,cache,colab}/` |

## 11. Packaging

`pyproject.toml`:
- **Extra:** `train = ['torch', 'transformers', 'peft', 'accelerate', 'tokenizers', 'vllm; sys_platform == "linux"']`.
- **Test flags:** `tst_flags` gains `gpu` and `train`.
- **Colab install:** `pip install "explRL[train] @ git+https://github.com/Positron00/explRL"`.

## 12. Determinism, cost, secrets

- **Seeds** fix the boards, dealing, channels, liars and teacher draws.
- **Caching:** API replies are cached as in Phase 10, local replies by `LocalPolicy`'s cache, so evaluation reruns are byte-identical. Training is reproducible up to GPU non-determinism; the training seed and library versions are recorded.
- **Costs:** API spend goes through the Phase 10 budget (cap $150, shared ledger). GPU hours per Colab session are recorded by hand in the README from the notebook's timers, against the $150 GPU cap.
- **Keys and data:** no key on Colab; on the Mac, cross-play reads the key from `.env.local`. Claude's replies never enter `sftExamples` or `trainRL` (P12-6).
