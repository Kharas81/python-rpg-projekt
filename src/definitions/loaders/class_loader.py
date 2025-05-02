# src/definitions/loaders/class_loader.py

import logging
from pathlib import Path
from typing import Union, List, Dict, Any

# Nutze relativen Import für base_definitions und common
from ..base_definitions import CharacterClassDefinition, ClassDatabase
from .common import load_json_file

logger = logging.getLogger(__name__)

def load_character_classes_from_json(file_path: Union[str, Path]) -> ClassDatabase:
    """
    Lädt Charakterklassen-Definitionen aus der angegebenen JSON-Datei.
    """
    classes: ClassDatabase = {}
    class_file = Path(file_path)

    logger.info(f"Lade Charakterklassen aus Datei: {class_file.absolute()}")

    try:
        data = load_json_file(class_file) # Nutze die Hilfsfunktion
        if data is None:
            return classes # Keine Daten geladen

        if not isinstance(data, list):
            logger.error(f"Unerwartetes Format in {class_file.name}. Erwartet: Liste.")
            raise TypeError(f"Die Datei {class_file.name} muss eine Liste von Objekten enthalten.")

        for entry in data:
            if not isinstance(entry, dict):
                 logger.warning(f"Ungültiger Klasseneintrag (kein Dict) in {class_file.name}. Überspringe: {entry}")
                 continue
            try:
                # Keine komplexen Typ-Checks hier, verlassen uns auf Dataclass TypeError
                class_def = CharacterClassDefinition(**entry)

                if class_def.id in classes:
                     logger.warning(f"Doppelte Klassen-ID '{class_def.id}' gefunden in {class_file.name}. Überschreibe!")
                classes[class_def.id] = class_def
            except (KeyError, TypeError) as e: # Fängt fehlende Keys oder falsche Typen bei Dataclass-Erstellung ab
                logger.error(f"Fehler beim Erstellen von CharacterClassDefinition für Eintrag {entry.get('id', 'N/A')} in {class_file.name}. Fehler: {e}")
                # raise # Fehler weitergeben oder nur loggen? Hier weitergeben.
                raise

    except FileNotFoundError:
         # Wird schon in load_json_file behandelt, aber fangen wir es hier nochmal ab
         logger.error(f"Charakterklassen-Datei nicht gefunden: {file_path}")
         raise
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Laden von {class_file.name} aufgetreten: {e}")
        raise

    logger.info(f"{len(classes)} Charakterklassen erfolgreich geladen.")
    return classes