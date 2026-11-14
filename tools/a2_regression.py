"T5 regression gate (Phase 21, NFR-1): Phase 14's scaleB boards replayed through the cache-only client ($0; a miss raises CacheMiss), every saved column equal, and the P2 originals at seeds 900-904 among them. Stage 3 and the other colony boards: tools/c1_regression.py. Run without EXPLRL_LLM_LIVE: `.venv/bin/python tools/a2_regression.py`."
import time
from explRL.a2_grid import P2_CACHED, p2Grid
from explRL.bench_grid import readCSV
from explRL.clue_runs import runClue
from explRL.colony_mech import _diff
from explRL.fix_grid import requestKey
from explRL.liar_trace import cacheOnlyClient
from explRL.llm_runs import LLMConfig, cellRow
from explRL.scale_grid import scaleGrid
from explRL.train import demo_artifact_dir

CACHE = str(demo_artifact_dir(None, 'multiagent/llm') / 'cache')
key = lambda r: (str(r['level']), int(float(r['N'])), int(float(r['seed'])))
t0, rows = time.time(), {key(r): r for r in readCSV(demo_artifact_dir('full', 'multiagent/scale') / 'runs.csv') if r['study'] == 'scaleB'}
cells = [c for c in scaleGrid() if (c['level'], c['N'], c['seed']) in rows]
bad = []
for c in cells:
    cfg = LLMConfig.fromDict(c['cfg'])
    row = cellRow(c, cfg, runClue(cfg, c['seed'], cacheOnlyClient(cfg, CACHE))[0][0])
    d = _diff(rows[(c['level'], c['N'], c['seed'])], row)
    if d:
        bad.append(((c['level'], c['N'], c['seed']), d[:5]))
orig = {requestKey(c) for c in p2Grid() if c['study'] == 'scaleB' and c['seed'] in P2_CACHED}
assert orig <= {requestKey(c) for c in cells}, 'a P2 original is not among the replayed scaleB boards'
print(f'scaleB: {len(cells)} of {len(scaleGrid())} replayed, mismatches {bad[:3]}; P2 originals 900-904 ({len(orig)}) among them; {time.time() - t0:.0f}s')
assert not bad
