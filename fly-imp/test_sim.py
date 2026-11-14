"""Headless comparison: same random ball stream, different dodge policies.

    python test_sim.py                # 12 seeds x 180 s
    python test_sim.py --seeds 20
"""
import argparse

import numpy as np

from sim import Brain, World

ap = argparse.ArgumentParser()
ap.add_argument("--seeds", type=int, default=12)
ap.add_argument("--seconds", type=int, default=180)
ap.add_argument("--table", default=None, help="path to a table file (default: fly_table.pkl)")
args = ap.parse_args()
DT = 1 / 60

brain = Brain(args.table)
print("brain:", "REAL connectome table" if brain.real else "PLACEHOLDER (run build_table.py for the real one)")

# (policy, lesion, blind eye, label)
RUNS = [
    ("fly", False, None, "fly brain (when and which side)"),
    ("fly", True, None, "fly brain, Giant Fibre silenced"),
    ("fly", False, "L", "fly brain, left eye blind"),
    ("fly", False, "R", "fly brain, right eye blind"),
    ("fly_geo", False, None, "brain says when, geometry aims"),
    ("dumb", False, None, "no brain: distance rule + geometry"),
    ("none", False, None, "never dodges"),
]
print(f"{args.seconds}s per run, {args.seeds} seeds (same spawn timing and edges per seed; aim follows the fly)\n")
print(f"{'policy':40s} {'hit %':>12s} {'hits':>5s} {'from L':>6s} {'from R':>6s} {'dodged':>7s} {'jumps':>6s}")
for pol, lesion, blind, name in RUNS:
    tot = dict(hits=0, hits_L=0, hits_R=0, dodged=0, close=0, jumps=0)
    frac = []
    for s in range(args.seeds):
        w = World(brain=brain, policy=pol, seed=s, lesion=lesion, blind=blind)
        for _ in range(int(args.seconds / DT)):
            w.step(DT)
        for k in tot:
            tot[k] += w.stats[k]
        frac.append(w.stats["hits"] / max(1, w.stats["hits"] + w.stats["dodged"]))
    m, se = 100 * np.mean(frac), 100 * np.std(frac, ddof=1) / np.sqrt(len(frac)) if len(frac) > 1 else 0.0
    print(f"{name:40s} {m:6.1f} +/-{1.96 * se:4.1f} {tot['hits']:5d} {tot['hits_L']:6d} {tot['hits_R']:6d} "
          f"{tot['dodged']:7d} {tot['jumps']:6d}")
print("\nhit % = balls that hit the fly / balls thrown, mean over seeds +/- 95% interval")
