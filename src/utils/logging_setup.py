# src/utils/logging_setup.py

import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIRECTORY = "logs"
LOG_FILENAME = "rpg_game.log"
MAX_LOG_SIZE_MB = 5
LOG_BACKUP_COUNT = 3 # Anzahl alter Logdateien, die behalten werden

# Standard Log Level (kann später z.B. aus config.py oder Umgebungsvariable kommen)
DEFAULT_LOG_LEVEL = logging.INFO # Ändere zu logging.DEBUG für mehr Details

def setup_logging(log_level: int = DEFAULT_LOG_LEVEL):
    """
    Konfiguriert das zentrale Logging für die Anwendung.

    - Gibt Logs ab dem angegebenen Level auf der Konsole aus.
    - Schreibt Logs ab dem angegebenen Level in eine rotierende Datei (logs/rpg_game.log).
    - Erstellt das Log-Verzeichnis, falls es nicht existiert.

    Sollte EINMALIG beim Start der Anwendung aufgerufen werden.

    Args:
        log_level: Das minimale Logging-Level (z.B. logging.DEBUG, logging.INFO).
    """
    log_dir = Path(LOG_DIRECTORY)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / LOG_FILENAME
    except OSError as e:
        # Fallback, falls das Log-Verzeichnis nicht erstellt werden kann
        logging.error(f"Konnte Log-Verzeichnis '{LOG_DIRECTORY}' nicht erstellen: {e}. Logging in Datei deaktiviert.")
        log_file_path = None

    # Logging-Format definieren
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # Root-Logger konfigurieren
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level) # Setze das Basis-Level

    # Vorhandene Handler entfernen, um Doppel-Logging zu vermeiden, falls die Funktion mehrfach aufgerufen wird
    # (sollte nicht passieren, aber sicher ist sicher)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Konsolen-Handler (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level) # Konsole zeigt ab diesem Level an
    root_logger.addHandler(console_handler)

    # Datei-Handler (RotatingFileHandler) - nur wenn Pfad erstellt werden konnte
    if log_file_path:
        max_bytes = MAX_LOG_SIZE_MB * 1024 * 1024
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level) # Datei loggt auch ab diesem Level
        root_logger.addHandler(file_handler)
        logging.info(f"Logging wird in Datei geschrieben: {log_file_path.absolute()}")
    else:
        logging.info("Datei-Logging ist deaktiviert.")

    logging.info(f"Logging konfiguriert mit Level: {logging.getLevelName(log_level)}")

# Beispielhafte Verwendung (wird normalerweise in main.py aufgerufen)
if __name__ == '__main__':
    print("Konfiguriere Logging für Testzwecke (Level DEBUG)...")
    setup_logging(log_level=logging.DEBUG)

    # Test-Logs auf verschiedenen Levels
    logging.debug("Dies ist eine Debug-Meldung.")
    logging.info("Dies ist eine Info-Meldung.")
    logging.warning("Dies ist eine Warnung.")
    logging.error("Dies ist ein Fehler.")
    logging.critical("Dies ist ein kritischer Fehler.")

    # Test-Log aus einem anderen 'Modul'
    test_logger = logging.getLogger("mein_modul_test")
    test_logger.info("Eine Meldung aus einem anderen Logger.")

    print(f"Prüfe die Konsole und die Datei '{LOG_DIRECTORY}/{LOG_FILENAME}' (falls erstellt).")