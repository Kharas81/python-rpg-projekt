"""
Base Loader Module

Dieses Modul stellt die Basisklasse für alle spezialisierten JSON-Daten-Loader bereit.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Setze den Pfad zum JSON-Datenverzeichnis relativ zum Projektroot
JSON_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "json_data")

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class BaseLoader:
    """
    Basisklasse für alle JSON-Daten-Loader.
    
    Stellt gemeinsame Funktionalität für das Laden und Caching von JSON-Dateien bereit.
    """
    
    def __init__(self, filename: str) -> None:
        """
        Initialisiert den BaseLoader.
        
        Args:
            filename: Name der zu ladenden JSON-Datei
        """
        self.filename = filename
        self._data_cache: Optional[Dict[str, Any]] = None
        
    def _load_json_file(self) -> Dict[str, Any]:
        """
        Lädt eine JSON-Datei und gibt deren Inhalt zurück.
        
        Returns:
            Dict mit den geladenen JSON-Daten
            
        Raises:
            FileNotFoundError: Wenn die Datei nicht gefunden wird
            json.JSONDecodeError: Wenn die Datei kein gültiges JSON enthält
        """
        file_path = os.path.join(JSON_DATA_DIR, self.filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                logger.debug(f"Lade JSON-Datei: {self.filename}")
                return json.load(file)
        except FileNotFoundError:
            logger.error(f"JSON-Datei nicht gefunden: {self.filename}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Fehler beim Parsen der JSON-Datei {self.filename}: {str(e)}")
            raise
    
    def get_data(self, reload: bool = False) -> Dict[str, Any]:
        """
        Lädt Daten aus der JSON-Datei oder gibt den Cache zurück.
        
        Args:
            reload: Wenn True, werden die Daten unabhängig vom Cache neu geladen
            
        Returns:
            Dict mit den geladenen Daten
        """
        if self._data_cache is None or reload:
            logger.info(f"Lade Daten aus {self.filename}...")
            self._data_cache = self._load_json_file()
        return self._data_cache
    
    def get_version(self) -> str:
        """
        Gibt die Versionsnummer der Daten zurück.
        
        Returns:
            Versionsnummer als String
        """
        data = self.get_data()
        return data.get("version", "unknown")
