"""Build the paper's numbers (numbers.tex, one LaTeX macro per reported value) and figures from the saved results, so every
number in the text is traceable to `results/multiagent/`. Run from the repo root: `.venv/bin/python paper/make_assets.py`."""
import json
import shutil
from pathlib import Path

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
best = max(S13['main'], key=lambda m: S13['main'][m]['welfare']['mean'] if m != 'warm' else -1)
M['BestWelfare'] = f"{S13['main'][best]['welfare']['mean']:.2f}"
M['BestGainPct'] = f"{100 * (S13['main'][best]['welfare']['mean'] / S13['main']['warm']['welfare']['mean'] - 1):.0f}"
fs = json.load(open(R / 'forecast/score.json'))
M['ForecastAgree'], M['ForecastTotal'] = str(fs['forecast']['agree']), str(fs['forecast']['total'])
M['RetroAgree'], M['RetroTotal'] = str(fs['retrodiction']['agree']), str(fs['retrodiction']['total'])

lines = ['% Generated by paper/make_assets.py from results/multiagent/; do not edit by hand.']
lines += [f'\\newcommand{{\\{k}}}{{{v}}}' for k, v in sorted(M.items())]
(OUT / 'numbers.tex').write_text('\n'.join(lines) + '\n')
for src, dst in (('fix/full/fix.png', 'fixes.png'), ('rl/eval/coop_main.png', 'rl_main.png'),
                 ('rl/eval/coop_info.png', 'rl_info.png'), ('rl/eval/coop_curves.png', 'rl_curves.png'),
                 ('rl/eval_p13/coop_main.png', 'rl13_main.png'), ('rl/eval_p13/coop_info.png', 'rl13_info.png')):
    shutil.copy(R / src, FIG / dst)
print(f'{len(M)} macros -> {OUT / "numbers.tex"}; figures -> {FIG}')
