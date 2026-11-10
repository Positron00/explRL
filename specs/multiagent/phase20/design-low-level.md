# Design (low level): Phase 20

Part of [README.md](README.md). The module contents follow; each module stays under 200 lines.

## `bridge_board.py` (new)

```python
BRIDGE_KEYS = ('couple', 'bridges', 'bridgeGuard')

def dealBridges(N, S, nLiar, guards, perPair=1, guarding=False):
    """[[bridge slots] per squad], squads placed as squadOf (slot i in squad i mod (N // S)); liars the first nLiar slots and
    guards the next `guards` (as dealSquads). Ordinary: the first perPair honest non-guard slots of each squad, by slot order;
    guarding: the first guard slot of each squad (perPair must be 1). ValueError if a squad lacks the slots."""

def checkBridge(world, N=None, nLiar=0, zeroOk=False):
    """FR-B3's checks (ValueError): any bridge key needs `couple` in the world (no silent default: a world with bridges=0 and no
    couple used to couple at 0.25); couple needs squads, a value 1/n in (0, 1] (every n-th subtask) and two squads or more;
    couple=0 only with zeroOk (a directly constructed BridgeBoardEnv: no coupling); bridges need couple > 0;
    bridgeGuard needs bridges = 1 and guards; dealBridges must succeed."""

class BridgeBoardEnv(ColonyBoardEnv):
    """ColonyBoardEnv in squads (S) with coupled subtasks and bridges. couple (0.25): each squad's every 1/couple-th assigned
    subtask is coupled to squad (s + 1) mod n: clue 0 dealt within s, clue 1 within s + 1 (two holders each, _pick on rngDeal).
    Mirrors: squad s + 1 sees each coupled subtask of s as a mirror; its agents' shares there go to mirrorLog. bridges (0, 1, 2
    per pair) and bridgeGuard: bridge slots from dealBridges; a bridge's share on a coupled subtask of a value in that subtask's
    mirrorLog is a relay (relayLog). Every other behaviour is ColonyBoardEnv's."""
    def __init__(self, seed, nAgents, couple=0.25, bridges=0, bridgeGuard=False, nLiar=0, **kw): ...   # checkBridge(..., zeroOk=True);
                                           # ValueError unless the guard slots directly follow the nLiar liar slots
    def reset(self, seed, nAgents):        # mirrorLog, relayLog, coupled {k: (s, s2)}, nAssigned per squad, then super().reset
    def mirrorTally(self, k):              # tally's format, from mirrorLog (mirror posts never reach the channel)
    def _deal(self):                       # called once per subtask (ClueBoardEnv._new) with self._squad and self.serial set: nAssigned[s] += 1;
                                           # if nAssigned[s] % round(1 / couple) == 0, coupled[serial] = (s, (s + 1) % n) and clue 0 is dealt
                                           # from squad s's slots, clue 1 from s2's; otherwise ColonyBoardEnv._deal. reset sets nAssigned,
                                           # coupled, mirrorLog and relayLog before super().reset, which deals the first 2N + 2 subtasks.
    def mirrors(self, i, every=None):      # coupled subtasks k (open) whose s2 is i's squad and whose clue 1 i holds (P20-16);
                                           # every (default: i < nLiar, a liar slot): all of them (P20-5)
    def bridgeOf(self, i):                 # (s, s2) if i is a bridge, else None
    def apply(self, i, action, t):
        # share on a mirror k (k in mirrors(i)): append to mirrorLog, counts['shares'] += 1, ledger row 'shared'; not shareLog
        # open, or share without the cross clue, on a mirror: ValueError (ColonyBoardEnv's another-squad check); parseBridge
        #   turns such a Claude reply into an invalid move; nobody in s + 1 can answer a mirror
        # share by a bridge on its pair's coupled k with r in mirror values of (k, j): ColonyBoardEnv.apply, then relayLog
        #   .append((t, i, k, j, r, source)) with source = the first mirrorLog post of (k, j, r)
    def _creditTo(self, i, k):             # P20-12: [(agent, divisor)]; each paid credit * delta / divisor; a relay's share is split
                                           # between the bridge and its source poster (the first true poster on the mirror)
    def _reward(self, i, delta, k=None, solved=False):   # overridden: under 'credit'/'contest' on a solve, pays _creditTo's pairs;
                                           # otherwise ColonyBoardEnv's (clueboard unchanged)
    def viewFor(self, i): return BridgeView(self, i)

class BridgeView(SquadView):
    "SquadView plus `mirrors` (agent i's mirrors) and, for a bridge, `pair` (mirror tallies)."
    def mirrors(self, i=None, every=None): # the board's mirrors(i) for the view's agent
    def crossClues(self):                  # {k: (p, r)}: the cross clue agent i holds on each of its mirrors
    @property
    def pair(self):                        # for a bridge, tally's format over its pair's open coupled subtasks; else None

def relaySource(board, post):              # the mirrorLog post a relay copied, or None
```

- **Coupling uses no new random draws.** Squad assignment (`_new`'s balancing) and the coupling count are deterministic. Only the deal of a coupled subtask's clues changes which slots `_pick` chooses from. The k-th subtask's value and clues are therefore the `squads` board's on the same seed (AC-2).
- **Holding.** `held(i, k)` already returns the clues i holds for any k. A mirror holder holds clue 1 of k. The prompt shows that clue only on the mirror line, because `observe`'s "own clues" lists the open subtasks of i's view, which exclude mirrors.
- **The pooled bound** sums the top-N values of `self.open`, and a mirror is not a separate subtask, so the bound is unchanged.
- **Relay credit** (P20-12). `_creditTo` returns `(agent, divisor)` pairs: each base agent with divisor the number of credited clues, and for a clue whose first true post on k is a relay, the bridge and the source poster each with twice that divisor, so each gets half of that clue's credit share. As built, `_reward` is overridden in `BridgeBoardEnv` (`clueboard` is at 197 lines and unchanged). Without relays the pairs equal `clueboard`'s split; under `'individual'` the base `_reward` runs.
- **Mirror posts never reach the channel.** Prompts, the counting display and rule agents' known clues are built from the channel (`tally(channel, board)` reads `channel.posts[k]` for every open k), and a mirror is subtask k of squad s. So `parseBridge` returns `report=None` for a mirror share (`TextClueEnv.post` then posts nothing), and the numpy member wrapper in `bridge_agents` suppresses `post` for a mirror share, which goes through `BridgeBoardEnv.apply` only. The mirror tally, used by `bridgeLines`, `RuleBridge` and honest rule agents' mirror posts (P22-12), is `mirrorTally(board, k)`, built from `mirrorLog` in `tally`'s format. Relays are ordinary shares and are posted to the channel.
- **ContestLog** (A1, Phase 19) reads `relaySource` to decide whether a value on k was first posted by a liar. That change belongs to Phase 19's bridged step. C1 only provides `relaySource` and its test (AC-6).

## `bridge_agents.py` (new)

The rule sentences (P20-4). `{s2}`: the squad that holds the cross clues (s + 1); `{s0}`: the squad whose subtasks need the agent's clue (s − 1). `bridge_board.checkBridge(world, N, nLiar)` holds FR-B3's checks, and `bridge_agents.bridgeRules(env, i)` returns the rule sentences that apply to agent i.

```python
COUPLE_RULE = ("About a quarter of your squad's subtasks need one clue held in squad {s2}; they are listed under 'Your subtasks that need squad {s2}'. "
               "Nobody in your squad holds that clue.")
MIRROR_RULE = ("This is the one exception to the squad rule: some subtasks of squad {s0} need a clue that you or your squad hold; they are listed under 'For squad {s0}'. "
               "Share your clue there. You cannot open or answer them.")
BRIDGE_RULE = ("This is the one exception to the squad rule: you are the bridge from squad {s2} to your squad: you also see what squad {s2} posted for your squad's "
               "subtasks that need it. Relay a value by sharing it on the matching subtask of your squad.")
```

- **The squad rule.** `SQUAD_RULE` stays byte-identical, so the reused `squads` cells and the clean `squads` cells keep their prompts. The mirror and bridge rules open with "This is the one exception to the squad rule" (P20-15). The mirror line goes only to honest agents that hold a cross clue (P20-16). `MIRROR_RULE` goes to every agent on a coupled board: the rules are system text, cached once per agent, and on the ring every squad is some squad's s + 1, so any agent may come to hold a cross clue (implementation note, T2); `view.mirrors(i)` lists only the mirrors whose clue i holds. Liar slots of s + 1 see every mirror line of their squad in their prompts (`mirrors(i, every=None)`, P20-5), beyond P20-16's holders-only rule for honest agents, and scripted liars draw from all of them.
- **The summary line.** `TextClueEnv.summary` shows the clue for a mirror share (`shared T41: x mod 5 = 2`), because a mirror share has no report. Every earlier summary and prompt is unchanged (hashes checked, T2).
- **`bridgeLines(view, i, t)`** renders:
  - for a mirror holder: `For squad 3 (share your clue; you cannot answer): T41: x mod 5 = 2 (yours); posted: x mod 5 = 2 (2 agents)`;
  - for a bridge: `From squad 4 for your subtasks: T37: x mod 7 = 3 (2 agents), x mod 7 = 6 (1 agent)`.
  - for squad s, one line: `Your subtasks that need squad 4: T37, T41`; the open-subtask line is unchanged.
  - So at most three lines. Without a bridge key, nothing is added.
- **`parseBridge(env, parsed, i)`** returns (action, report, valid), or `None` to fall back to `parse`'s own path. It handles two cases:
  - a share on a mirror by an agent holding its cross clue, at its true residue (a liar at any residue);
  - a relay by a bridge on its pair's coupled k, of any residue in that subtask's `mirrorLog`.
- **`RuleBridge(RuleAgent)`, a mixin:** `bridgeMembers` applies it to every honest numpy member (its class becomes `Bridge<class>`, built once per base class). Roles are read at act time. Only bridges relay: if its squad has a coupled subtask open with the cross clue missing from the board and posted on the mirror, a bridge relays the mirror's leading value (the most senders, then the earliest). Every member makes P22-12's mirror posts at its sharing step. Otherwise it acts as its base agent. A mirror share is applied to the board only, never posted to the channel (`onMirror`).
- **`bridgeMembers(world, members)`:** changes numpy members' classes in place (`InSquad` wrappers kept, Claude members left alone), and they look up their role at act time through `board.bridgeOf(i)` and `board.mirrors(i)`, so it needs no `nLiar` and does not call `dealBridges` or `stage4Members`. Honest rule agents (not liars or mistaken members) gain `RuleBridge`; exact `ClueLiar` members (not subclasses) become `MirrorLiar`. It is applied by a hook at the end of `stage4Members` (below), so every numpy path (`colony_trace.replay`, `runClueNumpy`, `boardFactory`'s one-member wrap) gets it. `RuleBridge` keeps its base agent's `knownFor` (a `ColonyAgent` on colony arms, flag-aware on failFlag boards).
- **`MirrorLiar(ClueLiar)`:** on its lying turns it draws k from `view.open + view.mirrors(i)` with `rng.integers`, as `ClueLiar` does; on a mirror it posts a false residue of clue 1 only. With no bridge key its draws equal `ClueLiar`'s (`clue_agents` is at 199 lines and does not change).
- **`bridgePromptTokens(cfg, seeds, tok=None, policy=None)`:** renders every prompt of a rollout (policy default: the fake Claude client) and returns the longest per role (`bridge`, `holder`, `other`). `tok`: a tokenizer or a text -> count function; default about 4 characters a token.

## Hooks in existing modules

| Module (lines now) | Change | Lines |
|---|---|---|
| `colony_board` (190) | `squadView`: `return board.viewFor(i) if hasattr(board, 'viewFor') else (SquadView(...) if S else board)` | 1 |
| `clue_colony` (148) | `checkOptions`: `bridge_board.checkBridge(world, N, nLiar)`; `colonyRules`: `+ bridge_agents.bridgeRules(env, i)` | 2-4 |
| `clue_text` (193) | `observe`: `lines += bridgeLines(b, i, t)`; `parse`: `if (x := parseBridge(self, parsed, i)) is not None: return x` | 3 |
| `clue_runs` (105) | `clueSetup`: `BridgeBoardEnv` when `any(k in w for k in BRIDGE_KEYS)` | 2 |
| `colony_board` (190), `stage4Members` | `return bridgeMembers(world, out) if any(k in world for k in BRIDGE_KEYS) else out` (lazy import), so `colony_trace.replay` (199 lines, unchanged) and every other numpy path get bridges | 2 |
| `clue_roll` (195) | `boardFactory`: the bridge keys join `s4` and select `BridgeBoardEnv`; `coopRows`: `**(bridgeColumns(...) if isPhase20(w) else {})` | 3 |

If a hook would take a module past 200 lines, the surrounding logic moves into the new module first, with the existing tests unchanged.

As built (NFR-5): `clue_text` 196 (the hooks plus the mirror-share summary), `clue_roll` 199, `colony_board` 191, `clue_colony` 150, `clue_runs` 107; `clueboard`, `colony_trace` and `clue_agents` unchanged. `clue_roll` is one line from the limit, so A1's bridged step (Phase 19, T5a) must put new code elsewhere.

## `bridge_grid.py` and `bridge_plan.py` (new)

The grids are in `bridge_grid`; the plans, the cost rule and the pilot check are in `bridge_plan`, so each stays under 200 lines.

```python
# bridge_grid.py
_S = ARMS4['squads']                                 # colony, guards 'quarter', squads 8 (Stage 4's arm, unchanged)
ARMS20 = dict(squads=_S, colonyGuards=ARMS4['colonyGuards'],
              coupled=dict(_S, couple=0.25), bridge1=dict(_S, couple=0.25, bridges=1),
              bridge2=dict(_S, couple=0.25, bridges=2), bridgeGuard=dict(_S, couple=0.25, bridges=1, bridgeGuard=True))
SEEDS8, SEEDS5 = COLONY_SEEDS, COLONY_SEEDS[:5]       # 1800-1807, 1800-1804
C1_CELLS = dict(coupled=SEEDS5, bridge1=SEEDS8, bridge2=SEEDS5, bridgeGuard=SEEDS5)   # 23 boards at N 64, independent liars
C1_CLEAN = dict(squads=SEEDS5, coupled=SEEDS5, bridge1=SEEDS5)   # P20-14: 15 boards at N 64, no liars, 16 guards
PILOT20 = ('coupled', 'bridge1', 'bridgeGuard')        # seed 1890, N 64, with liars; no clean pilot board
REUSED20 = (('squads', 'colony4'), ('colonyGuards', 'colony64'))   # 16 boards, seeds 1800-1807, with liars

def c1Cell(study, arm, seed, fault='independent', runner='llm'):   # fault 'clean': nLiar 0 (P20-14); runner 'numpy' for B3
    return colonyCell(study, arm, 64, seed, fault, runner, arms=ARMS20)   # + checkOptions
def c1Grid(): ...                                    # study 'colony20': C1_CELLS ('independent') + C1_CLEAN ('clean'), 38 cells
def c1PilotGrid(): ...                               # study 'colony20Pilot'
def reusedCells20(seeds=COLONY_SEEDS): ...          # stage4Grid() squads|independent N 64 + stage64Grid() colonyGuards
def c1Estimate(cells, perCall): ...                  # calls (cellCalls) and cost per arm; perCall a number or {arm: $}; an arm
                                                     # without its own (clean squads, bridge2: not in the pilot) at the highest
def c1Range(per=PER_CALL4, allow=ALLOW20): ...       # the README's (low, high) before the pilot: main, pilot, total

PARTB_MODELS = ('warm',) + tuple(f'r17mix_s{s}' for s in range(1, 9))   # final adapters, as published (P20-10)
def squadEvalSuite(models=PARTB_MODELS):            # evalCell(m, 'n32sq4' / 'n32sq4liar', 'blackboard', 32, sd, then cell['cfg']['world']['squads'] = 4,
                                                     # nLiar=8 for liar boards), sd in BIG_SEEDS (900-909)
def reusedPartB(root=COLAB, models=PARTB_MODELS, files=PARTB_FILES): ...   # |n32 and |n32liar rows of eval_p17/<run>.csv and
                                                     # eval_p17s0/warm.csv, configuration checked (ValueError)
def bridgeCheckCells(seeds=BIG_SEEDS[:5]): ...       # P20-11: warm, N 16, world19e(S) + couple 0.25 + bridges 1, S in (8, 4),
                                                     # 4 guards, 4 liars, seeds 900-904
def projectHours20(turnsPerHour=40_000, loadHours=0.4, unitsPerHour=12.0): ...   # part b and the check (README's derivation)

# bridge_plan.py
C1_PILOT_PLAN = dict(...)                            # frozen at T8, after the user approves the estimate (P20-8)
C1_PLAN = dict(C1_PILOT_PLAN, frozen=False, pilotHash=None, verdict=None, projection=None, forecast=dict(...))   # frozen at T9
def costRule20(projected, plan=None): ...            # report projected beside plan['costRule']['ceiling'] (35.0); always 'ask'
def pilotCheck20(rows, plan=None): ...               # FR-C2; then c1Estimate(c1Grid(), the pilot's cost per call by arm) and costRule20
```

`C1_PILOT_PLAN` and `C1_PLAN` are dicts with `version`, `frozen`, `plan='specs/multiagent/phase20/'` and the hash, as `STAGE4_PLAN`. Their contents:

| Item | Definition |
|---|---|
| world | `WORLD18`, Claude Haiku 5.5, low effort, full memory, 40 turns, blackboard; independent scripted liars in the first 16 slots, guards in the next 16 (`colonyCell`); on clean boards no liars, and the 16 guards in the first 16 slots |
| arms and cells | `ARMS20`, `C1_CELLS`, `C1_CLEAN`, `REUSED20`, `PILOT20` |
| H20-1 (primary, Gate C1 part i) | `bridge1` − `colonyGuards`, `honestPooled`, N 64, independent liars, 8 boards paired on seed: one-sided exact sign-flip > 0, α 0.05 (smallest p 1/256) |
| H20-2 (Gate C1 part ii) | mean(`bridge1` − `colonyGuards`) ≥ 0.5 × mean(`squads` − `colonyGuards`), same 8 boards; bootstrap interval; uncorrected sign-flip p of the per-board margin (`bridge1` − `colonyGuards`) − 0.5 (`squads` − `colonyGuards`), reported |
| robustness | H20-1 and H20-2 on `welfareHonest`; an estimate of the opposite sign marks the part not robust |
| H20-3 | win-back = (`bridge1` − `coupled`) / (`squads` − `coupled`), means over seeds 1800-1804, > 0.5; per-board sign-flip p of (`bridge1` − `coupled`) − 0.5 (`squads` − `coupled`). As built, `c1Summaries` marks it supported only when the coupling cost (`squads` − `coupled`) is above 0 and the win-back above 0.5 (implementation note, T5) |
| H20-4 | (`bridge2` − `bridge1`) < 0.25 × (`squads` − `coupled`), seeds 1800-1804; interval. As built, it also reports a one-sided sign-flip p for the margin (`bridge2` − `bridge1`) − 0.25 (`squads` − `coupled`) below 0 (implementation note, T5) |
| H20-5 | false-relay share, `bridge1` − `bridgeGuard` > 0, seeds 1800-1804; also `honestPooled`, `bridgeGuard` − `bridge1` (`pooled`, one-sided 'greater', as built) |
| H20-7 | cross-squad contamination per arm, descriptive; as built, also `bridge1` − `bridgeGuard` on `crossContamination` (`guarding`) |
| H20-8 (P20-14) | cost without liars: `honestPooled` (and `welfareHonest`) per arm on clean boards; `coupled` − `squads` and `bridge1` − `squads` (the plan's cost without liars, reference minus design, is their negative, `squads` − `coupled` and `squads` − `bridge1`; the report states both), `colony_report.pairs(rows, arm, m, fault='clean', base='squads')` over seeds 1800-1804, bootstrap interval, uncorrected one-sided sign-flip p < 0 (a cost; smallest p 1/32); descriptive, not part of Gate C1 |
| core measures | requirements FR-D5: `contestColumns` per board; gullibility, suppression, verification, collaboration and error correlation pooled per arm (`rl19_measures.ratio`, `lags`); welfare per agent-turn and per 1,000 tokens; tokens per solved task; Gorelick's index per board (`rl19_spec.dolIndex`); cross-squad contamination. No role persistence (single boards) |
| inert-bridge rule | if Gate C1 passes and mean(`bridge1` − `coupled`) ≤ 0 on seeds 1800-1804: stop and ask before A1 adopts bridges |
| secondary families | no Holm: each secondary has 5 boards, smallest p 1/32, reported uncorrected and labelled exploratory (the plan: families of two or more use 8 boards) |
| pilot | `PILOT20`, seed 1890, not analysed; maxInvalid 0.05; mirror posts > 0; relays > 0 per bridge board; bridge input tokens per call ≤ 2 × 780 |
| cost rule | report and wait (P20-8): the pilot's estimated cost before the pilot, and its projection of the main run (pilot cost per call by arm × `c1Grid` calls, 1,920 per liar board and 2,560 per clean board) after it; the user approves each. `c1Estimate` prices arms the pilot does not cover (clean `squads`, `bridge2`) at the pilot's highest cost per call. Expected ceiling $35 for the main run (raised from $25 with P20-14) |
| cap | `cap=250.0`, `capNote='per calendar month (the user, 2026-11-09)'`, shared with A2 (P20-9); `Budget` counts the current month only (NFR-7) |
| forecast (`C1_PLAN` only) | B3's fitted simulator, refit on the pilot, with `RuleBridge` for bridges (P20-13); file `specs/multiagent/phase20/c1_predictions.json`, its commit and SHA-256; the file B3's `c1Forecast()` writes: `C1_EFFECTS` (`C1-1` to `C1-8`: H20-1 to H20-4, H20-5 on both measures, and H20-8's clean `bridge1` − `squads` and `squads` − `coupled`; `C1-8` is the negative of H20-8's reported `coupled` − `squads`), each with five lines (fitted, unfitted, prior-only, pilot-only, every-design-helps) by B3's rules (Phase 22, P22-7, P22-8) |
| part b | `squadEvalSuite`, `reusedPartB`, the measures of FR-D3; the final `r17mix` adapters as published (P20-10); descriptive |
| exploratory | True, as every Phase 18 plan |

## Measures (`bridge_mech.py`)

```python
def isPhase20(world): ...                            # a bridge key in the world (coopRows adds bridgeColumns only then)
def tokensByRole(board, logs): ...                   # input tokens per call: bridge, mirror holder, other (NaN without calls)
def bridgeColumns(cfg, board, logs=None, answers=None): ...   # FR-D1's columns; zero mirror posts and relays without them
def c1Columns(cfg, rp): ...                          # stage4Columns + bridgeColumns + contestColumns, from a replay; the latter two
                                                     # read the replay's answers (rp.answers, numpy members' included)
def runC1(cfg, seed, client): ...                    # runClue's signature for runLLMCell
def runC1Cell(cell): ...                             # as runStage4Cell; numpy cells (B3's rows) through replay
def reusedRows20(client, prior, cells): ...          # as reusedRows4, with C1's columns; every saved column must be unchanged
def boardDol(row): ...                               # Gorelick's index on one board (rl19_spec.dolIndex, pos 0)
def tokPerSolved(row): ...                           # (inputTokens + outputTokens) / solved
def coreMeasures(ix, arm, fault='independent'): ...  # FR-D5's core measures over an arm's boards
```

| Measure | Definition |
|---|---|
| Honest pooled share | as Phase 18 (`clueMetrics`), all subtasks |
| Raw honest welfare | `welfareHonest`, per agent-turn |
| Coupled and uncoupled welfare | honest value solved minus penalties, split by whether the subtask was coupled, per agent-turn |
| Coupled solves (honest only) | `coupledSolved`: honest solves of coupled subtasks; `coupledSolveShare`: `coupledSolved` / coupled subtasks that appeared; `coupledOfSolves`: `coupledSolved` / honest solves |
| Mirror posts | posts in `mirrorLog`; false share; `mirrorPostsPerHolder`: honest mirror posts / honest cross-clue holdings (holder-subtask pairs) |
| Relays | `relayLog` entries; per bridge turn; false-relay share; median lag from the source post |
| Relays used | relays whose value a correct honest answer agreed with |
| Cross-squad contamination | honest answers on coupled subtasks agreeing with a false relayed value posted before them (so always wrong), over honest answers on coupled subtasks (`crossContamination`) |
| Bridge load | bridges' opens, solves and relays per turn; guarding bridges' guard posts per turn |
| Tokens by role | input tokens per call for bridges, mirror holders and others |
| Phase 18 columns | as Stage 4 (`stage4Columns`: guard-held lies, contest rate and lag, wrong answers per lie, openers per lied subtask, tokens per call) |
| Phase 19 columns | `contest_eval.contestColumns`, read by `c1Columns` with the replay's answers (`rp.answers`, numpy members' answers included): liar posts, contests (and on guard-held clues), `contestLags`, `misinformedFirst`, `honestTurns`, `liarFirst`, `uncorrected`, `wrongHonest`, `sameWrong`, per-slot `agentTurns`, `agentShares`, `agentContests`, `agentSubmits`, `agentOpens` |
| Cost without liars (P20-14) | `honestPooled` on clean boards per arm; `coupled` − `squads` and `bridge1` − `squads` paired on seed; `welfareHonest` beside it |
| Gullibility, suppression | `rl19_measures.ratio` over an arm's liar boards: `misinformedFirst` / `honestTurns` (first wrong answers made while misinformed per honest agent-turn, Phase 19's named variant; the plan's share of honest answers made while misinformed, right or wrong, is not computed); `uncorrected` / `liarFirst` |
| Verification | contests per lie (`contests` / `liarPosts`), time to contest (median of `rl19_measures.lags`), share of lies on a guarded clue (`guardLies` / `liarPosts`) |
| Error correlation | `sameWrong` / `wrongHonest` |
| Clues others used (B1) | the existing `assisted` column: the share of solves that used a clue another agent posted |
| Damage won back | does not apply: explRL's cache has no clean `plain` or clean `colonyGuards` board at 64 agents, and C1 adds none |
| Welfare per 1,000 tokens | as `welfarePerKTok` in `rl19_measures.runMeasures`: `welfare` × N × `tEnd` summed over the arm's boards, over their tokens / 1,000 |
| Tokens per solved task | (`inputTokens` + `outputTokens`) / `solved`, per board; the arm's mean |
| Division of labour | Gorelick's index per board, `rl19_spec.dolIndex(rs, nLiar, positions=(0,))` on the board's row with `pos` 0 and `agents` the slot order; the arm's mean; descriptive |

The reused rows have no bridge or Phase 19 columns; they get C1's columns (zero relays and mirrors, and `contestColumns`) from the cached replay, with every earlier column unchanged. Role persistence is not measured: C1 plays single boards. `contestColumns` reads `shareLog` only, so on a bridge board a relayed false value counts as the bridge's post there; relayed lies are in the relay and contamination rows. Mirror posts are not in `shareLog`, but `apply` counts them in `counts['shares']`. Mirror posts are counted in `shares` and so in sharing per held clue; `contestColumns`' per-agent shares and Gorelick's index count a mirror post as an idle turn, a small bias against the coupled arms in division of labour, which the report states (requirements FR-D5). Mirror posts are also measured by `mirrorPosts` and `mirrorPostsPerHolder`.

## Analysis and report (`bridge_report.py`, `bridge_write.py`)

The analysis is in `bridge_report`; the report, the figure and the synthetic rows are in `bridge_write`, so each stays under 200 lines.

```python
# bridge_report.py
def planned20(plan=C1_PLAN): ...                     # {(level, seed)} of every planned cell: new (with liars and clean) and reused
def gateC1(rows, plan=C1_PLAN, nboot=2000, metric='honestPooled'): ...   # parts (i) and (ii)
def c1Summaries(rows, plan=C1_PLAN, nboot=None): ... # every C1_PLAN item (FR-D2); ValueError unless every planned cell is present
def partBSummaries(rows, models=PARTB_MODELS, warm='warm', seeds=BIG_SEEDS): ...   # FR-D3 (H20-6)

# bridge_write.py
def writeC1(path, S, meta, plan=C1_PLAN, partB=None): ...   # report.md (FR-D4)
def figC1(out, S): ...                               # c1.png
def syntheticRows20(lead=0.171, cost=0.10, back=0.07, ...): ...   # every planned cell with known effects (AC-9)
def syntheticPartB(gain4=0.05, gain1=0.006, ...): ...             # part b rows with known effects
```

`demo_c1` runs quick (the fake client and synthetic rows), then the live stages by `EXPLRL_C1_STAGE`: `pilot` (asserts `C1_PILOT_PLAN['frozen']`, which records the user's approval of the estimate), `main1` and `main2` (the seed batches 1800-1803 and 1804-1807; `main2` needs `main1` with invalid replies under 5%), and `main` (both batches present with invalid replies under 5%; it first replays every cell of the full grid through the cache-only client, where a miss raises `CacheMiss` before any paid call, then writes the rows, with `reused.csv`, at $0). Every main stage asserts `mainReady()`: both plans frozen, `C1_PLAN['pilotHash']`, B3's forecast with its SHA-256, and `C1_PLAN['projection']['approved']`. Part b is flagged `train`.

## Statistics

- **H20-1:** exact sign-flip over 8 paired boards (`colony_report.signFlipExact`), one-sided. Per-board differences on these seeds for `squads` − `colonyGuards` were 0.132-0.203 (mean 0.171, SD 0.023). At that spread, a `bridge1` lead of half of it (0.086) is about 3.7 SD from zero, so a real effect of that size passes (8 of 8 positive gives p = 1/256).
- **H20-2** is a margin check on means, with `bootSeeds` intervals. It is not a test, so the gate has one test, as the plan names.
- **Secondary** estimates use `bootSeeds` over the 5 shared seeds and uncorrected sign-flip p.
- **H20-8 (cost without liars, P20-14):** `coupled` − `squads` and `bridge1` − `squads` on the 5 clean boards, paired on seed, with `bootSeeds` intervals and an uncorrected one-sided sign-flip p (the arm below `squads`; smallest p 1/32). Descriptive; no Holm family and no gate.
- **Part b:** per run, the gain is mean welfare over seeds 900-909 minus the warm start's, on clean boards, in squads of 4 and on one board. H20-6 is the per-run difference, with a sign-flip over 8 runs (smallest p 1/256), descriptive. Phase 17's H17-1 gain at 4 agents (+0.078) and its 32-agent gain (+0.006) are shown beside it.

## Cost derivation (`results/multiagent/colony/*/runs.csv`)

| Board (Claude Haiku 5.5, 40 turns, independent liars) | Boards | Mean cost | Calls | $ per call | Input tokens per call |
|---|---|---|---|---|---|
| Stage 4 `squads`, N 64 | 8 | $0.588 | 1,920 | 0.000306 | 780 |
| 64-agent run `colonyGuards`, N 64 | 8 | $1.721 | 1,920 | 0.000896 | 6,463 |
| 64-agent run `plain`, N 64 | 8 | $1.659 | 1,920 | 0.000864 | 5,090 |
| Stage 4 `squadsAll`, N 64 | 8 | $0.526 | 1,920 | 0.000274 | 720 |
| Stage 4 clean boards, N 16 (`colonyGuards`, `guardDeal`, `failFlag`, `plain`; reused for `colonyGuards`, `plain`) | 8 each | $0.169-0.209 | 640 | 0.000264-0.000327 | 904-962 |
| The same cells with liars, N 16 | 8 each | $0.188-0.252 | 480 | 0.000391-0.000526 | 1,435-1,594 |

Stage 4 has no clean `squads` cell, at 64 agents or any other size. Its only clean cells are the 16-agent ones above, so P20-14's 15 clean boards are all new.

- **The new boards with liars:** 23 boards × $0.588 = $13.52, or $17.0 at the 1.25x allowance.
- **The clean boards (P20-14):** a clean board has 64 × 40 = 2,560 calls, against 48 × 40 = 1,920 on a liar board. The 16-agent cells above measure the same ratio, 640 / 480. So a clean board costs $0.588 × 2,560 / 1,920 = $0.784, and $0.98 with the 1.25x allowance on `coupled` and `bridge1` (they have mirror lines and bridges). 5 × $0.784 (`squads`) + 10 × $0.784-0.98 = $11.8-13.7. This is conservative: at 16 agents a clean board cost 0.62-0.73 times a liar board per call, and 0.83-0.97 times in total.
- **The pilot:** 3 boards with liars × the same, $1.8-2.2. No clean pilot board: clean boards add no new mechanism, and the pilot's liar boards already check mirrors, relays, bridge prompts and invalid replies.
- **The total:** main run $25.3-30.6 (23 boards with liars and 15 clean), plus the pilot: **$27.0-32.8**, 41 new boards. P20-8's expected ceiling for the main run is $35 (raised from $25).
- **On the ledger:** the cap is $250 per calendar month (P20-9). The ledger's 491,301 entries ($233.18 in `results/multiagent/llm/spend.jsonl`) are undated and all from before November 2026. Once `Budget` counts by month (NFR-7), they count as earlier months, and C1's $27.0-32.8 plus A2's $34-39, about $61-72, fit November's cap. The user approves each estimate before it is spent (P20-8).
- **GPU (`projectHours20`):**
  - part b's new cells: 201,600 honest agent turns, about 5.0 A100 hours at 40,000 turns per hour;
  - the bridge check: 4,800 turns, about 0.5 hours with model loading;
  - re-running the one-board arm would add at least 5 hours.

  The rate comes from Phase 17's step 0 (15 models × 42,800 turns in about 16 hours) and `RL17_PLAN`'s "about 9 more" hours for 9 models.

## Tests

| Test | Flag | What it checks |
|---|---|---|
| `test_couple` | offline | AC-2: every fourth subtask per squad, holders in s and s + 1, never both clues, values and clues equal the `squads` board's |
| `test_mirror_isolation` | offline | AC-3: mirror posts (Claude and numpy posters) absent from s's `tally`, `colonyLine`, `knownColony` and prompt; `mirrorTally` built from `mirrorLog`; opening or answering a mirror is invalid; other squads see nothing |
| `test_deal_bridges` | offline | AC-4: one and two bridges, guarding bridges, uneven liars (6 of 16 in squads of 4), the errors |
| `test_relay` | offline | AC-4: a relay of a minority mirror value is valid and logged with its source; a non-bridge's unknown value is invalid |
| `test_bridge_liars` | offline | AC-5: scripted liars of s + 1 post on mirrors; their values reach the relay log; honest rule agents post true cross clues on mirrors by `ColonyAgent`'s rule (P22-12), so a `RuleBridge` relays a true value when the mirror leads with it |
| `test_relay_credit` | offline | AC-6: the split under `'credit'`; `'individual'` equal to `ColonyBoardEnv`; `relaySource` finds the liar |
| `test_bridge_prompts` | offline | rule sentences and lines appear only with bridge keys; a pre-Phase-20 prompt is byte-identical |
| `test_rollout_bridges` | offline | AC-7: 16-agent fake-policy `rollout` in squads of 4 with bridges; `bridgePromptTokens`; the adaptive-liar path with the fake client |
| `test_c1_grid` | offline | 38 new cells (23 with liars, 15 clean), 3 pilot cells, 16 reused cells; calls 1,920 per liar board and 2,560 per clean board; AC-10 (clean cells: `nLiar` 0, 16 guards, bridges dealt, no clean `colonyGuards`); part b's 180 new cells; the plans' freezes asserted; `checkOptions`' errors; `bridgeCheckCells` (10 cells, guards 4, nLiar 4, both squad sizes); `pilotCheck20` and `costRule20` (always 'ask') on synthetic pilot rows |
| `test_c1_numpy` | offline | `runC1Cell(colonyCell('t', 'bridge1', 64, 1890, 'independent', 'numpy', arms=ARMS20))` (equivalently `c1Cell('t', 'bridge1', 1890, runner='numpy')`) runs and shows honest and false mirror posts and relays (B3's handoff) |
| `test_c1_measures` | offline | AC-11: `contestColumns`, the pooled ratios, `dolIndex` on a one-board sequence, welfare per 1,000 tokens and tokens per solved task on a hand-built board |
| `test_c1_hashes` | offline | Phase 5-19 configuration and plan hashes unchanged |
| `test_budget_month` | offline | NFR-7, in `nbs/llm_budget.ipynb`: entries carry `month`; `spent()` counts the current month only, across a month boundary; undated legacy entries count as earlier months; `spentAll()` sums everything |
| `test_c1_report` | offline | AC-9 on `syntheticRows20` with known effects: the gate's parts, the margin, win-back, the inert-bridge flag, the clean contrasts (H20-8); `partBSummaries` on synthetic part-b rows |
| regression gate | `tools/c1_regression.py` | every earlier live board (413) replays from the cache-only client with every saved column equal (`replayCheck`, and Stage 4's columns for Stage 4 and 4b); then the 16 reused cells through `reusedRows20` with C1's columns. Passed 2026-11-10 (166 s) |
| `test_main_ready` | offline | AC-8, in `demo_c1`: the main stage refuses unless both plans are frozen, the pilot hash matches, the forecast's SHA-256 matches and the projection is approved |
| `test_c1_rows` | offline | `runC1Cell` and `reusedRows20` add the bridge columns and `contestColumns` to every C1 row |

## Handoff to Phase 19 (A1), recorded here so the next step is specified

Phase 19 adds one engineering step before its speed check: T5a (the wiring and tests, which can start now that C1's code exists) and T5b (recording Gate C1 and setting the world, after the gate):

- **World.** `BASE19`'s world gains `couple=0.25` and `bridges=1` for every arm (Phase 19's P19-8, the user, 2026-11-10; stop and ask if the inert-bridge rule fires). Liars stay uneven across squads (`dealSquads`), and bridges come from `dealBridges`.
- **Speed check.** `SPEED19` adds `bridgePromptTokens` (the window is refused if any prompt exceeds 3,072 tokens), relays per bridge turn, and `WARM_ANSWERS` measured in the bridged world.
- **Rewards.** Contest credit reads `relaySource` (P20-12), and relay credit follows FR-A5. Phase 19 recorded both on 2026-11-09 (its FR-A9 and T5a). The split is built here (`_creditTo`, `_reward`); Phase 19's T5a adds the relay-aware `ContestLog`.
- **The pilot's two squad sizes** both have bridges: 16 agents in squads of 4 make a ring of 4 pairs, and in squads of 8 a ring of 2.
- **Results to carry over.** P20-11's check reports whether the warm start relays at all. If it never does, A1's README records that bridges start inert for the 3B model.
- **Contamination across squads** is `bridge_mech`'s `crossContamination`; it is already in every bridged row through `coopRows`, and Phase 19 reuses it; `contestColumns` is unchanged.
- **Prompt length.** `SPEED19` records `bridgePromptTokens(cfg, seeds, tok=<3B tokenizer>, policy=<warm LocalPolicy>)['bridge']` (the prompt only); Phase 19's `longestBridge` (prompt plus reply, per step) is computed in Phase 19's own code (`rl19_step` / `rl19_bridge`) from the step rollout's prompts and `board.bridgeOf`.
- **Phase 19's `contestSuite`** adds the best arm in 64-agent squads with bridges, as its FR-C1 says.
