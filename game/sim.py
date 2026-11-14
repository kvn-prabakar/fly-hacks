"""Headless match. python -m game.sim --matches 50"""
import argparse
import dataclasses
import numpy as np
from game.physics import COURT_X, COURT_Z, PLAYER_R, step_ball, hit
from game.players import Player, make_controller, update_player
from game.throwers import throw, next_delay

DT = 1 / 60
TEAMS = ("blue", "red")


class Match:
    def __init__(self, brain=None, blue="fly", red="random", seed=0):
        self.rng = np.random.default_rng(seed)
        self.lesion = False
        self.time = 0.0
        self.balls = []
        self._next_id = 0
        self.stats = {t: dict(throws=0, hits=0, dodges=0, threats=0) for t in TEAMS}
        self.timers = {t: self.rng.uniform(0.5, 1.5) for t in TEAMS}
        self.players = []
        for team, kind in (("blue", blue), ("red", red)):
            s = -1.0 if team == "blue" else 1.0
            for i, z in enumerate((-2.5, 0.0, 2.5)):
                self.players.append(Player(
                    id=len(self.players), team=team,
                    pos=np.array([s * 4.0, PLAYER_R, z]),
                    facing=np.array([-s, 0.0, 0.0]),
                    controller=make_controller(kind, brain)))

    def set_move(self, player_id, dx, dz):
        """Manual input for one player, world axes (x along court, z across), each -1..0..1.
        Stays in effect until changed; call set_move(id, 0, 0) to stop. Normalised, so diagonals are not faster."""
        v = np.array([dx, 0.0, dz], float)
        n = np.linalg.norm(v)
        self.players[player_id].move = v / n if n > 1 else v

    def toggle_lesion(self):
        self.lesion = not self.lesion

    def _bounds(self, team):
        s = -1.0 if team == "blue" else 1.0
        xs = sorted((s * 0.5 + 0.0, s * (COURT_X - 0.5)))
        zl = COURT_Z - PLAYER_R
        return (np.array([xs[0], PLAYER_R, -zl]), np.array([xs[1], PLAYER_R, zl]))

    def step(self, dt=DT):
        self.time += dt
        for team in TEAMS:
            self.timers[team] -= dt
            if self.timers[team] <= 0:
                self.timers[team] = next_delay(self.rng)
                foes = [p for p in self.players if p.team != team]
                target = foes[self.rng.integers(len(foes))]
                self.balls.append(throw(self._next_id, team, target.pos, self.rng))
                self._next_id += 1
                self.stats[team]["throws"] += 1
        for p in self.players:
            d0, t0 = p.dodges, p.threats
            update_player(p, self.balls, dt, self.lesion, self.rng, self._bounds(p.team))
            self.stats[p.team]["dodges"] += p.dodges - d0
            self.stats[p.team]["threats"] += p.threats - t0
        for b in self.balls:
            step_ball(b, dt)
            for p in self.players:
                if hit(b, p):
                    b.alive = False
                    self.stats[p.team]["hits"] += 1
                    break
        self.balls = [b for b in self.balls if b.alive]

    def state(self):
        return dict(
            time=self.time, lesion=self.lesion,
            balls=[dict(id=b.id, pos=b.pos.tolist(), team=b.team) for b in self.balls],
            players=[dict(id=p.id, team=p.team, pos=p.pos.tolist(), state=p.state,
                          dodging=p.state == "DODGING",
                          decision=dataclasses.asdict(p.last_decision) if p.last_decision else None)
                     for p in self.players],
            stats={t: dict(s) for t, s in self.stats.items()},
        )


def run_match(brain, blue, red="still", seconds=60, lesion=False, seed=0):
    m = Match(brain, blue, red, seed)
    m.lesion = lesion
    for _ in range(int(seconds / DT)):
        m.step(DT)
    return m.stats


def _load_brain():
    try:
        from brain.table_brain import TableBrain
        return TableBrain(), "TableBrain"
    except Exception:
        from shared.stubs import StubBrain
        return StubBrain(), "StubBrain"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", type=int, default=50)
    ap.add_argument("--seconds", type=float, default=60)
    a = ap.parse_args()
    brain, name = _load_brain()
    print(f"brain: {name}, {a.matches} matches x {a.seconds:.0f}s (blue = team under test, red = still throwers)")
    for label, kind, les in (("fly", "fly", False), ("fly+lesion", "fly", True),
                             ("random", "random", False), ("still", "still", False)):
        hits = thr = dod = thrt = 0
        for s in range(a.matches):
            st = run_match(brain, kind, "still", a.seconds, les, seed=s)
            hits += st["blue"]["hits"]; dod += st["blue"]["dodges"]
            thrt += st["blue"]["threats"]; thr += st["red"]["throws"]
        print(f"{label:11s} hit rate {hits / max(thr, 1):.2f}  dodge rate {dod / max(thrt, 1):.2f}  ({hits}/{thr} throws)")


if __name__ == "__main__":
    main()
