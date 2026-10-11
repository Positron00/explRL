#!/usr/bin/env python3
"""Save golden Phase 5 regression fixtures from the pre-Phase-5 training loops.

Run once, on the old code (for example a git worktree of the commit before Phase 5,
with that worktree first on PYTHONPATH). Refuses to overwrite existing files.
Every field of every returned history is saved, with its dtype, plus final weights.
"""
from dataclasses import fields
from math import pi
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'nbs' / 'fixtures' / 'phase5'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _cols(prefix, history):
    "All fields of a history dataclass, keyed as prefix + field name."
    return {prefix + f.name: getattr(history, f.name) for f in fields(history)}


def _save(name, arrays):
    path = OUT / name
    if path.exists():
        sys.exit(f'refuse to overwrite {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    print(f'wrote {path}')


def flexible():
    from explRL.core import loadAgent, loadEnv
    from explRL.train import train_agent
    ag = loadAgent(seed=0)
    h = train_agent(ag, loadEnv(), Ttot=2.0)
    _save('flexible.npz', {**_cols('', h), 'omega': ag.policy.omega})


def prestructured():
    from explRL.core import loadEnv, loadPrestructuredAgent
    from explRL.prestructured_train import train_prestructured
    env = loadEnv(goal=pi)
    ag0 = loadPrestructuredAgent(seed=0)
    h0 = train_prestructured(ag0, env, Ttot=240)
    ag1 = loadPrestructuredAgent(seed=1, learn=False, thetaG0=pi)
    h1 = train_prestructured(ag1, env, Ttot=240)
    _save('prestructured.npz', {**_cols('learn_', h0), 'learn_thetaG_end': ag0.policy.thetaG,
                                **_cols('fixed_', h1), 'fixed_thetaG_end': ag1.policy.thetaG})


def circuit():
    from explRL.core import loadCircuitAgent
    from explRL.envs import ZoneArena
    from explRL.circuit_train import train_circuit, probe
    env = ZoneArena(symmetric=True)
    ag = loadCircuitAgent(seed=0)
    h0 = train_circuit(ag, env, Ttot=300)
    h1 = train_circuit(ag, env, Ttot=200, t0=500)
    pr = probe(ag, env, T=60, seed=7)
    _save('circuit.npz', {**_cols('seg0_', h0), **_cols('seg1_', h1), **_cols('probe_', pr['history']),
                          'wG': ag.policy.wG, 'wC': ag.policy.wC,
                          'probe_PI': pr['PI'], 'probe_jumpRate': pr['jumpRate']})


if __name__ == '__main__':
    flexible()
    prestructured()
    circuit()
