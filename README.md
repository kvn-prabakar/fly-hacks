# Fly Dodgeball Simulation

A 2D arcade-style simulation where a fruit fly dodges rolling balls using a **real simulated connectome** (139k neurons from the FlyWire project, Shiu et al. 2024). The fly's escape decisions come from a precomputed lookup table built from the actual fly brain wiring.

---

## Quick Start (Windows)

```bash
cd fly-imp

# 1. Create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional but recommended) Build the connectome lookup table
#    This downloads ~200 MB of data and takes 2–5 min on a laptop.
#    Without it, the game uses a placeholder rule.
python build_table.py

# 4. Play!
python game.py
```

---

## Controls

| Key | Action |
|-----|--------|
| `1` | **Fly brain** — use the real connectome table (or placeholder) |
| `2` | **Dumb distance rule** — dodge if a ball gets too close |
| `3` | **Never dodges** — the fly just wanders |
| `L` | **Lesion the Giant Fibre** — disables the fast escape pathway |
| `R` | Reset the simulation |
| `SPACE` | Pause / unpause |
| `+` / `-` | Increase / decrease ball spawn rate |
| **Click** (in arena) | Throw a ball at the clicked position |
| `ESC` | Quit |

---

## What's Happening Under the Hood

### The Brain (`fly_brain.py`)
- Downloads the **Shiu et al. 2024** fly connectome (783 neuron types, ~2M synapses) and **FlyWire** cell-type labels.
- Runs a **leaky integrate-and-fire** simulation (1 ms timestep, 150 ms per trial).
- Input: looming-sensitive neurons (`LC4`, `LPLC2`) driven at specified Hz.
- Output: firing rates of the **Giant Fibre (DNp01)** and **MDN** (moonwalker descending neuron).

### The Lookup Table (`build_table.py`)
- Precomputes the brain's response for a grid of left/right looming frequencies (0–200 Hz).
- Saves `fly_table.pkl` — a tiny dict the game loads instantly.
- **Run this once** for the real brain behavior. Without it, a heuristic placeholder is used.

### The World (`sim.py`)
- 2D top-down arena (16×10 units). Balls spawn from edges and roll toward the fly with friction.
- **Vision model**: each eye computes angular expansion rate (looming) from every ball → Hz drive.
- **Decision loop** (20 Hz): queries the brain table → if Giant Fibre fires → instant sideways dodge; if MDN fires → backward "moonwalk".
- Policies: `fly` (connectome), `dumb` (distance threshold), `none` (no dodge).

### The Viewer (`game.py`)
- Built with **pygame** (60 FPS rendering, 120 Hz physics).
- Shows the fly (with animated wings/legs), balls, looming drive per eye (HUD bars), and Giant Fibre / MDN output rates.
- Visual feedback: eye glow = looming drive; white ring = dodge cooldown; particles on hit/jump.

---

## Running Headless Tests

```bash
# Compare policies over 180s × 3 seeds (same ball streams)
python test_sim.py
```

Output example:
```
policy                         hits dodged close jumps
fly (brain)                     12    145    23    87
fly, Giant Fibre lesioned       45    112    31    12
dumb distance rule              28    129    29    64
never dodges                   189     0    12     0
```

---

## Project Structure

```
fly-hacks/
├── README.md              # this file
├── requirements.txt       # root deps (not used by fly-imp)
├── requirements-viz.txt   # optional 3D viz deps
└── fly-imp/               # ← the game lives here
    ├── requirements.txt   # numpy, scipy, pandas, pyarrow, pygame
    ├── fly_brain.py       # connectome download + simulation
    ├── build_table.py     # precompute fly_table.pkl
    ├── sim.py             # headless world + brain lookup
    ├── game.py            # pygame viewer
    ├── test_sim.py        # policy comparison script
    ├── cache/             # downloaded connectome data (gitignored)
    └── fly_table.pkl      # generated lookup table (gitignored)
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: pygame` | `pip install pygame` (ensure you're in `.venv`) |
| `FileNotFoundError: fly_table.pkl` | Run `python build_table.py` first |
| Download fails in `fly_brain.py` | Check internet; files are cached in `fly-imp/cache/` |
| Game runs slowly | The placeholder brain is fast; the real table is instant. Ensure `fly_table.pkl` exists. |
| `pyarrow` install fails on Windows | `pip install --only-binary :all: pyarrow` or use `conda install -c conda-forge pyarrow` |

---

## References

- **Connectome**: Shiu et al., *Nature* (2024) — *A connectome of the adult Drosophila central brain*
- **FlyWire annotations**: FlyWire Consortium — supplemental neuron type labels
- **Model**: Leaky integrate-and-fire parameters from the Shiu et al. handbook

---

## License

MIT