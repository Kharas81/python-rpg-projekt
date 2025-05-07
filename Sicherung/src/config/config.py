import json5
from pathlib import Path
import typing
import functools # Für die get_setting Hilfsfunktion

# --- Pfaddefinition ---
# Annahme: Diese Datei (config.py) liegt in src/config/
# Das Projekt-Hauptverzeichnis ist drei Ebenen darüber.
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
except NameError:
    # Fallback, falls __file__ nicht definiert ist (z.B. in manchen interaktiven Umgebungen)
    PROJECT_ROOT = Path('.').resolve()

CONFIG_FILE_PATH = PROJECT_ROOT / "src" / "config" / "settings.json5"

# --- Ladefunktion ---
def _load_config(file_path: Path) -> typing.Dict[str, typing.Any]:
    """Lädt die Konfigurationsdatei (JSON5)."""
    try:
        print(f"INFO: Lade Konfiguration von: {file_path}") # Info zur geladenen Datei
        with open(file_path, 'r', encoding='utf-8') as f:
            settings = json5.load(f)
        print("INFO: Konfiguration erfolgreich geladen.")
        return settings
    except FileNotFoundError:
        print(f"FATAL: Konfigurationsdatei nicht gefunden: {file_path}")
        # Hier könnten wir Standardwerte zurückgeben oder das Programm beenden
        raise # Fehler weitergeben, damit das Problem offensichtlich wird
    except json5.JSON5DecodeError as e:
        print(f"FATAL: Fehler beim Parsen der Konfigurationsdatei {file_path}: {e}")
        raise # Fehler weitergeben
    except Exception as e:
        print(f"FATAL: Unerwarteter Fehler beim Laden der Konfiguration {file_path}: {e}")
        raise # Fehler weitergeben

# --- Geladene Einstellungen (werden bei Modulimport geladen) ---
_settings: typing.Dict[str, typing.Any] = _load_config(CONFIG_FILE_PATH)

# --- Zugriffsfunktion ---
def get_setting(key_path: str, default: typing.Any = None) -> typing.Any:
    """
    Greift auf eine Einstellung mittels eines 'Punkt-Pfades' zu.

    Beispiel: get_setting("logging.log_level", "INFO")

    Args:
        key_path: Der Pfad zur Einstellung (z.B. "group.subgroup.key").
        default: Der Standardwert, der zurückgegeben wird, falls der Pfad ungültig ist.

    Returns:
        Der Wert der Einstellung oder der Standardwert.
    """
    keys = key_path.split('.')
    value = _settings # Start mit dem gesamten Dictionary
    try:
        for key in keys:
            # Prüfen, ob der aktuelle Wert ein Dictionary ist, bevor zugegriffen wird
            if isinstance(value, dict):
                value = value[key]
            else:
                # Pfad führt durch ein Element, das kein Dictionary ist -> Fehler
                # print(f"WARNUNG: Ungültiger Pfad in get_setting: '{key}' in '{key_path}' hat keinen dict-Parent.")
                return default # Sicherer Rückfall auf Default
        return value
    except KeyError:
        # print(f"WARNUNG: Schlüssel '{key}' nicht in Pfad '{key_path}' gefunden.")
        return default
    except Exception as e:
        # print(f"WARNUNG: Unerwarteter Fehler in get_setting für Pfad '{key_path}': {e}")
        return default # Sicherer Rückfall

# --- Testblock ---
if __name__ == '__main__':
    print("\n--- Konfiguration Test ---")
    print(f"Projekt-Root angenommen als: {PROJECT_ROOT}")
    print(f"Konfigurationsdatei: {CONFIG_FILE_PATH}")

    print("\nGeladene Einstellungen (Auszug):")
    # Sicherer Zugriff über get_setting
    log_level = get_setting("logging.log_level", "FEHLER_BEIM_LESEN")
    log_file = get_setting("logging.log_file") # Default ist None
    default_class = get_setting("game_settings.default_player_class")
    non_existent = get_setting("pfad.existiert.nicht", "Standardwert")
    rl_lr = get_setting("rl_settings.ppo_config.learning_rate")
    paths_logs = get_setting("paths.logs")

    print(f"  Log Level: {log_level}")
    print(f"  Log Datei: {log_file}")
    print(f"  Standardklasse: {default_class}")
    print(f"  Nicht existierender Pfad: {non_existent}")
    print(f"  RL Learning Rate: {rl_lr}")
    print(f"  Logs Pfad: {paths_logs}")

    print("\nVersuch, auf nicht existierende Top-Level-Einstellung zuzugreifen:")
    test = get_setting("gibtsnicht")
    print(f"  'gibtsnicht': {test} (Typ: {type(test).__name__})")

    print("\nVersuch, auf verschachtelte Einstellung mit falschem Zwischenschritt zuzugreifen:")
    test_invalid_path = get_setting("logging.log_level.unterpunkt", "Standard")
    print(f"  'logging.log_level.unterpunkt': {test_invalid_path}")


