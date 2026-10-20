"""Phase 18, Part 0: the numpy screen of colony rules and the forecast of Stage 1 (and of Stage 2's trend), and its
scoring against the Haiku runs (specs/multiagent/phase18/, requirements FR-01 to FR-03).

  python tools/colony_forecast.py run <repo> [workers]      -> results/multiagent/colony/forecast/runs.csv and
                                                               specs/multiagent/phase18/colony_predictions.json
  python tools/colony_forecast.py score <repo> <runs.csv>   -> specs/multiagent/phase18/colony_score.json

Rule agents (colony_agents) on `part0Grid()`: 7 arms x 4 fault settings x q in {2, 3} x N 4-128 x 30 seeds, two
holders per clue (r = q), 40 turns. The forecast uses the q = 2 cells: each hypothesis's estimate on the Stage 1 sizes
(8 and 16; H18-5: the per-seed slope over log2 N at 8-64), a 95% bootstrap interval over seeds, and a sign (+ or -
when the interval excludes 0, else 0). Scoring (frozen in COLONY_PLAN): a sign counts as right when the Haiku
interval excludes 0 on the predicted side, wrong when it excludes 0 on the other side; an interval spanning 0 is no
call (a predicted 0 is never right). H18-5 is forecast for the `colony` arm; it is scored only if Stage 2 ran `colony` (the
chosen arm), else it is left unscored."""
import json
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

KEYS = ('H18_1', 'H18_2', 'H18_3', 'H18_4', 'H18_6', 'colonyVsConfirm')


def _run(cell):
    from explRL.colony_trace import runColonyCell
    return runColonyCell(cell)


def _sign(lo, hi):
    return '+' if lo > 0 else '-' if hi < 0 else '0'


def estimates(rows, plan, nboot=2000, trendSizes=(8, 16, 32, 64)):
    "{hypothesis: dict(estimate, ci, sign)} from rows levelled '<arm>|<fault>' (H18_5: trend over trendSizes)."
    from explRL.colony_report import bootSeeds, colonySummaries, trendSlopes
    S = colonySummaries(rows, plan, nboot)
    out = {}
    for k in KEYS:
        t = S['hyp'][k] if k in S['hyp'] else S['secondary'][k]
        out[k] = dict(estimate=t['estimate'], ci=t['ci'], sign=_sign(*t['ci']))
    sl = trendSlopes(rows, 'colony', list(trendSizes))
    if sl:
        est, lo, hi = bootSeeds({(s, 0): v for s, v in sl.items()}, nboot=nboot)
        out['H18_5'] = dict(estimate=est, ci=[lo, hi], sign=_sign(lo, hi), arm='colony', sizes=list(trendSizes))
    return out


def run(repo, workers=8):
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import writeCSV
    from explRL.colony_grid import COLONY_PLAN, PART0_N, part0Grid
    cells = part0Grid()
    with mp.get_context('spawn').Pool(workers) as pool:
        rows = [r for rs in pool.imap(_run, cells, chunksize=8) for r in rs]
    out = Path(repo) / 'results/multiagent/colony/forecast'
    out.mkdir(parents=True, exist_ok=True)
    writeCSV(rows, out / 'runs.csv')
    q2 = [r for r in rows if '|q' not in r['level']]
    pred = estimates(q2, COLONY_PLAN)
    keep = ('honestPooled', 'pooledShare', 'contamination', 'suppression', 'freeRiding', 'misreport')
    screen = {}
    for r in rows:
        screen.setdefault(r['level'], {}).setdefault(int(r['N']), []).append([float(r[k]) for k in keep])
    screen = {lv: {N: dict(zip(keep, np.nanmean(v, 0).round(4).tolist())) for N, v in sorted(d.items())}
              for lv, d in sorted(screen.items())}
    spec = Path(repo) / 'specs/multiagent/phase18/colony_predictions.json'
    spec.write_text(json.dumps(dict(predictions=pred, screen=screen, sizes=PART0_N, cells=len(cells),
                                    rule='sign + or - when the 95% interval over seeds excludes 0, else 0; q = 2 cells'),
                               indent=1, default=float) + '\n')
    for k, v in pred.items():
        print(k, v['sign'], round(v['estimate'], 4), [round(x, 4) for x in v['ci']])


def score(repo, runsCsv):
    "Score the committed predictions against Haiku rows (Stage 1, and Stage 2 when present for H18-5)."
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    from explRL.colony_grid import COLONY_PLAN
    obs = estimates(readCSV(runsCsv), COLONY_PLAN)
    pred = json.loads((Path(repo) / 'specs/multiagent/phase18/colony_predictions.json').read_text())['predictions']
    res = {}
    for k, p in pred.items():
        if k not in obs or not np.isfinite(obs[k]['estimate']):
            continue
        o = obs[k]['sign']
        res[k] = dict(predicted=p['sign'], observed=o, ci=obs[k]['ci'],
                      result='no call' if o == '0' else 'right' if o == p['sign'] else 'wrong')
    out = dict(items=res, right=sum(v['result'] == 'right' for v in res.values()),
               wrong=sum(v['result'] == 'wrong' for v in res.values()), noCall=sum(v['result'] == 'no call' for v in res.values()))
    (Path(repo) / 'specs/multiagent/phase18/colony_score.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        run(Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    else:
        score(Path(sys.argv[2]), sys.argv[3])
