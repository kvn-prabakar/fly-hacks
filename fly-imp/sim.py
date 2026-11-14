"""Headless 2D dodgeball world: one fly wanders a top-down arena while balls roll at it.

Coordinates: x right, y up, origin bottom-left. The viewer flips y for drawing.
No graphics dependency, so it can be tested without a window.
"""
import hashlib
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
THETA_MIN = 1.0          # rad/s of expansion below which the looming cells stay silent
THETA_MAX = 3.0          # rad/s of expansion that maps to the max 200 Hz
DECISION_DT = 0.05       # brain is consulted 20x per second
DODGE_SPEED = 6.5
DODGE_COOLDOWN = 0.35
WALK_SPEED = 1.6
MDN_ON = 5.0             # Hz: MDN counts as "walk backwards" above one spike per brain window
EYE_OVERLAP = 0.35       # sin of the half-width (about 20 deg) of the strip both eyes share


class Brain:
    """The fly's answer to (left, right) looming drive in Hz, read from fly_table.pkl.

    The table is the real connectome simulated ahead of time by build_table.py (intact brain
    and a Giant-Fibre-silenced brain). decide() interpolates it and returns:

        gf     Giant Fibre (DNp01) rate, Hz: the escape command
        mdn    MDN rate, Hz: the walk-backwards command
        steer  -1..1, from all other descending neurons that exist as a left/right pair:
               (left copies - right copies) / (left + right). Positive = the left side of
               the brain is more active, i.e. the threat is on the fly's left.

    If the table file is missing, a PLACEHOLDER rule is used so the game still opens.
    The placeholder is NOT the connectome and the HUD says so.
    """

    def __init__(self, path=None):
        path = path or os.path.join(HERE, "fly_table.pkl")
        self.real = os.path.exists(path)
        self.sig = {}
        self.sha = ""
        if self.real:
            with open(path, "rb") as f:
                self.sha = hashlib.sha256(f.read()).hexdigest()
        if not self.real:
            self.grid, self.spike_hz = None, 5.0
            return
        with open(path, "rb") as f:
            d = pickle.load(f)
        self.grid = np.array(d["grid"], float)
        self.spike_hz = 1000.0 / d["ms"]                 # one spike in the simulated window
        typ, side = d["dn_type"], d["dn_side"]
        gf, mdn = typ == "DNp01", typ == "MDN"
        paired = np.intersect1d(typ[side == "left"], typ[side == "right"])
        lat = np.isin(typ, paired) & ~gf
        self.n_steer = int(lat.sum())
        for variant, r in d["rates"].items():            # r[left, right, neuron] in Hz
            left = r[:, :, lat & (side == "left")].sum(-1)
            right = r[:, :, lat & (side == "right")].sum(-1)
            raw = (left - right) / np.maximum(left + right, 1e-9)
            self.sig[variant] = {
                "gf": r[:, :, gf].mean(-1), "mdn": r[:, :, mdn].mean(-1),
                "gf_L": r[:, :, gf & (side == "left")].mean(-1),
                "gf_R": r[:, :, gf & (side == "right")].mean(-1),
                "left": left, "right": right,
                # This brain answers slightly "left" even to perfectly balanced input. Remove that
                # built-in side bias by comparing every stimulus with its mirror image (L<->R).
                "steer": (raw - raw.T) / 2,
            }

    def _interp(self, a, hz_l, hz_r):
        g = self.grid
        out = []
        for hz in (hz_l, hz_r):
            hz = min(max(hz, g[0]), g[-1])
            i = min(int(np.searchsorted(g, hz, side="right")) - 1, len(g) - 2)
            out.append((i, (hz - g[i]) / (g[i + 1] - g[i])))
        (i, u), (j, v) = out
        return float((1 - u) * (1 - v) * a[i, j] + u * (1 - v) * a[i + 1, j]
                     + (1 - u) * v * a[i, j + 1] + u * v * a[i + 1, j + 1])

    def decide(self, hz_l, hz_r, lesion=False):
        if self.real:
            s = self.sig["gf_cut" if lesion else "intact"]
            return {k: self._interp(a, hz_l, hz_r) for k, a in s.items()}
        # PLACEHOLDER (not the connectome): guessed thresholds so the window still opens.
        drive = max(hz_l, hz_r) + 0.3 * min(hz_l, hz_r)
        tot = hz_l + hz_r
        return {"gf": 0.0 if lesion or drive < 55 else 265.0, "gf_L": 0.0, "gf_R": 0.0,
                "mdn": 16.0 if drive >= 110 else 0.0, "left": hz_l, "right": hz_r,
                "steer": (hz_l - hz_r) / tot if tot > 0 else 0.0}


IDLE_OUT = {"gf": 0.0, "mdn": 0.0, "steer": 0.0}


class Ball:
    __slots__ = ("pos", "vel", "r", "age", "min_d", "hit", "alive", "angle")

    def __init__(self, pos, vel, r):
        self.pos, self.vel, self.r = pos, vel, r
        self.age, self.min_d, self.hit, self.alive, self.angle = 0.0, 1e9, False, True, 0.0


class World:
    def __init__(self, brain=None, policy="fly", seed=0, lesion=False, blind=None):
        """policy: 'fly'     the brain decides when to escape and to which side
                   'fly_geo' the brain decides when; game geometry picks the direction
                   'dumb'    no brain: distance rule + geometry
                   'none'    never dodges
        lesion: use the brain with the Giant Fibre silenced.
        blind:  None, 'L' or 'R': that eye sends nothing to the brain."""
        self.brain = brain or Brain()
        self.policy, self.lesion, self.blind = policy, lesion, blind
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
        self.last_out = dict(IDLE_OUT)
        self.stats = dict(hits=0, hits_L=0, hits_R=0, dodged=0, close=0, jumps=0)
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
            # Each eye covers its own side. In the strip straight ahead and straight behind the
            # two fields overlap, and the share shifts smoothly, so a ball slightly to the left
            # drives the left eye slightly more.
            w_l = min(max(0.5 + float(np.dot(u, left)) / (2 * EYE_OVERLAP), 0.0), 1.0)
            th_l = max(th_l, th * w_l)
            th_r = max(th_r, th * (1.0 - w_l))
            if th > worst_th:
                worst, worst_th = b, th
        to_hz = lambda th: 200.0 * min(max((th - THETA_MIN) / (THETA_MAX - THETA_MIN), 0.0), 1.0)
        hz_l, hz_r = to_hz(th_l), to_hz(th_r)
        if self.blind == "L":
            hz_l = 0.0
        elif self.blind == "R":
            hz_r = 0.0
        return hz_l, hz_r, worst

    def _escape(self, out):
        """Brain-driven escape. Both choices are read from the brain's output:

        when       a Giant Fibre spike (checked by the caller). Like the real Giant Fibre,
                   it is all-or-none: one spike is a full-speed jump.
        which way  sideways, away from the more active side of the brain (steer).

        The fly only knows left vs right, so 'away from that side' is the best it can aim.
        """
        f = np.array([math.cos(self.heading), math.sin(self.heading)])
        left = np.array([-f[1], f[0]])
        self._jump(-left if out["steer"] >= 0 else left)   # threat on the left -> jump right

    def _jump(self, d, speed=DODGE_SPEED):
        probe = self.pos + d * 1.2                       # body limit: don't jump into a wall
        if not (WALL < probe[0] < ARENA_W - WALL and WALL < probe[1] < ARENA_H - WALL):
            d = -d
        self.vel = d * speed
        self.cooldown = DODGE_COOLDOWN
        self.stats["jumps"] += 1
        self.events.append(("jump", self.pos.copy()))

    def _dodge(self, ball):
        """Game rule (not from the brain): sidestep off the ball's rolling line."""
        v = ball.vel / max(np.linalg.norm(ball.vel), 1e-6)
        w = self.pos - ball.pos
        perp = w - np.dot(w, v) * v
        n = np.linalg.norm(perp)
        if n < 1e-3:
            perp = np.array([-v[1], v[0]]) * self.rng.choice([-1, 1])
            n = 1.0
        self._jump(perp / n)

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
                fwd = np.array([math.cos(self.heading), math.sin(self.heading)])
                on_left = float(np.dot(b.pos - self.pos, [-fwd[1], fwd[0]])) > 0
                self.stats["hits_L" if on_left else "hits_R"] += 1
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
            self.last_out = dict(IDLE_OUT)
            return
        if self.policy == "dumb":
            self.last_out = dict(IDLE_OUT)
            if float(np.linalg.norm(worst.pos - self.pos)) < 2.5 and self.cooldown <= 0:
                self._dodge(worst)
            return
        out = self.brain.decide(self.hz_l, self.hz_r, self.lesion)
        self.last_out = out
        # A Giant Fibre spike is the escape command: at least one spike in the brain's window.
        if out["gf"] >= self.brain.spike_hz and self.cooldown <= 0:
            if self.policy == "fly_geo":
                self._dodge(worst)
            else:
                self._escape(out)
        elif out["mdn"] > MDN_ON:
            self.backing = True          # no escape available: MDN walks the fly backwards
