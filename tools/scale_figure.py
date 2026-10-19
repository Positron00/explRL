"""Summary figure of the team-size results with Claude Haiku 5.5 (Phases 13-15): the public track record's share of liars'
damage recovered and the request board's pooling gap closed against team size (left), and the share of honest answers
built on a false clue, Haiku against rule agents (right). Reads the saved results only.

  python tools/scale_figure.py <repo>   -> results/multiagent/report/trust_scale.png
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(repo):
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    from explRL.scale_report import scaleSummaries, trustSummaries
    R = Path(repo) / 'results/multiagent'
    ST = trustSummaries(readCSV(R / 'fix/full/runs.csv'), readCSV(R / 'trust/full/runs.csv'))
    SS = scaleSummaries(readCSV(R / 'scale/full/runs.csv'))
    TL = json.loads((R / 'liar/full/trace_summary.json').read_text())
    rec = [(4, ST['arms']['record'])] + [(v['N'], v) for v in SS['record'].values()]
    req = [(v['N'], v) for v in SS['request'].values()]
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.8))
    for pts, col, lab in ((rec, '#1f6391', 'public track record: liar damage recovered'),
                          (req, '#c0392b', 'request board: pooling gap closed')):
        x = [N for N, _ in pts]
        y = [v['gap'] for _, v in pts]
        err = [[v['gap'] - v['ci'][0] for _, v in pts], [v['ci'][1] - v['gap'] for _, v in pts]]
        a.errorbar(x, y, yerr=err, fmt='o-', capsize=3, color=col, label=lab)
    a.axhline(0, color='k', lw=0.6)
    a.set(xscale='log', xticks=[4, 8, 16, 32], xlabel='team size (Claude Haiku 5.5 agents)', ylabel='share of the gap',
          title='Fixes hold as teams grow (95% intervals)')
    a.set_xticklabels(['4', '8', '16', '32'])
    a.legend(fontsize=8, loc='center left')
    for who, mk, col, lab in (('haiku', 'o-', '#1f6391', 'Claude Haiku 5.5'), ('numpy', 's--', '#999999', 'rule agents')):
        P = TL['perN'][who]
        Ns = [N for N in (8, 16, 32) if str(N) in P]
        y = [P[str(N)]['contaminated']['mean'] for N in Ns]
        err = [[y[i] - P[str(N)]['contaminated']['ci'][0] for i, N in enumerate(Ns)],
               [P[str(N)]['contaminated']['ci'][1] - y[i] for i, N in enumerate(Ns)]]
        b.errorbar(Ns, y, yerr=err, fmt=mk, capsize=3, color=col, label=lab)
    b.set(xscale='log', xticks=[8, 16, 32], xlabel='team size (a quarter of the agents liars)', ylim=(0.6, 1.02),
          ylabel='honest answers built on a false clue', title='Larger teams build on lies more often')
    b.set_xticklabels(['8', '16', '32'])
    b.legend(fontsize=8, loc='lower right')
    for ax in (a, b):
        ax.minorticks_off()
    fig.tight_layout()
    out = R / 'report' / 'trust_scale.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170, metadata={'Software': None})
    print(out)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
