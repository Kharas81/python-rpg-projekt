# src/ui/cli_main_loop.py
"""
Steuert die automatische Simulationsschleife für Kämpfe im CLI-Modus.
Nutzt die refaktorierte Kampflogik.
"""
import time
import logging
import random
from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING

from src.game_logic.entities import CharacterInstance
from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
from src.definitions.character import CharacterTemplate
from src.definitions.opponent import OpponentTemplate
from src.definitions.skill import SkillTemplate
from src.ai.ai_dispatcher import get_ai_strategy_instance # Bleibt für NPC-KI

# Importiere die neuen Kampflogik-Komponenten und Interfaces
from src.game_logic.combat.calculators import CombatCalculator
from src.game_logic.combat.effect_manager import EffectManager
from src.game_logic.combat.skill_executor import SkillExecutor
from src.game_logic.combat.handler import CombatHandler # Neuer CombatHandler
from src.game_logic.combat.interfaces import CombatRewardInterface, CombatOutputInterface

# Importiere den Adapter und das Basis-Output-Modul
from src.ui.cli_output_adapter import CliOutputAdapter
from src.ui import cli_output # Für Loop-spezifische Ausgaben

if TYPE_CHECKING:
    pass # Keine spezifischen TYPE_CHECKING-Only Imports hier nötig

logger = logging.getLogger(__name__)

SIMULATION_DELAY_BETWEEN_TURNS = 0.5  # Kann angepasst werden
SIMULATION_DELAY_BETWEEN_ACTIONS = 0.2
MAX_COMBAT_ROUNDS = 50

# Skill-Definitionen global für die einfache KI der CLISimulationLoop laden
# SkillExecutor lädt sie intern ebenfalls, aber die KI hier braucht sie für die Auswahl.
try:
    SKILL_DEFINITIONS_SIM_LOOP: Dict[str, SkillTemplate] = load_skill_templates()
except Exception as e:
    logger.critical(f"FATAL: Skill-Definitionen konnten nicht geladen werden in cli_main_loop.py: {e}", exc_info=True)
    SKILL_DEFINITIONS_SIM_LOOP = {}

# No-Operation Implementierung für das CombatRewardInterface
class NoOpRewardNotifier(CombatRewardInterface):
    def record_event_execute_kill(self, actor: CharacterInstance, target: CharacterInstance, skill: SkillTemplate) -> None: pass
    def record_event_debuff_newly_applied(self, actor: CharacterInstance, target: CharacterInstance, effect: Any, skill: SkillTemplate) -> None: pass
    def record_event_utility_skill_status_applied(self, actor: CharacterInstance, skill: SkillTemplate, applied_effect: Any) -> None: pass
    def record_event_resource_management_skill_used(self, actor: CharacterInstance, skill: SkillTemplate, resource_type_affected: str, amount_changed: int, was_beneficial_context: bool) -> None: pass
    def record_event_pass_action(self, actor: CharacterInstance, was_unnecessary: bool) -> None: pass
    def record_event_skill_cost_paid(self, actor: CharacterInstance, skill: SkillTemplate, effective_cost_paid: int, original_cost: int) -> None: pass


class CLISimulationLoop:
    def __init__(self):
        self.character_templates: Dict[str, CharacterTemplate] = {}
        self.opponent_templates: Dict[str, OpponentTemplate] = {}
        self._load_definitions() # Lädt Char/Opponent Templates

        # Instanziiere die neuen Kampflogik-Komponenten
        self.cli_output_adapter = CliOutputAdapter()
        self.noop_reward_notifier = NoOpRewardNotifier() # Für SkillExecutor

        self.calculator = CombatCalculator()
        self.effect_manager = EffectManager(output_logger=self.cli_output_adapter)
        self.skill_executor = SkillExecutor(
            calculator=self.calculator,
            effect_manager=self.effect_manager,
            output_logger=self.cli_output_adapter,
            reward_notifier=self.noop_reward_notifier # SkillExecutor braucht einen RewardNotifier
        )
        # Der neue CombatHandler nimmt SkillExecutor und EffectManager
        # und auch einen output_logger für seine eigenen, wenigen Meldungen.
        self.combat_handler = CombatHandler(
            skill_executor=self.skill_executor,
            effect_manager=self.effect_manager,
            output_logger=self.cli_output_adapter
        )
        logger.info("CLISimulationLoop mit refaktorierter Kampflogik initialisiert.")

    def _load_definitions(self): # Unverändert
        try:
            self.character_templates = load_character_templates()
            self.opponent_templates = load_opponent_templates()
            if not self.character_templates or not self.opponent_templates:
                logger.warning("Einige oder alle Charakter/Gegner-Templates konnten nicht geladen werden.")
            else:
                 logger.info("Charakter- und Gegner-Templates für die Simulation geladen.")
        except Exception as e:
            logger.critical(f"Fehler beim Laden der Definitionen für die Simulation: {e}", exc_info=True)

    def _create_player_team(self, player_ids: List[str]) -> List[CharacterInstance]: # Unverändert
        team: List[CharacterInstance] = []
        if not player_ids:
            logger.warning("Keine Spieler-IDs für Team-Erstellung übergeben. Verwende Standard-Krieger.")
            player_ids = ["krieger"]
        for i, player_id in enumerate(player_ids):
            template = self.character_templates.get(player_id)
            if template:
                name_override = template.name
                if len(player_ids) > 1 : name_override = f"{template.name} {i+1}"
                instance = CharacterInstance(base_template=template, name_override=name_override)
                team.append(instance)
            else:
                logger.error(f"Spieler-Template mit ID '{player_id}' nicht gefunden.")
        return team

    def _create_opponent_team(self, opponent_config: Dict[str, Any]) -> List[CharacterInstance]: # Weitgehend unverändert
        team: List[CharacterInstance] = []
        num_opponents = opponent_config.get("num_opponents", 1)
        level_pool_str = str(opponent_config.get("level_pool", "1-2")).lower()
        eligible_opponents: List[OpponentTemplate] = []
        min_lvl, max_lvl = -1, -1
        if level_pool_str != "all":
            try:
                parts = level_pool_str.split('-'); min_lvl = int(parts[0])
                max_lvl = int(parts[1]) if len(parts) > 1 else min_lvl
            except (ValueError, IndexError): level_pool_str = "all"; logger.warning(f"Ungültiger Level-Pool: '{level_pool_str}'. Verwende 'all'.")
        if not self.opponent_templates: return []
        for opp_template in self.opponent_templates.values():
            if level_pool_str == "all" or (hasattr(opp_template, 'level') and min_lvl <= opp_template.level <= max_lvl):
                eligible_opponents.append(opp_template)
        if not eligible_opponents:
            gob_template = self.opponent_templates.get("goblin_lv1")
            if gob_template: eligible_opponents = [gob_template]
            if not eligible_opponents: logger.error("Keine Gegner (auch Fallback) gefunden."); return []
        for i in range(num_opponents):
            if not eligible_opponents: break
            chosen_template = random.choice(eligible_opponents)
            instance = CharacterInstance(base_template=chosen_template, name_override=f"{chosen_template.name} #{i+1}")
            team.append(instance)
        return team

    def _display_team_status(self, team: List[CharacterInstance], team_name: str, is_player_team: bool): # Unverändert
        # Nutzt jetzt cli_output direkt für diese übergeordnete Darstellung
        cli_output.print_message(f"\n--- Status {team_name} ---", bold=True, color=cli_output.Colors.CYAN if is_player_team else cli_output.Colors.LIGHT_MAGENTA)
        for member in team:
            # Die display_character_status Methode ist im cli_output, nicht im Adapter,
            # da sie für die allgemeine UI-Darstellung dient, nicht nur für Kampfevents.
            cli_output.display_character_status(member, is_player_team=is_player_team)

    def _get_opposing_team(self, current_actor: CharacterInstance, player_team: List[CharacterInstance], opponent_team: List[CharacterInstance]) -> List[CharacterInstance]: # Unverändert
        if current_actor in player_team:
            return [m for m in opponent_team if not m.is_defeated]
        elif current_actor in opponent_team:
            return [m for m in player_team if not m.is_defeated]
        return []

    def _award_xp(self, surviving_team: List[CharacterInstance], defeated_team: List[CharacterInstance]): # Unverändert
        total_xp_from_defeated_team = sum(getattr(dc.base_template, 'xp_reward', 0) for dc in defeated_team)
        if total_xp_from_defeated_team == 0: return
        actual_survivors = [s for s in surviving_team if not s.is_defeated]
        if not actual_survivors: return
        xp_per_survivor = total_xp_from_defeated_team // len(actual_survivors)
        if xp_per_survivor == 0 and total_xp_from_defeated_team > 0: xp_per_survivor = 1
        cli_output.print_message(f"\nVerteile {total_xp_from_defeated_team} XP an {len(actual_survivors)} Überlebende.", bold=True)
        for survivor in actual_survivors:
            survivor.add_xp(xp_per_survivor) # add_xp in CharacterInstance müsste ggf. display_level_up über OutputInterface machen

    def run_combat_encounter(self,
                             player_team_ids: List[str],
                             opponent_setup_config: Dict[str, Any]
                             ) -> Optional[str]: # Returns winner team name or None
        if not self.character_templates or not self.opponent_templates:
            if not self._load_definitions_if_empty():
                cli_output.print_message("FEHLER: Definitionen nicht geladen. Kampf kann nicht gestartet werden.", cli_output.Colors.RED)
                return None

        player_team = self._create_player_team(player_team_ids)
        opponent_team = self._create_opponent_team(opponent_setup_config)

        if not player_team or not opponent_team:
            cli_output.print_message("FEHLER: Team-Erstellung fehlgeschlagen. Kampf abgebrochen.", cli_output.Colors.RED)
            return None
        
        all_participants = player_team + opponent_team
        round_number = 0

        cli_output.print_message("\n" + "="*10 + " KAMPF BEGINNT " + "="*10, cli_output.Colors.BOLD + cli_output.Colors.YELLOW, log_to_combat=True)
        self._display_team_status(player_team, "Spieler-Team", True)
        self._display_team_status(opponent_team, "Gegner-Team", False)
        time.sleep(SIMULATION_DELAY_BETWEEN_TURNS)

        while round_number < MAX_COMBAT_ROUNDS:
            round_number += 1
            # Höherlevelige Ausgabe für Rundenstart direkt über cli_output
            cli_output.display_combat_round_start(round_number) # Diese Methode loggt auch ins Kampflog

            # Initiative bestimmen mit der statischen Methode des neuen CombatHandlers
            initiative_order = CombatHandler.get_initiative_order(all_participants)
            
            # Ausgabe der Initiative direkt über cli_output
            initiative_names = [p.name for p in initiative_order]
            cli_output.print_message(f"Initiative: {', '.join(initiative_names)}", cli_output.Colors.CYAN, log_to_combat=True)
            time.sleep(SIMULATION_DELAY_BETWEEN_ACTIONS)

            for actor in initiative_order:
                if actor.is_defeated:
                    continue
                
                # Aktion für den Akteur bestimmen (Spieler-KI oder NPC-KI)
                chosen_skill_id: Optional[str] = None
                primary_target_instance: Optional[CharacterInstance] = None
                
                opposing_team_for_actor = self._get_opposing_team(actor, player_team, opponent_team)

                if actor in player_team: # Einfache Spieler-Auto-KI
                    # Try to find an offensive skill first
                    available_offensive_skills = [
                        s_id for s_id in actor.skills 
                        if SKILL_DEFINITIONS_SIM_LOOP.get(s_id) and
                           (SKILL_DEFINITIONS_SIM_LOOP[s_id].direct_effects and
                            (SKILL_DEFINITIONS_SIM_LOOP[s_id].direct_effects.base_damage is not None or SKILL_DEFINITIONS_SIM_LOOP[s_id].direct_effects.base_damage is None)) and # type: ignore
                           actor.can_afford_skill(SKILL_DEFINITIONS_SIM_LOOP[s_id])
                    ]
                    if available_offensive_skills and opposing_team_for_actor:
                        chosen_skill_id = random.choice(available_offensive_skills)
                        primary_target_instance = random.choice(opposing_team_for_actor)
                    else: # Fallback to first usable skill (could be self-buff or pass)
                        for s_id in actor.skills:
                            skill_tpl = SKILL_DEFINITIONS_SIM_LOOP.get(s_id)
                            if skill_tpl and actor.can_afford_skill(skill_tpl):
                                chosen_skill_id = s_id
                                if skill_tpl.target_type.startswith("ENEMY_") and opposing_team_for_actor:
                                    primary_target_instance = random.choice(opposing_team_for_actor)
                                elif skill_tpl.target_type.startswith("ALLY_") or skill_tpl.target_type == "SELF":
                                     # Simple: target self if possible, or first ally for ALLY_SINGLE
                                    primary_target_instance = actor 
                                break
                    if not chosen_skill_id: chosen_skill_id = "skill_pass_turn" # Fallback
                    
                else: # NPC-Akteur
                    ai_strategy = get_ai_strategy_instance(actor, all_participants)
                    if ai_strategy:
                        decision = ai_strategy.decide_action(opposing_team_for_actor)
                        if decision:
                            chosen_skill_id, primary_target_instance = decision
                    if not chosen_skill_id: chosen_skill_id = "skill_pass_turn" # Fallback für NPC


                # Führe die Aktionsphase des Akteurs über den neuen CombatHandler aus
                if chosen_skill_id:
                    self.combat_handler.process_actor_action_phase(
                        actor,
                        chosen_skill_id,
                        primary_target_instance,
                        all_participants
                        # Kein reward_manager_passthrough mehr nötig
                    )
                else: # Sollte nicht passieren wegen Fallback auf "skill_pass_turn"
                    logger.warning(f"{actor.name} konnte keine Aktion auswählen.")
                    if self.cli_output_adapter: # oder direkt cli_output
                        self.cli_output_adapter.log_combat_info(f"{actor.name} führt keine Aktion aus.", to_console=True)


                time.sleep(SIMULATION_DELAY_BETWEEN_ACTIONS) # Kurze Pause nach jeder Aktion

                # Kampfende-Prüfung nach jeder Aktion
                player_team_alive = any(p for p in player_team if not p.is_defeated)
                opponent_team_alive = any(o for o in opponent_team if not o.is_defeated)

                if not player_team_alive:
                    cli_output.display_combat_end("Gegner-Team") # Höherlevelige UI-Ausgabe
                    self._award_xp(surviving_team=opponent_team, defeated_team=player_team)
                    return "Gegner-Team"
                if not opponent_team_alive:
                    cli_output.display_combat_end("Spieler-Team") # Höherlevelige UI-Ausgabe
                    self._award_xp(surviving_team=player_team, defeated_team=opponent_team)
                    return "Spieler-Team"
            
            # Rundenende: Status anzeigen, wenn Kampf noch läuft
            if any(p for p in player_team if not p.is_defeated) and \
               any(o for o in opponent_team if not o.is_defeated):
                self._display_team_status(player_team, "Spieler-Team", True)
                self._display_team_status(opponent_team, "Gegner-Team", False)
                time.sleep(SIMULATION_DELAY_BETWEEN_TURNS)
            else:
                break # Kampf ist vorbei

        if round_number >= MAX_COMBAT_ROUNDS:
            cli_output.print_message(f"Max. Rundenzahl ({MAX_COMBAT_ROUNDS}) erreicht. Unentschieden.", cli_output.Colors.YELLOW, bold=True, log_to_combat=True)
            cli_output.display_combat_end() # Unentschieden
            return None
        
        return None # Sollte nur bei Unentschieden nach Rundenlimit erreicht werden

    def start_simulation_loop(self,
                              num_encounters: int = 1,
                              player_team_ids: Optional[List[str]] = None,
                              opponent_setup_config: Optional[Dict[str, Any]] = None): # Weitgehend unverändert
        if not self._load_definitions_if_empty():
            cli_output.print_message("Simulation kann nicht gestartet werden: Definitionen fehlen.", cli_output.Colors.RED)
            return
        if player_team_ids is None: player_team_ids = ["krieger"]
        if opponent_setup_config is None: opponent_setup_config = {"num_opponents": 2, "level_pool": "1-2"}

        for i in range(num_encounters):
            cli_output.print_message(f"\n{'='*15} Starte Begegnung Nr. {i+1} von {num_encounters} {'='*15}", cli_output.Colors.BOLD + cli_output.Colors.LIGHT_BLUE, log_to_combat=True)
            winner = self.run_combat_encounter(player_team_ids, opponent_setup_config)
            if winner:
                 cli_output.print_message(f"Sieger der Begegnung: Team '{winner}'", cli_output.Colors.LIGHT_GREEN if winner == "Spieler-Team" else cli_output.Colors.LIGHT_RED, bold=True, log_to_combat=True)
            else:
                 cli_output.print_message("Begegnung unentschieden oder mit Fehler beendet.", cli_output.Colors.YELLOW, bold=True, log_to_combat=True)
            if i < num_encounters - 1:
                cli_output.print_message("\nNächste Begegnung startet...", cli_output.Colors.CYAN)
                time.sleep(max(1.0, SIMULATION_DELAY_BETWEEN_TURNS))
        cli_output.print_message("\nAlle Simulationen abgeschlossen.", cli_output.Colors.BOLD + cli_output.Colors.LIGHT_BLUE)

    def _load_definitions_if_empty(self) -> bool: # Unverändert
        if not self.character_templates or not self.opponent_templates:
            logger.info("Versuche, fehlende Definitionen in CLISimulationLoop nachzuladen...")
            self._load_definitions()
            return bool(self.character_templates and self.opponent_templates)
        return True

if __name__ == '__main__':
    # Der __main__ Block bleibt für direktes Testen der Loop, nutzt die neuen Komponenten.
    try:
        from src.utils import logging_setup # Sicherstellen, dass Logging konfiguriert ist
        from src.config.config import CONFIG # Für globale Settings, die ggf. indirekt genutzt werden
        if not CONFIG: raise Exception("Globale Konfiguration nicht geladen.")
        # Logging-Setup ggf. hier explizit aufrufen, wenn nicht schon von main.py geschehen
        # logging_setup.setup_logging()
    except Exception as e_main:
        print(f"FEHLER beim initialen Setup für cli_main_loop Test: {e_main}")
        exit(1)

    print("\n--- Teste CLISimulationLoop mit refaktorierter Kampflogik ---")
    sim_loop = CLISimulationLoop()
    if not sim_loop.character_templates or not sim_loop.opponent_templates:
        cli_output.print_message("FEHLER: Templates wurden im Konstruktor nicht geladen.", cli_output.Colors.RED)
    else:
        test_player_ids = ["krieger"]
        test_opponent_config = {"num_opponents": 1, "ids": ["goblin_lv1"]}
        sim_loop.start_simulation_loop(num_encounters=1,
                                       player_team_ids=test_player_ids,
                                       opponent_setup_config=test_opponent_config)
    print("\n--- CLISimulationLoop Test abgeschlossen ---")