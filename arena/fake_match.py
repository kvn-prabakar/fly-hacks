"""Fake Match for ARENA development before GAME is ready."""
import numpy as np
from typing import List, Dict, Any

class FakeBall:
    def __init__(self):
        self.pos = np.array([0, 2, 0], dtype=np.float32)
        self.vel = np.array([0, 0, 0], dtype=np.float32)
        self.team = 0
        self.alive = False

class FakePlayer:
    def __init__(self, team: int, id: int):
        self.pos = np.array([-7 if team == 0 else 7, 0, -3 + id * 3], dtype=np.float32)
        self.vel = np.zeros(3, dtype=np.float32)
        self.team = team
        self.id = id
        self.facing = np.array([1 if team == 0 else -1, 0, 0], dtype=np.float32)
        self.state = "IDLE"
        self.last_decision = None

class FakeMatch:
    """Minimal Match implementation for arena development."""
    
    def __init__(self):
        self.players = [FakePlayer(t, i) for t in [0, 1] for i in range(3)]
        self.balls = [FakeBall()]
        self.throws = [0, 0]
        self.hits = [0, 0]
        self.dodges = [0, 0]
        self.lesion = False
        self.time = 0.0
        self._paused = False
    
    def step(self, dt: float) -> None:
        if self._paused:
            return
        self.time += dt
        # Simple ball animation for visual testing
        for ball in self.balls:
            if ball.alive:
                ball.pos += ball.vel * dt
                ball.vel[1] -= 9.8 * dt
                if ball.pos[1] <= 0.15:
                    ball.pos[1] = 0.15
                    ball.vel[1] = -ball.vel[1] * 0.5
    
    def state(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "players": [
                {
                    "pos": p.pos.tolist(),
                    "vel": p.vel.tolist(),
                    "team": p.team,
                    "id": p.id,
                    "state": p.state,
                    "facing": p.facing.tolist(),
                    "last_decision": p.last_decision.__dict__ if p.last_decision else None,
                }
                for p in self.players
            ],
            "balls": [
                {
                    "pos": b.pos.tolist(),
                    "vel": b.vel.tolist(),
                    "team": b.team,
                    "alive": b.alive,
                }
                for b in self.balls
            ],
            "throws": self.throws,
            "hits": self.hits,
            "dodges": self.dodges,
            "lesion": self.lesion,
        }
    
    def toggle_lesion(self) -> None:
        self.lesion = not self.lesion
    
    def toggle_pause(self) -> None:
        self._paused = not self._paused
    
    def reset(self) -> None:
        self.__init__()