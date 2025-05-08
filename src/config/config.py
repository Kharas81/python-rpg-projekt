# src/config/config.py

import sys
from typing import Dict, Any, Optional
from pathlib import Path # Hinzugefügt für den Fallback-Importpfad

try:
    from src.definitions.loader import load_game_settings
except ImportError:
    # Fallback, um src/ zum Pfad hinzuzufügen, falls das Skript nicht im Kontext des Gesamtprojekts läuft
    current_dir = Path(__file__).resolve().parent
    src_dir = current_dir.parent # src/
    if str(src_dir) not in sys.path:
         sys.path.insert(0, str(src_dir))
    from definitions.loader import load_game_settings

_settings_data: Optional[Dict[str, Any]] = load_game_settings()

GAME_SETTINGS: Dict[str, Any] = {}
LOGGING_SETTINGS: Dict[str, Any] = {}
RL_SETTINGS: Dict[str, Any] = {}

if _settings_data is None:
    print("KRITISCHER FEHLER: Spieleinstellungen (settings.json5) konnten nicht geladen werden. "
          "Die Anwendung wird möglicherweise nicht korrekt funktionieren.", file=sys.stderr)
else:
    GAME_SETTINGS = _settings_data.get("game_settings", {})
    LOGGING_SETTINGS = _settings_data.get("logging_settings", {})
    RL_SETTINGS = _settings_data.get("rl_settings", {})