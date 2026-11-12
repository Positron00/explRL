# Requirements: Phase 23, bridges that carry evidence (C1b)

Status: draft v2 (aligned with README draft v2, 2026-11-11). Decisions P23-1 to P23-10 decided by the user on 2026-11-11, all as proposed; requirements that depend on one name it.

## Terms

- **Coupled subtask, mirror, bridge, relay, cross-squad contamination:** as Phase 20's requirements.
- **Mirror tally:** for a coupled subtask k, each value posted on its mirror with the set of distinct agents of the sending squad who posted it (`BridgeBoardEnv.mirrorTally`; `{}` when the mirror has no posts). Mirror posts are never withdrawn, so a value's sender set only grows.
- **Opened clue:** on an `evidence` board, the coupled clue of subtask k once any bridge has relayed any value on k.
- **Evidence count:** on the receiving squad's board, each value of an opened clue (on an `evidence` board) or of every coupled clue (on a `mirrorWindow` board) counted with its mirror senders only. The relaying bridge's own post does not add a sender (P23-2).
- **Dedicated bridge:** a bridge with `bridgeRole`. Its rule says never to open or answer, and to relay only an untied confirmed mirror leader (P23-3).
- **Arrival-confirmed relay:** a relay whose value had at least `Q` = 2 mirror senders at the turn it was relayed.
- **Filter gain:** the false share of the distinct mirror values on the bridge's pair when it relayed, minus the false share of the values it relayed (H23-4).

## Functional requirements

### Part A: the board

- **FR-A1** `RelayBoardEnv(BridgeBoardEnv)` with three keys, `RELAY_KEYS = ('evidence', 'bridgeRole', 'mirrorWindow')`, all off by default. Without any of them, every board, prompt and saved row is unchanged (NFR-1).
- **FR-A2** `evidence`: `relaySenders(k, j)` returns `{r: senders}` from the mirror tally of every opened clue (j = 1), and `{}` otherwise.
  - `clue_colony.tally` merges these senders into the receiving squad's tally when the board defines `relaySenders`. For a value the bridge posted, the bridge's own post is dropped from its sender set.
  - So the display, `knownColony`, the colony and guard rule agents and B3's agents all see the same evidence count.
- **FR-A3** `mirrorWindow`: `bridges` must be 0. `relaySenders` returns the mirror tally of every open coupled subtask of the receiving squad. Mirror posts still never reach the channel.
- **FR-A4** `bridgeRole`: needs `bridges` ≥ 1 and not `bridgeGuard`. As for guards, the role is set by its rule, not enforced by the board. A dedicated bridge's opens and answers stay valid and are counted (`bridgeOpens`, `bridgeSolves`), so the role can be measured and, in A1, trained. The board exposes `roleBridges`.
- **FR-A5** Display: on an evidence or window board, each value of an opened (or window) clue reads `x mod p = r (n agents in squad s2, relayed, confirmed|unconfirmed)`, with `, contested` after the clue when values disagree. Here n counts mirror senders only and s2 names the sending squad. Every other line keeps `colonyLine`'s format.
- **FR-A6** `checkRelay(world, N, nLiar)` rejects `mirrorWindow` with bridges, `bridgeRole` without bridges or with `bridgeGuard`, and any relay key without `couple`.

### Part B: prompts and rule agents

- **FR-B1** `BRIDGE_ROLE_RULE`, after `BRIDGE_RULE`: "Your role: bridge. Do not open or answer subtasks. Each turn, relay one value from squad {s2} that leads on its mirror, is confirmed there and is not tied with another value, and that your squad's board does not already show as leading; if a value you relayed has lost the lead on the mirror, relay the new leader; if there is none, wait." (P23-3)
- **FR-B2** `EVIDENCE_RULE` for every agent of an evidence board: "A value marked 'relayed' was posted in squad {s2}; its count is the number of agents there who posted it, and other values they post for that clue appear beside it."
- **FR-B3** `WINDOW_RULE` for every agent of a window board, in place of any bridge sentence: "Values that squad {s2} posts for your subtasks that need it appear on your board, marked 'relayed', with the number of agents there who posted them."
- **FR-B4** The new sentences come after the squad, couple and mirror sentences. `SQUAD_RULE`, `COUPLE_RULE`, `MIRROR_RULE` and `BRIDGE_RULE` stay byte-identical (P20-15).
- **FR-B5** `RoleBridge`, the numpy dedicated bridge: never opens. Each turn it relays the untied confirmed leader of a mirror of its pair that its own board does not show as leading; otherwise it waits. `relayMembers` applies it, as `bridgeMembers` applies `RuleBridge`.
- **FR-B6** On a `bridgeRole` or `evidence` board, the bridge's pair line (`bridgeLines`, `PAIR_HEAD`) marks each value `confirmed` or `unconfirmed` and each clue `contested` when values disagree, in `colonyLine`'s words. C1's boards keep their pair line unchanged.

### Part C: grid, plans and runs

- **FR-C1** `C1B_ARMS` and `C1B_CELLS` as README's table:
  - new cells with independent liars for `relayEvid`, `bridgeRole`, `bridgeFix` and `mirrorWindow`;
  - clean cells for `bridgeFix` and `mirrorWindow`;
  - all at N 64, on README's seeds.
- **FR-C2** `reusedRows23` replays C1's `squads`, `coupled` and `bridge1` cells, with liars and clean (36 boards), from the cache-only client at $0. Every saved column must be unchanged; the new columns are added.
- **FR-C3** Two frozen plans, both recording `cap=250.0` and its `capNote`:
  - `C1B_PILOT_PLAN`: frozen and pushed before the pilot, after the user approves the estimate;
  - `C1B_PLAN`: the pilot plan plus the pilot's verdict, the user's approval of its projection and the hand-recorded calls of P23-10; frozen and pushed before the main run.
- **FR-C4** `pilotCheck23` applies P23-9's checks and `costRule20`'s report-and-wait rule.
- **FR-C5** `demo_c1b`, staged by `EXPLRL_C1B_STAGE`:
  - `quick`: fake client, synthetic rows;
  - `pilot`;
  - `main1` and `main2`: the seed batches;
  - `main`: the full grid from the cache at $0, then the report.

  `mainReady23` refuses the main stages unless both plans are frozen and the approval is recorded.

### Part D: measures and analysis

- **FR-D1** Contamination and the new columns.
  - **Contamination:** `falseValues` on a `RelayBoardEnv` also includes every false value counted on a receiving board through `relaySenders`, with the turn it first counted. So `contamination` (`colony_trace.traceBoard`: the share of honest answers built on a false shown value) sees lies that arrive by relay or by window. It is computed the same way for every arm, and unchanged on C1's boards.
  - **New columns, per board, in `relayColumns`:**
    - `arrivalConfirmed`: the share of relays confirmed on arrival;
    - `filterGain` (Terms);
    - `reRelays`: relays of a new leader after a relayed value lost the lead;
    - `relaysUsedCorrect`: relays whose value entered a correct answer;
    - `roleBreaks`: a dedicated bridge's opens;
    - `coupledContamination`: contamination over honest answers on coupled subtasks only;
    - `truthConfirmable`: the share of mirrors that ever had a confirmed true value;
    - `liarConfirmed`: the share of mirrors with a false value confirmed by two liars.
  - C1's `bridgeColumns` stay.
- **FR-D2** `gateC1b`, with both parts repeated on raw honest welfare:
  - **Part (i):** one-sided exact sign-flip over the 8 paired boards of `bridgeFix` − `bridge1` in honest pooled share, α 0.05.
  - **Part (ii):** the 95th percentile of 2,000 paired bootstrap means of `bridgeFix` − `bridge1` in contamination must be below 0.05.
- **FR-D3** `c1bSummaries`, each with a 95% bootstrap interval and an uncorrected p:
  - H23-3: the win-back on seeds 1800-1804, supported only when the coupling cost is positive, as C1's T5 note;
  - H23-4: filter gain, a sign-flip over the bridge boards;
  - H23-5: the 2 × 2 table with each main effect;
  - H23-6: `bridgeFix` − `mirrorWindow`, and `relayEvid` − `mirrorWindow`;
  - H23-7: the clean contrasts with `squads`;
  - H23-8: `coupledContamination` per arm against `coupled`.
- **FR-D4** `writeC1b` (`results/multiagent/colony/c1b/report.md`) and `figC1b` (`c1b.png`). The figure shows honest pooled share and contamination per arm side by side, so effectiveness and safety are read together.

## Quality requirements

- **NFR-1** Every earlier board is unchanged after the `tally` hook. All 38 of C1's boards and its 16 reused cells replay from the cache with every saved column equal. Phase 20's regression tool (`tools/c1_regression.py`) and B3's check (`tools/b3_run.py check`) report 0 differences.
- **NFR-2** Modules stay under 200 lines. Notebooks import with `from explRL.`.
- **NFR-3** No API call in tests; live stages need `EXPLRL_LLM_LIVE=1`.
- **NFR-4** Prompt length:
  - on Claude, a dedicated bridge's mean input tokens per call stay under 1,560 (P23-9);
  - the longest 3B bridge prompt fits 3,072 tokens, measured by `bridgePromptTokens` on A1's world.
- **NFR-5** Keys are never logged. Spend is counted by `Budget` per calendar month.

## Acceptance criteria

- **AC-1** With no relay key, a `RelayBoardEnv` run equals a `BridgeBoardEnv` run on the same seed: same board and same log (FR-A1).
- **AC-2** On an evidence board (FR-A2):
  - a relay of a mirror value with 2 true senders is confirmed on arrival;
  - a lone liar's value on the receiving board loses to it in `knownColony`;
  - a relay of a value with 1 mirror sender stays unconfirmed, whatever the bridge posts.
- **AC-3** After a relayed lie, a true holder's mirror post appears on the receiving board within the same turn, and the clue is marked contested; with a second true post the true value leads (FR-A2, P23-2).
- **AC-4** On a window board, every mirror value appears on the receiving board with its mirror senders, and no bridge exists (FR-A3).
- **AC-5** A dedicated bridge gets `BRIDGE_ROLE_RULE`, and its opens are counted in `roleBreaks` (FR-A4, FR-B1).
- **AC-6** `RoleBridge` never relays an unconfirmed or tied value, and it re-relays a new leader (FR-B5).
- **AC-7** The reused cells replay at $0 with every saved column unchanged (FR-C2).
- **AC-8** `mainReady23` refuses until both plans are frozen and the approval is recorded (FR-C5).
- **AC-9** `gateC1b` on synthetic rows with known effects returns the planted verdicts, including a safety failure with an effectiveness pass (FR-D2).
- **AC-10** On a window board with a planted false mirror value, `contamination` counts an honest answer built on it (FR-D1).

## Out of scope

- Changing Gate C1 or C1's rows.
- Claude liars that target bridges or coordinate on mirrors (C4), and colluding mirror liars (P19-11).
- Bridges in both directions, or bridges that read the whole neighbour board.
- The A1 code changes themselves (Phase 19's T5a and T5b), beyond recording P23-7 and P23-8 there when decided.
