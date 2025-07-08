# src/app/runners.py
# V2: Passt den Welt-Simulations-Runner an, um eine hero_id zu akzeptieren.

import logging
import os
import sys
import subprocess
from typing import Optional, Dict, List, Any, Callable, Type

# Direkte Imports der auszuführenden Logik
# HINWEIS: Wir importieren die Funktion jetzt direkt
from src.ui.cli_world_simulation import run_world_simulation
from src.ui.cli_main_loop import CLISimulationLoop
from src.config.user_config_manager import UserConfigManager
from src.definitions.loader import load_character_templates

# ... (Lazy-loading für RL-Imports bleibt gleich) ...
try:
    from src.ai.rl_training import train_agent_entry_point
except ImportError:
    train_agent_entry_point = None
try:
    from src.ai.evaluate_agent import evaluate_agent_performance
except ImportError:
    evaluate_agent_performance = None

logger = logging.getLogger(__name__)


def _run_external_command(command_list: List[str], description: str):
    # ... (Diese Funktion bleibt unverändert)
    from src.ui import cli_output
    cli_output.print_message(f"\nFühre aus: '{description}'...", cli_output.Colors.CYAN, force_console=True)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        process = subprocess.Popen(command_list, cwd=project_root, stdout=sys.stdout, stderr=sys.stderr, text=True, encoding='utf-8')
        process.communicate()
        rc = process.poll()
        if rc != 0:
            cli_output.print_message(f"\n'{description}' mit Fehlern beendet (Return Code: {rc}).", cli_output.Colors.RED, force_console=True)
    except FileNotFoundError:
        cli_output.print_message(f"Befehl '{command_list[0]}' nicht gefunden. Stelle sicher, dass er im Systempfad ist.", cli_output.Colors.RED, force_console=True)
    except Exception as e:
        cli_output.print_message(f"Fehler beim Ausführen von '{description}': {e}", cli_output.Colors.RED, force_console=True)
    input("\nDrücke Enter, um zum Menü zurückzukehren...")


# --- Runner für Entwickler-Tools (bleiben unverändert) ---
def run_api_server():
    _run_external_command([sys.executable, "-m", "src.api.server"], "FastAPI Server starten")
def run_sequential_training():
    _run_external_command([sys.executable, "tools/run_sequential_training.py"], "Sequenzielles RL-Training")
def run_pytest():
    _run_external_command(['pytest', '-v'], "Pytest Testlauf (Verbose)")
def set_ngrok_token():
    token = input("Bitte gib deinen ngrok Authtoken ein und drücke Enter: ")
    if token and token.strip():
        _run_external_command([sys.executable, "-m", "pyngrok", "config", "add-authtoken", token.strip()], "ngrok Token installieren")

# --- Runner für Simulationen ---
def run_auto_combat_simulation(ucm: UserConfigManager):
    # ... (Diese Funktion bleibt unverändert)
    sim_settings = ucm.get_preference("simulation_settings")
    try:
        simulation = CLISimulationLoop()
        simulation.start_simulation_loop(
            num_encounters=sim_settings.get('num_encounters', 1),
            player_team_ids=[sim_settings.get('player_hero_id', 'krieger')],
            opponent_setup_config=sim_settings.get('opponent_config', {})
        )
    except Exception as e:
        logger.error(f"Fehler während der CLI-Kampf-Simulation: {e}", exc_info=True)
        input("Ein Fehler ist aufgetreten. Drücke Enter...")

# KORREKTUR: Die Funktion akzeptiert jetzt eine hero_id
def run_world_simulation_entrypoint(hero_id: str):
    """Führt die prozedurale Welt-Simulation (mit Dashboard) für einen bestimmten Helden aus."""
    try:
        run_world_simulation(hero_id=hero_id)
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Starten der Welt-Simulation aufgetreten: {e}", exc_info=True)
        input("Ein Fehler ist aufgetreten. Drücke Enter...")

# --- Runner für RL-Prozesse (bleiben unverändert) ---
def run_rl_training(config_path: str, profile: bool, batch_mode: bool):
    if train_agent_entry_point is None:
        logger.error("Die Funktion 'train_agent_entry_point' konnte nicht importiert werden. RL-Training nicht möglich.")
        return
    train_agent_entry_point(config_path, profile, batch_mode)

def run_rl_evaluation(config_path: str):
    if evaluate_agent_performance is None:
        logger.error("Die Funktion 'evaluate_agent_performance' konnte nicht importiert werden. RL-Evaluierung nicht möglich.")
        return
    evaluate_agent_performance(config_path)