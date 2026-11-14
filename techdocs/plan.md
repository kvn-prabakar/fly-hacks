# Fly Dodgeball: Implementation Plan

A 3D dodgeball game where the players dodge using a real fruit fly brain (FlyWire connectome, Shiu et al. 2024 LIF model). The brain is not trained or changed. An incoming ball is fed in as a looming stimulus, and the dodge comes from the escape neurons.

Stack: Python only. numpy for the brain, Ursina for the 3D game. 3 people, 5 hours, one GitHub repo, each person driving their own Claude Code agent.

---

## 0. How to use this file (for Claude Code)

The rules for every agent live in `CLAUDE.md`, which Claude Code loads by itself. Each teammate opens Claude Code in the repo, switches to plan mode, and pastes their role's kickoff prompt.

**BRAIN kickoff**
> I am the BRAIN role on branch `brain`. Read CLAUDE.md, then plan.md sections 4.3 and 5.1. Propose your steps. Then build them one at a time, in order 1 to 8. Step 4 (sanity) must pass before you start step 5. Run anything slower than 2 minutes in the background with a log file. After each step, show me the check result and commit.

**GAME kickoff**
> I am the GAME role on branch `game`. Read CLAUDE.md, then plan.md sections 4.3 and 5.2. Propose your steps. Use `StubBrain` from `shared/stubs.py` until I tell you `TableBrain` is ready. Nothing in `game/` may import ursina. After each step, run `pytest tests/test_game.py`, show me the result and commit.

**ARENA kickoff**
> I am the ARENA role on branch `arena`. Read CLAUDE.md, then plan.md sections 4.3 and 5.3. Propose your steps. Build `--headless-check` first. Use `game.sim.Match` through its `state()` dicts only; until GAME's code lands, write a tiny fake `Match` in `arena/fake_match.py` with the same methods. You cannot see the window, so after each visual step run `--headless-check`, then ask me to run the game and describe what I see. Commit after each step.

---

## 1. The demo we are building

* A court with two teams of 3 players. **Blue = fly brain team. Red = baseline team** (random dodges, or no dodging).
* Scripted throwers on each side pick up balls and throw at the other team. Throwing and aiming are plain game logic, not brain.
* When a ball is about to reach a blue player, the game asks the fly brain what to do. The brain answers with how hard to escape and which way. The player moves, and normal collision checks decide if it was a hit.
* HUD shows hits on each team, dodge rate, and the live neuron rates for the last decision.
* **Lesion button (L key):** silence the Giant Fibre. The blue team should start getting hit a lot more. This is the "proof it's the brain" moment.

---

## 2. Repo layout

```
fly-dodgeball/
  CLAUDE.md             # agent rules, auto loaded by Claude Code
  plan.md
  README.md
  requirements.txt
  .gitignore
  shared/
    contracts.py        # dataclasses + Brain protocol (everyone, agreed in setup)
    stubs.py            # fake brain so GAME/ARENA can work before BRAIN is done
  brain/                # BRAIN role
    download_data.py    # fetch Shiu + FlyWire label files into data/
    connectome.py       # load W, build neuron groups (incl. left/right)
    lif.py              # simulate() and rate(), ported from the starter notebook
    sanity.py           # the handbook sanity checks
    build_table.py      # precompute the decision lookup table
    table_brain.py      # Brain implementation that reads the table
  game/                 # GAME role
    physics.py          # ball + player motion, collisions
    players.py          # player state machine, fly vs baseline controllers
    throwers.py         # scripted throwing / ball pickup
    threat.py           # turns ball state into ThreatInput
    sim.py              # headless game loop, runs without graphics
  arena/                # ARENA role
    scene.py            # Ursina court, entities, camera
    hud.py              # scores, neuron rate bars, lesion indicator
    main.py             # entry point: python -m arena.main
  data/                 # gitignored: parquet, csv, tsv, lookup tables
  tests/
```

---

## 3. Roles and branches

| Role | Branch | Owns | Main deliverable |
|---|---|---|---|
| BRAIN | `brain` | `brain/`, `tests/test_brain.py` | `data/table.npz` + `TableBrain` that answers in under 1 ms |
| GAME | `game` | `game/`, `tests/test_game.py` | headless game loop that runs a full match with any `Brain` |
| ARENA | `arena` | `arena/`, `tests/test_arena.py`, `README.md` | Ursina window that draws `game.sim` state and the HUD |

Everyone shares `shared/` and `requirements.txt`. Change those only on `main` after telling the team.

---

## 4. Setup (all 3 together, first 30 minutes)

### 4.1 One person (call them the setup lead)

```bash
git clone https://github.com/<org>/<repo>.git fly-dodgeball
cd fly-dodgeball
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

Create `requirements.txt`:
```
numpy
scipy
pandas
pyarrow
ursina
pytest
```

Create `.gitignore`:
```
.venv/
__pycache__/
data/
*.npz
.env
```

Copy in `CLAUDE.md` and `plan.md`. Create `shared/__init__.py`, `shared/contracts.py` and `shared/stubs.py` exactly as in section 4.3, plus empty `brain/`, `game/`, `arena/` folders each with `__init__.py`. Then:

```bash
git add .
git status                          # check nothing from data/ or .venv/
git commit -m "Project skeleton and shared contracts"
git push origin main
```

### 4.2 The other two

```bash
git clone https://github.com/<org>/<repo>.git fly-dodgeball
cd fly-dodgeball
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Then everyone makes their branch:
```bash
git checkout -b brain      # or game, or arena
git push -u origin brain
```

### 4.3 `shared/contracts.py` (agree on this before splitting up)

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class ThreatInput:
    distance: float        # metres from ball to player, now
    closing_speed: float   # m/s, how fast the gap is shrinking (>0 means approaching)
    side: float            # -1 = ball coming from player's left, +1 = right, 0 = straight on

@dataclass
class DodgeDecision:
    escape_left_hz: float   # Giant Fibre (DNp01) left rate
    escape_right_hz: float  # Giant Fibre (DNp01) right rate
    backup_hz: float        # MDN rate (walk backwards)
    forward_hz: float       # DNp09 rate (walk forwards)
    dodge_dir: float        # -1 = dodge to player's left, +1 = right
    dodge_strength: float   # 0..1, 0 = do nothing
    looming_hz_in: float    # stimulus that was applied (for HUD)

class Brain(Protocol):
    def decide(self, threat: ThreatInput, lesion: bool = False) -> DodgeDecision: ...
```

### 4.4 `shared/stubs.py` (copy exactly)

GAME and ARENA use this until BRAIN is ready.

```python
import numpy as np
from shared.contracts import ThreatInput, DodgeDecision

class StubBrain:
    """Fake brain with the same interface as TableBrain. No neurons involved."""

    def decide(self, threat: ThreatInput, lesion: bool = False) -> DodgeDecision:
        looming = float(np.clip(20 * threat.closing_speed / max(threat.distance, 0.3), 0, 200))
        strength = 0.0 if lesion else float(np.clip(looming / 150, 0, 1))
        gf = 0.0 if lesion else looming * 0.4
        left = gf * (1 - threat.side) / 2
        right = gf * (1 + threat.side) / 2
        return DodgeDecision(
            escape_left_hz=left,
            escape_right_hz=right,
            backup_hz=looming * 0.1,
            forward_hz=0.0,
            dodge_dir=1.0 if threat.side <= 0 else -1.0,   # dodge away from the ball
            dodge_strength=strength,
            looming_hz_in=looming,
        )
```

---

## 5. Role tasks

### 5.1 BRAIN

Source to port: `fly_brain_starter.ipynb` (cells 4 to 6). Settings must stay exactly as Shiu: rest −52 mV, threshold −45 mV, 20 ms membrane, 5 ms synapse, 2.2 ms refractory, 1.8 ms delay, 0.275 mV per synapse, 0.1 ms step.

1. **`download_data.py`**: save into `data/`:
   * `Completeness_783.csv` and `Connectivity_783.parquet` from `https://github.com/philshiu/Drosophila_brain_model/raw/main/`
   * `Supplemental_file1_neuron_annotations.tsv` from `https://github.com/flyconnectome/flywire_annotations/raw/main/supplemental_files/`
   No FlyWire token needed.
2. **`connectome.py`**: build sparse `W` and these groups, using `labels.side` to split by side:
   * `looming_left`, `looming_right`: `cell_type in [LC4, LPLC2]`, split by side
   * `gf_left`, `gf_right`: `cell_type == DNp01`, split by side
   * `mdn`: `cell_type == MDN`
   * `dnp09`: `cell_type == DNp09`
   * `sugar` (`LB3c`), `bitter` (`cell_sub_class == bitter`), `mn9` (root id `720575940660219265`) for sanity checks only
   Print the size of each group. If any side split is empty, stop and report.
3. **`lif.py`**: port `simulate(inputs, ms=200, W=W, seed=0)` and `rate()` as is. Add `silenced_W(group)` that cuts all **incoming** connections to that group so it can never fire: `keep = np.ones(N); keep[group] = 0; (W @ sp.diags(keep)).tocsr()` (W is presynaptic × postsynaptic, so columns are inputs). Note: cutting the Giant Fibre's *outgoing* rows would not work here, because its targets are in the nerve cord, which is not in this brain dataset, so its own rate would not change.
4. **`sanity.py`** (must pass before building anything else). Run in the background. Write every measured number to `data/sanity.txt`. One spike in 200 ms equals 5 Hz.

   | Test | Input | Pass if |
   |---|---|---|
   | silence | nothing | mn9, gf, mdn all 0 Hz, fewer than 100 neurons active |
   | feeding | sugar 200 Hz | mn9 ≥ 20 Hz (paper reports about 50) |
   | bitter veto | sugar 200 + bitter 200 | mn9 ≤ half of the feeding result |
   | escape | looming both sides 150 Hz | mean gf ≥ 5 Hz |
   | lesion | looming 150 Hz, `silenced_W(gf)` | gf = 0 Hz |
   | side test | left only 150 Hz, then right only | no pass/fail; record gf_left, gf_right, mdn, dnp09 for both runs |

   If any pass/fail test fails, stop and report the numbers. The wiring is wrong, not the idea. Write the side test result to `data/side_test.txt`, and state clearly whether gf_left and gf_right differ by more than 20%.
5. **Stimulus mapping** (put in `table_brain.py`, used by both build and runtime):
   ```
   looming_total = clip(K * closing_speed / max(distance, 0.3), 0, 200)   # Hz, start K = 20
   left_hz  = looming_total * (1 - side) / 2
   right_hz = looming_total * (1 + side) / 2
   ```
   Ball from the left (side = −1) drives the left eye's looming neurons.
6. **`build_table.py`**: grid over
   * distance: 0.5, 1, 1.5, 2, 3, 4, 6, 8 m
   * closing_speed: 2, 5, 8, 12, 16, 20 m/s
   * side: −1, −0.5, 0, 0.5, 1
   That is 240 runs, times 2 (normal and Giant Fibre silenced) = 480. Each run is about 200 ms brain time and a few seconds of CPU. Use `multiprocessing.Pool` so it finishes in about 10 to 20 minutes. Save every group rate to `data/table.npz`, plus the grid axes. Also write a small `data/table_preview.csv`.
   * Add `--small` (distance 1, 3, 8; speed 5, 15; side −1, 0, 1 → 36 runs) and build that first so GAME can integrate early.
   * Always run it in the background: `python -m brain.build_table > data/build_table.log 2>&1 &`. Print progress every 10 runs.
   * Check: in the normal half, gf for (distance 1, speed 16) is higher than for (distance 8, speed 2). In the silenced half, gf is 0 everywhere.
7. **`table_brain.py`**: `TableBrain(Brain)` loads the npz once, does trilinear interpolation, and returns a `DodgeDecision`:
   * `escape = max(escape_left_hz, escape_right_hz)`
   * `dodge_strength = max(clip(escape / ESCAPE_FULL_HZ, 0, 1), 0.3 * clip(backup_hz / BACKUP_FULL_HZ, 0, 1))`. Set both FULL constants from the normal table's 90th percentile. So with the Giant Fibre silenced the fly can still shuffle back a little through MDN, but cannot jump away.
   * `dodge_dir`: if the side test showed the left and right Giant Fibre differ, dodge away from the side that fired more. If not, dodge away from `threat.side` and say so in the README (the brain decides *whether and how hard*, geometry decides *which way*).
   * `lesion=True` reads the lesioned half of the table.
8. Hand off: push `brain`, open a PR, tell GAME the table is ready. Do **not** commit the npz; GAME and ARENA run `python -m brain.download_data && python -m brain.build_table` or get the file over Slack/Drive.

**Checks:** `python -m brain.sanity` passes. `pytest tests/test_brain.py`: `TableBrain.decide` returns in under 1 ms, strength is near 0 for a far slow ball and near 1 for a close fast ball.

### 5.2 GAME

Everything here must run **headless** (no Ursina import). Use `StubBrain` until `TableBrain` lands.

1. **`physics.py`**: units are metres and seconds. Court 20 × 10 m, centre line at x = 0. Gravity 9.8. Ball radius 0.15, player radius 0.35.
   * `step_ball(ball, dt)`: `vel.y -= g*dt; pos += vel*dt`; bounce on floor with 0.5 damping; dead after 2 bounces or leaving court.
   * `hit(ball, player)`: distance between centres < sum of radii, ball alive and thrown by the other team.
2. **`threat.py`**: `make_threat(ball, player) -> ThreatInput | None`.
   * Return `None` unless the ball is moving toward the player and its predicted closest pass (time to closest approach, miss distance) is under 1.0 s and within 1.0 m.
   * `side`: sign of the cross product between the ball's velocity and the player's facing, scaled to −1..1.
3. **`players.py`**: state machine per player: `IDLE → DODGING (0.4 s) → RECOVER → IDLE`.
   * `FlyController(brain)`: asks the brain **once per ball per player** when `make_threat` first returns non `None`. Dodge velocity = perpendicular to the ball's path, direction from `dodge_dir`, speed `MAX_DODGE_SPEED * dodge_strength` (start 6 m/s).
   * `RandomController`: same trigger, random direction, random strength.
   * `StillController`: never dodges.
   * Store the last `DodgeDecision` per player for the HUD.
4. **`throwers.py`**: each team has one ball spawner. Every 1.5 to 3 s a thrower picks a random living opponent and throws with speed 10 to 16 m/s, aimed at where the target is now plus a little noise. Arc so it lands near the target.
5. **`sim.py`**: `class Match` with `step(dt)`, `state()` (plain dicts for ARENA), `toggle_lesion()`, and counters: throws, hits, dodges per team. Fixed 60 Hz step.
6. **`python -m game.sim --matches 50`**: headless runs printing hit rate for fly vs random vs still. This is the baseline comparison for the demo.

**Checks:** `pytest tests/test_game.py`: a ball thrown straight at a still player hits; threat is `None` for a ball flying away; a match of 60 s runs without errors with `StubBrain`.

### 5.3 ARENA

1. **`scene.py`**: Ursina window. Floor plane with court lines, centre line, low walls. Players as capsules (blue team, red team), balls as spheres. `EditorCamera` or a fixed angled camera looking at the court.
2. **`main.py`**: creates `Match` (from `game.sim`) and `TableBrain` if `data/table.npz` exists, else `StubBrain` with a banner "STUB BRAIN". Each Ursina `update()` calls `match.step(time.dt)` and copies positions onto entities.
3. **`hud.py`**:
   * score panel: hits taken per team, dodge rate per team
   * neuron panel for the last blue decision: bars for looming in, GF left, GF right, MDN, DNp09
   * lesion indicator, red when Giant Fibre is silenced
   * flash the player that just dodged
4. Keys: `L` lesion toggle, `Space` pause, `R` reset match, `1/2/3` switch red team controller (random, still), `Esc` quit.
5. `README.md`: how to install, download data, build table, run.

6. **`--headless-check` flag (build this first):** start Ursina offscreen (`Ursina(window_type='offscreen')`), run 300 frames with a fixed `dt` of 1/60, assert entity count matches `match.state()`, print `OK` and exit 0. If offscreen does not work on that laptop, the flag instead runs the same 300 steps without creating a window and only checks the state to entity mapping code.

**Checks:** `python -m arena.main --headless-check` prints `OK`. Then the human runs `python -m arena.main` and confirms: court visible, 6 players, balls fly in arcs, HUD numbers change, `L` turns the lesion indicator red, about 60 fps.

---

## 6. Timeline (5 hours)

| Time | Everyone |
|---|---|
| 0:00 to 0:30 | Setup (section 4). Contracts on `main`. Branches created. BRAIN starts the data download right away. |
| 0:30 to 1:30 | Parallel work. BRAIN: steps 1 to 4. GAME: physics, threat. ARENA: scene, entities. |
| **1:30 checkpoint** | 5 minute sync. BRAIN reports sanity + side test. GAME shows headless match with stub. ARENA shows window. Merge any ready PRs. |
| 1:30 to 2:30 | BRAIN: build table (let it run), TableBrain. GAME: players, throwers, match counters. ARENA: wire `Match` into Ursina, HUD v1. |
| **2:30 checkpoint** | Merge all three into `main`. Swap stub for `TableBrain`. Play one match together. |
| 2:30 to 3:30 | Integration fixes and tuning (K, MAX_DODGE_SPEED, ESCAPE_FULL_HZ). Lesion toggle end to end. |
| 3:30 to 4:30 | Baseline numbers from `game.sim --matches 50`. HUD polish. Stretch goals if ahead. |
| 4:30 to 5:00 | **Code freeze.** Merge to `main`, tag `demo`. Rehearse a 2 minute demo: normal play, lesion on, numbers. |

---

## 7. GitHub workflow

Assumption: the team has mixed Git experience, so here are the exact steps.

**Daily loop on your branch**
```bash
git add -A
git status                         # make sure no data/ or .venv/ files
git commit -m "brain: port LIF simulate"
git push
```
Commit every 20 to 30 minutes, or whenever something works.

**Getting teammates' work**
```bash
git fetch origin
git merge origin/main              # do this at every checkpoint
```

**Opening a pull request**
1. Push your branch.
2. On GitHub: Pull requests → New pull request → base `main`, compare `brain` (your branch).
3. Short title, one line saying what works. Ask one teammate to glance at it.
4. Click **Merge**. Do not delete your branch; keep working on it and merge `main` back in.

**Merge conflicts**
* Since each role owns its own folder, conflicts should only happen in `shared/`, `requirements.txt`, or `README.md`.
* If one happens: open the file, keep both changes when it makes sense, remove the `<<<<<<<`, `=======`, `>>>>>>>` markers, then `git add <file>` and `git commit`.
* You can ask your Claude Code agent to resolve it, but read the result before committing.

**Rules**
* Only merge to `main` through PRs, except for the setup commit.
* `main` must always run (`python -m arena.main` opens with at least the stub brain).
* Big files (`data/`, `*.npz`) never go in Git. Share the table over Drive/Slack if rebuilding is too slow.

---

## 8. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Left and right Giant Fibre do not differ by side | Brain decides strength and timing, geometry picks direction. Say so honestly in the demo. |
| Table build too slow | Shrink grid (5 × 4 × 3), or run `build_table.py` on Google Colab. |
| Brain seizes (everything fires) | Check signs come from Shiu's parquet unchanged. Lower K. Do not use smell or wind inputs. |
| Ursina install problems on someone's laptop | That person works headless (`game.sim`) and the ARENA person runs the window. |
| Fly team does no better than random | Tune K and the threat trigger. Still demo the lesion contrast and report the numbers honestly. |

---

## 9. Stretch goals (only after 3:30 and `main` is stable)

1. **Catch:** a close slow ball with high DNp09 and low escape = catch instead of dodge.
2. **Brain view:** a small 3D plot of active neurons for the last decision (navis + plotly, saved as an HTML file).
3. **Male vs female brain:** rebuild the table from the Male CNS dataset and race them.
4. **Live brain mode:** call `simulate()` directly instead of the table for one player, in a background thread, to show it is the real thing.
