from dataclasses import dataclass, field
import numpy as np
from game.physics import PLAYER_R
from game.threat import make_threat, player_right

MAX_DODGE_SPEED = 6.0
DODGE_TIME = 0.4
RECOVER_TIME = 0.6
MIN_DODGE = 0.05


@dataclass
class Player:
    id: int
    team: str
    pos: np.ndarray
    facing: np.ndarray
    controller: object
    radius: float = PLAYER_R
    state: str = "IDLE"          # IDLE -> DODGING -> RECOVER -> IDLE
    timer: float = 0.0
    vel: np.ndarray = field(default_factory=lambda: np.zeros(3))
    seen: set = field(default_factory=set)   # ball ids already reacted to
    last_decision: object = None
    threats: int = 0
    dodges: int = 0


class StillController:
    def decide(self, threat, lesion, rng):
        return None


class RandomController:
    def decide(self, threat, lesion, rng):
        return float(rng.choice([-1.0, 1.0])), float(rng.uniform(0, 1)), None


class FlyController:
    def __init__(self, brain):
        self.brain = brain

    def decide(self, threat, lesion, rng):
        d = self.brain.decide(threat, lesion)
        return d.dodge_dir, d.dodge_strength, d


def make_controller(kind, brain=None):
    if kind == "fly":
        return FlyController(brain)
    return {"random": RandomController, "still": StillController}[kind]()


def update_player(p: Player, balls, dt, lesion, rng, bounds):
    # react once per ball
    if p.state == "IDLE":
        for b in balls:
            if b.id in p.seen:
                continue
            threat = make_threat(b, p)
            if threat is None:
                continue
            p.seen.add(b.id)
            p.threats += 1
            res = p.controller.decide(threat, lesion, rng)
            if res is None:
                continue
            dodge_dir, strength, decision = res
            if decision is not None:
                p.last_decision = decision
            if strength < MIN_DODGE:
                continue
            v = b.vel * np.array([1.0, 0.0, 1.0])
            perp = np.array([-v[2], 0.0, v[0]])
            perp /= np.linalg.norm(perp) + 1e-9
            if perp @ player_right(p.facing) < 0:
                perp = -perp                       # perp now points to player's right
            p.vel = perp * dodge_dir * MAX_DODGE_SPEED * strength
            p.state, p.timer = "DODGING", DODGE_TIME
            p.dodges += 1
            break
    # state machine
    if p.state != "IDLE":
        p.timer -= dt
        if p.state == "DODGING":
            p.pos += p.vel * dt
            lo, hi = bounds
            p.pos[:] = np.clip(p.pos, lo, hi)
            if p.timer <= 0:
                p.state, p.timer, p.vel = "RECOVER", RECOVER_TIME, np.zeros(3)
        elif p.timer <= 0:
            p.state = "IDLE"
