# src/ui/cli_game_renderer.py
"""
Stellt Funktionen zur Verfügung, um die Komponenten für das
ipywidgets-Dashboard (Karte, Status-Tabelle, Event-Logs, Legende) zu erstellen.
V2: Greift auf den CharacterManager zu, um Charakterdaten zu erhalten.
"""
from typing import TYPE_CHECKING, List, Dict, Any
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import ipywidgets as widgets
from IPython.display import display, clear_output

if TYPE_CHECKING:
    from src.game_logic.game_state_manager import GameStateManager
    from src.game_logic.entities import CharacterInstance

# --- Farben für Matplotlib-Rendering ---
WALL_COLOR = np.array([0.2, 0.2, 0.2])
FLOOR_COLOR = np.array([0.7, 0.6, 0.5])
GOAL_COLOR = np.array([1.0, 0.84, 0.0])
PLAYER_COLOR_PLOT = 'blue'
OPPONENT_COLOR_PLOT = 'red'

def _create_map_figure(game_state_manager: 'GameStateManager') -> plt.Figure:
    """Erstellt die Matplotlib-Figur für die Karte."""
    tiles = game_state_manager.map_manager.get_tiles()
    height = len(tiles)
    width = len(tiles[0])
    
    image = np.zeros((height, width, 3))
    for r in range(height):
        for c in range(width):
            if tiles[r][c] == 1: image[r, c] = WALL_COLOR
            elif tiles[r][c] == 2: image[r, c] = GOAL_COLOR
            else: image[r, c] = FLOOR_COLOR
            
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.imshow(image)
    
    player_agent_id = game_state_manager.player_agent_id
    
    # KORREKTUR: Greift auf den character_manager zu
    for char_id, character in game_state_manager.character_manager.active_characters.items():
        if hasattr(character, 'position'):
            pos = character.position
            symbol = '$' if char_id == player_agent_id else '%'
            color = PLAYER_COLOR_PLOT if char_id == player_agent_id else OPPONENT_COLOR_PLOT
            ax.text(pos['x'], pos['y'], symbol, color=color, fontsize=16, ha='center', va='center', fontweight='bold')

    ax.axis('off')
    fig.tight_layout()
    return fig

def _create_bar_string(current: int, maximum: int, length: int = 10) -> str:
    """Erstellt einen textbasierten Fortschrittsbalken."""
    if maximum == 0:
        return f"[----------] (N/A)"
    percent = float(current) / maximum
    filled_length = int(length * percent)
    bar = '█' * filled_length + '-' * (length - filled_length)
    return f"[{bar}] ({current}/{maximum})"

def _create_stats_dataframe(game_state_manager: 'GameStateManager') -> pd.DataFrame:
    """Erstellt einen Pandas DataFrame mit den Charakter-Statuswerten, inkl. Balken."""
    # KORREKTUR: Greift auf den character_manager zu
    characters = list(game_state_manager.character_manager.active_characters.values())
    
    data: Dict[str, List[Any]] = {
        "Name": [], "Typ": [], "HP": [], "Ressource": [], "Level": [], "XP": []
    }
    
    # Sortiert den Spieler immer nach oben
    if game_state_manager.player_agent_id:
        characters.sort(key=lambda c: c.instance_id != game_state_manager.player_agent_id)

    for char in characters:
        if char.is_defeated: continue

        data["Name"].append(char.name)
        data["Typ"].append("Spieler" if hasattr(char, 'xp') else "Gegner")
        
        data["HP"].append(_create_bar_string(char.current_hp, char.max_hp))
        
        res_str = "N/A"
        res_type = getattr(char.base_template, 'resource_type', 'NONE')

        if res_type == "MANA":
            res_str = f"M: {_create_bar_string(char.current_mana, char.max_mana)}"
        elif res_type == "STAMINA":
            res_str = f"S: {_create_bar_string(char.current_stamina, char.max_stamina)}"
        elif res_type == "ENERGY":
            res_str = f"E: {_create_bar_string(char.current_energy, char.max_energy)}"
        data["Ressource"].append(res_str)

        data["Level"].append(char.level)
        xp_bar = _create_bar_string(char.xp, char.xp_to_next_level) if hasattr(char, 'xp') else "N/A"
        data["XP"].append(xp_bar)

    df = pd.DataFrame(data)
    return df.set_index("Name")

def _create_quest_text(game_state_manager: 'GameStateManager') -> str:
    quest = game_state_manager.quest_manager.active_quest
    if not quest: return "Keine aktive Quest."
    header = "--- Quest: Die Prüfung des Agenten ---"
    obj_texts = [
        f"[{'✓' if obj.is_complete() else ' '}] " +
        (f"Besiege Gegner ({obj.current_amount}/{obj.required_amount})" if obj.type == "kill" else "Erreiche das Ziel")
        for obj in quest.objectives
    ]
    return header + "\n" + " | ".join(obj_texts)

def _create_legend_text() -> str:
    return (
        "--- Legende ---\n"
        "$ : Spieler\n"
        "% : Gegner\n"
        "X : Ziel\n"
        "■ : Wand"
    )

def render_dashboard(
    map_widget: widgets.Output,
    stats_widget: widgets.Output,
    world_log_widget: widgets.Output,
    combat_log_widget: widgets.Output,
    quest_widget: widgets.Output,
    legend_widget: widgets.Output,
    game_state_manager: 'GameStateManager'
):
    with map_widget:
        clear_output(wait=True)
        fig = _create_map_figure(game_state_manager)
        display(fig)
        plt.close(fig)
        
    with quest_widget:
        clear_output(wait=True)
        print(_create_quest_text(game_state_manager))

    with stats_widget:
        clear_output(wait=True)
        df = _create_stats_dataframe(game_state_manager)
        if not df.empty:
            display(df)
        else:
            print("--- Keine Charaktere im Spiel ---")

    with world_log_widget:
        clear_output(wait=True)
        print("--- Welt-Ereignisse ---")
        print("\n".join(list(game_state_manager.world_events_for_ui)))
        
    with combat_log_widget:
        clear_output(wait=True)
        print("--- Kampf-Ereignisse ---")
        print("\n".join(list(game_state_manager.combat_events_for_ui)))

    with legend_widget:
        clear_output(wait=True)
        print(_create_legend_text())