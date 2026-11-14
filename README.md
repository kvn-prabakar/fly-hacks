# Fly Dodgeball Simulation

A 2D arcade-style simulation where a fruit fly dodges rolling balls using a **real simulated connectome** (139k neurons from the FlyWire project, Shiu et al. 2024). When the fly escapes and to which side are both read from a lookup table that was precomputed by simulating the actual fly brain wiring. The brain is never trained or changed.

---

## Quick Start (Windows)

```bash
cd fly-imp

# 1. Create & activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Play! The real-brain lookup table (fly_table.pkl) is already in the repo.
python game.py

# Optional: rebuild the table from the connectome yourself.
# Downloads ~130 MB once, then runs 324 brain simulations in parallel (about 20 min on 10 cores).
python build_table.py
```

---

## Controls

| Key | Action |
|-----|--------|
| `1` | **Fly brain**: the brain decides when to escape and to which side |
| `2` | **Dumb distance rule**: no brain, dodge if a ball gets too close |
| `3` | **Never dodges**: the fly just wanders |
| `4` | **Brain timing + geometry aim**: the brain decides when, the game aims the jump |
| `L` | **Silence the Giant Fibre**: switches to the brain simulated without its escape neuron |
| `B` | **Blind an eye**: cycles none, left, right |
| `R` | Reset the simulation |
| `SPACE` | Pause / unpause |
| `+` / `-` | Increase / decrease ball spawn rate |
| **Click** (in arena) | Throw a ball at the clicked position |
| `ESC` | Quit |

---

## What's Happening Under the Hood

### The Brain (`fly_brain.py`)
- Downloads the **Shiu et al. 2024** whole-brain model wiring (FlyWire v783: 138,639 neurons, about 15 million signed connections) and the **FlyWire** cell-type labels. No token needed.
- Runs the **leaky integrate-and-fire** simulation with Shiu's settings unchanged (0.1 ms step, 200 ms per run).
- Input: the looming-sensitive visual neurons (`LC4`, `LPLC2`) of the left and right eye, driven at a chosen rate.
- Output: spike rates of every descending neuron (the brain-to-body command lines).

### The Lookup Table (`build_table.py`)
- One brain run takes 10 to 15 s on a laptop, so the brain cannot run live. Instead it is simulated ahead of time for a 9 x 9 grid of left/right looming rates (0 to 200 Hz), two seeds each.
- It is built twice: for the **intact** brain, and for the brain with the **Giant Fibre silenced** (its incoming synapses cut, so it can never fire).
- Checks before saving: no input gives silence, looming fires the Giant Fibre, the silenced Giant Fibre stays at 0 Hz, and no runaway activity.
- Saves `fly_table.pkl` (about 180 KB, committed). The game interpolates it, so a decision takes microseconds and is still the real brain's answer.

### The World (`sim.py`)
- 2D top-down arena (16×10 units). Balls spawn from edges and roll toward the fly with friction.
- **Vision**: each ball's angular expansion rate (looming) becomes a drive in Hz, split between the left and right eye by which side the ball is on. That pair of numbers is all the fly sees.
- **Decision loop** (20 Hz), policy `fly`. Everything the fly does about a ball is read from the brain table:
  - **When to escape**: the Giant Fibre (`DNp01`) fires at least one spike. All-or-none, like the real one.
  - **Which way**: the other descending neurons come in left/right pairs. If the left copies are more active, the threat is on the left and the fly jumps right, and vice versa.
  - **Otherwise**: if `MDN` (the walk-backwards command) is firing, it walks backwards.
- The brain only knows left versus right, so it cannot aim as well as geometry can. Policy `fly_geo` (key `4`) shows the difference: same brain timing, but the game aims the jump off the ball's path.
- Body limits that are game rules, not brain: jump speed and duration, not jumping into a wall, wandering when nothing is coming.
- Policies: `fly`, `fly_geo`, `dumb` (distance threshold + geometry, no brain), `none`.

### The Viewer (`game.py`)
- Built with **pygame** (60 FPS rendering, 120 Hz physics).
- Shows the fly (with animated wings/legs), balls, looming drive per eye (HUD bars), and Giant Fibre / MDN output rates.
- Visual feedback: eye glow = looming drive; white ring = dodge cooldown; particles on hit/jump.

---

## Running Headless Tests

```bash
# Compare policies over 180 s x 12 seeds (same ball streams)
python test_sim.py
```

Measured with the committed table (hit % = balls that hit the fly / balls thrown, mean over 12 seeds with a 95% interval):

| Policy | Hit % | Hits from left / right |
|---|---|---|
| Fly brain (when and which side) | 11.6 ± 1.5 | 108 / 138 |
| Fly brain, Giant Fibre silenced | 31.5 ± 2.5 | 311 / 356 |
| Fly brain, left eye blind | 17.2 ± 2.2 | 266 / 95 |
| Fly brain, right eye blind | 17.8 ± 1.7 | 91 / 284 |
| Brain says when, geometry aims | 5.2 ± 0.8 | 52 / 58 |
| No brain: distance rule + geometry | 6.7 ± 1.7 | 63 / 78 |
| Never dodges | 26.8 ± 1.5 | 287 / 280 |

What this shows:
- The brain-driven fly is hit less than half as often as a fly that never dodges.
- Silencing the Giant Fibre removes the escape entirely (0 jumps).
- A blind eye gets the fly hit from its blind side.
- The brain's left/right aim is worse than exact geometry, because left versus right is all it knows.

The one tuned constant is `THETA_MIN` in `sim.py` (how fast a ball must be expanding before the looming cells respond). It was chosen on seeds 100 to 107; the table above uses seeds 0 to 11.

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
    ├── build_table.py     # precompute fly_table.pkl (intact + Giant Fibre silenced)
    ├── sim.py             # headless world + brain lookup
    ├── game.py            # pygame viewer
    ├── test_sim.py        # policy comparison script
    ├── cache/             # downloaded connectome data (gitignored)
    └── fly_table.pkl      # the real-brain lookup table (committed, about 180 KB)
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: pygame` | `pip install pygame` (ensure you're in `.venv`) |
| HUD says `PLACEHOLDER table` | `fly_table.pkl` is missing. Restore it with `git checkout fly-imp/fly_table.pkl` or run `python build_table.py` |
| Download fails in `fly_brain.py` | Check internet; files are cached in `fly-imp/cache/` |
| `pyarrow` install fails on Windows | `pip install --only-binary :all: pyarrow` or use `conda install -c conda-forge pyarrow` |

---

## References

- **Brain model**: Shiu et al., *Nature* (2024), *A Drosophila computational brain model reveals sensorimotor processing*
- **FlyWire annotations**: FlyWire Consortium — supplemental neuron type labels
- **Model settings**: leaky integrate-and-fire parameters from Shiu et al., used unchanged

---

## License

MIT