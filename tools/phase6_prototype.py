#!/usr/bin/env python3
"""Phase 6 T1: dynamic-range check (throwaway, numpy only, does not import explRL).

Synchronous 1 s steps; travel lasts ceil(T) steps; a stay lasts one step.
Writes results/multiagent/phase6_prototype/{report.md, metrics.json}."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / 'results' / 'multiagent' / 'phase6_prototype'
CHANNELS = ('none', 'blackboard', 'messages')
SIZES, SEEDS, T = (1, 4, 16, 64), 10, 600
DEFAULTS = dict(ringN=32, ringScale=0.1, side=8, torusScale=0.5, nPatches=4, nDanger=4,
                intake=(0.5, 1.0, 1.5, 2.0), K=100.0, g=0.2, Smin=1.0, c=1.0, dangerCost=1.0,
                Tmove=120, cUCB=1.0, H=10.0)
# tried in order until one passes; every attempt is written to report.md
ATTEMPTS = [dict(), dict(cUCB=0.3), dict(Tmove=60, cUCB=0.3)]


def layout_dist(name, s):
    if name == 'ring':
        i = np.arange(s['ringN'])
        d = np.minimum(abs(i[:, None] - i), s['ringN'] - abs(i[:, None] - i))
        return d.astype(float), s['ringScale']
    xy = np.array([(x, y) for y in range(s['side']) for x in range(s['side'])], float)
    dd = abs(xy[:, None, :] - xy[None, :, :])
    dd = np.minimum(dd, s['side'] - dd)
    return np.sqrt((dd ** 2).sum(-1)), s['torusScale']


def yield_rate(model, s, ip, n):
    if n <= 0:
        return 0.0
    if model == 'fixed':
        return min(n * s['c'], ip)
    msy = s['g'] * s['K'] / 4
    return n * s['c'] if n * s['c'] <= msy else s['g'] * s['Smin'] * (1 - s['Smin'] / s['K'])


def social_opt(model, s, N):
    best = np.zeros(N + 1)
    for ip in s['intake']:
        prev = best.copy()
        for m in range(N + 1):
            best[m] = max(prev[m - k] + yield_rate(model, s, ip, k) for k in range(m + 1))
    return float(best.max())


def episode(layout, model, harness, A, seed, s):
    "Returns (whole-run, first-quarter) team welfare rates (true harvest per second)."
    rSites, rMoves, rAgents = [np.random.default_rng(q) for q in np.random.SeedSequence(seed).spawn(3)]
    dist, scale = layout_dist(layout, s)
    L, P = len(dist), s['nPatches']
    Tm = dist * scale
    steps = np.maximum(1, np.ceil(Tm - 1e-9)).astype(int)
    site = rSites.choice(L, P, replace=False)
    danger = np.zeros(L, bool)
    danger[rSites.choice(np.setdiff1d(np.arange(L), site), s['nDanger'], replace=False)] = True
    intake = np.asarray(s['intake'], float)
    stock = np.full(P, s['K'])
    loc = rSites.integers(L, size=A)
    busy = np.zeros(A, int)
    cnt, tot = np.zeros((A, L)), np.zeros((A, L))
    info = np.full((A, L), np.nan)               # shared rate (blackboard or messages), own data wins
    board = np.full(L, np.nan)
    harvest = np.zeros(T)
    rows = np.arange(A)
    for t in range(T):
        if t and t % s['Tmove'] == 0:
            for p in range(P):
                free = [j for j in range(L) if j not in site and not danger[j]]
                site[p] = rMoves.choice(free)
        if model == 'logistic':
            stock = s['K'] / (1 + (s['K'] / stock - 1) * math.exp(-s['g']))
        free_ag = busy == 0
        if harness == 'random':
            target = rAgents.integers(L, size=A)
        else:
            if harness == 'blackboard':
                info[:] = board
            useInfo = (cnt == 0) & ~np.isnan(info)
            n = np.where(useInfo, 1.0, cnt)
            mean = np.where(useInfo, info, tot / np.maximum(cnt, 1))
            Trow = Tm[loc]
            unv = n == 0
            nearest = np.argmax(np.where(unv, -Trow, -np.inf), axis=1)
            bonus = s['cUCB'] * np.sqrt(np.log1p(n.sum(1, keepdims=True)) / np.maximum(n, 1))
            best = np.argmax((mean + bonus) * s['H'] / (s['H'] + Trow), axis=1)
            target = np.where(unv.any(1), nearest, best)
        stay = free_ag & (target == loc)
        go = free_ag & ~stay
        busy[go] = steps[loc[go], target[go]]
        loc = np.where(go, target, loc)
        reward = np.zeros(A)
        for p in range(P):
            here = stay & (loc == site[p])
            k = int(here.sum())
            if not k:
                continue
            if model == 'fixed':
                h = min(s['c'], intake[p] / k)
            else:
                take = min(s['c'] * k, stock[p] - s['Smin'])
                stock[p] -= take
                h = take / k
            reward[here] = h
            harvest[t] += h * k
        reward[stay & danger[loc]] = -s['dangerCost']
        sl = loc[stay]
        cnt[rows[stay], sl] += 1
        tot[rows[stay], sl] += reward[stay]
        board[sl] = reward[stay]
        if harness == 'messages' and t and t % 10 == 0 and A > 1:
            own = np.where(cnt > 0, tot / np.maximum(cnt, 1), -np.inf)
            bestLoc = own.argmax(1)
            for i in np.flatnonzero(cnt.sum(1) > 0):
                to = rAgents.choice(np.delete(np.arange(A), i), min(2, A - 1), replace=False)
                info[to, bestLoc[i]] = own[i, bestLoc[i]]
        busy = np.maximum(busy - 1, 0) * ~stay
    return harvest.mean(), harvest[: T // 4].mean()


def ci(x, seed=0, n=2000):
    rng = np.random.default_rng(seed)
    b = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)]
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def check(layout, model, s):
    runs = {(h, N): np.array([episode(layout, model, h, N, sd, s) for sd in range(SEEDS)])
            for h in CHANNELS + ('random',) for N in SIZES}
    so = {N: social_opt(model, s, N) for N in SIZES}
    c1 = all(runs[h, N][:, 1].mean() < 0.9 * so[N] for h in CHANNELS for N in SIZES)
    c2 = all(ci(runs['none', N][:, 0])[0] > ci(runs['random', N][:, 0])[1] for N in SIZES)
    gaps = {}
    for N in SIZES:
        m = {h: runs[h, N][:, 0].mean() for h in CHANNELS}
        d = runs[max(m, key=m.get), N][:, 0] - runs[min(m, key=m.get), N][:, 0]
        gaps[N] = (float(d.mean()),) + ci(d, seed=1)
    big, small = max(gaps, key=lambda N: gaps[N][0]), min(gaps, key=lambda N: gaps[N][0])
    c3 = sum(g[1] > 0 for g in gaps.values()) >= 2 and gaps[big][1] > gaps[small][2]
    table = {f'{h}/{N}': [round(float(runs[h, N][:, 0].mean()), 4), round(float(runs[h, N][:, 1].mean()), 4)]
             for h in CHANNELS + ('random',) for N in SIZES}
    return dict(layout=layout, model=model, ok=bool(c1 and c2 and c3), ceiling=bool(c1), floor=bool(c2),
                gap=bool(c3), so=so, gaps={N: [round(x, 4) for x in g] for N, g in gaps.items()}, rates=table)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report, attempts = ['# Phase 6 prototype (T1)\n',
                        f'Team sizes {SIZES}, {SEEDS} seeds, {T} s. Rates: [whole run, first quarter] team harvest/s.\n'], []
    for k, change in enumerate(ATTEMPTS, 1):
        s = {**DEFAULTS, **change}
        res = [check(lay, mod, s) for lay in ('ring', 'torus') for mod in ('fixed', 'logistic')]
        attempts.append(dict(attempt=k, change=change, results=res))
        report.append(f'## Attempt {k}: changes from defaults {change or "none"}\n')
        report.append('| layout | model | pass | ceiling | floor | gap | gap per size [mean, lo, hi] |\n|---|---|---|---|---|---|---|')
        for r in res:
            report.append(f"| {r['layout']} | {r['model']} | {r['ok']} | {r['ceiling']} | {r['floor']} | {r['gap']} | {r['gaps']} |")
        report.append('')
        if any(r['ok'] for r in res):
            break
    passed = [r for r in attempts[-1]['results'] if r['ok']]
    # "passes most clearly": largest weakest gap lower bound over team sizes > 1
    best = max(passed, key=lambda r: min(g[1] for N, g in r['gaps'].items() if N > 1)) if passed else None
    report.append(f"**Result:** MAIN={best['layout']}, model={best['model']}, settings={attempts[-1]['change'] or 'defaults'}\n"
                  if best else '**Result: no (layout, model) passed. Review the plan before T2.**\n')
    (OUT / 'report.md').write_text('\n'.join(report))
    (OUT / 'metrics.json').write_text(json.dumps(dict(attempts=attempts, main=best and [best['layout'], best['model']]),
                                                 indent=1, default=str))
    print('\n'.join(report))


if __name__ == '__main__':
    main()
