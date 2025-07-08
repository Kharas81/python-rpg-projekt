# src/environment/observation_manager.py
# V8: Fügt Execute-Range-Flags für Gegner zum Observation Space hinzu.
import numpy as np
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from gymnasium import spaces

if TYPE_CHECKING:
    from src.game_logic.interfaces import StateManagerInterface
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate

from src.config.config import CONFIG

logger = logging.getLogger(__name__)

MAX_SKILLS_OBS = 6
MAX_OPPONENTS_OBS = 3

class ObservationManager:
    def __init__(self,
                 skill_templates: Dict[str, 'SkillTemplate'],
                 hero_starting_skills_ids_ordered: List[str]):
        
        self.skill_templates = skill_templates
        self.observed_hero_skill_ids = hero_starting_skills_ids_ordered[:MAX_SKILLS_OBS]

        num_hero_features = 4 + MAX_SKILLS_OBS # HP, Schild, Ressource, can_act
        # KORREKTUR: 3 Features pro Gegner (HP, is_alive, is_in_execute_range)
        num_features_per_opponent = 3 
        self.total_observation_features = num_hero_features + (MAX_OPPONENTS_OBS * num_features_per_opponent)
        
        self.observation_space = spaces.Box(
            low=0, high=1, shape=(self.total_observation_features,), dtype=np.float32
        )
        logger.info(f"ObservationManager initialisiert. Observation Space Shape: {self.observation_space.shape}")

    def get_observation_space(self) -> spaces.Box:
        return self.observation_space

    def get_observation(self, gsm: 'StateManagerInterface') -> np.ndarray:
        obs_list = []
        hero = gsm.get_hero()

        # Held-Informationen (unverändert)
        if hero and not hero.is_defeated:
            obs_list.append(hero.current_hp / hero.max_hp if hero.max_hp > 0 else 0.0)
            obs_list.append(hero.shield_points / hero.max_hp if hero.max_hp > 0 and hero.shield_points > 0 else 0.0)
            res_val, res_max = hero.get_primary_resource_values()
            obs_list.append(res_val / res_max if res_max > 0 else 0.0)
            obs_list.append(1.0 if hero.can_act else 0.0)
            for i in range(MAX_SKILLS_OBS):
                if i < len(self.observed_hero_skill_ids):
                    skill_id = self.observed_hero_skill_ids[i]
                    skill_template = self.skill_templates.get(skill_id)
                    is_usable = skill_template and hero.can_afford_skill(skill_template)
                    obs_list.append(1.0 if is_usable else 0.0)
                else:
                    obs_list.append(0.0)
        else:
            obs_list.extend([0.0] * (4 + MAX_SKILLS_OBS))

        # Gegner-Informationen (erweitert)
        live_opponents = gsm.get_live_opponents()
        execute_threshold = CONFIG.get("game_settings.execute_skill_hp_threshold_percent", 0.25)

        for i in range(MAX_OPPONENTS_OBS):
            if i < len(live_opponents):
                opponent = live_opponents[i]
                obs_list.append(opponent.current_hp / opponent.max_hp if opponent.max_hp > 0 else 0.0)
                obs_list.append(1.0) # is_alive
                # NEU: Execute-Flag
                is_in_execute_range = (opponent.current_hp / opponent.max_hp) < execute_threshold if opponent.max_hp > 0 else False
                obs_list.append(1.0 if is_in_execute_range else 0.0)
            else:
                obs_list.extend([0.0, 0.0, 0.0]) # HP, is_alive, is_in_execute_range
        
        if len(obs_list) != self.total_observation_features:
            logger.error(f"Fehler bei Observationserstellung: Länge {len(obs_list)} vs {self.total_observation_features}.")
            obs_list.extend([0.0] * (self.total_observation_features - len(obs_list)))
            obs_list = obs_list[:self.total_observation_features]

        return np.array(obs_list, dtype=np.float32)