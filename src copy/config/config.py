# src/config/config.py
"""
Modul zum Laden und Bereitstellen von Konfigurationseinstellungen aus settings.json5.
Stellt ein globales CONFIG-Objekt bereit.
"""
import json5
import os
from typing import Dict, Any, Optional

# Pfad zur Konfigurationsdatei settings.json5
# Annahme: config.py ist in src/config/ und settings.json5 ist im selben Verzeichnis.
_SETTINGS_FILE_NAME = "settings.json5"
_SETTINGS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), _SETTINGS_FILE_NAME)

class Config:
    """
    Eine Klasse, die Konfigurationsdaten kapselt und einfachen Zugriff ermöglicht.
    Die Daten werden aus der settings.json5-Datei geladen.
    """
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        # Dynamisches Erstellen von Attributen für Top-Level-Keys in settings.json5
        # z.B. self.game_settings, self.logging_settings
        for key, value in data.items():
            if isinstance(value, dict):
                # Für verschachtelte Dictionaries erstellen wir Unter-Config-Objekte (oder lassen sie als dicts)
                # Für Einfachheit hier als dicts, könnte man auch zu Unter-Config-Objekten machen.
                setattr(self, key, value) 
            else:
                setattr(self, key, value)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Ermöglicht den Zugriff auf verschachtelte Konfigurationswerte über einen Pfad.
        Beispiel: config.get("game_settings.min_damage")
        """
        keys = key_path.split('.')
        value = self._data
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def __repr__(self) -> str:
        return f"Config(data_keys={list(self._data.keys())})"

# Globale Instanz der Konfiguration
# Wird beim ersten Import dieses Moduls geladen.
_CONFIG: Optional[Config] = None

def load_config() -> Config:
    """
    Lädt die Konfiguration aus der settings.json5 Datei und gibt ein Config-Objekt zurück.
    Implementiert Caching, um die Datei nicht mehrmals zu laden.
    """
    global _CONFIG
    if _CONFIG is None:
        try:
            with open(_SETTINGS_FILE_PATH, 'r', encoding='utf-8') as f:
                settings_data = json5.load(f)
            _CONFIG = Config(settings_data)
            # Hier könnte man Logging hinzufügen: logger.info("Konfiguration erfolgreich geladen.")
        except FileNotFoundError:
            # logger.critical(f"FATAL: Konfigurationsdatei settings.json5 nicht gefunden unter {_SETTINGS_FILE_PATH}")
            print(f"FATAL: Konfigurationsdatei settings.json5 nicht gefunden unter {_SETTINGS_FILE_PATH}")
            # In einem echten Szenario könnte hier das Programm beendet oder eine Standardkonfiguration geladen werden.
            raise  # Erneut auslösen, um das Problem deutlich zu machen
        except Exception as e:
            # logger.critical(f"FATAL: Fehler beim Laden der Konfigurationsdatei settings.json5: {e}")
            print(f"FATAL: Fehler beim Laden der Konfigurationsdatei settings.json5: {e}")
            raise
    return _CONFIG

# Stelle sicher, dass die Konfiguration beim Import geladen wird und als CONFIG verfügbar ist.
# Andere Module können dann einfach `from src.config.config import CONFIG` verwenden.
CONFIG = load_config()

if __name__ == '__main__':
    # Testen der Konfigurationsladung
    print(f"Versuche, Konfiguration aus '{_SETTINGS_FILE_PATH}' zu laden...")
    
    # Das Modul-Level CONFIG sollte bereits geladen sein
    if CONFIG:
        print("\nKonfigurationsobjekt (CONFIG) erfolgreich geladen.")
        print(f"Typ von CONFIG: {type(CONFIG)}")
        
        # Zugriff auf Top-Level-Einstellungen
        print(f"\nGame Settings (als Attribut): {CONFIG.game_settings}")
        print(f"Logging Settings (als Attribut): {CONFIG.logging_settings}")
        
        # Zugriff auf spezifische Werte über die get-Methode
        print(f"\nMin Damage (via get): {CONFIG.get('game_settings.min_damage')}")
        print(f"XP Level Base (via get): {CONFIG.get('game_settings.xp_level_base')}")
        print(f"Log Level (via get): {CONFIG.get('logging_settings.log_level')}")
        
        # Zugriff auf einen nicht existierenden Wert mit Default
        print(f"Nicht existierender Wert (via get mit Default): {CONFIG.get('game_settings.max_players', 4)}")
        
        # Direkter Attributzugriff auf verschachtelte Werte (wenn als dicts gespeichert)
        if hasattr(CONFIG, 'game_settings') and isinstance(CONFIG.game_settings, dict):
            print(f"\nBase Weapon Damage (direkter Dict-Zugriff): {CONFIG.game_settings.get('base_weapon_damage')}")

        print(f"\nGesamtes CONFIG-Objekt: {CONFIG}")

        # Testen, ob erneutes Laden aus dem Cache kommt (durch erneuten Aufruf von load_config)
        # (Schwer direkt zu testen ohne Mocking, da _CONFIG global ist)
        # Man könnte eine print-Anweisung in load_config() vor dem if _CONFIG is None: einfügen für den Test.
        print("\nErneuter Aufruf von load_config()...")
        config_again = load_config()
        if config_again is CONFIG:
            print("load_config() hat dieselbe Instanz zurückgegeben (aus Cache).")
        else:
            print("WARNUNG: load_config() hat eine neue Instanz zurückgegeben (Cache funktioniert nicht wie erwartet).")
            
    else:
        print("Fehler: Konfigurationsobjekt (CONFIG) konnte nicht geladen werden.")