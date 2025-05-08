"""
Environment State

Definiert den Zustand der RL-Umgebung, der für das Training und die Evaluation verwendet wird.
"""
from typing import Dict, List, Any, Optional, Set, Tuple
import numpy as np
import random
from dataclasses import dataclass, field

from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter
from src.utils.logging_setup import get_logger

# Logger für dieses Modul
logger = get_logger(__name__)


@dataclass
class EnvironmentState:
    """
    Repräsentiert den aktuellen Zustand der Umgebung für das RL-Training.
    
    Enthält alle relevanten Informationen zum aktuellen Kampf, einschließlich
    der Charaktere, des aktuellen Zuges und der verfügbaren Aktionen.
    """
    # Kampf-Management
    encounter: CombatEncounter
    player_characters: List[CharacterInstance]
    opponent_characters: List[CharacterInstance]
    
    # Aktueller Zustand
    current_round: int = 0
    current_character_index: int = 0
    current_character: Optional[CharacterInstance] = None
    is_player_turn: bool = False
    available_actions: List[int] = field(default_factory=list)
    valid_targets: List[CharacterInstance] = field(default_factory=list)
    
    # Verlaufsinformationen für Belohnungsberechnung
    last_action_result: Dict[str, Any] = field(default_factory=dict)
    combat_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Episode-Informationen
    episode_done: bool = False
    episode_reward: float = 0.0
    step_count: int = 0
    max_steps: int = 200  # Verhindert unendliche Episoden
    
    # Training-Konfiguration
    curriculum_level: int = 1
    
    def __post_init__(self):
        """Initialisierung nach der Erstellung des Objekts."""
        # Den aktuellen Charakter festlegen, falls nicht bereits gesetzt
        if self.encounter and not self.current_character:
            self._update_current_character()
    
    def _update_current_character(self) -> None:
        """
        Aktualisiert den aktuellen Charakter basierend auf dem Index und der Zugreihenfolge.
        """
        if not self.encounter.turn_order:
            logger.warning("Keine Zugreihenfolge verfügbar.")
            return
        
        if self.current_character_index >= len(self.encounter.turn_order):
            # Wenn wir am Ende der Runde sind, nächste Runde starten
            self.encounter.next_round()
            self.current_round = self.encounter.round
            self.current_character_index = 0
        
        self.current_character = self.encounter.turn_order[self.current_character_index]
        # Prüfen, ob der aktuelle Charakter ein Spieler ist
        self.is_player_turn = self.current_character in self.player_characters
        
        # Gültige Ziele aktualisieren
        self.valid_targets = self.encounter.get_valid_targets(self.is_player_turn)
        
        # Verfügbare Aktionen werden außerhalb aktualisiert (Action Manager)
        logger.debug(f"Aktueller Charakter: {self.current_character.name} (Spieler: {self.is_player_turn})")
    
    def next_character(self) -> None:
        """
        Wechselt zum nächsten Charakter in der Zugreihenfolge.
        """
        self.current_character_index += 1
        self._update_current_character()
    
    def check_episode_done(self) -> bool:
        """
        Prüft, ob die aktuelle Episode beendet ist.
        
        Returns:
            bool: True, wenn die Episode beendet ist, sonst False
        """
        # Prüfen, ob der Kampf beendet ist
        combat_ended = self.encounter.check_combat_end()
        
        # Prüfen, ob die maximale Anzahl an Schritten erreicht ist
        max_steps_reached = self.step_count >= self.max_steps
        
        if combat_ended:
            logger.info(f"Kampf beendet: {self.encounter.winner} haben gewonnen.")
        
        if max_steps_reached:
            logger.warning(f"Maximale Anzahl an Schritten ({self.max_steps}) erreicht.")
        
        self.episode_done = combat_ended or max_steps_reached
        return self.episode_done
    
    def get_state_representation(self) -> Dict[str, Any]:
        """
        Liefert eine vereinfachte Darstellung des aktuellen Zustands für Logging/Debugging.
        
        Returns:
            Dict[str, Any]: Zustandsdarstellung
        """
        player_health_percentage = [
            (pc.hp / pc.get_max_hp()) * 100 if pc.is_alive() else 0 
            for pc in self.player_characters
        ]
        
        opponent_health_percentage = [
            (op.hp / op.get_max_hp()) * 100 if op.is_alive() else 0 
            for op in self.opponent_characters
        ]
        
        return {
            "round": self.current_round,
            "player_turn": self.is_player_turn,
            "current_character": self.current_character.name if self.current_character else "None",
            "player_health_pct": player_health_percentage,
            "opponent_health_pct": opponent_health_percentage,
            "episode_done": self.episode_done,
            "step_count": self.step_count,
        }