"""Summary figure of Phase 18 Stage 1 (colony rules and guards, Claude Haiku 5.5, a quarter of the agents liars): honest
pooled share with liars per arm at 8, 16 and 32 agents (left; at 32 only the plain board and guards ran, a declared deviation) and the share of honest answers built on a lie (right), 95%
bootstrap intervals over seeds. Reads the saved results only.

  python tools/guard_figure.py <repo>   -> results/multiagent/report/guards.png
"""
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt

ARMS = (('plain', 'plain board', '#9aa3ad'), ('confirm', 'instruction only', '#c9a227'), ('colony', 'agreement counts', '#5b8fb9'),
        ('colonyGuards', 'counts + guards', '#1f6391'), ('record', 'oracle track record', '#7a5c99'))


def boot(v, n=2000, seed=0):
    v = np.array([x for x in v if np.isfinite(x)], float)
    m = v[np.random.default_rng(seed).integers(0, len(v), (n, len(v)))].mean(1)
    return v.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)


def main(repo):
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    R = Path(repo) / 'results/multiagent'
    rows = readCSV(R / 'colony/stage1/runs.csv')
    if (R / 'colony/stage32/runs.csv').exists():
        rows += readCSV(R / 'colony/stage32/runs.csv')
    val = lambda arm, N, k: [float(r[k]) for r in rows if r['level'] == f'{arm}|independent' and int(r['N']) == N]
    sizes = sorted({int(r['N']) for r in rows})
    fig, axs = plt.subplots(1, 2, figsize=(12, 3.9))
    w = 0.16
    for ax, k, title, ylab in ((axs[0], 'honestPooled', 'Guards protect the team best', 'honest pooled share (liars present)'),
                               (axs[1], 'contamination', 'and cut the answers built on lies', 'honest answers built on a false clue')):
        for i, (arm, lab, col) in enumerate(ARMS):
            xs, ys, err = [], [], [[], []]
            for j, N in enumerate(sizes):
                if not val(arm, N, k):
                    continue
                m, lo, hi = boot(val(arm, N, k))
                xs.append(j + (i - 2) * w)
                ys.append(m)
                err[0].append(m - lo)
                err[1].append(hi - m)
            ax.bar(xs, ys, w * 0.92, yerr=err, capsize=2, color=col, label=lab)
        ax.set_xticks(range(len(sizes)), [f'{N} agents' for N in sizes])
        ax.set(title=title, ylabel=ylab)
        ax.axhline(0, color='k', lw=0.6)
    axs[0].set_ylim(-0.13, 0.43)
    axs[0].legend(fontsize=8, loc='upper center', ncol=3)
    fig.tight_layout()
    out = R / 'report' / 'guards.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170, metadata={'Software': None})
    print(out)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
