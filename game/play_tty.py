"""Terminal top-down viewer to test movement without Ursina.
python -m game.play_tty [--blue still|fly|random]
WASD move player 0 (blue, left side). L lesion, Q quit.
A/D = left/right on screen (x), W/S = up/down on screen (z). Hit = counted on the HUD line."""
import argparse
import curses
import time
from game.sim import Match

HOLD = 0.15   # terminals send no key-up; a key counts as held this long
KEYS = {ord("w"): (0, -1), ord("s"): (0, 1), ord("a"): (-1, 0), ord("d"): (1, 0)}


def run(scr, blue, red):
    curses.curs_set(0)
    scr.nodelay(True)
    m = Match(None if blue != "fly" else _brain(), blue, red)
    me, until, last = 0, 0.0, time.time()
    while True:
        now = time.time()
        k = scr.getch()
        while k != -1:
            if k in (ord("q"), 27):
                return
            if k in (ord("l"),):
                m.toggle_lesion()
            if k in KEYS:
                m.set_move(me, *KEYS[k])
                until = now + HOLD
            k = scr.getch()
        if now > until:
            m.set_move(me, 0, 0)
        m.step(min(now - last, 0.05))
        last = now
        s = m.state()
        scr.erase()
        for z in range(-5, 6):
            _add(scr, z + 5, 0, "".join(("|" if x == 0 else ".") + " " for x in range(-10, 11)))
        for b in s["balls"]:
            _put(scr, b["pos"], "o")
        for p in s["players"]:
            ch = "X" if p["id"] == me else ("B" if p["team"] == "blue" else "R")
            _put(scr, p["pos"], ch.lower() if p["dodging"] else ch)
        st = s["stats"]["blue"]
        _add(scr, 12, 0, f"blue hits {st['hits']}  dodges {st['dodges']}/{st['threats']}  lesion {'ON' if s['lesion'] else 'off'}  [WASD move, L lesion, Q quit]")
        scr.refresh()
        time.sleep(1 / 60)


def _add(scr, y, x, text):
    h, w = scr.getmaxyx()          # clip instead of crashing on small terminals
    if y < h and x < w:
        try:
            scr.addstr(y, x, text[: w - x - 1])
        except curses.error:
            pass


def _put(scr, pos, ch):
    x = int(round(pos[0])) + 10
    z = int(round(pos[2])) + 5
    if 0 <= x <= 20 and 0 <= z <= 10:
        _add(scr, z, x * 2, ch)


def _brain():
    from game.sim import _load_brain
    return _load_brain()[0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--blue", default="still", choices=["still", "fly", "random"])
    ap.add_argument("--red", default="still", choices=["still", "fly", "random"])
    a = ap.parse_args()
    curses.wrapper(run, a.blue, a.red)
