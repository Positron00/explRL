"""Phase 18, Part 0: the numpy screen of colony rules and the forecast of Stage 1 (and of Stage 2's trend), and its
scoring against the Haiku runs (specs/multiagent/phase18/, requirements FR-01 to FR-03).

  python tools/colony_forecast.py run <repo> [workers]      -> results/multiagent/colony/forecast/runs.csv and
                                                               specs/multiagent/phase18/colony_predictions.json
  python tools/colony_forecast.py score <repo> <runs.csv>   -> specs/multiagent/phase18/colony_score.json
  python tools/colony_forecast.py stage4b <repo>             -> specs/multiagent/phase18/colony4b_predictions.json (from forecast4)
  python tools/colony_forecast.py stage4 <repo> [workers]   -> results/multiagent/colony/forecast4/runs.csv and
                                                               specs/multiagent/phase18/colony4_predictions.json (Stage 4)
  python tools/colony_forecast.py score4 <repo>             -> specs/multiagent/phase18/colony4_score.json

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


SIZES4, ARMS4_RUN = (8, 16, 32, 64, 128), ('plain', 'colonyGuards', 'guardDeal', 'failFlag', 'squads', 'guardDealFlag', 'squadsAll')


def _run4(cell):
    from explRL.colony_mech import runStage4Cell
    return runStage4Cell(cell)


def predict4(rows, nboot=2000):
    "Stage 4's forecast items from rows levelled '<arm>|independent': H18-13 to H18-15 at 64, each 16-to-64 change, the curves."
    from explRL.colony4_report import HYP4, diffs
    from explRL.colony_report import bootSeeds
    out, ind = {}, 'independent'
    for h, arm in HYP4:
        est, lo, hi = bootSeeds(diffs(rows, arm, 'colonyGuards', 'honestPooled', ind, 64), nboot=nboot)
        out[h] = dict(arm=arm, estimate=est, ci=[lo, hi], sign=_sign(lo, hi))
        d64, d16 = (diffs(rows, arm, 'colonyGuards', 'honestPooled', ind, N) for N in (64, 16))
        est, lo, hi = bootSeeds({(s, 0): v - d16[(s, 16)] for (s, _), v in d64.items() if (s, 16) in d16}, nboot=nboot)
        out[f'did_{arm}'] = dict(arm=arm, estimate=est, ci=[lo, hi], sign=_sign(lo, hi))
    curves = {a: {N: float(np.mean(list(dp.values()))) for N in SIZES4 if (dp := diffs(rows, a, 'plain', 'honestPooled', ind, N))}
              for a in ARMS4_RUN[1:]}
    return out, curves


def stage4(repo, workers=8):
    "Numpy rule agents with Stage 4's options, independent liars, N 8-128, Part 0's seeds; the frozen forecast."
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import writeCSV
    from explRL.colony4 import ARMS4
    from explRL.colony_grid import PART0_SEEDS, colonyCell
    cells = [colonyCell('colony4Forecast', a, N, s, 'independent', 'numpy', arms=ARMS4)
             for a in ARMS4_RUN for N in SIZES4 for s in PART0_SEEDS]
    with mp.get_context('spawn').Pool(workers) as pool:
        rows = [r for rs in pool.imap(_run4, cells, chunksize=4) for r in rs]
    out = Path(repo) / 'results/multiagent/colony/forecast4'
    out.mkdir(parents=True, exist_ok=True)
    writeCSV(rows, out / 'runs.csv')
    pred, curves = predict4(rows)
    spec = Path(repo) / 'specs/multiagent/phase18/colony4_predictions.json'
    spec.write_text(json.dumps(dict(predictions=pred, curves=curves, sizes=SIZES4, cells=len(cells),
                                    rule='sign + or - when the 95% interval over seeds excludes 0, else 0'),
                               indent=1, default=float) + '\n')
    for k, v in pred.items():
        print(k, v['sign'], round(v['estimate'], 4), [round(x, 4) for x in v['ci']])
    for a, c in curves.items():
        print(a, {N: round(v, 3) for N, v in c.items()})


def score4(repo):
    "Score Stage 4's predictions against the Haiku rows (stage4/runs.csv with the reused references, reused.csv)."
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    from explRL.colony4_report import stage4Summaries
    d = Path(repo) / 'results/multiagent/colony/stage4'
    S = stage4Summaries(readCSV(d / 'runs.csv'), readCSV(d / 'reused.csv'))
    obs = {h: S['hyp'][h] for h in S['hyp']} | {f'did_{a}': t for a, t in S['did'].items()}
    pred = json.loads((Path(repo) / 'specs/multiagent/phase18/colony4_predictions.json').read_text())['predictions']
    res = {}
    for k, p in pred.items():
        o = _sign(*obs[k]['ci'])
        res[k] = dict(predicted=p['sign'], observed=o, ci=obs[k]['ci'],
                      result='no call' if o == '0' else 'right' if o == p['sign'] else 'wrong')
    out = dict(items=res, right=sum(v['result'] == 'right' for v in res.values()),
               wrong=sum(v['result'] == 'wrong' for v in res.values()), noCall=sum(v['result'] == 'no call' for v in res.values()))
    (Path(repo) / 'specs/multiagent/phase18/colony4_score.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out, indent=1))


def stage4b(repo, nboot=2000):
    """Stage 4b's forecast from Stage 4's frozen numpy rows at 32 agents (forecast4/runs.csv, no new simulation): each design
    minus guards at 32 (H18-16 to H18-18) and each design's trend over team size, signed by the 95% interval rule."""
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    from explRL.colony4_report import diffs
    from explRL.colony4b import HYP4B, TRENDS4B
    from explRL.colony_report import bootSeeds, trendSlopes
    rows = readCSV(Path(repo) / 'results/multiagent/colony/forecast4/runs.csv')
    pred = {}
    for h, arm in HYP4B:
        est, lo, hi = bootSeeds(diffs(rows, arm, 'colonyGuards', 'honestPooled', 'independent', 32), nboot=nboot)
        pred[h] = dict(arm=arm, estimate=est, ci=[lo, hi], sign=_sign(lo, hi))
    for arm, sizes in TRENDS4B:
        sl = trendSlopes(rows, arm, list(sizes))
        est, lo, hi = bootSeeds({(k, 0): v for k, v in sl.items()}, nboot=nboot)
        pred[f'trend_{arm}'] = dict(arm=arm, sizes=list(sizes), estimate=est, ci=[lo, hi], sign=_sign(lo, hi))
    spec = Path(repo) / 'specs/multiagent/phase18/colony4b_predictions.json'
    spec.write_text(json.dumps(dict(predictions=pred, source='forecast4/runs.csv (numpy, 30 seeds, frozen at 1e9c53d)',
                                    rule='sign + or - when the 95% interval over seeds excludes 0, else 0'), indent=1, default=float) + '\n')
    for k, v in pred.items():
        print(k, v['sign'], round(v['estimate'], 4), [round(x, 4) for x in v['ci']])


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        run(Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif sys.argv[1] == 'stage4':
        stage4(Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif sys.argv[1] == 'stage4b':
        stage4b(Path(sys.argv[2]))
    elif sys.argv[1] == 'score4':
        score4(Path(sys.argv[2]))
    else:
        score(Path(sys.argv[2]), sys.argv[3])
