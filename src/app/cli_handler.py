# src/app/cli_handler.py
# V2: Aktualisiert den Menüaufruf für die Welt-Simulation.
import argparse
import logging
import sys
from typing import Optional, Any

from src.utils import logging_setup
from src.config.user_config_manager import UserConfigManager
from src.ui import cli_menu, cli_output, main_menu_callbacks
from src.app import runners
from src.ui.cli_main_loop import CLISimulationLoop
from src.definitions.loader import load_character_templates

logger = logging.getLogger(__name__)

def main_menu_loop(ucm: UserConfigManager):
    """Die Hauptmenü-Schleife der Anwendung."""
    if not all([cli_menu, cli_output, logging_setup, ucm, main_menu_callbacks]):
        print("FEHLER: Kernmodule für Hauptmenü nicht verfügbar.")
        return

    if hasattr(logging_setup, 'setup_logging'):
        logging_setup.setup_logging(force_reconfigure=True)
    
    main_options = [
        ("Welt-Simulation starten (mit Heldenauswahl)", main_menu_callbacks.start_world_simulation_with_hero_selection),
        ("Auto-Kampf-Simulation starten (nur Kampf)", lambda: runners.run_auto_combat_simulation(ucm)),
        ("Auto-Kampf-Einstellungen anpassen", lambda: main_menu_callbacks.configure_simulation_settings_menu_callback(ucm, load_character_templates)),
        ("RL Training & Evaluierung", lambda: main_menu_callbacks.configure_rl_menu_callback(ucm)),
        ("Entwickler-Tools & Tests", main_menu_callbacks.dev_tools_menu_callback),
        ("Detaillierte Logging-Einstellungen", lambda: main_menu_callbacks.configure_granular_logging_menu_callback(ucm)),
    ]
    
    while True:
        result = cli_menu.display_menu("Hauptmenü", main_options)
        if result == "exit_menu" or result == "error":
            cli_output.print_message("Programm wird beendet.", cli_output.Colors.BOLD)
            break

def handle_cli_entrypoint():
    """Der Haupteinstiegspunkt, der alles initialisiert und steuert."""
    user_config_manager_instance = UserConfigManager()
    logging_setup.set_user_config_manager_for_logging(user_config_manager_instance)
    logging_setup.setup_logging()
    main_menu_callbacks.initialize_menu_callbacks(user_config_manager_instance)
    
    parser = argparse.ArgumentParser(description="Textbasiertes RPG-Projekt.", add_help=False)
    parser.add_argument("--mode", type=str, choices=["auto", "train_rl", "eval_rl"], default=None, help="Direkter Start eines Modus ohne interaktives Menü.")
    default_sim_settings = user_config_manager_instance.get_preference("simulation_settings", {})
    parser.add_argument("--encounters", type=int, default=default_sim_settings.get('num_encounters', 1), help="Anzahl Begegnungen für Auto-Modus.")
    parser.add_argument("--player", type=str, default=default_sim_settings.get('player_hero_id', 'krieger'), help="ID des Spieler-Helden für Auto-Modus.")
    parser.add_argument('-h', '--help-cli', action='help', default=argparse.SUPPRESS, help='Zeige diese CLI-Hilfe und beende.')
    args = parser.parse_args()

    if args.mode:
        logger.info(f"Direkter Modusstart via CLI: {args.mode}")
        if args.mode == "auto":
            runners.run_auto_combat_simulation(user_config_manager_instance)
        elif args.mode == "train_rl":
            logger.warning("Direkter RL-Trainings-Start via CLI noch nicht implementiert.")
            pass
        elif args.mode == "eval_rl":
            logger.warning("Direkter RL-Evaluierungs-Start via CLI noch nicht implementiert.")
            pass
    else:
        logger.info("Kein direkter Modus via CLI angegeben. Starte interaktives Hauptmenü.")
        main_menu_loop(user_config_manager_instance)