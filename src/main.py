# src/main.py
"""
Haupteinstiegspunkt für das RPG-Projekt.
Verarbeitet Kommandozeilenargumente oder startet ein interaktives Menü.
"""
import argparse
import logging
import sys 
from typing import Optional, Dict, List, Any, Callable # KORREKTUR: Notwendige Typ-Hinweise importieren

try:
    from src.utils import logging_setup 
except ImportError as e:
    print(f"FEHLER beim Import von logging_setup: {e}. Standard-Python-Logging wird verwendet.")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__) 

try:
    from src.config.config import CONFIG
    from src.ui.cli_main_loop import CLISimulationLoop
    from src.ui import cli_menu 
    from src.ui import cli_output 
    from src.definitions.loader import load_character_templates, load_opponent_templates 
    from src.definitions.character import CharacterTemplate 
    from src.definitions.opponent import OpponentTemplate 

except ImportError as e:
    logger.critical(f"FATAL: Wichtige Module konnten nicht importiert werden: {e}. Abbruch.", exc_info=True)
    CONFIG = None 
    CLISimulationLoop = None
    cli_menu = None
    cli_output = None
    sys.exit(1) 

current_simulation_settings = {
    "num_encounters": 1,
    "player_hero_id": "krieger", 
    "opponent_config": { 
        "num_opponents": 2,
        "level_pool": "1-2" 
    }
}

_character_template_cache: Optional[Dict[str, CharacterTemplate]] = None
_opponent_template_cache: Optional[Dict[str, OpponentTemplate]] = None

def get_cached_character_templates() -> Dict[str, CharacterTemplate]:
    global _character_template_cache
    if _character_template_cache is None:
        try:
            _character_template_cache = load_character_templates()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Charakter-Templates für Menü: {e}")
            _character_template_cache = {} 
    return _character_template_cache

def get_cached_opponent_templates() -> Dict[str, OpponentTemplate]:
    global _opponent_template_cache
    if _opponent_template_cache is None:
        try:
            _opponent_template_cache = load_opponent_templates()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Gegner-Templates für Menü: {e}")
            _opponent_template_cache = {} 
    return _opponent_template_cache


def start_auto_simulation_with_current_settings():
    if not CLISimulationLoop or not CONFIG:
        if cli_output: cli_output.print_message("Fehler: Simulationskomponenten nicht initialisiert.", cli_output.Colors.RED)
        else: print("FEHLER: Simulationskomponenten nicht initialisiert.")
        return

    if cli_output:
        cli_output.print_message("\nStarte automatische Simulation mit folgenden Einstellungen:", cli_output.Colors.CYAN)
        cli_output.print_message(f"  Anzahl Begegnungen: {current_simulation_settings['num_encounters']}")
        cli_output.print_message(f"  Spieler-Held: {current_simulation_settings['player_hero_id']}")
        cli_output.print_message(f"  Gegner-Anzahl: {current_simulation_settings['opponent_config']['num_opponents']}")
        cli_output.print_message(f"  Gegner-Level-Pool: {current_simulation_settings['opponent_config']['level_pool']}")
    
    try:
        simulation = CLISimulationLoop()
        simulation.start_simulation_loop(
            num_encounters=current_simulation_settings['num_encounters'],
            player_team_ids=[current_simulation_settings['player_hero_id']],
            opponent_setup_config=current_simulation_settings['opponent_config']
        )
    except Exception as e:
        logger.error(f"Fehler während der CLI-Simulation (Menüstart): {e}", exc_info=True)
    logger.info("Automatische Simulation (Menüstart) beendet.")


def configure_simulation_settings():
    if not cli_menu or not CONFIG or not cli_output: return "exit_menu"

    char_templates = get_cached_character_templates()
    available_heroes = list(char_templates.keys())
    if not available_heroes: 
        available_heroes = ["krieger", "magier", "schurke", "kleriker"] 
        cli_output.print_message("WARNUNG: Konnte Charakter-Templates nicht laden, verwende Standardheldenliste.", cli_output.Colors.YELLOW)


    def change_encounters():
        new_val = cli_menu.get_user_input_int(
            f"Anzahl Begegnungen (1-100, Aktuell: {current_simulation_settings['num_encounters']}):", 1, 100)
        if new_val is not None: 
            current_simulation_settings['num_encounters'] = new_val
            cli_output.print_message(f"Anzahl Begegnungen auf {new_val} gesetzt.", cli_output.Colors.LIGHT_GREEN)

    def change_hero():
        if not available_heroes:
            cli_output.print_message("Keine Helden-Templates zum Auswählen verfügbar.", cli_output.Colors.RED)
            return

        hero_options = []
        for i, hero_id in enumerate(available_heroes):
            hero_name = hero_id # Fallback-Name
            template = char_templates.get(hero_id)
            if template and hasattr(template, 'name'):
                 hero_name = template.name
            hero_options.append((f"{hero_id} ({hero_name})", lambda h_id=hero_id: h_id)) # Callback gibt ID zurück
        
        # display_menu gibt die hero_id zurück (den zweiten Teil des Tupels, wenn Callback eine ID ist)
        chosen_hero_id_from_menu = cli_menu.display_menu(
            f"Spieler-Held auswählen (Aktuell: {current_simulation_settings['player_hero_id']})", 
            hero_options
        )
        
        # Überprüfen, ob die zurückgegebene ID gültig ist
        if chosen_hero_id_from_menu and chosen_hero_id_from_menu != "exit_menu" and chosen_hero_id_from_menu in available_heroes:
            current_simulation_settings['player_hero_id'] = chosen_hero_id_from_menu
            cli_output.print_message(f"Spieler-Held auf '{chosen_hero_id_from_menu}' gesetzt.", cli_output.Colors.LIGHT_GREEN)
        elif chosen_hero_id_from_menu == "exit_menu":
            pass 
        elif chosen_hero_id_from_menu is not None: # Ungültige Zahl oder Auswahl wurde von display_menu nicht als "error" behandelt
             cli_output.print_message(f"Ungültige Heldenauswahl: {chosen_hero_id_from_menu}.", cli_output.Colors.RED)


    def change_opponent_count():
        new_val = cli_menu.get_user_input_int(
            f"Anzahl Gegner pro Begegnung (1-5, Aktuell: {current_simulation_settings['opponent_config']['num_opponents']}):", 1, 5)
        if new_val is not None: 
            current_simulation_settings['opponent_config']['num_opponents'] = new_val
            cli_output.print_message(f"Anzahl Gegner auf {new_val} gesetzt.", cli_output.Colors.LIGHT_GREEN)
    
    def change_opponent_pool():
        pools = ["1-2", "all"] # Beispiel-Pools, könnte man dynamischer machen
        
        pool_options = []
        for pool_id in pools:
            pool_options.append((f"Level-Pool: {pool_id}", lambda p_id=pool_id: p_id)) # Callback gibt ID zurück
            
        chosen_pool_id_from_menu = cli_menu.display_menu(
            f"Gegner Level-Pool (Aktuell: {current_simulation_settings['opponent_config']['level_pool']})", 
            pool_options
        )

        if chosen_pool_id_from_menu and chosen_pool_id_from_menu != "exit_menu" and chosen_pool_id_from_menu in pools:
            current_simulation_settings['opponent_config']['level_pool'] = chosen_pool_id_from_menu
            cli_output.print_message(f"Gegner Level-Pool auf '{chosen_pool_id_from_menu}' gesetzt.", cli_output.Colors.LIGHT_GREEN)
        elif chosen_pool_id_from_menu == "exit_menu":
            pass
        elif chosen_pool_id_from_menu is not None:
             cli_output.print_message(f"Ungültige Pool-Auswahl: {chosen_pool_id_from_menu}.", cli_output.Colors.RED)

    while True:
        options = [
            (f"Anzahl Begegnungen ändern (Aktuell: {current_simulation_settings['num_encounters']})", change_encounters),
            (f"Spieler-Held auswählen (Aktuell: {current_simulation_settings['player_hero_id']})", change_hero),
            (f"Anzahl Gegner ändern (Aktuell: {current_simulation_settings['opponent_config']['num_opponents']})", change_opponent_count),
            (f"Gegner Level-Pool ändern (Aktuell: {current_simulation_settings['opponent_config']['level_pool']})", change_opponent_pool),
        ]
        choice = cli_menu.display_menu("Simulationseinstellungen", options)
        if choice == "exit_menu" or choice == "error": 
            break 
    return None

def change_log_level_menu():
    if not cli_menu or not logging_setup or not cli_output: return "exit_menu"
    
    def get_current_level_display_options():
        current_level_val = logging.getLogger().getEffectiveLevel()
        current_level_name = logging.getLevelName(current_level_val)
        
        options_with_callbacks = [
            ("DEBUG (Sehr detailliert)", lambda: logging_setup.set_global_log_level("DEBUG")),
            ("INFO (Standard)", lambda: logging_setup.set_global_log_level("INFO")),
            ("WARNING (Nur Warnungen und Fehler)", lambda: logging_setup.set_global_log_level("WARNING")),
            ("ERROR (Nur Fehler)", lambda: logging_setup.set_global_log_level("ERROR")),
        ]
        display_options = []
        for desc, func in options_with_callbacks:
            level_in_desc = desc.split(" ")[0] 
            prefix = ">> " if level_in_desc == current_level_name else "   "
            display_options.append((f"{prefix}{desc}", func))
        return display_options, current_level_name

    while True:
        display_opts, current_lvl_name = get_current_level_display_options()
        # display_menu führt den Callback direkt aus und gibt dessen Ergebnis zurück
        result_of_callback = cli_menu.display_menu(f"Ausgabedetailgrad ändern (Aktuell: {current_lvl_name})", display_opts)
        
        if result_of_callback == "exit_menu" or result_of_callback == "error":
            break
        # Wenn eine Option gewählt wurde, wurde der Loglevel geändert. 
        # Wir brauchen hier keine weitere Aktion basierend auf result_of_callback,
        # es sei denn, die Callbacks würden etwas anderes als None zurückgeben.
        # Um das Menü nach einer Auswahl neu zu zeichnen (mit aktualisiertem "Aktuell:"), bleibt die Schleife.
        # Wenn der Benutzer "0" wählt, kommt "exit_menu" und die Schleife bricht ab.
    return None 


def run_manual_mode_placeholder():
    logger.info("Starte manuellen Spielmodus (Platzhalter)...")
    if cli_output: cli_output.print_message("\n--- Manueller Modus (Platzhalter) ---", cli_output.Colors.YELLOW)
    if cli_output: cli_output.print_message("Diese Funktion ist noch nicht implementiert.", cli_output.Colors.YELLOW)

def run_rl_training_placeholder():
    logger.info("Starte RL-Training (Platzhalter)...")
    if cli_output: cli_output.print_message("\n--- RL-Training (Platzhalter) ---", cli_output.Colors.YELLOW)
    if cli_output: cli_output.print_message("Diese Funktion ist noch nicht implementiert.", cli_output.Colors.YELLOW)


def main_menu():
    if not cli_menu or not cli_output:
        print("FEHLER: Menü- oder Ausgabemodule nicht verfügbar.")
        return

    main_options = [
        ("Automatische Simulation starten", start_auto_simulation_with_current_settings),
        ("Simulationseinstellungen anpassen", configure_simulation_settings),
        ("Ausgabedetailgrad (Loglevel) ändern", change_log_level_menu),
        ("Manuelle Simulation starten (Platzhalter)", run_manual_mode_placeholder),
        ("RL-Training starten (Platzhalter)", run_rl_training_placeholder)
    ]

    while True:
        result = cli_menu.display_menu("Hauptmenü", main_options)
        if result == "exit_menu" or result == "error": 
            if cli_output: cli_output.print_message("Programm wird beendet.", cli_output.Colors.BOLD)
            else: print("Programm wird beendet.")
            break

def main():
    if CONFIG is None or CLISimulationLoop is None or cli_menu is None or cli_output is None or logging_setup is None:
        print("Kritische Fehler beim Initialisieren der Anwendung. Bitte Logs prüfen.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Textbasiertes RPG-Projekt.", add_help=False)
    parser.add_argument(
        "--mode", type=str, choices=["manual", "auto", "train_rl"],
        help="Direkter Start eines Betriebsmodus (überspringt das Menü)."
    )
    parser.add_argument(
        "--encounters", type=int, 
        help=f"Anzahl Begegnungen für Auto-Modus (Standard: {current_simulation_settings['num_encounters']})."
    )
    parser.add_argument(
        "--player", type=str,
        help=f"ID des Spieler-Helden für Auto-Modus (Standard: {current_simulation_settings['player_hero_id']})."
    )
    parser.add_argument(
        "--opponents", type=int,
        help=f"Anzahl Gegner für Auto-Modus (Standard: {current_simulation_settings['opponent_config']['num_opponents']})."
    )
    parser.add_argument(
        "--opplevelpool", type=str,
        help=f"Gegner Level-Pool für Auto-Modus (z.B. '1-2', 'all'; Standard: {current_simulation_settings['opponent_config']['level_pool']})."
    )
    parser.add_argument(
        "--loglevel", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Setzt den globalen Loglevel direkt (überspringt das Menü)."
    )
    parser.add_argument(
        '-h', '--help-cli', action='help', default=argparse.SUPPRESS, 
        help='Zeige diese Kommandozeilen-Hilfenachricht und beende.'
    )
    
    args = None
    # Parsen, nur wenn Argumente vorhanden sind, um Konflikte mit Menü zu vermeiden, falls keine Argumente da sind
    # Aber --help-cli muss immer funktionieren.
    if len(sys.argv) > 1:
        try:
            args = parser.parse_args()
        except SystemExit: 
            return # Beenden, wenn argparse wegen --help-cli beendet

    # Loglevel aus Argumenten setzen, falls vorhanden
    if args and args.loglevel:
        if logging_setup.set_global_log_level(args.loglevel):
             logger.info(f"Loglevel via CLI auf {args.loglevel} gesetzt.")
        else:
             logger.warning(f"Ungültiger Loglevel via CLI: {args.loglevel}.")
    
    effective_loglevel = logging.getLevelName(logging.getLogger().getEffectiveLevel())
    logger.info(f"RPG-Projekt gestartet. Effektiver Loglevel: {effective_loglevel}")

    # Modus aus Argumenten ausführen, falls vorhanden
    if args and args.mode:
        logger.info(f"Direkter Modusstart via CLI: {args.mode}")
        
        if args.encounters is not None: current_simulation_settings['num_encounters'] = args.encounters
        if args.player is not None: current_simulation_settings['player_hero_id'] = args.player
        if args.opponents is not None: current_simulation_settings['opponent_config']['num_opponents'] = args.opponents
        if args.opplevelpool is not None: current_simulation_settings['opponent_config']['level_pool'] = args.opplevelpool

        if args.mode == "manual":
            run_manual_mode_placeholder()
        elif args.mode == "auto":
            start_auto_simulation_with_current_settings() 
            logger.info("Automatischer Simulationsmodus (via CLI) beendet.")
        elif args.mode == "train_rl":
            run_rl_training_placeholder()
    else: 
        # Wenn keine Modus-Argumente ODER wenn `python -m src.main -h` aufgerufen wurde (was args erzeugt aber keinen mode)
        # und nicht durch SystemExit beendet wurde.
        # Zeige Menü, wenn nicht explizit ein CLI-Modus gestartet wurde.
        # Die --help-cli Logik von argparse beendet das Programm von selbst.
        if not (args and any(arg in sys.argv for arg in ['-h', '--help-cli'])):
             logger.info("Kein gültiger Modus via CLI angegeben oder keine Argumente. Starte Hauptmenü.")
             main_menu()

if __name__ == "__main__":
    main()