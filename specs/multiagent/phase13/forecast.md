# Forecast: can a numpy simulation predict the LLM RL arms?

Status: **plan frozen** (2026-10-16), before the full numpy run and before any Phase 13 Track B evaluation result exists. Part of [README.md](README.md) (Phase 13); evidence for the companion paper on simulation-first design ([../LITERATURE.md](../LITERATURE.md), section 14, gap 5).

## Question

Phases 10-11 found that numpy rule agents rank harness designs as LLM teams do. Does the same hold for **RL reward designs**: does training simple numpy agents under each reward design predict, in sign, what the same design does to a 3B LLM trained with RL? If so, reward designs could be screened for free before GPU runs.

## What is predicted, and what is already known

| Arm | LLM run | Status of the LLM result when this plan was frozen |
|---|---|---|
| `individual`, `team`, `credit` | Phase 12 v2 (one seed each) | known (**retrodiction**) |
| `indpen`, `credturn` | Phase 13 Track B (two seeds each) | unknown: runs in progress on Colab; no evaluation row exists. Seen so far: the training log of `credturn_s1` up to step 27 (training welfare flat at 0.21-0.29, KL to the warm start about 0.4), no evaluation (**forecast**) |
| `credit` seed 2 | Phase 13 Track B | unknown (a replication check of the numpy `credit` prediction) |

## The numpy model (fixed before running; `tools/rl_forecast.py`)

- **Agents:** the Phase 11 rule agent (`RuleAgent`, share policy `'always'`) on the clue board with Phase 11's settings (`CLUE_SETTINGS`: two clues per subtask, answers below 30, wrong answer 0.5), blackboard, N = 4, one policy shared by all four agents (as the shared LoRA adapter).
- **Two learned decisions:** (1) share a shareable clue or not, one logit; (2) guess on an undetermined open subtask or wait, one logit per candidate bucket (at most 2, 3, 6, more). Everything else is the rule agent (submit when determined, open the subtask with most known clues).
- **Warm start** (the imitation step's analogue, imperfect like the LLM's): share with probability 0.9, guess with probability 0.1 (logits +2.2 and -2.2); the rule teacher shares always and never guesses.
- **Training** (as `RL_PLAN` v2 where it applies): 60 steps; 8 board seeds per step, each played 4 times (the group); 10 turns per agent; group-relative advantages (per board and agent, or per turn from the reward-to-go for `credturn`); the training-only wrong-answer cost of 2.5 for `indpen` and `credturn`; policy gradient on the logged decisions with Adam, learning rate 0.05. No KL term (the policy has two kinds of parameters only).
- **Arms:** `individual`, `team`, `credit` (board penalty only); `indpen` (individual + 2.5); `credturn` (credit + 2.5 + per-turn advantages). Five training seeds per arm (0-4).
- **Evaluation:** the LLM evaluation's 15 main boards (seeds 900-904, 930-939), 40 turns per agent, 4 sampling repeats per board, with the LLM evaluation's metric definitions: welfare per agent-turn, shares per held clue (`clueMetrics`), solo share and wrong answers per solve (`coopMetrics`).

## Scoring rule

- For each arm and metric (welfare, shares per held clue, solo share, wrong answers per solve), the **numpy effect** is the arm's mean minus the warm start's, averaged over training seeds, with a 95% bootstrap interval over the five training seeds. Its **sign** is +, - or 0 (0 when the interval includes 0).
- The **LLM effect** is the same difference on the evaluation boards, paired on board seed (Phase 13 arms: both training seeds pooled), with its 95% bootstrap interval; its sign is classified the same way.
- **Score:** the share of (arm, metric) pairs whose signs agree, reported separately for the retrodiction (3 arms x 4 metrics = 12) and the forecast (2 arms x 4 metrics = 8), plus the `credit` replication (seed 2 against the numpy `credit` sign). A sign agreement counts 0 against 0 as agreement. No partial credit.
- **Headline forecast:** the sign of `credturn`'s welfare effect (does RL with per-turn credit and the loophole closed beat the warm start?) and of `indpen`'s shares-per-held-clue and solo-share effects (does pricing the loophole stop the selfish drift?).

## Order

1. Commit this plan and `tools/rl_forecast.py` (the method is frozen here).
2. Run the numpy model once; commit its output and the predicted signs, with the retrodiction score against Phase 12, before downloading the Colab zip.
3. After the Phase 13 evaluation, score the forecast with this rule, unchanged.

## Numpy run and frozen predictions (2026-10-16)

Run once with the frozen method (`tools/rl_forecast.py`, 5 arms x 5 training seeds, 50 s on the Mac); predictions computed with `tools/forecast_score.py` and copied to [forecast_predictions.json](forecast_predictions.json). Committed before the Phase 13 Colab results were downloaded or evaluated.

Numpy effect against the warm start (mean over training seeds [95% CI], sign):

| arm | welfare | shares per held clue | solo share | wrong per solve |
|---|---|---|---|---|
| individual | -0.060 [-0.064, -0.058] - | -0.486 - | +0.047 + | +0.115 + |
| team | +0.038 [+0.037, +0.040] + | -0.274 - | +0.003 + | +0.005 + |
| credit | +0.038 [+0.037, +0.039] + | -0.264 - | +0.002 + | +0.005 + |
| **indpen** (forecast) | -0.062 [-0.067, -0.056] - | -0.477 - | +0.023 + | +0.054 + |
| **credturn** (forecast) | +0.037 [+0.037, +0.038] + | -0.275 - | +0.003 + | +0.003 + |

Learned policies: sharing probability fell from 0.90 to about 0.30 under individual reward (with or without the guessing cost) and to about 0.55 under team, credit and credturn; guessing changed little (the warm start guesses 10%).

**Retrodiction against Phase 12: 7 of 12 signs agree.** Individual 4 of 4 (less sharing, more guessing, more wrong answers, lower welfare); team 3 of 4 (the numpy model predicts a small welfare gain, the LLM run collapsed: training instability is outside a two-parameter model); credit 0 of 4 (numpy: less sharing, a small gain; LLM: slightly more sharing, no change).

**Forecast for Phase 13, frozen:** `indpen`: pricing the guessing loophole does **not** stop the selfish drift (sharing -0.48, welfare -0.06; guessing rises half as much as without the cost), against H13-4; `credturn`: welfare **above** the warm start (+0.037), in line with H13-5, with less sharing than the warm start; `credit` seed 2: the numpy `credit` signs.

**A lesson recorded now, not applied:** the numpy runs vary so little across training seeds that effects of +0.003 get a definite sign, while the LLM's intervals call such effects 0. The frozen rule is kept; a practical-significance threshold (for example, |effect| below 10% of the warm start's value counts as 0) will be reported separately, labelled post hoc.
