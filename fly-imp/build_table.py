"""Precompute the fly's response to left/right looming and save fly_table.pkl.

Run once (a Colab T4 or a few minutes on a laptop). The game then looks the
answer up instead of simulating 138k neurons every frame.

    python build_table.py              # default grid
    python build_table.py --ms 100     # shorter runs
"""
import argparse
import itertools
import pickle
import time

from fly_brain import Connectome

GRID = [0, 10, 20, 35, 50, 75, 100, 150, 200]  # Hz applied to LC4/LPLC2

ap = argparse.ArgumentParser()
ap.add_argument("--ms", type=int, default=150, help="brain time per run (handbook: 100-200)")
ap.add_argument("--out", default="fly_table.pkl")
args = ap.parse_args()

c = Connectome()
g = c.groups
print({k: len(v) for k, v in g.items()})

# --- sanity checks from the handbook: if these fail, the wiring is wrong ---
quiet = c.simulate([], ms=args.ms)
assert quiet.sum() == 0, "no input should give silence"
loom = c.simulate([(g["loom_L"], 150), (g["loom_R"], 150)], ms=args.ms)
assert c.rate(loom, g["giant_fibre"], args.ms) > 0, "looming should make the Giant Fibre fire"
print("sanity checks passed")

table = {}
t0 = time.time()
pairs = list(itertools.product(GRID, GRID))
for n, (rl, rr) in enumerate(pairs, 1):
    counts = c.simulate([(g["loom_L"], rl), (g["loom_R"], rr)], ms=args.ms)
    table[(rl, rr)] = {
        "gf": c.rate(counts, g["giant_fibre"], args.ms),
        "gf_L": c.rate(counts, g["gf_L"], args.ms),
        "gf_R": c.rate(counts, g["gf_R"], args.ms),
        "mdn": c.rate(counts, g["mdn"], args.ms),
    }
    print(f"[{n}/{len(pairs)}] L={rl:3d} R={rr:3d} -> {table[(rl, rr)]}  ({time.time() - t0:.0f}s)")

with open(args.out, "wb") as f:
    pickle.dump({"grid": GRID, "ms": args.ms, "table": table}, f)
print("saved", args.out)
