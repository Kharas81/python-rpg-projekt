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
from src.game_logic.combat import CombatHandler, process_beginning_of_turn_effects
from src.ai.ai_dispatcher import get_ai_strategy_instance

# Definitionen werden hier nicht direkt geladen, sondern sollten dem StateManager
# bei der Initialisierung (oder über eine globale Instanz) übergeben werden.
# Für den Moment nehmen wir an, dass die Templates bei Bedarf von außen kommen.

logger = logging.getLogger(__name__)

class EnvStateManager:
    def __init__(self, 
                 character_templates: Dict[str, CharacterTemplate],
                 opponent_templates: Dict[str, OpponentTemplate],
                 combat_handler: CombatHandler, # Eine CombatHandler-Instanz
                 max_supported_opponents: int):
        self.character_templates = character_templates
        self.opponent_templates = opponent_templates
        self.combat_handler = combat_handler
        self.max_supported_opponents = max_supported_opponents

        self.hero: Optional[CharacterInstance] = None
        self.opponents: List[Optional[CharacterInstance]] = [None] * self.max_supported_opponents
        self.all_participants: List[CharacterInstance] = [] # Lebende Teilnehmer für Initiative etc.

        self.current_episode_step: int = 0
        self.last_action_successful: bool = True # War die letzte Agentenaktion erfolgreich?

    def reset_state(self, hero_id: str, opponent_ids: List[str]) -> bool:
        """
        Setzt den Spielzustand für eine neue Episode zurück.
        Erstellt Held und Gegner.
        Gibt True bei Erfolg zurück, False bei Fehlern.
        """
        self.current_episode_step = 0
        self.last_action_successful = True

        # Held erstellen
        hero_template = self.character_templates.get(hero_id)
        if not hero_template:
            logger.error(f"StateManager: Helden-Template '{hero_id}' nicht gefunden.")
            return False
        self.hero = CharacterInstance(base_template=hero_template, name_override=hero_template.name)

        # Gegner erstellen
        self.opponents = [None] * self.max_supported_opponents 
        actual_opponent_ids = opponent_ids[:self.max_supported_opponents] # Begrenzen

        for i, opp_id in enumerate(actual_opponent_ids):
            opp_template = self.opponent_templates.get(opp_id)
            if not opp_template:
                logger.error(f"StateManager: Gegner-Template '{opp_id}' nicht gefunden.")
                # Hier könnten wir entscheiden, ob wir abbrechen oder mit weniger Gegnern fortfahren
                continue # Überspringe diesen Gegner
            self.opponents[i] = CharacterInstance(base_template=opp_template, name_override=f"{opp_template.name} #{i+1}")
        
        self._update_all_participants_list()

        if not self.hero: # Sollte nicht passieren, wenn Template-Prüfung oben erfolgreich war
            return False
            
        logger.info(f"StateManager: Zustand resettet. Held: {self.hero.name}, "
                    f"Gegner: {[o.name for o in self.opponents if o]}.")
        return True

    def _update_all_participants_list(self):
        """Aktualisiert die Liste aller lebenden Teilnehmer."""
        self.all_participants = [p for p in ([self.hero] + self.opponents) if p and not p.is_defeated]

    def get_hero(self) -> Optional[CharacterInstance]:
        return self.hero

    def get_live_opponents(self) -> List[CharacterInstance]:
        """Gibt eine Liste der lebenden Gegner zurück."""
        return [opp for opp in self.opponents if opp and not opp.is_defeated]
    
    def get_all_live_participants(self) -> List[CharacterInstance]:
        """Gibt alle lebenden Teilnehmer zurück (Held + Gegner)."""
        self._update_all_participants_list() # Sicherstellen, dass sie aktuell ist
        return self.all_participants

    def execute_hero_action(self, skill_id: str, target_instance: Optional[CharacterInstance]) -> Tuple[bool, str]:
        """
        Führt die Aktion des Helden aus.
        Gibt (Erfolg: bool, Meldung: str) zurück.
        """
        self.last_action_successful = False # Standardmäßig nicht erfolgreich
        if not self.hero or self.hero.is_defeated or not self.hero.can_act:
            msg = f"Held {self.hero.name if self.hero else 'N/A'} kann nicht handeln."
            logger.debug(f"StateManager: {msg}")
            return False, msg
        
        if not target_instance: # Wenn ein Skill ein Ziel braucht, aber keines gegeben ist
             # Die Skill-Definition wird benötigt, um zu prüfen, ob ein Ziel nötig ist.
             # Diese Prüfung sollte idealerweise im ActionManager/action_masks erfolgen.
             # Hier nehmen wir an, die Aktion ist schon validiert worden.
             # Wenn kein Ziel da ist, obwohl nötig, war es eine ungültige Aktion des Agenten.
             msg = f"Held {self.hero.name} versuchte Skill {skill_id} ohne gültiges Ziel."
             logger.warning(f"StateManager: {msg}")
             return False, msg


        # Die execute_skill_action im CombatHandler macht bereits die internen Checks
        # und gibt ggf. Warnungen aus.
        # Wir nehmen hier an, dass der CombatHandler korrekt funktioniert.
        # Die Rückgabe von execute_skill_action ist nicht direkt ein Erfolg/Misserfolg,
        # sondern führt die Aktion aus. Wir müssen den Zustand danach prüfen.
        
        # Speichere Zustände vor der Aktion, um Änderungen zu erkennen (für Reward)
        hp_before_action: Dict[str, int] = {p.instance_id: p.current_hp for p in self.get_all_live_participants()}

        self.combat_handler.execute_skill_action(self.hero, skill_id, [target_instance])
        self.last_action_successful = True # Annahme: Wenn keine Exception, war es "erfolgreich" im Sinne der Ausführung

        # Reward-relevante Änderungen könnten hier berechnet oder vom RewardManager abgefragt werden.
        # z.B. delta_hp_opponents, delta_hp_hero
        
        msg = f"Held {self.hero.name} führte Skill {skill_id} auf {target_instance.name} aus."
        logger.debug(f"StateManager: {msg}")
        return True, msg


    def run_opponent_turns(self) -> None:
        """Lässt alle lebenden Gegner ihre Züge ausführen."""
        if not self.hero: return # Kein Held, kein Kampf

        # Gegner agieren in einer festen Reihenfolge (oder nach Initiative)
        # Hier einfache Iteration durch die Liste
        for opponent in self.opponents:
            if not opponent or opponent.is_defeated:
                continue

            process_beginning_of_turn_effects(opponent) # Effekte für den Gegner ticken lassen
            if opponent.is_defeated or not opponent.can_act:
                continue

            targets_for_npc = [self.hero] if self.hero and not self.hero.is_defeated else []
            
            if targets_for_npc:
                # Wichtig: `get_all_live_participants()` für den Kontext der KI-Strategie
                ai_strategy = get_ai_strategy_instance(opponent, self.get_all_live_participants())
                if ai_strategy:
                    decision = ai_strategy.decide_action(targets_for_npc) # KI zielt auf die übergebene Liste
                    if decision:
                        opp_skill_id, opp_target_instance = decision # opp_target_instance ist hier der Held
                        logger.debug(f"StateManager NPC '{opponent.name}' Aktion: Skill '{opp_skill_id}' auf '{opp_target_instance.name}'.")
                        self.combat_handler.execute_skill_action(opponent, opp_skill_id, [opp_target_instance])
                else:
                    logger.debug(f"StateManager NPC '{opponent.name}' hat keine KI-Strategie oder konnte keine Aktion wählen.")
            
            if self.hero.is_defeated: # Prüfen, ob Held durch NPC-Aktion besiegt wurde
                break # Kampf endet sofort für diese Runde der NPC-Aktionen


    def check_combat_end_conditions(self) -> Tuple[bool, bool, str]:
        """
        Prüft, ob der Kampf beendet ist.
        Gibt zurück: (terminated, hero_won, message)
        """
        hero_won = False
        terminated = False
        message = ""

        if self.hero and self.hero.is_defeated:
            terminated = True
            hero_won = False
            message = "Held wurde besiegt."
            logger.info(f"StateManager: {message}")
            return terminated, hero_won, message

        live_opponents = self.get_live_opponents()
        if not live_opponents: # Keine lebenden Gegner mehr
            terminated = True
            hero_won = True
            message = "Alle Gegner wurden besiegt."
            logger.info(f"StateManager: {message}")
            return terminated, hero_won, message
            
        return terminated, hero_won, message

    def increment_step(self):
        self.current_episode_step += 1