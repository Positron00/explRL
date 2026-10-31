"""Numbers (numbers.tex) and figures for the companion paper, from the saved results in results/multiagent/.
Run from the repo root: `.venv/bin/python paper2/make_assets.py`."""
import json
import shutil
from pathlib import Path

import numpy as np

from explRL.bench_grid import readCSV
from explRL.clue_report import summaries as clueSummaries
from explRL.llm_report import summaries as llmSummaries
from explRL.rl_report import rlSummaries

R, OUT = Path('results/multiagent'), Path('paper2')
FIG = OUT / 'figures'
FIG.mkdir(parents=True, exist_ok=True)
M = {}


def ci(name, v, d=3):
    M[name] = f"{v['mean']:.{d}f}"
    M[name + 'CI'] = f"[{v['ci'][0]:.{d}f}, {v['ci'][1]:.{d}f}]"


# Confirmatory numpy tests (Phases 8-9)
bench, h3 = json.loads((R / 'bench/full/metrics.json').read_text()), json.loads((R / 'safety/h3/metrics.json').read_text())
for k in ('P', 'H1', 'H2'):
    ci('Test' + k.replace('1', 'One').replace('2', 'Two'), bench['confirmatory'][k])
    M['Test' + k.replace('1', 'One').replace('2', 'Two') + 'P'] = f"{bench['confirmatory'][k]['pHolm']:.4f}"
ci('TestHThree', h3['h3']['H3'])
M['TestHThreeP'] = f"{h3['h3']['H3']['pHolm']:.4f}"
M['NumpySeeds'] = str(bench['confirmatory']['P']['n'])

# Do LLM teams follow? Rank agreement and the hypotheses' LLM counterparts
llm = readCSV(R / 'llm/full/runs.csv')
S10 = llmSummaries([r for r in llm if r['runner'] == 'llm'], [r for r in llm if r['runner'] == 'numpy'])
for k, name in (('board', 'Board'), ('forage', 'Forage')):
    M['Rho' + name], (lo, hi) = f"{S10['numpy'][k]['rho']:.2f}", S10['numpy'][k]['ci']
    M['Rho' + name + 'CI'] = f'[{lo:.2f}, {hi:.2f}]'
ben = S10['benefit']
ci('BoardBenefitEight', ben[('board', 'blackboard', 8)], 2)
ci('ForageBenefitEight', ben[('forage', 'blackboard', 8)], 2)
clue = readCSV(R / 'clue/full/runs.csv')
S11 = clueSummaries([r for r in clue if r['runner'] == 'llm'], [r for r in clue if r['study'] == 'clueNumpy'])
M['RhoClue'], (lo, hi) = f"{S11['numpy']['rho']:.2f}", S11['numpy']['ci']
M['RhoClueCI'] = f'[{lo:.2f}, {hi:.2f}]'
ev = readCSV(R / 'rl/eval/runs.csv')
SB = rlSummaries(ev, [r for r in clue if r['runner'] == 'llm'], [r for r in clue if r['study'] == 'clueNumpy'])
ci('LiarWarm', SB['liar']['warm blackboard - messages loss (H3: > 0)'])
ci('LiarCredit', SB['liar']['credit blackboard - messages loss (H3: > 0)'])

# Costs
M['CostPhaseTen'] = f"{json.loads((R / 'llm/full/metrics.json').read_text())['cost']:.2f}"
M['CostPhaseEleven'] = f"{json.loads((R / 'clue/full/metrics.json').read_text())['cost']:.2f}"
M['NumpyWallMinutes'] = f"{bench['wallSeconds'] / 60:.0f}"

# Forecast of RL reward designs
score = json.loads((R / 'forecast/score.json').read_text())
M['RetroAgree'], M['RetroTotal'] = str(score['retrodiction']['agree']), str(score['retrodiction']['total'])
M['ForecastAgree'], M['ForecastTotal'] = str(score['forecast']['agree']), str(score['forecast']['total'])
pred = json.loads((R / 'forecast/predictions.json').read_text())
for k, name in (('individual|sharePerHeld', 'PredIndShare'), ('indpen|sharePerHeld', 'PredIndpenShare'),
                ('indpen|welfare', 'PredIndpenWelfare'), ('credturn|welfare', 'PredCredturnWelfare')):
    M[name] = f"{pred[k]['mean']:+.3f}"
llm13 = score['llm13']
for k, name in (('indpen|sharePerHeld', 'ObsIndpenShare'), ('indpen|welfare', 'ObsIndpenWelfare'),
                ('credturn|welfare', 'ObsCredturnWelfare')):
    M[name] = f"{llm13[k]['mean']:+.3f}"
    M[name + 'CI'] = f"[{llm13[k]['ci'][0]:+.3f}, {llm13[k]['ci'][1]:+.3f}]"
for arm in ('individual', 'team', 'credit'):
    M['RetroAgree' + arm.capitalize()] = str(sum(p == q for k, (p, q) in score['retrodiction']['pairs'].items() if k.startswith(arm + '|')))
# post hoc (specs/multiagent/phase13/forecast.md): a numpy effect smaller than a tenth of the LLM warm start's value counts as 0
warm = {m: np.nanmean([r[m] for r in ev if r['level'] == 'warm|main']) for m in ('welfare', 'sharePerHeld', 'soloShare', 'wrongPerSolve')}
post = lambda part: sum(('0' if abs(pred[k]['mean']) < 0.1 * abs(warm[k.split('|')[1]]) else pred[k]['sign']) == q
                        for k, (_, q) in score[part]['pairs'].items())
M['RetroAgreePostHoc'], M['ForecastAgreePostHoc'] = str(post('retrodiction')), str(post('forecast'))

# Phase 16: penalized runs that still drifted selfish (RL16_PLAN's rule: a run's solo share above 0.5)
r16 = json.loads((R / 'rl/eval_p16/summary.json').read_text())['runs']
pen = [n for n in r16 if n.startswith('indpen')]
M['SixteenPenRuns'], M['SixteenPenDrift'] = str(len(pen)), str(sum(r16[n]['soloShare'] > 0.5 for n in pen))

# Phase 14: the numpy forecast of team-size trends, scored
sc = json.loads((R / 'forecast/scale_score.json').read_text())
M['ScaleAgree'], M['ScaleTotal'] = str(sc['agree']), str(sc['total'])
for k, name in (('pooledShare', 'Pool'), ('honestLoss', 'Loss')):
    M['ScalePred' + name] = f"{sc['predicted'][k]['mean']:+.3f}"
    M['ScaleObs' + name] = f"{sc['observed'][k]['mean']:+.3f}"
    M['ScaleObs' + name + 'CI'] = f"[{sc['observed'][k]['ci'][0]:+.3f}, {sc['observed'][k]['ci'][1]:+.3f}]"

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

# Phase 18: the colony-rule forecast (specs/multiagent/phase18/colony_predictions.json, colony_score.json)
SP = json.loads(Path('specs/multiagent/phase18/colony_predictions.json').read_text())['predictions']
SC = json.loads(Path('specs/multiagent/phase18/colony_score.json').read_text())
M['ColonyRight'], M['ColonyWrong'], M['ColonyNoCall'] = str(SC['right']), str(SC['wrong']), str(SC['noCall'])
M['ColonyCalled'] = str(SC['right'] + SC['wrong'])
M['ColonyPredGuards'] = f"{SP['H18_4']['estimate']:+.3f}"
M['ColonyPredBoard'] = f"{SP['H18_1']['estimate']:+.2f}"
M['ColonyPredTotal'], M['ColonyScored'] = str(len(SP)), str(len(SC['items']))
# what changed with Claude guards: honest agents' means on the Stage 1 liar boards (8 and 16 agents)
r18 = readCSV(R / 'colony/stage1/runs.csv')
for col, name in (('shareShare', 'ShareTurns'), ('contestFalse', 'Contests'), ('confirmFalse', 'Confirms')):
    for arm, who in (('colonyGuards', 'Guards'), ('colony', 'Board')):
        M['Colony' + who + name] = f"{np.nanmean([r[col] for r in r18 if r['level'] == arm + '|independent']):.2f}"

# Phase 18, Stage 4: the design-change forecast (colony4_predictions.json, frozen before the pilot; colony4_score.json)
P4 = json.loads(Path('specs/multiagent/phase18/colony4_predictions.json').read_text())
S4F = json.loads(Path('specs/multiagent/phase18/colony4_score.json').read_text())
O4 = json.loads((R / 'colony/stage4/metrics.json').read_text())['summary']
M['FourRight'], M['FourWrong'], M['FourNoCall'] = str(S4F['right']), str(S4F['wrong']), str(S4F['noCall'])
M['FourScored'] = str(len(S4F['items']))
# Stage 4b: the same designs at 32 agents; its forecast (from the frozen numpy rows) scored on the three primary tests
S4b = json.loads(Path('results/multiagent/colony/stage4b/metrics.json').read_text())['summary']
pred4b = json.loads(Path('specs/multiagent/phase18/colony4b_predictions.json').read_text())['predictions']
sg4 = lambda lo, hi: '+' if lo > 0 else '-' if hi < 0 else '0'
res4b = ['no call' if sg4(*S4b['hyp'][h]['ci']) == '0' else 'right' if sg4(*S4b['hyp'][h]['ci']) == pred4b[h]['sign'] else 'wrong'
         for h in ('H18_16', 'H18_17', 'H18_18')]
M['FourBRight'], M['FourBWrong'], M['FourBNoCall'] = (str(res4b.count(k)) for k in ('right', 'wrong', 'no call'))
M['FourBCalled'] = str(len(res4b) - res4b.count('no call'))
M['FourCalled'] = str(S4F['right'] + S4F['wrong'])
for k, name in (('H18_13', 'Copies'), ('H18_14', 'Flags'), ('H18_15', 'Squads')):
    M['FourPred' + name] = f"{P4['predictions'][k]['estimate']:+.3f}"
    M['FourObs' + name] = f"{O4['hyp'][k]['estimate']:+.3f}"
for a, name in (('guardDeal', 'Copies'), ('failFlag', 'Flags'), ('squads', 'Squads')):
    M['FourPredDid' + name] = f"{P4['predictions']['did_' + a]['estimate']:+.3f}"
    M['FourObsDid' + name] = f"{O4['did'][a]['estimate']:+.3f}"
cv, ad = P4['curves'], O4['advantage']
M['FourNumpySquadsSixteen'], M['FourNumpySquadsSixtyFour'] = f"{cv['squads']['16']:.2f}", f"{cv['squads']['64']:.2f}"
M['FourNumpyGuardsSixteen'], M['FourNumpyGuardsSixtyFour'] = f"{cv['colonyGuards']['16']:.2f}", f"{cv['colonyGuards']['64']:.2f}"
M['FourObsSquadsSixteen'], M['FourObsSquadsSixtyFour'] = f"{ad['squads']['16']:.2f}", f"{ad['squads']['64']:.2f}"
M['FourObsGuardsSixteen'], M['FourObsGuardsSixtyFour'] = f"{ad['colonyGuards']['16']:.2f}", f"{ad['colonyGuards']['64']:.2f}"
M['ColonyPredContam'] = f"{SP['H18_2']['estimate']:+.2f}"
M['ColonyPredTax'] = f"{SP['H18_3']['estimate']:+.3f}"

# Gap fixes (2026-10-31): what the simulated counting board left for guards, a naive baseline for the defence calls,
# the one input taken from an LLM pilot, subsets and costs behind the rankings, and the Haiku tests of H3
scr = json.loads(Path('specs/multiagent/phase18/colony_predictions.json').read_text())['screen']
for lv, name in (('colony|independent', 'Board'), ('colonyGuards|independent', 'Guard')):        # answers built on a lie, 8 and 16 agents
    M['ColonyNumpy' + name + 'Contam'] = f"{np.mean([scr[lv][str(N)]['contamination'] for N in (8, 16)]):.2f}"
    M['Colony' + name + 'Contam'] = f"{np.nanmean([float(r['contamination']) for r in r18 if r['level'] == lv]):.2f}"
ind = [n for n in r16 if n.startswith('individual')]
M['SixteenIndRuns'], M['SixteenDrift'] = str(len(ind)), str(sum(r16[n]['soloShare'] > 0.5 for n in ind))
concl = [v for v in {**SC['items'], **S4F['items']}.values() if v['result'] != 'no call']
obs4b = [sg4(*S4b['hyp'][h]['ci']) for h in ('H18_16', 'H18_17', 'H18_18')]
M['DefenceRight'] = str(sum(v['result'] == 'right' for v in concl) + res4b.count('right'))
M['DefenceCalled'] = str(len(concl) + len(res4b) - res4b.count('no call'))
M['DefenceNaiveRight'] = str(sum(v['observed'] == '+' for v in concl) + sum(o == '+' for o, r in zip(obs4b, res4b) if r != 'no call'))
M['ColonyObsBoard'] = f"{json.loads((R / 'colony/stage1/metrics.json').read_text())['summary']['hyp']['H18_1']['estimate']:+.3f}"
from explRL.llm_grid import SETTINGS
M['BoardSolveRate'] = f"{SETTINGS['solveRate']:.2f}"
M['TraceNumpyContamEight'] = f"{tm(tn, 8, 'contaminated'):.2f}"
S11c = clueSummaries([r for r in clue if r['runner'] == 'llm' and r['channel'] != 'none'],
                     [r for r in clue if r['study'] == 'clueNumpy' and r['channel'] != 'none'])
M['RhoClueChannel'], (lo, hi) = f"{S11c['numpy']['rho']:.2f}", S11c['numpy']['ci']
M['RhoClueChannelCI'] = f'[{lo:.2f}, {hi:.2f}]'
cost = lambda rs, study: sum(float(r['cost']) for r in rs if r['runner'] == 'llm' and r['study'] == study and r.get('cost') not in ('', None))
M['CostPhaseTenMain'], M['CostPhaseElevenMain'] = f"{cost(llm, 'main'):.2f}", f"{cost(clue, 'clue'):.2f}"
M['FourBPredTrendGuards'] = f"{pred4b['trend_colonyGuards']['estimate']:+.3f}"
ci('HaikuLiarBoard', S10['arms']['liar board: blackboard - messages loss (H3 sign: > 0)'])
ci('HaikuLiarForage', S10['arms']['liar forage: blackboard - messages loss (H3 sign: > 0)'])
ci('HaikuLiarClue', S11['liar']['blackboard - messages loss (H3 sign: > 0)'])

lines = ['% Generated by paper2/make_assets.py from results/multiagent/; do not edit by hand.']
lines += [f'\\newcommand{{\\{k}}}{{{v}}}' for k, v in sorted(M.items())]
(OUT / 'numbers.tex').write_text('\n'.join(lines) + '\n')
for src, dst in (('report/fig_scaling.png', 'scaling.png'), ('report/fig_robustness.png', 'robustness.png')):
    if (R / src).exists():
        shutil.copy(R / src, FIG / dst)
print(f'{len(M)} macros -> {OUT / "numbers.tex"}; figures -> {FIG}')
