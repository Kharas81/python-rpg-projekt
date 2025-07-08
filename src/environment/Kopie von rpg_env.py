# src/environment/rpg_env.py
# V20: Behebt den finalen KeyError für 'is_success'.

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import logging
from typing import Dict, Any, Optional, List, Tuple, SupportsFloat, Union

from src.game_logic.entities import CharacterInstance
from src.environment.state_manager import EnvStateManager
from src.environment.reward_manager import RewardManager
from src.environment.observation_manager import ObservationManager
from src.environment.action_manager import ActionManager
from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates, load_item_templates
from src.definitions.skill import SkillTemplate
from src.definitions.item import ItemTemplate
from src.game_logic.combat import constants as COMBAT_CONSTANTS
from src.config.config import CONFIG

logger = logging.getLogger(__name__)

class RPGEnv(gym.Env):
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 10}
    
    def __init__(self, env_config: Dict[str, Any]):
        super().__init__()
        self.env_config = env_config
        self.hero_id: str = env_config.get("hero_id", "krieger")
        self.opponent_setup: Dict[str, Any] = env_config.get("opponent_setup", {})
        self.max_steps: int = env_config.get("max_episode_steps", 100)
        
        self.character_templates = load_character_templates()
        self.opponent_templates = load_opponent_templates()
        self.item_templates = load_item_templates()
        self.skill_templates_global: Dict[str, SkillTemplate] = load_skill_templates()
        
        self.reward_manager = RewardManager(env_config.get("reward_weights"))
        self.state_manager = EnvStateManager(
            character_templates=self.character_templates,
            opponent_templates=self.opponent_templates,
            max_supported_opponents=3,
            reward_manager_instance=self.reward_manager 
        )
        current_hero_template = self.character_templates.get(self.hero_id)
        if not current_hero_template: raise RuntimeError(f"Hero template '{self.hero_id}' not found.")
        hero_initial_skills_ordered = list(current_hero_template.starting_skills)
        self.action_manager = ActionManager(skill_templates=self.skill_templates_global, hero_initial_skill_ids=hero_initial_skills_ordered)
        self.observation_manager = ObservationManager(skill_templates=self.skill_templates_global, hero_starting_skills_ids_ordered=hero_initial_skills_ordered)
        self.action_space = self.action_manager.get_action_space()
        self.observation_space = self.observation_manager.get_observation_space()

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.current_step_in_episode = 0
        current_opponent_setup = options.get("opponent_setup", self.opponent_setup) if options else self.opponent_setup
        self.state_manager.reset_state(self.hero_id, current_opponent_setup)
        
        hero = self.state_manager.get_hero()
        if hero:
            potion = self.item_templates.get("potion_health_small")
            if potion: hero.inventory.add_item(potion)
        
        self.reward_manager.reset_step_states()
        observation = self.observation_manager.get_observation(self.state_manager)
        
        # Das Info-Dict von reset() muss auch die erwarteten Schlüssel enthalten.
        info = self._get_info(terminated=False, truncated=False, term_message="")
        return observation, info

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, SupportsFloat, bool, bool, Dict[str, Any]]:
        self.current_step_in_episode += 1
        self.state_manager.increment_step()
        self.reward_manager.reset_step_states()
        hero = self.state_manager.get_hero()
        if not hero: return self.observation_space.sample(), -100.0, True, False, {"error": "Hero is None"}

        self.reward_manager.record_hp_at_action_start(self.state_manager.get_all_live_participants())
        action_int = int(action.item())
        
        game_action_tuple = self.action_manager.get_game_action(action_int, self.state_manager)
        
        if game_action_tuple is None:
            logger.error(f"KRITISCHER DEKODIERFEHLER für Aktion {action_int}.")
            return self.observation_space.sample(), -100.0, True, False, {"error": "Action decoding failed"}
        
        action_type, action_data, primary_target_instance = game_action_tuple
        
        was_beneficial_context = False
        if action_type == "SKILL" and action_data == COMBAT_CONSTANTS.SKILL_KRIEGER_KAMPFRAUSCH:
            res_val, res_max = hero.get_primary_resource_values()
            threshold = CONFIG.get("game_settings.resource_skill_beneficial_threshold", 0.3)
            if res_max > 0 and (res_val / res_max) < threshold: was_beneficial_context = True
            self.state_manager.execute_hero_action(action_data, primary_target_instance, was_beneficial_context)
        elif action_type == "ITEM":
            item_template: 'ItemTemplate' = action_data
            if item_template.direct_effects and item_template.direct_effects.base_healing is not None:
                hp_perc = hero.current_hp / hero.max_hp if hero.max_hp > 0 else 1.0
                threshold = CONFIG.get("game_settings.healing_item_beneficial_threshold", 0.5)
                if hp_perc < threshold: was_beneficial_context = True
            self.state_manager.execute_item_action(action_data, primary_target_instance, was_beneficial_context)
        else:
            self.state_manager.execute_hero_action(action_data, primary_target_instance, was_beneficial_context)
        
        terminated, hero_won, term_message = self.state_manager.check_combat_end_conditions()
        if not terminated:
            self.state_manager.run_opponent_turns()
            terminated, hero_won, term_message = self.state_manager.check_combat_end_conditions()

        step_reward_hero, hero_components = self.reward_manager.calculate_reward_for_hero_action(self.state_manager)
        step_reward_npc, npc_components = self.reward_manager.calculate_reward_for_npc_turn_outcomes(self.state_manager)
        current_step_reward = float(step_reward_hero) + float(step_reward_npc)
        
        is_truncated = self.current_step_in_episode >= self.max_steps and not terminated
        final_ep_reward, final_components = self.reward_manager.get_final_episode_rewards(self.state_manager, max_steps_reached=is_truncated)
        current_step_reward += float(final_ep_reward)

        info = self._get_info(terminated, is_truncated, term_message)
        info["reward_components"] = {**hero_components, **npc_components, **final_components}
        
        observation = self.observation_manager.get_observation(self.state_manager)
        return observation, current_step_reward, terminated, is_truncated, info

    # KORREKTUR: Diese Methode baut jetzt das vollständige info-Dict.
    def _get_info(self, terminated: bool, truncated: bool, term_message: str) -> Dict[str, Any]:
        hero = self.state_manager.get_hero()
        hero_won = hero and not hero.is_defeated and not self.state_manager.get_live_opponents()
        
        info = {
            "is_success": hero_won,
            "termination_reason": "N/A"
        }
        
        if terminated:
            info["termination_reason"] = term_message
        elif truncated:
            info["termination_reason"] = "Max steps reached"
            
        return info

    def action_masks(self) -> List[bool]:
        return self.action_manager.get_action_mask(self.state_manager)

    def close(self):
        pass