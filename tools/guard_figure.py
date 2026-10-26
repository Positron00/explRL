"""Summary figure of Phase 18 Stage 1 and the 32-agent run: honest pooled share and answers built on lies per arm.

Now a wrapper: the figure is drawn by `tools/figures.py` (guards), with the publication convention (mean ± SEM, * p < 0.05).

  python tools/guard_figure.py <repo>   -> docs/summary/guards.png (the summary page)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figures  # noqa: E402


def main(repo):
    sys.path.insert(0, str(repo))
    R = Path(repo) / 'results/multiagent'
    figures.guards(R, R / 'report')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
