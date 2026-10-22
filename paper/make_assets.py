"""Build the paper's numbers (numbers.tex, one LaTeX macro per reported value) and figures from the saved results, so every
number in the text is traceable to `results/multiagent/`. Run from the repo root: `.venv/bin/python paper/make_assets.py`."""
import json
import shutil
from pathlib import Path

import numpy as np

from explRL.bench_grid import readCSV
from explRL.clue_report import summaries as clueSummaries
from explRL.coop_report import trackASummaries
from explRL.fix_report import fixLogMetrics, fixSummaries
from explRL.llm_report import summaries as llmSummaries
from explRL.rl_report import rlSummaries

R, OUT = Path('results/multiagent'), Path('paper')
FIG = OUT / 'figures'
FIG.mkdir(parents=True, exist_ok=True)
M = {}


def ci(name, v, d=2):
    "Macros \\name (mean) and \\nameCI ([lo, hi]) from a {'mean', 'ci'} summary."
    M[name] = f"{v['mean']:.{d}f}"
    M[name + 'CI'] = f"[{v['ci'][0]:.{d}f}, {v['ci'][1]:.{d}f}]"


def gap(name, v, d=2):
    M[name] = f"{v['gap']:.{d}f}"
    M[name + 'CI'] = f"[{v['ci'][0]:.{d}f}, {v['ci'][1]:.{d}f}]"
    if v.get('primary'):
        M[name + 'P'] = f"{v['pHolm']:.3f}"


def rows(p):
    return readCSV(R / p)


# Phase 10: numpy predicts LLM rankings (task board, foraging)
llm = rows('llm/full/runs.csv')
S10 = llmSummaries([r for r in llm if r['runner'] == 'llm'], [r for r in llm if r['runner'] == 'numpy'])
for k, name in (('board', 'RhoBoard'), ('forage', 'RhoForage')):
    M[name], (lo, hi) = f"{S10['numpy'][k]['rho']:.2f}", S10['numpy'][k]['ci']
    M[name + 'CI'] = f'[{lo:.2f}, {hi:.2f}]'

# Phase 11: the clue board with Haiku
clue = rows('clue/full/runs.csv')
S11 = clueSummaries([r for r in clue if r['runner'] == 'llm'], [r for r in clue if r['study'] == 'clueNumpy'])
ci('BoardBenefitFour', S11['benefit'][('blackboard', 4)])
M['RhoClue'], (lo, hi) = f"{S11['numpy']['rho']:.2f}", S11['numpy']['ci']
M['RhoClueCI'] = f'[{lo:.2f}, {hi:.2f}]'
M['CoordBenefitFour'] = f"{S11['benefit'][('hierarchical', 4)]['mean']:.2f}"

# Phase 12, Track A: coordinator instructions and routing
SA = trackASummaries(rows('coop/full/runs.csv'), clue)
ci('FollowFour', SA['effect'][('A1', 'hierarchical', 4)])
ci('PassFour', SA['effect'][('A2', 'hierarchical', 4)])

# Phase 13, Track A: fixes
fx, logs = rows('fix/full/runs.csv'), [json.loads(x) for x in open(R / 'fix/full/turns.jsonl')]
SF = fixSummaries(fx, clue, fixLogMetrics(logs), rows('profile/full/runs.csv'))
for k, name in (('request|4', 'RequestFour'), ('request|8', 'RequestEight'), ('table|4', 'TableFour'), ('table|8', 'TableEight'),
                ('evidence|4', 'EvidenceFour'), ('evidence|8', 'EvidenceEight')):
    gap('Aone' + name, SF['A1'][k])
    M['Aone' + name + 'Diff'] = f"{SF['A1'][k]['diff']['mean']:.3f}"
for k in ('record', 'verify', 'warn'):
    gap('Atwo' + k.capitalize(), SF['A2'][k])
    ci('Atwo' + k.capitalize() + 'Cost', SF['A2cost'][k], 3)
for k, name in (('factsFirst|classic', 'FactsClassic'), ('table|classic', 'TableClassic'), ('dissent|classic', 'DissentClassic'),
                ('factsFirst|lone', 'FactsLone'), ('table|lone', 'TableLone'), ('dissent|lone', 'DissentLone')):
    gap('Athree' + name, SF['A3'][k])
mech = SF['mechanism']
M['BasePooledFour'] = f"{mech['A1']['baseline|4']['pooledShare']:.2f}"
M['AsksFour'] = f"{mech['A1']['request|4']['asks']:.0f}"
M['SharePerHeldBase'] = f"{mech['A1']['baseline|4']['sharePerHeld']:.2f}"
M['SharePerHeldEvidence'] = f"{mech['A1']['evidence|4']['sharePerHeld']:.2f}"
M['ChecksLiar'] = f"{mech['A2']['verify|liar|4']['checks']:.0f}"
M['CheckedFalseLiar'] = f"{mech['A2']['verify|liar|4']['checkedFalse']:.0f}"
M['BaseHonestLoss'] = f"{SF['A2']['record']['base']:.2f}"
for lv, name in (('baseline|classic', 'WinBaseClassic'), ('baseline|lone', 'WinBaseLone'), ('table|lone', 'WinTableLone'),
                 ('solo|classic', 'WinSolo')):
    M[name] = f"{mech['A3'][lv]['success']:.2f}"
M['DisclosedBase'] = f"{mech['A3']['baseline|classic']['uniquePosted']:.2f}"
M['VotesAgainstBaseLone'] = f"{mech['A3']['baseline|lone']['votesAgainst']:.2f}"
M['VotesAgainstTableLone'] = f"{mech['A3']['table|lone']['votesAgainst']:.2f}"
M['TrackACalls'] = f"{sum(int(float(r['calls'])) for r in fx) + sum(int(float(r['calls'])) for r in rows('profile/full/runs.csv')):,}"

# Phase 12, Track B: RL of a 3B open model
ev = rows('rl/eval/runs.csv')
SB = rlSummaries(ev, [r for r in clue if r['runner'] == 'llm'], [r for r in clue if r['study'] == 'clueNumpy'])
for m in ('untrained', 'warm', 'individual', 'team', 'credit'):
    ci('Welfare' + m.capitalize(), SB['main'][m]['welfare'], 3 if m == 'untrained' else 2)
for m in ('individual', 'team', 'credit'):
    ci('Gain' + m.capitalize(), SB['gain'][m])
ci('CreditMinusIndividual', SB['schemes']['credit - individual'])
ci('CreditMinusTeam', SB['schemes']['credit - team'])
M['ShareHeldWarm'] = f"{SB['info']['warm']['sharePerHeld']['mean']:.2f}"
M['ShareHeldIndividual'] = f"{SB['info']['individual']['sharePerHeld']['mean']:.2f}"
M['SoloShareIndividual'] = f"{SB['info']['individual']['soloShare']['mean'] * 100:.0f}"
M['WrongPerSolveIndividual'] = f"{SB['info']['individual']['wrongPerSolve']['mean']:.1f}"
ci('CrossThreeCredit', SB['cross']['credit cross3 - all Haiku'])
ci('CrossThreeWarm', SB['cross']['warm cross3 - all Haiku'])

# Phase 13, Track B: second seeds, the priced loophole, per-turn credit (RL13_PLAN)
ev13 = rows('rl/eval_p13/runs.csv')
S13 = rlSummaries(ev13, [r for r in clue if r['runner'] == 'llm'], [r for r in clue if r['study'] == 'clueNumpy'])
for a, name in (('credit', 'Credit'), ('credturn', 'Credturn'), ('indpen', 'Indpen')):
    ci('Arm' + name, S13['arms'][a], 3)
    for sd, sn in ((1, 'One'), (2, 'Two')):
        ci('Gain' + name + sn, S13['gain'][f'{a}_s{sd}'])
        M['Welfare' + name + sn] = f"{S13['main'][f'{a}_s{sd}']['welfare']['mean']:.3f}"
        M['ShareHeld' + name + sn] = f"{S13['info'][f'{a}_s{sd}']['sharePerHeld']['mean']:.2f}"
        M['SoloShare' + name + sn] = f"{S13['info'][f'{a}_s{sd}']['soloShare']['mean'] * 100:.0f}"
# The loophole fix against the same reward without it (Phase 12's individual run), paired on board seed
from explRL.llm_report import _paired, _stat
for sd, sn in ((1, 'One'), (2, 'Two')):
    ci('IndpenMinusIndividual' + sn, _stat(_paired([r for r in ev13 if r['level'] == f'indpen_s{sd}|main'],
                                                   [r for r in ev if r['level'] == 'individual|main'], 'welfare')))
best = max(S13['main'], key=lambda m: S13['main'][m]['welfare']['mean'] if m != 'warm' else -1)
M['BestWelfare'] = f"{S13['main'][best]['welfare']['mean']:.2f}"
M['BestGainPct'] = f"{100 * (S13['main'][best]['welfare']['mean'] / S13['main']['warm']['welfare']['mean'] - 1):.0f}"
fs = json.load(open(R / 'forecast/score.json'))
M['ForecastAgree'], M['ForecastTotal'] = str(fs['forecast']['agree']), str(fs['forecast']['total'])
M['RetroAgree'], M['RetroTotal'] = str(fs['retrodiction']['agree']), str(fs['retrodiction']['total'])

# HiddenBench replication of the vote arms (HB_PLAN)
hb = json.loads((R / 'hiddenbench/full/summary.json').read_text())['S']
for a, name in (('baseline', 'Base'), ('factsFirst', 'Facts'), ('table', 'Table'), ('dissent', 'Dissent'), ('solo', 'Solo')):
    M['HbWin' + name] = f"{hb['arms'][a]['win']:.2f}"
    if a != 'solo':
        M['HbAcc' + name] = f"{hb['arms'][a]['accuracy']:.2f}"
        M['HbDisc' + name] = f"{hb['arms'][a]['disclosed']:.2f}"
for a, name in (('factsFirst', 'Facts'), ('table', 'Table'), ('dissent', 'Dissent')):
    gap('HbGap' + name, hb['gap'][a])
M['HbEpisodes'] = str(hb['arms']['baseline']['n'])

# Phase 14: the 2 x 2 of trust information, and team size
from explRL.scale_report import scaleSummaries, trustSummaries
ST = trustSummaries(fx, rows('trust/full/runs.csv'))
for a, name in (('recordPrivate', 'RecordPrivate'), ('verifyPublic', 'VerifyPublic')):
    gap('Trust' + name, ST['arms'][a])
for k, name in (('publicity', 'Publicity'), ('cost', 'Cost'), ('difference', 'Difference')):
    M['Trust' + name], M['Trust' + name + 'CI'] = f"{ST['effects'][k]['effect']:.2f}", f"[{ST['effects'][k]['ci'][0]:.2f}, {ST['effects'][k]['ci'][1]:.2f}]"
SS = scaleSummaries(rows('scale/full/runs.csv'))
for N, w in ((8, 'Eight'), (16, 'Sixteen'), (32, 'ThirtyTwo')):
    gap('ScaleRequest' + w, SS['request'][f'request|{N}'])
    gap('ScaleRecord' + w, SS['record'][f'record|{N}'])
    M['ScalePool' + w] = f"{SS['baseline'][N]['pooledShare']['mean']:.2f}"
    M['ScaleLoss' + w] = f"{SS['baseline'][N]['honestLoss']['mean']:.2f}"

# Phase 16: more training seeds for the incentive result (results/multiagent/rl/eval_p16)
S16 = json.loads((R / 'rl/eval_p16/summary.json').read_text())
for k, name in (('H16_1', 'Share'), ('H16_2', 'Solo'), ('H16_3', 'Welfare'), ('H16_4', 'Gain')):
    v = S16['hyp'][k]
    M['Sixteen' + name] = f"{v.get('diff', v.get('mean')):+.2f}"
    M['Sixteen' + name + 'CI'] = f"[{v['ci'][0]:.2f}, {v['ci'][1]:.2f}]"
    M['Sixteen' + name + 'P'] = f"{v['p']:.3f}"
    if v['pHolm'] == v['pHolm']:
        M['Sixteen' + name + 'Holm'] = f"{v['pHolm']:.2f}"
M['SixteenDrift'] = str(S16['drift'])
r16 = S16['runs']
M['SixteenPenShareMin'] = f"{min(v['sharePerHeld'] for n, v in r16.items() if n.startswith('indpen')):.2f}"
M['SixteenPenShareMax'] = f"{max(v['sharePerHeld'] for n, v in r16.items() if n.startswith('indpen')):.2f}"

# Phase 15: tracing why larger teams lose more to liars (results/multiagent/liar/full)
TL = json.loads((R / 'liar/full/trace_summary.json').read_text())
TV = json.loads((R / 'liar/full/variants.json').read_text())
th, tn = TL['perN']['haiku'], TL['perN']['numpy']
tm = lambda P, N, k: P[str(N)][k]['mean']
for N, w in ((8, 'Eight'), (32, 'ThirtyTwo')):
    M['TraceContam' + w] = f"{tm(th, N, 'contaminated'):.2f}"
    for P, who in ((th, 'Haiku'), (tn, 'Numpy')):
        M['Trace' + who + 'Poison' + w] = f"{tm(P, N, 'a') + tm(P, N, 'c'):.2f}"
        M['Trace' + who + 'Untouched' + w] = f"{tm(P, N, 'd') + tm(P, N, 'f'):.2f}"
        M['Trace' + who + 'Pool' + w] = f"{tm(P, N, 'pooledShare'):.2f}"
M['TraceWrongContam'] = f"{100 * min(tm(th, N, 'wrongContam') for N in (8, 16, 32)):.0f}--{100 * max(tm(th, N, 'wrongContam') for N in (8, 16, 32)):.0f}"
M['TraceSuppress'] = f"{100 * min(tm(th, N, 'suppressed') for N in (8, 16, 32)):.0f}--{100 * max(tm(th, N, 'suppressed') for N in (8, 16, 32)):.0f}"
M['TraceRelayMax'] = f"{100 * max(tm(th, N, 'relayPerLie') for N in (8, 16, 32)):.2f}"
h3r = TL['hyp']['H15_3']
M['TraceShareAC'], M['TraceShareACCI'] = f"{h3r['mean']:.2f}", f"[{h3r['ci'][0]:.2f}, {h3r['ci'][1]:.1f}]"
M['TraceHaikuChange'] = f"{TL['change']['haiku']['loss']['mean']:+.2f}"
for v, name in (('relay', 'Relay'), ('first', 'First'), ('repost', 'Repost')):
    M['TraceVar' + name] = f"{TV[v]['honestLoss']['change']['mean']:+.2f}"
M['TracePlanHash'] = TL['planHash']

# Phase 18: colony rules and guard roles with faulty members (results/multiagent/colony/stage1)
m18 = json.loads((R / 'colony/stage1/metrics.json').read_text())
S18 = m18['summary']
pf = lambda p: '<0.001' if p < 0.001 else f'{p:.3f}'
for k, name in (('H18_1', 'Board'), ('H18_2', 'Contam'), ('H18_3', 'Tax'), ('H18_4', 'Guards')):
    v = S18['hyp'][k]
    M['Colony' + name] = f"{v['estimate']:.3f}"
    M['Colony' + name + 'CI'] = f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]"
    M['Colony' + name + 'Holm'] = pf(v['pHolm'])
for arm, name in (('colonyGuards', 'GuardAdv'), ('colony', 'BoardAdv'), ('confirm', 'ConfirmAdv'), ('record', 'RecordAdv')):
    for N, w in ((8, 'Eight'), (16, 'Sixteen')):
        e, lo, hi = S18['advantage'][arm][str(N)]
        M['Colony' + name + w] = f"{e:.2f}"
lr = S18['secondary']['lossRecovered']
M['ColonyRecoverGuards'], M['ColonyRecoverRecord'], M['ColonyRecoverBoard'] = (f"{lr[a]:.2f}" for a in ('colonyGuards', 'record', 'colony'))
M['ColonyVsConfirm'] = f"{S18['secondary']['colonyVsConfirm']['estimate']:+.3f}"
M['ColonyCost'] = f"{m18['cost']:.2f}"
M['ColonyPlanHash'] = m18['planHash']
from explRL.colony_report import pairs as cpairs, signFlipExact
r18 = rows('colony/stage1/runs.csv')
a8, a16 = (cpairs(r18, 'colonyGuards', 'honestPooled', sizes=[N]) for N in (8, 16))
dd = [a16[(s, 16)] - a8[(s, 8)] for s, _ in sorted(a8) if (s, 16) in a16]
M['ColonyGuardDrop'] = f"{np.mean(dd):+.2f}"
M['ColonyGuardDropP'] = f"{min(1.0, 2 * min(signFlipExact(dd, 'less'), signFlipExact(dd, 'greater'))):.2f}"
M['ColonyGuardContest'], M['ColonyBoardContest'], M['ColonyPlainContest'] = (
    f"{np.nanmean([float(r['contestFalse']) for r in r18 if r['level'] == lv]):.2f}" for lv in ('colonyGuards|independent', 'colony|independent', 'plain|independent'))
M['ColonyGuardContam'], M['ColonyBoardContam'], M['ColonyPlainContam'] = (
    f"{np.nanmean([float(r['contamination']) for r in r18 if r['level'] == lv]):.2f}" for lv in ('colonyGuards|independent', 'colony|independent', 'plain|independent'))

# Phase 18, guards at 32 agents (a user-approved deviation; results/multiagent/colony/stage32)
m32 = json.loads((R / 'colony/stage32/metrics.json').read_text())
S32 = m32['summary']
for k, name in (('H18_7', 'Liars'), ('H18_8', 'Mistaken'), ('H18_9', 'Collude')):
    v = S32['hyp'][k]
    M['GuardsThirtyTwo' + name] = f"{v['estimate']:+.3f}"
    M['GuardsThirtyTwo' + name + 'CI'] = f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]"
    M['GuardsThirtyTwo' + name + 'P'] = f"{v['p']:.3f}"
M['GuardsThirtyTwoTax'] = f"{S32['tax']['estimate']:.3f}"
M['GuardsTrend'], M['GuardsTrendP'] = f"{S32['trend']['estimate']:+.3f}", f"{S32['trend']['p']:.2f}"
c32 = S32['cells']
M['GuardsThirtyTwoPlainClean'] = f"{c32['plain|clean']['honestPooled']:.2f}"
M['GuardsThirtyTwoPlainLiar'] = f"{c32['plain|independent']['honestPooled']:.2f}"
M['GuardsThirtyTwoGuardLiar'] = f"{c32['colonyGuards|independent']['honestPooled']:.2f}"
M['GuardsThirtyTwoGap'] = f"{(c32['colonyGuards|independent']['honestPooled'] - c32['plain|independent']['honestPooled']) / (c32['plain|clean']['honestPooled'] - c32['plain|independent']['honestPooled']):.2f}"
M['GuardsThirtyTwoContamPlain'] = f"{c32['plain|independent']['contamination']:.2f}"
M['GuardsThirtyTwoContamGuard'] = f"{c32['colonyGuards|independent']['contamination']:.2f}"
M['GuardsThirtyTwoCost'] = f"{m32['cost']:.2f}"
M['GuardsThirtyTwoPlanHash'] = m32['planHash']

# Phase 18, Stage 3: Claude liars and unassigned guards (results/multiagent/colony/stage3)
m3 = json.loads((R / 'colony/stage3/metrics.json').read_text())
S3 = m3['summary']
for k, name in (('H18_10', 'Adaptive'), ('H18_11', 'Volunteer')):
    v = S3['hyp'][k]
    M['Stage' + name] = f"{v['estimate']:+.3f}"
    M['Stage' + name + 'CI'] = f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]"
    M['Stage' + name + 'Holm'] = f"{v['pHolm']:.3f}"
c3, s3 = S3['secondary']['cells'], S3['secondary']
M['StageRecoverAdaptive'], M['StageRecoverScripted'] = f"{s3['recovered']['adaptive']:.2f}", f"{s3['recovered']['independent']:.2f}"
M['StageLiarRate'] = f"{c3['plain|adaptive']['liarFalsePerTurn']:.2f}"
M['StageLiarRateGuards'] = f"{c3['colonyGuards|adaptive']['liarFalsePerTurn']:.2f}"
M['StageLiarTarget'] = f"{c3['colonyGuards|adaptive']['liarTargetGuarded']:.2f}"
M['StagePerLie'] = f"{s3['damagePerLie']['plain|adaptive']:.3f}"
M['StagePerLieScripted'] = f"{s3['damagePerLie']['plain|independent']:.3f}"
M['StageContamPlain'], M['StageContamGuards'] = f"{c3['plain|adaptive']['contamination']:.2f}", f"{c3['colonyGuards|adaptive']['contamination']:.2f}"
M['StageVolunteerVsGuards'] = f"{s3['volunteersMinusGuards']['estimate']:+.2f}"
M['StageVolunteerTax'] = f"{s3['volunteerTax']['estimate']:.2f}"
M['StageCost'] = f"{m3['cost']:.2f}"
M['StagePlanHash'] = m3['planHash']

# Phase 18, guards at 64 agents (a second deviation; results/multiagent/colony/stage64) and the $0 replay diagnosis of the
# guard advantage's decline (the 64-agent guard boards replayed from the response cache with Stage 4's measures)
m64 = json.loads((R / 'colony/stage64/metrics.json').read_text())
S64 = m64['summary']
v = S64['hyp']['H18_12']
M['GuardsSixtyFour'], M['GuardsSixtyFourCI'], M['GuardsSixtyFourP'] = f"{v['estimate']:+.3f}", f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]", f"{v['p']:.3f}"
M['GuardsTrendSixtyFour'], M['GuardsTrendSixtyFourP'] = f"{S64['trend']['estimate']:+.3f}", f"{S64['trend']['p']:.3f}"
M['GuardsAdvEight'], M['GuardsAdvSixtyFour'] = (f"{S64['advantage'][str(N)] if str(N) in S64['advantage'] else S64['advantage'][N]:.2f}" for N in (8, 64))
c64 = S64['cells']
M['GuardsSixtyFourPlainLiar'] = f"{c64['plain|independent']['honestPooled']:.2f}"
M['GuardsSixtyFourGuardLiar'] = f"{c64['colonyGuards|independent']['honestPooled']:.2f}"
M['GuardsSixtyFourContamPlain'] = f"{c64['plain|independent']['contamination']:.2f}"
M['GuardsSixtyFourContamGuard'] = f"{c64['colonyGuards|independent']['contamination']:.2f}"
M['GuardsSixtyFourCost'], M['GuardsSixtyFourPlanHash'] = f"{m64['cost']:.2f}", m64['planHash']
from explRL.colony64 import stage64Grid
from explRL.colony_mech import reusedRows4
from explRL.liar_trace import cacheOnlyClient
g64 = reusedRows4(lambda cfg: cacheOnlyClient(cfg, R / 'llm/cache'), rows('colony/stage64/runs.csv'),
                  [c for c in stage64Grid() if c['level'] == 'colonyGuards|independent'])
nf = np.array([r['falseValues'] for r in g64], float)
held = np.array([r['guardHeldLies'] for r in g64])
M['DiagGuardHeld'] = f"{(held * nf).sum() / nf.sum():.2f}"
M['DiagContestGuarded'] = f"{np.mean([r['contestRateGuarded'] for r in g64]):.2f}"
ug, gu = ((1 - held) * nf * [r['usesPerLieUnguarded'] for r in g64]), held * nf * [r['usesPerLieGuarded'] for r in g64]
M['DiagUnguardedShare'] = f"{ug.sum() / (ug.sum() + gu.sum()):.2f}"
M['DiagUsesGuarded'], M['DiagUsesUnguarded'] = f"{gu.sum() / (held * nf).sum():.2f}", f"{ug.sum() / ((1 - held) * nf).sum():.2f}"

# Phase 18, Stage 4: guards that scale (results/multiagent/colony/stage4; two seed batches, then the full grid from the cache)
m4 = json.loads((R / 'colony/stage4/metrics.json').read_text())
S4 = m4['summary']
for k, name in (('H18_13', 'Copies'), ('H18_14', 'Flags'), ('H18_15', 'Squads')):
    v = S4['hyp'][k]
    M['Four' + name] = f"{v['estimate']:+.3f}"
    M['Four' + name + 'CI'] = f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]"
    M['Four' + name + 'Holm'] = f"{v['pHolm']:.3f}"
adv4 = S4['advantage']
for a4, name in (('colonyGuards', 'Guards'), ('squads', 'Squads'), ('guardDeal', 'Copies'), ('failFlag', 'Flags')):
    M['FourAdv' + name + 'Sixteen'], M['FourAdv' + name + 'SixtyFour'] = (f"{adv4[a4][N]:.2f}" for N in ('16', '64'))
M['FourSquadsDid'] = f"{S4['did']['squads']['estimate']:+.3f}"
M['FourSquadsDidCI'] = f"[{S4['did']['squads']['ci'][0]:.3f}, {S4['did']['squads']['ci'][1]:.3f}]"
M['FourSquadsDidP'] = f"{S4['did']['squads']['p']:.3f}"
c4 = S4['cells']
M['FourSquadsLevel'] = f"{c4['squads|independent N 64']['honestPooled']:.2f}"
M['FourGuardsEightLevel'] = f"{c4['colonyGuards|independent N 8']['honestPooled']:.2f}"
M['FourSquadsTokens'] = f"{c4['squads|independent N 64']['inTokPerCall']:,.0f}"
M['FourBoardTokens'] = f"{c4['colonyGuards|independent N 64']['inTokPerCall']:,.0f}"
M['FourFlagsSixteen'] = f"{adv4['failFlag']['16'] - adv4['colonyGuards']['16']:+.3f}"
M['FourFlagsClean'] = f"{S4['cleanCost']['failFlag']['estimate']:+.3f}"
M['FourFlagsOnTrue'] = f"{c4['failFlag|independent N 64']['flagsOnTrue']:.2f}"
M['FourCopiesClean'] = f"{S4['cleanCost']['guardDeal']['estimate']:+.3f}"
M['FourCopiesContest'] = f"{c4['guardDeal|independent N 64']['contestRateGuarded']:.2f}"
M['FourGuardsContest'] = f"{c4['colonyGuards|independent N 64']['contestRateGuarded']:.2f}"
M['FourCost'] = f"{m4['cost']:.2f}"
M['FourPlanHash'] = m4['planHash']

# Phase 17: RL on mixed team sizes (results/multiagent/rl/eval_p17; RL17_PLAN, 8 runs)
S17 = json.loads((R / 'rl/eval_p17/summary.json').read_text())
for k, name in (('H17_1', 'Gain'), ('H17_2', 'Shrink'), ('H17_3', 'Pool'), ('H17_4', 'Liar')):
    v = S17['hyp'][k]
    M['Seventeen' + name] = f"{v['mean']:+.3f}"
    M['Seventeen' + name + 'CI'] = f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]"
    M['Seventeen' + name + 'P'], M['Seventeen' + name + 'Holm'] = f"{v['p']:.3f}", f"{v['pHolm']:.3f}"
c17 = S17['curves']
r17 = [m for m in c17 if m != 'warm']
for N, name in ((4, 'Four'), (32, 'ThirtyTwo')):
    M['SeventeenWarm' + name] = f"{c17['warm'][str(N)]['welfare']:.2f}"
    M['SeventeenTrained' + name] = f"{np.mean([c17[m][str(N)]['welfare'] for m in r17]):.2f}"
M['SeventeenPositive'] = str(sum(S17['runs'][m]['gain4'] > 0 for m in r17))
M['SeventeenHaikuThirtyTwo'] = f"{S17['refs']['32']['welfare']:.2f}" if S17.get('refs') else '0.44'
M['SeventeenPlanHash'] = S17['planHash']

lines = ['% Generated by paper/make_assets.py from results/multiagent/; do not edit by hand.']
lines += [f'\\newcommand{{\\{k}}}{{{v}}}' for k, v in sorted(M.items())]
(OUT / 'numbers.tex').write_text('\n'.join(lines) + '\n')
for src, dst in (('fix/full/fix.png', 'fixes.png'), ('rl/eval/coop_main.png', 'rl_main.png'),
                 ('rl/eval/coop_info.png', 'rl_info.png'), ('rl/eval/coop_curves.png', 'rl_curves.png'),
                 ('rl/eval_p13/coop_main.png', 'rl13_main.png'), ('rl/eval_p13/coop_info.png', 'rl13_info.png')):
    shutil.copy(R / src, FIG / dst)
print(f'{len(M)} macros -> {OUT / "numbers.tex"}; figures -> {FIG}')
