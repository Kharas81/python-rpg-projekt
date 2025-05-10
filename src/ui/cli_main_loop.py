# src/ui/cli_main_loop.py
"""
Steuert die automatische Simulationsschleife für Kämpfe im CLI-Modus.
Nutzt die KI, Kampflogik und CLI-Ausgaben.
"""
import time
import logging
import random
from typing import List, Optional, Tuple, Dict, Any 

from src.game_logic.entities import CharacterInstance
from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates 
from src.definitions.character import CharacterTemplate
from src.definitions.opponent import OpponentTemplate
from src.definitions.skill import SkillTemplate 
from src.ai.ai_dispatcher import get_ai_strategy_instance
from src.game_logic.combat import CombatHandler, get_initiative_order, process_beginning_of_turn_effects
from src.ui import cli_output

logger = logging.getLogger(__name__)

SIMULATION_DELAY_BETWEEN_TURNS = 0.7  # Etwas schneller für Tests
SIMULATION_DELAY_BETWEEN_ACTIONS = 0.3 
MAX_COMBAT_ROUNDS = 50 

try:
    SKILL_DEFINITIONS_CLI: Dict[str, SkillTemplate] = load_skill_templates()
except Exception as e:
    logger.critical(f"FATAL: Skill-Definitionen konnten nicht geladen werden in cli_main_loop.py: {e}", exc_info=True)
    SKILL_DEFINITIONS_CLI = {}

class CLISimulationLoop:
    def __init__(self):
        self.combat_handler = CombatHandler()
        self.character_templates: Dict[str, CharacterTemplate] = {}
        self.opponent_templates: Dict[str, OpponentTemplate] = {}
        self._load_definitions()

    def _load_definitions(self):
        try:
            self.character_templates = load_character_templates()
            self.opponent_templates = load_opponent_templates()
            if not self.character_templates or not self.opponent_templates:
                 logger.warning("Einige oder alle Charakter/Gegner-Templates konnten nicht geladen werden.")
            else:
                 logger.info("Charakter- und Gegner-Templates für die Simulation geladen.")
        except Exception as e:
            logger.critical(f"Fehler beim Laden der Definitionen für die Simulation: {e}", exc_info=True)

    def _create_player_team(self, player_ids: List[str]) -> List[CharacterInstance]:
        team: List[CharacterInstance] = []
        if not player_ids: # Fallback, falls keine Spieler-IDs übergeben werden
            logger.warning("Keine Spieler-IDs für Team-Erstellung übergeben. Verwende Standard-Krieger.")
            player_ids = ["krieger"]

        for i, player_id in enumerate(player_ids):
            template = self.character_templates.get(player_id)
            if template:
                name_override = template.name # Für Single-Player oder wenn nur einer da ist
                if len(player_ids) > 1 : # Mehrere Spieler im Team
                     name_override = f"{template.name} {i+1}"
                instance = CharacterInstance(base_template=template, name_override=name_override)
                team.append(instance)
            else:
                logger.error(f"Spieler-Template mit ID '{player_id}' nicht gefunden. Kann nicht erstellt werden.")
        return team

    def _create_opponent_team(self, opponent_config: Dict[str, Any]) -> List[CharacterInstance]:
        team: List[CharacterInstance] = []
        num_opponents = opponent_config.get("num_opponents", 1)
        level_pool_str = str(opponent_config.get("level_pool", "1-2")).lower() # Sicherstellen, dass es ein String ist
        
        eligible_opponents: List[OpponentTemplate] = []
        min_lvl, max_lvl = -1, -1

        if level_pool_str != "all":
            try:
                parts = level_pool_str.split('-')
                min_lvl = int(parts[0])
                max_lvl = int(parts[1]) if len(parts) > 1 else min_lvl
            except (ValueError, IndexError):
                logger.warning(f"Ungültiger Level-Pool String: '{level_pool_str}'. Verwende alle Gegner.")
                level_pool_str = "all" 

        if not self.opponent_templates: # Sicherstellen, dass Templates geladen sind
            logger.error("Keine Gegner-Templates geladen. Gegnerteam kann nicht erstellt werden.")
            return []

        for opp_template in self.opponent_templates.values():
            if level_pool_str == "all":
                eligible_opponents.append(opp_template)
            elif hasattr(opp_template, 'level') and min_lvl <= opp_template.level <= max_lvl:
                eligible_opponents.append(opp_template)
        
        if not eligible_opponents:
            logger.warning(f"Keine Gegner im Level-Pool '{level_pool_str}' gefunden. Versuche Fallback auf 'goblin_lv1'.")
            gob_template = self.opponent_templates.get("goblin_lv1")
            if gob_template:
                eligible_opponents = [gob_template] 
            if not eligible_opponents:
                 logger.error("Fallback-Gegner 'goblin_lv1' nicht gefunden. Gegnerteam kann nicht erstellt werden.")
                 return []

        for i in range(num_opponents):
            if not eligible_opponents: 
                logger.warning(f"Nicht genügend unterschiedliche Gegner im Pool, um {num_opponents} zu erstellen. Erstellt: {len(team)}")
                break
            chosen_template = random.choice(eligible_opponents)
            instance = CharacterInstance(base_template=chosen_template, name_override=f"{chosen_template.name} #{i+1}")
            team.append(instance)
            
        return team

    def _display_team_status(self, team: List[CharacterInstance], team_name: str, is_player_team: bool):
        cli_output.print_message(f"\n--- Status {team_name} ---", bold=True)
        for member in team:
            cli_output.display_character_status(member, is_player_team=is_player_team)

    def _get_opposing_team(self, current_actor: CharacterInstance, player_team: List[CharacterInstance], opponent_team: List[CharacterInstance]) -> List[CharacterInstance]:
        if current_actor in player_team:
            return [m for m in opponent_team if not m.is_defeated]
        elif current_actor in opponent_team:
            return [m for m in player_team if not m.is_defeated]
        return [] 

    def run_combat_encounter(self, 
                             player_team_ids: List[str], 
                             opponent_setup_config: Dict[str, Any] 
                             ) -> Optional[str]:
        if not self.character_templates or not self.opponent_templates: # Prüfung, ob Templates geladen sind
            if not self._load_definitions_if_empty(): # Versuch, sie nachzuladen
                cli_output.print_message("Fehler: Definitionen nicht geladen und konnten nicht nachgeladen werden. Kampf kann nicht gestartet werden.", cli_output.Colors.RED)
                return None


        player_team = self._create_player_team(player_team_ids)
        opponent_team = self._create_opponent_team(opponent_setup_config) 

        if not player_team:
            cli_output.print_message(f"Fehler: Spieler-Team konnte nicht erstellt werden (IDs: {player_team_ids}). Kampf abgebrochen.", cli_output.Colors.RED)
            return None
        if not opponent_team:
            cli_output.print_message(f"Fehler: Gegner-Team konnte nicht erstellt werden (Config: {opponent_setup_config}). Kampf abgebrochen.", cli_output.Colors.RED)
            return None
        
        all_participants = player_team + opponent_team
        round_number = 0

        cli_output.print_message("\n" + "="*10 + " KAMPF BEGINNT " + "="*10, cli_output.Colors.BOLD + cli_output.Colors.YELLOW)
        self._display_team_status(player_team, "Spieler-Team", True)
        self._display_team_status(opponent_team, "Gegner-Team", False)
        time.sleep(SIMULATION_DELAY_BETWEEN_TURNS)

        while round_number < MAX_COMBAT_ROUNDS:
            round_number += 1
            cli_output.display_combat_round_start(round_number)
            initiative_order = get_initiative_order(all_participants)
            cli_output.print_message(f"Initiative-Reihenfolge: {', '.join([p.name for p in initiative_order])}", cli_output.Colors.CYAN)
            time.sleep(SIMULATION_DELAY_BETWEEN_ACTIONS)

            for actor in initiative_order:
                if actor.is_defeated:
                    continue
                process_beginning_of_turn_effects(actor)
                if actor.is_defeated: 
                    cli_output.print_message(f"{actor.name} wurde durch einen Effekt zu Beginn des Zuges besiegt.", cli_output.Colors.RED)
                    # Prüfen, ob das der letzte Gegner des anderen Teams war
                    player_team_alive_after_tick = any(p for p in player_team if not p.is_defeated)
                    opponent_team_alive_after_tick = any(o for o in opponent_team if not o.is_defeated)
                    if not player_team_alive_after_tick or not opponent_team_alive_after_tick:
                        break # Runde beenden, da ein Team komplett besiegt ist
                    continue 

                if not actor.can_act: 
                    cli_output.print_message(f"{actor.name} kann nicht handeln (z.B. betäubt).", cli_output.Colors.YELLOW)
                    time.sleep(SIMULATION_DELAY_BETWEEN_ACTIONS)
                    continue
                
                action_decision_list: Optional[Tuple[str, List[CharacterInstance]]] = None 
                target_list_for_ai = self._get_opposing_team(actor, player_team, opponent_team)
                is_npc_actor = hasattr(actor.base_template, 'ai_strategy_id')

                if is_npc_actor:
                    ai_strategy = get_ai_strategy_instance(actor, all_participants)
                    if ai_strategy:
                        decision = ai_strategy.decide_action(target_list_for_ai)
                        if decision:
                            skill_id, target_instance = decision
                            action_decision_list = (skill_id, [target_instance]) 
                    else: 
                        logger.warning(f"Keine KI-Strategie für NPC {actor.name} gefunden/instanziiert.")
                        cli_output.print_message(f"{actor.name} (NPC) findet keine Strategie und führt keine Aktion aus.", cli_output.Colors.YELLOW)
                else: # Spieler-Charakter (im Auto-Modus)
                    if target_list_for_ai and actor.skills:
                        chosen_skill_id_player: Optional[str] = None
                        # Priorisiere offensive Skills
                        for s_id in actor.skills: 
                            skill_template = SKILL_DEFINITIONS_CLI.get(s_id)
                            if skill_template and skill_template.direct_effects and \
                               (skill_template.direct_effects.base_damage is not None or \
                                (skill_template.direct_effects.base_damage is None and True)): # True, wenn Waffenschaden
                                if actor.can_afford_skill(skill_template): 
                                    chosen_skill_id_player = s_id
                                    break
                        if not chosen_skill_id_player: # Wenn kein offensiver, nimm ersten nutzbaren
                            for s_id in actor.skills:
                                skill_template = SKILL_DEFINITIONS_CLI.get(s_id)
                                if skill_template and actor.can_afford_skill(skill_template):
                                    chosen_skill_id_player = s_id
                                    break
                        
                        if chosen_skill_id_player:
                            # Zielauswahl für Spieler-Auto-KI (z.B. zufällig oder schwächstes Ziel)
                            # Hier: zufälliges Ziel
                            if target_list_for_ai: # Sicherstellen, dass es Ziele gibt
                                chosen_target_player = random.choice(target_list_for_ai)
                                action_decision_list = (chosen_skill_id_player, [chosen_target_player])
                                skill_name_player = chosen_skill_id_player
                                skill_template_obj = SKILL_DEFINITIONS_CLI.get(chosen_skill_id_player)
                                if skill_template_obj: 
                                    skill_name_player = skill_template_obj.name
                                cli_output.print_message(f"{actor.name} (Spieler-Auto-KI) entscheidet: '{skill_name_player}' auf '{chosen_target_player.name}'.", cli_output.Colors.CYAN)
                            else:
                                cli_output.print_message(f"{actor.name} (Spieler-Auto-KI) findet keine Ziele für Skill '{chosen_skill_id_player}'.", cli_output.Colors.YELLOW)
                        else:
                            cli_output.print_message(f"{actor.name} (Spieler-Auto-KI) findet keinen nutzbaren Skill.", cli_output.Colors.YELLOW)

                if action_decision_list:
                    skill_id, targets_for_skill = action_decision_list
                    skill_name_to_display = skill_id 
                    skill_template_for_display = SKILL_DEFINITIONS_CLI.get(skill_id)
                    if skill_template_for_display:
                        skill_name_to_display = skill_template_for_display.name
                    
                    target_name_display = "N/A"
                    if targets_for_skill and targets_for_skill[0]: # Sicherstellen, dass Liste nicht leer ist
                        target_name_display = targets_for_skill[0].name

                    cli_output.display_combat_action(actor.name, skill_name_to_display, target_name_display)
                    self.combat_handler.execute_skill_action(actor, skill_id, targets_for_skill)
                else:
                    # Nur für NPCs ausgeben, wenn sie nichts tun (Spieler-Auto-KI loggt schon selbst)
                    if is_npc_actor : 
                        cli_output.print_message(f"{actor.name} führt keine Aktion aus.", cli_output.Colors.YELLOW)

                time.sleep(SIMULATION_DELAY_BETWEEN_ACTIONS)
                player_team_alive = any(p for p in player_team if not p.is_defeated)
                opponent_team_alive = any(o for o in opponent_team if not o.is_defeated)

                if not player_team_alive:
                    cli_output.display_combat_end("Gegner-Team")
                    self._award_xp(surviving_team=opponent_team, defeated_team=player_team)
                    return "Gegner-Team"
                if not opponent_team_alive:
                    cli_output.display_combat_end("Spieler-Team")
                    self._award_xp(surviving_team=player_team, defeated_team=opponent_team)
                    return "Spieler-Team"
            
            # Am Ende der Runde den Status anzeigen, wenn der Kampf noch läuft
            if any(p for p in player_team if not p.is_defeated) and any(o for o in opponent_team if not o.is_defeated):
                self._display_team_status(player_team, "Spieler-Team", True)
                self._display_team_status(opponent_team, "Gegner-Team", False)
                time.sleep(SIMULATION_DELAY_BETWEEN_TURNS)
            else: # Kampf ist nach dieser Runde vorbei
                break # Äußere while-Schleife (Runden) verlassen


        if round_number >= MAX_COMBAT_ROUNDS:
            cli_output.print_message(f"Maximale Rundenzahl ({MAX_COMBAT_ROUNDS}) erreicht. Kampf endet unentschieden.", cli_output.Colors.YELLOW)
            cli_output.display_combat_end()
            return None 
        # Der return für Sieg/Niederlage geschieht schon in der Aktionsschleife
        return None # Fallback, sollte nicht erreicht werden, wenn Sieg/Niederlage korrekt behandelt wird

    def _award_xp(self, surviving_team: List[CharacterInstance], defeated_team: List[CharacterInstance]):
        total_xp_from_defeated_team = 0
        for defeated_char in defeated_team:
            if hasattr(defeated_char.base_template, 'xp_reward'):
                total_xp_from_defeated_team += defeated_char.base_template.xp_reward
        
        if total_xp_from_defeated_team == 0 or not surviving_team: return
        actual_survivors = [s for s in surviving_team if not s.is_defeated]
        if not actual_survivors: return 

        xp_per_survivor = total_xp_from_defeated_team // len(actual_survivors)
        if xp_per_survivor == 0 and total_xp_from_defeated_team > 0: xp_per_survivor = 1

        cli_output.print_message(f"\nVerteile {total_xp_from_defeated_team} XP an {len(actual_survivors)} Überlebende.", bold=True)
        for survivor in actual_survivors:
            survivor.add_xp(xp_per_survivor) 

    def start_simulation_loop(self, 
                              num_encounters: int = 1,
                              player_team_ids: Optional[List[str]] = None,
                              opponent_setup_config: Optional[Dict[str, Any]] = None):
        if not self.character_templates or not self.opponent_templates:
            if not self._load_definitions_if_empty():
                cli_output.print_message("Simulation kann nicht gestartet werden: Definitionen fehlen und konnten nicht geladen werden.", cli_output.Colors.RED)
                return

        # Standardwerte, falls nichts übergeben wird
        if player_team_ids is None:
            player_team_ids = ["krieger"] 
        if opponent_setup_config is None:
            opponent_setup_config = {"num_opponents": 2, "level_pool": "1-2"}

        for i in range(num_encounters):
            cli_output.print_message(f"\n{'='*15} Starte Begegnung Nr. {i+1} von {num_encounters} {'='*15}", cli_output.Colors.BOLD + cli_output.Colors.LIGHT_BLUE)
            
            winner = self.run_combat_encounter(player_team_ids, opponent_setup_config)
            
            if winner:
                 cli_output.print_message(f"Sieger der Begegnung: Team '{winner}'", cli_output.Colors.LIGHT_GREEN if winner == "Spieler-Team" else cli_output.Colors.LIGHT_RED, bold=True)
            else:
                 cli_output.print_message("Begegnung endete unentschieden oder mit Fehler.", cli_output.Colors.YELLOW, bold=True)

            if i < num_encounters - 1:
                cli_output.print_message("\nNächste Begegnung startet in Kürze...", cli_output.Colors.CYAN)
                time.sleep(max(1.0, SIMULATION_DELAY_BETWEEN_TURNS)) # Kürzere Pause als zuvor
        
        cli_output.print_message("\nAlle Simulationen abgeschlossen.", cli_output.Colors.BOLD + cli_output.Colors.LIGHT_BLUE)

    def _load_definitions_if_empty(self) -> bool:
        """Versucht, Definitionen zu laden, falls sie leer sind. Gibt True bei Erfolg zurück."""
        if not self.character_templates or not self.opponent_templates:
            logger.info("Versuche, fehlende Definitionen in CLISimulationLoop nachzuladen...")
            self._load_definitions()
            if not self.character_templates or not self.opponent_templates:
                return False
        return True


if __name__ == '__main__':
    try:
        import src.utils.logging_setup
        from src.config.config import CONFIG 
        if not CONFIG: raise Exception("Konfiguration nicht geladen.")
    except Exception as e:
        print(f"FEHLER beim initialen Setup für cli_main_loop Test: {e}")
        exit(1)

    print("\n--- Teste CLI Main Loop ---")
    simulation_loop = CLISimulationLoop()
    if not simulation_loop.character_templates or not simulation_loop.opponent_templates:
        cli_output.print_message("FEHLER: Templates wurden im Konstruktor nicht geladen. Test abgebrochen.", cli_output.Colors.RED)
    else:
        cli_output.print_message(f"{len(simulation_loop.character_templates)} Charakter-Templates und "
                                 f"{len(simulation_loop.opponent_templates)} Gegner-Templates gefunden.", cli_output.Colors.CYAN)
        
        test_player_ids = ["schurke"] # Test mit Schurke
        test_opponent_config = {"num_opponents": 1, "level_pool": "1-2"} # Nur 1 Gegner
        simulation_loop.start_simulation_loop(num_encounters=1, 
                                              player_team_ids=test_player_ids, 
                                              opponent_setup_config=test_opponent_config)
        
        print("\n--- Zweiter Testlauf mit anderer Konfiguration ---")
        test_player_ids_2 = ["magier"]
        test_opponent_config_2 = {"num_opponents": 3, "level_pool": "all"} # 3 Gegner, alle Level
        simulation_loop.start_simulation_loop(num_encounters=1,
                                              player_team_ids=test_player_ids_2,
                                              opponent_setup_config=test_opponent_config_2)

    print("\n--- CLI Main Loop Test abgeschlossen ---")