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

# Standardpfad zur Konfigurationsdatei des Benutzers
DEFAULT_USER_PREFS_FILENAME = "user_preferences.json5"
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config") # Annahme: Dieses Modul ist in src/config/
USER_PREFS_FILE_PATH = os.path.join(CONFIG_DIR, DEFAULT_USER_PREFS_FILENAME)


# Standardwerte, falls die Datei nicht existiert oder unvollständig ist
DEFAULT_PREFERENCES = {
  "simulation_settings": {
    "num_encounters": 1,
    "player_hero_id": "krieger",
    "opponent_config": {
      "num_opponents": 2,
      "level_pool": "1-2"
    }
  },
  "preferred_loglevel": "INFO",
  "last_selected_rl_setup_file": None
}

class UserConfigManager:
    def __init__(self, file_path: str = USER_PREFS_FILE_PATH):
        self.file_path = file_path
        self.preferences: Dict[str, Any] = self._load_preferences()

    def _load_preferences(self) -> Dict[str, Any]:
        """Lädt die Benutzereinstellungen aus der Datei."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    prefs = json5.load(f)
                logger.info(f"Benutzereinstellungen aus '{self.file_path}' geladen.")
                # Stelle sicher, dass alle Default-Schlüssel vorhanden sind
                return self._ensure_default_keys(prefs)
            else:
                logger.info(f"Keine Benutzereinstellungsdatei unter '{self.file_path}' gefunden. Erstelle mit Standardwerten.")
                self._save_preferences(DEFAULT_PREFERENCES) # Erstelle Datei mit Defaults
                return dict(DEFAULT_PREFERENCES) # Wichtig: Kopie zurückgeben
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benutzereinstellungen aus '{self.file_path}': {e}. Verwende Standardwerte.", exc_info=True)
            # Bei Fehler mit Defaults arbeiten und versuchen, Defaults zu speichern, um eine valide Datei zu haben
            clean_defaults = dict(DEFAULT_PREFERENCES)
            try:
                self._save_preferences(clean_defaults)
            except Exception as save_e:
                logger.error(f"Konnte auch keine Standard-Benutzereinstellungen in '{self.file_path}' speichern: {save_e}")
            return clean_defaults

    def _ensure_default_keys(self, loaded_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Stellt sicher, dass alle Schlüssel aus DEFAULT_PREFERENCES in den geladenen Prefs vorhanden sind."""
        updated_prefs = dict(DEFAULT_PREFERENCES) # Starte mit Defaults
        
        # Überschreibe Defaults mit geladenen Werten, wenn die Struktur passt
        for key, default_value in DEFAULT_PREFERENCES.items():
            if key in loaded_prefs:
                if isinstance(default_value, dict) and isinstance(loaded_prefs[key], dict):
                    # Für verschachtelte Dictionaries (wie simulation_settings)
                    # auch die inneren Schlüssel sicherstellen
                    inner_updated = dict(default_value)
                    inner_updated.update(loaded_prefs[key])
                    # Und für opponent_config noch eine Ebene tiefer
                    if key == "simulation_settings" and "opponent_config" in default_value:
                        default_opp_conf = default_value["opponent_config"]
                        loaded_opp_conf = loaded_prefs[key].get("opponent_config", {})
                        final_opp_conf = dict(default_opp_conf)
                        final_opp_conf.update(loaded_opp_conf)
                        inner_updated["opponent_config"] = final_opp_conf
                    updated_prefs[key] = inner_updated
                else:
                    updated_prefs[key] = loaded_prefs[key]
        return updated_prefs


    def _save_preferences(self, prefs_to_save: Optional[Dict[str, Any]] = None):
        """Speichert die aktuellen Benutzereinstellungen in die Datei."""
        data_to_save = prefs_to_save if prefs_to_save is not None else self.preferences
        try:
            # Stelle sicher, dass das config-Verzeichnis existiert
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json5.dump(data_to_save, f, indent=2, quote_keys=True, trailing_commas=False)
            logger.info(f"Benutzereinstellungen in '{self.file_path}' gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Benutzereinstellungen in '{self.file_path}': {e}", exc_info=True)

    def get_preference(self, key_path: str, default: Any = None) -> Any:
        """
        Holt einen Wert aus den Einstellungen. Unterstützt Punktnotation für Pfade.
        Beispiel: get_preference("simulation_settings.num_encounters")
        """
        keys = key_path.split('.')
        value = self.preferences
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            logger.warning(f"Einstellung '{key_path}' nicht in user_preferences gefunden. Gebe Default '{default}' zurück.")
            return default

    def set_preference(self, key_path: str, value: Any):
        """
        Setzt einen Wert in den Einstellungen. Unterstützt Punktnotation für Pfade.
        Speichert die Änderungen danach automatisch.
        """
        keys = key_path.split('.')
        data_ptr = self.preferences
        try:
            for i, key in enumerate(keys[:-1]): # Navigiere bis zum vorletzten Schlüssel
                if key not in data_ptr or not isinstance(data_ptr[key], dict):
                    data_ptr[key] = {} # Erstelle verschachteltes Dict, falls nicht vorhanden
                data_ptr = data_ptr[key]
            
            last_key = keys[-1]
            data_ptr[last_key] = value
            logger.debug(f"Benutzereinstellung '{key_path}' auf '{value}' gesetzt.")
            self._save_preferences() # Änderungen sofort speichern
        except Exception as e:
            logger.error(f"Fehler beim Setzen der Benutzereinstellung '{key_path}': {e}")


if __name__ == '__main__':
    print("--- Teste UserConfigManager ---")
    # Erstelle eine temporäre Testdatei
    test_file_path = os.path.join(CONFIG_DIR, "test_user_prefs.json5")
    if os.path.exists(test_file_path):
        os.remove(test_file_path)

    manager = UserConfigManager(file_path=test_file_path)
    print(f"Geladene/Standard-Präferenzen: {manager.preferences}")
    assert manager.get_preference("preferred_loglevel") == "INFO" # Default

    manager.set_preference("preferred_loglevel", "DEBUG")
    assert manager.get_preference("preferred_loglevel") == "DEBUG"
    print(f"Loglevel nach set: {manager.get_preference('preferred_loglevel')}")

    manager.set_preference("simulation_settings.num_encounters", 5)
    assert manager.get_preference("simulation_settings.num_encounters") == 5
    print(f"Num Encounters nach set: {manager.get_preference('simulation_settings.num_encounters')}")
    
    manager.set_preference("simulation_settings.opponent_config.level_pool", "all")
    assert manager.get_preference("simulation_settings.opponent_config.level_pool") == "all"
    print(f"Opponent Level Pool nach set: {manager.get_preference('simulation_settings.opponent_config.level_pool')}")

    manager.set_preference("last_selected_rl_setup_file", "configs/rl_setups/my_test.json5")
    print(f"RL Setup File: {manager.get_preference('last_selected_rl_setup_file')}")

    # Teste Laden einer existierenden Datei
    manager2 = UserConfigManager(file_path=test_file_path) # Sollte jetzt aus der Datei laden
    print(f"\nGeladen aus existierender Datei: {manager2.preferences}")
    assert manager2.get_preference("preferred_loglevel") == "DEBUG"
    assert manager2.get_preference("simulation_settings.num_encounters") == 5
    assert manager2.get_preference("simulation_settings.opponent_config.level_pool") == "all"

    # Test mit fehlendem Schlüssel in der Datei (sollte Default verwenden)
    faulty_prefs = {"preferred_loglevel": "WARNING"} # num_encounters fehlt
    with open(test_file_path, 'w', encoding='utf-8') as f:
        json5.dump(faulty_prefs, f, indent=2)
    manager3 = UserConfigManager(file_path=test_file_path)
    print(f"\nGeladen aus fehlerhafter Datei (num_encounters sollte Default sein): {manager3.preferences}")
    assert manager3.get_preference("preferred_loglevel") == "WARNING"
    assert manager3.get_preference("simulation_settings.num_encounters") == DEFAULT_PREFERENCES["simulation_settings"]["num_encounters"]


    if os.path.exists(test_file_path):
        os.remove(test_file_path) # Aufräumen
    print("\n--- UserConfigManager-Tests abgeschlossen ---")