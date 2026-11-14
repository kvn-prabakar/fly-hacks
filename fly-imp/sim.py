"""Headless 2D dodgeball world: one fly wanders a top-down arena while balls roll at it.

Coordinates: x right, y up, origin bottom-left. The viewer flips y for drawing.
No graphics dependency, so it can be tested without a window.
"""
import math
import os
import pickle

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- tunables ---------------------------------------------------------------
ARENA_W, ARENA_H = 16.0, 10.0
WALL = 0.7               # fly stays this far from the walls
FLY_R = 0.3              # fly hit radius
SPAWN_EVERY = 1.0        # mean seconds between balls
SPEED = (3.0, 7.0)       # ball launch speed range (units/s)
BALL_R = (0.25, 0.5)
AIM_SIGMA = 0.7          # aim scatter around the fly, so some balls miss
FRICTION = 0.12          # balls slowly lose speed as they roll
THETA_MAX = 3.0          # rad/s of expansion that maps to the max 200 Hz
DECISION_DT = 0.05       # brain is consulted 20x per second
DODGE_SPEED = 6.5
DODGE_COOLDOWN = 0.35
WALK_SPEED = 1.6
EYE_OVERLAP = -0.35      # an eye sees dot(direction, eye_axis) > this (a bit over a half-plane)


class Brain:
    """Looks up the fly's response to (left, right) looming drive in Hz.

    Uses fly_table.pkl (built from the real connectome by build_table.py).
    If it is missing, falls back to a PLACEHOLDER rule so the game still runs.
    """

    def __init__(self, path=None):
        path = path or os.path.join(HERE, "fly_table.pkl")
        self.real = os.path.exists(path)
        if self.real:
            with open(path, "rb") as f:
                d = pickle.load(f)
            self.grid, self.table = np.array(d["grid"]), d["table"]
        else:
            self.grid, self.table = None, None

    def decide(self, hz_l, hz_r):
        if self.real:
            gl = int(self.grid[np.abs(self.grid - hz_l).argmin()])
            gr = int(self.grid[np.abs(self.grid - hz_r).argmin()])
            return self.table[(gl, gr)]
        # PLACEHOLDER (not the connectome): guessed threshold, loosely matching
        # the notebook's single data point (150 Hz looming -> GF 265 Hz, MDN 16 Hz).
        drive = max(hz_l, hz_r) + 0.3 * min(hz_l, hz_r)
        return {"gf": 265.0 if drive >= 55 else 0.0,
                "gf_L": 0.0, "gf_R": 0.0,
                "mdn": 16.0 if drive >= 110 else 0.0}


class Ball:
    __slots__ = ("pos", "vel", "r", "age", "min_d", "hit", "alive", "angle")

    def __init__(self, pos, vel, r):
        self.pos, self.vel, self.r = pos, vel, r
        self.age, self.min_d, self.hit, self.alive, self.angle = 0.0, 1e9, False, True, 0.0


class World:
    def __init__(self, brain=None, policy="fly", seed=0, lesion=False):
        """policy: 'fly' (connectome brain), 'dumb' (distance rule), 'none' (never dodges)."""
        self.brain = brain or Brain()
        self.policy, self.lesion = policy, lesion
        self.spawn_every = SPAWN_EVERY
        self.spawn_rng = np.random.default_rng(seed)
        self.rng = np.random.default_rng(seed + 1)
        self.reset()

    def reset(self):
        self.t = 0.0
        self.pos = np.array([ARENA_W / 2, ARENA_H / 2])
        self.vel = np.zeros(2)
        self.heading = 0.0
        self.waypoint = self.pos.copy()
        self.wp_timer = 0.0
        self.balls = []
        self.next_spawn = 0.5
        self.next_decision = 0.0
        self.cooldown = 0.0
        self.backing = False
        self.hz_l = self.hz_r = 0.0
        self.last_out = {"gf": 0.0, "mdn": 0.0}
        self.stats = dict(hits=0, dodged=0, close=0, jumps=0)
        self.events = []   # ('hit'|'jump', position) for the viewer

    # ---- balls ----------------------------------------------------------------
    def spawn_at(self, pos, aim=None):
        r = self.spawn_rng
        aim = self.pos + r.normal(scale=AIM_SIGMA, size=2) if aim is None else aim
        d = aim - pos
        vel = d / max(np.linalg.norm(d), 1e-6) * r.uniform(*SPEED)
        self.balls.append(Ball(np.array(pos, float), vel, r.uniform(*BALL_R)))

    def _spawn_edge(self):
        r = self.spawn_rng
        side = r.choice(4, p=np.array([ARENA_W, ARENA_W, ARENA_H, ARENA_H]) / (2 * ARENA_W + 2 * ARENA_H))
        u = r.random()
        pos = [(u * ARENA_W, -0.8), (u * ARENA_W, ARENA_H + 0.8),
               (-0.8, u * ARENA_H), (ARENA_W + 0.8, u * ARENA_H)][side]
        self.spawn_at(pos)

    # ---- vision ---------------------------------------------------------------
    def _look(self):
        """Per-eye looming drive (Hz) and the most threatening ball."""
        f = np.array([math.cos(self.heading), math.sin(self.heading)])
        left = np.array([-f[1], f[0]])
        th_l = th_r = 0.0
        worst, worst_th = None, 0.0
        for b in self.balls:
            p = b.pos - self.pos
            d = float(np.linalg.norm(p))
            if d < 1e-6:
                continue
            u = p / d
            closing = -float(np.dot(p, b.vel - self.vel)) / d
            if closing <= 0:
                continue
            de = max(d, b.r * 1.05)
            th = 2 * b.r * closing / (de * math.sqrt(de * de - b.r * b.r))   # d(angular width)/dt
            if float(np.dot(u, left)) > EYE_OVERLAP:
                th_l = max(th_l, th)
            if float(np.dot(u, -left)) > EYE_OVERLAP:
                th_r = max(th_r, th)
            if th > worst_th:
                worst, worst_th = b, th
        to_hz = lambda th: 200.0 * min(max(th / THETA_MAX, 0.0), 1.0)
        return to_hz(th_l), to_hz(th_r), worst

    def _dodge(self, ball):
        """Game rule (not from the brain): sidestep off the ball's rolling line."""
        v = ball.vel / max(np.linalg.norm(ball.vel), 1e-6)
        w = self.pos - ball.pos
        perp = w - np.dot(w, v) * v
        n = np.linalg.norm(perp)
        if n < 1e-3:
            perp = np.array([-v[1], v[0]]) * self.rng.choice([-1, 1])
            n = 1.0
        d = perp / n
        probe = self.pos + d * 1.2                       # don't dodge into a wall
        if not (WALL < probe[0] < ARENA_W - WALL and WALL < probe[1] < ARENA_H - WALL):
            d = -d
        self.vel = d * DODGE_SPEED
        self.cooldown = DODGE_COOLDOWN
        self.stats["jumps"] += 1
        self.events.append(("jump", self.pos.copy()))

    # ---- one tick -------------------------------------------------------------
    def step(self, dt):
        self.t += dt
        self.cooldown = max(0.0, self.cooldown - dt)

        self.next_spawn -= dt
        if self.next_spawn <= 0:
            self._spawn_edge()
            self.next_spawn = self.spawn_rng.exponential(self.spawn_every)

        decay = math.exp(-FRICTION * dt)
        for b in self.balls:
            b.vel = b.vel * decay
            b.pos = b.pos + b.vel * dt
            b.angle += float(np.linalg.norm(b.vel)) / b.r * dt      # rolling spin for the viewer
            b.age += dt
            b.min_d = min(b.min_d, float(np.linalg.norm(b.pos - self.pos)))

        self.next_decision -= dt
        if self.next_decision <= 0:
            self.next_decision = DECISION_DT
            self._decide()

        # the fly wanders between random waypoints; MDN makes it walk backwards instead
        self.wp_timer -= dt
        if self.wp_timer <= 0 or np.linalg.norm(self.waypoint - self.pos) < 0.3:
            self.waypoint = np.array([self.rng.uniform(WALL, ARENA_W - WALL),
                                      self.rng.uniform(WALL, ARENA_H - WALL)])
            self.wp_timer = self.rng.uniform(2.0, 4.0)
        to_wp = self.waypoint - self.pos
        wp_dir = to_wp / max(np.linalg.norm(to_wp), 1e-6)
        f = np.array([math.cos(self.heading), math.sin(self.heading)])
        if self.backing:
            desired = -f * WALK_SPEED
        else:
            desired = wp_dir * WALK_SPEED
            diff = (math.atan2(wp_dir[1], wp_dir[0]) - self.heading + math.pi) % (2 * math.pi) - math.pi
            self.heading += diff * min(1.0, 5.0 * dt)
        self.vel = self.vel + (desired - self.vel) * min(1.0, 4.0 * dt)
        self.pos = self.pos + self.vel * dt
        self.pos[0] = min(max(self.pos[0], WALL), ARENA_W - WALL)
        self.pos[1] = min(max(self.pos[1], WALL), ARENA_H - WALL)

        # collisions and cleanup
        keep = []
        for b in self.balls:
            d = float(np.linalg.norm(b.pos - self.pos))
            if b.alive and d < b.r + FLY_R:
                b.alive, b.hit = False, True
                self.stats["hits"] += 1
                self.events.append(("hit", b.pos.copy()))
            out = (b.pos[0] < -2 or b.pos[0] > ARENA_W + 2 or b.pos[1] < -2 or b.pos[1] > ARENA_H + 2)
            if (not b.alive) or out or b.age > 15 or (b.age > 1 and np.linalg.norm(b.vel) < 0.4):
                if not b.hit:
                    self.stats["dodged"] += 1
                    if b.min_d < 1.2:
                        self.stats["close"] += 1
            else:
                keep.append(b)
        self.balls = keep

    def _decide(self):
        self.hz_l, self.hz_r, worst = self._look()
        self.backing = False
        if self.policy == "none" or worst is None:
            self.last_out = {"gf": 0.0, "mdn": 0.0}
            return
        if self.policy == "dumb":
            if float(np.linalg.norm(worst.pos - self.pos)) < 2.5 and self.cooldown <= 0:
                self._dodge(worst)
            return
        out = self.brain.decide(self.hz_l, self.hz_r)
        self.last_out = out
        if out["gf"] > 0 and not self.lesion and self.cooldown <= 0:
            self._dodge(worst)               # any Giant Fibre spike = bail now
        elif out["mdn"] > 5:
            self.backing = True
