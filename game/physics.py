"""Ball physics. Units: metres, seconds. x = along court (centre line x=0), y = up, z = across."""
from dataclasses import dataclass
import numpy as np

G = 9.8
COURT_X = 10.0   # court spans x in [-10, 10]
COURT_Z = 5.0    # and z in [-5, 5]
BALL_R = 0.15
PLAYER_R = 0.35
MAX_BOUNCES = 2


@dataclass
class Ball:
    id: int
    pos: np.ndarray
    vel: np.ndarray
    team: str              # team that threw it
    alive: bool = True
    bounces: int = 0


def step_ball(ball: Ball, dt: float) -> None:
    if not ball.alive:
        return
    ball.vel[1] -= G * dt
    ball.pos += ball.vel * dt
    if ball.pos[1] < BALL_R and ball.vel[1] < 0:
        ball.pos[1] = BALL_R
        ball.vel[1] *= -0.5
        ball.bounces += 1
        if ball.bounces >= MAX_BOUNCES:
            ball.alive = False
    if abs(ball.pos[0]) > COURT_X or abs(ball.pos[2]) > COURT_Z:
        ball.alive = False


def hit(ball: Ball, player) -> bool:
    """Player needs .pos, .team, .radius."""
    return (ball.alive and ball.team != player.team
            and np.linalg.norm(ball.pos - player.pos) < BALL_R + player.radius)
