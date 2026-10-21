# Design (high level): Phase 18, colony rules for large Claude teams

Requirements: [requirements.md](requirements.md). Plan and decisions: [README.md](README.md). Low-level design: [design-low-level.md](design-low-level.md).

## Where each part runs

| Part | Where | Why | Output |
|---|---|---|---|
| 0: numpy screen and forecast | Mac | no model, free; must be committed before any Haiku cell | `results/multiagent/colony/forecast/`, `specs/multiagent/phase18/colony_predictions.json` |
| A: pilot, Stage 1, Stage 2 | Mac | Claude Haiku through the API; the key stays in `.env.local` (never on Colab), so the API runs cannot move to Colab; cells run in parallel processes on the Mac (as Phases 13-15; Phase 14's 33,000 calls took 75 minutes) | `results/multiagent/colony/{quick,pilot,stage1,stage2}/` |
| A: lie tracing | Mac | cached replays, $0 | `trace.jsonl`, `trace_summary.json` per stage |
| B: RL runs and evaluation | Colab, one or two Pro+ accounts | GPU; no key needed; runs and evaluation models claimed per account (Phase 17's `claim`) | Drive `explRL_rl/runs_p18/`, `eval_p18/`, `explRL_rl18.zip` |
| B: analysis | Mac | from the zip | `results/multiagent/rl/eval_p18/` |

## Modules

| Notebook -> module | New or changed | Contents |
|---|---|---|
| `nbs/clue_colony.ipynb` -> `explRL/clue_colony.py` | new | the colony view (values grouped per clue, senders, labels), its board line, the `colony`, `confirm` and guard sentences, the known clues under `colony`, option checks |
| `nbs/colony_agents.ipynb` -> `explRL/colony_agents.py` | new | `ColonyAgent`, `ConfirmAgent`, `GuardAgent`, `ThresholdGuard`, `ColludingLiar`, `MistakenAgent`; `faultClass(world)`, `memberClass(world, slot)` |
| `nbs/clue_text.ipynb` -> `explRL/clue_text.py` | changed (small) | the board line and rules call `clue_colony` when an option is set; `rules(i=None)` for guard slots |
| `nbs/clue_fix.ipynb` -> `explRL/clue_fix.py` | changed (small) | `fixOptions` passes `colony`, `confirm`, `guards` |
| `nbs/clue_policy.ipynb`, `nbs/llm_agent.ipynb` (LLMMember), `nbs/clue_roll.ipynb` | changed (small) | the slot reaches `env.rules(i)`; `rollout`'s callers and `runClue` take the faulty members' class from the world (`fault`); `coopRows` adds Phase 18's columns on Phase 18 cells |
| `nbs/clue_runs.ipynb` -> `explRL/clue_runs.py` | changed (small) | numpy and LLM cells build colony rule agents, guards and faulty members from the world (`faultClass`, `memberClass`) |
| `nbs/colony_trace.ipynb` -> `explRL/colony_trace.py` | new | `replay` (a cell as the runners run it), contamination, reach, suppression and relay (outcome-based, FR-A9), free-riding, misreporting and the action mix; `runColonyCell` runs every Phase 18 cell with these columns; the specialization index and Part B's rollout columns |
| `nbs/colony_grid.ipynb` -> `explRL/colony_grid.py` | new | `COLONY_ARMS`, grids (Part 0, pilot, Stage 1, Stage 2), `COLONY_PLAN`, `COLONY2_PLAN`, cost rules, `goNoGo`, estimates |
| `nbs/colony_report.ipynb` -> `explRL/colony_report.py` | new | measures per cell, exact paired sign-flip tests, Holm, the trend test, bootstrap intervals, summaries, report, figure |
| `tools/colony_forecast.py` | new | Part 0 run and score |
| `nbs/colony32.ipynb` -> `explRL/colony32.py` | new (T6b) | guards at 32 agents: `stage32Grid`, `COLONY32_PLAN`, `stage32Summaries`, `writeStage32` |
| `nbs/colony64.ipynb` -> `explRL/colony64.py` | new (T6d) | guards at 64 agents (lean): `stage64Grid`, `stage64PilotGrid`, `COLONY64_PLAN`, `pilotCheck64`, `costRule64`, `stage64Summaries`, `writeStage64` |
| `nbs/colony3.ipynb` -> `explRL/colony3.py` | new (T6c) | Stage 3: `stage3Grid`, `stage3PilotGrid`, `stage3Estimate`, `costRule3`, `complianceGate`, liar and volunteering measures, `runStage3Cell`, `COLONY3_PLAN`, `stage3Summaries`, `writeStage3` |
| `nbs/clue_colony.ipynb`, `nbs/clue_text.ipynb`, `nbs/clue_runs.ipynb`, `nbs/colony_trace.ipynb`, `nbs/clue_roll.ipynb` | changed (T6c) | the deceiver and volunteer sentences; `fault = 'adaptive'` (Claude agents in the liar slots, the share exemption, call counting) in every LLM runner; `volunteer` |
| `nbs/demo_colony.ipynb` | new | the Part 0 summary, quick, pilot, Stage 1, go/no-go, Stage 2, the 32-agent run (`stage32`), Stage 3 (`stage3pilot`, `stage3`), guards at 64 (`stage64pilot`, `stage64`), cached reruns |
| `nbs/rl17_grid.ipynb`, `nbs/rl17_train.ipynb` | changed (small) | `RL17Config.world` (default `()`, outside the hash at the default), passed to every rollout; `trainRL17` logs `longest` (`rl17_update.pairLengths`) for the speed check |
| `nbs/rl18_grid.ipynb` -> `explRL/rl18_grid.py` | new | Part B arms, runs, `colonySuite`, `RL18_PLAN`, `rl18Config`, hours projection |
| `nbs/rl18_report.ipynb` -> `explRL/rl18_report.py` | new | H18-B1 to H18-B4, report, figure (the specialization index and its null come in the evaluation rows, from `colony_trace`) |
| `nbs/colab_clue_rl.ipynb` | changed | "Phase 18 speed check" and "Phase 18 main" cells (claims, evaluation, pack) |
| `nbs/demo_rl18.ipynb` | new | Part B analysis on the Mac (the speed check is read on Colab) |

## Data flow

```
Part 0 (Mac, numpy) --forecast committed--> COLONY_PLAN frozen --> pilot (Mac, Haiku, N 16, not analysed)
   --cost rule--> Stage 1 (Mac, Haiku, N 8 and 16, 8 seeds) --> tracing ($0) --> colonySummaries, forecast score
   --goNoGo--> stop (report)  |  go --> user raises the cap --> COLONY2_PLAN frozen --> Stage 2 (Mac, Haiku, N 32 and 64)
                                                                                         --> trend test, forecast rescore
   stop, decline not significant --> user-approved deviation: COLONY32_PLAN frozen --> guards at N 32, three faulty-member kinds
   --> Stage 3: regression gate --> COLONY3_PLAN frozen --> pilot (N 16, compliance gate, cost rule) --> Stage 3 (N 16, adaptive
       liars and volunteers; Stage 1's references replayed from the cache, $0) --> stage3Summaries
   --> guards at 64 (second deviation): COLONY64_PLAN frozen --> one-board pilot (invalid, cost rule $35) --> 16 boards --> stage64Summaries
Phase 17 recipe frozen + Stage 1 done --> Part B speed check (Colab: seconds per step, maxLen, projected hours) --> user confirms --> RL18_PLAN frozen
   --> Part B main (Colab, accounts A and B: claimed runs, then claimed evaluation models) --> explRL_rl18.zip --> Mac analysis
```

## Two Colab accounts (Part B)

As Phase 17: both accounts share `MyDrive/explRL_rl` (the second through a Drive shortcut with the same path, because the configuration hash includes the model path). Each sets its own `HOST` and runs the same cell. A run folder's `claim.json` decides who trains it; a run checkpoints every step, so when a session ends (about 24 hours) the same cell resumes it. When every run is final, evaluation models are claimed one at a time (`eval_p18/claims/<model>`), so both accounts evaluate in parallel; the account that finds all evaluated wins `_pack` and writes the zip. `TAKEOVER` moves a run between accounts (stop the first runtime first).

## Gates

1. No Haiku cell before the forecast is committed (FR-03).
2. No main cell before the plan covering it is frozen and its hash recorded (`COLONY_PLAN`, `COLONY2_PLAN`, `COLONY32_PLAN`, `COLONY3_PLAN`, `COLONY64_PLAN`, `RL18_PLAN`).
3. Stage 2 only on a `go` verdict and after the user raises the API cap.
4. Guards at 64: no live cell before `COLONY64_PLAN` is frozen; the 16 boards only if the pilot's invalid share is under 5% and the cost rule says run (`stage64pilot`, then `stage64`).
5. Stage 3: no live cell before the regression gate (AC-11) passes and `COLONY3_PLAN` is frozen; no main cell unless the pilot passes the compliance gate and the cost rule; each live step behind its own `EXPLRL_COLONY_STAGE` value (`stage3pilot`, then `stage3`).
6. Part B only after `RL17_PLAN` is frozen with a recipe (Phase 17's pilot v3) and Stage 1 is done (the colony option tested live), and after the user confirms the projected GPU hours.

## Reuse

`runWorkload`, the response cache, the spend ledger and the client (Phases 10-14); `fixEstimate`, `cellCalls` and the cost-rule pattern (Phase 14); `Tracer`-style cached replays (Phase 15); `signFlip`, `permTest` and `hierBoot` patterns (Phases 16-17); `trainRL17`, `claim`, `stream`, `packZip`, `evalModels` (Phase 17).
