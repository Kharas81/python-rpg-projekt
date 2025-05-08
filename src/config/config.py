# src/config/config.py

import sys
from typing import Dict, Any
from pathlib import Path

# Versuche, die Ladefunktion und Exceptions zu importieren
try:
    from src.definitions.loader import load_game_settings
    from src.utils.exceptions import DefinitionFileError, CriticalConfigError, RPGBaseException
except ImportError:
    # Fallback für lokale Ausführung oder Pfadprobleme
    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from definitions.loader import load_game_settings # type: ignore
    from utils.exceptions import DefinitionFileError, CriticalConfigError, RPGBaseException # type: ignore

# Initialisiere Konfigurationsvariablen mit Standardwerten (leer)
GAME_SETTINGS: Dict[str, Any] = {}
LOGGING_SETTINGS: Dict[str, Any] = {}
RL_SETTINGS: Dict[str, Any] = {}

try:
    _settings_data = load_game_settings() # Kann DefinitionFileError oder DefinitionContentError werfen
    
    # Weise die geladenen Sektionen zu, falls _settings_data erfolgreich geladen wurde
    # Die load_game_settings Funktion stellt sicher, dass es ein Dict ist oder wirft einen Fehler.
    GAME_SETTINGS = _settings_data.get("game_settings", {})
    LOGGING_SETTINGS = _settings_data.get("logging_settings", {})
    RL_SETTINGS = _settings_data.get("rl_settings", {})

    # Zusätzliche Prüfung, ob die Hauptsektionen vorhanden sind (optional, aber gut für Robustheit)
    if not GAME_SETTINGS:
        print("WARNUNG: Der Abschnitt 'game_settings' fehlt in settings.json5 oder ist leer.", file=sys.stderr)
    if not LOGGING_SETTINGS:
        print("WARNUNG: Der Abschnitt 'logging_settings' fehlt in settings.json5 oder ist leer.", file=sys.stderr)

except DefinitionFileError as e:
    # Wenn eine Definitionsdatei nicht gefunden oder nicht geparst werden konnte.
    # Dies ist ein kritischer Fehler für die settings.json5.
    # Wir verpacken den Fehler in CriticalConfigError, um seine Bedeutung hervorzuheben.
    # Die ursprüngliche Exception e wird als Ursache mitgegeben (__cause__).
    raise CriticalConfigError(
        message=f"Kritischer Fehler beim Laden der Spieleinstellungen (settings.json5).",
        original_exception=e
    ) from e
except RPGBaseException as e: # Fängt andere RPG-spezifische Fehler ab
    raise CriticalConfigError(
        message=f"Ein unerwarteter RPG-spezifischer Fehler trat beim Laden der Konfiguration auf.",
        original_exception=e
    ) from e
except Exception as e: # Fängt alle anderen, nicht vorhergesehenen Exceptions ab
    raise CriticalConfigError(
        message=f"Ein allgemeiner, unerwarteter Fehler trat beim Laden der Konfiguration auf.",
        original_exception=e
    ) from e

# Das Modul ist jetzt so konzipiert, dass es beim Import entweder erfolgreich die Konfiguration lädt
# oder eine CriticalConfigError wirft, was die Anwendung an höherer Stelle (z.B. main.py)
# behandeln muss (z.B. durch Programmabbruch mit Fehlermeldung).