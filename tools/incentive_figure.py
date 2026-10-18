"""Summary figure of the RL incentive results (Phases 12-13): for each trained 3B team, on the 15 held-out main boards,
the share of held clues it shared, the share of its solves made without any shared clue, and its welfare per agent-turn
(means with 95% bootstrap intervals over boards; each training seed its own row). Reads the saved evaluations only; once the
Phase 16 batch is unzipped (results/multiagent/rl/colab/eval_p16/runs.csv), its six extra seeds appear as their own rows.

  python tools/incentive_figure.py <repo>   -> results/multiagent/report/incentives.png
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROWS = (  # (label, eval dir, level, colour)
    ('imitation (warm start)', 'eval', 'warm', '#555555'),
    ('individual reward', 'eval', 'individual', '#c0392b'),
    ('team reward', 'eval', 'team', '#999999'),
    ('individual, loophole priced (seed 1)', 'eval_p13', 'indpen_s1', '#e67e22'),
    ('individual, loophole priced (seed 2)', 'eval_p13', 'indpen_s2', '#e67e22'),
    ('credit reward (seed 1)', 'eval_p13', 'credit_s1', '#2471a3'),
    ('credit reward (seed 2)', 'eval_p13', 'credit_s2', '#2471a3'),
    ('credit, per-turn (seed 1)', 'eval_p13', 'credturn_s1', '#5dade2'),
    ('credit, per-turn (seed 2)', 'eval_p13', 'credturn_s2', '#5dade2'),
)
PANELS = (('sharePerHeld', 'clues shared / clues held'), ('soloShare', 'solves made without a shared clue'),
          ('welfare', 'welfare per agent-turn'))


def main(repo):
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    from explRL.llm_report import _stat
    R = Path(repo) / 'results/multiagent/rl'
    data = {d: readCSV(R / d / 'runs.csv') for d in ('eval', 'eval_p13')}
    rows = list(ROWS)
    p16 = R / 'colab' / 'eval_p16' / 'runs.csv'
    if p16.exists():                                   # Phase 16: individual seeds 2-4 and indpen seeds 3-5
        data['eval_p16'] = readCSV(p16)
        rows[1] = ('individual reward (seed 1)', 'eval', 'individual', '#c0392b')
        rows[2:2] = [(f'individual reward (seed {s})', 'eval_p16', f'individual_s{s}', '#c0392b') for s in (2, 3, 4)]
        i = max(k for k, r in enumerate(rows) if r[2].startswith('indpen')) + 1
        rows[i:i] = [(f'individual, loophole priced (seed {s})', 'eval_p16', f'indpen_s{s}', '#e67e22') for s in (3, 4, 5)]
    clue = readCSV(Path(repo) / 'results/multiagent/clue/full/runs.csv')       # Phase 11: the same boards (seeds 900-904)
    ref = lambda study, runner: _stat(r['welfare'] for r in clue if r['study'] == study and r['runner'] == runner and
                                      r['channel'] == 'blackboard' and int(r['N']) == 4 and 900 <= int(r['seed']) <= 904)['mean']
    REFS = dict(welfare=((ref('clue', 'llm'), 'Claude Haiku 5.5'), (ref('clueNumpy', 'numpy'), 'rule agents')))
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.2 + 0.3 * (len(rows) - len(ROWS))), sharey=True)
    for ax, (m, title) in zip(axs, PANELS):
        for y, (label, d, lv, col) in enumerate(rows):
            v = _stat(r[m] for r in data[d] if r['level'] == f'{lv}|main')
            lo, hi = v['ci']
            ax.errorbar([v['mean']], [y], xerr=[[v['mean'] - lo], [hi - v['mean']]], fmt='o', color=col, capsize=3, ms=7)
        for (x, name), ls in zip(REFS.get(m, ()), ('--', ':')):
            ax.axvline(x, ls=ls, lw=1.2, color='k', alpha=0.6, label=f'{name} ({x:.2f})')
        if m in REFS:
            ax.set_xlim(-0.02, 0.85)
            ax.legend(fontsize=8, loc='upper right', framealpha=1, title='references (same boards)', title_fontsize=8)
        ax.set_title(title, fontsize=11)
        ax.grid(axis='x', alpha=0.3)
    axs[0].set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=9)
    axs[0].invert_yaxis()
    fig.suptitle('Trained 3B teams: the guessing loophole, not the reward alone, decided whether agents cooperated',
                 fontsize=12)
    fig.text(0.5, 0.005, 'Qwen2.5-3B-Instruct, 4 agents sharing one LoRA adapter, GRPO; 15 held-out boards; '
             'means with 95% bootstrap intervals over boards; each training seed shown separately', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    out = Path(repo) / 'results/multiagent/report/incentives.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170, metadata={'Software': None})
    print(out)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
