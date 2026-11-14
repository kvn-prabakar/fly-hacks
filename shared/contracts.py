from dataclasses import dataclass
from typing import Protocol

@dataclass
class ThreatInput:
    distance: float        # metres from ball to player, now
    closing_speed: float   # m/s, how fast the gap is shrinking (>0 means approaching)
    side: float            # -1 = ball coming from player's left, +1 = right, 0 = straight on

@dataclass
class DodgeDecision:
    escape_left_hz: float   # Giant Fibre (DNp01) left rate
    escape_right_hz: float  # Giant Fibre (DNp01) right rate
    backup_hz: float        # MDN rate (walk backwards)
    forward_hz: float       # DNp09 rate (walk forwards)
    dodge_dir: float        # -1 = dodge to player's left, +1 = right
    dodge_strength: float   # 0..1, 0 = do nothing
    looming_hz_in: float    # stimulus that was applied (for HUD)

class Brain(Protocol):
    def decide(self, threat: ThreatInput, lesion: bool = False) -> DodgeDecision: ...