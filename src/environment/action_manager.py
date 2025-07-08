# src/environment/action_manager.py
# V14: Fügt das Logging für Agenten-Aktionen wieder hinzu.
import logging
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from gymnasium import spaces

if TYPE_CHECKING:
    from src.game_logic.interfaces import StateManagerInterface
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate
    from src.definitions.item import ItemTemplate

from src.config.config import CONFIG

# Standard-Logger für allgemeine Modul-Nachrichten
logger = logging.getLogger(__name__)
# Spezieller Logger, der in die agent_actions...txt schreibt
agent_action_logger = logging.getLogger("agent_action_log")


MAX_SKILLS_ACTION = 6
MAX_OPPONENTS_ACTION = 3
MAX_INVENTORY_SLOTS_ACTION = 4

PASS_ACTION_ID_NUMERIC = 0
PASS_ACTION_SKILL_ID_STR = "skill_pass_turn"
EXECUTE_SKILL_TAG = "EXECUTE"

class ActionManager:
    def __init__(self,
                 skill_templates: Dict[str, 'SkillTemplate'],
                 hero_initial_skill_ids: List[str]):
        self.skill_templates = skill_templates
        if len(hero_initial_skill_ids) > MAX_SKILLS_ACTION:
             logger.warning(f"ActionManager: Held hat mehr Skills ({len(hero_initial_skill_ids)}) als MAX_SKILLS_ACTION ({MAX_SKILLS_ACTION}).")
        
        self.hero_action_skill_ids = hero_initial_skill_ids[:MAX_SKILLS_ACTION]
        self.num_skills_in_space = len(self.hero_action_skill_ids)
        self.num_target_options_in_space = 1 + MAX_OPPONENTS_ACTION
        self.num_item_slots_in_space = MAX_INVENTORY_SLOTS_ACTION

        num_skill_target_combinations = self.num_skills_in_space * self.num_target_options_in_space
        self.action_space_size = 1 + num_skill_target_combinations + self.num_item_slots_in_space
        
        self.action_space = spaces.Discrete(self.action_space_size)
        logger.info(f"ActionManager initialisiert. Action Space Size: {self.action_space_size}")

    def get_action_space(self) -> spaces.Discrete:
        return self.action_space

    def get_action_mask(self, gsm: 'StateManagerInterface') -> List[bool]:
        mask = [False] * self.action_space_size
        hero = gsm.get_hero()
        if not hero or hero.is_defeated: return mask
        
        mask[PASS_ACTION_ID_NUMERIC] = True
        if not hero.can_act: return mask

        live_opponents = gsm.get_live_opponents()
        current_action_id = 1
        for skill_idx in range(self.num_skills_in_space):
            skill_id_local = self.hero_action_skill_ids[skill_idx]
            skill_template_local = self.skill_templates.get(skill_id_local)
            if not skill_template_local or not hero.can_afford_skill(skill_template_local):
                current_action_id += self.num_target_options_in_space
                continue

            is_execute_skill = EXECUTE_SKILL_TAG in skill_template_local.tags
            execute_hp_threshold = CONFIG.get("game_settings.execute_skill_hp_threshold_percent", 0.25)
            
            for target_option_idx in range(self.num_target_options_in_space):
                if current_action_id >= self.action_space_size: break
                
                is_valid_target = False
                passes_execute_condition = not is_execute_skill

                if target_option_idx == 0:
                    if skill_template_local.target_type == "SELF" or skill_template_local.target_type.startswith("ALLY_"):
                        is_valid_target = True
                else:
                    opponent_slot_idx = target_option_idx - 1
                    if opponent_slot_idx < len(live_opponents):
                        actual_target_entity = live_opponents[opponent_slot_idx]
                        if skill_template_local.target_type.startswith("ENEMY_"):
                            is_valid_target = True
                            if is_execute_skill:
                                if actual_target_entity.max_hp > 0 and (actual_target_entity.current_hp / actual_target_entity.max_hp) <= execute_hp_threshold:
                                    passes_execute_condition = True
                                else:
                                    passes_execute_condition = False
                
                if is_valid_target and passes_execute_condition:
                    mask[current_action_id] = True
                
                current_action_id += 1
        
        inventory_items = list(hero.inventory.items.values()) if hero.inventory else []
        for item_slot_idx in range(self.num_item_slots_in_space):
            if current_action_id >= self.action_space_size: break
            if item_slot_idx < len(inventory_items):
                item_template, quantity = inventory_items[item_slot_idx]
                if item_template.usable_in_combat and quantity > 0:
                    mask[current_action_id] = True
            current_action_id += 1

        return mask

    def get_game_action(self, action_id: int, gsm: 'StateManagerInterface') -> Optional[Tuple[str, Any, Optional['CharacterInstance']]]:
        hero = gsm.get_hero()
        if not hero: return None
        if not (0 <= action_id < self.action_space_size): return None
        
        # KORREKTUR: Logging hier wieder eingefügt
        log_message = f"RL-Agent wählte Aktion ID: {action_id}."
        decoded_action_str = "FEHLER BEI DEKODIERUNG"

        if action_id == PASS_ACTION_ID_NUMERIC:
            decoded_action_str = "PASS"
            agent_action_logger.info(f"{log_message} Dekodiert als: {decoded_action_str}.")
            return ("PASS", PASS_ACTION_SKILL_ID_STR, hero)

        skill_action_space_end = 1 + (self.num_skills_in_space * self.num_target_options_in_space)

        if 1 <= action_id < skill_action_space_end:
            adjusted_action_id = action_id - 1
            skill_idx = adjusted_action_id // self.num_target_options_in_space
            target_option_idx = adjusted_action_id % self.num_target_options_in_space

            if not (0 <= skill_idx < len(self.hero_action_skill_ids)):
                agent_action_logger.error(f"{log_message} FEHLER: Ungültiger Skill-Index {skill_idx}.")
                return None
            
            skill_id_to_use = self.hero_action_skill_ids[skill_idx]
            target_instance: Optional['CharacterInstance'] = None

            if target_option_idx == 0:
                target_instance = hero
            else:
                opponent_slot_idx = target_option_idx - 1
                live_opponents = gsm.get_live_opponents()
                if opponent_slot_idx < len(live_opponents):
                    target_instance = live_opponents[opponent_slot_idx]
                else:
                    logger.error(f"AM.get_game_action: Ziel-Gegner-Slot {opponent_slot_idx} nicht gültig/lebendig. Live-Gegner: {len(live_opponents)}. Gibt None zurück.")
                    agent_action_logger.error(f"{log_message} FEHLER: Ungültiger Gegner-Slot-Index {opponent_slot_idx}.")
                    return None
            
            if not target_instance:
                agent_action_logger.error(f"{log_message} FEHLER: Konnte kein Ziel für Skill '{skill_id_to_use}' finden.")
                return None
            
            decoded_action_str = f"SKILL: '{skill_id_to_use}' auf ZIEL: '{target_instance.name}'"
            agent_action_logger.info(f"{log_message} Dekodiert als: {decoded_action_str}.")
            return ("SKILL", skill_id_to_use, target_instance)
        else:
            item_slot_idx = action_id - skill_action_space_end
            inventory_items = list(hero.inventory.items.values()) if hero.inventory else []
            if 0 <= item_slot_idx < len(inventory_items):
                item_template, _ = inventory_items[item_slot_idx]
                target_instance = hero
                decoded_action_str = f"ITEM: '{item_template.name}' auf ZIEL: '{target_instance.name}'"
                agent_action_logger.info(f"{log_message} Dekodiert als: {decoded_action_str}.")
                return ("ITEM", item_template, target_instance)

        logger.error(f"AM.get_game_action: Konnte Aktion {action_id} nicht dekodieren. Fallback auf None.")
        agent_action_logger.error(f"{log_message} FEHLER: Aktion konnte keinem Typ (PASS, SKILL, ITEM) zugeordnet werden.")
        return None