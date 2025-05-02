# src/definitions/loader.py

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Union # Union hinzugefügt

from .base_definitions import DefinitionsDatabase, StatDefinition # Import aus gleicher Ebene

# Konfiguriere einen Logger speziell für dieses Modul
logger = logging.getLogger(__name__)

def load_definitions_from_json(data_path: Union[str, Path]) -> DefinitionsDatabase:
    """
    Lädt alle *.json Dateien aus dem angegebenen Verzeichnis und erstellt eine
    Datenbank (Dict) von StatDefinition-Objekten, wobei die ID der Schlüssel ist.

    Args:
        data_path: Der Pfad zum Verzeichnis mit den JSON-Definitionsdateien.

    Returns:
        Ein Dictionary, das Stat-IDs auf StatDefinition-Objekte abbildet.

    Raises:
        FileNotFoundError: Wenn der angegebene Pfad kein gültiges Verzeichnis ist.
        json.JSONDecodeError: Wenn eine JSON-Datei ungültig formatiert ist.
        KeyError: Wenn einem Eintrag in der JSON ein benötigtes Feld fehlt (id, name, description).
        TypeError: Wenn die JSON-Datei keine Liste von Objekten enthält.
    """
    definitions: DefinitionsDatabase = {}
    data_dir = Path(data_path)

    if not data_dir.is_dir():
        logger.error(f"Definitions-Pfad ist kein Verzeichnis: {data_path}")
        raise FileNotFoundError(f"Das angegebene Verzeichnis wurde nicht gefunden: {data_path}")

    logger.info(f"Lade Definitionen aus Verzeichnis: {data_dir.absolute()}")

    for file_path in data_dir.glob('*.json'):
        logger.debug(f"Verarbeite Definitionsdatei: {file_path.name}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.error(f"Unerwartetes Format in {file_path.name}. Erwartet: Liste von Objekten.")
                raise TypeError(f"Die Datei {file_path.name} muss eine Liste von Objekten enthalten.")

            for entry in data:
                try:
                    stat_def = StatDefinition(
                        id=entry['id'],
                        name=entry['name'],
                        description=entry['description']
                    )
                    if stat_def.id in definitions:
                        logger.warning(f"Doppelte ID '{stat_def.id}' gefunden in {file_path.name}. "
                                       f"Überschreibe vorherigen Eintrag aus einer anderen Datei!")
                    definitions[stat_def.id] = stat_def
                except KeyError as e:
                    logger.error(f"Fehlender Schlüssel {e} in einem Eintrag in {file_path.name}: {entry}")
                    raise # Fehler weitergeben
                except Exception as e:
                    logger.error(f"Fehler beim Erstellen von StatDefinition für Eintrag in {file_path.name}: {entry}. Fehler: {e}")
                    raise # Fehler weitergeben

        except json.JSONDecodeError as e:
            logger.error(f"Fehler beim Parsen von JSON in Datei: {file_path.name}. Fehler: {e}")
            raise # Fehler weitergeben
        except FileNotFoundError:
            logger.error(f"Datei nicht gefunden während des Ladens: {file_path.name}")
            raise # Fehler weitergeben
        except Exception as e:
            logger.error(f"Ein unerwarteter Fehler ist beim Laden von {file_path.name} aufgetreten: {e}")
            raise # Fehler weitergeben


    if not definitions:
        logger.warning(f"Keine Definitionen im Verzeichnis gefunden: {data_dir.absolute()}")
    else:
        logger.info(f"{len(definitions)} Definitionen erfolgreich geladen.")

    return definitions

# Beispielhafte Verwendung (kann später in main.py o.ä. erfolgen)
if __name__ == '__main__':
    # Einfaches Logging-Setup für Testzwecke
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Bestimme den Pfad zum json_data Ordner relativ zu dieser Datei
    # __file__ ist der Pfad zur loader.py -> .parent ist src/definitions -> .parent ist src -> 'definitions/json_data'
    definitions_path = Path(__file__).parent / 'json_data'

    try:
        all_definitions = load_definitions_from_json(definitions_path)
        print(f"\nGeladene Definitionen ({len(all_definitions)}):")
        for stat_id, stat_def in all_definitions.items():
            print(f"- ID: {stat_id}, Name: {stat_def.name}")

        # Zugriff auf eine spezifische Definition
        print("\nBeispiel Zugriff:")
        strength_def = all_definitions.get("STR")
        if strength_def:
            print(strength_def)
        else:
            print("Definition für 'STR' nicht gefunden.")

    except Exception as e:
        print(f"\nFehler beim Laden der Definitionen: {e}")