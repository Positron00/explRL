"""Build the bridges preprint's numbers (numbers.tex, one LaTeX macro per reported value) and its figure from the saved results,
so every number in the text is traceable to `results/multiagent/colony/` (C1, C1b, C1c, C1d) and `results/multiagent/b3quick/`
(B3's scores). Run from the repo root: `.venv/bin/python paper_bridges/make_assets.py`. C1d's macros are written only once its
summary exists; until then `\\ifCOneD` is false and the text marks the run as pending."""
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from explRL.figs_team import ALPHA, PAPER, W, save, sem, signP, star

R, OUT = Path('results/multiagent'), Path('paper_bridges')
C = R / 'colony'
FIG = OUT / 'figures'
FIG.mkdir(parents=True, exist_ok=True)
M, conds = {}, {}


def summary(d):
    S = json.loads((C / d / 'summary.json').read_text())
    return S.get('summary', S), S


def num(name, v, d=3, signed=False):
    M[name] = f'{v:+.{d}f}' if signed else f'{v:.{d}f}'


def test(name, t, d=3, signed=True):
    "\\name (estimate), \\nameCI ([lo, hi]) and \\nameP (p) from a {'estimate', 'ci', 'p'} test."
    num(name, t['estimate'], d, signed)
    M[name + 'CI'] = f"[{t['ci'][0]:.{d}f}, {t['ci'][1]:.{d}f}]"
    if 'p' in t:
        M[name + 'P'] = f"{t['p']:.3f}"


def money(name, v):
    M[name] = f'{v:.2f}'


# ---- C1 (Phase 20)
S1, _ = summary('c1')
g = S1['gate']
test('GateOneI', g['i']); test('GateOneII', g['ii']); test('GateOneLead', g['ii']['lead'])
num('GateOneBar', g['ii']['bar']); test('GateOneIWelfare', g['welfareHonest']['i'])
h3, h4, h5, h7, h8 = (S1['hyp'][k] for k in ('H20_3', 'H20_4', 'H20_5', 'H20_7', 'H20_8'))
test('CouplingCost', h3['couplingCost'], signed=False); test('BridgeGain', h3['bridgeGain'])
num('WinBack', 100 * h3['winBack'], 0); M['WinBackCI'] = f"[{100 * h3['winBackCi'][0]:.0f}, {100 * h3['winBackCi'][1]:.0f}]"
test('SecondBridge', h4['secondBridge']); test('GuardBridgeFalseRelay', h5, signed=False); test('GuardBridgePooled', h5['pooled'])
num('CrossBridgeOne', h7['perArm']['bridge1'][0]); num('CrossBridgeGuard', h7['perArm']['bridgeGuard'][0])
test('CleanCoupled', h8['contrasts']['coupled - squads']['honestPooled'])
test('CleanBridgeOne', h8['contrasts']['bridge1 - squads']['honestPooled'])
col = S1['arms']['bridge1']['columns']
num('RelayRateOne', 100 * col['bridgeRelays'] / col['bridgeTurns'], 1)
for a, name in (('squads', 'Squads'), ('colonyGuards', 'OneBoard'), ('coupled', 'Coupled'), ('bridge1', 'BridgeOne')):
    num(f'Pooled{name}', S1['arms'][a]['honestPooled'][0])
m1 = json.loads((C / 'c1' / 'metrics.json').read_text())

# ---- C1b (Phase 23)
Sb, _ = summary('c1bmain')
g = Sb['gate']
test('GateBI', g['i']); test('GateBII', g['ii']); num('GateBIIUpper', g['ii']['upper'])
H = Sb['hyp']
num('WinBackFix', 100 * H['H23_3']['winBack'], 0); test('FilterGain', H['H23_4'])
test('RoleEffect', H['H23_5']['role']); test('EvidenceEffect', H['H23_5']['evidence']); test('Interaction', H['H23_5']['interaction'])
test('FixMinusWindow', H['H23_6']['bridgeFix - mirrorWindow'])
for a, name in (('relayEvid', 'RelayEvid'), ('bridgeRole', 'BridgeRole'), ('bridgeFix', 'BridgeFix')):
    c = Sb['arms'][a]['columns']
    num(f'RelayRate{name}', 100 * c['bridgeRelays'] / c['bridgeTurns'], 1)
num('ContamWindowB', Sb['arms']['mirrorWindow']['contamination'][0]); num('ContamBridgeOneB', Sb['arms']['bridge1']['contamination'][0])

# ---- C1c (Phase 24)
Sc, Sc_meta = summary('c1c')
g = Sc['gate']
test('GateCI', g['i']); test('GateCII', g['ii']); num('GateCIIUpper', g['ii']['upper']); test('GateCIWelfare', g['welfareHonest'])
for a, name in (('bridge1', 'One'), ('bridgeRole', 'Role')):
    A = Sc['arms'][a]
    num(f'CRelay{name}', 100 * A['relaysPerBridgeTurn'][0], 1); num(f'CCross{name}', A['crossContamination'][0])
num('CArrivalRole', 100 * Sc['arms']['bridgeRole']['arrivalConfirmed'][0], 0)

# ---- costs (each run's metrics.json; C1b's two batches and the pilots as the plans record them)
from explRL.relay_plan import C1B_PLAN
from explRL.bridge_plan import C1_PLAN
money('CostOne', m1['cost'] + C1_PLAN['projection']['pilotCost'])
money('CostB', sum(json.loads((C / d / 'metrics.json').read_text())['cost'] for d in ('c1bmain1', 'c1bmain2')) + C1B_PLAN['projection']['pilotCost'])
money('CostC', Sc_meta['cost'])

# ---- B3's forecast of C1 (Phase 22) and the hand-recorded calls of C1b and C1c
B = json.loads((R / 'b3quick' / 'c1_score.json').read_text())['all']
for k, name in (('fitted', 'Fitted'), ('unfitted', 'Unfitted'), ('naive', 'Naive')):
    M[f'BThree{name}Right'], M[f'BThree{name}Called'] = str(B[k]['right']), str(B[k]['right'] + B[k]['wrong'])
Sb_calls = json.loads((C / 'c1bmain' / 'calls.json').read_text()) if (C / 'c1bmain' / 'calls.json').exists() else None

# ---- C1d (Phase 25), when it has run
D = C / 'c1d' / 'summary.json'
conds['COneD'] = D.exists()
if D.exists():
    Sd, Sd_meta = summary('c1d')
    g = Sd['gate']
    test('GateDI', g['i']); test('GateDII', g['ii']); num('GateDIIUpper', g['ii']['upper']); test('GateDIWelfare', g['welfareHonest'])
    test('DClean', Sd['clean']['honestPooled']); test('DCleanWelfare', Sd['clean']['welfareHonest'])
    M['GateDVerdict'] = g['verdict']; M['DCleanSupported'] = 'supported' if Sd['clean']['supported'] else 'not supported'
    money('CostD', Sd_meta['cost'])
    Ad = Sd['arms']['independent']
    for name, arm in (('Window', 'mirrorWindow'), ('One', 'bridge1')):
        for k, m in (('Cont', 'contamination'), ('Coupled', 'coupledContamination'), ('Cross', 'crossContamination')):
            num(f'D{k}{name}', Ad[arm][m][0])
    # the answer mix (runs.csv): coupled subtasks solved per board and honest pooled share on coupled subtasks
    import csv, statistics
    Rd = list(csv.DictReader(open(C / 'c1d' / 'runs.csv')))
    for f, fn in (('independent', 'Liars'), ('clean', 'Clean')):
        for name, arm in (('Window', 'mirrorWindow'), ('One', 'bridge1')):
            rs = [r for r in Rd if r['level'] == f'{arm}|{f}']
            M[f'DCoupledSolved{fn}{name}'] = f"{statistics.mean(float(r['coupledSolved']) for r in rs):.0f}"
            if f == 'independent': num(f'DPooledCoupled{name}', statistics.mean(float(r['honestPooledCoupled']) for r in rs))


# ---- the figure: per-seed rows
def load(*paths):
    out = {}
    for p in paths:
        if (C / p).exists():
            for r in csv.DictReader(open(C / p)):
                if int(float(r['N'])) == 64:
                    out.setdefault((r['level'], int(float(r['seed']))), float(r['honestPooled']))
    return out


V = load('c1/runs.csv', 'c1/reused.csv', 'c1bmain/runs.csv', 'c1c/runs.csv', 'c1d/runs.csv')
S5 = range(1800, 1805)
ARMS = (('squads', 'squads,\nuncoupled'), ('coupled', 'coupled'), ('bridge1', 'one\nbridge'), ('bridge2', 'two\nbridges'),
        ('bridgeGuard', 'guard\nbridge'), ('relayEvid', 'evidence'), ('bridgeRole', 'role'), ('bridgeFix', 'both'),
        ('mirrorWindow', 'mirror\nwindow'))
LIAR, CLEAN = '#1f6391', '#c9a227'


def vals(arm, fault, seeds):
    return [V[(f'{arm}|{fault}', s)] for s in seeds if (f'{arm}|{fault}', s) in V]


def diffs(arm, fault, seeds):
    return [V[(f'{arm}|{fault}', s)] - V[(f'bridge1|{fault}', s)] for s in seeds
            if (f'{arm}|{fault}', s) in V and (f'bridge1|{fault}', s) in V]


plt.rcParams.update(PAPER)
fig, (a, b) = plt.subplots(2, 1, figsize=(W, 4.3), gridspec_kw=dict(height_ratios=[1.25, 1]))
for k, (arm, _) in enumerate(ARMS):
    for fault, colr, dx, mk in (('independent', LIAR, -0.13, 'o'), ('clean', CLEAN, 0.13, 's')):
        v = vals(arm, fault, S5)
        if v:
            a.errorbar(k + dx, np.mean(v), yerr=sem(v), color=colr, marker=mk, ms=3.5, capsize=1.5, lw=1,
                       label=('with liars' if fault == 'independent' else 'no liars') if arm == 'squads' else None)
a.set_xticks(range(len(ARMS)), [l for _, l in ARMS], fontsize=6)
a.set(ylabel='honest pooled share', ylim=(0, 0.4))
a.axvspan(0.5, 4.5, color='#eef1f4', zorder=0, lw=0); a.axvspan(4.5, 8.5, color='#f7f4ea', zorder=0, lw=0)
a.text(2.5, 0.385, 'C1', ha='center', va='top', fontsize=6.5, color='#566372'); a.text(6.5, 0.385, 'C1b', ha='center', va='top', fontsize=6.5, color='#566372')
a.spines[['top', 'right']].set_visible(False); a.legend(frameon=False, loc='lower left', fontsize=6)
a.set_title('a  64 agents in squads of 8, seeds 1800-1804', loc='left', fontsize=7.5)
ROWS = [('dedicated bridge, C1b', diffs('bridgeRole', 'independent', S5), LIAR, 'o'),
        ('dedicated bridge, C1c', diffs('bridgeRole', 'independent', range(1810, 1818)), LIAR, 'o'),
        ('mirror window, C1b', diffs('mirrorWindow', 'independent', S5), LIAR, 'o'),
        ('mirror window, C1d', diffs('mirrorWindow', 'independent', range(1820, 1828)), LIAR, 'o'),
        ('window, no liars, C1b', diffs('mirrorWindow', 'clean', S5), CLEAN, 's'),
        ('window, no liars, C1d', diffs('mirrorWindow', 'clean', range(1820, 1828)), CLEAN, 's')]
labels = []
for k, (lab, d, colr, mk) in enumerate(ROWS):
    y = len(ROWS) - 1 - k
    labels.append((y, lab + ('' if d else ': pending')))
    if d:
        b.scatter(d, [y + 0.18] * len(d), s=4, color=colr, alpha=0.45, lw=0)
        b.errorbar(np.mean(d), y, xerr=sem(d), color=colr, marker=mk, ms=3.5, capsize=1.5, lw=1)
        if signP(d) < ALPHA:   # figs_team.star's offset suits size 12; at size 8 it lands on the axis
            b.annotate('*', (np.mean(d) + sem(d), y), xytext=(3, -2.5), textcoords='offset points', fontsize=8, color=colr, va='center')
b.set_yticks([y for y, _ in labels], [l for _, l in labels], fontsize=6.5)
b.axvline(0, color='#9aa3ad', lw=0.8)
b.set(xlabel='minus one bridge, paired on seed (dots: seeds)')
b.spines[['top', 'right', 'left']].set_visible(False); b.tick_params(axis='y', length=0)
b.set_title('b  confirmations', loc='left', fontsize=7.5)
fig.tight_layout()
save(fig, FIG / 'bridges.png')

lines = ['% Generated by paper_bridges/make_assets.py from results/multiagent/: do not edit.']
lines += [f'\\newif\\if{k}\\{k}{"true" if v else "false"}' for k, v in conds.items()]
lines += [f'\\newcommand{{\\{k}}}{{{v}}}' for k, v in sorted(M.items())]
(OUT / 'numbers.tex').write_text('\n'.join(lines) + '\n')
print(f'{len(M)} macros; C1d {"in" if conds["COneD"] else "pending"}; figure {FIG / "bridges.png"}')
