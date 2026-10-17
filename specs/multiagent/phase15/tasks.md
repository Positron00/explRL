# Tasks: Phase 15

Status (2026-10-17): T1 and T2 done (offline; `liar_trace` 186 lines, `liar_grid` 130, `liar_report` 181; one clean Haiku cell replayed from cache with the cache-only client matched Phase 14's row and 320 turn-log lines exactly). Next: T3 (freeze `TRACE_PLAN`, then the full traces, $0).

Rules as Phase 14 (notebook first, export, one notebook per test call, modules under 200 lines, offline tests without `anthropic` or `torch`; Phase 5-14 cached reruns byte-identical). Gates: no full trace (numpy or Haiku) before `TRACE_PLAN` is frozen and committed; Parts A-C spend nothing (cache-only client); no Part D LLM cell before its forecast is committed and the user approves.

## T1. Tracer, cache-only client, variants
- **Files**: `nbs/liar_trace.ipynb` (design: the tracer, the cache-only client, the variants).
- **Tests**: AC-2 (traced = untraced rows and logs, numpy and fake LLM, with and without liars; known clues equal `known`; the cache-only client replays hits and raises on a miss); AC-5 (`variant=None` byte-identical on the forecast cells; each variant on a hand-made board).

## T2. Grids, plan, measures, accounting, demo
- **Files**: `nbs/liar_grid.ipynb`, `nbs/liar_report.ipynb`, `nbs/demo_liar.ipynb`.
- **Tests**: grid sizes and keys (`traceGrid` equals Phase 14's baseline cells; `forecastCells()` equals the forecast's); AC-3 (M1-M6 and the eight terms on hand-made traces; the exact sum; `nChange` equals the forecast rule); the quick demo with the fake client.

## T3. Freeze and trace (offline, $0)
- **What**: freeze `TRACE_PLAN`, commit, record the commit and hash in the README; trace the 30 Haiku cells (cache-only) and the numpy cells; check AC-4; accounting and variants; results in the README.
- **Done when**: AC-4, AC-6 (Parts A-C).

## T4. Part D (optional, live, about $3.20)
- **What**: only if a variant passes H15-4 and the user approves: pick the variant (FR-D2), write and commit its forecast, run `liarShareGrid`, cached rerun, score.
- **Done when**: AC-6 (Part D).

## T5. Docs and preprints
- **What**: README results, `REPORT.md` Phase 15 section, the multi-agent plan's status, the preprints where a claim changes.
- **Done when**: docs updated; all checks pass.
