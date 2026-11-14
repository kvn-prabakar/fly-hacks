# Evidence that the fly brain is used

The fly's decisions in `fly-imp/` come from a simulation of a real fruit fly brain: the FlyWire
connectome (138,639 neurons, about 15 million signed connections) run with the Shiu et al. 2024
leaky integrate-and-fire settings, unchanged. One brain run takes 10 to 15 s, so the game reads a
table of results that was computed ahead of time (`fly_table.pkl`). These files let anyone check that.

| File | What it shows |
|---|---|
| `provenance.json` | Exactly what the table is: sha256, grid, seeds, number of runs, the Shiu constants, the public source files with their sha256, sanity checks, versions, git commit. |
| `verification.json` | Result of `verify_brain.py`: the brain was re-simulated from scratch at 4 grid points x 2 seeds and compared against the table, neuron by neuron. |
| `episode_trace.jsonl` | One 40 s game. Every decision tick in which a ball was visible: what each eye saw, what the brain returned (Giant Fibre, MDN, left/right descending neurons), and what the fly did. The first line carries the table's sha256. |
| `eval_results.txt` | The hit-rate comparison (brain, Giant Fibre silenced, blind eyes, baselines) quoted in the README. |

## Why these files matter, and what they do not prove

A JSON file can be written by anyone, so `provenance.json` on its own proves nothing. The proof is that
you can reproduce it:

```bash
cd fly-imp
python verify_brain.py        # about 1 to 2 minutes on 8 cores; downloads the public Shiu files once
```

It re-runs the full-brain simulation from the public wiring files and exits 0 only if every descending
neuron's rate matches the table (our run: 8 runs, maximum difference 0.0000 Hz). If someone replaced the
table with a made-up rule, this check fails.

The game also prints the first 8 characters of the table's sha256 in its HUD
(`REAL connectome table #97ebd9a4`), so what you see on screen can be matched to `provenance.json`.

What this does not show: that the simulated fly behaves like a living one. The brain model is the published
Shiu et al. 2024 one; what we add is how a ball becomes input and how output becomes a jump, both described
in the main README.

## Rebuilding everything

```bash
python build_table.py         # about 20 min on 10 cores, rewrites fly_table.pkl
python provenance.py          # rewrites evidence/provenance.json
python verify_brain.py        # rewrites evidence/verification.json
python trace_episode.py       # rewrites evidence/episode_trace.jsonl
python test_sim.py            # the hit-rate comparison
```
