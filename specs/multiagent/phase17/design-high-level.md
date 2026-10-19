# Design (high level): Phase 17

Part of [README.md](README.md); requirements in [requirements.md](requirements.md); details in [design-low-level.md](design-low-level.md).

## Components

| Component | New / changed | Role |
|---|---|---|
| `nbs/rl17_grid.ipynb` -> `explRL/rl17_grid.py` | new | `teamSizeSuite`, step-0 model list, `RL17Config`, pilot and main run lists, `PILOT17_PLAN`, `RL17_PLAN`, claim helpers |
| `nbs/rl17_update.ipynb` -> `explRL/rl17_update.py` | new | the step's pieces: `boardGroups`, `clippedTerm`, `valueMask`, `tokenTerm`, `cutCount`, `ppoUpdate`, `saveTurns` |
| `nbs/rl17_train.ipynb` -> `explRL/rl17_train.py` | new | `trainRL17`, `makePolicies17`: mixed team sizes and liars per step, `epochs` clipped-ratio updates, `lrFixed`; reuses `rl_adv`, `rl_torch`, `rl_control` |
| `nbs/local_policy.ipynb` -> `explRL/local_policy.py` | changed | `guided=True`: vLLM structured outputs with the reply schema (default off: unchanged behaviour) |
| `nbs/rl17_report.ipynb` -> `explRL/rl17_report.py` | new | `rl17Summaries`, `writeRL17`, `figRL17`, `syntheticRows17`; tests from `rl16_report` |
| `nbs/colab_clue_rl.ipynb` | changed | three sections (step 0, pilot, main), each one cell, resumable, claim-aware; `HOST` and `RUNS17` in the configuration cell |
| `nbs/demo_rl17.ipynb` | new | quick (synthetic), full (flag `train`) |

Unchanged: `clue_rl.trainRL` and every Phase 12-16 configuration hash.

## Data flow

```
Mac: implement -> test -> push
Mac: freeze PILOT17_PLAN -> push
Colab, account B (in parallel with Phase 16 on account A): pilot (4 x 30 steps, one cell) -> runs_p17pilot, selection -> explRL_rl17pilot.zip
Colab, account A after Phase 16: step 0 (eval only, all 15 adapters) -> eval_p17s0 -> explRL_rl17s0.zip
Mac: step-0 curves (baseline); pilot selection, recipe, projected hours -> user confirms
Mac: apply the selection rule; project main-run hours from the pilot's step times; user confirms; freeze RL17_PLAN -> push
Colab, one or two accounts on the same Drive folder: main cell (claims runs) -> runs_p17/<arm>_s<seed>
      -> when all 13 runs are final: one host wins the evaluation claim -> evaluation (teamSizeSuite) -> eval_p17 -> explRL_rl17.zip
Mac: demo_rl17 full -> report, curves -> README, REPORT.md, preprint, summary page
```

## Key decisions

- **A new trainer, not a modified one.** `trainRL` stays as it is, so Phase 12-16 runs remain reproducible; `trainRL17` reuses its pieces and is tested to equal it in the default configuration.
- **The recipe is chosen by a frozen pilot on training boards.** Held-out boards are only for evaluation.
- **Training on the conditions the claim is about.** The main arm trains on larger and adversarial teams; the ablation trains as before, so H17-5 separates "any stronger RL" from "training on bigger teams".
- **Evaluation fixes the memory setting** (notes, as all trained models); Haiku's full-memory curves are references only.
- **Run claiming** lets several Colab accounts share one Drive folder safely; takeover is explicit.

## Gates

1. Step 0 is complete only with Phase 16's adapters (the cell evaluates what exists and is rerun after Phase 16); the pilot may run in parallel on another account.
2. `PILOT17_PLAN` frozen and pushed before the pilot cell; `RL17_PLAN` frozen and pushed before the main cell (each cell asserts it).
3. The main runs start only after the user confirms the pilot-projected hours.
4. Evaluation and packing only after every main run has a final adapter, on one host.
5. No API calls.
