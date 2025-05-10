# src/utils/logging_setup.py
"""
Modul zur zentralen Konfiguration des Logging-Systems für das Projekt.
"""
import logging
import logging.config
import os
from typing import Dict, Any

# Versuche, die globale Konfiguration zu laden, um Logging-Einstellungen zu beziehen.
# Dies schafft eine Abhängigkeit, die beachtet werden muss (config muss vor logging_setup initialisiert werden können).
# Eine Alternative wäre, Pfade/Level direkt hier zu definieren oder per Umgebungsvariablen zu übergeben.
try:
    from src.config.config import CONFIG
    LOG_SETTINGS = CONFIG.get("logging_settings")
    if LOG_SETTINGS is None: # Fallback, falls logging_settings nicht in settings.json5 definiert ist
        LOG_SETTINGS = {
            "log_level": "INFO",
            "log_file": "logs/rpg_game_default.log",
            "log_to_console": True,
            "log_to_file": True,
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S"
        }
except ImportError:
    # Fallback, falls src.config.config nicht importiert werden kann (z.B. während initialem Setup oder Tests)
    print("WARNUNG: src.config.config konnte nicht importiert werden. Verwende Standard-Logging-Einstellungen.")
    LOG_SETTINGS = {
        "log_level": "INFO",
        "log_file": "logs/rpg_game_default.log",
        "log_to_console": True,
        "log_to_file": True,
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S"
    }

# Sicherstellen, dass das logs-Verzeichnis existiert
LOG_FILE_PATH = LOG_SETTINGS.get("log_file", "logs/rpg_game_default.log")
LOG_DIR = os.path.dirname(os.path.abspath(LOG_FILE_PATH))
if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR)
    except OSError as e:
        # Dies könnte passieren, wenn mehrere Prozesse gleichzeitig versuchen, das Verzeichnis zu erstellen.
        # Oder bei Berechtigungsproblemen.
        print(f"FEHLER: Konnte Log-Verzeichnis nicht erstellen: {LOG_DIR} - {e}")
        # Im Fehlerfall könnte man das Logging in die Datei deaktivieren
        LOG_SETTINGS["log_to_file"] = False


def setup_logging() -> None:
    """
    Konfiguriert das Python-Logging-System basierend auf den Einstellungen
    aus der Konfigurationsdatei (via LOG_SETTINGS).
    """
    log_level_str = LOG_SETTINGS.get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO) # Default zu INFO, falls Level ungültig

    log_format = LOG_SETTINGS.get("log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    date_format = LOG_SETTINGS.get("date_format", "%Y-%m-%d %H:%M:%S")

    handlers: Dict[str, Any] = {}
    
    if LOG_SETTINGS.get("log_to_console", True):
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        }
        
    if LOG_SETTINGS.get("log_to_file", True) and LOG_FILE_PATH:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "standard",
            "filename": LOG_FILE_PATH,
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 3, # Behalte 3 alte Logdateien
            "encoding": "utf-8"
        }

    if not handlers: # Falls weder Konsole noch Datei konfiguriert sind
        print("WARNUNG: Kein Logging-Handler konfiguriert (weder Konsole noch Datei).")
        # Füge einen NullHandler hinzu, um "No handlers could be found for logger X" Meldungen zu vermeiden
        logging.getLogger().addHandler(logging.NullHandler())
        return

    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False, # Wichtig, um Loggers von Bibliotheken nicht zu deaktivieren
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": date_format,
            },
        },
        "handlers": handlers,
        "root": { # Konfiguriert den Root-Logger
            "level": log_level, # Setze den Level hier, damit Handler ihn übernehmen können
            "handlers": list(handlers.keys()),
        },
        # Man könnte hier auch spezifische Logger konfigurieren, z.B.:
        # "loggers": {
        #     "src.game_logic": { # Beispiel für einen spezifischen Logger
        #         "level": "DEBUG",
        #         "handlers": list(handlers.keys()),
        #         "propagate": False # Verhindert, dass Nachrichten an den Root-Logger weitergegeben werden
        #     }
        # }
    }
    
    try:
        logging.config.dictConfig(logging_config)
        # Test Log-Nachricht
        # logging.getLogger(__name__).info("Logging-System erfolgreich konfiguriert.")
    except Exception as e:
        # Falls dictConfig fehlschlägt, falle auf eine Basiskonfiguration zurück
        print(f"FEHLER bei logging.config.dictConfig: {e}. Fallback auf basicConfig.")
        logging.basicConfig(level=log_level, format=log_format, datefmt=date_format)
        logging.error("Fallback auf logging.basicConfig aufgrund eines Konfigurationsfehlers.")


# Führe die Setup-Funktion aus, wenn das Modul importiert wird.
# Andere Module können dann einfach `import logging` und `logger = logging.getLogger(__name__)` verwenden.
setup_logging()


if __name__ == '__main__':
    # Dieser Block wird ausgeführt, wenn das Skript direkt gestartet wird.
    # Er dient zum Testen der Logging-Konfiguration.
    
    # Erhalte einen Logger für dieses Testmodul
    logger = logging.getLogger(__name__) # oder z.B. logging.getLogger("my_test_logger")
    
    print(f"\nAktuelles Arbeitsverzeichnis: {os.getcwd()}")
    print(f"Logging-Einstellungen werden verwendet: {LOG_SETTINGS}")
    print(f"Log-Datei Pfad: {os.path.abspath(LOG_FILE_PATH) if LOG_SETTINGS.get('log_to_file') else 'Nicht konfiguriert'}")
    
    logger.debug("Dies ist eine Debug-Nachricht (sollte nur bei Level DEBUG sichtbar sein).")
    logger.info("Dies ist eine Info-Nachricht.")
    logger.warning("Dies ist eine Warnung.")
    logger.error("Dies ist eine Fehlermeldung.")
    logger.critical("Dies ist eine kritische Fehlermeldung.")
    
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Eine Ausnahme ist aufgetreten (mit Stacktrace, wenn Level ERROR oder niedriger).")
        
    print("\nTest-Logging abgeschlossen. Überprüfe die Konsole und ggf. die Log-Datei.")
    if LOG_SETTINGS.get('log_to_file'):
        print(f"Log-Datei sollte hier sein: {os.path.abspath(LOG_FILE_PATH)}")