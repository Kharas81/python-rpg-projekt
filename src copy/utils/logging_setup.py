# src/utils/logging_setup.py
"""
Modul zur zentralen Konfiguration des Logging-Systems für das Projekt.
"""
import logging
import logging.config # dictConfig importieren
import os
from typing import Dict, Any, Optional

# Globale Variable für die aktuelle Logging-Konfiguration, damit sie geändert werden kann
CURRENT_LOGGING_CONFIG: Dict[str, Any] = {}

try:
    from src.config.config import CONFIG
    LOG_SETTINGS_FROM_JSON = CONFIG.get("logging_settings")
    if LOG_SETTINGS_FROM_JSON is None: 
        LOG_SETTINGS_FROM_JSON = {} 
except ImportError:
    print("WARNUNG: src.config.config konnte nicht importiert werden für logging_setup. Verwende Standard-Logging-Einstellungen.")
    LOG_SETTINGS_FROM_JSON = {}

# Standardwerte, falls in settings.json5 nicht vorhanden
DEFAULT_LOG_SETTINGS = {
    "log_level": "INFO",
    "log_file": "logs/rpg_game_default.log",
    "log_to_console": True,
    "log_to_file": True,
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}

# Fülle CURRENT_LOGGING_CONFIG mit Werten aus JSON oder Defaults
CURRENT_LOGGING_CONFIG['log_level'] = LOG_SETTINGS_FROM_JSON.get("log_level", DEFAULT_LOG_SETTINGS["log_level"])
CURRENT_LOGGING_CONFIG['log_file'] = LOG_SETTINGS_FROM_JSON.get("log_file", DEFAULT_LOG_SETTINGS["log_file"])
CURRENT_LOGGING_CONFIG['log_to_console'] = LOG_SETTINGS_FROM_JSON.get("log_to_console", DEFAULT_LOG_SETTINGS["log_to_console"])
CURRENT_LOGGING_CONFIG['log_to_file'] = LOG_SETTINGS_FROM_JSON.get("log_to_file", DEFAULT_LOG_SETTINGS["log_to_file"])
CURRENT_LOGGING_CONFIG['log_format'] = LOG_SETTINGS_FROM_JSON.get("log_format", DEFAULT_LOG_SETTINGS["log_format"])
CURRENT_LOGGING_CONFIG['date_format'] = LOG_SETTINGS_FROM_JSON.get("date_format", DEFAULT_LOG_SETTINGS["date_format"])


LOG_FILE_PATH = CURRENT_LOGGING_CONFIG["log_file"]
LOG_DIR = os.path.dirname(os.path.abspath(LOG_FILE_PATH))

if not os.path.exists(LOG_DIR) and CURRENT_LOGGING_CONFIG['log_to_file']:
    try:
        os.makedirs(LOG_DIR)
    except OSError as e:
        print(f"FEHLER: Konnte Log-Verzeichnis nicht erstellen: {LOG_DIR} - {e}")
        CURRENT_LOGGING_CONFIG["log_to_file"] = False


def _build_logging_dictconfig() -> Dict[str, Any]:
    """Baut die Konfiguration für logging.config.dictConfig zusammen."""
    log_level_str = CURRENT_LOGGING_CONFIG.get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO) 

    log_format = CURRENT_LOGGING_CONFIG.get("log_format")
    date_format = CURRENT_LOGGING_CONFIG.get("date_format")

    handlers: Dict[str, Any] = {}
    
    if CURRENT_LOGGING_CONFIG.get("log_to_console", True):
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level, 
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        }
        
    if CURRENT_LOGGING_CONFIG.get("log_to_file", True) and LOG_FILE_PATH:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level, 
            "formatter": "standard",
            "filename": LOG_FILE_PATH,
            "maxBytes": 1024 * 1024 * 5,  
            "backupCount": 3, 
            "encoding": "utf-8"
        }

    if not handlers: 
        return { 
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {"null": {"class": "logging.NullHandler", "level": "DEBUG"}},
            "root": {"handlers": ["null"], "level": "DEBUG"},
        }

    return {
        "version": 1,
        "disable_existing_loggers": False, 
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": date_format,
            },
        },
        "handlers": handlers,
        "root": { 
            "level": log_level, 
            "handlers": list(handlers.keys()),
        },
    }

def setup_logging() -> None:
    """Konfiguriert das Python-Logging-System."""
    config_dict = _build_logging_dictconfig()
    try:
        logging.config.dictConfig(config_dict)
    except Exception as e:
        print(f"FEHLER bei logging.config.dictConfig: {e}. Fallback auf basicConfig.")
        logging.basicConfig(level=getattr(logging, CURRENT_LOGGING_CONFIG.get("log_level", "INFO").upper(), logging.INFO), 
                            format=CURRENT_LOGGING_CONFIG.get("log_format"), 
                            datefmt=CURRENT_LOGGING_CONFIG.get("date_format"))
        logging.error("Fallback auf logging.basicConfig aufgrund eines Konfigurationsfehlers.")

def set_global_log_level(level_name: str) -> bool:
    """
    Ändert den globalen Loglevel zur Laufzeit.
    Akzeptiert Level-Namen wie "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
    Gibt True bei Erfolg zurück, False bei ungültigem Level-Namen.
    """
    level_name_upper = level_name.strip().upper()
    numeric_level = getattr(logging, level_name_upper, None)

    logger_instance = logging.getLogger(__name__) # Logger für diese Funktion

    if numeric_level is None:
        logger_instance.warning(f"Ungültiger Loglevel-Name: {level_name}. Loglevel nicht geändert.")
        return False

    CURRENT_LOGGING_CONFIG['log_level'] = level_name_upper 
    
    new_config_dict = _build_logging_dictconfig()
    try:
        logging.config.dictConfig(new_config_dict)
        # Logge die erfolgreiche Änderung mit dem *neuen* Level des Root-Loggers
        logging.getLogger().info(f"Globaler Loglevel auf {level_name_upper} ({numeric_level}) gesetzt.")
        return True
    except Exception as e:
        logger_instance.error(f"Fehler beim Setzen des Loglevels auf {level_name_upper}: {e}")
        return False

# Initiale Konfiguration beim Import
setup_logging()

if __name__ == '__main__':
    logger_test = logging.getLogger("test_logging_setup")
    
    print(f"Aktueller Loglevel (aus Config-Var): {CURRENT_LOGGING_CONFIG['log_level']}")
    logger_test.debug("Dies ist eine Debug-Nachricht (vor Level-Änderung).")
    logger_test.info("Dies ist eine Info-Nachricht (vor Level-Änderung).")
    
    print("\nSetze Loglevel auf DEBUG...")
    set_global_log_level("DEBUG")
    logger_test.debug("Dies ist eine Debug-Nachricht (NACH Level-Änderung auf DEBUG).")
    logger_test.info("Dies ist eine Info-Nachricht (NACH Level-Änderung auf DEBUG).")

    print("\nSetze Loglevel auf WARNING...")
    set_global_log_level("WARNING")
    logger_test.debug("Diese Debug-Nachricht sollte NICHT erscheinen.")
    logger_test.info("Diese Info-Nachricht sollte NICHT erscheinen.")
    logger_test.warning("Diese Warnung SOLLTE erscheinen.")

    print("\nSetze Loglevel auf ungültig 'VERBOS'.")
    set_global_log_level("VERBOS") 
    logger_test.warning("Diese Warnung sollte immer noch erscheinen (Level ist WARNING).")

    print("\nLogging Setup Tests abgeschlossen.")