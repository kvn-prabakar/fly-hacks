"""Connectome side of the fly: load Shiu et al. wiring + FlyWire labels, and simulate().

Adapted from the hack-day notebook. Files are downloaded once into ./cache.
Model settings are Shiu et al. 2024 and must not be tuned.
"""
import os
import urllib.request

import numpy as np
import pandas as pd
import scipy.sparse as sp

SHIU = "https://github.com/philshiu/Drosophila_brain_model/raw/main/"
LABELS_URL = (
    "https://github.com/flyconnectome/flywire_annotations/raw/main/"
    "supplemental_files/Supplemental_file1_neuron_annotations.tsv"
)
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def _fetch(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print(f"downloading {name} ...", flush=True)
        urllib.request.urlretrieve(url, path + ".part")
        os.replace(path + ".part", path)
    return path


class Connectome:
    def __init__(self):
        self.neurons = pd.read_csv(_fetch(SHIU + "Completeness_783.csv", "neurons.csv"), index_col=0)
        wiring = pd.read_parquet(_fetch(SHIU + "Connectivity_783.parquet", "wiring.parquet"))
        self.labels = pd.read_csv(_fetch(LABELS_URL, "labels.tsv"), sep="\t", low_memory=False)
        self.N = len(self.neurons)
        # W[pre, post] = signed synapse count (+ excites, - inhibits)
        self.W = sp.csr_matrix(
            (wiring["Excitatory x Connectivity"],
             (wiring["Presynaptic_Index"], wiring["Postsynaptic_Index"])),
            shape=(self.N, self.N),
        )
        self.row = {r: i for i, r in enumerate(self.neurons.index)}

        L = self.labels
        loom = L.cell_type.isin(["LC4", "LPLC2"])
        gf = L.cell_type == "DNp01"
        mdn = L.cell_type == "MDN"
        self.groups = {
            "loom_L": self.find(loom & (L.side == "left")),
            "loom_R": self.find(loom & (L.side == "right")),
            "gf_L": self.find(gf & (L.side == "left")),
            "gf_R": self.find(gf & (L.side == "right")),
            "giant_fibre": self.find(gf),
            "mdn": self.find(mdn),
        }
        # Every descending neuron (the brain-to-body command lines), with type and side.
        dn = L[(L.super_class == "descending") & L.root_id.isin(self.row)].drop_duplicates("root_id")
        self.dn_idx = np.array([self.row[r] for r in dn.root_id])
        self.dn_type = dn.cell_type.fillna("?").to_numpy(str)
        self.dn_side = dn.side.fillna("").to_numpy(str)

    def find(self, mask):
        return np.array([self.row[r] for r in self.labels.root_id[mask] if r in self.row])

    def silenced(self, group):
        """Copy of W in which `group` can never fire: all its INCOMING synapses are cut.

        (Cutting a neuron's outgoing synapses would leave its own firing unchanged.)
        """
        keep = np.ones(self.N)
        keep[group] = 0.0
        return (self.W @ sp.diags(keep)).tocsr()

    def simulate(self, inputs, ms=200, W=None, seed=0):
        """inputs: [(neuron_idx_array, rate_hz), ...] -> spike count per neuron.
        Shiu et al. 2024 leaky integrate-and-fire settings."""
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
        """Average spikes/second of a neuron group."""
        if len(group) == 0:
            return 0.0
        return counts[group].sum() / len(group) / (ms / 1000)
