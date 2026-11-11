"""Phase 22 (B3) runs, multiprocess, behind a __main__ guard (macOS spawn; NFR-5). Offline, $0.

    python tools/b3_run.py check [workers]    θ_default reruns of Part 0's Stage 1 cells (N 8, 16; q 2; clean, independent) and
                                              Stage 4's forecast cells (N 16, 32, 64), 30 seeds, against forecast/ and forecast4/runs.csv
    python tools/b3_run.py probe              1-seed timing of the slowest fit cell (64 agents) and the projected grid hours
    python tools/b3_run.py grid [workers]     the coarse grid for the three candidates, chooseKnob, then the winner's fine grid
                                              (refuses an unfrozen B3_PLAN; AC-9)
    python tools/b3_run.py fit                folds, the fit on all cells, bootTau and fitHealth from the grid cache -> b3/fit.json
    python tools/b3_run.py retro              the retrospective check, every candidate -> b3/retro.json, retro.md
    python tools/b3_run.py forecast C1        C1's forecast after its pilot -> specs/multiagent/phase20/c1_predictions.json
    python tools/b3_run.py score C1           C1's score after its report -> c1_score.json beside the forecast
"""
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
OUT = REPO / 'results/multiagent/b3'


def _check(cell):
    from explRL.b3_agents import b3Replay
    from explRL.colony_mech import stage4Columns
    from explRL.colony_trace import colonyColumns
    from explRL.llm_runs import LLMConfig, cellRow
    cfg = LLMConfig.fromDict(cell['cfg'])
    rp = b3Replay(cfg, cell['seed'])
    return cellRow(cell, cfg, stage4Columns(cfg, rp) if cell['study'] == 'colony4Forecast' else colonyColumns(rp))


def check(workers=8):
    "NFR-1, T4 step 1: every θ_default rerun equals its saved numpy row, column for column."
    from explRL.bench_grid import readCSV
    from explRL.colony4 import ARMS4
    from explRL.colony_grid import PART0_SEEDS, colonyCell, part0Grid
    from explRL.colony_mech import _diff, _key
    F = REPO / 'results/multiagent/colony'
    ref = {_key(r): r for f in ('forecast', 'forecast4') for r in readCSV(F / f / 'runs.csv')}
    c0 = [c for c in part0Grid(sizes=(8, 16)) if c['level'].split('|')[1] in ('clean', 'independent') and 'q3' not in c['level']]
    arms4 = sorted({k[1].split('|')[0] for k in ref if k[0] == 'colony4Forecast'})
    c4 = [colonyCell('colony4Forecast', a, N, s, 'independent', 'numpy', arms=ARMS4) for a in arms4 for N in (16, 32, 64)
          for s in PART0_SEEDS]
    t0 = time.time()
    with mp.get_context('spawn').Pool(workers) as pool:
        rows = pool.map(_check, c0 + c4, chunksize=4)
    bad = [(_key(r), d[:5]) for r in rows if (d := _diff(ref[_key(r)], r))]
    print(f'check: {len(c0)} Part 0 and {len(c4)} Stage 4 forecast boards, {len(bad)} differ, {time.time() - t0:.0f} s')
    assert not bad, bad[:5]


def probe():
    "T4 step 3: one seed of the slowest fit cell at a non-default θ, and the projected coarse and fine grid hours on 8 workers."
    from explRL.b3_cells import CELL, FIT_CELLS
    from explRL.b3_fit import simRow
    times = {}
    for cid in ('colony/stage4:squadsAll|independent:64', 'colony/stage64:colonyGuards|independent:64', 'colony/stage1:plain|clean:8'):
        t0 = time.time()
        simRow(CELL[cid], 3000, dict(trustOne=0.6, spread=0.6, shareAll=0.6))
        times[cid] = time.time() - t0
    per = sum(times[c] for c in times if c.endswith(':64')) / 2
    est = {c['id']: per * (c['N'] / 64) ** 1.5 for c in FIT_CELLS}         # board cost grows faster than N (turns x agents)
    board = sum(est.values()) * 30                                           # one grid point: 32 cells x 30 seeds
    print(json.dumps(dict(seconds=times, perGridPoint=round(board, 1),
                          coarseHours=round(96 * board / 8 / 3600, 2), fineHours=round(85 * board / 8 / 3600, 2)), indent=1))


def _coarse():
    from explRL.b3_cells import CANDIDATES, grid, thetaKey
    seen, out = set(), []
    for c in CANDIDATES:
        for th in grid(('trustOne', c)):
            if thetaKey(th) not in seen:
                seen.add(thetaKey(th))
                out.append(th)
    return out


def gridRun(workers=8):
    "T4 step 4: the coarse grid (96 distinct points), chooseKnob, then the winner's fine grid (121 points)."
    from explRL.b3_cells import FIT_CELLS, claudeRows, claudeTargets, grid
    from explRL.b3_fit import chooseKnob, gridSim
    from explRL.b3_plan import B3_PLAN
    assert B3_PLAN['frozen'], 'freeze and push B3_PLAN before the week-1 fit (FR-D5, NFR-7)'
    t0, T = time.time(), claudeTargets(claudeRows())
    sims = gridSim(FIT_CELLS, _coarse(), workers)
    print(f'coarse: {len(sims)} points, {gridSim.new} new boards, {time.time() - t0:.0f} s')
    k, tot = chooseKnob(sims, T)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'choose.json').write_text(json.dumps(dict(knob=k, heldOutLoss=tot), indent=1, sort_keys=True) + '\n')
    sims = gridSim(FIT_CELLS, grid(('trustOne', k), 'fine'), workers)
    print(f'chose {k} {tot}; fine: {gridSim.new} new boards, {time.time() - t0:.0f} s')


def fitRun(workers=8):
    "T4 step 5: heldOut per fold (all three candidates on the coarse grid; the winner on its fine grid too), the fit on all"
    "cells and on all minus C1's reused cells, bootTau and fitHealth -> results/multiagent/b3/fit.json."
    from explRL.b3_cells import CANDIDATES, FIT_CELLS, REUSED, claudeRows, claudeTargets, grid
    from explRL.b3_fit import bootTau, fit, fitHealth, gridSim, heldOut, loss, onKnobs
    k = json.loads((OUT / 'choose.json').read_text())['knob']
    rows = claudeRows()
    T = claudeTargets(rows)
    coarse = gridSim(FIT_CELLS, _coarse(), workers)
    sims = {**coarse, **gridSim(FIT_CELLS, grid(('trustOne', k), 'fine'), workers)}
    assert gridSim.new == 0, 'run grid first'
    held = {c: {f: heldOut(f, onKnobs(coarse, ('trustOne', c)), T) for f in ('S1', 'S4', 'S4b', 'P14')} for c in CANDIDATES}
    sub, ids = onKnobs(sims, ('trustOne', k)), list(T)
    fine = {f: heldOut(f, sub, T) for f in ('S1', 'S4', 'S4b', 'P14')}
    fits = {'all': fit(ids, sub, T), 'allC1': fit(ids, sub, T, REUSED['C1']), **{f: fine[f]['theta'] for f in fine}}
    keep = [c for c in ids if c not in REUSED['C1']]
    tau = bootTau(keep, sub, rows, knobs=('trustOne', k))
    tauBy = {c: tau if c == k else bootTau(keep, onKnobs(coarse, ('trustOne', c)), rows, knobs=('trustOne', c)) for c in CANDIDATES}
    health = fitHealth({n: th for n, th in fits.items() if n != 'P14'}, held, ('trustOne', k), k)
    res = dict(knob=k, fits=fits, tau=tau, tauBy=tauBy, heldOut=dict(coarse=held, fine=fine), health=health,
               loss=dict(all=loss(fits['all'], ids, sub, T), default=loss({}, ids, sub, T)))
    (OUT / 'fit.json').write_text(json.dumps(res, indent=1, sort_keys=True, default=float) + '\n')
    print(json.dumps(dict(knob=k, fits=fits, tau=tau, health=health, loss=res['loss']), indent=1, default=float))


def retroRun(workers=8):
    "T5: the retrospective check for every candidate -> results/multiagent/b3/retro.json and retro.md."
    from explRL.b3_retro import retrospective
    from explRL.b3_report import retroMarkdown
    t0, fitRes = time.time(), json.loads((OUT / 'fit.json').read_text())
    r = retrospective(fitRes, workers)
    (OUT / 'retro.json').write_text(json.dumps(r, indent=1, sort_keys=True, default=float) + '\n')
    (OUT / 'retro.md').write_text(retroMarkdown(r))
    print(json.dumps(r['summary'], indent=1, default=float), f'{time.time() - t0:.0f} s')


def forecastRun(exp, workers=8):
    """T6 (C1): θ0 fit without C1's reused cells (fit.json 'allC1'), τ, the trustOne refit on the pilot's contamination (the
    pilot cells simulated on the trustOne grid, the knob at θ0), the five lines and the simulated relays and mirror posts beside
    the pilot's -> specs/multiagent/phase20/c1_predictions.json (commit and push it; its SHA-256 goes into C1_PLAN)."""
    import numpy as np
    from explRL.b3_cells import FIT_CELLS, claudeRows, claudeTargets, grid
    from explRL.b3_effects import c1Forecast, c1PilotMap
    from explRL.b3_fit import gridSim, onKnobs, pilotScale, refit, simRow
    from explRL.bench_grid import readCSV
    assert exp == 'C1', 'C2 and C4 part b: their specs add effects, cellFn, pilotMap and reused first (P22-15)'
    fitRes = json.loads((OUT / 'fit.json').read_text())
    assert fitRes['health']['ok'] or (OUT / 'health_decision.txt').exists(), 'fit health failed: stop and ask (P22-11)'
    k, th0, tau, t0 = fitRes['knob'], fitRes['fits']['allC1'], fitRes['tau'], time.time()
    rows, pilotRows = claudeRows(), readCSV(REPO / 'results/multiagent/colony/c1pilot/runs.csv')
    T = claudeTargets(rows)
    sims = onKnobs(gridSim(FIT_CELLS, grid(('trustOne', k), 'fine'), workers), ('trustOne', k))
    pilot = c1PilotMap(pilotRows, lambda n: pilotScale(rows, 'contamination', n))
    pc = [dict(id=p['cell'], kind='c1', arm=p['cell'].split(':')[1].split('|')[0], fault='independent', N=64,
               target='contamination') for p in pilot]
    ths = [dict(th0, trustOne=v) for v in np.round(np.arange(0, 1.01, 0.1), 2)]
    psims = gridSim(pc, ths, workers)
    thp = refit(th0, tau, pilot, psims)
    cols = ('relaysPerBridgeTurn', 'mirrorPostsPerHolder')
    simB = {c['id'].split(':')[1]: {m: float(np.nanmean([simRow(c, s, thp)[m] for s in range(3000, 3030)])) for m in cols}
            for c in pc if c['arm'] != 'coupled'}
    f, sha = c1Forecast(pilotRows, root=REPO, fitFn=lambda rd: th0, tauFn=lambda th, rd: tau,
                        refitFn=lambda th, ta, p: thp, pilotBridgeSim=simB, refitTargets=pilot)
    print(f'C1 forecast: θ0 {th0}, θ_pilot {thp}, SHA-256 {sha}, {time.time() - t0:.0f} s')


def scoreRun(exp):
    """T9: score an experiment's forecast against its own estimates and intervals. C1: each effect's terms on C1's Claude rows
    (results/multiagent/colony/c1/runs.csv and reused.csv), paired on seed over its boards (1800-1807 for C1-1 and C1-2,
    1800-1804 otherwise), bootSeeds with 2,000 resamples, as c1Summaries."""
    from explRL.b3_effects import C1_EFFECTS
    from explRL.b3_forecast import estimate, scoreExperiment
    from explRL.bench_grid import readCSV
    from explRL.colony_report import bootSeeds
    assert exp == 'C1'
    D = REPO / 'results/multiagent/colony/c1'
    rows = [r for f in ('runs.csv', 'reused.csv') for r in readCSV(D / f) if r.get('runner', 'llm') == 'llm']
    obs = {}
    for e in C1_EFFECTS:
        est, lo, hi = bootSeeds(estimate(rows, e, seeds=range(1800, 1808 if e.note.startswith('boards 1800-1807') else 1805))[0])
        obs[e.id] = (est, [lo, hi])
    out = scoreExperiment(REPO / 'specs/multiagent/phase20/c1_predictions.json', obs)
    print(json.dumps(dict(common=out['common'], all=out['all']), indent=1))


if __name__ == '__main__':
    cmd, arg = sys.argv[1], sys.argv[2:]
    w = int(arg[-1]) if arg and arg[-1].isdigit() else 8
    dict(check=lambda: check(w), probe=probe, grid=lambda: gridRun(w), fit=lambda: fitRun(w), retro=lambda: retroRun(w), forecast=lambda: forecastRun(arg[0]),
         score=lambda: scoreRun(arg[0]))[cmd]()
