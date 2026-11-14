Python Ursina Fly Dodgeball simulation

NumPy is used

## Fly brain setup

Built on a simulated fruit fly brain (FlyWire connectome, 139k neurons, Shiu et al. 2024 integrate-and-fire model).

### Layout
- `notebooks/fly_brain_starter.ipynb`: original hackday notebook (runs in Colab)
- `docs/Fly-Brain-Handbook.docx`: ideas, gotchas, resource links
- `src/flybrain.py`: reusable `load_brain()` / `simulate()` / `rate()` / `lesion()`
- `src/sanity_check.py`: handbook sanity checks

### Setup (local)
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python src/sanity_check.py    # first run downloads data into data/ (gitignored)
```

Optional 3D viewer / FlyWire API: `pip install -r requirements-viz.txt` (best on Python 3.10/3.11 or Colab).
FlyWire token: https://global.daf-apis.com/auth/api/v1/create_token. Never commit it.

### Usage
```python
import sys; sys.path.insert(0, "src")
from flybrain import load_brain
b = load_brain()
counts = b.simulate([(b.sugar, 200)])
b.rate(counts, b.mn9)   # eat
```
