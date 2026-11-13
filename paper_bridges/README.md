# Preprint: Bridges Between Squads

*Moving Information Across Team Boundaries Without Moving the Lies*, by Chuntao Dan and Claude Opus 5.5 (Anthropic). Started 2026-11-12. It covers the work after the first preprint (`paper/`): squads on coupled work, C1 (Phase 20), C1b (Phase 23), C1c (Phase 24) and C1d (Phase 25), and the forecasts recorded before each run (B3, Phase 22, and the hand-recorded calls).

- Status: draft complete (2026-11-12). C1-C1d are written; C1d's text is conditional (`\ifCOneD` in `numbers.tex`), switched on by `results/multiagent/colony/c1d/summary.json`. Not yet submitted anywhere.
- Regenerate every number and the figure from the saved results (repo root): `.venv/bin/python paper_bridges/make_assets.py`, then build with `tectonic paper_bridges/main.tex`. The text uses only the macros in `numbers.tex`, so no result is typed by hand.
- Citations: reused from `paper/references.bib` (checked 2026-10-16 and 2026-10-23); one new entry, Tushman and Scanlan (1981), checked against its Crossref record (DOI 10.2307/255825) on 2026-11-12; it is cited only for the existence of boundary-spanning roles (Crossref has no abstract).
- Authorship: as `paper/README.md`; check the venue's policy on AI authors before a submission.
