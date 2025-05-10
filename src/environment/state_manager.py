# src/environment/state_manager.py
"""
Verwaltet den Spielzustand für die RL-Umgebung, einschließlich Held, Gegner
und Kampfinteraktionen.
"""
import logging
import random
from typing import List, Optional, Dict, Any, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.character import CharacterTemplate
from src.definitions.opponent import OpponentTemplate
from src.game_logic.combat import CombatHandler, process_beginning_of_turn_effects # process_beginning_of_turn_effects hier oder in Env? Hier ist ok.
from src.ai.ai_dispatcher import get_ai_strategy_instance

logger = logging.getLogger(__name__)

class EnvStateManager:
    def __init__(self, 
                 character_templates: Dict[str, CharacterTemplate],
                 opponent_templates: Dict[str, OpponentTemplate],
                 combat_handler: CombatHandler, 
                 max_supported_opponents: int): # Max Slots für Gegner
        self.character_templates = character_templates
        self.opponent_templates = opponent_templates
        self.combat_handler = combat_handler
        self.max_supported_opponents = max_supported_opponents # Wie viele Gegner-Slots es in der Env gibt

        self.hero: Optional[CharacterInstance] = None
        # self.opponents ist jetzt eine Liste von CharacterInstance oder None fester Länge
        self.opponents: List[Optional[CharacterInstance]] = [None] * self.max_supported_opponents
        self.all_participants: List[CharacterInstance] = [] 

        self.current_episode_step: int = 0
        self.last_action_successful: bool = True 

    def _create_dynamic_opponent_team(self, opponent_config: Dict[str, Any]) -> List[Optional[CharacterInstance]]:
        """Erstellt ein Gegnerteam basierend auf der Konfiguration (num, pool). Füllt self.opponents."""
        new_opponent_list: List[Optional[CharacterInstance]] = [None] * self.max_supported_opponents
        num_opponents_to_create = opponent_config.get("num_opponents", 1)
        level_pool_str = str(opponent_config.get("level_pool", "1-2")).lower()
        specific_ids = opponent_config.get("ids") # Optional: Liste spezifischer Gegner-IDs

        eligible_templates: List[OpponentTemplate] = []

        if specific_ids and isinstance(specific_ids, list):
            logger.debug(f"StateManager: Erstelle Gegnerteam mit spezifischen IDs: {specific_ids}")
            for i, opp_id in enumerate(specific_ids):
                if i >= self.max_supported_opponents: break # Nicht mehr als max Slots füllen
                template = self.opponent_templates.get(opp_id)
                if template:
                    new_opponent_list[i] = CharacterInstance(base_template=template, name_override=f"{template.name} #{i+1}")
                else:
                    logger.warning(f"StateManager: Spezifisches Gegner-Template '{opp_id}' nicht gefunden.")
            return new_opponent_list # Rückgabe hier, da spezifische IDs Vorrang haben

        # Wenn keine spezifischen IDs, dann basierend auf Pool und Anzahl
        min_lvl, max_lvl = -1, -1
        if level_pool_str != "all":
            try:
                parts = level_pool_str.split('-')
                min_lvl = int(parts[0])
                max_lvl = int(parts[1]) if len(parts) > 1 else min_lvl
            except (ValueError, IndexError):
                logger.warning(f"StateManager: Ungültiger Level-Pool '{level_pool_str}'. Verwende 'all'.")
                level_pool_str = "all"

        for opp_template in self.opponent_templates.values():
            if level_pool_str == "all":
                eligible_templates.append(opp_template)
            elif hasattr(opp_template, 'level') and min_lvl <= opp_template.level <= max_lvl:
                eligible_templates.append(opp_template)
        
        if not eligible_templates:
            logger.warning(f"StateManager: Keine Gegner im Level-Pool '{level_pool_str}'. Fallback auf 'goblin_lv1'.")
            gob_template = self.opponent_templates.get("goblin_lv1")
            if gob_template: eligible_templates = [gob_template]
            else: 
                logger.error("StateManager: Fallback 'goblin_lv1' nicht gefunden. Kein Gegnerteam erstellt.")
                return new_opponent_list # Leere Liste (bzw. Liste von Nones)

        # Erstelle die angeforderte Anzahl von Gegnern, aber nicht mehr als Slots verfügbar sind
        num_to_actually_create = min(num_opponents_to_create, self.max_supported_opponents, len(eligible_templates) if eligible_templates else 0)

        for i in range(num_to_actually_create):
            chosen_template = random.choice(eligible_templates) # TODO: Vermeide Duplikate, wenn gewünscht und len(eligible) > num
            new_opponent_list[i] = CharacterInstance(base_template=chosen_template, name_override=f"{chosen_template.name} #{i+1}")
            
        return new_opponent_list


    def reset_state(self, hero_id: str, opponent_setup_config: Dict[str, Any]) -> bool:
        self.current_episode_step = 0
        self.last_action_successful = True

        hero_template = self.character_templates.get(hero_id)
        if not hero_template:
            logger.error(f"StateManager: Helden-Template '{hero_id}' nicht gefunden.")
            return False
        self.hero = CharacterInstance(base_template=hero_template, name_override=hero_template.name)

        # Gegner dynamisch erstellen
        self.opponents = self._create_dynamic_opponent_team(opponent_setup_config)
        
        self._update_all_participants_list()

        if not self.hero: return False # Sollte nicht passieren
        if not any(self.opponents): # Kein einziger Gegner konnte erstellt werden
            logger.warning("StateManager: Kein Gegnerteam konnte erstellt werden. Kampf ist trivial.")
            # Hier könnte man entscheiden, ob das ein Fehler ist oder ein trivialer Sieg.
            # Fürs Erste: Episode kann trotzdem starten, Held gewinnt sofort.
            
        logger.info(f"StateManager: Zustand resettet. Held: {self.hero.name}, "
                    f"Gegner: {[o.name for o in self.opponents if o]}.")
        return True

    def _update_all_participants_list(self):
        self.all_participants = [p for p in ([self.hero] + self.opponents) if p and not p.is_defeated]

    def get_hero(self) -> Optional[CharacterInstance]:
        return self.hero

    def get_live_opponents(self) -> List[CharacterInstance]:
        return [opp for opp in self.opponents if opp and not opp.is_defeated]
    
    def get_all_live_participants(self) -> List[CharacterInstance]:
        self._update_all_participants_list() 
        return self.all_participants

    def execute_hero_action(self, skill_id: str, target_instance: Optional[CharacterInstance]) -> Tuple[bool, str]:
        self.last_action_successful = False 
        if not self.hero or self.hero.is_defeated or not self.hero.can_act:
            msg = f"Held {self.hero.name if self.hero else 'N/A'} kann nicht handeln."
            logger.debug(f"StateManager: {msg}")
            return False, msg
        
        if not target_instance:
             msg = f"Held {self.hero.name} versuchte Skill {skill_id} ohne gültiges Ziel."
             logger.warning(f"StateManager: {msg}")
             return False, msg

        # Die `execute_skill_action` im CombatHandler ist verantwortlich für die eigentliche Aktionslogik
        # und sollte auch Ressourcen verbrauchen etc.
        # Hier rufen wir sie nur auf.
        self.combat_handler.execute_skill_action(self.hero, skill_id, [target_instance]) # targets ist eine Liste
        self.last_action_successful = True # Annahme: Wenn CombatHandler keine Exception wirft, ist die Ausführung "gestartet"
        
        msg = f"Held {self.hero.name} führte Skill {skill_id} auf {target_instance.name} aus (via StateManager)."
        logger.debug(f"StateManager: {msg}")
        return True, msg


    def run_opponent_turns(self) -> None:
        if not self.hero: return 

        # Iteriere über die Slots, da Gegner besiegt werden können
        for i in range(len(self.opponents)):
            opponent = self.opponents[i] # Kann None sein, wenn Slot leer
            if not opponent or opponent.is_defeated:
                continue

            process_beginning_of_turn_effects(opponent) 
            if opponent.is_defeated or not opponent.can_act:
                continue

            # Gegner zielen auf den Helden (wenn er lebt)
            targets_for_npc = [self.hero] if self.hero and not self.hero.is_defeated else []
            
            if targets_for_npc:
                current_all_participants = self.get_all_live_participants() # Aktuelle Liste für KI-Kontext
                ai_strategy = get_ai_strategy_instance(opponent, current_all_participants)
                if ai_strategy:
                    decision = ai_strategy.decide_action(targets_for_npc) 
                    if decision:
                        opp_skill_id, opp_target_instance = decision 
                        logger.debug(f"StateManager NPC '{opponent.name}' Aktion: Skill '{opp_skill_id}' auf '{opp_target_instance.name}'.")
                        self.combat_handler.execute_skill_action(opponent, opp_skill_id, [opp_target_instance])
                else: # Keine Strategie für NPC
                    logger.debug(f"StateManager NPC '{opponent.name}' hat keine KI-Strategie oder konnte keine Aktion wählen.")
            
            if self.hero.is_defeated: 
                break 


    def check_combat_end_conditions(self) -> Tuple[bool, bool, str]:
        hero_won = False
        terminated = False
        message = ""

        if self.hero and self.hero.is_defeated:
            terminated = True
            hero_won = False
            message = "Held wurde besiegt."
            # logger.info(f"StateManager: {message}") # Wird in RPGEnv geloggt
            return terminated, hero_won, message

        live_opponents_list = self.get_live_opponents()
        if not live_opponents_list and self.hero and not self.hero.is_defeated : # Keine lebenden Gegner mehr UND Held lebt noch
            terminated = True
            hero_won = True
            message = "Alle Gegner wurden besiegt."
            # logger.info(f"StateManager: {message}") # Wird in RPGEnv geloggt
            return terminated, hero_won, message
            
        return terminated, hero_won, message

    def increment_step(self):
        self.current_episode_step += 1