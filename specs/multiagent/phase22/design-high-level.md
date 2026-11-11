# Design (high level): Phase 22

Part of [README.md](README.md); requirements are in [requirements.md](requirements.md), and details in [design-low-level.md](design-low-level.md).

## Components

| Component | New or changed | Role |
|---|---|---|
| `nbs/b3_agents.ipynb` -> `explRL/b3_agents.py` | new | `B3_KNOBS`, `B3Params`, `b3Rng`, the wrappers that add `trustOne`, `spread` and `shareAll` to honest members, `b3Members`, `b3Replay` lives in `b3_fit` |
| `nbs/b3_fit.ipynb` -> `explRL/b3_fit.py` | new | `FIT_CELLS`, `FOLDS`, `claudeTargets`, `simCell`, `gridSim` (with its disk cache), `loss`, `fit`, `heldOut`, `chooseKnob`, `bootTau`, `refit`, `fitHealth` |
| `nbs/b3_forecast.ipynb` -> `explRL/b3_forecast.py` | new | `Effect`, `estimate`, `forecastSim`, `forecastPilot`, `forecastNaive`, `forecastExperiment` (the entry point), `writeForecast`, `scoreExperiment` |
| `nbs/b3_effects.ipynb` -> `explRL/b3_effects.py` | new | `C1_EFFECTS`, `A2_EFFECTS`, `RETRO_EFFECTS`, `c1Forecast`, `a2Forecast` (C2's and C4's lists go in their own specs' modules) |
| `nbs/b3_report.ipynb` -> `explRL/b3_report.py` | new | `B3_PLAN`, `retrospective`, `poolScores`, `gateB3`, `writeB3`, `figB3`, `syntheticB3` |
| `nbs/demo_b3.ipynb` | new | Stages `quick`, `fit` and `forecast` behind `EXPLRL_B3_STAGE` |
| `tools/b3_run.py` | new | The multiprocess script (`__main__` guard): `grid`, `fit`, `retro`, `forecast <exp>`, `score <exp>` |
| `nbs/sidebar.yml` | changed | The six new notebooks |
| Phase 20's `bridge_agents` | changed in Phase 20 (P22-12, accepted 2026-11-10) | Honest rule agents post a held cross clue on its mirror |

Unchanged: `clue_agents`, `colony_agents`, every board, every earlier tool script, every frozen forecast, score and plan of Phases 13-21, and every Phase 5-21 hash.

## Data flow

```text
Mac: implement b3_agents, b3_forecast (naive and pilot-only first, for A2), b3_fit, b3_effects, b3_report
     -> offline tests (defaults reproduce cached numpy rows; behaviours; fit recovers a planted θ; forecasters; scoring) -> push
Mac: freeze B3_PLAN (cells, folds, grid, loss, knob candidates and rule, refit, forecasters, scoring, gate) -> push
Mac, laptop (about 6 hours, once): timing probe -> coarse grid for 3 knob candidates x trustOne -> chooseKnob
     -> fine grid -> θ0 per fold and on all cells -> bootTau -> fitHealth
Mac ($0): retrospective on paper2's 11 calls (4 folds; each study's own pilot, seed 1890)
     -> results/multiagent/b3/retro.md -> report to the user; stop and ask only on a fit-health failure
Phase 20: bridge board, RuleBridge, mirror posts (P22-12); C1 pilot (seed 1890, 3 boards at 64 agents)
Mac (under 1 hour): c1Forecast: θ0 without C1's reused cells -> refit on the pilot's contamination -> five lines
     -> specs/multiagent/phase20/c1_predictions.json, committed; SHA-256 into C1_PLAN (Phase 20 T9) -> push
     -> C1's main run may start
Phase 21 (any time): a2Forecast (naive and pilot-only) -> a2_predictions.json -> SHA-256 into A2_PLAN's second version
C2, C4 part b (later): their effects, cells and pilots -> forecastExperiment -> their frozen plans
After each main run: the experiment's report -> scoreExperiment -> <exp>_score.json
After the last one (plan: weeks 14-16): poolScores -> gateB3 -> results/multiagent/b3/report.md, b3.png
     -> README results, REPORT.md, the research plan's B3 line; paper2 only where a claim changes
```

## Key decisions

- **Fit mechanisms, score outcomes.** The fit sees only two mechanism measures, clean pooled share and the share of honest answers built on a lie. Most scored effects are honest-pooled-share contrasts on liar boards. Some are contrasts on the fit's own measures (H18-2 on contamination; H18-3, C1-7 and C1-8 on clean boards, where honest pooled share is pooled share), but never on cells the fit saw: folds drop them, and C1's clean arms are new. So the fit never sees the boards it is scored on, although the measures overlap.
- **Leave one study out for the retrospective check.** Each of paper2's three forecast studies is scored with a θ fit without any cell that enters its contrasts. Forward forecasts drop the cells the experiment reuses as arms. Neither removes the bias of having chosen the behaviours after seeing the misses; the report says so.
- **Defaults draw nothing.** The behaviours use their own random generator, made only when a parameter is not at its default. So the unfitted simulator is exactly today's, and every earlier forecast and hash stands.
- **One knob per behaviour.** Behaviour 2 has an obvious knob (`trustOne`). Behaviour 1 has no settled cause: rule agents crowd onto the top-ranked subtask, share only for subtasks a teammate has open, and never guess, and Claude agents differ on all three. Week 1 picks one of the three candidates by held-out error, under a rule frozen in `B3_PLAN`. Two parameters keep the fit readable, and a 1-3 board pilot cannot inform more.
- **The pilot refit shrinks to the cached-run fit.** A pilot of 1-3 boards is noise next to 30 cached cells. A Gaussian penalty with the cached fit's bootstrap spread lets the pilot move θ only as far as its evidence warrants, and parameters it has no measure for stay put.
- **Four forecasters, one rule.** All give a sign per effect and are scored by paper2's rule. Pilot-only has no interval, so it always calls when it can compute an effect; every-design-helps always calls. A predicted 0 on a conclusive outcome is wrong, so abstaining is not free.
- **The gate counts.** With 15-25 calls expected, B3 reports counts and an exact McNemar p beside them, not calibration. The fitted simulator must beat each alternative outright. Ties fail.
- **Experiments own their effects; B3 owns the rules.** C1's and A2's lists are written in B3 because their specs are decided. C2 and C4 part b write theirs in their own specs, through the same entry point.

## Gates

1. **Regression gate** before any fit: NFR-1, and the full suite.
2. **`B3_PLAN` frozen and pushed** before the week-1 fit (NFR-7).
3. **Fit health** (P22-11): a parameter at the top of its range (P22-21; a knob at 0 is reported, not a stop), or H22-3 failing, stops B3 and asks the user before C1's forecast. Otherwise the retrospective check is reported and nothing waits on its score.
4. **Before each main run:** the experiment's forecast is committed and pushed and its SHA-256 recorded in its frozen plan. C1's main run cannot start without it (P20-13). A2's runs do not wait (P21-8).
5. **Gate B3** (plan: week 16): P22-10's counting rule on the pooled common set, read only with at least 8 conclusive items. It gates nothing downstream. Its result goes to the Stage 2 decision on whether a fitted screen is worth running before expensive experiments.
