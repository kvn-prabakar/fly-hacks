"""Write evidence/provenance.json: what exactly the committed table is and where it came from.

    python provenance.py
"""
import hashlib
import json
import os
import pickle
import platform
import subprocess
import sys

import numpy as np
import scipy

import fly_brain as fb

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "evidence")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*a):
    try:
        return subprocess.check_output(["git", *a], cwd=HERE, text=True).strip()
    except Exception:
        return ""


def main():
    os.makedirs(OUT, exist_ok=True)
    table_path = os.path.join(HERE, "fly_table.pkl")
    with open(table_path, "rb") as f:
        d = pickle.load(f)
    grid = d["grid"]
    typ, side, roots = d["dn_type"], d["dn_side"], d["dn_root_id"]
    I, C = d["rates"]["intact"], d["rates"]["gf_cut"]
    gf = typ == "DNp01"
    sources = {}
    for name, url in (("neurons.csv", fb.SHIU + "Completeness_783.csv"),
                      ("wiring.parquet", fb.SHIU + "Connectivity_783.parquet"),
                      ("labels.tsv", fb.LABELS_URL)):
        p = os.path.join(fb.CACHE, name)
        sources[name] = {"url": url, "sha256": sha(p) if os.path.exists(p) else None,
                         "bytes": os.path.getsize(p) if os.path.exists(p) else None}
    c = fb.Connectome()
    prov = {
        "what": "Lookup table of a whole-brain fruit fly simulation (FlyWire connectome, Shiu et al. 2024 model). "
                "Every number in the table is the spike rate of a real connectome neuron, produced by fly_brain.Connectome.simulate.",
        "table": {"file": "fly-imp/fly_table.pkl", "sha256": sha(table_path), "bytes": os.path.getsize(table_path),
                  "grid_hz": grid, "brain_ms_per_run": d["ms"], "seeds": d["seeds"],
                  "runs": len(grid) ** 2 * len(d["seeds"]) * 2, "variants": list(d["rates"]),
                  "descending_neurons_stored": int(len(typ))},
        "brain": {"neurons": c.N, "connections": int(c.W.nnz), "flywire_materialization": 783,
                  "model_settings_Shiu_2024": fb.SHIU_CONSTANTS,
                  "input_groups": {"LC4+LPLC2 left": len(c.groups["loom_L"]), "LC4+LPLC2 right": len(c.groups["loom_R"])},
                  "readout_groups": {"DNp01 (Giant Fibre)": len(c.groups["giant_fibre"]), "MDN": len(c.groups["mdn"])}},
        "sources": sources,
        "checks_on_table": {
            "no_input_gives_silence": bool(I[0, 0].sum() == 0),
            "giant_fibre_rate_at_200_200_Hz": float(I[-1, -1][gf].mean()),
            "giant_fibre_max_when_silenced_Hz": float(C[:, :, gf].max()),
            "max_active_neurons_any_run": float(d["active"]["intact"].max()),
        },
        "example_rows": [
            {"left_Hz": grid[i], "right_Hz": grid[j], "variant": v,
             "giant_fibre_Hz": float((I if v == "intact" else C)[i, j][gf].mean()),
             "left_minus_right_descending_neurons_Hz": float((I if v == "intact" else C)[i, j][side == "left"].sum()
                                                             - (I if v == "intact" else C)[i, j][side == "right"].sum())}
            for v in ("intact", "gf_cut") for i, j in ((4, 0), (0, 4), (4, 4), (8, 8))],
        "first_five_descending_neuron_ids": [{"flywire_root_id": int(r), "cell_type": str(t), "side": str(s)}
                                            for r, t, s in list(zip(roots, typ, side))[:5]],
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__,
                        "platform": platform.platform()},
        "code": {"git_commit": git("rev-parse", "HEAD"), "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
                 "uncommitted_changes": bool(git("status", "--porcelain", "--", "."))},
        "caveat": "This file is a description, not proof by itself. Run verify_brain.py to re-simulate the "
                  "brain from the public Shiu et al. files and compare against the table.",
    }
    with open(os.path.join(OUT, "provenance.json"), "w", encoding="utf8") as f:
        json.dump(prov, f, indent=2)
    print("wrote evidence/provenance.json  table sha256", prov["table"]["sha256"][:16])


if __name__ == "__main__":
    main()
