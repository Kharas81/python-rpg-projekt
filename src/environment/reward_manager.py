# src/environment/reward_manager.py
# V13: Stellt die fehlenden Methoden wieder her und behebt den AttributeError.

import logging
from typing import List, Dict, Any, Optional, SupportsFloat, Tuple, TYPE_CHECKING

from src.game_logic.combat.interfaces import CombatRewardInterface 
if TYPE_CHECKING:
    from src.game_logic.interfaces import StateManagerInterface
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate
    from src.definitions.item import ItemTemplate
    from src.game_logic.combat.effects.base_effect import StatusEffect

from src.definitions.character import CharacterTemplate
from src.game_logic.combat import constants as COMBAT_CONSTANTS
logger = logging.getLogger(__name__)

class RewardManager(CombatRewardInterface):
    def __init__(self, reward_config: Optional[Dict[str, float]] = None):
        self.config: Dict[str, float] = {
            "step_penalty": -0.05,
            "no_resource_penalty": -2.0,
            "krieger_kampfrausch_bonus": 10.0,
            "heal_bonus_under_50_percent": 15.0,
            "damage_to_opponent_mult": 0.1,
            "all_opponents_defeated_bonus": 50.0,
            "hero_defeated_penalty": -50.0,
            "max_steps_reached_penalty": -25.0,
            "unnecessary_pass_penalty": -30.0,
            "executed_action_bonus": 2.5,
            "stun_opponent_bonus": 5.0,
            "damage_to_hero_penalty_mult": -0.3,
        }
        if reward_config: self.config.update(reward_config)
        self.reset_step_states()

    def reset_step_states(self) -> None:
        self.hp_at_turn_start: Dict[str, int] = {}
        self._insufficient_resources_this_step: bool = False
        self._resource_skill_was_beneficial: bool = False
        self._healing_was_beneficial: bool = False
        self._stun_applied_this_step: bool = False

    def record_hp_at_action_start(self, participants: List['CharacterInstance']):
        self.hp_at_turn_start = {p.instance_id: p.current_hp for p in participants if p}

    def record_event_insufficient_resources(self, actor: 'CharacterInstance', skill_id: str) -> None:
        if isinstance(actor.base_template, CharacterTemplate):
            self._insufficient_resources_this_step = True

    def record_event_resource_management_skill_used(self, actor: 'CharacterInstance', skill: 'SkillTemplate', was_beneficial_context: bool) -> None:
        if isinstance(actor.base_template, CharacterTemplate):
            self._resource_skill_was_beneficial = was_beneficial_context
    
    def record_event_item_used(self, actor: 'CharacterInstance', item: 'ItemTemplate', was_beneficial_context: bool) -> None:
        if isinstance(actor.base_template, CharacterTemplate):
            self._healing_was_beneficial = was_beneficial_context
            
    def record_event_status_effect_applied(self, actor: 'CharacterInstance', target: 'CharacterInstance', effect: 'StatusEffect', skill: 'SkillTemplate') -> None:
        is_hero_action = isinstance(actor.base_template, CharacterTemplate)
        if not is_hero_action: return
        if actor.is_opponent_of(target) and effect.effect_id == COMBAT_CONSTANTS.EFFECT_ID_STUNNED:
            self._stun_applied_this_step = True
    
    # Leere Implementierungen für nicht genutzte Events
    def record_event_execute_kill(self, actor: 'CharacterInstance', target: 'CharacterInstance', skill: 'SkillTemplate') -> None: pass
    def record_event_pass_action(self, actor: 'CharacterInstance', was_unnecessary: bool) -> None: pass
    def record_event_skill_cost_paid(self, actor: 'CharacterInstance', skill: 'SkillTemplate', effective_cost_paid: int, original_cost: int) -> None: pass

    def calculate_reward_for_hero_action(self, state_manager: 'StateManagerInterface') -> Tuple[SupportsFloat, Dict[str, float]]:
        all_components: Dict[str, float] = {}
        total_reward: float = 0.0

        total_reward += self.config.get("step_penalty", -0.05)
        all_components["rew_step_penalty"] = self.config.get("step_penalty", -0.05)

        if self._insufficient_resources_this_step:
            penalty = self.config.get("no_resource_penalty", -2.0)
            total_reward += penalty
            all_components["rew_no_resource_penalty"] = penalty

        if self._resource_skill_was_beneficial:
            bonus = self.config.get("krieger_kampfrausch_bonus", 10.0)
            total_reward += bonus
            all_components["rew_kampfrausch_bonus"] = bonus

        if self._healing_was_beneficial:
            bonus = self.config.get("heal_bonus_under_50_percent", 15.0)
            total_reward += bonus
            all_components["rew_strategic_heal_bonus"] = bonus
            
        if self._stun_applied_this_step:
            bonus = self.config.get("stun_opponent_bonus", 5.0)
            total_reward += bonus
            all_components["rew_stun_opponent_bonus"] = bonus

        return total_reward, all_components
    
    # WIEDERHERGESTELLTE METHODE
    def calculate_reward_for_npc_turn_outcomes(self, state_manager: 'StateManagerInterface') -> Tuple[SupportsFloat, Dict[str, float]]:
        reward_components: Dict[str, float] = {}
        current_reward: float = 0.0
        hero = state_manager.get_hero()
        if not hero: return 0.0, {}
        
        hp_before = self.hp_at_turn_start.get(hero.instance_id, hero.current_hp)
        damage_to_hero = max(0, hp_before - hero.current_hp)
        if damage_to_hero > 0:
            penalty = damage_to_hero * self.config.get("damage_to_hero_penalty_mult", -0.3)
            current_reward += penalty
            reward_components["rew_damage_to_hero_penalty"] = penalty
            
        return current_reward, reward_components

    # WIEDERHERGESTELLTE METHODE
    def get_final_episode_rewards(self, state_manager: 'StateManagerInterface', max_steps_reached: bool) -> Tuple[SupportsFloat, Dict[str, float]]:
        final_reward: float = 0.0
        final_components: Dict[str, float] = {}
        terminated, hero_won, _ = state_manager.check_combat_end_conditions()

        if terminated:
            if hero_won:
                bonus = self.config.get("all_opponents_defeated_bonus", 50.0)
                final_reward += bonus
                final_components["rew_victory_bonus"] = bonus
            else: # Hero lost
                penalty = self.config.get("hero_defeated_penalty", -50.0)
                final_reward += penalty
                final_components["rew_defeat_penalty"] = penalty
        
        if max_steps_reached:
            penalty = self.config.get("max_steps_reached_penalty", -25.0)
            final_reward += penalty
            final_components["rew_max_steps_penalty"] = penalty
            
        return final_reward, final_components