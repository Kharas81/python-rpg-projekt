# src/environment/state_manager.py
# V4: Korrigiert die Signatur von execute_hero_action, um den TypeError zu beheben.

import logging
import random
from typing import List, Optional, Dict, Any, Tuple, TYPE_CHECKING

from src.game_logic.entities import CharacterInstance
from src.definitions.character import CharacterTemplate
from src.definitions.opponent import OpponentTemplate
from src.definitions.item import ItemTemplate
from src.ai.ai_dispatcher import get_ai_strategy_instance

from src.game_logic.combat.calculators import CombatCalculator
from src.game_logic.combat.effect_manager import EffectManager
from src.game_logic.combat.skill_executor import SkillExecutor
from src.game_logic.combat.handler import CombatHandler
from src.game_logic.combat.item_executor import ItemExecutor
from src.game_logic.combat import constants as COMBAT_CONSTANTS
from src.ui.cli_output_adapter import CliOutputAdapter

if TYPE_CHECKING:
    from src.environment.reward_manager import RewardManager

logger = logging.getLogger(__name__)

class EnvStateManager:
    def __init__(self,
                 character_templates: Dict[str, CharacterTemplate],
                 opponent_templates: Dict[str, OpponentTemplate],
                 max_supported_opponents: int,
                 reward_manager_instance: Optional['RewardManager'] = None):

        self.character_templates = character_templates
        self.opponent_templates = opponent_templates
        self.max_supported_opponents = max_supported_opponents
        self.output_adapter = CliOutputAdapter()
        self.calculator = CombatCalculator()
        self.effect_manager = EffectManager(output_logger=self.output_adapter)
        self.skill_executor = SkillExecutor(
            calculator=self.calculator,
            effect_manager=self.effect_manager,
            output_logger=self.output_adapter,
            reward_notifier=reward_manager_instance
        )
        self.item_executor = ItemExecutor(
            effect_manager=self.effect_manager,
            output_logger=self.output_adapter,
            reward_notifier=reward_manager_instance
        )
        self.combat_handler = CombatHandler(
            skill_executor=self.skill_executor,
            effect_manager=self.effect_manager,
            output_logger=self.output_adapter
        )
        self.hero: Optional[CharacterInstance] = None
        self.opponents: List[Optional[CharacterInstance]] = [None] * self.max_supported_opponents
        self.all_participants: List[CharacterInstance] = []
        self.current_episode_step: int = 0
        self.last_action_successful: bool = True

    def _create_dynamic_opponent_team(self, opponent_config: Dict[str, Any]) -> List[Optional[CharacterInstance]]:
        new_opponent_list: List[Optional[CharacterInstance]] = [None] * self.max_supported_opponents
        num_opponents_to_create = opponent_config.get("num_opponents", 1)
        level_pool_str = str(opponent_config.get("level_pool", "1-2")).lower()
        specific_ids = opponent_config.get("ids")
        eligible_templates: List[OpponentTemplate] = []
        if specific_ids and isinstance(specific_ids, list):
            for i, opp_id in enumerate(specific_ids):
                if i >= self.max_supported_opponents: break
                template = self.opponent_templates.get(opp_id)
                if template: new_opponent_list[i] = CharacterInstance(base_template=template, name_override=f"{template.name} #{i+1}")
            return new_opponent_list
        min_lvl, max_lvl = -1, -1
        if level_pool_str != "all":
            try:
                parts = level_pool_str.split('-'); min_lvl = int(parts[0]); max_lvl = int(parts[1]) if len(parts) > 1 else min_lvl
            except (ValueError, IndexError): level_pool_str = "all"
        for opp_template in self.opponent_templates.values():
            if level_pool_str == "all" or (hasattr(opp_template, 'level') and min_lvl <= opp_template.level <= max_lvl):
                eligible_templates.append(opp_template)
        if not eligible_templates:
            gob_template = self.opponent_templates.get("goblin_lv1")
            if gob_template: eligible_templates = [gob_template]
            else: return new_opponent_list
        num_to_actually_create = min(num_opponents_to_create, self.max_supported_opponents, len(eligible_templates))
        for i in range(num_to_actually_create):
            if not eligible_templates: break
            chosen_template = random.choice(eligible_templates)
            new_opponent_list[i] = CharacterInstance(base_template=chosen_template, name_override=f"{chosen_template.name} #{i+1}")
        return new_opponent_list

    def reset_state(self, hero_id: str, opponent_setup_config: Dict[str, Any]) -> bool:
        self.current_episode_step = 0
        self.last_action_successful = True
        hero_template = self.character_templates.get(hero_id)
        if not hero_template: return False
        self.hero = CharacterInstance(base_template=hero_template, name_override=hero_template.name)
        self.opponents = self._create_dynamic_opponent_team(opponent_setup_config)
        self._update_all_participants_list()
        return True

    def _update_all_participants_list(self):
        self.all_participants = []
        if self.hero and not self.hero.is_defeated:
            self.all_participants.append(self.hero)
        for opp in self.opponents:
            if opp and not opp.is_defeated:
                self.all_participants.append(opp)

    def get_hero(self) -> Optional[CharacterInstance]: return self.hero
    def get_live_opponents(self) -> List[CharacterInstance]: return [opp for opp in self.opponents if opp and not opp.is_defeated]
    def get_all_live_participants(self) -> List[CharacterInstance]:
        self._update_all_participants_list() 
        return self.all_participants

    def execute_hero_action(self, skill_id: str, primary_target: Optional[CharacterInstance], was_beneficial_context: bool) -> Tuple[bool, str]:
        self.last_action_successful = False
        if not self.hero:
            return False, "No hero available to perform action."

        self._update_all_participants_list()
        
        _ = self.combat_handler.process_actor_action_phase(
            actor=self.hero,
            skill_id_to_execute=skill_id,
            primary_target_for_skill=primary_target,
            all_participants_in_combat=self.all_participants,
            was_beneficial_context=was_beneficial_context
        )
        self.last_action_successful = True
        return self.last_action_successful, f"Hero action '{skill_id}' processed."

    def execute_item_action(self, item: 'ItemTemplate', primary_target: Optional[CharacterInstance], was_beneficial_context: bool) -> Tuple[bool, str]:
        self.last_action_successful = False
        if not self.hero: return False, "No hero available."
        if not primary_target: return False, "No target for item action."
            
        success = self.item_executor.execute_item(
            actor=self.hero, item=item, target=primary_target, was_beneficial_context=was_beneficial_context
        )
        self.last_action_successful = success
        return success, f"Hero item action '{item.name}' processed. Success: {success}"

    def run_opponent_turns(self) -> None:
        if not self.hero: return
        self._update_all_participants_list()
        opponents_able_to_act = [opp for opp in self.opponents if opp and not opp.is_defeated]
        for opponent_actor in opponents_able_to_act:
            if self.hero.is_defeated: break
            if not opponent_actor or opponent_actor.is_defeated: continue
            potential_ai_targets = [p for p in self.all_participants if p and not p.is_defeated and opponent_actor.is_opponent_of(p)]
            chosen_skill_id_npc: Optional[str] = None
            primary_target_instance_npc: Optional[CharacterInstance] = None
            ai_strategy = get_ai_strategy_instance(opponent_actor, self.all_participants)
            if ai_strategy and potential_ai_targets:
                decision = ai_strategy.decide_action(potential_ai_targets)
                if decision: chosen_skill_id_npc, primary_target_instance_npc = decision
            if not chosen_skill_id_npc:
                chosen_skill_id_npc = COMBAT_CONSTANTS.SKILL_PASS_TURN
                primary_target_instance_npc = opponent_actor
            self.combat_handler.process_actor_action_phase(
                actor=opponent_actor, skill_id_to_execute=chosen_skill_id_npc,
                primary_target_for_skill=primary_target_instance_npc,
                all_participants_in_combat=self.all_participants, was_beneficial_context=False
            )
            if self.hero.is_defeated: break

    def check_combat_end_conditions(self) -> Tuple[bool, bool, str]:
        hero_won = False; terminated = False; message = ""
        if self.hero and self.hero.is_defeated:
            terminated = True; hero_won = False; message = "Hero was defeated."
            return terminated, hero_won, message
        live_opps = self.get_live_opponents()
        if not live_opps and self.hero and not self.hero.is_defeated:
            terminated = True; hero_won = True; message = "All opponents defeated."
            return terminated, hero_won, message
        return terminated, hero_won, message

    def increment_step(self):
        self.current_episode_step += 1