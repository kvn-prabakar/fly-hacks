import numpy as np
from game.physics import Ball, G, COURT_X

RELEASE_H = 1.5
TARGET_H = 0.9
AIM_NOISE = 0.3


def throw(ball_id, team, target_pos, rng) -> Ball:
    sign = -1.0 if team == "blue" else 1.0
    origin = np.array([sign * (COURT_X - 0.5), RELEASE_H, 0.0])
    aim = target_pos + rng.normal(0, AIM_NOISE, 3) * np.array([1, 0, 1])
    delta = aim - origin
    horiz = float(np.hypot(delta[0], delta[2]))
    speed = rng.uniform(10, 16)
    T = horiz / speed
    vel = np.array([delta[0] / T, (TARGET_H - RELEASE_H + 0.5 * G * T * T) / T, delta[2] / T])
    return Ball(ball_id, origin, vel, team)


def next_delay(rng) -> float:
    return float(rng.uniform(1.5, 3.0))
