# src/main.py
"""
Haupteinstiegspunkt für das RPG-Projekt.
Verarbeitet Kommandozeilenargumente oder startet ein interaktives Menü.
"""
import argparse
import logging
import sys 
import os 
import json # Für das Anzeigen von JSON-Inhalten (in Callbacks)
import json5 # Für das Laden von RL-Setup-Dateien (in Callbacks)
from typing import Optional, Dict, List, Any, Callable # Callable wird hier nicht mehr direkt gebraucht, aber schadet nicht

# Logging-Setup so früh wie möglich
try:
    from src.utils import logging_setup 
except ImportError as e:
    print(f"FATAL_ERROR: src.utils.logging_setup konnte nicht importiert werden: {e}. Abbruch.")
    sys.exit(1) 

logger = logging.getLogger(__name__) 

# Globale Konfiguration und andere wichtige Imports
_CONFIG = None
_UserConfigManager_CLASS = None # Umbenannt, um klarzustellen, dass es die Klasse ist
_CLISimulationLoop_CLASS = None
_cli_menu_MODULE = None
_cli_output_MODULE = None
_load_character_templates_FUNC = None
# _CharacterTemplate_CLASS = None # Wird in main.py nicht direkt benötigt
_main_menu_callbacks_MODULE = None 

try:
    from src.config.config import CONFIG as _CONFIG_MAIN; _CONFIG = _CONFIG_MAIN
    from src.config.user_config_manager import UserConfigManager as _UserConfigManager_CLASS_MAIN; _UserConfigManager_CLASS = _UserConfigManager_CLASS_MAIN
    from src.ui.cli_main_loop import CLISimulationLoop as _CLISimulationLoop_CLASS_MAIN; _CLISimulationLoop_CLASS = _CLISimulationLoop_CLASS_MAIN
    from src.ui import cli_menu as _cli_menu_MODULE_MAIN; _cli_menu_MODULE = _cli_menu_MODULE_MAIN
    from src.ui import cli_output as _cli_output_MODULE_MAIN; _cli_output_MODULE = _cli_output_MODULE_MAIN
    from src.definitions.loader import load_character_templates as _load_character_templates_FUNC_MAIN; _load_character_templates_FUNC = _load_character_templates_FUNC_MAIN
    # from src.definitions.character import CharacterTemplate as _CharacterTemplate_CLASS_MAIN; _CharacterTemplate_CLASS = _CharacterTemplate_CLASS_MAIN
    from src.ui import main_menu_callbacks as _main_menu_callbacks_MODULE_MAIN; _main_menu_callbacks_MODULE = _main_menu_callbacks_MODULE_MAIN
except ImportError as e:
    logger.critical(f"FATAL: Wichtige Module konnten nicht importiert werden: {e}. Abbruch.", exc_info=True)
    sys.exit(1) 

# Globale Instanz des UserConfigManagers
user_config_manager_instance: Optional[Any] = None
if _UserConfigManager_CLASS:
    user_config_manager_instance = _UserConfigManager_CLASS()
    if _main_menu_callbacks_MODULE and hasattr(_main_menu_callbacks_MODULE, 'initialize_menu_callbacks'):
        _main_menu_callbacks_MODULE.initialize_menu_callbacks(user_config_manager_instance)
else:
    logger.critical("UserConfigManager Klasse konnte nicht geladen werden. Programm wird beendet.")
    sys.exit(1)


def main_menu_loop():
    """Hauptmenüschleife, die Callbacks aus dem main_menu_callbacks Modul verwendet."""
    if not _cli_menu_MODULE or not _cli_output_MODULE or not logging_setup or \
       not user_config_manager_instance or not _main_menu_callbacks_MODULE:
        print("FEHLER: UI-, Logging-, UserConfig- oder Callback-Module nicht verfügbar für Hauptmenü.")
        return

    # Loglevel beim Start aus user_preferences setzen
    initial_pref_loglevel = user_config_manager_instance.get_preference("preferred_loglevel", "INFO")
    if not logging_setup.set_global_log_level(initial_pref_loglevel):
        logger.warning(f"Konnte initialen Loglevel '{initial_pref_loglevel}' aus user_preferences nicht setzen.")
    else:
        logger.info(f"Initialer Loglevel aus Benutzerpräferenzen auf '{initial_pref_loglevel}' gesetzt.")

    # Stelle sicher, dass die notwendigen Klassen für die Callbacks vorhanden sind
    if not _CLISimulationLoop_CLASS or not _load_character_templates_FUNC:
        _cli_output_MODULE.print_message("Fehler: Kernkomponenten für Menüaktionen fehlen (CLISimulationLoop oder Template Loader).", _cli_output_MODULE.Colors.RED)
        return

    main_options = [
        ("Automatische Simulation starten", 
         lambda: _main_menu_callbacks_MODULE.start_auto_simulation_with_user_settings_callback(user_config_manager_instance, _CLISimulationLoop_CLASS)),
        ("Auto-Simulationseinstellungen anpassen", 
         lambda: _main_menu_callbacks_MODULE.configure_simulation_settings_menu_callback(user_config_manager_instance, _load_character_templates_FUNC)),
        ("RL Training & Evaluierung", 
         lambda: _main_menu_callbacks_MODULE.configure_rl_menu_callback(user_config_manager_instance)), 
        ("Ausgabedetailgrad (Loglevel) ändern", 
         lambda: _main_menu_callbacks_MODULE.change_log_level_menu_callback(user_config_manager_instance)),
        ("Manuelle Simulation starten (Platzhalter)", 
         _main_menu_callbacks_MODULE.run_manual_mode_placeholder_callback),
    ]

    while True:
        result = _cli_menu_MODULE.display_menu("Hauptmenü", main_options)
        if result == "exit_menu" or result == "error": 
            if _cli_output_MODULE: _cli_output_MODULE.print_message("Programm wird beendet.", _cli_output_MODULE.Colors.BOLD)
            else: print("Programm wird beendet.")
            break

def main():
    # Kritische Modulprüfung
    critical_components = {
        "CONFIG": _CONFIG, "UserConfigManager_CLASS": _UserConfigManager_CLASS, 
        "CLISimulationLoop_CLASS": _CLISimulationLoop_CLASS, "cli_menu_MODULE": _cli_menu_MODULE, 
        "cli_output_MODULE": _cli_output_MODULE, "logging_setup_MODULE": logging_setup, # logging_setup ist ein Modul
        "load_character_templates_FUNC": _load_character_templates_FUNC, 
        "main_menu_callbacks_MODULE": _main_menu_callbacks_MODULE
    }
    for name, component in critical_components.items():
        if component is None:
            # Logger ist hier möglicherweise noch nicht voll initialisiert, daher print
            print(f"FATAL_ERROR: Kritische Komponente '{name}' konnte nicht geladen werden. Programm wird beendet.")
            sys.exit(1)
    
    # UserConfigManager Instanz wurde bereits global erstellt und geprüft.
    if user_config_manager_instance is None:
        print("FATAL_ERROR: UserConfigManager Instanz konnte nicht erstellt werden. Programm wird beendet.")
        sys.exit(1)

    # Standardeinstellungen für CLI-Argumente aus user_preferences holen
    default_sim_settings = user_config_manager_instance.get_preference("simulation_settings", {})
    default_opp_config = default_sim_settings.get("opponent_config", {})
    default_loglevel = user_config_manager_instance.get_preference("preferred_loglevel", "INFO")
    default_rl_config_file = user_config_manager_instance.get_preference("last_selected_rl_setup_file")


    parser = argparse.ArgumentParser(description="Textbasiertes RPG-Projekt.", add_help=False)
    parser.add_argument("--mode", type=str, choices=["manual", "auto", "train_rl", "eval_rl"], help="Direkter Start eines Betriebsmodus.")
    parser.add_argument("--encounters", type=int, default=default_sim_settings.get('num_encounters', 1), help=f"Anzahl Begegnungen für Auto-Modus.")
    parser.add_argument("--player", type=str, default=default_sim_settings.get('player_hero_id', 'krieger'), help=f"ID des Spieler-Helden.")
    parser.add_argument("--opponents", type=int, default=default_opp_config.get('num_opponents', 2), help=f"Anzahl Gegner.")
    parser.add_argument("--opplevelpool", type=str, default=default_opp_config.get('level_pool', '1-2'), help=f"Gegner Level-Pool.")
    parser.add_argument("--loglevel", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default=default_loglevel, help="Setzt globalen Loglevel.")
    parser.add_argument("--rl_config", type=str, default=default_rl_config_file, help="Pfad zur RL-Setup-Datei.")
    parser.add_argument('-h', '--help-cli', action='help', default=argparse.SUPPRESS, help='Zeige CLI-Hilfe und beende.')
    
    args = None
    if len(sys.argv) > 1 : 
        try: args = parser.parse_args()
        except SystemExit: return 
    else: 
        args = parser.parse_args([]) 

    # Loglevel setzen (CLI überschreibt User-Präferenz, die den Default aus settings.json5 überschreibt)
    # logging_setup.set_global_log_level wird mit dem Default aus argparse (der aus user_prefs kommt) aufgerufen,
    # oder mit dem expliziten CLI-Wert.
    if logging_setup.set_global_log_level(args.loglevel): # args.loglevel hat immer einen Wert
         logger.info(f"Loglevel auf {args.loglevel} gesetzt.")
         # Wenn der Loglevel explizit via CLI geändert wurde und nicht dem Default aus Prefs entspricht, speichere ihn
         if any(arg_name for arg_name in ["--loglevel"] if arg_name in sys.argv) and \
            args.loglevel.upper() != user_config_manager_instance.get_preference("preferred_loglevel", "INFO").upper():
             user_config_manager_instance.set_preference("preferred_loglevel", args.loglevel.upper())
    else:
         logger.warning(f"Ungültiger Loglevel: {args.loglevel}. Aktueller Level bleibt.")
    
    effective_loglevel = logging.getLevelName(logging.getLogger().getEffectiveLevel())
    logger.info(f"RPG-Projekt gestartet. Effektiver Loglevel: {effective_loglevel}")

    if args.mode:
        logger.info(f"Direkter Modusstart via CLI: {args.mode}")
        
        # Temporäre Simulationseinstellungen für diesen CLI-Lauf
        # Diese werden NICHT in user_preferences.json5 gespeichert, es sei denn, wir fügen diese Logik hinzu.
        cli_sim_settings = {
            "num_encounters": args.encounters,
            "player_hero_id": args.player,
            "opponent_config": {
                "num_opponents": args.opponents,
                "level_pool": args.opplevelpool
            }
        }
        # Aktualisiere die globale Variable _current_selected_rl_setup_file für den CLI-Lauf
        global _current_selected_rl_setup_file_callbacks # Zugriff auf die Variable in main_menu_callbacks
        if args.rl_config:
            # Wenn Callbacks direkt auf eine globale Var zugreifen:
            if _main_menu_callbacks_MODULE:
                 _main_menu_callbacks_MODULE._current_selected_rl_setup_file_callbacks = args.rl_config
            # Optional: Auch in user_prefs speichern, wenn gewünscht
            # user_config_manager_instance.set_preference("last_selected_rl_setup_file", args.rl_config)


        if args.mode == "manual": 
            if _main_menu_callbacks_MODULE: _main_menu_callbacks_MODULE.run_manual_mode_placeholder_callback()
        elif args.mode == "auto":
            # Für den direkten CLI-Aufruf müssen wir die Einstellungen irgendwie an start_auto_simulation übergeben.
            # Die einfachste Methode ist, wenn start_auto_simulation_with_user_settings_callback
            # die CLI-Args berücksichtigt, wenn es von hier gerufen wird, oder wir eine separate Funktion haben.
            # Aktuell liest es aus user_config_manager. Um CLI-Args zu nutzen, müssen wir
            # die user_config_manager-Werte temporär überschreiben oder die Parameter direkt übergeben.
            
            # Temporäres Überschreiben der user_config für diesen Lauf:
            original_sim_settings = user_config_manager_instance.get_preference("simulation_settings")
            user_config_manager_instance.preferences["simulation_settings"] = cli_sim_settings # Direkt im Dict ändern
            
            if _main_menu_callbacks_MODULE: _main_menu_callbacks_MODULE.start_auto_simulation_with_user_settings_callback(user_config_manager_instance, _CLISimulationLoop_CLASS)
            
            user_config_manager_instance.preferences["simulation_settings"] = original_sim_settings # Zurücksetzen
            logger.info("Automatischer Simulationsmodus (via CLI) beendet.")

        elif args.mode == "train_rl":
            # Der Callback würde auf _current_selected_rl_setup_file_callbacks zugreifen
            if _main_menu_callbacks_MODULE and hasattr(_main_menu_callbacks_MODULE, 'start_rl_training_placeholder'):
                 # Die Callback-Funktion im RL-Menü muss den globalen _current_selected_rl_setup_file_callbacks verwenden
                 _main_menu_callbacks_MODULE.configure_rl_menu_callback(user_config_manager_instance) # Öffnet Menü, um dann Training zu starten
                 # Besser: Direkter Aufruf, wenn rl_config gegeben ist
                 if args.rl_config and _main_menu_callbacks_MODULE._current_selected_rl_setup_file_callbacks:
                     logger.info(f"Starte RL-Training (Platzhalter) mit Konfig: {args.rl_config}")
                     # _main_menu_callbacks_MODULE.start_rl_training_placeholder() # Diese Funktion müsste den Pfad nehmen
                 elif not args.rl_config:
                     logger.error("--rl_config ist erforderlich für --mode train_rl.")
            else:
                 logger.error("RL-Trainings-Callback nicht gefunden.")

        elif args.mode == "eval_rl":
            if _main_menu_callbacks_MODULE and hasattr(_main_menu_callbacks_MODULE, 'start_rl_evaluation_placeholder'):
                 if args.rl_config and _main_menu_callbacks_MODULE._current_selected_rl_setup_file_callbacks:
                     logger.info(f"Starte RL-Evaluierung (Platzhalter) mit Konfig: {args.rl_config}")
                 elif not args.rl_config:
                     logger.error("--rl_config ist erforderlich für --mode eval_rl.")
            else:
                 logger.error("RL-Evaluierungs-Callback nicht gefunden.")
    else: 
        if not (len(sys.argv) > 1 and any(arg in sys.argv for arg in ['-h', '--help-cli'])):
             logger.info("Kein Modus via CLI angegeben oder nur Hilfe angefordert. Starte Hauptmenü.")
             main_menu_loop()

if __name__ == "__main__":
    main()