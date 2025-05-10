"""
Action Manager for RPG Environment

Diese Klasse ist verantwortlich für die Definition des Aktionsraums,
die Dekodierung von Aktionen und die Erstellung der Aktionsmaske.
"""
import random
from typing import Dict, Any, Optional, Tuple, List

import numpy as np

from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter # Benötigt für Zielvalidierung in Maske
from src.definitions.skill import SkillDefinition
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

# Konstanten (sollten mit denen in RPGEnv und ObservationManager übereinstimmen)
AGENT_MAX_SKILLS_ACTION = 5 # Max Skills im Aktionsraum des Agenten

class ActionManager:
    def __init__(self,
                 agent_max_skills: int = AGENT_MAX_SKILLS_ACTION,
                 num_target_slots: int = 7 # Beispiel: 1 (self) + 1 (max_allies) + 5 (max_enemies)
                 ):
        self.agent_max_skills = agent_max_skills
        self.num_target_slots = num_target_slots
        self.action_space_size = self.agent_max_skills * self.num_target_slots
        logger.info(f"ActionManager initialisiert. Action Space Size: {self.action_space_size}")
        logger.info(f"  (agent_max_skills: {self.agent_max_skills}, num_target_slots: {self.num_target_slots})")


    def decode_action(self,
                      action_int: int,
                      agent_skill_map: List[Optional[SkillDefinition]],
                      target_map: List[Optional[CharacterInstance]],
                      agent_character: Optional[CharacterInstance],
                      current_encounter: Optional[CombatEncounter] # Hinzugefügt für Splash/Cleave
                      ) -> Tuple[Optional[SkillDefinition], Optional[CharacterInstance], List[CharacterInstance]]:
        """
        Dekodiert eine Integer-Aktion in einen Skill und ein/mehrere Ziel(e).
        """
        if action_int < 0 or action_int >= self.action_space_size:
            logger.warning(f"Ungültige action_int: {action_int}. Muss zwischen 0 und {self.action_space_size -1} sein.")
            return None, None, []

        skill_idx = action_int // self.num_target_slots
        target_slot_idx = action_int % self.num_target_slots

        chosen_skill: Optional[SkillDefinition] = None
        if skill_idx < len(agent_skill_map): # agent_skill_map hat Länge self.agent_max_skills
            chosen_skill = agent_skill_map[skill_idx]
        
        primary_target: Optional[CharacterInstance] = None
        if target_slot_idx < len(target_map): # target_map hat Länge self.num_target_slots
            primary_target = target_map[target_slot_idx]
            
        secondary_targets: List[CharacterInstance] = []
        
        # Logik für sekundäre Ziele bei Flächeneffekten
        if chosen_skill and chosen_skill.is_area_effect() and primary_target and current_encounter:
            # Nur Ziele aus der "gegnerischen" oder "eigenen" Gruppe des Primärziels in Betracht ziehen
            # und sicherstellen, dass das Primärziel nicht in den Sekundärzielen ist.
            potential_secondary_pool: List[CharacterInstance] = []

            if primary_target in current_encounter.opponents:
                potential_secondary_pool = [
                    t for t in current_encounter.opponents if t != primary_target and t.is_alive()
                ]
            elif primary_target in current_encounter.players:
                potential_secondary_pool = [
                    t for t in current_encounter.players if t != primary_target and t.is_alive()
                ]

            if chosen_skill.get_area_type() == 'SPLASH':
                secondary_targets = potential_secondary_pool # Alle anderen in der Gruppe
            elif chosen_skill.get_area_type() == 'CLEAVE':
                if potential_secondary_pool:
                    secondary_targets = [random.choice(potential_secondary_pool)]
            # Weitere Area-Types könnten hier behandelt werden

        if not chosen_skill:
            logger.debug(f"Aktion {action_int} dekodiert zu ungültigem Skill-Index {skill_idx}.")
            return None, None, []
        if not primary_target:
            # Wenn der Skill ein Selbst-Effekt ist, ist das Ziel der Agent selbst
            if chosen_skill.is_self_effect() and agent_character:
                primary_target = agent_character
            else: # Kein Ziel für einen nicht-Selbst-Skill
                 logger.debug(f"Aktion {action_int} dekodiert zu ungültigem Target-Slot-Index {target_slot_idx} für nicht-Selbst-Skill oder kein Agent vorhanden.")
                 return None, None, []
            
        return chosen_skill, primary_target, secondary_targets

    def get_action_mask(self,
                        agent_character: Optional[CharacterInstance],
                        current_encounter: Optional[CombatEncounter],
                        agent_skill_map: List[Optional[SkillDefinition]],
                        target_map: List[Optional[CharacterInstance]]
                        ) -> List[bool]:
        """
        Gibt eine Maske für gültige Aktionen zurück.
        """
        mask = [False] * self.action_space_size
        if not agent_character or not current_encounter or not agent_character.can_act():
            # Wenn der Agent nicht handeln kann, ist keine Aktion gültig (oder nur eine "Passen"-Aktion)
            # Fürs Erste: Wenn der Action Space > 0 ist, erlaube die erste Aktion als Notfall-Passen.
            if self.action_space_size > 0 : mask[0] = True
            return mask

        for skill_idx, skill_def in enumerate(agent_skill_map): # Länge: self.agent_max_skills
            if not skill_def:  # Leerer Skill-Slot im Agenten-Mapping
                continue

            can_use_skill_base = agent_character.has_enough_resource(skill_def)

            for target_slot_idx, target_char_in_map in enumerate(target_map): # Länge: self.num_target_slots
                action_int = skill_idx * self.num_target_slots + target_slot_idx
                # Index-Check ist eigentlich nicht nötig wenn Maps korrekt dimensioniert sind, aber sicher ist sicher
                if action_int >= self.action_space_size: 
                    logger.error(f"Action index {action_int} out of bounds for mask size {self.action_space_size}")
                    continue 

                is_valid_action = False
                if can_use_skill_base:
                    actual_target_for_check: Optional[CharacterInstance] = None

                    if skill_def.is_self_effect():
                        # Aktion ist gültig, wenn der target_slot den Agenten selbst repräsentiert
                        # und der Agent anvisierbar ist (was er für self-effects immer sein sollte, wenn er handelt).
                        # target_map[0] ist immer der Agent.
                        if target_slot_idx == 0: # Strikte Prüfung, dass die Aktion auf den "Selbst"-Slot geht
                            is_valid_action = True
                            actual_target_for_check = agent_character
                    elif target_char_in_map and target_char_in_map.can_be_targeted():
                        is_valid_action = True # Grundsätzlich anvisierbar
                        actual_target_for_check = target_char_in_map
                    
                    # Zusätzliche Validierungen basierend auf Skill-Typ und Ziel
                    if is_valid_action and actual_target_for_check:
                        is_heal = 'base_healing' in skill_def.effects
                        is_attack = 'base_damage' in skill_def.effects or skill_def.get_base_damage() is not None

                        if is_heal:
                            # Heilung nicht auf Gegner
                            if actual_target_for_check in current_encounter.opponents:
                                is_valid_action = False
                            # Heilung nicht auf Ziele mit vollen HP (es sei denn, der Skill hat andere Effekte wie Buffs)
                            elif actual_target_for_check.hp >= actual_target_for_check.get_max_hp() and not skill_def.applies_effects:
                                is_valid_action = False
                        elif is_attack:
                            # Angriff nicht auf Verbündete (außer Agent selbst, wenn Skill es explizit erlaubt - hier nicht)
                            if actual_target_for_check in current_encounter.players and \
                               actual_target_for_check != agent_character:
                                is_valid_action = False
                            # Direkter Angriff auf sich selbst nur, wenn es KEIN self_effect ist und explizit gewollt
                            # (z.B. Blutmagie - aktuell nicht unterstützt, daher hier verbieten)
                            elif actual_target_for_check == agent_character and not skill_def.is_self_effect():
                                is_valid_action = False
                        # Hier könnte man Logik für Buffs (nicht auf Gegner) / Debuffs (nicht auf Verbündete) einfügen
                        # Beispiel:
                        # if skill_def.applies_effects and any(e.id.endswith("_UP") for e in skill_def.applies_effects): # Ist ein Buff
                        #    if actual_target_for_check in current_encounter.opponents:
                        #        is_valid_action = False # Buff nicht auf Gegner
                        # elif skill_def.applies_effects and any(e.id.endswith("_DOWN") for e in skill_def.applies_effects): # Ist ein Debuff
                        #    if actual_target_for_check in current_encounter.players and actual_target_for_check != agent_character:
                        #        is_valid_action = False # Debuff nicht auf andere Spieler
                
                mask[action_int] = is_valid_action
        
        if not any(mask) and self.action_space_size > 0:
            logger.warning("Keine gültige Aktion in ActionManager.get_action_mask gefunden. Erlaube Aktion 0 als Fallback.")
            mask[0] = True
        return mask