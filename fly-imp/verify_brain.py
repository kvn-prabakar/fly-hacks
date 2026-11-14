"""Independent check that fly_table.pkl really is the fly brain.

Re-simulates a few table entries from scratch with the full 138,639-neuron model (public Shiu
et al. wiring files), then compares every descending neuron's rate with what the table holds.

    python verify_brain.py              # 4 grid points, both seeds (about 1-2 min on 8 cores)
    python verify_brain.py --workers 4

Writes evidence/verification.json. Exit code 0 only if every checked rate matches.
"""
import argparse
import datetime
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np

import fly_brain as fb

HERE = os.path.dirname(os.path.abspath(__file__))
POINTS = [("intact", 50, 50), ("intact", 200, 0), ("intact", 0, 200), ("gf_cut", 100, 100)]
_c = _W = None


def _init():
    global _c, _W
    _c = fb.Connectome()
    _W = {"intact": _c.W, "gf_cut": _c.silenced(_c.groups["giant_fibre"])}


def _run(job):
    variant, rl, rr, seed, ms = job
    g = _c.groups
    counts = _c.simulate([(g["loom_L"], rl), (g["loom_R"], rr)], ms=ms, W=_W[variant], seed=seed)
    return job, counts[_c.dn_idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 2))
    args = ap.parse_args()
    with open(os.path.join(HERE, "fly_table.pkl"), "rb") as f:
        d = pickle.load(f)
    grid, ms, seeds = list(d["grid"]), d["ms"], d["seeds"]
    c = fb.Connectome()                                   # downloads the public files if needed
    root_of_dn = c.neurons.index.to_numpy()[c.dn_idx]
    pos = {int(r): k for k, r in enumerate(root_of_dn)}
    stored = {int(r): k for k, r in enumerate(d["dn_root_id"])}
    jobs = [(v, rl, rr, s, ms) for v, rl, rr in POINTS for s in seeds]
    t0 = time.time()
    print(f"re-simulating {len(jobs)} runs ({len(POINTS)} grid points x {len(seeds)} seeds) on {args.workers} workers ...", flush=True)
    sums = {p: np.zeros(len(root_of_dn)) for p in POINTS}
    with Pool(args.workers, initializer=_init) as pool:
        for (v, rl, rr, s, _), counts in pool.imap_unordered(_run, jobs):
            sums[(v, rl, rr)] += counts / (ms / 1000) / len(seeds)

    results, ok = [], True
    for v, rl, rr in POINTS:
        fresh = sums[(v, rl, rr)]
        i, j = grid.index(rl), grid.index(rr)
        table = np.zeros(len(root_of_dn))
        for r, k in stored.items():
            table[pos[r]] = d["rates"][v][i, j, k]
        diff = np.abs(fresh - table)
        gf = c.dn_type == "DNp01"
        row = {"variant": v, "left_Hz": rl, "right_Hz": rr,
               "descending_neurons_compared": int(len(fresh)),
               "neurons_firing_in_fresh_run": int((fresh > 0).sum()),
               "max_abs_difference_Hz": float(diff.max()),
               "table_giant_fibre_Hz": float(table[gf].mean()),
               "fresh_giant_fibre_Hz": float(fresh[gf].mean()),
               "match": bool(diff.max() < 0.01)}
        ok &= row["match"]
        results.append(row)
        print(f"  {v:7s} L={rl:3d} R={rr:3d}  Giant Fibre table {row['table_giant_fibre_Hz']:6.1f} Hz  "
              f"fresh {row['fresh_giant_fibre_Hz']:6.1f} Hz  max diff {row['max_abs_difference_Hz']:.4f} Hz  "
              f"{'MATCH' if row['match'] else 'MISMATCH'}", flush=True)

    out = {"verified_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "method": "Re-ran the full-brain simulation (fly_brain.Connectome.simulate, Shiu et al. 2024 settings, "
                     "public wiring files) with the table's own seeds and compared every descending neuron's rate.",
           "all_match": bool(ok), "seconds": round(time.time() - t0), "python": sys.version.split()[0],
           "numpy": np.__version__, "results": results}
    os.makedirs(os.path.join(HERE, "evidence"), exist_ok=True)
    with open(os.path.join(HERE, "evidence", "verification.json"), "w", encoding="utf8") as f:
        json.dump(out, f, indent=2)
    print("ALL MATCH" if ok else "MISMATCH: the table is not what the brain produces", f"({out['seconds']}s)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
