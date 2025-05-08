"""
Observation Manager

Definiert den Beobachtungsraum und übersetzt Spielzustände in Beobachtungsvektoren.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import gymnasium as gym

from src.game_logic.entities import CharacterInstance
from src.environment.env_state import EnvironmentState
from src.utils.logging_setup import get_logger

# Logger für dieses Modul
logger = get_logger(__name__)


class ObservationManager:
    """
    Verwaltet den Beobachtungsraum für das RL-Environment.
    
    Übernimmt die Konvertierung zwischen Spielzustand und Beobachtungsvektor
    für das Reinforcement Learning.
    """
    def __init__(self, 
                max_players: int = 4, 
                max_opponents: int = 6,
                max_skills: int = 10,
                max_status_effects: int = 10,
                feature_size: int = 15):
        """
        Initialisiert den Observation Manager.
        
        Args:
            max_players (int): Maximale Anzahl an Spielercharakteren
            max_opponents (int): Maximale Anzahl an Gegnern
            max_skills (int): Maximale Anzahl an Skills pro Charakter
            max_status_effects (int): Maximale Anzahl an Status-Effekten pro Charakter
            feature_size (int): Anzahl der Features pro Charakter
        """
        self.max_players = max_players
        self.max_opponents = max_opponents
        self.max_skills = max_skills
        self.max_status_effects = max_status_effects
        self.feature_size = feature_size
        
        # Berechnen der Größe des Beobachtungsvektors
        self.player_size = max_players * feature_size
        self.opponent_size = max_opponents * feature_size
        self.skill_size = max_skills * 3  # Skill ID, Kosten, Verfügbarkeit
        self.status_size = max_status_effects * 3  # Effect ID, Dauer, Stärke
        self.global_size = 5  # Runde, aktiver Charakter, etc.
        
        self.observation_size = (
            self.player_size +
            self.opponent_size +
            self.skill_size +
            self.status_size +
            self.global_size
        )
        
        logger.info(f"Observation Space: {self.observation_size} Dimensionen")
    
    def get_observation_space(self) -> gym.spaces.Box:
        """
        Gibt den Beobachtungsraum für das RL-Environment zurück.
        
        Returns:
            gym.spaces.Box: Der kontinuierliche Beobachtungsraum
        """
        # Verwende float32 zur Darstellung des Observation Space
        return gym.spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(self.observation_size,), 
            dtype=np.float32
        )
    
    def observe(self, state: EnvironmentState) -> np.ndarray:
        """
        Konvertiert den aktuellen Spielzustand in einen Beobachtungsvektor.
        
        Args:
            state (EnvironmentState): Der aktuelle Spielzustand
            
        Returns:
            np.ndarray: Der Beobachtungsvektor
        """
        observation = np.zeros(self.observation_size, dtype=np.float32)
        
        # Index für die schrittweise Befüllung des Beobachtungsvektors
        idx = 0
        
        # 1. Spielercharaktere
        idx = self._encode_characters(observation, idx, state.player_characters, self.max_players)
        
        # 2. Gegner
        idx = self._encode_characters(observation, idx, state.opponent_characters, self.max_opponents)
        
        # 3. Skills des aktuellen Charakters
        if state.current_character:
            idx = self._encode_skills(observation, idx, state.current_character)
        else:
            idx += self.skill_size
        
        # 4. Status-Effekte des aktuellen Charakters
        if state.current_character:
            idx = self._encode_status_effects(observation, idx, state.current_character)
        else:
            idx += self.status_size
        
        # 5. Globale Informationen
        # Runde
        observation[idx] = state.current_round / 50.0  # Normalisierung, max 50 Runden angenommen
        idx += 1
        
        # Ist aktueller Charakter ein Spieler?
        observation[idx] = 1.0 if state.is_player_turn else 0.0
        idx += 1
        
        # Aktueller Charakter-Index in der Zugreihenfolge
        if state.encounter.turn_order:
            observation[idx] = state.current_character_index / len(state.encounter.turn_order)
        idx += 1
        
        # Anzahl der noch lebenden Spieler
        alive_players = sum(1 for p in state.player_characters if p.is_alive())
        observation[idx] = alive_players / self.max_players
        idx += 1
        
        # Anzahl der noch lebenden Gegner
        alive_opponents = sum(1 for o in state.opponent_characters if o.is_alive())
        observation[idx] = alive_opponents / self.max_opponents
        
        return observation
    
    def _encode_characters(self, 
                          observation: np.ndarray, 
                          start_idx: int, 
                          characters: List[CharacterInstance], 
                          max_chars: int) -> int:
        """
        Kodiert Charaktereigenschaften in den Beobachtungsvektor.
        
        Args:
            observation (np.ndarray): Der Beobachtungsvektor
            start_idx (int): Startindex im Vektor
            characters (List[CharacterInstance]): Liste der zu kodierenden Charaktere
            max_chars (int): Maximale Anzahl an Charakteren
            
        Returns:
            int: Neuer Index nach den kodierten Charakteren
        """
        idx = start_idx
        
        for char_idx, char in enumerate(characters):
            if char_idx >= max_chars:
                break
                
            # Normalisierte HP (0-1)
            observation[idx] = char.hp / char.get_max_hp() if char.is_alive() else 0.0
            idx += 1
            
            # Normalisierte Ressourcen
            max_mana = char.base_combat_values.get('base_mana', 1)
            observation[idx] = char.mana / max_mana if max_mana > 0 else 0.0
            idx += 1
            
            max_stamina = char.base_combat_values.get('base_stamina', 1)
            observation[idx] = char.stamina / max_stamina if max_stamina > 0 else 0.0
            idx += 1
            
            max_energy = char.base_combat_values.get('base_energy', 1)
            observation[idx] = char.energy / max_energy if max_energy > 0 else 0.0
            idx += 1
            
            # Normalisierte Attribute (STR, DEX, INT, CON, WIS)
            for attr in ['STR', 'DEX', 'INT', 'CON', 'WIS']:
                observation[idx] = char.get_attribute(attr) / 20.0  # Normalisierung, max 20 angenommen
                idx += 1
            
            # Normalisierte Kampfwerte
            observation[idx] = char.get_combat_value('armor') / 15.0  # Normalisierung
            idx += 1
            
            observation[idx] = char.get_combat_value('magic_resist') / 15.0  # Normalisierung
            idx += 1
            
            observation[idx] = char.get_initiative() / 50.0  # Normalisierung
            idx += 1
            
            observation[idx] = char.get_accuracy() / 20.0  # Normalisierung
            idx += 1
            
            observation[idx] = char.get_evasion() / 20.0  # Normalisierung
            idx += 1
            
            # Ist lebendig?
            observation[idx] = 1.0 if char.is_alive() else 0.0
            idx += 1
        
        # Restliche Platzhalter auffüllen
        remaining_chars = max_chars - len(characters)
        if remaining_chars > 0:
            idx += remaining_chars * self.feature_size
        
        return idx
    
    def _encode_skills(self, observation: np.ndarray, start_idx: int, character: CharacterInstance) -> int:
        """
        Kodiert Skills in den Beobachtungsvektor.
        
        Args:
            observation (np.ndarray): Der Beobachtungsvektor
            start_idx (int): Startindex im Vektor
            character (CharacterInstance): Der Charakter mit den Skills
            
        Returns:
            int: Neuer Index nach den kodierten Skills
        """
        idx = start_idx
        
        from src.definitions.skill import get_skill_definition
        
        for skill_idx, skill_id in enumerate(character.skill_ids):
            if skill_idx >= self.max_skills:
                break
                
            try:
                skill_def = get_skill_definition(skill_id)
                
                # Skill-ID (eindeutige ID für den Skill, als Hash kodiert)
                observation[idx] = hash(skill_id) % 1000 / 1000.0  # Normalisierung, Hash-Modulo für kleinere Zahlen
                idx += 1
                
                # Kosten (normalisiert auf 0-1)
                cost_value = skill_def.get_cost_value()
                max_cost = 100.0  # Annahme: Maximale Kosten
                observation[idx] = cost_value / max_cost if max_cost > 0 else 0.0
                idx += 1
                
                # Verfügbarkeit (hat genug Ressourcen?)
                observation[idx] = 1.0 if character.has_enough_resource(skill_def) else 0.0
                idx += 1
                
            except Exception as e:
                logger.error(f"Fehler beim Kodieren des Skills {skill_id}: {e}")
                # Dummy-Werte bei Fehler
                observation[idx:idx+3] = 0.0
                idx += 3
        
        # Restliche Platzhalter auffüllen
        remaining_skills = self.max_skills - len(character.skill_ids)
        if remaining_skills > 0:
            idx += remaining_skills * 3
        
        return idx
    
    def _encode_status_effects(self, observation: np.ndarray, start_idx: int, character: CharacterInstance) -> int:
        """
        Kodiert Status-Effekte in den Beobachtungsvektor.
        
        Args:
            observation (np.ndarray): Der Beobachtungsvektor
            start_idx (int): Startindex im Vektor
            character (CharacterInstance): Der Charakter mit den Status-Effekten
            
        Returns:
            int: Neuer Index nach den kodierten Status-Effekten
        """
        idx = start_idx
        
        for effect_idx, (effect_id, effect) in enumerate(character.active_effects.items()):
            if effect_idx >= self.max_status_effects:
                break
                
            # Effect-ID (eindeutige ID für den Effekt, als Hash kodiert)
            observation[idx] = hash(effect_id) % 1000 / 1000.0  # Normalisierung
            idx += 1
            
            # Dauer (normalisiert auf 0-1)
            max_duration = 10.0  # Annahme: Maximale Dauer
            observation[idx] = effect.duration / max_duration if max_duration > 0 else 0.0
            idx += 1
            
            # Stärke (normalisiert auf 0-1)
            max_potency = 20.0  # Annahme: Maximale Stärke
            observation[idx] = effect.potency / max_potency if max_potency > 0 else 0.0
            idx += 1
        
        # Restliche Platzhalter auffüllen
        remaining_effects = self.max_status_effects - len(character.active_effects)
        if remaining_effects > 0:
            idx += remaining_effects * 3
        
        return idx