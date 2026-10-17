"""Phase 14, Part B: the numpy forecast of how the clue-board team changes with team size, and its scoring against the
Haiku baseline (specs/multiagent/phase14/README.md, requirements FR-C1, FR-C2).

  python tools/scale_forecast.py run <repo>                  -> results/multiagent/forecast/scale_numpy.json and
                                                                specs/multiagent/phase14/scale_predictions.json
  python tools/scale_forecast.py score <repo> <runs.csv>     -> results/multiagent/forecast/scale_score.json

Rule agents of Phase 11 (blackboard, 'needed' sharing, the chosen guess rate; liars first) at N in (4, 8, 16, 32, 64),
clean and with a quarter of the agents liars, 40 turns per agent, seeds 2000-2019. Predicted: the sign of the change
from N = 8 to N = 32 in (a) the clean team's pooled share and (b) the honest agents' loss from liars (welfareHonest
clean minus with liars, same seed and N). Each side's change is the mean at N = 32 minus the mean at N = 8, with a
95% bootstrap interval resampling seeds within each N (boards differ by N, so seeds are not paired); + or - when the
interval excludes 0, else 0."""
import json
import sys
from pathlib import Path

import numpy as np

SIZES, SEEDS, TURNS = (4, 8, 16, 32, 64), range(2000, 2020), 40
METRICS = ('pooledShare', 'honestLoss')


def change(lo, hi, n=2000, seed=0):
    "Mean of hi minus mean of lo, with a 95% bootstrap interval resampling each side's seeds; and its sign."
    lo, hi = np.asarray([x for x in lo if x == x], float), np.asarray([x for x in hi if x == x], float)
    rng = np.random.default_rng(seed)
    d = rng.choice(hi, (n, len(hi))).mean(1) - rng.choice(lo, (n, len(lo))).mean(1)
    ci = [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
    return dict(mean=float(hi.mean() - lo.mean()), ci=ci, sign='+' if ci[0] > 0 else '-' if ci[1] < 0 else '0')


def perN(rows, N):
    "pooledShare of the clean cells and the honest loss per seed at team size N, from rows with level clean/liar."
    f = lambda x: float(x) if x not in ('', None) else float('nan')
    clean = {int(f(r['seed'])): r for r in rows if int(f(r['N'])) == N and r['kind'] == 'clean'}
    liar = {int(f(r['seed'])): r for r in rows if int(f(r['N'])) == N and r['kind'] == 'liar'}
    return dict(pooledShare=[f(clean[s]['pooledShare']) for s in sorted(clean)],
                honestLoss=[f(clean[s]['welfareHonest']) - f(liar[s]['welfareHonest']) for s in sorted(set(clean) & set(liar))])


def run(repo):
    sys.path.insert(0, str(repo))
    from explRL.clue_grid import CLUE_SETTINGS, _board, clueCell
    from explRL.clue_runs import runClueNumpy
    from explRL.llm_runs import LLMConfig
    s, rows = CLUE_SETTINGS, []
    for N in SIZES:
        for kind, nLiar in (('clean', 0), ('liar', N // 4)):
            for sd in SEEDS:
                cell = clueCell('scaleNumpy', kind, N, sd, 'numpy', s=s, channel='blackboard', turns=TURNS, nLiar=nLiar,
                                world=dict(_board(s), guess=s['guess'], share='needed'))
                r = runClueNumpy(LLMConfig.fromDict(cell['cfg']), sd)[0]
                rows.append(dict(N=N, seed=sd, kind=kind, nLiar=nLiar, pooledShare=r['pooledShare'], welfare=r['welfare'],
                                 welfareHonest=r['welfareHonest']))
    out = Path(repo) / 'results/multiagent/forecast'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'scale_numpy.json').write_text(json.dumps(rows, indent=1) + '\n')
    curves = {m: {N: float(np.nanmean(perN(rows, N)[m])) for N in SIZES} for m in METRICS}
    pred = {m: change(perN(rows, 8)[m], perN(rows, 32)[m]) for m in METRICS}
    spec = Path(repo) / 'specs/multiagent/phase14/scale_predictions.json'
    spec.write_text(json.dumps(dict(predictions=pred, curves=curves, sizes=list(SIZES), seeds=[SEEDS[0], SEEDS[-1]],
                                    turns=TURNS), indent=1) + '\n')
    for m in METRICS:
        print(m, {N: round(v, 3) for N, v in curves[m].items()}, 'N 8 -> 32:', pred[m])


def score(repo, runsCsv):
    "The Haiku baseline cells of study scaleB (clean: level 'baseline'; liars: 'baseline|liar'), scored with the frozen rule."
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    rows = []
    for r in readCSV(runsCsv):
        if r['study'] == 'scaleB' and r['level'] in ('baseline', 'baseline|liar'):
            rows.append(dict(r, kind='liar' if r['level'].endswith('|liar') else 'clean'))
    obs = {m: change(perN(rows, 8)[m], perN(rows, 32)[m]) for m in METRICS}
    pred = json.loads((Path(repo) / 'specs/multiagent/phase14/scale_predictions.json').read_text())['predictions']
    res = dict(observed=obs, predicted=pred, agree=sum(pred[m]['sign'] == obs[m]['sign'] for m in METRICS), total=len(METRICS))
    out = Path(repo) / 'results/multiagent/forecast/scale_score.json'
    out.write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        run(Path(sys.argv[2]))
    else:
        score(Path(sys.argv[2]), sys.argv[3])
