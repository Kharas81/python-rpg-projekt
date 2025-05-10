# src/ai/strategies/support_caster.py
import random
import logging
from typing import Optional, List, Dict, Any, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillTemplate
from src.definitions.character import CharacterTemplate 
from src.definitions.opponent import OpponentTemplate # Import für Typ-Check

logger = logging.getLogger(__name__)

class SupportCasterStrategy:
    def __init__(self, actor: 'CharacterInstance', 
                 all_entities_in_combat: List['CharacterInstance'], 
                 skill_definitions: Dict[str, 'SkillTemplate'], 
                 character_definitions: Dict[str, 'CharacterTemplate']):
        self.actor = actor
        self.all_entities_in_combat = all_entities_in_combat 
        self.skill_definitions = skill_definitions
        # self.character_definitions = character_definitions # Aktuell nicht direkt genutzt

    def _get_allies(self) -> List['CharacterInstance']:
        actor_is_opponent_type = isinstance(self.actor.base_template, OpponentTemplate)
        allies = []
        for entity in self.all_entities_in_combat:
            if entity.is_defeated: continue
            entity_is_opponent_type = isinstance(entity.base_template, OpponentTemplate)
            if actor_is_opponent_type == entity_is_opponent_type:
                allies.append(entity)
        return allies

    def _get_opponents(self) -> List['CharacterInstance']:
        actor_is_opponent_type = isinstance(self.actor.base_template, OpponentTemplate)
        opponents = []
        for entity in self.all_entities_in_combat:
            if entity.is_defeated: continue
            entity_is_opponent_type = isinstance(entity.base_template, OpponentTemplate)
            if actor_is_opponent_type != entity_is_opponent_type:
                opponents.append(entity)
        return opponents

    def _is_skill_type(self, skill_id: str, skill_type: str) -> bool:
        skill = self.skill_definitions.get(skill_id)
        if not skill: return False
        if skill_type == "HEAL":
            return skill.direct_effects is not None and skill.direct_effects.base_healing is not None
        if skill_type == "BUFF_ALLY":
            if skill.target_type in ["ALLY_SINGLE", "ALLY_ALL", "SELF"] and skill.applied_status_effects:
                # Hier müsste man die 'is_positive' Eigenschaft der Effekte prüfen, falls vorhanden
                return True 
            return False
        if skill_type == "DEBUFF_ENEMY":
            if skill.target_type.startswith("ENEMY_") and skill.applied_status_effects:
                return True 
            return False
        if skill_type == "OFFENSIVE_ENEMY":
            is_offensive = skill.direct_effects and \
                           (skill.direct_effects.base_damage is not None or \
                            (skill.direct_effects.base_damage is None and True)) # True, wenn Waffenschaden als offensiv gilt
            return skill.target_type.startswith("ENEMY_") and is_offensive
        return False

    def _get_skill_potential_damage(self, skill_id: str) -> int: # Gleich wie in anderen Strategien
        skill = self.skill_definitions.get(skill_id)
        try: from src.config.config import CONFIG
        except ImportError: CONFIG = None
        base_damage_val = 0
        is_offensive = False
        if skill and skill.direct_effects:
            if skill.direct_effects.base_damage is not None:
                base_damage_val = skill.direct_effects.base_damage; is_offensive = True
            elif skill.direct_effects.base_damage is None:
                if CONFIG and hasattr(CONFIG, 'get'): base_damage_val = CONFIG.get("game_settings.base_weapon_damage", 5)
                else: base_damage_val = 5 
                is_offensive = True
        if not is_offensive or not skill or not skill.direct_effects : return 0
        multiplier = skill.direct_effects.multiplier
        attr_bonus = 0
        if skill.direct_effects.scaling_attribute:
            attr_bonus = self.actor.get_attribute_bonus(skill.direct_effects.scaling_attribute)
        return int((base_damage_val + attr_bonus) * multiplier)

    def decide_action(self, potential_targets_unused: List['CharacterInstance']) -> Optional[Tuple[str, 'CharacterInstance']]:
        if not self.actor or self.actor.is_defeated or not self.actor.can_act: return None
        allies = self._get_allies()
        opponents = self._get_opponents()
        
        usable_skills = [s_id for s_id in self.actor.skills if self.actor.can_afford_skill(self.skill_definitions.get(s_id))]
        if not usable_skills: 
            logger.debug(f"'{self.actor.name}' (SupportCaster) hat keine nutzbaren Skills.")
            return None

        # 1. Heilung
        healing_skills = [s_id for s_id in usable_skills if self._is_skill_type(s_id, "HEAL")]
        if healing_skills:
            injured_allies = sorted([ally for ally in allies if ally.current_hp < ally.max_hp],
                                    key=lambda a: (a.current_hp / a.max_hp) if a.max_hp > 0 else float('inf'))
            if injured_allies:
                target_for_heal = injured_allies[0]
                chosen_skill_id = healing_skills[0] 
                logger.debug(f"'{self.actor.name}' (SupportCaster) entscheidet HEILUNG: '{chosen_skill_id}' auf '{target_for_heal.name}'.") # KORREKTUR: DEBUG
                return chosen_skill_id, target_for_heal

        # 2. Buffs
        buff_skills = [s_id for s_id in usable_skills if self._is_skill_type(s_id, "BUFF_ALLY")]
        if buff_skills and allies:
            target_for_buff = random.choice(allies) 
            chosen_skill_id = random.choice(buff_skills)
            logger.debug(f"'{self.actor.name}' (SupportCaster) entscheidet BUFF: '{chosen_skill_id}' auf '{target_for_buff.name}'.") # KORREKTUR: DEBUG
            return chosen_skill_id, target_for_buff
        
        # 3. Debuffs
        debuff_skills = [s_id for s_id in usable_skills if self._is_skill_type(s_id, "DEBUFF_ENEMY")]
        if debuff_skills and opponents:
            target_for_debuff = random.choice(opponents)
            chosen_skill_id = random.choice(debuff_skills)
            logger.debug(f"'{self.actor.name}' (SupportCaster) entscheidet DEBUFF: '{chosen_skill_id}' auf '{target_for_debuff.name}'.") # KORREKTUR: DEBUG
            return chosen_skill_id, target_for_debuff

        # 4. Offensive Angriffe
        offensive_skills = [s_id for s_id in usable_skills if self._is_skill_type(s_id, "OFFENSIVE_ENEMY")]
        if offensive_skills and opponents:
            target_for_attack = random.choice(opponents)
            offensive_skills.sort(key=lambda s_id: self._get_skill_potential_damage(s_id), reverse=True)
            chosen_skill_id = offensive_skills[0]
            logger.debug(f"'{self.actor.name}' (SupportCaster) entscheidet ANGRIFF: '{chosen_skill_id}' auf '{target_for_attack.name}'.") # KORREKTUR: DEBUG
            return chosen_skill_id, target_for_attack

        logger.debug(f"'{self.actor.name}' (SupportCaster) konnte keine passende Aktion finden.")
        return None

# ... (if __name__ == '__main__' Block bleibt gleich)
if __name__ == '__main__':
    from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
    from src.config.config import CONFIG
    print("\n--- Teste SupportCasterStrategy ---")
    try:
        char_defs = load_character_templates()
        opp_defs = load_opponent_templates()
        skill_defs = load_skill_templates()
        ai_actor_template = opp_defs["goblin_shaman_lv3"]
        ai_actor = CharacterInstance(base_template=ai_actor_template, name_override="AI Support Shaman")
        ai_actor.current_mana = ai_actor.max_mana 
        ally_goblin_template = opp_defs["goblin_lv1"]
        ally_goblin = CharacterInstance(base_template=ally_goblin_template, name_override="Ally Goblin")
        player_krieger = CharacterInstance(base_template=char_defs["krieger"], name_override="Player Krieger")
        player_magier = CharacterInstance(base_template=char_defs["magier"], name_override="Player Magier")
        combat_participants = [ai_actor, ally_goblin, player_krieger, player_magier]
        strategy = SupportCasterStrategy(actor=ai_actor, 
                                          all_entities_in_combat=combat_participants,
                                          skill_definitions=skill_defs,
                                          character_definitions=char_defs)
        print(f"\nAI Akteur: {ai_actor.name} mit Skills: {ai_actor.skills}")
        print("Verbündete des Akteurs:")
        for ally_char in strategy._get_allies(): print(f" - {ally_char.name}")
        print("Gegner des Akteurs:")
        for opp_char in strategy._get_opponents(): print(f" - {opp_char.name}")
        print("\n-- Szenario 1: Verbündeter stark verletzt --")
        ally_goblin.current_hp = int(ally_goblin.max_hp * 0.2) 
        print(f"{ally_goblin.name} HP: {ally_goblin.current_hp}/{ally_goblin.max_hp}")
        action1 = strategy.decide_action([]) 
        if action1:
            skill_chosen, target_chosen = action1
            print(f"Aktion 1: Skill '{skill_chosen}' auf '{target_chosen.name}'.")
        else: print("Aktion 1: Keine Aktion entschieden.")
        ally_goblin.current_hp = ally_goblin.max_hp 
        print("\n-- Szenario 2: Kein Verbündeter verletzt, Gegner vorhanden --")
        action2 = strategy.decide_action([])
        if action2:
            skill_chosen, target_chosen = action2
            print(f"Aktion 2: Skill '{skill_chosen}' auf Gegner '{target_chosen.name}'.")
        else: print("Aktion 2: Keine Aktion entschieden.")
        print("\n-- Szenario 3: Nur noch Angriffsoptionen --")
        original_skills = list(ai_actor.skills) # Skills sichern
        ai_actor.skills = ["basic_magic_bolt"] 
        ai_actor.current_mana = ai_actor.max_mana
        action3 = strategy.decide_action([])
        if action3:
            skill_chosen, target_chosen = action3
            print(f"Aktion 3: Skill '{skill_chosen}' auf Gegner '{target_chosen.name}'.")
        else: print("Aktion 3: Keine Aktion entschieden.")
        ai_actor.skills = original_skills # Skills wiederherstellen
        print("\n-- Szenario 4: Keine Ressourcen --")
        ai_actor.current_mana = 0
        action4 = strategy.decide_action([])
        if action4:
            skill_chosen, target_chosen = action4
            print(f"Aktion 4: Skill '{skill_chosen}' auf '{target_chosen.name}'.")
        else: print("Aktion 4: Keine Aktion entschieden (korrekt).")
    except ImportError as e: print(f"FEHLER bei Imports für den Test in support_caster.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in support_caster.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    print("\n--- SupportCasterStrategy-Tests abgeschlossen ---")