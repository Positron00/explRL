"""Summary figure of the RL incentive results (Phases 12-16): every trained 3B team on the 15 held-out boards.

Now a wrapper: the figure is drawn by `tools/figures.py` (incentives), with the publication convention (mean ± SEM, * p < 0.05).

  python tools/incentive_figure.py <repo>   -> docs/summary/incentives.png (the summary page)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figures  # noqa: E402


def main(repo):
    sys.path.insert(0, str(repo))
    R = Path(repo) / 'results/multiagent'
    figures.incentives(R, R / 'report')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
