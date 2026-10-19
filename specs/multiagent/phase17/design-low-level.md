# Design (low level): Phase 17

Part of [README.md](README.md); see [design-high-level.md](design-high-level.md).

## `rl17_grid`

```python
SIZES, LIAR_SEEDS = (4, 8, 16, 32), range(900, 910)
def teamSizeSuite(models) -> list          # per model: n4 (MAIN_SEEDS), n8/n16/n32 (900-909) clean; n<N>liar (900-909, nLiar = N // 4)
STEP0_MODELS = dict(warm=..., individual=..., team=..., credit=..., credit_s2=..., indpen_s1=..., ...)   # name -> adapter dir on Drive
@dataclass
class RL17Config(RLConfig):
    guided: bool = False; epochs: int = 1; clip: float = None; mixN: tuple = ((4, 1.0),); liarShare: float = 0.0; lrFixed: float = None
RL17_DEFAULTS = dict(guided=False, epochs=1, clip=None, mixN=((4, 1.0),), liarShare=0.0, lrFixed=None)
def runFields17(cfg); def configHash17(cfg) -> str   # runFields minus RL17_DEFAULTS at default; equals configHash for an equal RLConfig
PILOT17 = dict(p17a=dict(...), p17b=dict(...), p17c=dict(...))      # p17d is filled in from p17b/p17c by the rule (turns=40)
PILOT17_PLAN = dict(version=1, frozen=False, configs=..., steps=30, seed=1, mix=..., selection=..., measures=...)
RL17_ARMS = dict(r17mix=dict(mixN=((4, 0.5), (8, 0.5)), liarShare=0.25), r17four=dict(mixN=((4, 1.0),), liarShare=0.0))
RL17_SEEDS = dict(r17mix=8, r17four=5)
RL17_RUNS = [(a, s) for s in range(1, 9) for a in RL17_ARMS if s <= RL17_SEEDS[a]]   # interleaved, 13 runs
BASE17 = dict(scheme='credit', wrongPenalty=2.5, haltJump=0.15, guided=True, turns=20)   # common to pilot and main runs
def pilotConfig(name, model, out, recipe=None) -> RL17Config        # r17mix's mix, seed 1, 30 steps; p17d = recipe + turns 40
def pilotChoice(metrics, halted, names=None) -> (choice, table)     # the selection rule (README); a run without metrics fails it
def chosenRecipe(choice, p17dBase=None) -> dict                     # RL17_PLAN's recipe: PILOT17[choice], or p17d's base + turns 40
RL17_PLAN = dict(version=1, frozen=False, recipe=None, arms=..., runs=..., steps=200, evaluation=..., hypotheses=..., families=...,
                 cutRule='if a 32-agent cell runs out of memory: 6 boards per size at N 32 (seeds 900-905)', ...)
def rl17Config(arm, seed, model, out, recipe) -> RL17Config         # RL_PLAN v2 + BASE17 + recipe + arm; trainSeed = seed - 1; ckptEvery 1
def claim(runDir, host, takeover=()) -> bool                         # write runDir/claim.json if free or ours or listed; True if ours
                                                                     # (also used for eval_p17/claim.json)
def projectHours(stepSeconds, steps=200, seeds=RL17_SEEDS) -> dict   # from the chosen pilot run's mean seconds per step; r17four at 2/3
```

`claim`: a folder with progress (metrics, checkpoints or `final/`) but no claim counts as another host's (a run started by a cell that does not claim) unless listed in `takeover`; if `claim.json` is absent otherwise, write it (to a temporary name, then rename) with the host and time, read it back, and return whether the host is ours; if present and the host differs, return False unless the run is in `takeover` (then overwrite). Simulated in tests with two hosts on a temporary folder.

## `rl17_train.trainRL17` (step pieces in `rl17_update`: `boardGroups`, `clippedTerm`, `valueMask`, `tokenTerm`, `cutCount`, `ppoUpdate`, `saveTurns`)

Structure as `trainRL`, with these differences:

1. **Rollouts per step.** The step's distinct board seeds (`seedsPerStep` of them, as `stepSeeds`) are split in order by `mixN` (8 seeds: the first 4 at N 4, the last 4 at N 8); within each team size, the first `round(liarShare x boards)` boards have their first `N // 4` slots scripted `ClueLiar` (as `runEval` passes `scripted={i: ClueLiar ...}` to `rollout`). Each board is played `group` times. One `rollout` call per (N, liars or not) group. Scripted slots write no text turns, so they yield no samples.
2. **Advantages within each group of replays only**, honest slots only (liar slots get no samples).
3. **Old and reference log-probabilities, once per step.** Before the update, `replyLogps` of every sample under the current weights (old) and with the adapter off (reference), no gradients; reused by every pass (Phase 12's update recomputed the reference per call).
4. **`epochs` passes** over the samples (the first pass in micro-batch order, as Phase 12; later passes shuffled with a seed from the run and step): loss per reply = -min(r A, clip(r, 1-eps, 1+eps) A) with r = exp(mean log pi - mean old log pi) per reply (reply-level ratio, matching the reply-level mean used since Phase 12), plus `kl` x k3 to the adapter-free model; with `clip=None` and `epochs=1` the loss is Phase 12's `-A * mean log pi + kl * k3`.
5. **Controller:** the per-step change is measured after all passes; `lrFixed` switches the controller off (the rate stays fixed except that a roll-back of the jump rule halves it, as in Phase 13).
6. **Constrained replies:** `makePolicies` passes `guided` to `LocalPolicy`.
7. **Pilot v3's fix (`FIX17`, in `BASE17`; user-approved 2026-10-19 after pilot v2):** `valueOnly` weights each reply's loss and k3 by `valueMask` (1 on tokens that overlap a value of the reply's JSON object: a string's content and closing quote, a number; 0 on keys, punctuation, opening quotes and eos, which the schema fixes, so they carry no decision; a reply that is not a JSON object counts every token); `tokenClip` replaces the reply-level ratio with PPO's per-token ratio, -mean_t min(r_t A, clip(r_t) A) over the weighted tokens (`tokenTerm`), so no single token can fall more than the clip allows per batch; `maxLen` 3,072 (8-agent prompts reach about 2,200 tokens); `cutCount` logs `cut` per step (prompts longer than the window; the pilot rule requires 0) and, with `valueOnly`, `klAll` (k3 over every token) beside `kl` (value tokens, used by the halt rule).

Stopping rules, checkpoints (every 5 steps; turn logs of every board group via `saveTurns`), resume and `final` as `trainRL`; the configuration hash is `configHash17`. One shared adapter and board-level advantages only (`perRole` and `advantage='turn'` refused).

## `local_policy` change

`LocalPolicy(..., guided=False)`: with `guided='model'` (Phase 17 from pilot v2) the structured outputs use `GUIDED_SCHEMA`, `CLUE_SCHEMA` reordered to the warm start's own key order (notes first, as in 99.9% of its replies); with `guided=True` (pilot v1) `CLUE_SCHEMA` itself. Otherwise each request's `SamplingParams` carries structured outputs with the schema (`StructuredOutputsParams`, with the older `GuidedDecodingParams` as a fallback); the HF engine raises `ValueError`; guided replies get their own cache keys. Default unchanged (cache keys and sampling parameters as before; tested).

## `rl17_report`

```python
def curves(rows, models) -> {model: {N: dict(welfare, pooledShare, honestLoss, sharePerHeld, soloShare, invalid)}}
def gains(rows, runs, N, metric='welfare') -> {run: mean over boards of run - warm}
def rl17Summaries(rows, s0rows=None, haiku=None) -> S        # H17-1..5 via rl16_report.signFlip / permTest; Holm per family
def writeRL17(path, S, meta); figRL17(out, S); syntheticRows17(seed, ...)
```

H17-2 per run: `gains(n32) - gains(n4)`; H17-4 per run: warm's honest loss at N 32 minus the run's; H17-5: `permTest(gains[r17mix] at n32, gains[r17four] at n32)`.

## Colab cells

- **Configuration:** `HOST = 'account-a'` (set per account), `RUNS17 = OUT / 'runs_p17'`, `TAKEOVER = []`; prints both plans' hashes and frozen states.
- **Phase 17 step 0** (one cell; two accounts may share it): per model not yet evaluated and claimable (`eval_p17s0/claims/<model>`), `evalModels` for that model in its own process; when all 15 are evaluated, the account that wins `claims/_pack` writes `runs.csv` (all read back) and the zip.
- **Phase 17 pilot** (one cell; two accounts may share it): asserts `PILOT17_PLAN['frozen']`; trains the claimable runs among `p17a`-`p17c` (each its own process, resumable); once `p17b` and `p17c` are done, picks `p17d`'s base and trains `p17d` if claimable; when all are done, the account that wins `runs_p17pilot/_select` prints the selection table (halted, last-10 invalid, steps 21-30 welfare, seconds per step), writes `selection.json` and the zip.
- The configuration cell also defines `stream` (a child process per run) and `packZip` for the Phase 17 cells.
- **Phase 17 main** (one cell; asserts `RL17_PLAN['recipe']` and `['userConfirmed']` too): asserts `RL17_PLAN['frozen']`; for each run in `RL17_RUNS`: skip if final, skip if `claim` refuses, else train (own process); when every run is final and this host wins `claim(OUT / 'eval_p17', HOST)`: evaluate all 13 adapters (own process; resumes per model), zip; otherwise print which runs or which evaluation other hosts hold.
- **Configuration:** sets `HOST` (`claim` refuses an empty one); the second account sets a different `HOST`.

## Tests

| Notebook | Checks |
|---|---|
| `rl17_grid` | suite sizes and levels (AC-2), `configHash17` at defaults equals `configHash` (Phase 12-16 hashes unchanged), run lists, plan keys, claiming of runs and of the evaluation with two simulated hosts (AC-4), `projectHours` on hand-made pilot metrics |
| `rl17_update` | board groups (defaults equal `stepSeeds`; the mix and liars), clipped loss on hand-made numbers, liar slots yield no samples (a scripted rollout with 2 liars) |
| `rl17_train` | flag `train`: FR-B4 equivalence with a tiny randomly initialised Qwen2 built locally (warm start's tokenizer; no download) |
| `local_policy` | `guided` default unchanged; HF refuses `guided=True` |
| `rl17_report` | exact tests and Holm on synthetic runs; refusal of incomplete rows (any grid level missing); curves; report and figure; Haiku references recomputed from the saved rows |
| `demo_rl17` | quick end to end |
