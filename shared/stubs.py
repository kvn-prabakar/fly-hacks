import numpy as np
from shared.contracts import ThreatInput, DodgeDecision

class StubBrain:
    """Fake brain with the same interface as TableBrain. No neurons involved."""

    def decide(self, threat: ThreatInput, lesion: bool = False) -> DodgeDecision:
        looming = float(np.clip(20 * threat.closing_speed / max(threat.distance, 0.3), 0, 200))
        strength = 0.0 if lesion else float(np.clip(looming / 150, 0, 1))
        gf = 0.0 if lesion else looming * 0.4
        left = gf * (1 - threat.side) / 2
        right = gf * (1 + threat.side) / 2
        return DodgeDecision(
            escape_left_hz=left,
            escape_right_hz=right,
            backup_hz=looming * 0.1,
            forward_hz=0.0,
            dodge_dir=1.0 if threat.side <= 0 else -1.0,   # dodge away from the ball
            dodge_strength=strength,
            looming_hz_in=looming,
        )
