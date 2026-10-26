"""Summary figure of the team-size results (Phases 13-15): the track record and request board against team size, and answers built on lies.

Now a wrapper: the figure is drawn by `tools/figures.py` (trustScale), with the publication convention (mean ± SEM, * p < 0.05).

  python tools/scale_figure.py <repo>   -> docs/summary/trust_scale.png (the summary page)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figures  # noqa: E402


def main(repo):
    sys.path.insert(0, str(repo))
    R = Path(repo) / 'results/multiagent'
    figures.trustScale(R, R / 'report')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
