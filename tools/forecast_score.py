"""Score the numpy forecast of the RL arms with the frozen rule of specs/multiagent/phase13/forecast.md.
Usage: python tools/forecast_score.py <repo> [Phase 13 eval runs.csv]  -> results/multiagent/forecast/{predictions,score}.json"""
import json
import sys
from pathlib import Path

import numpy as np

METRICS = ('welfare', 'sharePerHeld', 'soloShare', 'wrongPerSolve')
RETRO, FORE = ('individual', 'team', 'credit'), ('indpen', 'credturn')


def boot(x, n=2000, seed=0):
    x = np.asarray([v for v in x if v == v], float)
    if len(x) == 0:
        return float('nan'), [float('nan')] * 2
    m = np.random.default_rng(seed).choice(x, (n, len(x))).mean(1)
    return float(x.mean()), [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def sign(ci):
    return '+' if ci[0] > 0 else '-' if ci[1] < 0 else '0'


def numpyEffects(res):
    "Per arm and metric: mean over training seeds of (arm - warm) on the evaluation boards, CI over training seeds."
    warm = {m: np.nanmean([r[m] for r in res['warm']['eval']]) for m in METRICS}
    out = {}
    for arm in RETRO + FORE:
        runs = [v for k, v in res.items() if k.startswith(arm + '_s')]
        for m in METRICS:
            mean, ci = boot([np.nanmean([r[m] for r in v['eval']]) - warm[m] for v in runs])
            out[f'{arm}|{m}'] = dict(mean=mean, ci=ci, sign=sign(ci))
    return out


def llmEffects(rows, arms):
    "Per arm and metric: the LLM model minus the warm start on the main boards, paired on board seed (seeds pooled)."
    f = lambda x: float(x) if x not in ('', None) else float('nan')
    main = [r for r in rows if r['level'].endswith('|main')]
    warm = {int(f(r['seed'])): r for r in main if r['level'] == 'warm|main'}
    out = {}
    for arm, models in arms.items():
        rs = [r for r in main if r['level'].split('|')[0] in models]
        for m in METRICS:
            d = [f(r[m]) - f(warm[int(f(r['seed']))][m]) for r in rs if int(f(r['seed'])) in warm]
            mean, ci = boot(d)
            out[f'{arm}|{m}'] = dict(mean=mean, ci=ci, sign=sign(ci), n=len(d))
    return out


def score(pred, llm, arms):
    keys = [f'{a}|{m}' for a in arms for m in METRICS if f'{a}|{m}' in llm]
    agree = [k for k in keys if pred[k]['sign'] == llm[k]['sign']]
    return dict(agree=len(agree), total=len(keys), pairs={k: (pred[k]['sign'], llm[k]['sign']) for k in keys})


def main():
    repo = Path(sys.argv[1])
    R = repo / 'results/multiagent'
    sys.path.insert(0, str(repo))
    from explRL.bench_grid import readCSV
    pred = numpyEffects(json.load(open(R / 'forecast/numpy.json')))
    (R / 'forecast/predictions.json').write_text(json.dumps(pred, indent=1) + '\n')
    p12 = readCSV(R / 'rl/eval/runs.csv')
    out = dict(retrodiction=score(pred, llmEffects(p12, {a: (a,) for a in RETRO}), RETRO))
    if len(sys.argv) > 2:                          # after the Phase 13 evaluation: the forecast, scored unchanged
        p13 = readCSV(sys.argv[2])
        rows = p12 + [r for r in p13 if r['level'].split('|')[0] != 'warm']
        llm13 = llmEffects(rows, {'indpen': ('indpen_s1', 'indpen_s2'), 'credturn': ('credturn_s1', 'credturn_s2'),
                                  'credit2': ('credit_s2',)})
        out['forecast'] = score(pred, llm13, FORE)
        out['replication'] = dict(pairs={m: (pred[f'credit|{m}']['sign'], llm13[f'credit2|{m}']['sign']) for m in METRICS})
        out['llm13'] = llm13
    (R / 'forecast/score.json').write_text(json.dumps(out, indent=1) + '\n')
    for k, v in pred.items():
        print(f"{k:24s} numpy {v['mean']:+.3f} [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}] {v['sign']}")
    print(json.dumps({k: v for k, v in out.items() if k != 'llm13'}, indent=1))


if __name__ == '__main__':
    main()
