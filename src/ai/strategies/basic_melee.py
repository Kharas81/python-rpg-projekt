# src/ai/strategies/basic_melee.py
import random
import logging
from typing import Optional, List, Dict, Any, Tuple 

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillTemplate
from src.game_logic.combat import constants as COMBAT_CONSTANTS

logger = logging.getLogger(__name__)

class BasicMeleeStrategy:
    def __init__(self, actor: 'CharacterInstance', skill_definitions: Dict[str, 'SkillTemplate']):
        self.actor = actor
        self.skill_definitions = skill_definitions

    def _is_skill_offensive(self, skill_id: str) -> bool:
        skill = self.skill_definitions.get(skill_id)
        if not skill or not skill.direct_effects:
            return False
        # Prüft, ob der Skill entweder direkten Schaden hat oder auf Waffenschaden skaliert
        if skill.direct_effects.base_damage is not None and skill.direct_effects.base_damage > 0:
            return True
        if skill.direct_effects.base_damage is None: # Skaliert mit Waffe
            return True
        return False

    def _get_skill_potential_damage(self, skill_id: str) -> int:
        skill = self.skill_definitions.get(skill_id)
        if not skill or not self._is_skill_offensive(skill_id) or not skill.direct_effects:
            return 0
        from src.config.config import CONFIG
        base_damage_val = skill.direct_effects.base_damage or CONFIG.get("game_settings.base_weapon_damage", 5)
        
        attr_bonus = self.actor.get_attribute_bonus(skill.direct_effects.scaling_attribute) if skill.direct_effects.scaling_attribute else 0
        
        return int((base_damage_val + attr_bonus) * skill.direct_effects.multiplier)

    def choose_skill(self, available_skills: List[str], target: Optional[CharacterInstance]) -> Optional[str]:
        if not available_skills or not target: return None
        
        offensive_skills = [
            s_id for s_id in available_skills 
            if self._is_skill_offensive(s_id) and self.actor.can_afford_skill(self.skill_definitions[s_id])
        ]

        if not offensive_skills:
            return None

        offensive_skills.sort(key=lambda s_id: self._get_skill_potential_damage(s_id), reverse=True)
        return offensive_skills[0]


    def decide_action(self, potential_targets: List['CharacterInstance']) -> Optional[Tuple[str, 'CharacterInstance']]:
        if not self.actor or self.actor.is_defeated or not self.actor.can_act:
            return None

        actor_pos = getattr(self.actor, 'position', None)
        
        # KORREKTUR: Logik für räumliche und nicht-räumliche Kämpfe
        targets_in_range = []
        if actor_pos:
            # Welt-Simulation: Prüfe Adjazenz
            for target in potential_targets:
                target_pos = getattr(target, 'position', None)
                if not target_pos: continue
                distance = abs(actor_pos['x'] - target_pos['x']) + abs(actor_pos['y'] - target_pos['y'])
                if distance == 1:
                    targets_in_range.append(target)
        else:
            # RL-Kampf (ohne Position): Alle Ziele sind in Reichweite
            targets_in_range = potential_targets

        if not targets_in_range:
            logger.debug(f"'{self.actor.name}' (BasicMelee) hat kein Ziel in Reichweite und passt.")
            return (COMBAT_CONSTANTS.SKILL_PASS_TURN, self.actor)

        # Wähle das Ziel mit den prozentual niedrigsten HP
        targets_in_range.sort(key=lambda t: (t.current_hp / t.max_hp) if t.max_hp > 0 else float('inf'))
        chosen_target = targets_in_range[0]
        
        # Wähle den besten Skill für dieses Ziel
        chosen_skill_id = self.choose_skill(self.actor.skills, chosen_target)
        
        if not chosen_skill_id:
            logger.debug(f"'{self.actor.name}' (BasicMelee) hat ein Ziel, aber keinen nutzbaren Skill und passt.")
            return (COMBAT_CONSTANTS.SKILL_PASS_TURN, self.actor)

        logger.debug(f"'{self.actor.name}' (BasicMelee) entscheidet sich für Skill '{chosen_skill_id}' auf Ziel '{chosen_target.name}'.")
        return chosen_skill_id, chosen_target