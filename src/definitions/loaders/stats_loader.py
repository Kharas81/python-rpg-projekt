# src/definitions/loaders/stats_loader.py

import logging
from pathlib import Path
from typing import Union, List, Dict, Any

# Nutze relativen Import für base_definitions und common
from ..base_definitions import StatDefinition, DefinitionsDatabase
from .common import load_json_file

logger = logging.getLogger(__name__)

# Liste der JSON-Dateien, die Stat-Definitionen enthalten
STAT_DEFINITION_FILES = [
    'primary_attributes.json',
    'resources.json',
    'combat_stats.json',
    'status_flags.json'
]

def load_stats_definitions_from_json(data_path: Union[str, Path]) -> DefinitionsDatabase:
    """
    Lädt Stat/Attribut/Ressource/Flag Definitionen aus spezifischen JSON-Dateien
    im angegebenen Verzeichnis.

    Args:
        data_path: Der Pfad zum Verzeichnis mit den JSON-Definitionsdateien
                   (z.B. src/definitions/json_data).

    Returns:
        Ein Dictionary, das Stat-IDs auf StatDefinition-Objekte abbildet.
    """
    definitions: DefinitionsDatabase = {}
    data_dir = Path(data_path)

    if not data_dir.is_dir():
        logger.error(f"Definitions-Pfad ist kein Verzeichnis: {data_path}")
        raise FileNotFoundError(f"Das angegebene Verzeichnis wurde nicht gefunden: {data_path}")

    logger.info(f"Lade Stat/Attr/Res/Flag-Definitionen aus: {data_dir.absolute()}")

    for filename in STAT_DEFINITION_FILES:
        file_path = data_dir / filename
        try:
            data = load_json_file(file_path) # Nutze die Hilfsfunktion
            if data is None: # Sollte durch Exception abgedeckt sein, aber zur Sicherheit
                continue

            if not isinstance(data, list):
                logger.warning(f"Unerwartetes Format in {file_path.name}. Erwartet: Liste. Überspringe Datei.")
                continue

            for entry in data:
                 if isinstance(entry, dict) and all(k in entry for k in ['id', 'name', 'description']):
                    try:
                        if not all(isinstance(entry[k], str) for k in ['id', 'name', 'description']):
                             logger.warning(f"Eintrag in {file_path.name} hat falsche Typen. Überspringe: {entry}")
                             continue

                        stat_def = StatDefinition(**entry) # Direkte Übergabe an Dataclass

                        if stat_def.id in definitions:
                            logger.warning(f"Doppelte Stat/Attr/Res/Flag-ID '{stat_def.id}' gefunden in {file_path.name}. Überschreibe!")
                        definitions[stat_def.id] = stat_def
                    except Exception as e: # Fängt z.B. TypeError bei Dataclass-Erstellung ab
                        logger.error(f"Fehler beim Erstellen von StatDefinition für Eintrag in {file_path.name}: {entry}. Fehler: {e}")
                        continue # Nächsten Eintrag versuchen
                 else:
                    pass # Ignoriere Einträge, die nicht wie StatDefinition aussehen

        except FileNotFoundError:
            logger.warning(f"Definitionsdatei '{filename}' nicht gefunden, übersprungen.")
        except Exception as e:
            logger.error(f"Konnte Stats aus Datei {filename} nicht laden. Fehler: {e}")
            # Hier ggf. entscheiden, ob der gesamte Ladevorgang abbrechen soll
            # raise # Um den Fehler nach oben zu geben

    if not definitions:
        logger.warning(f"Keine Stat/Attr/Res/Flag-Definitionen geladen aus: {data_dir.absolute()}")
    else:
        logger.info(f"{len(definitions)} Stat/Attr/Res/Flag-Definitionen erfolgreich geladen.")

    return definitions