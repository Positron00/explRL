# Summary page

The one-page summary of the multi-agent work ([published page](https://claude.ai/artifact/XvSxHA7f54LfDpZQ7PknKd); private until shared from its Share menu). This folder is its only source:

- `agent-teams-summary.html`: the page, edited by hand.
- `guards_scale.png`, `guards.png`, `trust_scale.png`, `incentives.png`: its four figures, drawn here by `python tools/figures.py .` from the saved results (mean ± SEM, an asterisk at p < 0.05, the guards-and-squads legend with each design's trend over team size).

To update the page, edit the HTML or redraw the figures, then publish this folder with the Artifact tool: `file_path` `docs/summary/agent-teams-summary.html`, the four figures as `files`, and the page's URL as `url`, so the link stays the same.
