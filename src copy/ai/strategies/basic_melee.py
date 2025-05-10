# src/ai/strategies/basic_melee.py
import random
import logging
from typing import Optional, List, Dict, Any, Tuple 

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillTemplate

logger = logging.getLogger(__name__)

class BasicMeleeStrategy:
    def __init__(self, actor: 'CharacterInstance', skill_definitions: Dict[str, 'SkillTemplate']):
        self.actor = actor
        self.skill_definitions = skill_definitions

    def _is_skill_offensive(self, skill_id: str) -> bool:
        skill = self.skill_definitions.get(skill_id)
        if skill and skill.direct_effects and skill.direct_effects.base_damage is not None:
            return True
        # Berücksichtige Skills, die Waffenschaden nutzen (base_damage: null)
        if skill and skill.direct_effects and skill.direct_effects.base_damage is None:
             try:
                 from src.config.config import CONFIG
                 if CONFIG and CONFIG.get("game_settings.base_weapon_damage") is not None:
                     return True
             except ImportError:
                 pass # CONFIG nicht verfügbar, kann nicht geprüft werden
        return False

    def _get_skill_potential_damage(self, skill_id: str) -> int:
        skill = self.skill_definitions.get(skill_id)
        if not skill or not self._is_skill_offensive(skill_id) or not skill.direct_effects:
            return 0

        base_damage_val = 0
        try:
            from src.config.config import CONFIG
        except ImportError:
            CONFIG = None
            
        if skill.direct_effects.base_damage is None:
            if CONFIG and hasattr(CONFIG, 'get'):
                base_damage_val = CONFIG.get("game_settings.base_weapon_damage", 5)
            else:
                base_damage_val = 5 
        else:
            base_damage_val = skill.direct_effects.base_damage

        multiplier = skill.direct_effects.multiplier
        attr_bonus = 0
        if skill.direct_effects.scaling_attribute:
            attr_bonus = self.actor.get_attribute_bonus(skill.direct_effects.scaling_attribute)
        return int((base_damage_val + attr_bonus) * multiplier)

    def choose_target(self, potential_targets: List['CharacterInstance']) -> Optional['CharacterInstance']:
        if not potential_targets: return None
        valid_targets = [t for t in potential_targets if not t.is_defeated]
        if not valid_targets: return None

        if random.random() < 0.80:
            valid_targets.sort(key=lambda t: (t.current_hp / t.max_hp) if t.max_hp > 0 else float('inf'))
            chosen_target = valid_targets[0]
            logger.debug(f"'{self.actor.name}' (BasicMelee) wählt schwächstes Ziel: '{chosen_target.name}'")
            return chosen_target
        else:
            chosen_target = random.choice(valid_targets)
            logger.debug(f"'{self.actor.name}' (BasicMelee) wählt zufälliges Ziel: '{chosen_target.name}'.")
            return chosen_target

    def choose_skill(self, available_skills: List[str], target: Optional['CharacterInstance']) -> Optional[str]:
        if not available_skills: return None
        
        offensive_skills = []
        for skill_id in available_skills:
            skill_template = self.skill_definitions.get(skill_id)
            if skill_template and self._is_skill_offensive(skill_id) and self.actor.can_afford_skill(skill_template):
                offensive_skills.append(skill_id)

        if not offensive_skills:
            non_offensive_usable_skills = []
            for skill_id in available_skills:
                skill_template = self.skill_definitions.get(skill_id)
                if skill_template and not self._is_skill_offensive(skill_id) and self.actor.can_afford_skill(skill_template):
                    non_offensive_usable_skills.append(skill_id)
            if non_offensive_usable_skills:
                chosen_skill_id = random.choice(non_offensive_usable_skills)
                logger.debug(f"'{self.actor.name}' (BasicMelee) wählt nicht-offensiven Skill: '{chosen_skill_id}'.")
                return chosen_skill_id
            return None

        if random.random() < 0.70:
            offensive_skills.sort(key=lambda s_id: self._get_skill_potential_damage(s_id), reverse=True)
            chosen_skill_id = offensive_skills[0]
            logger.debug(f"'{self.actor.name}' (BasicMelee) wählt stärksten Skill: '{chosen_skill_id}'.")
        else:
            chosen_skill_id = random.choice(offensive_skills)
            logger.debug(f"'{self.actor.name}' (BasicMelee) wählt zufälligen offensiven Skill: '{chosen_skill_id}'.")
        return chosen_skill_id

    def decide_action(self, potential_targets: List['CharacterInstance']) -> Optional[Tuple[str, 'CharacterInstance']]:
        if not self.actor or self.actor.is_defeated or not self.actor.can_act: return None
        target = self.choose_target(potential_targets)
        if not target:
            logger.debug(f"'{self.actor.name}' (BasicMelee) findet kein Ziel.")
            return None
        skill_id = self.choose_skill(self.actor.skills, target)
        if not skill_id:
            logger.debug(f"'{self.actor.name}' (BasicMelee) konnte keinen Skill auswählen.")
            return None
        logger.debug(f"'{self.actor.name}' (BasicMelee) entscheidet sich für Skill '{skill_id}' auf Ziel '{target.name}'.") # KORREKTUR: DEBUG statt INFO
        return skill_id, target

# ... (if __name__ == '__main__' Block bleibt gleich)
if __name__ == '__main__':
    from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
    from src.config.config import CONFIG 
    print("\n--- Teste BasicMeleeStrategy ---")
    try:
        char_templates = load_character_templates()
        opp_templates = load_opponent_templates()
        skill_defs = load_skill_templates() 
        krieger_template = char_templates["krieger"] 
        goblin_template = opp_templates["goblin_lv1"] 
        ai_actor = CharacterInstance(base_template=goblin_template, name_override="AI Goblin")
        ai_actor.skills = ["basic_strike_phys", "power_strike"] 
        player1 = CharacterInstance(base_template=krieger_template, name_override="Player 1 (Full HP)")
        player2 = CharacterInstance(base_template=krieger_template, name_override="Player 2 (Low HP)")
        player2.current_hp = int(player2.max_hp * 0.3) 
        targets = [player1, player2]
        strategy = BasicMeleeStrategy(actor=ai_actor, skill_definitions=skill_defs)
        print(f"\nAI Akteur: {ai_actor.name} mit Skills: {ai_actor.skills}")
        print("Potenzielle Ziele:")
        for t in targets: print(f" - {t.name}: {t.current_hp}/{t.max_hp} HP")
        print("\n-- Teste Zielauswahl (mehrere Versuche) --")
        target_counts = {player1.name: 0, player2.name: 0}
        for _ in range(10):
            chosen_t = strategy.choose_target(targets)
            if chosen_t: target_counts[chosen_t.name] += 1
        print(f"Zielauswahl-Verteilung über 10 Versuche: {target_counts}")
        print("\n-- Teste Skillauswahl (mehrere Versuche) --")
        skill_counts = {"power_strike": 0, "basic_strike_phys": 0, "None":0}
        ai_actor.current_stamina = ai_actor.max_stamina 
        for _ in range(10):
            chosen_s = strategy.choose_skill(ai_actor.skills, player2) 
            if chosen_s: skill_counts[chosen_s] = skill_counts.get(chosen_s, 0) + 1
            else: skill_counts["None"] +=1
        print(f"Skillauswahl-Verteilung über 10 Versuche: {skill_counts}")
        print("\n-- Teste Aktionsentscheidung --")
        action = strategy.decide_action(targets)
        if action:
            skill_chosen, target_chosen = action
            print(f"Entschiedene Aktion: Skill '{skill_chosen}' auf Ziel '{target_chosen.name}'.")
        else: print("Keine Aktion entschieden.")
        print("\n-- Test: Akteur hat nicht genug Ressourcen für stärksten Skill --")
        power_strike_cost = 0
        if "power_strike" in skill_defs: power_strike_cost = skill_defs["power_strike"].cost.value
        ai_actor.current_stamina = power_strike_cost -1 if power_strike_cost > 0 else 0
        action_low_res = strategy.decide_action(targets)
        if action_low_res:
            skill_chosen_lr, target_chosen_lr = action_low_res
            print(f"Entschiedene Aktion bei niedrigen Ressourcen ({ai_actor.current_stamina} Stamina): Skill '{skill_chosen_lr}' auf Ziel '{target_chosen_lr.name}'.")
            # assert skill_chosen_lr == "basic_strike_phys" # basic_strike_phys kostet 0
        else: print(f"Keine Aktion entschieden bei niedrigen Ressourcen ({ai_actor.current_stamina} Stamina).")
    except ImportError as e: print(f"FEHLER bei Imports für den Test in basic_melee.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in basic_melee.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    print("\n--- BasicMeleeStrategy-Tests abgeschlossen ---")