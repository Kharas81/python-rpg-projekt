# src/definitions/loaders/common.py

import json
import logging
from pathlib import Path
from typing import Any, Union, List, Dict

logger = logging.getLogger(__name__)

def load_json_file(file_path: Union[str, Path]) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
    """
    Hilfsfunktion zum sicheren Laden und Parsen einer einzelnen JSON-Datei.

    Args:
        file_path: Der Pfad zur JSON-Datei.

    Returns:
        Der geparste JSON-Inhalt (Liste oder Dict) oder None bei Fehlern.

    Raises:
        FileNotFoundError: Wenn die Datei nicht existiert.
        json.JSONDecodeError: Wenn die Datei kein valides JSON ist.
        Exception: Bei anderen unerwarteten Fehlern beim Dateizugriff.
    """
    path = Path(file_path)
    logger.debug(f"Versuche JSON-Datei zu laden: {path.absolute()}")

    if not path.is_file():
        logger.error(f"Datei nicht gefunden: {file_path}")
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"JSON-Datei erfolgreich geladen und geparst: {path.name}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Fehler beim Parsen von JSON in Datei: {path.name}. Fehler: {e}")
        raise  # Fehler weitergeben
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Laden von {path.name} aufgetreten: {e}")
        raise # Fehler weitergeben