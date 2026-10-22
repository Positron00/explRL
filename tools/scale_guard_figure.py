"""Summary figure of Phase 18's guards against team size: each arm's advantage over the plain board (honest pooled share,
independent liars, a quarter of the agents) at 8, 16, 32 and 64 agents for today's guards (Stage 1, 32 and 64 agents) and
at 16 and 64 for Stage 4's design changes (squads of 8, failure flags, guard copies), 95% bootstrap intervals over seeds of
the paired differences. Reads the saved results only.

  python tools/scale_guard_figure.py <repo>   -> results/multiagent/report/guards_scale.png
"""
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt

ARMS = (('colonyGuards', 'guards (one board)', '#1f6391', 'o', '-'), ('squads', 'squads of 8 with guards', '#2a9d8f', 's', '-'),
        ('failFlag', 'guards + failure flags', '#c9a227', '^', '--'), ('guardDeal', 'guards + a copy of every clue', '#b03a2e', 'D', '--'))


def boot(v, n=2000, seed=0):
    v = np.array(v, float)
    m = v[np.random.default_rng(seed).integers(0, len(v), (n, len(v)))].mean(1)
    return v.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)


def main(repo):
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    from explRL.colony_report import pairs
    R = Path(repo) / 'results/multiagent'
    rows = sum((readCSV(R / f'colony/{d}/runs.csv') for d in ('stage1', 'stage32', 'stage64', 'stage4')), [])
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=200)
    for k, (arm, label, col, mk, ls) in enumerate(ARMS):
        pts = []
        for N in (8, 16, 32, 64):
            d = list(pairs(rows, arm, 'honestPooled', sizes=[N]).values())
            if d:
                pts.append((N, *boot(d)))
        if not pts:
            continue
        N, m, lo, hi = map(np.array, zip(*pts))
        x = np.log2(N) + (k - 1.5) * 0.04
        ax.errorbar(x, m, yerr=[m - lo, hi - m], color=col, marker=mk, ls=ls, lw=1.8, ms=6, capsize=3, label=label)
        ax.annotate(f'{m[-1]:.2f}', (x[-1], m[-1]), textcoords='offset points', xytext=(8, -3), fontsize=8, color=col)
    ax.set_xticks(np.log2([8, 16, 32, 64]), ['8', '16', '32', '64'])
    ax.set_xlabel('agents (a quarter of them scripted liars)')
    ax.set_ylabel('advantage over the plain board\n(honest pooled share)')
    ax.axhline(0, color='#9aa3ad', lw=0.8)
    ax.set_ylim(0, 0.4)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc='upper left')
    ax.set_title('Guards lose ground as teams grow; squads of 8 with their own guards gain it', fontsize=10)
    out = R / 'report/guards_scale.png'
    fig.tight_layout()
    fig.savefig(out)
    print(out)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
