# Plan: Phase 23, bridges that carry evidence (C1b)

Status: **v3, 2026-11-11 (aligned with requirements v4 and design v4; the spec had an independent review, 15 findings fixed, and the build an alignment check). The user decided P23-1 to P23-10 on 2026-11-11, all as proposed.** T1-T5 done 2026-11-11: T1-T4 built and independently reviewed; T5's gate passed (C1's regression and B3's check: 0 differences; the full suite with slow tests passes); an alignment check of plan, specs and code fixed the gaps listed in design.md's build notes. `C1B_PILOT_PLAN` frozen 2026-11-11 after the user approved the pilot's estimate ($2.60-2.99). T6's pilot ran on 2026-11-12 ($2.73): every check passed except relayEvid's two (0.003 relays per bridge turn, none confirmed on arrival); the user kept relayEvid and approved the $24.88 projection, and `C1B_PLAN` was frozen with the P23-10 calls (T7). The main run (T7, $21.44, 2026-11-12) gave Gate C1b **ask**: `bridgeFix` was no more effective than `bridge1` (−0.003, p 0.62) but was safer (contamination −0.048). The dedicated role helped (+0.016, exploratory) and evidence did not. The user chose to confirm `bridgeRole` against `bridge1` on fresh seeds before A1 adopts a bridge design; see tasks.md's T7 for the numbers. T8 waits for that. Nothing live had run when the plan was frozen. One clause was added to the dedicated bridge's rule at build (FR-B1); it was shown to the user before the pilot was approved. This phase follows up C1 (Phase 20), whose Gate C1 passed on 2026-11-11 but whose bridges did almost nothing: `bridge1` − `coupled` +0.013, a win-back of 14% of the coupling cost (H20-3 not supported). It belongs to project C of the Stage 1 research plan ("test which team structures help and can arise from RL") and feeds A1 (Phase 19), which trains in a bridged world.

## Files in this spec

| File | What it covers |
|------|----------------|
| [requirements.md](requirements.md) | Terms, functional and quality requirements, acceptance criteria, out of scope |
| [design.md](design.md) | Components, the evidence tally, the bridge role, data flow, measures, statistics, cost, tests |
| [tasks.md](tasks.md) | Ordered tasks with "done when" checks and the gates |

Precedence: requirements win over the design, and the design wins over this plan. Where this plan amends another phase (Phase 19's P19-8 and P19-10), the amendment takes effect only when the user decides it.

## Goal: safe and effective agent teams

The project's goal is to train teams of agents that are **effective** (they pool what they know and solve more) and **safe** (lies and errors do not spread through them). C1 showed that squads keep most of their advantage when work crosses squads. It did not show that the links between squads can be made to work. It also found that links are where lies cross: guarded bridges relayed about 27 times as often as ordinary ones (0.133 against 0.005 relays per bridge turn) and spread lies across squads about 30 times as much (cross-squad contamination 0.193 against 0.006).

A1 is about to train the guard role in squads joined by bridges. If the bridges in that world are inert, A1 trains nothing about links between groups. The trained team's weakest point, the border, would never be exercised or rewarded. C1b asks whether a link can carry true information and stop lies, before A1 adopts it:

- **Effective:** the link gets the clue across in a form teammates trust.
- **Safe:** the evidence for a value crosses with it, the true holders can still contest a lie after it has crossed, and the bridge relays only what is confirmed and uncontested.
- **Trainable:** every fix lives in the board and its display or in a role, not in Claude-only prompting, so A1's 3B rollouts can use it within the 3,072-token window. A1's credit scheme must pay for stopping a lie at the border (P23-8).

## Why C1's bridges failed (from C1's rows, `results/multiagent/colony/c1/runs.csv` and `reused.csv`)

| Cause | Evidence (boards with liars unless marked) |
|---|---|
| **A relay can never be confirmed.** Nobody in the receiving squad holds the cross clue (`COUPLE_RULE`: "Nobody in your squad holds that clue"). With one bridge, a relayed value has one sender on the receiving board, so the counting rule (confirmed at 2) never confirms it, and a liar in the receiving squad posting a different value ties it. P20-17 predicted this in the simulator; it was left as is. | Honest pooled share from coupled subtasks: 0.001 (`bridge1`), 0.008 (`bridge2`), −0.006 (`bridgeGuard`). On clean boards, where no lie competes: 0.033 (`bridge1`) against 0.001 (`coupled`). |
| **Bridges solved instead of relaying.** A bridge keeps its solver's job (P20-2); bridging is one sentence in a solver's prompt. | `bridge1`: 1.6 relays, 125 bridge opens and 80 bridge solves per board; 0.5% of bridge turns relayed. `bridgeGuard` (a guard does not open): 42.6 relays, 0 opens, 13% of turns relayed. |
| **Relays were not filtered.** A bridge may relay any mirror value (P20-4); scripted liars post on mirrors (P20-5). | Mirror posts 37% false. False relays: 67% (`bridge1`), 32% (`bridgeGuard`), so the guard bridge barely beat picking a mirror value at random. |
| **A relayed lie cannot be contested downstream.** Contesting means posting the true value one holds; nobody in the receiving squad holds it. | Cross-squad contamination rises with relays: 0.006, 0.065, 0.193 (`bridge1`, `bridge2`, `bridgeGuard`). |

So the place where a lie can be stopped is the mirror, where the true holders are, and what they post there must reach the receiving squad.

**What even a perfect link cannot fix (found in review, from a rule-agent replay of C1's boards).** Cross clues are dealt to any slot of the sending squad, liars and guards included. A liar holds one of the two copies on about 47% of mirrors and never posts the truth. Over seeds 1800-1807, only 403 of 777 mirrors (52%) ever had a confirmed true value. Each squad's 2 scripted liars see every mirror of their squad; on 14 of 777 mirrors (1.8%) they confirmed a false value between them. Ties go to the newest post, and liars post again often. So:

- a bridge that relays only confirmed values can deliver the truth on about half the coupled subtasks, which caps H23-1's possible gain;
- a lie confirmed by two liars can reach the receiving squad through any link, `window` included; the dedicated bridge's rule refuses a tied lead (P23-3), and FR-D1 measures how often such lies cross.

## Questions and hypotheses

| ID | Hypothesis | Family |
|---|---|---|
| H23-1 | A dedicated bridge whose relays carry the mirror's evidence (`bridgeFix`) beats C1's `bridge1` in honest pooled share | Gate C1b, part i (effective) |
| H23-2 | `bridgeFix` is not less safe than `bridge1`: its contamination (FR-D1, counting lies that arrive through relays and mirror lines) is less than 0.05 above `bridge1`'s, by the one-sided 95% bound (non-inferiority) | Gate C1b, part ii (safe) |
| H23-3 | `bridgeFix` wins back more than half of what coupling costs: (`bridgeFix` − `coupled`) / (`squads` − `coupled`) > 0.5 (C1's H20-3, retried) | Secondary |
| H23-4 | Bridges filter: `bridgeFix`'s false-relay share is below the false share of the mirror values it could relay | Secondary |
| H23-5 | Evidence and role each help: the 2 × 2 of evidence (no, yes) × role (solver, dedicated), with `bridge1` as (no, solver) | Descriptive |
| H23-6 | How close an agent link comes to a structural one: `bridgeFix` against `mirrorWindow`, where the receiving squad sees the mirror directly, with no bridge | Descriptive |
| H23-7 | Cost without liars: on clean boards `bridgeFix` − `squads` and `mirrorWindow` − `squads` (C1's H20-8: `bridge1` − `squads` −0.058) | Descriptive |
| H23-8 | Border safety: contamination on coupled subtasks alone (`coupledContamination`), per arm, against `coupled` | Descriptive |

Each can fail:

- H23-1 fails if teammates still ignore relays, or if the bridge's lost solving outweighs what it passes on.
- H23-2 fails if more traffic across the border means more lies across it.
- H23-4 fails if a bridge relays what is loudest rather than what is confirmed.
- H23-6 tells A1 and C3 whether a link role is worth training at all: if `mirrorWindow` is far ahead, the link is better built into the board than learned. The comparison is not pure: `mirrorWindow`'s squads keep 4 solvers and `bridgeFix`'s have 3. `relayEvid` against `bridgeFix` separates the role's cost from the link's quality.

## Design summary

- **Board and team as C1:**
  - `WORLD18` counting board, Claude Haiku 5.5, 40 turns;
  - 64 agents in eight squads of 8, with 16 independent scripted liars and 16 guards;
  - a quarter of each squad's subtasks coupled to the next squad around a ring;
  - mirrors as P20-1, P20-5 and P20-16.
- **Evidence (`evidence`, P23-2).** Once any value has been relayed on a coupled subtask, the receiving squad's board shows that clue's whole mirror tally, every value posted there with its count of mirror senders, and counts it.
  - **Mirror senders only:** the bridge's own post does not add to the count, so one liar's value plus the bridge is still unconfirmed.
  - **Example line:** `x mod 7 = 3 (2 agents in squad 3, relayed, confirmed)`.
  - **Counts never fall:** mirror posts are never withdrawn. But when the true holders post later, their value appears downstream and contests a relayed lie, without anyone relaying it again.
  - **One hook:** a hook in `clue_colony.tally` does this for the display, for Claude and for rule agents alike.
- **Dedicated bridge (`bridgeRole`, P23-3).** The bridge does not open or answer subtasks. As for guards, this is its rule, not something the board enforces.
  - **Its rule:** relay a value only when it leads on the mirror, is confirmed there, no other value is tied with it, and its own squad's board does not already show it leading. When the mirror's leader changes, relay the new one. With nothing to relay, share a clue it holds that a board is missing, shows wrong or shows unconfirmed (added at build: the deal gives a bridge clues like any slot); otherwise wait.
  - **Its view:** its view of the mirror marks values confirmed and contested (FR-B6).
  - **Its slot:** it is taken from the 4 honest non-guard agents of its squad, so each squad has 3 solvers, 2 guards and 1 bridge (P23-4).
- **Mirror window (`mirrorWindow`, P23-5).** No bridge agent. The receiving squad's board shows every mirror value of its coupled subtasks with its mirror senders from the start. This is the structural ceiling for a link.
- **Upstream contest.** Unchanged from C1: the holders of each cross clue see its mirror and post there. With evidence, a true holder's mirror post is the contest that protects the receiving squad. P23-8 proposes paying for it in A1.

| Arm | Key | Evidence | Bridge | Boards with liars | Clean boards | Source |
|---|---|---|---|---|---|---|
| Squads without cross-squad subtasks | `squads` | | | 8 | 5 | C1 cache, $0 |
| Coupled squads, no bridges | `coupled` | | none | 5 | 5 | C1 cache, $0 |
| C1's bridge | `bridge1` | no | solver | 8 | 5 | C1 cache, $0 |
| Evidence only | `relayEvid` | yes | solver | 5 | none | new |
| Role only | `bridgeRole` | no | dedicated | 5 | none | new |
| Both (the candidate for A1) | `bridgeFix` | yes | dedicated | 8 | 5 | new |
| Structural link | `mirrorWindow` | yes (all values, no relay) | none | 5 | 5 | new |

Seeds:
- 1800-1807 for the 8-board arms;
- 1800-1804 for the 5-board arms and the clean boards.

Every new board is paired with C1's boards on the same seed. The pilot is seed 1890: one board with liars of each new arm.

- **Gate C1b:** both parts must hold.
  - **(i) effective:** `bridgeFix` − `bridge1` > 0 in honest pooled share. One-sided exact sign-flip over 8 paired boards, α = 0.05.
  - **(ii) safe:** the one-sided 95% upper bound (the 95th percentile of 2,000 paired bootstrap means) of `bridgeFix` − `bridge1` in contamination is below 0.05.
    - **Why 0.05:** in C1, paired differences in contamination between arms vary by 0.04-0.07 from seed to seed. With 8 pairs, a design as safe as `bridge1` passes about 95% of the time, and one that is truly 0.05 worse passes about 5% of the time. A 0.02 margin would pass only a design that is clearly safer.
  - **Robustness:** part (i) is repeated on raw honest welfare, as in C1; part (ii) is contamination, which does not depend on the welfare measure.
  - **Correction:** two parts that must both hold need no multiplicity correction.
- **What the gate decides (P23-7).**
  - **Passes:** A1's bridged world uses evidence, and dedicated bridges in its assigned arms (amends P19-8).
  - **Part (ii) fails:** A1 trains without bridges.
  - **Part (i) fails but part (ii) holds:** stop and ask.

## Cost

**API: about $24-27**, from C1's measured per-board costs (`results/multiagent/colony/c1/runs.csv`: boards with liars $0.646-0.684 by arm, clean boards $0.609-0.620):

| Item | Boards | Per board | Cost |
|---|---|---|---|
| New arms with liars (`relayEvid` 5, `bridgeRole` 5, `bridgeFix` 8, `mirrorWindow` 5) | 23 | $0.65 measured (C1's bridge arms), up to $0.75 with a 1.15x allowance for the evidence tags and the role sentence | $15.0-17.3 |
| Clean boards (`bridgeFix`, `mirrorWindow`, 5 each) | 10 | $0.61 measured (C1's clean bridge and coupled boards), up to $0.70 | $6.1-7.0 |
| Pilot (seed 1890, the four new arms with liars) | 4 | as the first row | $2.6-3.0 |
| Reused (`squads` 8 + 5, `coupled` 5 + 5, `bridge1` 8 + 5) | 36 | replayed from the cache, $0 | $0 |
| **Total** | 37 new | | **$23.7-27.3** |

- **The cap.** November's spend is $25.98 of the $250 monthly cap (the ledger, 2026-11-11). A2 (Phase 21) is estimated at $34-39. C1b would bring the month to about $85-93. That is within the cap and close to the $100 monthly credit. As in every phase, the user sees the estimate before the pilot and the projection before the main run (P20-8's rule, P23-9).
- **Wall time.** C1 played 38 boards in 3.3 hours (11:25-14:45 on 2026-11-11). So the main run should take about 3 hours, and the pilot under 30 minutes.
- **Main-run ceiling: $28.** The pilot's projection is reported beside it; above it the user decides (P20-8's rule, P23-9).
- **GPU: none in this phase.** The 3B check of the chosen design is P23-6.

## Decisions (the user, 2026-11-11: all ten accepted as proposed)

| ID | Decision | Decided value | Alternative (not chosen) |
|---|---|---|---|
| P23-1 | Run C1b before A1 adopts bridges | Yes. A1 also waits for Gate A2, which is not built, so C1b runs alongside A2's build and should not delay A1. | A1 adopts `bridge1` now (as P19-8), and C1b informs C3 only. |
| P23-2 | How a relay carries evidence | After the first relay on a coupled subtask, the receiving board shows and counts that clue's whole mirror tally (mirror senders only), live. True holders' later posts then reach the receiving squad and contest a relayed lie. | Only the relayed value with its mirror senders, as a snapshot: simpler, but a relayed lie can never be contested downstream. |
| P23-3 | The dedicated bridge's rule | It never opens or answers. It relays only a value that leads on the mirror, is confirmed there and is not tied, and it relays the new leader when the leader changes. This is set in the prompt, not enforced by the board, so a bridge can still choose wrongly; H23-4 measures that, and A1 can reward it. | Enforced by the board (only an untied confirmed leader can be relayed): safer, but it removes the choice there is to train. |
| P23-4 | Whose slot the dedicated bridge takes | The first honest non-guard slot, as C1: 3 solvers, 2 guards and 1 bridge per squad of 8. The clean boards price the lost solver. **In A1's squads of 4** (1 liar, 1 guard, 2 others), a dedicated bridge would leave 1 solver. So A1 would use evidence without a dedicated bridge in squads of 4, and a dedicated bridge in squads of 8 (P23-7). | A guard slot: keeps the solvers but loses a guard. |
| P23-5 | Include `mirrorWindow` | Yes: 5 boards with liars and 5 clean (about $7). It is the ceiling that says whether a link role is worth training (H23-6). | Drop it, saving about $7. |
| P23-6 | 3B check | Point Phase 20's T7 bridge check (P20-11, not yet run) at `bridgeFix` in squads of 8, and at evidence with solver bridges in squads of 4. Its 0.5 A100 hours then test what A1 would use. Part b of T7 is unchanged. | Run C1's bridge check as well (about 0.5 A100 hours more). |
| P23-7 | What Gate C1b decides for A1 | **Pass:** A1's bridged world has evidence. Arms 1-3 (assigned guards) get a dedicated bridge in squads of 8 and solver bridges in squads of 4. Arm 4 (no assigned roles, emergence) gets evidence and solver bridges, since an assigned role would defeat its test (as P19-8 noted for `bridgeGuard`). **Part (ii) fails:** A1 trains without bridges. **Part (i) fails and (ii) holds:** stop and ask. | Advisory only. |
| P23-8 | Pay for stopping a lie at the border in A1 (amends P19-10) | In A1's bridged world, a true holder's mirror post that contests a false mirror value earns contest credit, as a contest on the squad's own board does. With evidence (P23-2) that post now reaches the receiving squad, so the reward trains a behaviour that has an effect. | Keep P19-10: a mirror post earns no contest credit. |
| P23-9 | Pilot checks and cost rule | P20-8's rule: report the estimate and wait, then report the projection and wait. **Stop and ask** on any of: invalid replies at 5%; no mirror posts; on a bridge arm, relays per bridge turn below 0.05 (C1's check only asked for more than zero); on an evidence arm, no relayed value confirmed on arrival; a bridge's mean input tokens per call above 1,560 (C1's check). The relay check covers all three bridge arms, `relayEvid`'s solver bridges included (the user, 2026-11-11, knowing C1's solver bridges relayed on 0.5% of turns, so `relayEvid` may stop the pilot to ask). | C1's checks unchanged. |
| P23-10 | Forecast | No B3 forecast: `B3_PLAN` is frozen with its list of experiments, and C1b is not on it. Instead `C1B_PLAN` records by hand, before the main run, the pilot-only and every-design-helps calls for H23-1 to H23-4. Those have been the best forecasters so far (C1: pilot-only 5 of 6 right). | Amend B3 to add C1b, which needs a new B3 plan version. |

## Relation to the other experiments

- **C1 (Phase 20):** its gate stands as frozen. C1b reuses:
  - C1's code (`BridgeBoardEnv`, `c1Columns` with `bridgeColumns`, `colony_trace.replay`, and the statistics helpers of `bridge_report`);
  - C1's cached reference boards;
  - its seeds.
- **A1 (Phase 19):** C1b decides A1's bridge configuration (P23-7, amending P19-8). It also asks whether A1 pays for stopping lies at the border (P23-8, amending P19-10). A1's T5a (the bridged world's wiring) can go ahead now; the new keys add to it.
- **A2 (Phase 21):** independent. The two share the month's cap.
- **B3 (Phase 22):** no forecast (P23-10). C1b's rows could later refit B3's `trustOne` if you want, outside B3's frozen plan.
- **C3 (emergent structure):** `mirrorWindow` against `bridgeFix` (H23-6) tells C3 whether a relay role is worth learning. `RoleBridge`, the rule-agent version of the dedicated bridge, is the base for C3's warm start.
- **C4 (stronger adversaries):** part b's Claude liars in squads with bridges should use whichever bridge Gate C1b chooses. Liars that target the mirror in pairs (the 1.8% exploit above) are C4's to strengthen.
