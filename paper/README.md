# Preprint: From Diagnosis to Fixes

Draft (2026-10-16). Sources: `main.tex`, `references.bib`, `numbers.tex` (generated), `figures/` (generated).

- Regenerate every number and figure from the saved results (repo root): `.venv/bin/python paper/make_assets.py`. The text uses only the macros in `numbers.tex`, so no result is typed by hand.
- Build alternatives: upload `paper/` to Overleaf. For the NeurIPS look, add `neurips_2026.sty` (official style file) to this folder; without it the draft uses a plain layout.
- Done: the Phase 13 RL results (Section 5), the scored numpy forecast (Appendix B), the HiddenBench replication of the vote arms (Section 4.4). Open: the liar fixes on an established misinformation benchmark; a HiddenBench-protocol baseline (to explain our high baseline); `neurips_2026.sty` for the conference layout.
- Build: `tectonic paper/main.tex` (installed 2026-10-16).
- Citations were checked against each paper's own page on 2026-10-16 (see the literature review).
