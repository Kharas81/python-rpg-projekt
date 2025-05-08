"""
Reward Calculator

Berechnet die Belohnungen für das RL-Training basierend auf Spielaktionen und -ergebnissen.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np

from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatResult
from src.utils.logging_setup import get_logger

# Logger für dieses Modul
logger = get_logger(__name__)


class RewardCalculator:
    """
    Berechnet die Belohnungen für das RL-Training.
    
    Implementiert verschiedene Belohnungsfunktionen für verschiedene Aspekte des Spiels,
    wie z.B. Schaden, Heilung, Überlebensraten etc.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialisiert den Reward Calculator mit Konfiguration.
        
        Args:
            config (Optional[Dict[str, Any]]): Konfiguration für die Belohnungsberechnung
        """
        self.config = config or {}
        
        # Gewichte für verschiedene Belohnungskomponenten
        self.weights = {
            'damage_dealt': self.config.get('weight_damage', 1.0),
            'healing_done': self.config.get('weight_healing', 1.2),
            'kill_reward': self.config.get('weight_kill', 5.0),
            'death_penalty': self.config.get('weight_death', -10.0),
            'victory_reward': self.config.get('weight_victory', 20.0),
            'defeat_penalty': self.config.get('weight_defeat', -15.0),
            'action_penalty': self.config.get('weight_action', -0.05),  # Kleiner Malus für jede Aktion
            'efficient_skill_reward': self.config.get('weight_efficiency', 0.5),
            'low_health_ally_heal_reward': self.config.get('weight_clutch_heal', 2.0),
            'status_effect_reward': self.config.get('weight_status', 0.8),
        }
        
        logger.info(f"RewardCalculator initialisiert mit Gewichten: {self.weights}")
    
    def calculate_reward(self, 
                       is_player_turn: bool, 
                       action_result: CombatResult,
                       character: CharacterInstance,
                       targets: List[CharacterInstance],
                       player_characters: List[CharacterInstance],
                       opponent_characters: List[CharacterInstance],
                       winner: Optional[str] = None) -> float:
        """
        Berechnet die Gesamtbelohnung basierend auf dem Ergebnis der Aktion.
        
        Args:
            is_player_turn (bool): Ist es ein Spielerzug?
            action_result (CombatResult): Das Ergebnis der Aktion
            character (CharacterInstance): Der ausführende Charakter
            targets (List[CharacterInstance]): Die Ziele der Aktion
            player_characters (List[CharacterInstance]): Alle Spielercharaktere
            opponent_characters (List[CharacterInstance]): Alle Gegner
            winner (Optional[str]): Der Gewinner des Kampfes, falls der Kampf beendet wurde
            
        Returns:
            float: Die berechnete Belohnung
        """
        # Basisbelohnung initialisieren
        reward = 0.0
        
        # 1. Belohnung für zugefügten Schaden
        damage_reward = self._calculate_damage_reward(is_player_turn, action_result)
        reward += damage_reward
        
        # 2. Belohnung für Heilung
        healing_reward = self._calculate_healing_reward(is_player_turn, action_result, player_characters, opponent_characters)
        reward += healing_reward
        
        # 3. Belohnung für Kills/Todesfälle
        kill_death_reward = self._calculate_kill_death_reward(is_player_turn, action_result)
        reward += kill_death_reward
        
        # 4. Belohnung für Kampfergebnis
        if winner:
            victory_defeat_reward = self._calculate_victory_defeat_reward(is_player_turn, winner)
            reward += victory_defeat_reward
        
        # 5. Belohnung für Status-Effekte
        status_reward = self._calculate_status_effect_reward(is_player_turn, action_result)
        reward += status_reward
        
        # 6. Kleiner Malus für jede Aktion (fördert Effizienz)
        reward += self.weights['action_penalty']
        
        # Logging für Debugging
        logger_components = [
            f"Gesamt: {reward:.2f}",
            f"Schaden: {damage_reward:.2f}",
            f"Heilung: {healing_reward:.2f}",
            f"Kills/Tod: {kill_death_reward:.2f}",
            f"Status: {status_reward:.2f}",
        ]
        if winner:
            victory_defeat_reward = self._calculate_victory_defeat_reward(is_player_turn, winner)
            logger_components.append(f"Sieg/Niederlage: {victory_defeat_reward:.2f}")
        
        logger.debug(f"Reward-Komponenten: {', '.join(logger_components)}")
        
        return reward
    
    def _calculate_damage_reward(self, is_player_turn: bool, result: CombatResult) -> float:
        """
        Berechnet die Belohnung basierend auf dem zugefügten Schaden.
        
        Args:
            is_player_turn (bool): Ist es ein Spielerzug?
            result (CombatResult): Das Ergebnis der Aktion
            
        Returns:
            float: Die berechnete Belohnung
        """
        total_damage = sum(result.damage_dealt.values())
        weight = self.weights['damage_dealt']
        
        # Für den Spieler ist Schaden positiv, für Gegner negativ
        reward = total_damage * weight if is_player_turn else -total_damage * weight
        
        # Normalisierung für höhere Schadenswerte
        normalized_reward = np.tanh(reward / 20.0) * weight * 2.0  # Sättigt bei hohen Werten
        
        return normalized_reward
    
    def _calculate_healing_reward(self, 
                               is_player_turn: bool, 
                               result: CombatResult,
                               player_characters: List[CharacterInstance],
                               opponent_characters: List[CharacterInstance]) -> float:
        """
        Berechnet die Belohnung basierend auf der durchgeführten Heilung.
        
        Args:
            is_player_turn (bool): Ist es ein Spielerzug?
            result (CombatResult): Das Ergebnis der Aktion
            player_characters (List[CharacterInstance]): Alle Spielercharaktere
            opponent_characters (List[CharacterInstance]): Alle Gegner
            
        Returns:
            float: Die berechnete Belohnung
        """
        if not result.healing_done:
            return 0.0
            
        allies = player_characters if is_player_turn else opponent_characters
        enemies = opponent_characters if is_player_turn else player_characters
        
        total_reward = 0.0
        
        for target, healing in result.healing_done.items():
            # Belohnung basierend auf der Heilungsmenge
            base_reward = healing * self.weights['healing_done']
            
            # Höhere Belohnung für Heilung von Verbündeten mit wenig HP
            if target in allies:
                hp_percentage = target.hp / target.get_max_hp() if target.get_max_hp() > 0 else 0
                
                # Extra-Belohnung für Heilung eines Verbündeten mit wenig HP (<= 30%)
                if hp_percentage <= 0.3:
                    clutch_factor = (0.3 - hp_percentage) / 0.3  # 0 bis 1, je weniger HP desto höher
                    base_reward += healing * self.weights['low_health_ally_heal_reward'] * clutch_factor
                
                total_reward += base_reward
            else:
                # Bestrafung für Heilung von Gegnern
                total_reward -= base_reward
        
        # Normalisierung, um sehr hohe Belohnungen zu vermeiden
        normalized_reward = np.tanh(total_reward / 15.0) * self.weights['healing_done'] * 2.0
        
        return normalized_reward if is_player_turn else -normalized_reward
    
    def _calculate_kill_death_reward(self, is_player_turn: bool, result: CombatResult) -> float:
        """
        Berechnet die Belohnung basierend auf Kills und Todesfällen.
        
        Args:
            is_player_turn (bool): Ist es ein Spielerzug?
            result (CombatResult): Das Ergebnis der Aktion
            
        Returns:
            float: Die berechnete Belohnung
        """
        reward = 0.0
        
        for death in result.deaths:
            # Prüfen, ob der Tod im Kontext gut oder schlecht ist
            is_player_character = any(pc.id == death.id for pc in result.deaths)
            
            if is_player_turn:
                # Spieler tötet Gegner: Belohnung
                # Spieler tötet Verbündeten (kann bei AOE passieren): Bestrafung
                if not is_player_character:
                    reward += self.weights['kill_reward']
                else:
                    reward += self.weights['death_penalty']
            else:
                # Gegner tötet Spieler: Bestrafung
                # Gegner tötet Verbündeten: Belohnung
                if is_player_character:
                    reward += self.weights['death_penalty']
                else:
                    reward += self.weights['kill_reward']
        
        return reward if is_player_turn else -reward
    
    def _calculate_victory_defeat_reward(self, is_player_turn: bool, winner: str) -> float:
        """
        Berechnet die Belohnung basierend auf dem Kampfergebnis.
        
        Args:
            is_player_turn (bool): Ist es ein Spielerzug?
            winner (str): Der Gewinner des Kampfes
            
        Returns:
            float: Die berechnete Belohnung
        """
        if winner == 'players':
            return self.weights['victory_reward'] if is_player_turn else self.weights['defeat_penalty']
        elif winner == 'opponents':
            return self.weights['defeat_penalty'] if is_player_turn else self.weights['victory_reward']
        else:
            return 0.0  # Unentschieden oder unbestimmt
    
    def _calculate_status_effect_reward(self, is_player_turn: bool, result: CombatResult) -> float:
        """
        Berechnet die Belohnung basierend auf angewendeten Status-Effekten.
        
        Args:
            is_player_turn (bool): Ist es ein Spielerzug?
            result (CombatResult): Das Ergebnis der Aktion
            
        Returns:
            float: Die berechnete Belohnung
        """
        if not result.effects_applied:
            return 0.0
            
        total_effects = 0
        
        for target, effects in result.effects_applied.items():
            # Positive Effekte auf Verbündete, negative auf Feinde
            is_player_character = hasattr(target, 'is_player') and target.is_player
            
            for effect in effects:
                # Vereinfachte Logik: Annahme, dass bestimmte Effekte positiv/negativ sind
                # In einer echten Implementierung müsste man differenzierter vorgehen
                positive_effects = {'SHIELDED', 'DEFENSE_UP', 'INITIATIVE_UP'}
                negative_effects = {'STUNNED', 'WEAKENED', 'SLOWED', 'BURNING', 'ACCURACY_DOWN'}
                
                if effect in positive_effects:
                    # Positive Effekte sind gut für Verbündete, schlecht für Feinde
                    if (is_player_turn and is_player_character) or (not is_player_turn and not is_player_character):
                        total_effects += 1
                    else:
                        total_effects -= 1
                elif effect in negative_effects:
                    # Negative Effekte sind gut für Feinde, schlecht für Verbündete
                    if (is_player_turn and not is_player_character) or (not is_player_turn and is_player_character):
                        total_effects += 1
                    else:
                        total_effects -= 1
        
        return total_effects * self.weights['status_effect_reward'] if is_player_turn else -total_effects * self.weights['status_effect_reward']