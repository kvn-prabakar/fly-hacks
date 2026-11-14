"""Headless comparison: same random ball stream, different dodge policies.

    python test_sim.py
"""
import sys

from sim import Brain, World

SECONDS, DT = 180, 1 / 60
SEEDS = [0, 1, 2]

brain = Brain()
print("brain:", "REAL connectome table" if brain.real else "PLACEHOLDER (run build_table.py for the real one)")

policies = [("fly", False, "fly (brain)"), ("fly", True, "fly, Giant Fibre lesioned"),
            ("dumb", False, "dumb distance rule"), ("none", False, "never dodges")]
print(f"{SECONDS}s per run, {len(SEEDS)} seeds (same spawn timing and edges per seed; aim follows the fly)\n")
print(f"{'policy':28s} {'hits':>6s} {'dodged':>7s} {'close':>6s} {'jumps':>6s}")
for pol, lesion, name in policies:
    tot = dict(hits=0, dodged=0, close=0, jumps=0)
    for s in SEEDS:
        w = World(brain=brain, policy=pol, seed=s, lesion=lesion)
        for _ in range(int(SECONDS / DT)):
            w.step(DT)
        for k in tot:
            tot[k] += w.stats[k]
    print(f"{name:28s} {tot['hits']:6d} {tot['dodged']:7d} {tot['close']:6d} {tot['jumps']:6d}")
