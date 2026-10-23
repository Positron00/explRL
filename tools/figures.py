"""Publication figures for the summary page, both preprints and the highlights notebook, from the saved results only (no rerun).

One convention throughout: points and bars are means, error bars one standard error of the mean (SEM) over the
independent unit (board seeds for Claude and numpy teams; held-out boards for one trained model; for ratio measures
such as the share of a gap closed, the bootstrap standard error over seeds); an asterisk marks p < 0.05 by a two-sided
paired sign-flip test against the stated reference (exact up to 15 pairs, seeded random flips beyond; an exact two-sample
permutation test between team sizes), uncorrected for multiple comparisons. The preprints report the pre-registered
tests, with Holm correction, in the text.

The team and training figures are drawn by the package (explRL.figs_team, explRL.figs_rl) from compact per-seed data, which
this script extracts from results/multiagent/ and saves to data/highlights/highlights.json (committed, so the highlights
notebook redraws them without the raw results). The summary page uses the wide figures; the preprints use the fig_* ones,
drawn at the printed width of a NeurIPS page (5.5 in) with the convention in their captions instead of a footnote.

  python tools/figures.py <repo>   -> data/highlights/highlights.json,
                                      results/multiagent/report/{guards_scale,guards,trust_scale,incentives}.png
                                      and results/multiagent/report/fig_{guards_scale,guards,trust_scale,fixes,rl_main,scaling,robustness}.png
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

FIXNAME = dict(request='request board', table='clue table', evidence='share first', record='track record', verify='check action',
               warn='warning', factsFirst='facts first', dissent='speak up')
FIXPART = dict(A1='Pooling: clue board', A2='One liar in four: clue board', A3='Hidden-profile vote')
CH = ('none', 'messages', 'blackboard', 'hierarchical')
CHCOL = dict(none='#9aa3ad', messages='#c9a227', blackboard='#1f6391', hierarchical='#7a5c99')


def bySeed(rows, level, metric, N):
    return {int(r['seed']): float(r[metric]) for r in rows if r['level'] == level and int(float(r['N'])) == N and np.isfinite(float(r[metric]))}


def fixLabel(part, key):
    "A readable row label for a fix arm: 'request|4' -> 'request board (4 agents)', 'table|lone' -> 'fact table (lone dissenter)'."
    arm, _, v = key.partition('|')
    name = 'fact table' if (part, arm) == ('A3', 'table') else FIXNAME.get(arm, arm)
    return name + (f' ({v} agents)' if v.isdigit() else ' (lone dissenter)' if v == 'lone' else f' ({v})' if v else '')


# ---------- compact data for the package's figures ----------

def guardsScaleData(R):
    "Per-seed advantage over the plain board (honest pooled share, independent liars), per arm and team size."
    from explRL.bench_grid import readCSV
    rows = sum((readCSV(R / f'colony/{d}/runs.csv') for d in ('stage1', 'stage32', 'stage64', 'stage4')), [])
    out = {}
    for arm in ('colonyGuards', 'squads', 'failFlag', 'guardDeal'):
        for N in (8, 16, 32, 64):
            a, p = bySeed(rows, f'{arm}|independent', 'honestPooled', N), bySeed(rows, 'plain|independent', 'honestPooled', N)
            if d := [a[s] - p[s] for s in sorted(a) if s in p]:
                out.setdefault(arm, {})[str(N)] = d
    return out


def guardsData(R):
    "Per-seed honest pooled share and contamination per defence and team size (Stage 1 and the 32-agent run)."
    from explRL.bench_grid import readCSV
    rows = readCSV(R / 'colony/stage1/runs.csv') + readCSV(R / 'colony/stage32/runs.csv')
    arms = ('plain', 'confirm', 'colony', 'colonyGuards', 'record')
    return {k: {arm: {str(N): {str(s): v for s, v in a.items()} for N in (8, 16, 32) if (a := bySeed(rows, f'{arm}|independent', k, N))}
                for arm in arms} for k in ('honestPooled', 'contamination')}


def trustData(R):
    "The track record's and the request board's summaries by team size, and per-seed contamination per runner."
    from explRL.bench_grid import readCSV
    from explRL.scale_report import scaleSummaries, trustSummaries
    ST = trustSummaries(readCSV(R / 'fix/full/runs.csv'), readCSV(R / 'trust/full/runs.csv'))
    SS = scaleSummaries(readCSV(R / 'scale/full/runs.csv'))
    acc = readCSV(R / 'liar/full/accounting.csv')
    row = lambda N, v: [int(N), v['gap'], v['se'], v['p']]
    return dict(record=[row(4, ST['arms']['record'])] + [row(v['N'], v) for v in SS['record'].values()],
                request=[row(v['N'], v) for v in SS['request'].values()],
                contaminated={who: {str(N): [float(r['contaminated']) for r in acc if r['runner'] == who and int(float(r['N'])) == N]
                                    for N in (8, 16, 32)} for who in ('haiku', 'numpy')})


def incentivesData(R):
    "Every trained 3B team on the 15 held-out boards (per-board metrics), the warm start first, and the reference teams."
    from explRL.bench_grid import readCSV
    from explRL.figs_rl import PANELS
    rl = R / 'rl'
    data = {d: readCSV(rl / d / 'runs.csv') for d in ('eval', 'eval_p13')}
    data['eval_p16'] = readCSV(rl / 'colab' / 'eval_p16' / 'runs.csv')
    runs = [('imitation (warm start)', 'eval', 'warm', '#555555'), ('individual reward (seed 1)', 'eval', 'individual', '#c0392b')]
    runs += [(f'individual reward (seed {s})', 'eval_p16', f'individual_s{s}', '#c0392b') for s in (2, 3, 4)]
    runs += [('team reward', 'eval', 'team', '#999999')]
    runs += [(f'individual, loophole priced (seed {s})', 'eval_p13', f'indpen_s{s}', '#e67e22') for s in (1, 2)]
    runs += [(f'individual, loophole priced (seed {s})', 'eval_p16', f'indpen_s{s}', '#e67e22') for s in (3, 4, 5)]
    runs += [(f'credit reward (seed {s})', 'eval_p13', f'credit_s{s}', '#2471a3') for s in (1, 2)]
    runs += [(f'credit, per-turn (seed {s})', 'eval_p13', f'credturn_s{s}', '#5dade2') for s in (1, 2)]
    board = lambda d, lv, m: {str(int(r['seed'])): float(r[m]) for r in data[d] if r['level'] == f'{lv}|main' and np.isfinite(float(r[m]))}
    clue = readCSV(R / 'clue/full/runs.csv')
    ref = lambda study: float(np.mean([float(r['welfare']) for r in clue if r['study'] == study and r['channel'] == 'blackboard'
                                       and int(float(r['N'])) == 4 and 900 <= int(float(r['seed'])) <= 904]))
    return dict(runs=[[lab, col, {m: board(d, lv, m) for m, _ in PANELS}] for lab, d, lv, col in runs],
                refs=dict(welfare=[[ref('clue'), 'Claude Haiku 5.5', '--'], [ref('clueNumpy'), 'rule agents', ':']]))


def fixesData(R):
    "The Phase 13 fixes at four agents, one row per arm (share of the gap closed or of the liar's damage recovered), headed by part."
    from explRL.bench_grid import readCSV
    from explRL.fix_report import fixLogMetrics, fixSummaries
    logs = [json.loads(x) for x in open(R / 'fix/full/turns.jsonl')]
    S = fixSummaries(readCSV(R / 'fix/full/runs.csv'), readCSV(R / 'clue/full/runs.csv'), fixLogMetrics(logs), readCSV(R / 'profile/full/runs.csv'))
    rows = []
    for part in ('A1', 'A2', 'A3'):
        if S[part]:
            rows += [dict(label=FIXPART[part], kind=None)]
            rows += [dict(label=fixLabel(part, k), kind=v['kind'], gap=v['gap'], se=v['se'], p=v['p']) for k, v in S[part].items()]
    return rows


def highlights(R):
    return dict(note='Compact per-seed data behind the published figures, extracted from results/multiagent/ by tools/figures.py.',
                guardsScale=guardsScaleData(R), guards=guardsData(R), trust=trustData(R), incentives=incentivesData(R), fixes=fixesData(R))


# ---------- figure entry points (the wrappers in tools/ call these) ----------

def _draw(f, data, out, name, paper=False):
    f(data, out / name, paper=paper)
    print(out / name)


def guardsScale(R, out, paper=False):
    from explRL.figs_team import guardsScale as draw
    _draw(draw, guardsScaleData(R), out, 'fig_guards_scale.png' if paper else 'guards_scale.png', paper)


def guards(R, out, paper=False):
    from explRL.figs_team import guards as draw
    _draw(draw, guardsData(R), out, 'fig_guards.png' if paper else 'guards.png', paper)


def trustScale(R, out, paper=False):
    from explRL.figs_team import trustScale as draw
    _draw(draw, trustData(R), out, 'fig_trust_scale.png' if paper else 'trust_scale.png', paper)


def incentives(R, out):
    from explRL.figs_rl import incentives as draw
    _draw(draw, incentivesData(R), out, 'incentives.png')


def fixes(R, out):
    from explRL.figs_rl import fixes as draw
    _draw(draw, fixesData(R), out, 'fig_fixes.png', paper=True)


# ---------- preprint-only figures, drawn from the raw results ----------

def printed(f):
    "Draw a preprint-only figure with the preprints' font sizes."
    def g(R, out):
        from explRL.figs_team import PAPER
        with plt.rc_context(PAPER):
            return f(R, out)
    g.__name__, g.__doc__ = f.__name__, f.__doc__
    return g


@printed
def rlMain(R, out):
    "Welfare per agent-turn on the 15 held-out boards for the warm start and one run per reward (Phase 12)."
    from explRL.bench_grid import readCSV
    from explRL.figs_team import W, save, sem, signP, star
    ev = readCSV(R / 'rl/eval/runs.csv')
    clue = readCSV(R / 'clue/full/runs.csv')
    board = lambda lv: {int(r['seed']): float(r['welfare']) for r in ev if r['level'] == f'{lv}|main'}
    ref = lambda study: float(np.mean([float(r['welfare']) for r in clue if r['study'] == study and r['channel'] == 'blackboard'
                                       and int(float(r['N'])) == 4 and 900 <= int(float(r['seed'])) <= 904]))
    models = (('untrained', 'untrained'), ('warm', 'warm start (imitation)'), ('individual', 'individual reward'),
              ('team', 'team reward'), ('credit', 'credit reward'))
    warm = board('warm')
    fig, ax = plt.subplots(figsize=(W, 2.1))
    for y, (lv, lab) in enumerate(models):
        v = board(lv)
        x = list(v.values())
        mu, e = float(np.mean(x)), sem(x)
        ax.errorbar([mu], [y], xerr=[e], fmt='o', color='tab:blue')
        if lv != 'warm':
            star(ax, mu + e, y, signP([v[s] - warm[s] for s in sorted(v) if s in warm]), horizontal=True, size=9)
    for x, lab, ls in ((ref('clue'), 'Claude Haiku 5.5', '--'), (ref('clueNumpy'), 'rule agents', ':')):
        ax.axvline(x, color='k', ls=ls, lw=1, alpha=0.7, label=f'{lab} ({x:.2f})')
    ax.set_yticks(range(len(models)), [m[1] for m in models])
    ax.invert_yaxis()
    ax.set(xlabel='welfare per agent-turn (15 held-out boards)')
    ax.legend(loc='lower right', title='same boards', title_fontsize=6.5)
    fig.tight_layout()
    save(fig, out / 'fig_rl_main.png')
    print(out / 'fig_rl_main.png')


@printed
def scaling(R, out):
    "Phase 8: welfare per agent-second against team size per channel, fixed compute and fixed world time (30 seeds)."
    from explRL.bench_grid import readCSV
    from explRL.figs_team import W, save, sem, signP, star
    rows = [r for r in readCSV(R / 'bench/full/runs.csv') if r['study'] == 'main']
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.5), sharey=True)
    Ns = sorted({int(r['N']) for r in rows})
    for ax, b in zip(axs, ('compute', 'time')):
        for k, ch in enumerate(CH):
            val = lambda c, N: {int(r['seed']): float(r['perAgentSecond']) for r in rows if r['channel'] == c and r['budget'] == b and int(r['N']) == N}
            pts = [(N, val(ch, N)) for N in Ns if val(ch, N)]
            y, e = np.array([np.mean(list(v.values())) for _, v in pts]), np.array([sem(list(v.values())) for _, v in pts])
            x = [N * 2 ** ((k - 1.5) * 0.07) for N, _ in pts]          # dodged so overlapping points and asterisks stay apart
            ax.errorbar(x, y, yerr=e, label=ch, color=CHCOL[ch], marker='o', ms=3)
            if ch != 'none':
                for xi, (N, v), yi, ei in zip(x, pts, y, e):
                    base = val('none', N)
                    star(ax, xi, yi + ei, signP([v[s] - base[s] for s in sorted(v) if s in base]), color=CHCOL[ch], size=7)
        ax.set(xscale='log', xlabel='team size N', title=f'fixed {"compute (N x T constant)" if b == "compute" else "world time"}')
        ax.set_xticks(Ns, [str(N) for N in Ns])
        ax.minorticks_off()
    axs[0].set_ylabel('welfare per agent-second')
    axs[0].legend(frameon=False)
    fig.tight_layout()
    save(fig, out / 'fig_scaling.png')
    print(out / 'fig_scaling.png')


@printed
def robustness(R, out):
    "Phase 9: the honest agents' relative welfare loss against the share of liars, per channel, at 16 and 64 agents."
    from explRL.bench_grid import readCSV
    from explRL.figs_team import W, save, sem, signP, star
    from explRL.safety_runs import lossRows
    loss = [r for r in lossRows(readCSV(R / 'safety/full/runs.csv')) if r['study'] == 'attack' and r['kind'] == 'liar']
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.5), sharey=True)
    for ax, N in zip(axs, (16, 64)):
        for k, ch in enumerate(CH):
            nb = sorted({int(r['nBad']) for r in loss if r['channel'] == ch and int(r['N']) == N})
            pts = [(n / N, [float(r['loss']) for r in loss if r['channel'] == ch and int(r['N']) == N and int(r['nBad']) == n]) for n in nb]
            pts = [(x, [v for v in vs if np.isfinite(v)]) for x, vs in pts]
            if not pts:
                continue
            xs = np.array([0.0] + [x for x, _ in pts]) + (k - 1.5) * 0.004     # dodged so overlapping asterisks stay apart
            y = np.array([0.0] + [np.mean(v) for _, v in pts])
            e = np.array([0.0] + [sem(v) for _, v in pts])
            ax.errorbar(xs, y, yerr=e, label=ch, color=CHCOL[ch], marker='o', ms=3)
            for x, (_, v), yi, ei in zip(xs[1:], pts, y[1:], e[1:]):
                star(ax, x, yi + ei, signP(v), color=CHCOL[ch], size=7)
        ax.set(xlabel='share of liars in the team', title=f'N = {N}', ylim=(-0.06, 0.6))
        ax.axhline(0, color='k', lw=0.5)
    axs[0].set_ylabel("honest agents' welfare loss (share)")
    axs[0].legend(frameon=False)
    fig.tight_layout()
    save(fig, out / 'fig_robustness.png')
    print(out / 'fig_robustness.png')


def main(repo):
    sys.path.insert(0, str(repo))
    from explRL.figs_rl import fixes as drawFixes, incentives as drawIncentives
    from explRL.figs_team import guards as drawGuards, guardsScale as drawScale, trustScale as drawTrust
    R = Path(repo) / 'results/multiagent'
    out = R / 'report'
    H = highlights(R)
    path = Path(repo) / 'data/highlights/highlights.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(H, indent=1) + '\n')
    print(path)
    for draw, key, name in ((drawScale, 'guardsScale', 'guards_scale'), (drawGuards, 'guards', 'guards'), (drawTrust, 'trust', 'trust_scale')):
        _draw(draw, H[key], out, f'{name}.png')
        _draw(draw, H[key], out, f'fig_{name}.png', paper=True)
    _draw(drawIncentives, H['incentives'], out, 'incentives.png')
    _draw(drawFixes, H['fixes'], out, 'fig_fixes.png', paper=True)
    for f in (rlMain, scaling, robustness):
        f(R, out)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
