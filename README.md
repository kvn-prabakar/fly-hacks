# Fly Dodgeball

A 3D dodgeball game where the blue team dodges using a real fruit fly brain (FlyWire connectome, Shiu et al. 2024 LIF model).

## Installation

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

## Data Download

```bash
python -m src.flybrain  # downloads connectome data to data/
```

## Brain Sanity Check

```bash
python src/sanity_check.py
```

## Build Decision Table (for TableBrain)

```bash
# Small grid for testing (36 runs, ~2 min)
python -m brain.build_table --small

# Full grid (480 runs, ~10-20 min)
python -m brain.build_table
```

## Run the Game

### Arena (visual)
```bash
python -m arena.main
```

### Headless simulation
```bash
python -m game.sim --matches 50
```

### Headless check (for CI)
```bash
python -m arena.main --headless-check
```

## Controls

- `L` - Toggle Giant Fibre lesion
- `Space` - Pause/unpause
- `R` - Reset match
- `1` - Red team: Random controller
- `2` - Red team: Still controller
- `3` - Red team: Fly brain controller (requires table)
- `Esc` - Quit

## Project Structure

```
fly-hacks/
├── src/
│   ├── flybrain.py       # Fly brain simulation (Shiu et al. 2024)
│   └── sanity_check.py   # Sanity checks
├── brain/                # BRAIN role (table building)
│   ├── download_data.py
│   ├── connectome.py
│   ├── lif.py
│   ├── sanity.py
│   ├── build_table.py
│   └── table_brain.py
├── game/                 # GAME role (headless simulation)
│   ├── physics.py
│   ├── players.py
│   ├── throwers.py
│   ├── threat.py
│   └── sim.py
├── arena/                # ARENA role (Ursina visualization)
│   ├── scene.py
│   ├── hud.py
│   ├── main.py
│   └── fake_match.py
├── shared/               # Shared contracts
│   ├── contracts.py
│   └── stubs.py
├── data/                 # Gitignored: parquet, csv, lookup tables
└── tests/
```

## References

- Shiu et al. 2024: "A complete model of the Drosophila brain"
- FlyWire connectome
- FlyWire annotations