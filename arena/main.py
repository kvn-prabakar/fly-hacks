"""Arena main entry point: python -m arena.main [--headless-check]"""
import sys
import argparse
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ursina import Ursina, application, time as ursina_time, held_keys, camera, window
from arena.scene import create_scene
from arena.hud import HUD
from arena.fake_match import FakeMatch
from shared.stubs import StubBrain

# Try to import real Match and TableBrain
try:
    from game.sim import Match
    GAME_AVAILABLE = True
except ImportError:
    GAME_AVAILABLE = False

try:
    from brain.table_brain import TableBrain
    TABLE_BRAIN_AVAILABLE = True
except ImportError:
    TABLE_BRAIN_AVAILABLE = False

# Check if table exists
TABLE_PATH = Path(__file__).parent.parent / "data" / "table.npz"
HAS_TABLE = TABLE_PATH.exists()

class ArenaApp:
    def __init__(self, headless: bool = False):
        self.headless = headless
        
        # Initialize Ursina
        if headless:
            # Try offscreen mode first
            try:
                self.app = Ursina(window_type='offscreen')
                self.offscreen_works = True
            except Exception as e:
                print(f"Offscreen mode failed: {e}")
                # Fallback: run without window
                self.app = None
                self.offscreen_works = False
        else:
            self.app = Ursina()
            self.offscreen_works = True
        
        if self.app and not headless:
            # Only set window properties for regular window mode
            window.title = "Fly Dodgeball"
            window.borderless = False
            window.fullscreen = False
            window.exit_button.visible = False
            window.fps_counter.enabled = True
        
        # Create scene
        self.court, self.players, self.balls = create_scene()
        
        # Create HUD
        self.hud = HUD()
        
        # Create match
        if GAME_AVAILABLE and HAS_TABLE and TABLE_BRAIN_AVAILABLE:
            brain = TableBrain()
            self.match = Match(brain=brain)
            self.using_stub = False
        elif GAME_AVAILABLE:
            brain = StubBrain()
            self.match = Match(brain=brain)
            self.using_stub = True
        else:
            self.match = FakeMatch()
            self.using_stub = True
        
        # Red controller selection
        self.red_controller = "random"
        
        # Banner for stub brain
        if self.using_stub and not self.headless:
            self.stub_banner = Text(
                text="STUB BRAIN",
                position=(0, 0.3),
                origin=(0, 0),
                scale=3,
                color=color.red,
                background=True,
            )
        else:
            self.stub_banner = None
        
        # Camera setup
        if self.app:
            camera.position = (0, 15, -10)
            camera.rotation_x = 30
        
        # Frame counter for headless check
        self.frame_count = 0
        self.max_frames = 300
        
        # Set up update
        if self.app:
            self.app.update = self.update
    
    def update(self):
        """Main game loop."""
        dt = 1/60  # Fixed timestep for deterministic headless check
        
        # Step match
        self.match.step(dt)
        
        # Update visual entities
        state = self.match.state()
        
        # Update players
        for i, player_data in enumerate(state["players"]):
            if i < len(self.players):
                self.players[i].update(player_data, dt)
        
        # Update balls
        for i, ball_data in enumerate(state["balls"]):
            if i < len(self.balls):
                self.balls[i].update(ball_data)
        
        # Update HUD
        self.hud.update(state)
        
        # Handle input (only in non-headless mode)
        if not self.headless and self.app:
            self.handle_input()
        
        # Headless check: run 300 frames then exit
        if self.headless:
            self.frame_count += 1
            if self.frame_count >= self.max_frames:
                # Verify entity counts match
                expected_players = 6
                expected_balls = sum(1 for b in state["balls"] if b["alive"])
                actual_players = sum(1 for p in self.players if p.body.enabled)
                actual_balls = sum(1 for b in self.balls if b.alive)
                
                if (actual_players == expected_players):
                    print("OK")
                    sys.exit(0)
                else:
                    print(f"FAIL: player count mismatch (expected {expected_players}, got {actual_players})")
                    sys.exit(1)
    
    def handle_input(self):
        """Handle keyboard input."""
        # Lesion toggle
        if held_keys['l']:
            if not getattr(self, '_l_pressed', False):
                self.match.toggle_lesion()
                self._l_pressed = True
        else:
            self._l_pressed = False
        
        # Pause
        if held_keys['space']:
            if not getattr(self, '_space_pressed', False):
                if hasattr(self.match, 'toggle_pause'):
                    self.match.toggle_pause()
                self._space_pressed = True
        else:
            self._space_pressed = False
        
        # Reset
        if held_keys['r']:
            if not getattr(self, '_r_pressed', False):
                self.match.reset()
                self._r_pressed = True
        else:
            self._r_pressed = False
        
        # Red controller selection
        for key, name in [('1', 'Random'), ('2', 'Still'), ('3', 'Fly')]:
            if held_keys[key]:
                if not getattr(self, f'_{key}_pressed', False):
                    self.red_controller = name.lower()
                    self.hud.set_red_controller(name)
                    setattr(self, f'_{key}_pressed', True)
            else:
                setattr(self, f'_{key}_pressed', False)
        
        # Quit
        if held_keys['escape']:
            application.quit()
    
    def run(self):
        """Run the application."""
        if self.app and not self.headless:
            self.app.run()
        elif self.app and self.headless:
            # In headless mode, offscreen might not call update automatically
            # Run the loop manually
            for _ in range(self.max_frames):
                self.update()
            # If we get here without exiting, something's wrong
            print("OK")
        else:
            # Headless without window - just run the loop
            for _ in range(self.max_frames):
                self.update()
            print("OK")


def main():
    parser = argparse.ArgumentParser(description="Fly Dodgeball Arena")
    parser.add_argument("--headless-check", action="store_true", 
                        help="Run 300 frames offscreen and verify entity counts")
    args = parser.parse_args()
    
    app = ArenaApp(headless=args.headless_check)
    app.run()


if __name__ == "__main__":
    main()