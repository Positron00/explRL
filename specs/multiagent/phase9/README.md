# Spec: Phase 9, safety and mechanism design

Status: **implemented** (2026-10-11). Results below; how to run: [RUN.md](RUN.md). Part of the multi-agent plan: [../README.md](../README.md). Builds on Phase 8: [../phase8/README.md](../phase8/README.md).

## Goal

Find out how the communication harnesses fail when some agents are bad, and which defences restore them at what cost. Phase 8 showed that a shared blackboard makes large teams far more productive and of one mind; the plan's hypothesis is that the same sharing makes them more vulnerable to liars.

1. **Three bad-agent types:** a *liar* (reports danger and empty spots as good and good patches as danger), a *free-rider* (goes only where others report value, never explores, never shares) and a *saboteur* (crowds the best reported patch). Swept over 0, 1, 10% and 25% of the team.
2. **Defences:** private *trust* (each agent weights a sender by how well its reports matched what the agent later saw), shared *reputation* (one public record pooled from everyone's checks) and *graduated sanctions* (Ostrom: a warning, then half weight, then loss of write access), with *monitoring* (deliberate spot-check trips at rate `q`) whose cost is counted.
3. **Interpretability:** compare what an agent *believes* (its own estimates, readable from its state) with what it *reports*; report how well this white-box score and the defences' black-box scores pick out liars (detection AUC).
4. **Confirmatory test H3, pre-registered in Phase 8:** one liar costs honest agents a larger share of their welfare with the blackboard than with messages.
5. **Outputs:** honest and team welfare against the number of bad agents, per channel and defence; defence cost without attack; monitoring cost against benefit; detection AUC; the H3 result.

Phase 9 adds no new channels, no language models (Phase 10) and no defences for the hierarchical lead or for circuit teams (out of scope).

**Main acceptance tests:** (a) with no bad agents and no defence, runs equal Phase 8 runs exactly, and every Phase 5-8 result is unchanged; (b) each bad agent, defence and metric matches hand-checked examples; (c) H3 runs once, on unseen seeds, after its pre-registration is committed; (d) the exploratory grids run in under 30 minutes.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, the pre-registered H3 analysis, acceptance criteria, out of scope |
| [design-high-level.md](design-high-level.md) | Modules, data flow, main decisions and rejected alternatives, risks |
| [design-low-level.md](design-low-level.md) | Classes, signatures, rules for bad agents and defences, metrics, grids, defaults, demo layout |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks |
| [RUN.md](RUN.md) | How to run the tests, H3, the exploratory grids and the regression checks |

## What Phase 8 gives us (the facts the design depends on)

| Piece | Fact | Consequence for Phase 9 |
|---|---|---|
| `CommBandit` | Reads the channel in `_stats`, acts by UCB, learns from its own stays in `learn`, then writes (blackboard) or sends (messages); draws no random numbers | Bad agents are small subclasses that override what they write or how they choose; defended agents override how they weight what they read |
| `Blackboard` (`K = None`) | Keeps each writer's faded sums (`Si`, `Ci`) next to the totals | Per-sender trust weights cost one `(n x L)` product per read; sanctions can block a writer |
| `MessageBus` | Every message carries its sender | Trust and sanctions apply to messages the same way |
| `bench_grid` | Parallel deterministic runner, CSV, `confirm` (sign-flip, Holm, verdicts), `PREREG` frozen at hash `8a59293847ae` | Phase 9 reuses them; two backward-compatible amendments (a runner argument, a study key) leave the Phase 8 hash and results unchanged |
| Phase 8 results | Blackboard best from 4 agents up; `messages` adds about nothing over `none`; confirmatory seeds 100-129 and exploratory 200-209 used | H3 uses new seeds 300-329; exploratory runs use 400-409 |
| Pilot (seeds 1000-1011, 2026-10-11) | 25% liars cost honest agents 24% (N = 16) and 46% (N = 64) of their welfare on the blackboard and about nothing through messages; one liar costs 4-8% on the blackboard at N = 8-32; free-riders and saboteurs barely lower honest welfare per agent and at N = 64 even raise it (fewer competitors); private trust recovers part of the liar damage (N = 64, 25% liars: 0.145 to 0.203) but costs 8% with no attack at N = 16 and gains 20% at N = 64 | The attack has room to matter; honest *and* team welfare are both reported; a defence's cost without attack is a first-class result; H3 sizes are 8, 16, 32 (pilot contrast +0.046, dz 1.85 on 12 seeds) |

## Decisions

| ID | Question | Answer |
|----|----------|--------|
| C1 | Bad-agent behaviour | **Liar:** forages and learns honestly for itself, but each blackboard write reports `-dangerCost` where it harvested and `c` (the best solo rate) where it did not; each message offers its *worst* own location as worth `c`; lead reports are the same lie. **Free-rider:** reads the channel, goes to the reported-positive location it rates best (no exploration bonus), stays put when nothing is reported, never writes or sends (with a lead: follows assignments, never reports). **Saboteur:** always goes to the location with the highest reported value and stays, never writes (with a lead: goes where the lead has sent most followers) |
| C2 | Which agents are bad | The first `b` agent indices; start positions are random per world seed, so the choice is neutral. Counts: 0, 1, `round(0.10 N)`, `round(0.25 N)` (N = 16: 0, 1, 2, 4; N = 64: 0, 1, 6, 16) |
| C3 | Harm metrics | **Honest welfare** per honest agent-second (harvest minus danger cost of agents `b .. N-1`) is the primary harm measure; **team welfare** per agent-second (all agents) is reported too, because free-riders and saboteurs can lower the total while raising honest per-agent shares. **Relative loss** = 1 - W(attacked) / W(clean), paired on seed, size, channel and defence, where the clean run has honest agents in the same slots |
| C4 | Defences (blackboard and messages) | **D0** none. **D1 private trust:** each agent keeps a trust `tau[s]` per sender, updated after each of its own stays against what that sender currently reports there; reads are weighted `w x tau[s]`. **D2 shared reputation:** one `Monitor` keeps `rho[s]`, updated by every agent's checks; everyone reads with `w x rho[s]`. **D3 graduated sanctions:** D2 plus strikes: a check with error above `theta` adds a strike to the sender; a strike counts for 120 s (a sliding window, so old strikes are forgiven); the sanction level is the number of strikes in the window: 1 = warning, 2 = half weight, 3 or more = write access revoked (the channel drops its writes and messages) until strikes leave the window |
| C5 | Monitoring | **Deliberate spot checks at rate `q`:** at each event, with probability `q` (own seeded generator), an agent travels to the highest-valued reported location it has not stayed at in the last `Tmove` and stays once; that stay is a check like any other. Monitoring cost = agent-seconds spent on check trips. D1 runs with `q = 0` by default (passive); the monitoring sweep compares D1, D2 and D3 at the same `q`, as the plan asks ("compared with trust weighting at the same monitoring cost") |
| C6 | Trust update | Exponential moving average of a match score: `tau <- (1 - alpha) tau + alpha exp(-|m - r| / sigma)`, with `m` the sender's current report at the location and `r` the observed rate; `alpha = 0.1`, `sigma = 0.5` (pilot). Starts at 1 (trusting) |
| C7 | Interpretability | **White-box score:** per agent, the mean over its writes and sends of `|reported value - its own belief at that location then|` (own belief: its own-stays estimate). **Black-box score:** 1 - mean trust given to it by honest observers (D1) or 1 - its reputation (D2, D3). Detection AUC = probability that a random liar scores above a random honest agent. Liar runs on the blackboard and messages only (free-riders and saboteurs do not report, and lead followers have no per-agent beliefs). Honest agents are always `DefendedBandit`s, which equal `CommBandit` when undefended, so their reports are logged in every run |
| C8 | Lead and `none` | The hierarchical lead and the `none` channel take part in the attack grid without defences: `none` is the control (bad agents can only hurt through a channel), the lead is the centralised baseline. Defences for the lead are out of scope |
| C9 | H3 (confirmatory, own family) | Cells: blackboard and messages, fixed compute, sizes 8, 16, 32, one liar vs clean, no defence, seeds 300-329. Per seed: mean over sizes of relative honest-welfare loss; contrast blackboard minus messages; expected sign +; two-sided sign-flip test, 10 000 flips, alpha 0.05 (a family of one) |
| C10 | Seeds | H3 300-329 (never used before); exploratory 400-409; pilot and calibration 1000-1099 |
| C11 | Calibration (before freezing) | `theta` = the smallest of (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0) at which honest agents are sanctioned at level 2 or more in at most 5% of clean runs (pilot seeds, N = 16 and 64, `q = 0.05`). H3 depends on no calibrated value; its pre-registration is frozen with the calibration anyway |
| C12 | Code reuse | Amend `bench_grid.runGrid` to take the cell runner as an argument and `confirm` to read the study name from the pre-registration (default `'main'`); `Blackboard` and `MessageBus` gain an (empty by default) set of blocked writers and `Blackboard` a per-writer weighted view. Phase 8's `PREREG` and results do not change |
| C13 | Outputs | `results/multiagent/safety/{quick,h3,full}/`: `runs.csv`, `metrics.json`, `report.md`, figures; the H3 pre-registration hash and git commit in `metrics.json` and the report |
| C14 | Row keys | A row's `factor` is its grid (`attack`, `defence`, `monitor`, `h3`) and its `level` encodes kind, number of bad agents, defence and `q`, so Phase 8's `rowKey` keeps every row distinct and sorting stays deterministic |

Defaults that were marked *(check)* in the low-level design (`theta`) were fixed by task T7 on pilot seeds.

### Calibration (T7, AC-7, 2026-10-11)

Clean runs with sanctions and `q = 0.05`, blackboard and messages, N = 16 and 64, pilot seeds 1000-1009 (40 runs per `theta`). "False" = share of clean runs in which any honest agent reached sanction level 2 or more; "honest" = mean share of honest agents at level 2 or more; "revoked" = share of liars revoked in runs with 25% liars.

| `theta` | False (all) | blackboard 16: honest, revoked | blackboard 64 | messages 16 | messages 64 |
|---|---|---|---|---|---|
| 0.5 | 1.00 | 1.000, 1.00 | 0.992, 1.00 | 1.000, 0.40 | 0.939, 0.21 |
| 1.0 | 1.00 | 1.000, 1.00 | 0.966, 0.89 | 0.956, 0.28 | 0.864, 0.09 |
| 1.5 | 1.00 | 1.000, 1.00 | 0.983, 0.79 | 0.394, 0.30 | 0.352, 0.11 |
| 2.0 | 0.65 | 0.200, 1.00 | 0.056, 0.77 | 0.050, 0.33 | 0.028, 0.10 |
| **2.5** | **0.00** | 0.000, 1.00 | 0.000, 0.77 | 0.000, 0.28 | 0.000, 0.12 |
| 3.0 | 0.00 | 0.000, 1.00 | 0.000, 0.74 | 0.000, 0.28 | 0.000, 0.12 |

**Deviation from the draft rule, before freezing:** none of the drafted candidates (0.5-1.5) met the rule; at those values honest agents are sanctioned in every clean run, because harvest noise (0.45), crowding and patch moves make an honest report differ from a later check by up to about 2. The candidate list was extended to 3.0 with the rule unchanged; **`theta = 2.5`** is the smallest value with no false sanction in any clean run. Lies at patches and danger sites differ from a check by 3.45, so they still count as strikes; a liar's "c at an empty spot" (error 0.85) cannot be told from honest noise. H3 does not depend on `theta`. Liars on the message channel are revoked far less often (about 0.1-0.3), since few of their messages are checked.

Pre-registration frozen: `PREREG_H3` hash `a44617201f88`, commit `cae6b3a`.


## Results (2026-10-11)

### H3 (confirmatory; T9, seeds 300-329, run once on the frozen `PREREG_H3`)

360 runs in 59 s on 8 processes. Relative loss of honest agents' welfare from one liar, blackboard minus messages, mean over 8, 16 and 32 agents, 30 seeds:

| Test | Mean difference [95% CI] | dz | p | Verdict |
|---|---|---|---|---|
| H3 | +0.041 [0.033, 0.049] | 1.67 | 0.0001 | **supported** |

Per size, one liar costs honest agents 3.8% (N = 8), 4.1% (16) and 7.4% (32) of their welfare on the blackboard, and 1.2%, 1.1% and 0.6% (not different from 0) through messages. 0.0001 is the smallest p the 10 000-flip test can give. The CSV re-analysis reproduces the result exactly; no deviation from the pre-registration. This confirms part (3) of the plan's hypothesis: the shared map that makes teams faster and of one mind (Phase 8) also makes them more vulnerable to a liar. Part of the gap reflects that messages carry little information in this world (Phase 8), so a liar has little to corrupt.

### Exploratory (T10, seeds 400-409; 2 480 runs in 570 s)

- **Liars** do almost all the damage. On the blackboard, 25% liars cost honest agents 24% (N = 16) and 50% (N = 64) of their welfare; with the lead, 8% and 46%; through messages and with no channel, nothing measurable. One liar in 64 costs 4.5% on the blackboard (CI includes 0).
- **Free-riders and saboteurs** barely hurt honest agents and at N = 64 even raise their welfare per agent (blackboard, 16 saboteurs: -19% loss), because they idle or crowd one patch and leave the rest to fewer competitors; team welfare shows their cost (blackboard N = 16, 4 saboteurs: 23% of team welfare). With no channel they never move (nothing is reported), and those that start on a danger site drag team welfare below zero at N = 64.
- **Private trust** is the only defence that pays: on the blackboard at N = 64 it raises honest welfare without attack (0.306 vs 0.259) and under 25% liars (0.205 vs 0.130; benefit 29% of clean welfare); at N = 16 it costs 10% without attack and gains only above two liars in 16. Through messages it changes nothing (liars do no harm there).
- **Shared reputation and sanctions** at the defence grid's spot-check rate (`q = 0.05`) cost far more than they save: spot-check trips take about a third of all agent-seconds (each trip can cross half the ring), costing 47% of honest welfare at N = 16 without attack on the blackboard, and over 90% through messages at N = 64. With incidental checks only (`q = 0`, the monitoring sweep), sanctions revoke every liar at N = 16 and about 80% at N = 64 (in the defence grid the first revocation comes after 17-111 s) and never sanction an honest agent; without attack they cost 12% at N = 16 and gain 8% at N = 64. Yet under 25% liars honest welfare is no better than without a defence (N = 16: 0.371 vs 0.361; N = 64: 0.122 vs 0.130), because the shared reputation also discounts honest reports (their noise and crowding pull an honest agent's reputation to about 0.5).
- **Monitoring cost vs benefit:** welfare falls steadily as the spot-check rate rises, for every defence, with and without liars; at equal monitoring cost, private trust is always at or above shared reputation and sanctions (`monitor.png`). The plan's question "trust weighting vs sanctions at the same monitoring cost" is answered: trust, at zero deliberate monitoring.
- **Detection:** the white-box score (reports vs the agent's own beliefs) separates liars perfectly in every run (AUC 1.00), the ceiling that reading agents' internal state gives. Black-box scores from the defences are good on the blackboard (private trust 1.00 at N = 16 and 0.56 at N = 64; reputation and sanctions 0.86-0.93) but **inverted through messages** (AUC 0.00-0.13): liars' messages are rarely checked, while honest agents' best-place messages get crowded and look wrong when checked, so liars end up better rated than honest agents.
- **Free-riding index (Phase 8 metric check):** it rises with the number of free-riders (blackboard N = 16: 0.26 clean, 0.95 with 4 free-riders) instead of turning negative as Phase 8 assumed, because free-riders have both a low harvest share and a low discovery share; as defined, the index does not flag free-riding in this world and needs redefining (for example harvest per discovery).

### Figure guide in plain language

The figures are in `results/multiagent/safety/h3/` (`h3.png`) and `results/multiagent/safety/full/` (the rest); that folder is not in git, so rebuild it with the commands in [RUN.md](RUN.md).

**The setup.** The same foraging world as Phase 8 (64 spots, 16 moving food patches, 8 danger spots), but some agents are bad. A *liar* tells the team that dangerous or empty spots are great and that good patches are dangerous, while quietly foraging well for itself. A *free-rider* only goes where others have reported food and never shares what it finds. A *saboteur* always crowds the most praised spot. "Honest welfare" is the food (minus danger penalties) that the honest agents collect, per honest agent per second.

**`h3.png`: the pre-registered test.** How much of their food honest agents lose when one liar joins, by team size, for the shared notice board (blackboard) and for occasional messages. On the board the loss is 4-7%; with messages about 1%. The test, fixed before running, confirmed that the board is the more vulnerable channel.

**`attack.png`: what each kind of bad agent does.** Honest welfare as the number of bad agents grows, one panel per kind and team size, one line per way of sharing. Liars pull the board and the lead down steeply (half the honest food at 16 liars in 64); messages and no sharing are flat because there is little shared information to corrupt. Free-riders and saboteurs leave honest agents almost untouched, and in big teams even help them by idling.

**`team.png`: the whole team, bad agents included.** The same picture for everyone's food. Here free-riders and saboteurs do show a cost: they take food without finding any, or sit on one patch, so the team as a whole produces less.

**`defence.png`: do the defences help against liars?** Honest welfare vs number of liars, with no defence (black) and each defence. Private trust (each agent learns whom to believe from its own experience) is the only one that helps, and in big teams it even helps when there are no liars. Shared reputation and sanctions sit far lower, because in this grid they also send agents on frequent checking trips.

**`cost.png`: what a defence costs without an attack, and what it saves under one.** Blue bars: how much honest food a defence loses when everyone is honest; orange bars: how much it recovers when a quarter of the team lies. Trust at 64 agents is the one clear win (it costs nothing and recovers 29%); the defences that send agents on checking trips cost much more than they save.

**`monitor.png`: paying for monitoring.** Each point is one spot-check rate; further right means more of the team's time spent checking. Every line slopes down: checking costs more than it catches here. At any given cost, private trust (purple and brown) stays on top.

**`detection.png`: can we tell who the liars are?** Two kinds of test. White-box (blue): compare what an agent believes, read directly from its memory, with what it reports; this catches every liar. Black-box (orange): judge agents only by whether their reports matched what others later found. That works on the board but fails through messages, where liars even end up looking more trustworthy than honest agents, because their lies are rarely checked.

**In one sentence:** sharing makes a team more productive and more exposed; a lie on a shared board costs the honest agents several times more than a lie in a message, and the defence that works is the cheapest one, each agent quietly learning whom to trust, while costly policing and public sanctions do more harm than good here.
