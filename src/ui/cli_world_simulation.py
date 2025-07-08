# src/ui/cli_world_simulation.py
# V10: Akzeptiert eine hero_id als Parameter, um die Simulation flexibel zu starten.

import time
import logging
import os
import ipywidgets as widgets
from IPython.display import display, clear_output

from src.game_logic.game_state_manager import GameStateManager
from src.game_logic.player_controller import RLPlayerController
from src.ui.cli_game_renderer import render_dashboard
from src.ui import cli_output
from src.ui.cli_output_adapter import CliOutputAdapter
from src.utils.logging_setup import SIMULATION_EVENT_LOGGER_NAME

logger = logging.getLogger(__name__)
SIMULATION_SPEED_SECONDS = 0.5

# KORREKTUR: Die Funktion nimmt jetzt eine hero_id entgegen.
def run_world_simulation(hero_id: str):
    cli_output.print_message(f"\nStarte RL-gesteuerte Welt-Simulation mit Held: {hero_id.upper()}...", cli_output.Colors.BOLD, force_console=True)
    
    # KORREKTUR: hero_to_load wird durch den Parameter ersetzt.
    hero_to_load = hero_id
    model_path = os.path.join("latest_models", f"{hero_to_load}_latest_model.zip")
    
    cli_output.print_message(f"Versuche, das neueste Modell für '{hero_to_load}' zu laden von: {model_path}", force_console=True)
    
    gsm = None
    try:
        # ... (Rest der try-except und finally Blöcke bleibt unverändert wie in V9) ...
        cli_output.print_message("[DEBUG] RLPlayerController wird initialisiert...", force_console=True)
        player_controller = RLPlayerController(model_path=model_path)
        cli_output.print_message("[DEBUG] RLPlayerController erfolgreich initialisiert.", cli_output.Colors.LIGHT_GREEN, force_console=True)
        
        output_adapter = CliOutputAdapter()
        cli_output.print_message("[DEBUG] GameStateManager wird initialisiert...", force_console=True)
        gsm = GameStateManager(hero_id=hero_to_load, player_controller=player_controller, output_logger=output_adapter)
        cli_output.print_message("[DEBUG] GameStateManager erfolgreich initialisiert.", cli_output.Colors.LIGHT_GREEN, force_console=True)
        
        event_log_instance = logging.getLogger(SIMULATION_EVENT_LOGGER_NAME)
        file_handler_found = None
        for handler in event_log_instance.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler_found = handler
                break
        if file_handler_found:
            abs_log_path = os.path.abspath(file_handler_found.baseFilename)
            cli_output.print_message(f"\n[DEBUG] Log-Konfiguration OK. Events werden geschrieben nach:\n-> {abs_log_path}\n", cli_output.Colors.LIGHT_GREEN, force_console=True)
        else:
            cli_output.print_message("\n[DEBUG] WARNUNG: Der Logger für Simulations-Events ist NICHT für die Datei-Ausgabe konfiguriert!", cli_output.Colors.RED, force_console=True)

    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung der Simulation: {e}", exc_info=True)
        cli_output.print_message(f"\n--- FATALER FEHLER BEI DER INITIALISIERUNG ---\nFehlertyp: {type(e).__name__}\nMeldung: {e}", cli_output.Colors.RED, force_console=True)
        return

    map_widget = widgets.Output(layout={'border': '1px solid black'})
    legend_widget = widgets.Output()
    quest_widget = widgets.Output(layout={'border': '1px solid lightgrey'})
    stats_widget = widgets.Output()
    world_log_widget = widgets.Output(layout={'border': '1px solid lightgrey', 'height': '150px', 'overflow': 'auto'})
    combat_log_widget = widgets.Output(layout={'border': '1px solid lightgrey', 'height': '150px', 'overflow': 'auto'})
    left_column = widgets.VBox([map_widget, legend_widget])
    right_column = widgets.VBox([quest_widget, stats_widget, world_log_widget, combat_log_widget])
    dashboard = widgets.HBox([left_column, right_column])
    left_column.layout.width = '60%'
    right_column.layout.width = '38%'
    display(dashboard)

    try:
        while not gsm.simulation_is_over:
            render_dashboard(map_widget, stats_widget, world_log_widget, combat_log_widget, quest_widget, legend_widget, gsm)
            gsm.tick()
            time.sleep(SIMULATION_SPEED_SECONDS)
        
        render_dashboard(map_widget, stats_widget, world_log_widget, combat_log_widget, quest_widget, legend_widget, gsm)
        player = gsm.get_hero()
        if player and not player.is_defeated:
             cli_output.print_message("\n🎉 SIEG! Quest erfüllt und Ausgang erreicht! 🎉", cli_output.Colors.BOLD + cli_output.Colors.LIGHT_GREEN, force_console=True)
        else:
             cli_output.print_message("\n Niederlage. Der Agent wurde besiegt.", cli_output.Colors.BOLD + cli_output.Colors.RED, force_console=True)

    except KeyboardInterrupt:
        cli_output.print_message("\nSimulation durch Benutzer abgebrochen.", cli_output.Colors.YELLOW, force_console=True)
    except Exception as e:
        logger.error("Ein unerwarteter Fehler ist in der Welt-Simulation aufgetreten.", exc_info=True)
        with world_log_widget:
            clear_output(wait=True)
            print(f"FATALER FEHLER IN DER SIMULATIONSLOGIK:\n{e}")
    finally:
        cli_output.print_message("[DEBUG] Erzwinge das Schließen aller Logger (shutdown)...", force_console=True)
        logging.shutdown()
        cli_output.print_message("[DEBUG] Logging-System heruntergefahren. Alle Daten sollten jetzt geschrieben sein.", force_console=True)