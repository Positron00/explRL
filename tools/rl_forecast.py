"""Numpy forecast of the LLM RL arms (Phase 13, specs/multiagent/phase13/forecast.md): rule agents on the clue board with two learned choices (share a shareable clue;
guess on an undetermined subtask, per candidate bucket), trained by group-relative policy gradient under the RL arms'
rewards, from a warm start that imitates the rule agent. Usage: python tools/rl_forecast.py <repo> <out.json> [training seeds, default 0,1,2,3,4] [steps, default 60]"""
import json
import sys
from dataclasses import dataclass, field

import numpy as np


def setup(repo):
    sys.path.insert(0, repo)


BUCKETS = (2, 3, 6, 99)          # candidates <= 2, <= 3, <= 6, more


def bucket(c):
    return next(k for k, b in enumerate(BUCKETS) if c <= b)


def sig(x):
    return 1 / (1 + np.exp(-x))


@dataclass
class Policy:
    share: float = 2.2             # warm start: shares a shareable clue 90% of the time (the teacher always does)
    guess: list = field(default_factory=lambda: [-2.2] * len(BUCKETS))   # and guesses 10% of the time (the teacher never)

    def vec(self):
        return np.array([self.share, *self.guess])

    @staticmethod
    def of(v):
        return Policy(float(v[0]), [float(x) for x in v[1:]])


def makeAgent(RuleAgent, known, candidates):
    class PolicyAgent(RuleAgent):
        "The rule agent with the share and guess decisions drawn from a policy; logs (param index, taken, p, turn)."
        def __init__(self, channel, rng, pol):
            super().__init__(channel, rng, share='always', guess=0.0)
            self.pol, self.dec, self.rew, self.t = pol, [], [], 0

        def choose(self, b, t):
            kn, k = known(self.id, b, self.channel), b.opened[self.id]
            if k in b.open and len(c := candidates(b, k, kn[k])) == 1:
                b.noteSubmit(self.id, 1)
                return ('submit', c[0])
            act = self._shareable(b, kn, t)
            if act is not None:
                p = sig(self.pol.share)
                took = self.rng.random() < p
                self.dec.append((0, took, p, self.t))
                if took:
                    return act
            live = [x for x in b.open if b.tasks[x].expire > t + 1] or list(b.open)
            best = max(len(kn[x]) for x in live)
            top = [x for x in live if len(kn[x]) == best]
            top = [x for x in top if b.tasks[x].value == max(b.tasks[y].value for y in top)]
            if k not in top:
                return ('open', int(top[int(self.rng.integers(len(top)))]))
            c = candidates(b, k, kn[k])
            q = 1 + bucket(len(c))
            p = sig(self.pol.guess[q - 1])
            took = self.rng.random() < p
            self.dec.append((q, took, p, self.t))
            if took:
                b.noteSubmit(self.id, len(c))
                return ('submit', int(c[int(self.rng.integers(len(c)))]))
            return ('wait', None)

        def event(self, world, t):
            out = super().event(world, t)
            self.rew.append(float(out.reward))
            self.t += 1
            return out
    return PolicyAgent


def play(env, pol, seed, scheme, turns, rngSeed, N=4):
    "One board: -> (board, agents) after `turns` turns per agent, blackboard channel."
    b = env['Board'](seed, N, **env['kw'], scheme=scheme)
    ch = env['ClueBoard']()
    rngs = env['spawnRngs'](rngSeed, N)
    agents = [env['Agent'](ch, rngs[i], pol) for i in range(N)]
    env['runTurns'](agents, b, turns)
    return b, agents


def advantages(group, wrongPenalty, mode):
    "group: [(board, agents)] of one seed -> per board, agent, turn: advantage (board mode: one per board and agent)."
    G, N = len(group), len(group[0][1])
    R = []                          # per board, agent: per-turn training rewards
    for b, ags in group:
        wrong = {(s[1], s[0]) for s in b.submits if s[4] == 'wrong'}
        R.append([[r - wrongPenalty * ((i, float(t)) in wrong) for t, r in enumerate(a.rew)] for i, a in enumerate(ags)])
    out = [[None] * N for _ in range(G)]
    for i in range(N):
        if mode == 'board':
            ret = np.array([sum(R[g][i]) + group[g][0].pending[i] for g in range(G)])
            a = (ret - ret.mean()) / (ret.std() + 1e-6) if ret.std() > 1e-9 else np.zeros(G)
            for g in range(G):
                out[g][i] = [a[g]] * len(R[g][i])
        else:
            togo = [np.cumsum(R[g][i][::-1])[::-1] + group[g][0].pending[i] for g in range(G)]
            T = max(len(x) for x in togo)
            for g in range(G):
                out[g][i] = [0.0] * len(togo[g])
            for n in range(T):
                have = [g for g in range(G) if n < len(togo[g])]
                v = np.array([togo[g][n] for g in have])
                if v.std() > 1e-9:
                    for g, x in zip(have, v):
                        out[g][i][n] = float((x - v.mean()) / (v.std() + 1e-6))
    return out


def train(env, arm, trainSeed, steps=60, seedsPerStep=8, group=4, turns=10, lr=0.05):
    "Policy gradient (Adam) on the two decisions; -> the policy after `steps` steps."
    v = Policy().vec()
    m1, m2 = np.zeros_like(v), np.zeros_like(v)
    for s in range(steps):
        pol, grad = Policy.of(v), np.zeros_like(v)
        n = 0
        for j in range(seedsPerStep):
            seed = 10000 + 1000 * trainSeed + s * seedsPerStep + j
            grp = [play(env, pol, seed, arm['scheme'], turns, [trainSeed, s, j, g]) for g in range(group)]
            adv = advantages(grp, arm['wrongPenalty'], arm['advantage'])
            for g, (_, ags) in enumerate(grp):
                for i, a in enumerate(ags):
                    for q, took, p, t in a.dec:
                        A = adv[g][i][min(t, len(adv[g][i]) - 1)]
                        grad[q] += A * (float(took) - p)
                        n += 1
        grad /= max(n, 1)
        m1, m2 = 0.9 * m1 + 0.1 * grad, 0.999 * m2 + 0.001 * grad ** 2
        mh, vh = m1 / (1 - 0.9 ** (s + 1)), m2 / (1 - 0.999 ** (s + 1))
        v = v + lr * mh / (np.sqrt(vh) + 1e-8)
    return Policy.of(v)


def evaluate(env, pol, seeds, reps=4, turns=40):
    "Welfare per agent-turn, shares per held clue and the solo share on the evaluation boards (scheme irrelevant)."
    out = []
    for sd in seeds:
        for r in range(reps):
            b, ags = play(env, pol, sd, 'individual', turns, [sd, 99, r])
            T = turns
            row = env['metrics'](b, ags, T)
            out.append(dict(seed=sd, rep=r, **row))
    return out


def metrics(b, ags, T, N=4):
    "As the LLM evaluation: welfare per agent-turn and sharePerHeld (clueMetrics), soloShare and wrongPerSolve (coopMetrics)."
    held = sum(len(hs) for s in b.tasks.values() for hs in s.holders)
    solved, wrong = b.counts['solved'], b.counts['wrong']
    solo = sum(1 for s in b.submits if s[4] == 'solved' and s[3] is not None and s[3] > 1)
    nan = float('nan')
    return dict(welfare=float(b.netByAgent().sum()) / (N * T), sharePerHeld=b.counts['shares'] / held if held else nan,
                soloShare=solo / solved if solved else nan, wrongPerSolve=wrong / solved if solved else nan)


ARMS = dict(warm=None,
            individual=dict(scheme='individual', wrongPenalty=0.0, advantage='board'),
            team=dict(scheme='team', wrongPenalty=0.0, advantage='board'),
            credit=dict(scheme='credit', wrongPenalty=0.0, advantage='board'),
            indpen=dict(scheme='individual', wrongPenalty=2.5, advantage='board'),
            credturn=dict(scheme='credit', wrongPenalty=2.5, advantage='turn'))
EVAL_SEEDS = list(range(900, 905)) + list(range(930, 940))


def main():
    repo, out = sys.argv[1], sys.argv[2]
    setup(repo)
    from explRL.clue_agents import ClueBoard, RuleAgent, candidates, known
    from explRL.clue_grid import BOARD, CLUE_SETTINGS
    from explRL.clueboard import ClueBoardEnv
    from explRL.llm_agent import runTurns
    from explRL.multi import spawnRngs
    env = dict(Board=ClueBoardEnv, ClueBoard=ClueBoard, spawnRngs=spawnRngs, runTurns=runTurns, metrics=metrics,
               kw={k: CLUE_SETTINGS[k] for k in BOARD}, Agent=makeAgent(RuleAgent, known, candidates))
    seeds = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [0, 1, 2, 3, 4]
    steps = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    res = dict(warm=dict(policy=Policy().__dict__, eval=evaluate(env, Policy(), EVAL_SEEDS)))
    for name, arm in ARMS.items():
        if arm is None:
            continue
        for ts in seeds:
            pol = train(env, arm, ts, steps=steps)
            res[f'{name}_s{ts + 1}'] = dict(policy=pol.__dict__, eval=evaluate(env, pol, EVAL_SEEDS))
            print(name, ts + 1, 'share p %.2f' % sig(pol.share), 'guess p', np.round(sig(np.array(pol.guess)), 2), flush=True)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
