"""Tests for arena module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from arena.fake_match import FakeMatch
from arena.scene import create_scene, Court, PlayerEntity, BallEntity
from arena.hud import HUD
from shared.contracts import ThreatInput, DodgeDecision
from shared.stubs import StubBrain

class TestFakeMatch:
    def test_fake_match_creation(self):
        match = FakeMatch()
        assert len(match.players) == 6
        assert len(match.balls) == 1
        assert match.lesion == False
        assert match.time == 0.0
    
    def test_fake_match_step(self):
        match = FakeMatch()
        match.step(1/60)
        assert match.time > 0
    
    def test_fake_match_state(self):
        match = FakeMatch()
        state = match.state()
        assert "players" in state
        assert "balls" in state
        assert "throws" in state
        assert "hits" in state
        assert "dodges" in state
        assert "lesion" in state
        assert len(state["players"]) == 6
    
    def test_fake_match_toggle_lesion(self):
        match = FakeMatch()
        assert match.lesion == False
        match.toggle_lesion()
        assert match.lesion == True
        match.toggle_lesion()
        assert match.lesion == False
    
    def test_fake_match_reset(self):
        match = FakeMatch()
        match.step(1.0)
        assert match.time > 0
        match.reset()
        assert match.time == 0.0

class TestScene:
    def test_create_scene(self):
        court, players, balls = create_scene()
        assert court is not None
        assert len(players) == 6
        assert len(balls) == 10
    
    def test_player_entity_creation(self):
        player = PlayerEntity(team=0, id=0)
        assert player.team == 0
        assert player.id == 0
        assert player.body is not None
    
    def test_ball_entity_creation(self):
        ball = BallEntity()
        assert ball.entity is not None
        assert ball.alive == False

class TestHUD:
    def test_hud_creation(self):
        hud = HUD()
        assert hud.score_text is not None
        assert hud.neuron_text is not None
        assert hud.lesion_entity is not None
    
    def test_hud_update(self):
        hud = HUD()
        state = {
            "throws": [10, 10],
            "hits": [3, 2],
            "dodges": [7, 8],
            "lesion": False,
            "players": [
                {"team": 0, "last_decision": {
                    "looming_hz_in": 100,
                    "escape_left_hz": 20,
                    "escape_right_hz": 30,
                    "backup_hz": 5,
                    "forward_hz": 0,
                    "dodge_dir": 1,
                    "dodge_strength": 0.8
                }},
                {"team": 1, "last_decision": None},
            ]
        }
        hud.update(state)
        assert "Blue: 3 hits" in hud.score_text.text
        assert "Red: 2 hits" in hud.score_text.text

class TestContracts:
    def test_threat_input(self):
        threat = ThreatInput(distance=5.0, closing_speed=10.0, side=0.5)
        assert threat.distance == 5.0
        assert threat.closing_speed == 10.0
        assert threat.side == 0.5
    
    def test_dodge_decision(self):
        decision = DodgeDecision(
            escape_left_hz=20, escape_right_hz=30,
            backup_hz=5, forward_hz=0,
            dodge_dir=1, dodge_strength=0.8,
            looming_hz_in=100
        )
        assert decision.escape_left_hz == 20
        assert decision.dodge_strength == 0.8
    
    def test_stub_brain(self):
        brain = StubBrain()
        threat = ThreatInput(distance=5.0, closing_speed=10.0, side=0.0)
        decision = brain.decide(threat, lesion=False)
        assert decision.dodge_strength > 0
        assert decision.looming_hz_in > 0
        
        # With lesion
        decision_lesion = brain.decide(threat, lesion=True)
        assert decision_lesion.dodge_strength == 0
        assert decision_lesion.escape_left_hz == 0
        assert decision_lesion.escape_right_hz == 0

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])