# src/ui/main_menu_callbacks.py
# V2: Fügt eine Heldenauswahl für die Welt-Simulation hinzu.

import logging
import os
import random
from typing import Optional, Dict, List, Any, Callable, Type

from src.config.user_config_manager import UserConfigManager
from src.ui import cli_menu, cli_output
from src.definitions.character import CharacterTemplate
from src.app import runners

logger = logging.getLogger(__name__)

_profile_next_training_run: bool = False

def initialize_menu_callbacks(ucm: UserConfigManager):
    pass

def start_world_simulation_with_hero_selection():
    """Zeigt ein Menü zur Heldenauswahl und startet dann die Simulation."""
    from src.definitions.loader import load_character_templates
    
    char_templates = load_character_templates()
    hero_ids = list(char_templates.keys())
    
    menu_options = [(info.name.capitalize(), lambda h_id=h_id: h_id) for h_id, info in char_templates.items()]
    menu_options.append(("Zufälliger Held", lambda: "random"))

    chosen_hero = cli_menu.display_menu("Wähle einen Helden für die Simulation", menu_options)

    if chosen_hero and chosen_hero != "exit_menu":
        if chosen_hero == "random":
            chosen_hero = random.choice(hero_ids)
        
        runners.run_world_simulation_entrypoint(hero_id=chosen_hero)

def configure_simulation_settings_menu_callback(ucm: UserConfigManager, char_template_loader: Callable[[], Dict[str, CharacterTemplate]]):
    available_heroes = list(char_template_loader().keys()) if char_template_loader else ["krieger"]
    def change_encounters():
        current_val = ucm.get_preference("simulation_settings.num_encounters", 1)
        new_val = cli_menu.get_user_input_int(f"Anzahl Begegnungen (1-100, Aktuell: {current_val}):", 1, 100)
        if new_val is not None: ucm.set_preference("simulation_settings.num_encounters", new_val)
    def change_hero():
        current_val = ucm.get_preference("simulation_settings.player_hero_id", "krieger")
        hero_options = [(hero_id, lambda hid=hero_id: hid) for hero_id in available_heroes]
        chosen_hero = cli_menu.display_menu(f"Spieler-Held auswählen (Aktuell: {current_val})", hero_options)
        if chosen_hero and chosen_hero != "exit_menu": ucm.set_preference("simulation_settings.player_hero_id", chosen_hero)
    def change_opponent_count():
        current_val = ucm.get_preference("simulation_settings.opponent_config.num_opponents", 1)
        new_val = cli_menu.get_user_input_int(f"Anzahl Gegner (1-5, Aktuell: {current_val}):", 1, 5)
        if new_val is not None: ucm.set_preference("simulation_settings.opponent_config.num_opponents", new_val)
    while True:
        s = ucm.get_preference("simulation_settings")
        options = [
            (f"Anzahl Begegnungen ändern (Aktuell: {s.get('num_encounters', 1)})", change_encounters),
            (f"Spieler-Held auswählen (Aktuell: {s.get('player_hero_id', 'N/A')})", change_hero),
            (f"Anzahl Gegner ändern (Aktuell: {s.get('opponent_config', {}).get('num_opponents', 1)})", change_opponent_count),
        ]
        if cli_menu.display_menu("Auto-Kampf-Einstellungen", options) == "exit_menu": break

def configure_granular_logging_menu_callback(ucm: UserConfigManager):
    from src.utils import logging_setup
    def set_level(key, name):
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_options = [(level, lambda l=level: l) for level in levels]
        chosen_level = cli_menu.display_menu(f"Loglevel für {name} setzen", level_options)
        if chosen_level and chosen_level != "exit_menu":
            ucm.set_preference(f"logging_preferences.{key}", chosen_level)
            logging_setup.setup_logging(force_reconfigure=True)
    while True:
        prefs = ucm.get_preference("logging_preferences")
        options = [
            (f"Konsolen-Loglevel (Aktuell: {prefs.get('loglevel_console', 'INFO')})", lambda: set_level("loglevel_console", "Konsole")),
            (f"Haupt-Logdatei-Loglevel (Aktuell: {prefs.get('loglevel_main_file', 'DEBUG')})", lambda: set_level("loglevel_main_file", "Haupt-Logdatei")),
        ]
        if cli_menu.display_menu("Detaillierte Logging-Einstellungen", options) == "exit_menu": break

def configure_rl_menu_callback(ucm: UserConfigManager):
    global _profile_next_training_run
    config_dir_pref = ucm.get_preference("last_selected_rl_setup_file")
    config_dir = os.path.dirname(config_dir_pref) if config_dir_pref else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "rl_setups")
    if not os.path.exists(config_dir):
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "rl_setups")
    def select_file():
        files = [f for f in os.listdir(config_dir) if f.endswith(".json5")]
        if not files:
            cli_output.print_message("Keine RL-Setups gefunden.", cli_output.Colors.YELLOW)
            return
        file_options = [(f, lambda name=f: name) for f in files]
        chosen = cli_menu.display_menu("RL-Setup-Datei auswählen", file_options)
        if chosen and chosen != "exit_menu": ucm.set_preference("last_selected_rl_setup_file", os.path.join(config_dir, chosen))
    def start_training():
        f_path = ucm.get_preference("last_selected_rl_setup_file")
        if f_path and os.path.exists(f_path):
            runners.run_rl_training(f_path, _profile_next_training_run, batch_mode=False)
        else:
            cli_output.print_message("Bitte zuerst eine gültige RL-Setup-Datei auswählen.", cli_output.Colors.RED)
    def start_eval():
        f_path = ucm.get_preference("last_selected_rl_setup_file")
        if f_path and os.path.exists(f_path):
            runners.run_rl_evaluation(f_path)
        else:
            cli_output.print_message("Bitte zuerst eine gültige RL-Setup-Datei auswählen.", cli_output.Colors.RED)
    while True:
        last_file = ucm.get_preference('last_selected_rl_setup_file')
        file_disp = os.path.basename(last_file) if last_file else "Keine"
        options = [
            (f"RL-Setup-Datei auswählen (Aktuell: {file_disp})", select_file),
            ("Training starten", start_training),
            ("Evaluierung starten", start_eval),
            (f"Profiling für nächsten Lauf (Aktuell: {'AN' if _profile_next_training_run else 'AUS'})", lambda: globals().update(_profile_next_training_run=not _profile_next_training_run)),
        ]
        if cli_menu.display_menu("RL Training & Evaluierung", options) == "exit_menu": break

def dev_tools_menu_callback():
    options = [
        ("API-Server starten", runners.run_api_server),
        ("Sequenzielles RL-Training starten", runners.run_sequential_training),
        ("ngrok Authtoken setzen", runners.set_ngrok_token),
        ("Alle Tests ausführen (pytest)", runners.run_pytest),
    ]
    while True:
        if cli_menu.display_menu("Entwickler-Tools & Tests", options) == "exit_menu": break