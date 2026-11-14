"""HUD: scores, neuron rates, lesion indicator."""
from ursina import Text, Entity, Vec2, color, camera, window
from typing import Dict, Any, Optional
import numpy as np

class HUD:
    """Heads-up display for the game."""
    
    def __init__(self):
        # Score panel (top left)
        self.score_text = Text(
            text="Blue: 0 hits, 0% dodge\nRed: 0 hits, 0% dodge",
            position=(-0.85, 0.45),
            origin=(-0.5, 0.5),
            scale=1.5,
            color=color.white,
            background=True,
        )
        
        # Neuron panel (top right)
        self.neuron_text = Text(
            text="NEURON RATES\nLooming: 0 Hz\nGF Left: 0 Hz\nGF Right: 0 Hz\nMDN: 0 Hz\nDNp09: 0 Hz",
            position=(0.65, 0.45),
            origin=(-0.5, 0.5),
            scale=1.3,
            color=color.white,
            background=True,
        )
        
        # Lesion indicator (top center)
        self.lesion_entity = Entity(
            parent=camera.ui,
            model='quad',
            scale=(0.3, 0.06),
            position=(0, 0.45),
            color=color.green,
        )
        self.lesion_text = Text(
            text="NORMAL",
            parent=self.lesion_entity,
            scale=1.5,
            color=color.black,
            origin=(0, 0),
        )
        
        # Controller indicator
        self.controller_text = Text(
            text="Red: Random",
            position=(-0.85, -0.45),
            origin=(-0.5, -0.5),
            scale=1.3,
            color=color.white,
            background=True,
        )
        
        # Instructions
        self.help_text = Text(
            text="L: Lesion  Space: Pause  R: Reset  1/2/3: Red AI  Esc: Quit",
            position=(0, -0.48),
            origin=(0, -0.5),
            scale=1.0,
            color=color.gray,
        )
    
    def update(self, match_state: Dict[str, Any]) -> None:
        """Update HUD from match state."""
        # Scores
        hits_blue = match_state["hits"][0]
        hits_red = match_state["hits"][1]
        throws_at_blue = match_state["throws"][1]  # red throws at blue
        throws_at_red = match_state["throws"][0]   # blue throws at red
        dodges_blue = match_state["dodges"][0]
        dodges_red = match_state["dodges"][1]
        
        dodge_rate_blue = dodges_blue / max(1, hits_blue + dodges_blue) * 100
        dodge_rate_red = dodges_red / max(1, hits_red + dodges_red) * 100
        
        self.score_text.text = (
            f"Blue: {hits_blue} hits, {dodge_rate_blue:.0f}% dodge\n"
            f"Red: {hits_red} hits, {dodge_rate_red:.0f}% dodge"
        )
        
        # Neuron rates from last blue player decision
        neuron_text = "NEURON RATES\n"
        last_decision = None
        for p in match_state["players"]:
            if p["team"] == 0 and p["last_decision"]:
                last_decision = p["last_decision"]
                break
        
        if last_decision:
            neuron_text += (
                f"Looming: {last_decision['looming_hz_in']:.0f} Hz\n"
                f"GF Left: {last_decision['escape_left_hz']:.1f} Hz\n"
                f"GF Right: {last_decision['escape_right_hz']:.1f} Hz\n"
                f"MDN: {last_decision['backup_hz']:.1f} Hz\n"
                f"DNp09: {last_decision['forward_hz']:.1f} Hz\n"
                f"Dodge: {last_decision['dodge_dir']:.1f} @ {last_decision['dodge_strength']:.2f}"
            )
        else:
            neuron_text += "No decision yet"
        
        self.neuron_text.text = neuron_text
        
        # Lesion indicator
        if match_state["lesion"]:
            self.lesion_entity.color = color.red
            self.lesion_text.text = "LESION"
        else:
            self.lesion_entity.color = color.green
            self.lesion_text.text = "NORMAL"
    
    def set_red_controller(self, name: str) -> None:
        self.controller_text.text = f"Red: {name}"