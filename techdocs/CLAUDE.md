# CLAUDE.md

Fly Dodgeball: a 3D dodgeball game where the blue team dodges using a real fruit fly brain (FlyWire connectome, Shiu et al. 2024 LIF model). Python only: numpy/scipy for the brain, Ursina for the 3D game. Full spec is in `plan.md`. Read the sections for your role before writing code.

## Roles

Three people, each with their own agent. Your human tells you your role at the start. If they did not, ask.

| Role | Branch | You may edit | Spec |
|---|---|---|---|
| BRAIN | `brain` | `brain/`, `tests/test_brain.py` | plan.md 4.3, 5.1 |
| GAME | `game` | `game/`, `tests/test_game.py` | plan.md 4.3, 5.2 |
| ARENA | `arena` | `arena/`, `tests/test_arena.py`, `README.md` | plan.md 4.3, 5.3 |

## Hard rules

1. Only edit files your role owns. If you need something from another role, use `shared/stubs.py` and leave a `TODO(<role>)` comment.
2. Never change `shared/contracts.py`, `shared/stubs.py`, `requirements.txt`, `CLAUDE.md` or `plan.md` on your own. Stop and ask your human; all three people must agree.
3. Never commit `data/`, `.venv/`, `*.npz`, or any token or `.env` file. Run `git status` before every commit and check.
4. The brain model settings are fixed (Shiu): rest −52 mV, threshold −45 mV, 20 ms membrane, 5 ms synapse, 2.2 ms refractory, 1.8 ms delay, 0.275 mV per synapse, 0.1 ms step. Do not tune them. Do not change connection signs. Tune only the stimulus mapping and game constants.
5. Do not add smell or wind inputs (they make the brain seize).
6. `game/` must never import `ursina`. It has to run headless.

## Long running commands

Your shell commands time out after about 2 minutes.

* Anything slower (`brain.sanity`, `brain.build_table`, long `game.sim` runs) must run in the background with output to a log file, for example:
  `python -m brain.build_table > data/build_table.log 2>&1 &`
  Then check the log. Or ask your human to run it.
* Always try the small version first: `python -m brain.build_table --small`, `python -m game.sim --matches 2`.

## You cannot see the game window

ARENA: you cannot look at the Ursina window. After each visual change:
1. Run `python -m arena.main --headless-check` (300 frames offscreen, then exit 0) to catch crashes.
2. Ask your human to run `python -m arena.main` and tell you what they see. Do not claim something looks right without that.

## Commands

```bash
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m brain.download_data          # once, fills data/
python -m brain.sanity                 # background, about 1 to 2 min
python -m brain.build_table [--small]  # background, small ~2 min, full 10 to 20 min
python -m game.sim --matches 50        # headless baseline numbers
python -m arena.main                   # the game (human runs this)
python -m arena.main --headless-check  # crash check for agents
pytest tests/test_<role>.py
```

## How to work

1. Start in plan mode. Read your plan.md sections, then list the steps you will take and wait for your human to approve.
2. Build one step at a time. After each step run that step's check from plan.md and show the result.
3. Commit after each working step on your branch: `git add -A && git status && git commit -m "<role>: <what works>" && git push`.
4. A step is done only when its check in plan.md passes. If a check fails, say so plainly; do not loosen the check to make it pass.
5. At checkpoints (1:30, 2:30) your human will merge `origin/main` into your branch. Run your tests again after.

## Definition of done for the whole project

* `python -m arena.main` opens, a match plays with `TableBrain` (no "STUB BRAIN" banner).
* `L` silences the Giant Fibre and the blue team's hit rate visibly goes up.
* `python -m game.sim --matches 50` prints hit rates for fly, random and still controllers.
