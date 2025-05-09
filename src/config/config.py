"""
Zentrales Config-Modul, das Einstellungen aus settings.json5 lädt.
"""
import os
import json5
from typing import Dict, Any, Optional

# Globale Variable, um die Konfiguration zu cachen
_config_cache = None

def get_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Gibt die Konfiguration aus settings.json5 zurück.
    
    Args:
        config_path: Optionaler Pfad zur Konfigurationsdatei.
        
    Returns:
        Dict[str, Any]: Ein Dictionary mit den Konfigurationseinstellungen.
    """
    global _config_cache
    
    # Wenn die Konfiguration bereits geladen wurde und kein neuer Pfad angegeben wurde, returne den Cache
    if _config_cache is not None and config_path is None:
        return _config_cache
    
    # Standard-Konfigurationspfad, wenn keiner angegeben wurde
    if config_path is None:
        # Pfad relativ zum aktuellen Skript
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, 'src', 'config', 'settings.json5')
    
    try:
        print(f"DEBUG: Versuche, Konfigurationsdatei zu laden: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json5.load(f)
        print("DEBUG: Konfiguration erfolgreich geladen.")
        _config_cache = config
        return config
    except FileNotFoundError:
        print(f"FEHLER: Konfigurationsdatei nicht gefunden: {config_path}")
    except Exception as e:
        print(f"FEHLER beim Laden der Konfigurationsdatei: {e}")
    
    # Rückfallkonfiguration
    print("DEBUG: Verwende Standardwerte für die Konfiguration.")
    return {
        "game_settings": {
            "min_damage": 1,
            "base_weapon_damage": 5,
            "hit_chance_base": 90,
            "hit_chance_accuracy_factor": 3,
            "hit_chance_evasion_factor": 2,
            "hit_chance_min": 5,
            "hit_chance_max": 95,
            "xp_level_base": 100,
            "xp_level_factor": 1.5,
            "resource_regen_percent": 5
        },
        "logging": {
            "level": "INFO",
            "file": "logs/rpg_game.log",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "console_level": "INFO"
        },
        "rl_settings": {
            "max_episode_steps": 100,
            "max_players": 4,
            "max_opponents": 6,
            "max_skills_per_character": 10,
            "max_targets": 10,
            "rewards": {
                "victory": 10.0,
                "defeat": -10.0,
                "damage_factor": 0.1,
                "healing_factor": 0.2,
                "kill": 1.0,
                "time_penalty": -0.01
            }
        }
    }