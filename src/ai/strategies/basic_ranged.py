# src/ai/strategies/basic_ranged.py
import random
import logging
from typing import Optional, List, Dict, Any, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillTemplate
from src.definitions.character import CharacterTemplate 
from src.definitions.opponent import OpponentTemplate
from src.game_logic.combat import constants as COMBAT_CONSTANTS

logger = logging.getLogger(__name__)

class BasicRangedStrategy:
    def __init__(self, actor: 'CharacterInstance', skill_definitions: Dict[str, 'SkillTemplate'], 
                 character_definitions: Dict[str, 'CharacterTemplate']):
        self.actor = actor
        self.skill_definitions = skill_definitions
        self.character_definitions = character_definitions 

    def _is_target_caster_type(self, target: 'CharacterInstance') -> bool:
        if isinstance(target.base_template, CharacterTemplate):
            if target.base_template.resource_type == "MANA": return True
        elif isinstance(target.base_template, OpponentTemplate): 
            if "CASTER" in target.base_template.tags: return True
        return False

    def _skill_applies_debuff(self, skill_id: str) -> bool:
        skill = self.skill_definitions.get(skill_id)
        return bool(skill and skill.applied_status_effects)

    def _get_skill_potential_damage(self, skill_id: str) -> int:
        skill = self.skill_definitions.get(skill_id)
        if not skill or not skill.direct_effects: return 0
        try: from src.config.config import CONFIG
        except ImportError: CONFIG = None
        base_damage_val = skill.direct_effects.base_damage or (CONFIG.get("game_settings.base_weapon_damage", 5) if CONFIG else 5)
        attr_bonus = self.actor.get_attribute_bonus(skill.direct_effects.scaling_attribute) if skill.direct_effects.scaling_attribute else 0
        return int((base_damage_val + attr_bonus) * skill.direct_effects.multiplier)

    def choose_target(self, potential_targets: List['CharacterInstance']) -> Optional['CharacterInstance']:
        if not potential_targets: return None
        
        caster_targets = [t for t in potential_targets if self._is_target_caster_type(t)]
        
        if caster_targets and random.random() < 0.70:
            return random.choice(caster_targets)
        else:
            potential_targets.sort(key=lambda t: (t.current_hp / t.max_hp) if t.max_hp > 0 else float('inf'))
            return potential_targets[0]

    def choose_skill(self, available_skills: List[str], target: Optional['CharacterInstance']) -> Optional[str]:
        if not available_skills or not target: return None
        
        usable_skills = [s_id for s_id in available_skills if self.actor.can_afford_skill(self.skill_definitions.get(s_id))]
        if not usable_skills: return None

        skills_with_debuffs = [s_id for s_id in usable_skills if self._skill_applies_debuff(s_id)]
        if skills_with_debuffs and random.random() < 0.60:
            return random.choice(skills_with_debuffs)

        offensive_skills = [s_id for s_id in usable_skills if self._get_skill_potential_damage(s_id) > 0]
        if offensive_skills:
            offensive_skills.sort(key=self._get_skill_potential_damage, reverse=True)
            return offensive_skills[0]
        
        return random.choice(usable_skills) if usable_skills else None

    def decide_action(self, potential_targets: List['CharacterInstance']) -> Optional[Tuple[str, 'CharacterInstance']]:
        if not self.actor or self.actor.is_defeated or not self.actor.can_act:
            return None

        actor_pos = getattr(self.actor, 'position', None)
        
        # KORREKTUR: Logik für räumliche und nicht-räumliche Kämpfe
        targets_in_range = []
        if actor_pos:
            # Welt-Simulation: Prüfe auf Distanz > 1
            for target in potential_targets:
                target_pos = getattr(target, 'position', None)
                if not target_pos: continue
                distance = abs(actor_pos['x'] - target_pos['x']) + abs(actor_pos['y'] - target_pos['y'])
                if distance > 1:
                    targets_in_range.append(target)
        else:
            # RL-Kampf (ohne Position): Alle Ziele sind in Reichweite
            targets_in_range = potential_targets

        if not targets_in_range:
            logger.debug(f"'{self.actor.name}' (BasicRanged) hat kein Ziel in Reichweite und passt.")
            return (COMBAT_CONSTANTS.SKILL_PASS_TURN, self.actor)

        chosen_target = self.choose_target(targets_in_range)
        if not chosen_target:
            return (COMBAT_CONSTANTS.SKILL_PASS_TURN, self.actor)
            
        chosen_skill_id = self.choose_skill(self.actor.skills, chosen_target)
        
        if not chosen_skill_id:
            logger.debug(f"'{self.actor.name}' (BasicRanged) hat ein Ziel, aber keinen nutzbaren Skill und passt.")
            return (COMBAT_CONSTANTS.SKILL_PASS_TURN, self.actor)

        logger.debug(f"'{self.actor.name}' (BasicRanged) entscheidet sich für Skill '{chosen_skill_id}' auf Ziel '{chosen_target.name}'.")
        return chosen_skill_id, chosen_target