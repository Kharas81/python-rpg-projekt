"""
Zentrale Konfiguration

Lädt die Konfigurationsdaten aus settings.json5 und stellt sie zur Verfügung.
"""
import os
import json5
from typing import Dict, Any

# Standardwerte für den Fall, dass einige Einstellungen in der Datei fehlen
DEFAULT_CONFIG = {
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
    },
    "logging": {
        "level": "INFO",
        "file_level": "DEBUG",
        "console_level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "log_dir": "logs",
        "log_file": "rpg.log",
    },
    "rl": {
        "train": {
            "total_timesteps": 100000,
            "log_interval": 100,
            "n_eval_episodes": 10,
            "eval_interval": 1000,
        },
        "env": {
            "max_steps": 100,
            "reward_win": 100,
            "reward_lose": -100,
            "reward_damage_dealt_factor": 0.1,
            "reward_damage_taken_factor": -0.1,
        },
    },
}


class Config:
    """
    Zentrale Konfigurationsklasse, die Einstellungen aus settings.json5 lädt.
    """
    _instance = None
    _config = {}
    
    def __new__(cls):
        """
        Singleton-Pattern: Stellt sicher, dass nur eine Instanz existiert.
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """
        Lädt die Konfigurationsdaten aus der settings.json5-Datei.
        Wenn die Datei nicht existiert oder fehlerhaft ist, werden Standardwerte verwendet.
        """
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json5')
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as file:
                    self._config = json5.load(file)
            else:
                print(f"WARNUNG: Konfigurationsdatei {settings_path} nicht gefunden. Verwende Standardwerte.")
                self._config = DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"FEHLER beim Laden der Konfiguration: {str(e)}. Verwende Standardwerte.")
            self._config = DEFAULT_CONFIG.copy()
    
    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """
        Gibt einen Konfigurationswert zurück.
        
        Args:
            section (str): Der Abschnitt der Konfiguration (z.B. 'game_settings')
            key (str, optional): Der Schlüssel innerhalb des Abschnitts
            default (Any, optional): Der Standardwert, wenn der Wert nicht gefunden wird
            
        Returns:
            Any: Der Konfigurationswert oder der Standardwert
        """
        if section not in self._config:
            if section in DEFAULT_CONFIG:
                return DEFAULT_CONFIG[section] if key is None else DEFAULT_CONFIG[section].get(key, default)
            return default
        
        if key is None:
            return self._config[section]
        
        if key in self._config[section]:
            return self._config[section][key]
        
        if section in DEFAULT_CONFIG and key in DEFAULT_CONFIG[section]:
            return DEFAULT_CONFIG[section][key]
        
        return default
    
    @property
    def game_settings(self) -> Dict[str, Any]:
        """Gibt die Spieleinstellungen zurück."""
        return self.get('game_settings', default={})
    
    @property
    def logging(self) -> Dict[str, Any]:
        """Gibt die Logging-Einstellungen zurück."""
        return self.get('logging', default={})
    
    @property
    def rl(self) -> Dict[str, Any]:
        """Gibt die RL-Einstellungen zurück."""
        return self.get('rl', default={})
    
    def reload(self):
        """
        Lädt die Konfiguration neu.
        Nützlich, wenn die Konfigurationsdatei während der Laufzeit geändert wurde.
        """
        self._load_config()


# Globale Konfigurationsinstanz
config = Config()


def get_config() -> Config:
    """
    Gibt die globale Konfigurationsinstanz zurück.
    
    Returns:
        Config: Die globale Konfigurationsinstanz
    """
    return config
