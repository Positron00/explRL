"T6 regression gate (Phase 20): every earlier live colony board replayed through the cache-only client ($0; a miss raises CacheMiss), every saved column equal; then the 16 reused C1 cells with C1's columns. Run without EXPLRL_LLM_LIVE: `.venv/bin/python tools/c1_regression.py`."
import sys, time
from explRL.bench_grid import readCSV
from explRL.colony_grid import colonyPilotGrid, stage1Grid
from explRL.colony32 import stage32Grid
from explRL.colony3 import stage3Grid, stage3PilotGrid
from explRL.colony64 import stage64Grid, stage64PilotGrid
from explRL.colony4 import stage4Grid, stage4PilotGrid
from explRL.colony4b import stage4bGrid, stage4bPilotGrid
from explRL.colony_mech import replayCheck, _diff, _key, stage4Columns
from explRL.colony_trace import replay
from explRL.liar_trace import cacheOnlyClient
from explRL.llm_runs import LLMConfig
from explRL.clue_runs import cellRow
from explRL.bridge_grid import reusedCells20
from explRL.bridge_mech import reusedRows20
from explRL.train import demo_artifact_dir

COLONY, CACHE = 'multiagent/colony', str(demo_artifact_dir(None, 'multiagent/llm') / 'cache')

def check4(cells, rows):
    idx, bad, n = {_key(r): r for r in rows}, [], 0
    for c in cells:
        if _key(c) in idx:
            cfg = LLMConfig.fromDict(c['cfg'])
            row = cellRow(c, cfg, stage4Columns(cfg, replay(cfg, c['seed'], cacheOnlyClient(cfg, CACHE))))
            d = _diff(idx[_key(c)], row); n += 1
            if d: bad.append((_key(c), d[:5]))
    return dict(checked=n, mismatches=bad)

total, t0 = 0, time.time()
for mode, cells, fn in (('pilot', colonyPilotGrid(), replayCheck), ('stage1', stage1Grid(), replayCheck), ('stage32', stage32Grid(), replayCheck),
                        ('stage3pilot', stage3PilotGrid(), replayCheck), ('stage3', stage3Grid(), replayCheck),
                        ('stage64pilot', stage64PilotGrid(), replayCheck), ('stage64', stage64Grid(), replayCheck),
                        ('stage4pilot', stage4PilotGrid(), None), ('stage4', stage4Grid(), None),
                        ('stage4bpilot', stage4bPilotGrid(), None), ('stage4b', stage4bGrid(), None)):
    f = demo_artifact_dir(mode, COLONY) / 'runs.csv'
    if not f.exists():
        print(f'{mode}: no live run'); continue
    rows = readCSV(f)
    chk = replayCheck(cells, rows, CACHE) if fn else check4(cells, rows)
    total += chk['checked']
    print(f"{mode}: {chk['checked']} replayed, mismatches {chk['mismatches'][:3]}", flush=True)
    assert not chk['mismatches'], mode
prior = readCSV(demo_artifact_dir('stage4', COLONY) / 'runs.csv') + readCSV(demo_artifact_dir('stage64', COLONY) / 'runs.csv')
r20 = reusedRows20(lambda cfg: cacheOnlyClient(cfg, CACHE), prior, reusedCells20())
print(f'reusedRows20: {len(r20)} rows, earlier columns equal, C1 columns added ({sum(1 for k in r20[0] if k.startswith("mirror"))} mirror cols)')
print(f'TOTAL {total} boards replayed + {len(r20)} reused, {time.time()-t0:.0f}s')
