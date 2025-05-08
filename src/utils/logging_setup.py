"""
Logging-Setup

Konfiguriert das Logging-System für das gesamte Projekt.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from src.config.config import get_config


def setup_logging(logger_name: str = None) -> logging.Logger:
    """
    Richtet das Logging-System ein und gibt einen Logger zurück.
    
    Args:
        logger_name (str, optional): Der Name des Loggers (Standardmäßig der Stammlogger)
        
    Returns:
        logging.Logger: Der konfigurierte Logger
    """
    config = get_config()
    log_config = config.logging
    
    # Standardwerte, falls nicht in der Konfiguration vorhanden
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    file_level = getattr(logging, log_config.get('file_level', 'DEBUG'))
    console_level = getattr(logging, log_config.get('console_level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    date_format = log_config.get('date_format', '%Y-%m-%d %H:%M:%S')
    log_dir = log_config.get('log_dir', 'logs')
    log_file = log_config.get('log_file', 'rpg.log')
    
    # Logger erstellen oder abrufen
    logger = logging.getLogger(logger_name)
    
    # Nur konfigurieren, wenn noch keine Handler vorhanden sind
    if not logger.handlers:
        logger.setLevel(log_level)
        formatter = logging.Formatter(log_format, date_format)
        
        # Konsolen-Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Datei-Handler (mit Rotation)
        try:
            # Verzeichnis erstellen, falls es nicht existiert
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, log_file)
            
            # Rotierender Datei-Handler (maximal 5MB pro Datei, maximal 5 Backup-Dateien)
            file_handler = RotatingFileHandler(
                log_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
            )
            file_handler.setLevel(file_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Wenn das Schreiben in die Logdatei fehlschlägt, loggen wir den Fehler in die Konsole
            logger.error(f"Konnte Logdatei nicht einrichten: {str(e)}")
    
    return logger


def get_logger(module_name: Optional[str] = None) -> logging.Logger:
    """
    Gibt einen für das Modul konfigurierten Logger zurück.
    
    Args:
        module_name (Optional[str]): Der Name des Moduls (standardmäßig __name__)
        
    Returns:
        logging.Logger: Der konfigurierte Logger für das Modul
    """
    logger_name = module_name if module_name else 'rpg'
    return setup_logging(logger_name)
