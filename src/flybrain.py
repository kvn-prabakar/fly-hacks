"""Fly brain simulation helpers (ported from the hackday starter notebook).

Model: leaky integrate-and-fire, settings from Shiu et al. 2024.
No FlyWire token is needed for anything in this file.

    from flybrain import load_brain
    brain = load_brain()
    sugar = brain.find(brain.labels.cell_type == "LB3c")
    counts = brain.simulate([(sugar, 200)])
    brain.rate(counts, brain.mn9)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

SHIU = "https://github.com/philshiu/Drosophila_brain_model/raw/main/"
LABELS_URL = ("https://github.com/flyconnectome/flywire_annotations/raw/main/"
              "supplemental_files/Supplemental_file1_neuron_annotations.tsv")
MN9_ID = 720575940660219265  # not in the label file; ID from Shiu et al. 2024

CACHE = Path(__file__).resolve().parent.parent / "data"  # gitignored


def _cached(name, loader):
    """Download once, then reuse a local copy (keeps repeated runs fast)."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if path.exists():
        return pd.read_pickle(path)
    df = loader()
    df.to_pickle(path)
    return df


class Brain:
    def __init__(self, neurons, wiring, labels):
        self.neurons, self.labels = neurons, labels
        self.N = len(neurons)
        self.W = sp.csr_matrix(
            (wiring["Excitatory x Connectivity"],
             (wiring["Presynaptic_Index"], wiring["Postsynaptic_Index"])),
            shape=(self.N, self.N))
        self.row = {root_id: i for i, root_id in enumerate(neurons.index)}

        # Default neuron groups (see handbook for more)
        L = labels
        self.sugar = self.find(L.cell_type == "LB3c")
        self.bitter = self.find(L.cell_sub_class == "bitter")
        self.looming = self.find(L.cell_type.isin(["LC4", "LPLC2"]))
        self.giant_fibre = self.find(L.cell_type == "DNp01")
        self.mdn = self.find(L.cell_type == "MDN")
        self.mn9 = np.array([self.row[MN9_ID]])

    def find(self, mask):
        """Neurons matching a label filter -> their row numbers in W."""
        return np.array([self.row[r] for r in self.labels.root_id[mask]
                         if r in self.row])

    def lesion(self, group):
        """Copy of W where `group` still fires but nothing hears it."""
        keep = np.ones(self.N)
        keep[group] = 0
        return (sp.diags(keep) @ self.W).tocsr()

    def simulate(self, inputs, ms=200, W=None, seed=0):
        """inputs: [(neuron_indices, rate_hz), ...] -> spike count per neuron."""
        W = self.W if W is None else W
        N = self.N
        dt, v0, vth, tm, ts, ref = 0.1, -52.0, -45.0, 20.0, 5.0, 2.2
        wsyn, kick, delay = 0.275, 250 * 0.275, int(1.8 / 0.1)
        rng = np.random.default_rng(seed)
        v, g = np.full(N, v0), np.zeros(N)
        last, counts = np.full(N, -1e9), np.zeros(N, int)
        driven = np.zeros(N, bool)
        for idx, _ in inputs:
            driven[idx] = True
        ring = np.zeros((delay, N))
        for k in range(int(ms / dt)):
            t, slot = k * dt, k % delay
            g += ring[slot]
            ring[slot] = 0
            free = ((t - last) > ref) | driven
            v[free] += dt * (v0 - v[free] + g[free]) / tm
            g[free] *= np.exp(-dt / ts)
            for idx, hz in inputs:
                v[idx[rng.random(len(idx)) < hz * dt / 1000]] += kick
            s = np.flatnonzero(v > vth)
            v[s], g[s], last[s] = v0, 0.0, t
            counts[s] += 1
            if len(s):
                ring[slot] += np.asarray(W[s].sum(0)).ravel() * wsyn
        return counts

    @staticmethod
    def rate(counts, group, ms=200):
        """Average spikes per second of a group."""
        return counts[group].sum() / len(group) / (ms / 1000)


def load_brain():
    neurons = _cached("neurons.pkl", lambda: pd.read_csv(SHIU + "Completeness_783.csv", index_col=0))
    wiring = _cached("wiring.pkl", lambda: pd.read_parquet(SHIU + "Connectivity_783.parquet"))
    labels = _cached("labels.pkl", lambda: pd.read_csv(LABELS_URL, sep="\t", low_memory=False))
    return Brain(neurons, wiring, labels)
