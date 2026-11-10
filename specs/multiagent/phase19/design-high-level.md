# Design (high level): Phase 19

Part of [README.md](README.md); requirements are in [requirements.md](requirements.md), and details in [design-low-level.md](design-low-level.md).

## Components

| Component | New or changed | Role |
|---|---|---|
| `nbs/contest.ipynb` -> `explRL/contest.py` | new | `ContestLog` (contests, who saw the lie first, later solves); `preventionBonus`; the all-sharing penalty; `Records` (each agent's own past payoffs over a sequence of 6 boards, arm 4) |
| `nbs/clueboard.ipynb` -> `explRL/clueboard.py` | changed | `scheme='contest'` in `_reward`: credit's `_creditTo`, plus pending prevention bonuses for the contest slots. `'credit'` is unchanged. |
| `nbs/colony_board.ipynb` -> `explRL/colony_board.py` | changed | Squads with uneven liar counts and even guards; the text environment passes `squads` and `guards` through in rollouts |
| `nbs/rl19_grid.ipynb` -> `explRL/rl19_grid.py` | new | `RL19Config`, `configHash19`, the arms and the varied-threat mix, the training world (`worldFor19`, `needWorld19`), `SPEED19`, `PILOT19_PLAN`, `RL19_PLAN`, `projectHours19`, `evalAdapter19` |
| `nbs/rl19_step.ipynb` -> `explRL/rl19_step.py` | new | The threat draws, the step's rollouts, arm 4's records across steps (`RecordBook`), the answer halt |
| `nbs/rl19_suite.ipynb` -> `explRL/rl19_suite.py` | new | `contestSuite`, the sequences, the `WARM_ANSWERS` and pilot cells |
| `nbs/contest_eval.ipynb` -> `explRL/contest_eval.py` | new | `enforceK`, and the Phase 19 columns of each evaluation board (contests, waiting, gullibility, suppression, repeated errors, per-agent task counts) |
| Phase 20 (C1) | to come | Bridged rollouts (squads joined by bridges); A1 trains and evaluates in them (FR-A9) |
| `nbs/rl17_train.ipynb` -> `explRL/rl17_train.py` | changed | `trainRL17` reads the reward scheme, threat mix, penalty, records and the answer halt from the config (defaults unchanged); `trainRL19` is a thin wrapper |
| `nbs/rl19_report.ipynb` -> `explRL/rl19_report.py`, with `rl19_measures`, `rl19_spec`, `rl19_synth` | new | `rl19Summaries`, the measures (`waitCurve`, `waitSlope`, `regret`, `cost0`, ...), arm 4's (specialization, division of labour, persistence, recovery), `writeRL19`, `figRL19`, `syntheticRows19`, `powerPrimary` |
| `nbs/colab_clue_rl.ipynb` | changed | Section "Phase 19": speed check, pilot and main cells, each one cell, resumable and claim-aware |
| `nbs/demo_rl19.ipynb` | new | Quick (synthetic) and full (flag `train`) |

Unchanged: `trainRL`, the credit, team and individual schemes, and every Phase 5-18 configuration hash.

## Data flow

```text
Mac: implement -> offline tests (contest credit on hand-built boards; credit equivalence; squads) -> push
Phase 20 (C1): bridged rollouts built and tested; B3's simulator refit on C1's pilot (P20-13); Gate C1 run
     -> RL19_PLAN['gates']['C1']; Phase 21 (A2): Gate A2 run -> ['A2']
Mac: T5, A1 in squads with bridges (FR-A9); freeze SPEED19 (world from Gate C1) -> push
Colab A: speed check (arm 2, 3 steps, squads of 4 and 8) -> step times, longest prompt (a bridge agent's too), WARM_ANSWERS
         (with and without guards), units per hour
Mac: projectHours19 -> user confirms the pilot; freeze PILOT19_PLAN -> push
Colab A and B: pilot (2 x 10 steps, claimed) -> held-out gain per squad size -> selection
Mac: apply the selection rule; Gate C1 (training world) and Gate A2 (arm 4's records) as recorded; project main-run hours;
     power check; user confirms (P19-6); freeze RL19_PLAN -> push
Colab A and B, one Drive folder: main cell claims the first 2 runs -> stability check on the Mac -> STABLE19 = True
      -> main cell claims the rest -> runs_p19/<arm>_s<seed>
      -> when all 29 runs are final, one host wins the evaluation claim -> contestSuite (gate grid, held-out sizes and
         faults, arm 4's sequences, the best arm in 64-agent squads with bridges) -> eval_p19 -> explRL_rl19.zip
Mac: demo_rl19 full -> Gate A1 -> README, REPORT.md, research plan, preprint if a claim changes
```

## Key decisions

- **Reward shaping on the environment side, not a new algorithm.** Contest credit is a reward scheme in `clueboard`, like credit. The trainer, advantages and KL fix stay Phase 17-18's, so a difference between arms comes from the reward and the threat mix.
- **The bonus is a proxy, priced at evaluation's cost.** A prevented wrong answer is unobservable. "Saw the lie, lacked the clue, later solved correctly" is observable. It is priced at 0.5, the wrong-answer cost at evaluation, not the training cost of 3, and it decays so that delay does not pay.
- **Only a liar's value can be contested for pay.** Otherwise a guard could post a false value and then contest it itself. Honest false posts earn nothing and are tracked as misreporting.
- **Role-conditioned objective.** Guards are paid differently from solvers through the same shared adapter, which is conditioned by the guard instruction in its prompt. One policy must then encode both roles, as a colony's genome does.
- **Varied threat in training, held-out shares at evaluation.** H19-2 is about tracking the threat, so arm 3 trains at a fixed threat as the control, and the shares 2 and 8 of 16 are never trained.
- **A team-level penalty against collapse.** Part B's runs collapsed into all-sharing under team reward. The penalty is collective, so no agent is pushed away from its own role.
- **The plan's world, in the plan's order.** A1 trains in squads joined by bridges (P19-1). Bridges are C1's to build and test (Phase 20), so A1 waits for C1's code and Gate C1; the world is a plan field, and `rl19Config` refuses `'bridges'` until bridged rollouts exist. The plan's fallback, squads without cross-squad subtasks (Stage 4's squads), applies only if Gate C1 fails.
- **One reference for every arm.** The warm start without guards (the plain board in the same squads, world and seeds), so damage won back compares honest losses across arms and cost without liars prices guarding against the same team.
- **A guard-free reference for arm 4.** `WARM_ANSWERS` is measured with and without guards, so arm 4's penalty and answer halt compare it with the warm start in its own, unassigned world.
- **Stopping collapse early.** The plan's answer halt (answers below a third of the warm start's for 3 steps) catches all-sharing during training, which Part B's runs did not flag.

## Gates

1. **Gate C1 recorded** in `RL19_PLAN['gates']`, with each plan's world matching it; the cells assert it. Bridged rollouts must exist for the world 'bridges' and for the 64-agent evaluation.
2. `SPEED19` is frozen before the speed check. `PILOT19_PLAN` is frozen before the pilot.
3. The main runs start only after the user confirms the projected hours (P19-6), and `RL19_PLAN` is frozen and pushed. The cells assert both.
4. **Stability check after the first 2 main runs:** no halt, and in particular no answer halt. The main cell stops after them until `STABLE19 = True`; if either halted, stop and ask.
5. Evaluation and packing run only after every main run has a final adapter, on one host.
6. **Gate A1 (plan: week 10):** H19-1 and H19-2 under Holm, plus the H19-3 constraint. If it fails, and arm 4's specialization at 16 agents does not exceed the warm start's, C3 and further RL of honest teams stop. C4 runs either way.
7. No API calls.
