"""Summary figure of Phase 18's guards against team size, with the Stage 4 designs.

Now a wrapper: the figure is drawn by `tools/figures.py` (guardsScale), with the publication convention (mean ± SEM, * p < 0.05).

  python tools/scale_guard_figure.py <repo>   -> docs/summary/guards_scale.png (the summary page)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figures  # noqa: E402


def main(repo):
    sys.path.insert(0, str(repo))
    R = Path(repo) / 'results/multiagent'
    figures.guardsScale(R, R / 'report')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
