# src/ai/strategies/basic_ranged.py
import random
import logging
from typing import Optional, List, Dict, Any, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillTemplate
from src.definitions.character import CharacterTemplate 
from src.definitions.opponent import OpponentTemplate # Import für Typ-Check

logger = logging.getLogger(__name__)

class BasicRangedStrategy:
    def __init__(self, actor: 'CharacterInstance', skill_definitions: Dict[str, 'SkillTemplate'], character_definitions: Dict[str, 'CharacterTemplate']):
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
        if skill and skill.applied_status_effects:
            # Hier könnte man noch prüfen, ob die Effekte negativ sind,
            # aber für eine einfache KI reicht oft die Annahme, dass angewandte Effekte Debuffs sind.
            return True 
        return False

    def _get_skill_potential_damage(self, skill_id: str) -> int:
        skill = self.skill_definitions.get(skill_id)
        try: from src.config.config import CONFIG
        except ImportError: CONFIG = None

        base_damage_val = 0
        is_offensive = False
        if skill and skill.direct_effects:
            if skill.direct_effects.base_damage is not None:
                base_damage_val = skill.direct_effects.base_damage
                is_offensive = True
            elif skill.direct_effects.base_damage is None: # Waffenschaden
                if CONFIG and hasattr(CONFIG, 'get'):
                    base_damage_val = CONFIG.get("game_settings.base_weapon_damage", 5)
                else:
                    base_damage_val = 5 
                is_offensive = True
        
        if not is_offensive or not skill or not skill.direct_effects : return 0
        
        multiplier = skill.direct_effects.multiplier
        attr_bonus = 0
        if skill.direct_effects.scaling_attribute:
            attr_bonus = self.actor.get_attribute_bonus(skill.direct_effects.scaling_attribute)
        return int((base_damage_val + attr_bonus) * multiplier)

    def choose_target(self, potential_targets: List['CharacterInstance']) -> Optional['CharacterInstance']:
        if not potential_targets: return None
        valid_targets = [t for t in potential_targets if not t.is_defeated]
        if not valid_targets: return None

        caster_targets = [t for t in valid_targets if self._is_target_caster_type(t)]
        chosen_target: Optional[CharacterInstance] = None

        if caster_targets and random.random() < 0.70:
            chosen_target = random.choice(caster_targets)
            logger.debug(f"'{self.actor.name}' (BasicRanged) wählt Caster-Ziel: '{chosen_target.name}'.")
        else:
            if random.random() < 0.60:
                valid_targets.sort(key=lambda t: (t.current_hp / t.max_hp) if t.max_hp > 0 else float('inf'))
                chosen_target = valid_targets[0]
                logger.debug(f"'{self.actor.name}' (BasicRanged) wählt schwächstes Ziel: '{chosen_target.name}'.")
            else:
                chosen_target = random.choice(valid_targets)
                logger.debug(f"'{self.actor.name}' (BasicRanged) wählt zufälliges Ziel: '{chosen_target.name}'.")
        return chosen_target

    def choose_skill(self, available_skills: List[str], target: Optional['CharacterInstance']) -> Optional[str]:
        if not available_skills: return None
        usable_skills = [s_id for s_id in available_skills if self.actor.can_afford_skill(self.skill_definitions.get(s_id))]
        if not usable_skills: return None

        skills_with_debuffs = [s_id for s_id in usable_skills if self._skill_applies_debuff(s_id)]
        chosen_skill_id: Optional[str] = None

        if skills_with_debuffs and random.random() < 0.60:
            chosen_skill_id = random.choice(skills_with_debuffs)
            logger.debug(f"'{self.actor.name}' (BasicRanged) wählt Skill mit Debuff: '{chosen_skill_id}'.")
        else:
            offensive_skills = []
            for s_id in usable_skills:
                skill = self.skill_definitions.get(s_id)
                if skill and skill.direct_effects and \
                   (skill.direct_effects.base_damage is not None or \
                    (skill.direct_effects.base_damage is None and True)): # True, wenn Waffenschaden als offensiv gilt
                    offensive_skills.append(s_id)
            
            if offensive_skills:
                offensive_skills.sort(key=lambda s_id: self._get_skill_potential_damage(s_id), reverse=True)
                chosen_skill_id = offensive_skills[0]
                logger.debug(f"'{self.actor.name}' (BasicRanged) wählt stärksten offensiven Skill: '{chosen_skill_id}'.")
            elif usable_skills: 
                chosen_skill_id = random.choice(usable_skills)
                logger.debug(f"'{self.actor.name}' (BasicRanged) wählt zufälligen verfügbaren Skill: '{chosen_skill_id}'.")
        return chosen_skill_id

    def decide_action(self, potential_targets: List['CharacterInstance']) -> Optional[Tuple[str, 'CharacterInstance']]:
        if not self.actor or self.actor.is_defeated or not self.actor.can_act: return None
        target = self.choose_target(potential_targets)
        if not target:
            logger.debug(f"'{self.actor.name}' (BasicRanged) findet kein Ziel.")
            return None
        skill_id = self.choose_skill(self.actor.skills, target)
        if not skill_id:
            logger.debug(f"'{self.actor.name}' (BasicRanged) konnte keinen Skill auswählen.")
            return None
        logger.debug(f"'{self.actor.name}' (BasicRanged) entscheidet sich für Skill '{skill_id}' auf Ziel '{target.name}'.") # KORREKTUR: DEBUG statt INFO
        return skill_id, target

# ... (if __name__ == '__main__' Block bleibt gleich)
if __name__ == '__main__':
    from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
    from src.game_logic.entities import OpponentTemplate 
    from src.config.config import CONFIG
    print("\n--- Teste BasicRangedStrategy ---")
    try:
        char_defs = load_character_templates()
        opp_defs = load_opponent_templates()
        skill_defs = load_skill_templates()
        ai_actor_template = opp_defs["goblin_archer_lv2"] 
        ai_actor = CharacterInstance(base_template=ai_actor_template, name_override="AI Archer")
        ai_actor.skills = ["basic_shot_phys"] 
        ai_shaman_template = opp_defs["goblin_shaman_lv3"]
        ai_shaman_actor = CharacterInstance(base_template=ai_shaman_template, name_override="AI Shaman Ranged Test")
        player_krieger = CharacterInstance(base_template=char_defs["krieger"], name_override="Krieger (Non-Caster)")
        player_magier = CharacterInstance(base_template=char_defs["magier"], name_override="Magier (Caster)")
        player_magier.current_hp = int(player_magier.max_hp * 0.5) 
        targets = [player_krieger, player_magier]
        strategy_archer = BasicRangedStrategy(actor=ai_actor, skill_definitions=skill_defs, character_definitions=char_defs)
        strategy_shaman = BasicRangedStrategy(actor=ai_shaman_actor, skill_definitions=skill_defs, character_definitions=char_defs)
        print(f"\nAI Akteur (Archer): {ai_actor.name} mit Skills: {ai_actor.skills}")
        print(f"AI Akteur (Shaman): {ai_shaman_actor.name} mit Skills: {ai_shaman_actor.skills}")
        print("Potenzielle Ziele:")
        for t in targets: print(f" - {t.name}: {t.current_hp}/{t.max_hp} HP, Caster: {strategy_archer._is_target_caster_type(t)}")
        print("\n-- Teste Zielauswahl für Archer (mehrere Versuche) --")
        target_counts_archer = {t.name: 0 for t in targets}
        for _ in range(20): 
            chosen_t = strategy_archer.choose_target(targets)
            if chosen_t: target_counts_archer[chosen_t.name] += 1
        print(f"Archer Zielauswahl-Verteilung (20 Versuche): {target_counts_archer}")
        print("\n-- Teste Skillauswahl für Archer --")
        ai_actor.current_stamina = ai_actor.max_stamina 
        chosen_s_archer = strategy_archer.choose_skill(ai_actor.skills, player_magier)
        print(f"Archer gewählter Skill: {chosen_s_archer}")
        print("\n-- Teste Skillauswahl für Shaman (mehrere Versuche) --")
        skill_counts_shaman = {s_id: 0 for s_id in ai_shaman_actor.skills}
        skill_counts_shaman["None"] = 0
        ai_shaman_actor.current_mana = ai_shaman_actor.max_mana 
        for _ in range(10):
            chosen_s_shaman = strategy_shaman.choose_skill(ai_shaman_actor.skills, player_magier)
            if chosen_s_shaman: skill_counts_shaman[chosen_s_shaman] += 1
            else: skill_counts_shaman["None"] +=1
        print(f"Shaman Skillauswahl-Verteilung (10 Versuche): {skill_counts_shaman}")
        print("\n-- Teste Aktionsentscheidung für Archer --")
        action_archer = strategy_archer.decide_action(targets)
        if action_archer:
            skill_chosen, target_chosen = action_archer
            print(f"Archer entschiedene Aktion: Skill '{skill_chosen}' auf Ziel '{target_chosen.name}'.")
        else: print("Archer: Keine Aktion entschieden.")
        print("\n-- Teste Aktionsentscheidung für Shaman --")
        action_shaman = strategy_shaman.decide_action(targets)
        if action_shaman:
            skill_chosen, target_chosen = action_shaman
            print(f"Shaman entschiedene Aktion: Skill '{skill_chosen}' auf Ziel '{target_chosen.name}'.")
        else: print("Shaman: Keine Aktion entschieden.")
    except ImportError as e: print(f"FEHLER bei Imports für den Test in basic_ranged.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in basic_ranged.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    print("\n--- BasicRangedStrategy-Tests abgeschlossen ---")