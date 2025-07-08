# src/config/user_config_manager.py
"""
Verwaltet das Laden und Speichern von benutzerspezifischen Einstellungen
aus/in einer JSON5-Datei (z.B. user_preferences.json5).
"""
import json5
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_USER_PREFS_FILENAME = "user_preferences.json5"
_THIS_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_PREFS_FILE_PATH = os.path.join(_THIS_MODULE_DIR, DEFAULT_USER_PREFS_FILENAME)

# NEUE DEFAULT_PREFERENCES Struktur für granulare Logging-Einstellungen
DEFAULT_PREFERENCES = {
  "simulation_settings": {
    "num_encounters": 1,
    "player_hero_id": "krieger",
    "opponent_config": {
      "num_opponents": 2,
      "level_pool": "1-2"
    }
  },
  "rl_training_settings": { # Beibehalten für Konsistenz, auch wenn noch nicht voll genutzt
    "agent_hero_id": "schurke", 
    "training_opponent_config": { "num_opponents": 1, "level_pool": "1-2" },
    "num_training_episodes": 10000,
    "use_curriculum_learning": False,
    "curriculum_definition_file": None,
    "num_parallel_runs": 1
  },
  "logging_preferences": { # NEUER Block für granulare Logging-Einstellungen
      "loglevel_console": "INFO",      # DEBUG, INFO, WARNING, ERROR, CRITICAL
      "loglevel_main_file": "DEBUG",   # Haupt-Logdatei (rpg_app.log) ist oft detaillierter
      "enable_combat_log_file": True, # True/False
      "loglevel_combat_file": "INFO"  # Dediziertes Kampfprotokoll, meist INFO
  },
  "last_selected_rl_setup_file": None 
}

class UserConfigManager:
    def __init__(self, file_path: str = USER_PREFS_FILE_PATH):
        self.file_path = file_path
        self.preferences: Dict[str, Any] = self._load_preferences()

    def _recursive_copy_defaults(self, default_dict: Dict[str, Any]) -> Dict[str, Any]:
        copied_dict = {}
        for key, value in default_dict.items():
            if isinstance(value, dict): copied_dict[key] = self._recursive_copy_defaults(value)
            elif isinstance(value, list): copied_dict[key] = [self._recursive_copy_defaults(item) if isinstance(item, dict) else item for item in value]
            else: copied_dict[key] = value
        return copied_dict

    def _ensure_default_keys(self, loaded_prefs: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Stellt rekursiv sicher, dass alle Default-Schlüssel in den geladenen Präferenzen vorhanden sind."""
        # Starte mit einer tiefen Kopie der Defaults
        final_prefs = self._recursive_copy_defaults(defaults if defaults is not None else DEFAULT_PREFERENCES)
        
        # Iteriere über die Schlüssel der Default-Struktur
        for key, default_value in (defaults if defaults is not None else DEFAULT_PREFERENCES).items():
            if key in loaded_prefs:
                if isinstance(default_value, dict) and isinstance(loaded_prefs[key], dict):
                    # Rekursiver Aufruf für verschachtelte Dictionaries
                    final_prefs[key] = self._ensure_default_keys(loaded_prefs[key], default_value)
                else:
                    # Überschreibe Default mit geladenem Wert, wenn Typ nicht Dict ist oder nicht übereinstimmt
                    final_prefs[key] = loaded_prefs[key]
            # Wenn key nicht in loaded_prefs, bleibt der Wert aus final_prefs (der Default) erhalten.
        return final_prefs


    def _load_preferences(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    prefs = json5.load(f)
                logger.info(f"Benutzereinstellungen aus '{self.file_path}' geladen.")
                return self._ensure_default_keys(prefs) # Stelle Defaults sicher
            else:
                logger.info(f"Keine Benutzereinstellungsdatei '{self.file_path}'. Erstelle mit Standardwerten.")
                default_copy = self._recursive_copy_defaults(DEFAULT_PREFERENCES)
                self._save_preferences(default_copy) 
                return default_copy
        except Exception as e:
            logger.error(f"Fehler Laden Benutzereinstellungen '{self.file_path}': {e}. Verwende Standardwerte.", exc_info=True)
            default_copy = self._recursive_copy_defaults(DEFAULT_PREFERENCES)
            try: self._save_preferences(default_copy)
            except Exception as save_e: logger.error(f"Konnte Standard-Benutzereinstellungen nicht in '{self.file_path}' speichern: {save_e}")
            return default_copy

    def _save_preferences(self, prefs_to_save: Optional[Dict[str, Any]] = None):
        data_to_save = prefs_to_save if prefs_to_save is not None else self.preferences
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json5.dump(data_to_save, f, indent=2, quote_keys=True, trailing_commas=False)
            logger.info(f"Benutzereinstellungen in '{self.file_path}' gespeichert.")
        except Exception as e:
            logger.error(f"Fehler Speichern Benutzereinstellungen '{self.file_path}': {e}", exc_info=True)

    def get_preference(self, key_path: str, default_return: Any = None) -> Any:
        keys = key_path.split('.')
        value = self.preferences
        try:
            for key in keys: value = value[key]
            return value
        except (KeyError, TypeError):
            # Hole Default aus der DEFAULT_PREFERENCES Struktur
            default_val_struct = DEFAULT_PREFERENCES
            try:
                for key in keys: default_val_struct = default_val_struct[key]
                return default_val_struct # Gib Default aus Struktur zurück
            except (KeyError, TypeError):
                return default_return # Äußerster Fallback

    def set_preference(self, key_path: str, value: Any):
        keys = key_path.split('.')
        data_ptr = self.preferences
        try:
            for key in keys[:-1]: 
                data_ptr = data_ptr.setdefault(key, {}) # Erstelle Pfad, falls nicht vorhanden
            data_ptr[keys[-1]] = value
            logger.debug(f"Benutzereinstellung '{key_path}' auf '{value}' gesetzt.")
            self._save_preferences() 
        except Exception as e:
            logger.error(f"Fehler Setzen Benutzereinstellung '{key_path}': {e}")

# ... (if __name__ == '__main__' Block bleibt gleich)
if __name__ == '__main__':
    print("--- Teste UserConfigManager ---")
    _TEST_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_config_data")
    os.makedirs(_TEST_CONFIG_DIR, exist_ok=True)
    test_file_path_ucm = os.path.join(_TEST_CONFIG_DIR, "test_user_prefs.json5")
    if os.path.exists(test_file_path_ucm): os.remove(test_file_path_ucm)

    manager = UserConfigManager(file_path=test_file_path_ucm)
    print(f"Initial geladen/Defaults: {manager.preferences}")
    assert manager.get_preference("logging_preferences.loglevel_console") == "INFO"
    assert manager.get_preference("logging_preferences.loglevel_main_file") == "DEBUG"
    assert manager.get_preference("logging_preferences.enable_combat_log_file") is True
    assert manager.get_preference("simulation_settings.num_encounters") == 1

    manager.set_preference("logging_preferences.loglevel_console", "DEBUG")
    assert manager.get_preference("logging_preferences.loglevel_console") == "DEBUG"
    manager.set_preference("simulation_settings.num_encounters", 5)
    assert manager.get_preference("simulation_settings.num_encounters") == 5
    
    manager2 = UserConfigManager(file_path=test_file_path_ucm) 
    print(f"\nGeladen aus existierender Datei: {manager2.preferences}")
    assert manager2.get_preference("logging_preferences.loglevel_console") == "DEBUG"
    assert manager2.get_preference("simulation_settings.num_encounters") == 5
    
    # Test: Teilweise fehlende Schlüssel in der Datei (z.B. opponent_config fehlt)
    faulty_prefs = {
        "simulation_settings": {"num_encounters": 10}, 
        "logging_preferences": {"loglevel_console": "WARNING"}
    } 
    with open(test_file_path_ucm, 'w') as f: json5.dump(faulty_prefs, f)
    manager3 = UserConfigManager(file_path=test_file_path_ucm)
    print(f"\nGeladen aus Datei mit teilweise fehlenden Keys: {manager3.preferences}")
    assert manager3.get_preference("logging_preferences.loglevel_console") == "WARNING" # Geladen
    assert manager3.get_preference("simulation_settings.num_encounters") == 10 # Geladen
    # Diese sollten von Defaults kommen:
    assert manager3.get_preference("simulation_settings.player_hero_id") == DEFAULT_PREFERENCES["simulation_settings"]["player_hero_id"]
    assert manager3.get_preference("simulation_settings.opponent_config.num_opponents") == DEFAULT_PREFERENCES["simulation_settings"]["opponent_config"]["num_opponents"]
    assert manager3.get_preference("logging_preferences.loglevel_main_file") == DEFAULT_PREFERENCES["logging_preferences"]["loglevel_main_file"]


    if os.path.exists(test_file_path_ucm): os.remove(test_file_path_ucm) 
    if os.path.exists(_TEST_CONFIG_DIR) and not os.listdir(_TEST_CONFIG_DIR): os.rmdir(_TEST_CONFIG_DIR)
    print("\n--- UserConfigManager-Tests abgeschlossen ---")