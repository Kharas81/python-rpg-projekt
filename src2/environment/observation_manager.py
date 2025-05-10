"""
Observation Manager for RPG Environment

Diese Klasse ist verantwortlich für die Erstellung des Beobachtungsvektors
für die RL-Umgebung.
"""
from typing import Dict, Any, Optional, List
import numpy as np

from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter
from src.definitions.skill import SkillDefinition
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

# --- Konstanten für Observation und Normalisierung ---
# Diese sollten idealerweise aus einer zentralen Konfiguration kommen oder hier als Standardwerte dienen
MAX_ATTRIBUTE_VALUE = 30.0
MAX_DEFENSE_VALUE = 20.0
MAX_RESOURCE_VALUE = 200.0
MAX_HP_VALUE = 200.0 # Wird dynamisch durch max_hp des Charakters ersetzt
MAX_SKILL_COST = 50.0

# Anzahl der Features pro Charakter in der Observation
CHARACTER_FEATURE_SIZE = 15 # Wie in RPGEnv definiert

# Maximale Anzahl an Skills, die im Obs/Action Space repräsentiert werden
AGENT_MAX_SKILLS_OBS_ACTION = 5 # Wie in RPGEnv definiert

# Features pro Skill in der Observation
SKILL_FEATURE_SIZE = 2 # Wie in RPGEnv definiert


class ObservationManager:
    def __init__(self,
                 max_allies: int,
                 max_enemies: int,
                 character_feature_size: int = CHARACTER_FEATURE_SIZE,
                 agent_max_skills: int = AGENT_MAX_SKILLS_OBS_ACTION,
                 skill_feature_size: int = SKILL_FEATURE_SIZE):
        self.max_allies = max_allies
        self.max_enemies = max_enemies
        self.character_feature_size = character_feature_size
        self.agent_max_skills = agent_max_skills
        self.skill_feature_size = skill_feature_size

        self.observation_shape_agent = self.character_feature_size
        self.observation_shape_allies = self.max_allies * self.character_feature_size
        self.observation_shape_enemies = self.max_enemies * self.character_feature_size
        self.observation_shape_skills = self.agent_max_skills * self.skill_feature_size
        
        self.total_observation_size = (
            self.observation_shape_agent +
            self.observation_shape_allies +
            self.observation_shape_enemies +
            self.observation_shape_skills
        )
        logger.info(f"ObservationManager initialisiert. Erwartete Observation Size: {self.total_observation_size}")


    def _normalize(self, value: float, max_value: float, min_value: float = 0.0) -> float:
        if max_value == min_value: # Verhindert Division durch Null, wenn min und max gleich sind
            return 0.0 if value == min_value else (1.0 if value > min_value else -1.0) # Oder eine andere Logik
        
        # Normalisiert auf [0, 1] wenn min_value=0, ansonsten auf einen entsprechenden Bereich
        normalized = (value - min_value) / (max_value - min_value)
        
        # Für Box Space [-1, 1] könnte man 2*normalized - 1 rechnen, wenn die Rohwerte immer positiv sind.
        # Hier clippen wir einfach, was für die meisten Features (0-1 Normalisierung) passt.
        return np.clip(normalized, 0.0, 1.0) # Clip auf [0,1] für die meisten Features

    def _get_character_features(self, character: Optional[CharacterInstance]) -> np.ndarray:
        if character is None or not character.is_alive():
            return np.zeros(self.character_feature_size, dtype=np.float32)

        features = np.zeros(self.character_feature_size, dtype=np.float32)
        
        # Dynamische max_hp für präzisere Normalisierung
        char_max_hp = character.get_max_hp() if character.get_max_hp() > 0 else MAX_HP_VALUE
        features[0] = self._normalize(character.hp, char_max_hp)
        
        char_max_mana = character.base_combat_values.get('base_mana', 0)
        features[1] = self._normalize(character.mana, char_max_mana if char_max_mana > 0 else MAX_RESOURCE_VALUE)
        
        char_max_stamina = character.base_combat_values.get('base_stamina', 0)
        features[2] = self._normalize(character.stamina, char_max_stamina if char_max_stamina > 0 else MAX_RESOURCE_VALUE)
        
        char_max_energy = character.base_combat_values.get('base_energy', 0)
        features[3] = self._normalize(character.energy, char_max_energy if char_max_energy > 0 else MAX_RESOURCE_VALUE)
        
        features[4] = 1.0  # is_alive

        features[5] = self._normalize(character.get_attribute('STR'), MAX_ATTRIBUTE_VALUE)
        features[6] = self._normalize(character.get_attribute('DEX'), MAX_ATTRIBUTE_VALUE)
        features[7] = self._normalize(character.get_attribute('INT'), MAX_ATTRIBUTE_VALUE)
        features[8] = self._normalize(character.get_attribute('CON'), MAX_ATTRIBUTE_VALUE)
        features[9] = self._normalize(character.get_attribute('WIS'), MAX_ATTRIBUTE_VALUE)

        features[10] = self._normalize(character.get_combat_value('armor'), MAX_DEFENSE_VALUE)
        features[11] = self._normalize(character.get_combat_value('magic_resist'), MAX_DEFENSE_VALUE)

        features[12] = 1.0 if 'STUNNED' in character.active_effects else 0.0
        features[13] = 1.0 if 'BURNING' in character.active_effects else 0.0
        features[14] = 1.0 if 'SLOWED' in character.active_effects else 0.0
        
        return features

    def _get_skill_features(self,
                             agent_character: Optional[CharacterInstance],
                             agent_skill_map: List[Optional[SkillDefinition]]
                             ) -> np.ndarray:
        skill_features_list = []
        for skill_def in agent_skill_map:  # Iteriere über die festen Skill-Slots
            if skill_def and agent_character:
                usable = 1.0 if agent_character.has_enough_resource(skill_def) else 0.0
                cost_norm = self._normalize(skill_def.get_cost_value(), MAX_SKILL_COST)
                skill_features_list.extend([usable, cost_norm])
            else:
                skill_features_list.extend([0.0, 0.0])  # Padding
        return np.array(skill_features_list, dtype=np.float32)

    def get_observation(self,
                        agent_character: Optional[CharacterInstance],
                        current_encounter: Optional[CombatEncounter],
                        agent_skill_map: List[Optional[SkillDefinition]]
                        ) -> np.ndarray:
        obs_parts = []

        # 1. Agenten-Features
        obs_parts.append(self._get_character_features(agent_character))

        # 2. Verbündeten-Features (gepaddingt)
        allies_in_encounter = []
        if current_encounter and agent_character:
            allies_in_encounter = [p for p in current_encounter.players if p != agent_character and p.is_alive()]
        
        for i in range(self.max_allies):
            ally = allies_in_encounter[i] if i < len(allies_in_encounter) else None
            obs_parts.append(self._get_character_features(ally))

        # 3. Gegner-Features (gepaddingt)
        enemies_in_encounter = []
        if current_encounter:
            enemies_in_encounter = [o for o in current_encounter.opponents if o.is_alive()]

        for i in range(self.max_enemies):
            enemy = enemies_in_encounter[i] if i < len(enemies_in_encounter) else None
            obs_parts.append(self._get_character_features(enemy))
            
        # 4. Skill-Features des Agenten
        obs_parts.append(self._get_skill_features(agent_character, agent_skill_map))
        
        final_obs = np.concatenate(obs_parts).astype(np.float32)
        
        if final_obs.shape[0] != self.total_observation_size:
            logger.error(f"ObservationManager: Shape mismatch! Expected {self.total_observation_size}, got {final_obs.shape[0]}. Check feature sizes and max counts.")
            # Notfall-Anpassung (sollte nicht passieren)
            if final_obs.shape[0] > self.total_observation_size:
                final_obs = final_obs[:self.total_observation_size]
            else:
                padding = np.zeros(self.total_observation_size - final_obs.shape[0], dtype=np.float32)
                final_obs = np.concatenate([final_obs, padding])
        return final_obs