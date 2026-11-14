import numpy as np
from shared.contracts import ThreatInput

MAX_TIME = 1.0   # s until closest approach
MAX_MISS = 1.0   # m miss distance


def player_right(facing: np.ndarray) -> np.ndarray:
    return np.array([-facing[2], 0.0, facing[0]])


def make_threat(ball, player) -> ThreatInput | None:
    """Horizontal-plane prediction (ignores gravity arc, which would wrongly look like a miss)."""
    if not ball.alive or ball.team == player.team:
        return None
    rel = (player.pos - ball.pos) * np.array([1.0, 0.0, 1.0])
    v = ball.vel * np.array([1.0, 0.0, 1.0])
    dist = float(np.linalg.norm(rel))
    v2 = float(v @ v)
    if dist < 1e-6 or v2 < 1e-6:
        return None
    closing = float(rel @ v) / dist
    if closing <= 0:
        return None
    t_ca = float(rel @ v) / v2
    miss = float(np.linalg.norm(rel - v * t_ca))
    if t_ca > MAX_TIME or miss > MAX_MISS:
        return None
    lateral = float((-rel) @ player_right(player.facing)) / dist   # ball offset from player, + = right
    return ThreatInput(distance=dist, closing_speed=closing, side=float(np.clip(lateral, -1, 1)))
