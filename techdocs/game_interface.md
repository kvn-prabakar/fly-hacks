# GAME interface (for the ARENA agent)

`game/` is implemented and headless. Do not import anything from it except `game.sim.Match`. Never edit `game/`; if you need a change, leave a `TODO(game)` and tell your human.

## Use

```python
from game.sim import Match
from shared.stubs import StubBrain      # or brain.table_brain.TableBrain if data/table.npz exists

match = Match(brain=StubBrain(), blue="fly", red="random", seed=0)
match.step(dt)          # call once per frame with time.dt (internal physics is fine with 1/60)
match.toggle_lesion()   # L key
s = match.state()       # plain dicts, safe to read every frame
```

`blue` is `"fly"`, `"random"` or `"still"`. `red` is `"random"`, `"still"` or `"fly"`. The default for the demo is `blue="fly", red="random"`.

## `state()` shape

```python
{
  "time": float, "lesion": bool,
  "balls":   [{"id": int, "pos": [x, y, z], "team": "blue"|"red"}],   # team = thrower; count changes every frame
  "players": [{"id": int, "team": "blue"|"red", "pos": [x, y, z],
               "state": "IDLE"|"DODGING"|"RECOVER", "dodging": bool,
               "decision": None | {escape_left_hz, escape_right_hz, backup_hz,
                                   forward_hz, dodge_dir, dodge_strength, looming_hz_in}}],
  "stats": {"blue": {"throws", "hits", "dodges", "threats"}, "red": {...}},
}
```

* Always 6 players, ids 0-2 blue and 3-5 red, in fixed order. Create those entities once and update positions.
* Balls spawn and die, so create, move and destroy ball entities by `id`. Count of balls is not fixed.
* `decision` is `None` until that player's first threat. The HUD must handle `None`. Only players on a `"fly"` controller have one.
* `stats[team]["hits"]` is hits taken by that team. Dodge rate is `dodges / threats` (guard against 0). Hit rate is `hits` divided by the other team's `throws`.

## Coordinates

Metres. x runs along the court, with the centre line at x = 0 and the court spanning x in [-10, 10]. y is up. z is across, spanning [-5, 5]. Blue is at x < 0 (starts at x = -4), red at x > 0. Ball radius 0.15, player radius 0.35. Player y is 0.35 (centre height). These constants are in `game/physics.py`.

## Not implemented (do it in `arena/`)

* `R` reset: just build a new `Match(...)`.
* `1/2/3` red controller switch: build a new `Match` with a different `red=`. There is no `set_red_controller`.
* Pause: skip calling `step`.
* Flash a player that just dodged: use `dodging` (true for 0.4 s).

## Checks

```bash
python -m pytest tests/test_game.py          # 4 tests
python -m game.sim --matches 2               # headless baseline table
python -m arena.main --headless-check        # yours; must print OK
```

Needs `numpy` only. No window is needed to test any of this.
