"""Ursina scene setup: court, players, balls."""
from ursina import Entity, Vec3, color, EditorCamera, camera, window, Ursina
from typing import List, Dict, Any
import numpy as np

# Court dimensions (match game/physics.py)
COURT_WIDTH = 20.0
COURT_DEPTH = 10.0
PLAYER_RADIUS = 0.35
BALL_RADIUS = 0.15

class Court:
    """Court visual elements."""
    
    def __init__(self):
        # Floor
        self.floor = Entity(
            model='plane',
            scale=(COURT_WIDTH, 1, COURT_DEPTH),
            position=(0, 0, 0),
            color=color.rgb(40, 80, 40),
            collider='box',
        )
        
        # Centre line
        self.centre_line = Entity(
            model='cube',
            scale=(0.1, 0.05, COURT_DEPTH),
            position=(0, 0.03, 0),
            color=color.white,
        )
        
        # Side lines
        self.side_lines = [
            Entity(model='cube', scale=(COURT_WIDTH, 0.05, 0.1), position=(0, 0.03, COURT_DEPTH/2), color=color.white),
            Entity(model='cube', scale=(COURT_WIDTH, 0.05, 0.1), position=(0, 0.03, -COURT_DEPTH/2), color=color.white),
        ]
        
        # End lines
        self.end_lines = [
            Entity(model='cube', scale=(0.1, 0.05, COURT_DEPTH), position=(COURT_WIDTH/2, 0.03, 0), color=color.white),
            Entity(model='cube', scale=(0.1, 0.05, COURT_DEPTH), position=(-COURT_WIDTH/2, 0.03, 0), color=color.white),
        ]
        
        # Low walls
        wall_h = 1.0
        self.walls = [
            Entity(model='cube', scale=(COURT_WIDTH, wall_h, 0.2), position=(0, wall_h/2, COURT_DEPTH/2 + 0.1), color=color.rgb(100, 100, 100)),
            Entity(model='cube', scale=(COURT_WIDTH, wall_h, 0.2), position=(0, wall_h/2, -COURT_DEPTH/2 - 0.1), color=color.rgb(100, 100, 100)),
            Entity(model='cube', scale=(0.2, wall_h, COURT_DEPTH), position=(COURT_WIDTH/2 + 0.1, wall_h/2, 0), color=color.rgb(100, 100, 100)),
            Entity(model='cube', scale=(0.2, wall_h, COURT_DEPTH), position=(-COURT_WIDTH/2 - 0.1, wall_h/2, 0), color=color.rgb(100, 100, 100)),
        ]

class PlayerEntity:
    """Visual representation of a player."""
    
    def __init__(self, team: int, id: int):
        self.team = team
        self.id = id
        
        # Capsule body (use cube as visual, capsule as collider)
        self.body = Entity(
            model='cube',
            scale=(PLAYER_RADIUS * 2, 1.8, PLAYER_RADIUS * 2),
            position=(0, 0.9, 0),
            color=color.blue if team == 0 else color.red,
            collider='capsule',
        )
        
        # Head
        self.head = Entity(
            model='sphere',
            scale=(0.3, 0.3, 0.3),
            position=(0, 2.0, 0),
            color=color.blue if team == 0 else color.red,
            parent=self.body,
        )
        
        # Facing indicator
        self.facing_indicator = Entity(
            model='cube',
            scale=(0.1, 0.1, 0.5),
            position=(0, 0.9, 0.6),
            color=color.white,
            parent=self.body,
        )
        
        # Dodge flash
        self.flash_timer = 0.0
        self.original_color = color.blue if team == 0 else color.red
    
    def update(self, player_data: Dict[str, Any], dt: float) -> None:
        """Update from player state dict."""
        pos = player_data["pos"]
        self.body.position = Vec3(pos[0], pos[1] + 0.9, pos[2])
        
        # Facing rotation
        facing = player_data["facing"]
        if np.linalg.norm(facing) > 1e-6:
            angle = np.degrees(np.arctan2(facing[0], facing[2]))
            self.body.rotation_y = angle
        
        # State color flash
        if player_data["state"] == "DODGING":
            self.body.color = color.cyan if self.team == 0 else color.orange
            self.flash_timer = 0.2
        elif self.flash_timer > 0:
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                self.body.color = self.original_color

class BallEntity:
    """Visual representation of a ball."""
    
    def __init__(self):
        self.entity = Entity(
            model='sphere',
            scale=(BALL_RADIUS * 2, BALL_RADIUS * 2, BALL_RADIUS * 2),
            position=(0, 0, 0),
            color=color.yellow,
        )
        self.alive = False
    
    def update(self, ball_data: Dict[str, Any]) -> None:
        pos = ball_data["pos"]
        self.entity.position = Vec3(pos[0], pos[1], pos[2])
        self.alive = ball_data["alive"]
        self.entity.enabled = self.alive
        if self.alive:
            self.entity.color = color.blue if ball_data["team"] == 0 else color.red

def create_scene() -> tuple:
    """Create court, player entities, ball entities."""
    court = Court()
    players = [PlayerEntity(p["team"], p["id"]) for p in [
        {"team": 0, "id": 0}, {"team": 0, "id": 1}, {"team": 0, "id": 2},
        {"team": 1, "id": 0}, {"team": 1, "id": 1}, {"team": 1, "id": 2},
    ]]
    balls = [BallEntity() for _ in range(10)]
    return court, players, balls