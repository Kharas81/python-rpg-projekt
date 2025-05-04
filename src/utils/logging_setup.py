"""
Logging-Setup für das Python RPG Projekt.

Dieses Modul konfiguriert das Logging-System für das gesamte Projekt.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import datetime

# Pfad zum Logs-Verzeichnis relativ zum Projektroot
LOGS_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'logs'
))

# Stelle sicher, dass das Logs-Verzeichnis existiert
os.makedirs(LOGS_DIR, exist_ok=True)

def setup_logger(name=None, log_level=logging.INFO):
    """
    Richtet einen Logger mit Konsolenausgabe und Datei-Logging ein.
    
    Args:
        name: Name des Loggers (default: None für Root-Logger)
        log_level: Logging-Level (default: logging.INFO)
        
    Returns:
        logging.Logger: Konfigurierter Logger
    """
    # Logger erstellen oder abrufen
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Logger zurücksetzen, falls er bereits Handler hat
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Formatter erstellen
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Konsolen-Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Datei-Handler (rotierend)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOGS_DIR, f"{timestamp}_rpg.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Beispielnutzung
if __name__ == "__main__":
    logger = setup_logger("test_logger")
    logger.debug("Das ist eine Debug-Nachricht")
    logger.info("Das ist eine Info-Nachricht")
    logger.warning("Das ist eine Warnung")
    logger.error("Das ist ein Fehler")
    logger.critical("Das ist ein kritischer Fehler")
