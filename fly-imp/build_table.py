"""Precompute the fly brain's response to left/right looming and save fly_table.pkl.

The game looks answers up in this table instead of simulating 138k neurons live
(one run takes about 10-15 s on a laptop CPU). Two brains are tabulated:

    intact   the unmodified connectome
    gf_cut   the same brain with the Giant Fibre silenced (its incoming synapses cut)

For every (left Hz, right Hz) grid point we store the rate of every descending
neuron that responds at all, averaged over seeds.

    python build_table.py                  # full grid, both brains, 2 seeds (~10-20 min, parallel)
    python build_table.py --small          # 3x3 grid, 1 seed, quick smoke test
    python build_table.py --workers 4
"""
import argparse
import itertools
import os
import pickle
import time
from multiprocessing import Pool

import numpy as np

from fly_brain import Connectome

GRID = [0, 10, 20, 35, 50, 75, 100, 150, 200]   # Hz applied to LC4/LPLC2 on each side
SMALL = [0, 50, 200]
VARIANTS = ["intact", "gf_cut"]

_c = _W = None


def _init():
    global _c, _W
    _c = Connectome()
    _W = {"intact": _c.W, "gf_cut": _c.silenced(_c.groups["giant_fibre"])}


def _run(job):
    variant, rl, rr, seed, ms = job
    g = _c.groups
    counts = _c.simulate([(g["loom_L"], rl), (g["loom_R"], rr)], ms=ms, W=_W[variant], seed=seed)
    return job, counts[_c.dn_idx].astype(np.uint16), int((counts > 0).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", type=int, default=200, help="brain time per run")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--small", action="store_true")
    ap.add_argument("--workers", type=int, default=min(8, max(1, (os.cpu_count() or 2) // 2)))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "fly_table.pkl"))
    args = ap.parse_args()
    grid = SMALL if args.small else GRID
    seeds = [0] if args.small else list(range(args.seeds))

    c = Connectome()                       # also downloads the data once, before workers start
    g = c.groups
    print({k: len(v) for k, v in g.items()}, "descending:", len(c.dn_idx), flush=True)
    for k in ("loom_L", "loom_R", "gf_L", "gf_R", "mdn"):
        assert len(g[k]), f"neuron group {k} is empty"

    jobs = [(v, rl, rr, s, args.ms) for v in VARIANTS for rl, rr in itertools.product(grid, grid) for s in seeds]
    print(f"{len(jobs)} runs on {args.workers} workers", flush=True)
    G, n_dn = len(grid), len(c.dn_idx)
    acc = {v: np.zeros((G, G, n_dn)) for v in VARIANTS}
    active = {v: np.zeros((G, G)) for v in VARIANTS}
    t0 = time.time()
    with Pool(args.workers, initializer=_init) as pool:
        for n, (job, dn_counts, n_active) in enumerate(pool.imap_unordered(_run, jobs), 1):
            v, rl, rr, _, _ = job
            i, j = grid.index(rl), grid.index(rr)
            acc[v][i, j] += dn_counts / (args.ms / 1000) / len(seeds)
            active[v][i, j] += n_active / len(seeds)
            if n % 10 == 0 or n == len(jobs):
                print(f"[{n}/{len(jobs)}] {time.time() - t0:.0f}s", flush=True)

    # --- sanity checks: if these fail the wiring is wrong, so do not save a table ---
    is_gf = c.dn_type == "DNp01"
    gf = {v: acc[v][:, :, is_gf].mean(-1) for v in VARIANTS}
    assert acc["intact"][0, 0].sum() == 0 and active["intact"][0, 0] == 0, "no input must give silence"
    assert gf["intact"][-1, -1] > 0, "looming must make the Giant Fibre fire"
    assert gf["gf_cut"].max() == 0, "the silenced Giant Fibre must never fire"
    assert active["intact"].max() < 5000, "runaway activity: the brain seized"
    print("sanity checks passed", flush=True)

    keep = (acc["intact"].reshape(-1, n_dn).max(0) > 0) | (acc["gf_cut"].reshape(-1, n_dn).max(0) > 0)
    out = {
        "grid": grid, "ms": args.ms, "seeds": seeds,
        "dn_type": c.dn_type[keep], "dn_side": c.dn_side[keep],
        "dn_root_id": c.neurons.index.to_numpy()[c.dn_idx][keep],
        "rates": {v: acc[v][:, :, keep].astype(np.float32) for v in VARIANTS},   # [left, right, neuron] Hz
        "active": active,
    }
    with open(args.out, "wb") as f:
        pickle.dump(out, f)
    print(f"saved {args.out}: {int(keep.sum())} responsive descending neurons, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
