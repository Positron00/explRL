# HiddenBench replication of the vote fixes

Status: **done** (2026-10-16): the fact table did not replicate; the speak-up instruction helped through disclosure (results below). Earlier: pilot passed, `HB_PLAN` frozen at `a75f11f` (hash `791a2df079a8`). Part of [README.md](README.md) (Phase 13); the top-ranked gap of [../LITERATURE.md](../LITERATURE.md), section 14.

## Question

A3 found, on our templated vote, that a structured table of the facts posted so far improved decisions without increasing disclosure (lone-dissenter gap closed 0.75), that enforcing facts first did nothing, and that a prompt to speak up helped in one variant. Do these hold on an established benchmark, where groups of LLM agents reach about 30% against 81% for one agent with all facts (HiddenBench, Li, Naito and Shirado, ICML 2026)?

## Data and protocol

- **Tasks:** HiddenBench's 65 tasks, vendored unchanged in `data/hiddenbench/benchmark.json` (MIT; sha256 prefix `2815afffca4e470d`). Each task: a description, 3 or 4 options with one correct, shared facts (all agents), and 3-4 hidden facts, hidden fact j held by agent j.
- **Protocol (ours, not HiddenBench's):** four Claude Haiku 5.5 agents (effort low), three rounds of simultaneous posts on a shared board (a fact, published verbatim, or a short opinion), then a private vote; the task's own description precedes our protocol text (`explRL/hidden_bench.py`). HiddenBench itself uses sequential messages over more rounds; absolute numbers therefore differ from the paper's, and the comparison that matters is between our arms.
- **Arms:** as A3: `baseline`, `factsFirst` (round 1 accepts facts only), `table` (a deduplicated list of the facts posted so far, without senders), `dissent` (the instruction to speak up), plus the one-agent ceiling (`solo`: every fact, then the vote).
- **Episodes:** each task 3 times (episode seed = 1000 x task id + rep: option order and fact order shuffled per seed), the same seeds for every arm and the ceiling: 195 episodes per arm, 975 in all, about 12 700 calls (about $3-6; the token profile is the vote's provisional one).

## Analysis (`HB_PLAN` in `nbs/fix_grid.ipynb`, frozen after the pilot)

- **Primary:** win rate (strict majority for the correct option) gap closed by `factsFirst` and `table` against `baseline`, with the solo ceiling, paired on episode seed, bootstrap over episodes; Holm over the two tests.
- **Control:** `dissent`, the same way.
- **Secondary:** agent accuracy (the share of agents voting for the correct option, HiddenBench's default metric) per arm; disclosure (hidden facts posted per hidden fact held); invalid replies.
- **Directions expected from A3:** `table` closes part of the gap; `factsFirst` does not; `dissent` unclear (helped in one A3 variant, not the other).

## Pilot and bands (AC-6 style)

`baseline` and `solo` on the first 20 tasks, one rep (340 calls). Freeze only if: invalid replies under 5%; solo ceiling at least 0.8; and a gap of at least 0.2 between the ceiling and the baseline win rate. If not, stop and ask (no tuning of tasks or protocol on the main data).

## Order

1. Commit this plan, the adapter and the grids (`HB_PLAN` unfrozen).
2. Pilot; record it here; freeze `HB_PLAN` and commit.
3. Main run (`demo_hb`, `--flags llm`); cached rerun byte-identical; results here, in the Phase 13 README and in the preprint.

## Pilot (2026-10-16)

`baseline` and `solo` on tasks 1-20, one rep, 340 calls, $0.10 (about $0.0003 per call: 784 uncached input, 410 cache-read, 442 cache-write and 318 output tokens on average). Bands: invalid replies 0.6% (under 5%); solo ceiling 0.95 (at least 0.8); gap 0.95 - 0.75 = 0.20 (at least 0.2, met exactly). `HB_PLAN` frozen unchanged at `a75f11f` (`coopHash(HB_PLAN)` = `791a2df079a8`).

Note: the baseline is far above HiddenBench's reported group accuracy (agent accuracy 0.79 here against 30.1% there). Our protocol differs (facts published verbatim on a shared board, simultaneous rounds, three rounds), the model may differ (we have not checked the paper's model list), and the pilot used only the first 20 tasks. Which of these explains the difference is not tested here; a HiddenBench-protocol baseline (sequential free messages) would separate protocol from model.

## Results (2026-10-16; exploratory)

Main run: 975 episodes (65 tasks x 3 reps x 5 arms), 12 675 calls, $3.46 (API total $60.73 of $150); cached rerun byte-identical and free. Report: `results/multiagent/hiddenbench/full/report.md`.

| arm | win rate (majority) | agent accuracy | hidden facts disclosed | gap closed [95% CI] | Holm p |
|---|---|---|---|---|---|
| baseline | 0.77 | 0.79 | 0.74 | | |
| factsFirst | 0.78 | 0.82 | 0.76 | 0.11 [-0.37, 0.45] | 1.00 |
| table | 0.76 | 0.80 | 0.76 | -0.07 [-0.69, 0.30] | 1.00 |
| dissent (control) | 0.83 | 0.85 | 0.88 | 0.41 [0.00, 0.71] | control (p 0.090) |
| solo | 0.91 | | | | |

- **The table does not replicate.** A3's strongest vote result (lone-dissenter gap closed 0.75) does not hold on HiddenBench (-0.07); facts-first does nothing here either, as in A3.
- **The instruction to speak up is the arm that moves**, through disclosure (hidden facts posted 0.74 -> 0.88), the opposite mechanism to A3's table. It was the control arm, its interval touches 0, and it was not Holm-tested: suggestive only.
- **Little headroom.** Our protocol's baseline (agent accuracy 0.79) is far above HiddenBench's reported 30%, and the solo ceiling is 0.91; the gap was 0.14 of win rate, which limits what any arm could close. Whether the protocol (facts posted verbatim, simultaneous rounds) or the model explains the high baseline is untested.
- **Refusals:** 412 of 12 675 replies (3.3%) ended with the model's refusal stop reason partway through the JSON, in every arm including solo; they count as invalid (no post or vote) and are balanced across arms.

What changes in the claims: "aggregation, not only disclosure" is withdrawn as a general claim; it held on our templated vote, whose facts favour or oppose an option explicitly, and not on HiddenBench, whose facts must be interpreted. The preprint (`paper/`) was revised accordingly.
