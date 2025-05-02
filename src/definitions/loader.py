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

def load_character_classes_from_json(file_path: Union[str, Path]) -> ClassDatabase:
    """
    Lädt Charakterklassen-Definitionen aus der angegebenen JSON-Datei.

    Args:
        file_path: Der Pfad zur JSON-Datei mit den Klassendefinitionen.

    Returns:
        Ein Dictionary, das Klassen-IDs auf CharacterClassDefinition-Objekte abbildet.

    Raises:
        FileNotFoundError: Wenn die angegebene Datei nicht gefunden wird.
        json.JSONDecodeError: Wenn die JSON-Datei ungültig formatiert ist.
        KeyError: Wenn einem Eintrag in der JSON ein benötigtes Feld fehlt.
        TypeError: Wenn die JSON-Datei keine Liste von Objekten enthält.
    """
    classes: ClassDatabase = {}
    class_file = Path(file_path)

    logger.info(f"Lade Charakterklassen aus Datei: {class_file.absolute()}")

    if not class_file.is_file():
        logger.error(f"Charakterklassen-Datei nicht gefunden: {file_path}")
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

    try:
        with open(class_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.error(f"Unerwartetes Format in {class_file.name}. Erwartet: Liste von Objekten.")
            raise TypeError(f"Die Datei {class_file.name} muss eine Liste von Objekten enthalten.")

        for entry in data:
            try:
                class_def = CharacterClassDefinition(
                    id=entry['id'],
                    name=entry['name'],
                    description=entry['description'],
                    base_stats=entry['base_stats'], # Erwartet ein Dict[str, int]
                    starting_skills=entry['starting_skills'] # Erwartet eine List[str]
                )
                if class_def.id in classes:
                     logger.warning(f"Doppelte Klassen-ID '{class_def.id}' gefunden in {class_file.name}. "
                                   f"Überschreibe vorherigen Eintrag!")
                classes[class_def.id] = class_def
            except KeyError as e:
                logger.error(f"Fehlender Schlüssel {e} in einem Klasseneintrag in {class_file.name}: {entry}")
                raise
            except TypeError as e:
                 logger.error(f"Typfehler in Datenstruktur für Klasseneintrag in {class_file.name}: {entry}. Fehler: {e}")
                 raise
            except Exception as e:
                logger.error(f"Fehler beim Erstellen von CharacterClassDefinition für Eintrag in {class_file.name}: {entry}. Fehler: {e}")
                raise

    except json.JSONDecodeError as e:
        logger.error(f"Fehler beim Parsen von JSON in Datei: {class_file.name}. Fehler: {e}")
        raise
    except FileNotFoundError: # Redundant durch Check oben, aber sicher ist sicher
        logger.error(f"Datei nicht gefunden während des Ladens: {class_file.name}")
        raise
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Laden von {class_file.name} aufgetreten: {e}")
        raise

    logger.info(f"{len(classes)} Charakterklassen erfolgreich geladen.")
    return classes

# --- Optional: Test-Block aktualisieren ---
# Wenn du den `if __name__ == '__main__':`-Block in loader.py zum Testen verwendest,
# könntest du ihn so erweitern, dass er beide Ladefunktionen aufruft:

if __name__ == '__main__':
    # Einfaches Logging-Setup für Testzwecke
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Pfade definieren (relativ zur loader.py)
    base_path = Path(__file__).parent
    definitions_path = base_path / 'json_data'
    classes_file_path = base_path / 'json_data' / 'character_classes.json'

    try:
        # Stats laden
        all_stats = load_definitions_from_json(definitions_path)
        print(f"\n--- Stats Geladen ({len(all_stats)}) ---")
        # Optional: Einzelne Stats ausgeben
        # for stat_id, stat_def in all_stats.items():
        #     print(f"- {stat_def.name} ({stat_id})")

        # Klassen laden
        all_classes = load_character_classes_from_json(classes_file_path)
        print(f"\n--- Klassen Geladen ({len(all_classes)}) ---")
        # Optional: Einzelne Klassen ausgeben
        for class_id, class_def in all_classes.items():
             print(f"- {class_def.name} ({class_id})")
             # print(class_def) # Gibt die ausführliche __str__ Repräsentation aus

        # Beispielhafter Zugriff
        print("\n--- Beispiel Zugriff ---")
        warrior = all_classes.get("WARRIOR")
        if warrior:
            print(f"Krieger Basis-STR: {warrior.base_stats.get('STR', 'N/A')}")
            print(f"Krieger Start-Skills: {warrior.starting_skills}")
        else:
             print("Klasse 'WARRIOR' nicht gefunden.")


    except Exception as e:
        print(f"\nFEHLER beim Laden der Definitionen im Test: {e}")
        # Bei einem Fehler hier ist es oft hilfreich, den vollen Traceback zu sehen
        import traceback
        traceback.print_exc()


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