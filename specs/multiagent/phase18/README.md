# Plan: Phase 18 (stub), learning like animals: few trials, from memory and from teammates

Status: **stub** (2026-10-18): an idea, not a plan. To be written after Phase 17. Part of the multi-agent plan: [../README.md](../README.md).

## The question

Animals learn useful behaviour from a handful of trials. Our RL needs thousands of games. Which mechanisms behind animals' sample efficiency carry over to teams of language-model agents, and do any of them beat simply spending more compute (the Bitter Lesson test)?

## Candidate directions (to be narrowed by a literature scan)

| Animal finding | Machine-learning counterpart | Possible experiment |
|---|---|---|
| Hippocampal replay of past experience | several updates per batch; replay buffers | already a Phase 17 pilot option (`epochs`); here: off-policy replay across steps |
| Prefrontal cortex as a meta-learner (Wang et al., 2018, Nature Neuroscience) | in-context or meta-RL: learning within and across episodes from memory | train agents whose notes or lessons carry learning across games; measure few-game adaptation to a new board or a new liar |
| Social and observational learning | learning from teammates' rewarded actions | agents learn from what worked for others on the shared board (in context, or as an auxiliary training signal) |
| Strong priors shaped by evolution | pretraining; the imitation warm start | (covered) |

The social-learning row is the most specific to multi-agent systems.

## To decide when written

Literature scan (neuroscience and meta-RL); which one direction; its environment change (for example, a changing board or liar between games); metrics (games to criterion); a compute-matched baseline (the same compute spent on plain RL).
