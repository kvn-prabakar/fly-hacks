import numpy as np
from game.physics import Ball, step_ball, hit
from game.players import Player, StillController
from game.threat import make_threat
from game.sim import Match
from shared.stubs import StubBrain


def _player(pos=(4, 0.35, 0)):
    return Player(0, "blue", np.array(pos, float), np.array([-1.0, 0, 0]), StillController())


def test_straight_throw_hits_still_player():
    p = _player()
    b = Ball(0, np.array([9.0, 0.5, 0.0]), np.array([-10.0, 0, 0]), "red")
    for _ in range(120):
        b.pos += b.vel * (1 / 60)
        if hit(b, p):
            return
    assert False, "ball did not hit"


def test_threat_none_when_flying_away():
    p = _player()
    b = Ball(0, np.array([6.0, 0.9, 0.0]), np.array([10.0, 0, 0]), "red")
    assert make_threat(b, p) is None


def test_threat_when_approaching():
    p = _player()
    b = Ball(0, np.array([9.0, 0.5, 0.0]), np.array([-10.0, 0, 0]), "red")
    t = make_threat(b, p)
    assert t is not None and t.closing_speed > 0


def test_match_runs_60s():
    m = Match(StubBrain(), "fly", "random", seed=1)
    for _ in range(60 * 60):
        m.step(1 / 60)
    s = m.state()
    assert len(s["players"]) == 6 and s["stats"]["red"]["throws"] > 0


def test_manual_move_and_bounds():
    m = Match(StubBrain(), "still", "still")
    start = m.players[0].pos.copy()
    m.set_move(0, 1, 1)
    for _ in range(30):
        m.step(1 / 60)
    d = m.players[0].pos - start
    assert d[0] > 0 and d[2] > 0
    for _ in range(600):
        m.step(1 / 60)
    assert m.players[0].pos[0] <= -0.5 + 1e-9      # cannot cross centre line
    m.set_move(0, 0, 0)
    p = m.players[0].pos.copy()
    m.step(1 / 60)
    assert (m.players[0].pos == p).all()
