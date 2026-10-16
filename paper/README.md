# Preprint: From Diagnosis to Fixes

Draft (2026-10-16). Sources: `main.tex`, `references.bib`, `numbers.tex` (generated), `figures/` (generated).

- Regenerate every number and figure from the saved results (repo root): `.venv/bin/python paper/make_assets.py`. The text uses only the macros in `numbers.tex`, so no result is typed by hand.
- Build: no LaTeX toolchain on the Mac yet. Either `brew install tectonic && tectonic paper/main.tex`, or upload `paper/` to Overleaf. For the NeurIPS look, add `neurips_2026.sty` (official style file) to this folder; without it the draft uses a plain layout.
- Pending: Section 5's Phase 13 RL results (Colab runs), and the external-benchmark replication suggested in `specs/multiagent/LITERATURE.md` section 14.
- Citations were checked against each paper's own page on 2026-10-16 (see the literature review).
