# src/definitions/loader.py

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Union, Any # Union und Any hinzugefügt

# Importiere alle Definitionen und Datenbank-Typen
from .base_definitions import (
    StatDefinition, DefinitionsDatabase,
    CharacterClassDefinition, ClassDatabase,
    EffectDefinition, SkillDefinition, SkillDatabase
)

# Konfiguriere einen Logger speziell für dieses Modul
logger = logging.getLogger(__name__)


def load_definitions_from_json(data_path: Union[str, Path]) -> DefinitionsDatabase:
    """
    Lädt alle Stat/Attribut/Ressource/Flag *.json Dateien aus dem angegebenen
    Verzeichnis und erstellt eine Datenbank (Dict) von StatDefinition-Objekten,
    wobei die ID der Schlüssel ist. Ignoriert Dateien, die nicht StatDefinitions sind.

    Args:
        data_path: Der Pfad zum Verzeichnis mit den JSON-Definitionsdateien
                   (z.B. src/definitions/json_data).

    Returns:
        Ein Dictionary, das Stat-IDs auf StatDefinition-Objekte abbildet.

    Raises:
        FileNotFoundError: Wenn der angegebene Pfad kein gültiges Verzeichnis ist.
        json.JSONDecodeError: Wenn eine JSON-Datei ungültig formatiert ist.
        KeyError: Wenn einem Eintrag in der JSON ein benötigtes Feld fehlt (id, name, description).
        TypeError: Wenn die JSON-Datei keine Liste von Objekten enthält oder Objekte falsche Typen haben.
    """
    definitions: DefinitionsDatabase = {}
    data_dir = Path(data_path)

    if not data_dir.is_dir():
        logger.error(f"Definitions-Pfad ist kein Verzeichnis: {data_path}")
        raise FileNotFoundError(f"Das angegebene Verzeichnis wurde nicht gefunden: {data_path}")

    logger.info(f"Lade Stat/Attr/Res/Flag-Definitionen aus Verzeichnis: {data_dir.absolute()}")

    # Filtere relevante Dateien (könnte man auch über Namen machen, z.B. *_stats.json)
    # Hier laden wir erstmal alle und prüfen den Inhalt grob
    files_to_load = [
        'primary_attributes.json',
        'resources.json',
        'combat_stats.json',
        'status_flags.json'
        # Füge hier ggf. weitere hinzu oder nutze glob('*.json') und prüfe den Inhalt genauer
    ]

    for filename in files_to_load:
        file_path = data_dir / filename
        if not file_path.is_file():
            logger.warning(f"Definitionsdatei '{filename}' nicht im Verzeichnis gefunden, überspringe.")
            continue

        logger.debug(f"Verarbeite Definitionsdatei: {file_path.name}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.warning(f"Unerwartetes Format in {file_path.name}. Erwartet: Liste. Überspringe Datei.")
                continue # Ignoriere Dateien mit falschem Top-Level-Typ

            for entry in data:
                 # Prüfe, ob es wie eine StatDefinition aussieht (hat id, name, description)
                 if isinstance(entry, dict) and all(k in entry for k in ['id', 'name', 'description']):
                    try:
                        # Prüfe, ob Felder korrekte Typen haben (rudimentär)
                        if not all(isinstance(entry[k], str) for k in ['id', 'name', 'description']):
                             logger.warning(f"Eintrag in {file_path.name} hat falsche Typen für id/name/description. Überspringe Eintrag: {entry}")
                             continue

                        stat_def = StatDefinition(
                            id=entry['id'],
                            name=entry['name'],
                            description=entry['description']
                        )
                        if stat_def.id in definitions:
                            logger.warning(f"Doppelte Stat/Attr/Res/Flag-ID '{stat_def.id}' gefunden in {file_path.name}. "
                                           f"Überschreibe vorherigen Eintrag!")
                        definitions[stat_def.id] = stat_def
                    except KeyError as e: # Sollte durch Check oben abgedeckt sein, aber sicher ist sicher
                        logger.error(f"Fehlender Schlüssel {e} in einem Stat-Eintrag in {file_path.name}: {entry}")
                        # Hier nicht abbrechen, nur diesen Eintrag überspringen? Oder doch Fehler werfen?
                        # raise # Fehler weitergeben
                        continue # Eintrag überspringen
                    except Exception as e:
                        logger.error(f"Fehler beim Erstellen von StatDefinition für Eintrag in {file_path.name}: {entry}. Fehler: {e}")
                        # raise # Fehler weitergeben
                        continue # Eintrag überspringen
                 else:
                     # Eintrag sieht nicht wie eine StatDefinition aus, ignorieren
                     # logger.debug(f"Eintrag in {file_path.name} ist keine StatDefinition. Überspringe: {entry}")
                     pass


        except json.JSONDecodeError as e:
            logger.error(f"Fehler beim Parsen von JSON in Datei: {file_path.name}. Fehler: {e}")
            raise # Fehler weitergeben
        except Exception as e:
            logger.error(f"Ein unerwarteter Fehler ist beim Laden von {file_path.name} aufgetreten: {e}")
            raise # Fehler weitergeben


    if not definitions:
        logger.warning(f"Keine Stat/Attr/Res/Flag-Definitionen im Verzeichnis gefunden oder geladen: {data_dir.absolute()}")
    else:
        logger.info(f"{len(definitions)} Stat/Attr/Res/Flag-Definitionen erfolgreich geladen.")

    return definitions


def load_character_classes_from_json(file_path: Union[str, Path]) -> ClassDatabase:
    """
    Lädt Charakterklassen-Definitionen aus der angegebenen JSON-Datei.

    Args:
        file_path: Der Pfad zur JSON-Datei mit den Klassendefinitionen.

    Returns:
        Ein Dictionary, das Klassen-IDs auf CharacterClassDefinition-Objekte abbildet.

    Raises:
        FileNotFoundError, json.JSONDecodeError, KeyError, TypeError
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
                 # Rudimentäre Typ-Checks für Klassen-Daten
                if not isinstance(entry.get('base_stats'), dict):
                     raise TypeError("'base_stats' fehlt oder ist kein Dictionary")
                if not isinstance(entry.get('starting_skills'), list):
                     raise TypeError("'starting_skills' fehlt oder ist keine Liste")

                class_def = CharacterClassDefinition(
                    id=entry['id'],
                    name=entry['name'],
                    description=entry['description'],
                    base_stats=entry['base_stats'],
                    starting_skills=entry['starting_skills']
                )
                if class_def.id in classes:
                     logger.warning(f"Doppelte Klassen-ID '{class_def.id}' gefunden in {class_file.name}. Überschreibe!")
                classes[class_def.id] = class_def
            except KeyError as e:
                logger.error(f"Fehlender Schlüssel {e} in einem Klasseneintrag in {class_file.name}: {entry}")
                raise
            except TypeError as e:
                 logger.error(f"Typfehler in Datenstruktur für Klasseneintrag {entry.get('id', 'N/A')} in {class_file.name}. Fehler: {e}")
                 raise
            except Exception as e:
                logger.error(f"Fehler beim Erstellen von CharacterClassDefinition für Eintrag {entry.get('id', 'N/A')} in {class_file.name}. Fehler: {e}")
                raise

    except json.JSONDecodeError as e:
        logger.error(f"Fehler beim Parsen von JSON in Datei: {class_file.name}. Fehler: {e}")
        raise
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Laden von {class_file.name} aufgetreten: {e}")
        raise

    logger.info(f"{len(classes)} Charakterklassen erfolgreich geladen.")
    return classes


def load_skills_from_json(file_path: Union[str, Path]) -> SkillDatabase:
    """
    Lädt Skill-Definitionen aus der angegebenen JSON-Datei.

    Args:
        file_path: Der Pfad zur JSON-Datei mit den Skilldefinitionen.

    Returns:
        Ein Dictionary, das Skill-IDs auf SkillDefinition-Objekte abbildet.

    Raises:
        FileNotFoundError, json.JSONDecodeError, KeyError, TypeError
    """
    skills: SkillDatabase = {}
    skill_file = Path(file_path)

    logger.info(f"Lade Skills aus Datei: {skill_file.absolute()}")

    if not skill_file.is_file():
        logger.error(f"Skill-Datei nicht gefunden: {file_path}")
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.error(f"Unerwartetes Format in {skill_file.name}. Erwartet: Liste von Objekten.")
            raise TypeError(f"Die Datei {skill_file.name} muss eine Liste von Objekten enthalten.")

        for entry in data:
            skill_id = entry.get('id', 'N/A') # Für Fehlermeldungen
            try:
                loaded_effects = []
                if 'effects' in entry and isinstance(entry['effects'], list):
                    for effect_data in entry['effects']:
                        if not isinstance(effect_data, dict):
                             logger.warning(f"Ungültiger Effekt-Eintrag (kein Dict) in Skill '{skill_id}'. Überspringe Effekt: {effect_data}")
                             continue
                        try:
                             # Erstelle EffectDefinition Objekt, nutze Defaults für fehlende Felder
                             effect = EffectDefinition(**effect_data)
                             loaded_effects.append(effect)
                        except TypeError as te:
                             # Fängt Fehler ab, wenn z.B. ein Feld im JSON einen falschen Typ hat oder unerwartet ist
                             logger.error(f"Typfehler beim Erstellen von EffectDefinition für Effekt in Skill '{skill_id}': {effect_data}. Fehler: {te}")
                             raise # Fehler weitergeben, um Problem zu signalisieren
                else:
                     logger.warning(f"Skill '{skill_id}' hat keine 'effects'-Liste oder sie ist ungültig.")

                # Rudimentäre Typ-Checks für Skill-Daten
                if not isinstance(entry.get('cost'), dict):
                     raise TypeError("'cost' fehlt oder ist kein Dictionary")
                if not isinstance(entry.get('target'), str):
                     raise TypeError("'target' fehlt oder ist kein String")

                skill_def = SkillDefinition(
                    id=entry['id'],
                    name=entry['name'],
                    description=entry['description'],
                    cost=entry['cost'], # Typ-Check oben
                    target=entry['target'], # Typ-Check oben
                    effects=loaded_effects
                )

                if skill_def.id in skills:
                     logger.warning(f"Doppelte Skill-ID '{skill_def.id}' gefunden in {skill_file.name}. Überschreibe!")
                skills[skill_def.id] = skill_def

            except KeyError as e:
                logger.error(f"Fehlender Schlüssel {e} in einem Skill-Eintrag ('{skill_id}') in {skill_file.name}: {entry}")
                raise
            except TypeError as e:
                 logger.error(f"Typfehler in Datenstruktur für Skill-Eintrag '{skill_id}' in {skill_file.name}. Fehler: {e}")
                 raise
            except Exception as e:
                logger.error(f"Fehler beim Erstellen von SkillDefinition für Eintrag '{skill_id}' in {skill_file.name}. Fehler: {e}")
                raise

    except json.JSONDecodeError as e:
        logger.error(f"Fehler beim Parsen von JSON in Datei: {skill_file.name}. Fehler: {e}")
        raise
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Laden von {skill_file.name} aufgetreten: {e}")
        raise

    logger.info(f"{len(skills)} Skills erfolgreich geladen.")
    return skills


# --- Beispielhafte Verwendung (wird ausgeführt, wenn man python src/definitions/loader.py startet) ---
if __name__ == '__main__':
    # === Einfaches Logging-Setup NUR für diesen Test ===
    # In einer echten Anwendung wird das Logging zentral konfiguriert!
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=log_format) # DEBUG für ausführliche Lade-Infos
    # === Ende Logging Setup ===

    # Pfade definieren (relativ zur loader.py)
    base_path = Path(__file__).parent # src/definitions
    json_data_path = base_path / 'json_data'
    classes_file_path = json_data_path / 'character_classes.json'
    skills_file_path = json_data_path / 'skills.json'

    # --- Laden ---
    all_stats: Optional[DefinitionsDatabase] = None
    all_classes: Optional[ClassDatabase] = None
    all_skills: Optional[SkillDatabase] = None
    load_error = False

    print("\n--- Lade Stats/Attributes/Resources/Flags ---")
    try:
        all_stats = load_definitions_from_json(json_data_path)
        print(f"-> {len(all_stats)} Definitionen geladen.")
    except Exception as e:
        print(f"FEHLER beim Laden der Stats/etc.: {e}")
        load_error = True

    print("\n--- Lade Charakterklassen ---")
    try:
        all_classes = load_character_classes_from_json(classes_file_path)
        print(f"-> {len(all_classes)} Klassen geladen.")
    except Exception as e:
        print(f"FEHLER beim Laden der Klassen: {e}")
        load_error = True

    print("\n--- Lade Skills ---")
    try:
        all_skills = load_skills_from_json(skills_file_path)
        print(f"-> {len(all_skills)} Skills geladen.")
    except Exception as e:
        print(f"FEHLER beim Laden der Skills: {e}")
        load_error = True

    # --- Beispielhafter Zugriff (nur wenn Laden erfolgreich war) ---
    if not load_error and all_stats and all_classes and all_skills:
        print("\n--- Beispiel Zugriffe ---")

        # Stat
        strength_def = all_stats.get("STR")
        if strength_def:
            print(f"Stat gefunden: {strength_def.name}")
        else:
            print("Stat 'STR' nicht gefunden.")

        # Klasse
        cleric = all_classes.get("CLERIC")
        if cleric:
            print(f"Klasse gefunden: {cleric.name}")
            print(f"  Basis-HP: {cleric.base_stats.get('HP', 'N/A')}")
            print(f"  Start-Skills: {cleric.starting_skills}")
        else:
            print("Klasse 'CLERIC' nicht gefunden.")

        # Skill
        heal_skill = all_skills.get("heal")
        if heal_skill:
            print(f"Skill gefunden: {heal_skill.name} ({heal_skill.id})")
            print(f"  Kosten: {heal_skill.cost}")
            for effect in heal_skill.effects:
                 print(f"  Effekt: {effect}")
        else:
            print("Skill 'heal' nicht gefunden.")
    elif not load_error:
         print("\nLaden war fehlerfrei, aber eine der Datenbanken ist leer oder None.")
    else:
         print("\nLaden fehlgeschlagen, siehe Fehler oben.")
         print("Führe das Skript erneut aus, um den Traceback zu sehen, wenn ein Fehler auftritt.")
         # Bei einem Fehler ist es oft hilfreich, den vollen Traceback zu sehen
         # import traceback
         # traceback.print_exc() # Wird jetzt oben im except Block behandelt