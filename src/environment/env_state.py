"""
Verwaltet den Zustand der Umgebung für Reinforcement Learning.
Diese Klasse kapselt den gesamten für das RL relevanten Spielzustand.
"""
from typing import Dict, List, Any, Optional
import copy
import numpy as np
import json5
from src.game_logic.entities import CharacterInstance
from src.config.config import get_config


class EnvState:
    """
    Speichert und verwaltet den Zustand der Gym-Umgebung für das RL-Training.
    Hält Referenzen auf alle relevanten Spielobjekte (Charaktere, Gegner) und deren Status.
    """
    
    def __init__(self):
        """
        Initialisiert einen neuen, leeren Umgebungszustand.
        """
        # Spielerkonfiguration
        self.config = get_config()
        
        # Spielcharaktere (player_characters) und Gegner (opponents)
        self.player_characters: List[CharacterInstance] = []
        self.opponents: List[CharacterInstance] = []
        
        # Aktuelle Runde und welcher Charakter am Zug ist
        self.current_round: int = 0
        self.current_actor_idx: int = 0  # Index des aktuellen Akteurs in der Initiative-Reihenfolge
        
        # Initiative-Reihenfolge (enthält Indizes der Spieler und Gegner)
        self.initiative_order: List[Dict[str, Any]] = []
        
        # Flag ob das Spiel zu Ende ist
        self.is_done: bool = False
        
        # Belohnungssystem (für das RL)
        self.accumulated_reward: float = 0.0
        self.last_action_reward: float = 0.0
        
        # Kampf-Runden-Historie (für Feature-Engineering und Nachanalyse)
        self.combat_history: List[Dict[str, Any]] = []
        
    def reset(self, player_templates: List[str] = None, opponent_templates: List[str] = None) -> None:
        """
        Setzt den Umgebungszustand zurück und initialisiert einen neuen Kampf.

        Args:
            player_templates: Liste der Spielercharakter-Templates, die verwendet werden sollen.
            opponent_templates: Liste der Gegner-Templates, die verwendet werden sollen.
        """
        # Hier würde die Logik für das Erstellen neuer Charaktere und Gegner basierend auf Templates kommen
        # Sowie die Initialisierung des Kampfes (Initiative-Reihenfolge etc.)
        
        # In einer vollständigen Implementierung würden wir hier:
        # 1. Charaktere und Gegner aus den Templates erstellen
        # 2. Sie im Zustand speichern
        # 3. Die Initiative-Reihenfolge berechnen
        # 4. Den Kampf initialisieren
        
        self.current_round = 0
        self.current_actor_idx = 0
        self.is_done = False
        self.accumulated_reward = 0.0
        self.last_action_reward = 0.0
        self.combat_history = []
    
    def get_current_actor(self) -> Optional[CharacterInstance]:
        """
        Gibt den aktuell handelnden Charakter zurück.
        
        Returns:
            CharacterInstance: Der aktuelle Akteur oder None, wenn der Kampf beendet ist.
        """
        if self.is_done or not self.initiative_order:
            return None
        
        actor_data = self.initiative_order[self.current_actor_idx]
        if actor_data['type'] == 'player':
            return self.player_characters[actor_data['index']]
        else:  # opponent
            return self.opponents[actor_data['index']]
    
    def is_current_actor_player(self) -> bool:
        """
        Prüft, ob der aktuelle Akteur ein Spielercharakter ist.
        
        Returns:
            bool: True wenn der aktuelle Akteur ein Spielercharakter ist, sonst False.
        """
        if not self.initiative_order:
            return False
        return self.initiative_order[self.current_actor_idx]['type'] == 'player'
    
    def advance_to_next_actor(self) -> None:
        """
        Geht zum nächsten Akteur in der Initiative-Reihenfolge über.
        Erhöht die Rundenzahl, wenn alle Charaktere an der Reihe waren.
        """
        if self.is_done:
            return
            
        self.current_actor_idx = (self.current_actor_idx + 1) % len(self.initiative_order)
        
        # Wenn wir wieder am Anfang der Initiative-Reihenfolge sind, beginnt eine neue Runde
        if self.current_actor_idx == 0:
            self.current_round += 1
            self._apply_round_effects()
    
    def _apply_round_effects(self) -> None:
        """
        Wendet Rundeneffekte auf alle Charaktere an (z.B. DoT-Effekte, Dauer von Status-Effekten).
        """
        # Hier würden wir über alle Charaktere iterieren und DoT-Effekte, Cooldowns etc. aktualisieren
        # In einer vollständigen Implementierung würden wir auch prüfen, ob der Kampf beendet ist
        
        # Beispiel (nicht vollständig):
        all_characters = self.player_characters + self.opponents
        for character in all_characters:
            if hasattr(character, 'apply_dot_effects'):
                character.apply_dot_effects()
            
            # Statuseffekte reduzieren
            if hasattr(character, 'reduce_effect_durations'):
                character.reduce_effect_durations()
        
        # Prüfen, ob alle Spieler oder alle Gegner besiegt sind
        self._check_combat_end()
    
    def _check_combat_end(self) -> None:
        """
        Prüft, ob der Kampf beendet ist (alle Spieler oder alle Gegner besiegt).
        """
        all_players_defeated = all(not pc.is_alive() for pc in self.player_characters) if self.player_characters else True
        all_opponents_defeated = all(not opp.is_alive() for opp in self.opponents) if self.opponents else True
        
        if all_players_defeated or all_opponents_defeated:
            self.is_done = True
            
            # Belohnung für Sieg/Niederlage
            if all_opponents_defeated and not all_players_defeated:
                # Sieg: Positive Belohnung
                self.last_action_reward += self.config.get('rl_settings', {}).get('victory_reward', 10.0)
                self.accumulated_reward += self.last_action_reward
            elif all_players_defeated:
                # Niederlage: Negative Belohnung
                self.last_action_reward += self.config.get('rl_settings', {}).get('defeat_penalty', -10.0)
                self.accumulated_reward += self.last_action_reward
    
    def deep_copy(self) -> 'EnvState':
        """
        Erstellt eine tiefe Kopie des aktuellen Umgebungszustands.
        
        Returns:
            EnvState: Eine tiefe Kopie des aktuellen Zustands.
        """
        return copy.deepcopy(self)
    
    def get_serializable_state(self) -> Dict[str, Any]:
        """
        Gibt eine serialisierbare Version des Zustands zurück (für Logging, Debugging).
        
        Returns:
            Dict[str, Any]: Eine serialisierbare Version des Zustands.
        """
        # Hier würden wir eine vereinfachte, JSON-serialisierbare Version des Zustands erstellen
        # Diese könnte für Logging, Debugging oder das Speichern von Trainingsdaten verwendet werden
        state_dict = {
            'current_round': self.current_round,
            'current_actor_idx': self.current_actor_idx,
            'is_done': self.is_done,
            'accumulated_reward': self.accumulated_reward,
            'player_characters': [self._character_to_dict(pc) for pc in self.player_characters],
            'opponents': [self._character_to_dict(opp) for opp in self.opponents],
        }
        return state_dict
    
    def _character_to_dict(self, character: CharacterInstance) -> Dict[str, Any]:
        """
        Konvertiert ein CharacterInstance-Objekt in ein serialisierbares Dictionary.
        
        Args:
            character: Das zu konvertierende CharacterInstance-Objekt.
            
        Returns:
            Dict[str, Any]: Ein serialisierbares Dictionary mit den wichtigsten Charakter-Attributen.
        """
        # Hier extrahieren wir die wichtigsten Attribute des Charakters für die Serialisierung
        # In einer vollständigen Implementierung würden wir eine umfassendere Konvertierung vornehmen
        char_dict = {
            'id': getattr(character, 'id', 'unknown'),
            'name': getattr(character, 'name', 'unknown'),
            'is_alive': character.is_alive() if hasattr(character, 'is_alive') else False,
            'hp': getattr(character, 'hp', 0),
            'max_hp': getattr(character, 'max_hp', 0),
        }
        
        # Füge weitere Attribute hinzu, wenn sie existieren
        for attr in ['mana', 'stamina', 'energy', 'armor', 'magic_resist']:
            if hasattr(character, attr):
                char_dict[attr] = getattr(character, attr)
        
        return char_dict
