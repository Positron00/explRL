# Companion preprint: Simulate First?

*What Cheap Rule-Agent Worlds Predict About Teams of Language-Model Agents*, by Chuntao Dan and Claude Opus 5.5 (Anthropic). Revised 2026-10-23, and on 2026-10-26 with the 32-agent forecast. What hand-built numpy worlds, not fitted to any language model, predicted before each expensive run, scored against the five findings of the companion paper (`paper/`): the confirmatory simulation tests of Phases 8-9, the transfer of harness rankings to Claude Haiku teams (Phases 10-11), and the frozen forecasts of the defences (Phase 18), the team-size trends (Phases 14-15) and the reward designs (Phase 13).

- Regenerate figures and numbers (repo root): `.venv/bin/python tools/figures.py .` then `.venv/bin/python paper2/make_assets.py`; build: `tectonic paper2/main.tex`. The layout is the NeurIPS 2025 style (`neurips_2025.sty`, `preprint` option).
- Structure: Introduction, Methods (the simulations and their LLM counterparts, forecasts and scoring, statistics), Results (one subsection per finding), Discussion (when the simulation transfers, a practical workflow, future directions, limitations) and author contributions.
- Authorship: as for `paper/` (check the venue's policy on AI authors before a submission).
- Citations re-checked on 2026-10-23 against each source's own record (arXiv, Crossref, publisher); fixed then: the Itkin author name and the authors of Anthropic's research-system post.
- Next step for this paper: a hybrid simulation that adds the behaviours the forecasts missed, fitted from a cheap LLM pilot, and a test of the perception-memory explanation of the foraging failure.
