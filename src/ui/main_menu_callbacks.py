# src/ui/main_menu_callbacks.py
"""
Enthält die Callback-Funktionen, die von den Menüoptionen in main.py aufgerufen werden.
Diese Funktionen implementieren die Logik hinter den Menüauswahlen.
"""
import logging
import os
import json 
import json5 
import subprocess # Für den Aufruf externer Skripte als Alternative
import sys # Um sys.executable zu finden
from typing import Optional, Dict, List, Any, Callable 

from src.utils import logging_setup
from src.config.config import CONFIG 
from src.config.user_config_manager import UserConfigManager 
from src.ui.cli_main_loop import CLISimulationLoop
from src.ui import cli_menu
from src.ui import cli_output
from src.definitions.loader import load_character_templates 
from src.definitions.character import CharacterTemplate 

# Importiere die Hauptfunktionen der RL-Skripte
try:
    from src.ai.rl_training import train_agent as run_training_script
except ImportError:
    logger = logging.getLogger(__name__) # Logger holen, falls noch nicht da
    logger.error("Konnte src.ai.rl_training.train_agent nicht importieren. Trainingsstart nicht möglich.", exc_info=True)
    def run_training_script(config_path: str): # Dummy-Funktion
        if cli_output: cli_output.print_message("FEHLER: Trainingsskript nicht gefunden.", cli_output.Colors.RED)

try:
    from src.ai.evaluate_agent import evaluate_agent_performance as run_evaluation_script
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("Konnte src.ai.evaluate_agent.evaluate_agent_performance nicht importieren. Evaluierungsstart nicht möglich.", exc_info=True)
    def run_evaluation_script(config_path: str): # Dummy-Funktion
        if cli_output: cli_output.print_message("FEHLER: Evaluierungsskript nicht gefunden.", cli_output.Colors.RED)


logger = logging.getLogger(__name__)

_current_selected_rl_setup_file_callbacks: Optional[str] = None

def initialize_menu_callbacks(ucm: UserConfigManager):
    global _current_selected_rl_setup_file_callbacks
    _current_selected_rl_setup_file_callbacks = ucm.get_preference("last_selected_rl_setup_file")
    logger.debug(f"main_menu_callbacks initialisiert. Last RL Setup: {_current_selected_rl_setup_file_callbacks}")


# --- Auto Simulation Callbacks --- (Bleiben unverändert)
def start_auto_simulation_with_user_settings_callback(ucm: UserConfigManager, 
                                                     clsm_type: Optional[type[CLISimulationLoop]]):
    if not clsm_type or not CONFIG or not cli_output:
        print("FEHLER: Simulationskomponenten nicht korrekt initialisiert für Callback (start_auto_simulation).")
        return

    sim_settings = ucm.get_preference("simulation_settings")
    if not sim_settings or not isinstance(sim_settings, dict): 
        logger.error("Ungültige oder fehlende Simulationseinstellungen in user_preferences für start_auto_simulation.")
        sim_settings = {"num_encounters": 1, "player_hero_id": "krieger", 
                        "opponent_config": {"num_opponents": 1, "level_pool": "1-2"}}
    
    cli_output.print_message("\nStarte automatische Simulation mit aktuellen Benutzereinstellungen:", cli_output.Colors.CYAN)
    cli_output.print_message(f"  Anzahl Begegnungen: {sim_settings.get('num_encounters', 1)}")
    cli_output.print_message(f"  Spieler-Held: {sim_settings.get('player_hero_id', 'krieger')}")
    opp_conf = sim_settings.get('opponent_config', {}) 
    cli_output.print_message(f"  Gegner-Anzahl: {opp_conf.get('num_opponents', 1)}")
    cli_output.print_message(f"  Gegner-Level-Pool: {opp_conf.get('level_pool', '1-2')}")
    
    try:
        simulation = clsm_type() 
        simulation.start_simulation_loop(
            num_encounters=sim_settings.get('num_encounters', 1),
            player_team_ids=[sim_settings.get('player_hero_id', 'krieger')],
            opponent_setup_config=opp_conf
        )
    except Exception as e:
        logger.error(f"Fehler während der CLI-Simulation (Callback): {e}", exc_info=True)
    logger.info("Automatische Simulation (Callback) beendet.")


def configure_simulation_settings_menu_callback(ucm: UserConfigManager, 
                                               char_template_loader: Optional[Callable[[], Dict[str, CharacterTemplate]]]):
    # ... (Diese Funktion bleibt unverändert von der letzten Version)
    if not cli_menu or not CONFIG or not cli_output or not char_template_loader: 
        print("FEHLER: Benötigte Module für Simulationseinstellungsmenü-Callback nicht geladen.")
        return "exit_menu" 

    char_templates: Dict[str, CharacterTemplate] = {}
    available_heroes: List[str] = []
    try:
        char_templates = char_template_loader() 
        available_heroes = list(char_templates.keys())
        if not available_heroes: raise ValueError("Keine Helden-Templates geladen.")
    except Exception as e:
        logger.error(f"Fehler beim Laden der Charakter-Templates für Menü-Callback: {e}")
        available_heroes = ["krieger", "magier", "schurke", "kleriker"] 
        cli_output.print_message("WARNUNG: Konnte Charakter-Templates nicht laden, verwende Standardheldenliste.", cli_output.Colors.YELLOW)

    def get_current_sim_settings_for_display() -> Dict[str, Any]:
        defaults = {"num_encounters": 1, "player_hero_id": "krieger", 
                    "opponent_config": {"num_opponents": 1, "level_pool": "1-2"}}
        current = ucm.get_preference("simulation_settings", defaults)
        if not isinstance(current.get("opponent_config"), dict): 
            current["opponent_config"] = defaults["opponent_config"]
        return current

    def change_encounters():
        current_val = get_current_sim_settings_for_display().get('num_encounters', 1)
        new_val = cli_menu.get_user_input_int(f"Anzahl Begegnungen (1-100, Aktuell: {current_val}):", 1, 100)
        if new_val is not None: 
            ucm.set_preference("simulation_settings.num_encounters", new_val)
            cli_output.print_message(f"Anzahl Begegnungen auf {new_val} gesetzt.", cli_output.Colors.LIGHT_GREEN)

    def change_hero():
        if not available_heroes:
            cli_output.print_message("Keine Helden-Templates zum Auswählen verfügbar.", cli_output.Colors.RED)
            return
        current_val = get_current_sim_settings_for_display().get('player_hero_id', 'krieger')
        current_char_templates = char_template_loader() 
        hero_options = []
        for hero_id in available_heroes:
            hero_name = hero_id 
            template = current_char_templates.get(hero_id) 
            if template and hasattr(template, 'name'): hero_name = template.name
            hero_options.append((f"{hero_id} ({hero_name})", lambda hid=hero_id: hid)) 
        
        chosen_hero_id_from_menu = cli_menu.display_menu(f"Spieler-Held auswählen (Aktuell: {current_val})", hero_options)
        if chosen_hero_id_from_menu and chosen_hero_id_from_menu != "exit_menu" and chosen_hero_id_from_menu in available_heroes:
            ucm.set_preference("simulation_settings.player_hero_id", chosen_hero_id_from_menu)
            cli_output.print_message(f"Spieler-Held auf '{chosen_hero_id_from_menu}' gesetzt.", cli_output.Colors.LIGHT_GREEN)

    def change_opponent_count():
        current_val = get_current_sim_settings_for_display().get('opponent_config', {}).get('num_opponents', 1)
        from src.environment.observation_manager import MAX_OPPONENTS_OBS # Importiere Konstante
        max_opp = MAX_OPPONENTS_OBS if MAX_OPPONENTS_OBS else 5 # Fallback, falls Konstante nicht definiert ist
        new_val = cli_menu.get_user_input_int(f"Anzahl Gegner (1-{max_opp}, Aktuell: {current_val}):", 1, max_opp)
        if new_val is not None: 
            ucm.set_preference("simulation_settings.opponent_config.num_opponents", new_val)
            cli_output.print_message(f"Anzahl Gegner auf {new_val} gesetzt.", cli_output.Colors.LIGHT_GREEN)
    
    def change_opponent_pool():
        current_val = get_current_sim_settings_for_display().get('opponent_config', {}).get('level_pool', '1-2')
        pools = ["1-2", "all"] 
        pool_options = [(pool, lambda p=pool: p) for pool in pools]
        chosen_pool_id = cli_menu.display_menu(f"Gegner Level-Pool (Aktuell: {current_val})", pool_options)
        if chosen_pool_id and chosen_pool_id != "exit_menu" and chosen_pool_id in pools: 
            ucm.set_preference("simulation_settings.opponent_config.level_pool", chosen_pool_id)
            cli_output.print_message(f"Gegner Level-Pool auf '{chosen_pool_id}' gesetzt.", cli_output.Colors.LIGHT_GREEN)

    while True:
        current_s = get_current_sim_settings_for_display()
        current_opp_s = current_s.get('opponent_config', {}) 
        options = [
            (f"Anzahl Begegnungen ändern (Aktuell: {current_s.get('num_encounters',1)})", change_encounters),
            (f"Spieler-Held auswählen (Aktuell: {current_s.get('player_hero_id', 'N/A')})", change_hero),
            (f"Anzahl Gegner ändern (Aktuell: {current_opp_s.get('num_opponents',1)})", change_opponent_count),
            (f"Gegner Level-Pool ändern (Aktuell: {current_opp_s.get('level_pool','N/A')})", change_opponent_pool),
        ]
        choice = cli_menu.display_menu("Auto-Simulationseinstellungen", options)
        if choice == "exit_menu" or choice == "error": break 
    return None


# --- Loglevel Callbacks --- (Bleiben unverändert)
def change_log_level_menu_callback(ucm: UserConfigManager):
    if not cli_menu or not logging_setup or not cli_output: return "exit_menu"
    
    def get_display_options_and_current_level():
        current_level_name = ucm.get_preference("preferred_loglevel", "INFO").upper()
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        display_opts = []
        for level in levels:
            prefix = ">> " if level == current_level_name else "   "
            display_opts.append(
                (f"{prefix}{level}", 
                 lambda lvl=level, ucm_param=ucm: (logging_setup.set_global_log_level(lvl), 
                                                   ucm_param.set_preference("preferred_loglevel", lvl)))
            )
        return display_opts, current_level_name

    while True:
        opts, current_name = get_display_options_and_current_level()
        result = cli_menu.display_menu(f"Ausgabedetailgrad ändern (Aktuell: {current_name})", opts)
        if result == "exit_menu" or result == "error": break
    return None 


# --- RL Training & Evaluierung Callbacks ---
def configure_rl_menu_callback(ucm: UserConfigManager):
    global _current_selected_rl_setup_file_callbacks 
    if not cli_menu or not cli_output: return "exit_menu"

    config_module_path = os.path.dirname(ucm.file_path) 
    rl_setups_dir = os.path.join(config_module_path, "rl_setups")
    os.makedirs(rl_setups_dir, exist_ok=True) 

    def select_rl_setup_file():
        global _current_selected_rl_setup_file_callbacks
        try:
            files = [f for f in os.listdir(rl_setups_dir) if f.endswith(".json5") and os.path.isfile(os.path.join(rl_setups_dir, f))]
        except FileNotFoundError: 
            logger.warning(f"RL Setup Verzeichnis '{rl_setups_dir}' nicht gefunden.")
            files = []
        
        if not files:
            cli_output.print_message(f"Keine RL-Setup-Dateien in '{rl_setups_dir}' gefunden.", cli_output.Colors.YELLOW)
            cli_output.print_message("Bitte erstelle eine Setup-Datei (z.B. 'my_training.json5') dort.", cli_output.Colors.YELLOW)
            return

        file_options = [(file, lambda f_name=file: f_name) for file in files]
        chosen_file_name = cli_menu.display_menu("RL-Setup-Datei auswählen", file_options)

        if chosen_file_name and chosen_file_name != "exit_menu" and chosen_file_name in files:
            _current_selected_rl_setup_file_callbacks = os.path.join(rl_setups_dir, chosen_file_name)
            ucm.set_preference("last_selected_rl_setup_file", _current_selected_rl_setup_file_callbacks)
            cli_output.print_message(f"RL-Setup '{_current_selected_rl_setup_file_callbacks}' ausgewählt.", cli_output.Colors.LIGHT_GREEN)

    def view_current_rl_setup():
        current_file_to_view = ucm.get_preference("last_selected_rl_setup_file")
        if current_file_to_view and os.path.exists(current_file_to_view):
            try:
                with open(current_file_to_view, 'r', encoding='utf-8') as f:
                    content = json5.load(f) 
                cli_output.print_message(f"\n--- Inhalt von '{current_file_to_view}' ---", cli_output.Colors.BOLD)
                cli_output.print_message(json.dumps(content, indent=2, ensure_ascii=False)) 
                cli_output.print_message("--- Ende des Inhalts ---", cli_output.Colors.BOLD)
            except Exception as e:
                logger.error(f"Fehler beim Lesen/Anzeigen der RL-Setup-Datei '{current_file_to_view}': {e}")
                cli_output.print_message(f"Konnte RL-Setup-Datei nicht anzeigen: {e}", cli_output.Colors.RED)
        else:
            cli_output.print_message("Keine RL-Setup-Datei ausgewählt oder Datei nicht gefunden.", cli_output.Colors.YELLOW)

    # KORREKTUR: Echte Aufrufe der importierten Funktionen
    def start_rl_training_with_config():
        current_file_to_use = ucm.get_preference("last_selected_rl_setup_file")
        if current_file_to_use and os.path.exists(current_file_to_use):
            cli_output.print_message(f"\nStarte RL-Training mit '{os.path.basename(current_file_to_use)}'...", cli_output.Colors.LIGHT_BLUE)
            try:
                run_training_script(current_file_to_use) # Direkter Aufruf
                cli_output.print_message("Trainingsskript beendet.", cli_output.Colors.LIGHT_GREEN)
            except Exception as e:
                logger.error(f"Fehler beim Ausführen des Trainingsskripts '{current_file_to_use}': {e}", exc_info=True)
                cli_output.print_message(f"Fehler im Trainingsskript: {e}", cli_output.Colors.RED)
        else: 
            cli_output.print_message("Bitte zuerst eine gültige RL-Setup-Datei auswählen.", cli_output.Colors.RED)
            
    def start_rl_evaluation_with_config():
        current_file_to_use = ucm.get_preference("last_selected_rl_setup_file")
        if current_file_to_use and os.path.exists(current_file_to_use):
            cli_output.print_message(f"\nStarte RL-Evaluierung mit '{os.path.basename(current_file_to_use)}'...", cli_output.Colors.LIGHT_BLUE)
            try:
                run_evaluation_script(current_file_to_use) # Direkter Aufruf
                cli_output.print_message("Evaluierungsskript beendet.", cli_output.Colors.LIGHT_GREEN)
            except Exception as e:
                logger.error(f"Fehler beim Ausführen des Evaluierungsskripts '{current_file_to_use}': {e}", exc_info=True)
                cli_output.print_message(f"Fehler im Evaluierungsskript: {e}", cli_output.Colors.RED)
        else: 
            cli_output.print_message("Bitte zuerst eine gültige RL-Setup-Datei auswählen.", cli_output.Colors.RED)

    while True:
        current_file_disp = os.path.basename(ucm.get_preference("last_selected_rl_setup_file","")) if ucm.get_preference("last_selected_rl_setup_file") else "Keine"
        options = [
            (f"RL-Setup-Datei auswählen (Aktuell: {current_file_disp})", select_rl_setup_file),
            ("Aktuelles RL-Setup anzeigen", view_current_rl_setup),
            ("Training starten (mit aktuellem Setup)", start_rl_training_with_config), # KORREKTUR
            ("Evaluierung starten (mit aktuellem Setup)", start_rl_evaluation_with_config), # KORREKTUR
        ]
        choice = cli_menu.display_menu("RL Training & Evaluierung", options)
        if choice == "exit_menu" or choice == "error": break
    return None


# --- Platzhalter Callbacks ---
def run_manual_mode_placeholder_callback():
    logger.info("Starte manuellen Spielmodus (Platzhalter)...")
    if cli_output: cli_output.print_message("\n--- Manueller Modus (Platzhalter) ---", cli_output.Colors.YELLOW)
    if cli_output: cli_output.print_message("Diese Funktion ist noch nicht implementiert.", cli_output.Colors.YELLOW)