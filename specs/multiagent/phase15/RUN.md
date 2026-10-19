# Running Phase 15 (the mechanism behind liar damage at scale)

Plan, decisions and results: [README.md](README.md). Builds on Phase 14: [../phase14/RUN.md](../phase14/RUN.md).

Status 2026-10-17: T3 done (full traces in 29 s, $0, AC-4 held); T4 (Part D) not run: no variant passed H15-4.

## Tests

From the repo root (`.venv/bin` first on `PATH`), one notebook per command; none needs a network, a key, `anthropic` or `torch`:

| Command | What it checks | Time |
|---------|----------------|------|
| `nbdev-test --n-workers 0 nbs/liar_trace.ipynb` | traced runs equal untraced ones (numpy, fake LLM, with and without liars); known clues equal `known`; the cache-only client; variants (AC-2, AC-5) | ~5 s |
| `nbdev-test --n-workers 0 nbs/liar_grid.ipynb` | grid sizes and keys against Phase 14's cells and the forecast's | ~2 s |
| `nbdev-test --n-workers 0 nbs/liar_report.ipynb` | M1-M6 and the eight accounting terms on hand-made traces; exact sum; `nChange` equals the forecast rule (AC-3) | ~3 s |
| `nbdev-test --n-workers 0 nbs/demo_liar.ipynb` | quick: fake client and numpy, end to end | ~15 s |
| `nbdev-test --n-workers 0` | full suite | ~90 s |

## Runs, in order

| Step | Where | Command | Cost |
|------|-------|---------|------|
| T3 freeze | Mac | `TRACE_PLAN['frozen'] = True` in `nbs/liar_grid.ipynb`, export, commit (the full section checks both files are committed); record the commit and `coopHash(TRACE_PLAN)` in the README | none |
| T3 traces | Mac | `nbdev-test --n-workers 0 --cell-timeout 0 --flags llm nbs/demo_liar.ipynb`: replays the 30 Haiku cells with the cache-only client (no key, no network; stops on any miss), traces the numpy cells, runs the accounting and the variants, writes the report; the Part D section is skipped unless `EXPLRL_PHASE15_D=1` | $0 |
| T4 Part D (optional) | Mac | after approval: the demo's Part D forecast cell (numpy, seconds) writes `specs/multiagent/phase15/liar_predictions.json`; commit it; then `EXPLRL_LLM_LIVE=1 EXPLRL_PHASE15_D=1` with the same command (the section checks the forecast is committed, runs the cells, reruns them from cache and scores the forecast) | about $3.20 |

## Artifacts

- `results/multiagent/liar/{quick,full}/`: `trace_summary.json`, `accounting.csv`, `variants.json`, `report.md`, `liar.png`; `full/traces/` (all of `results/multiagent/` is git-ignored); `trace_summary.json` and `variants.json` copied to this folder with the results.
- Optional `results/multiagent/liarD/`: `runs.csv`, per-run turn logs in `turns/`, `score.json`; `specs/multiagent/phase15/liar_predictions.json`.

## Summary figure (Phases 13-15)

`python tools/scale_figure.py $PWD` -> `results/multiagent/report/trust_scale.png`: the public track record's share of liars' damage recovered and the request board's pooling gap closed against team size (Phases 13-14), and the share of honest answers built on a false clue, Claude Haiku against rule agents (Phase 15). Reads the saved results only.
