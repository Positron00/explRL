"""Numbers (numbers.tex) and figures for the companion paper, from the saved results in results/multiagent/.
Run from the repo root: `.venv/bin/python paper2/make_assets.py`."""
import json
import shutil
from pathlib import Path

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

lines = ['% Generated by paper2/make_assets.py from results/multiagent/; do not edit by hand.']
lines += [f'\\newcommand{{\\{k}}}{{{v}}}' for k, v in sorted(M.items())]
(OUT / 'numbers.tex').write_text('\n'.join(lines) + '\n')
for src, dst in (('report/scaling.png', 'scaling.png'), ('report/robustness.png', 'robustness.png')):
    if (R / src).exists():
        shutil.copy(R / src, FIG / dst)
print(f'{len(M)} macros -> {OUT / "numbers.tex"}; figures -> {FIG}')
