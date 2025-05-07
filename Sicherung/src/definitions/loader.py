import json5
from pathlib import Path
import typing

# Importiere die Klassen, die wir instanziieren wollen
from .skill import Skill  # Relativer Import, da skill.py im selben Ordner liegt
from .character import Character # Relativer Import

# Pfad zum Verzeichnis mit den JSON5-Datendateien
DEFINITIONS_DIR = Path(__file__).parent / "json_data"

# Typ-Aliase für bessere Lesbarkeit der Rückgabewerte
SkillsDict = typing.Dict[str, Skill]
CharacterDefinitionsDict = typing.Dict[str, Character]

def _load_json_file(filename: str) -> typing.Dict[str, typing.Any]:
    """
    Eine Hilfsfunktion zum Laden und Parsen einer JSON5-Datei.

    Args:
        filename: Der Name der JSON5-Datei (ohne Pfad, z.B. "skills.json5").

    Returns:
        Ein Dictionary mit den Rohdaten aus der JSON5-Datei.

    Raises:
        FileNotFoundError: Wenn die Datei nicht im DEFINITIONS_DIR gefunden wird.
        json5.JSON5DecodeError: Wenn die Datei ungültiges JSON5 enthält.
        ValueError: Wenn die Datenstruktur nicht wie erwartet ist.
    """
    file_path = DEFINITIONS_DIR / filename
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json5.load(f)
        if not isinstance(data, dict):
             raise ValueError(f"Expected a dictionary at the top level of {filename}, but got {type(data)}")
        return data
    except FileNotFoundError:
        print(f"FEHLER: Definitionsdatei {file_path} nicht gefunden.")
        raise
    except json5.JSON5DecodeError as e:
        print(f"FEHLER: Fehler beim Parsen von {file_path}: {e}")
        raise
    except ValueError as e:
        print(f"FEHLER: Unerwartete Datenstruktur in {file_path}: {e}")
        raise


def load_skills() -> SkillsDict:
    """
    Lädt alle Skill-Definitionen aus skills.json5 und gibt sie
    als Dictionary von Skill-IDs zu Skill-Objekten zurück.
    """
    raw_skill_data = _load_json_file("skills.json5")
    skills: SkillsDict = {}
    for skill_id, data_dict in raw_skill_data.items(): # data umbenannt zu data_dict zur Klarheit
        try:
            skills[skill_id] = Skill(skill_id=skill_id, **data_dict)
        except TypeError as e:
            print(f"FEHLER beim Erstellen des Skill-Objekts für ID '{skill_id}': {e}")
            print(f"  Daten: {data_dict}")
    return skills

def load_character_classes() -> CharacterDefinitionsDict:
    """
    Lädt alle Charakterklassen-Definitionen aus characters.json5 und gibt sie
    als Dictionary von Klassen-IDs zu Character-Objekten zurück.
    """
    raw_class_data = _load_json_file("characters.json5")
    character_classes: CharacterDefinitionsDict = {}
    for class_id, data_dict in raw_class_data.items():
        try:
            # Bereite Argumente für Character-Konstruktor vor
            char_args = data_dict.copy() # Kopie, um Originaldaten nicht zu ändern
            if 'starting_skills' in char_args:
                # Mappe 'starting_skills' aus JSON auf 'skill_ids' für den Konstruktor
                char_args['skill_ids'] = char_args.pop('starting_skills')
            else:
                # Stelle sicher, dass skill_ids existiert, auch wenn leer (falls JSON es nicht hat)
                char_args.setdefault('skill_ids', [])

            character_classes[class_id] = Character(entity_id=class_id, **char_args)
        except TypeError as e:
            print(f"FEHLER beim Erstellen des Character-Objekts für Klassen-ID '{class_id}': {e}")
            print(f"  Übergebene Argumente an Character(): entity_id='{class_id}', {char_args}")
    return character_classes

def load_opponents() -> CharacterDefinitionsDict:
    """
    Lädt alle Gegner-Definitionen aus opponents.json5 und gibt sie
    als Dictionary von Gegner-IDs zu Character-Objekten zurück.
    """
    raw_opponent_data = _load_json_file("opponents.json5")
    opponents: CharacterDefinitionsDict = {}
    for opponent_id, data_dict in raw_opponent_data.items():
        try:
            # Bereite Argumente für Character-Konstruktor vor
            char_args = data_dict.copy()
            if 'skills' in char_args: # Gegner-JSON verwendet 'skills'
                # Mappe 'skills' aus JSON auf 'skill_ids' für den Konstruktor
                char_args['skill_ids'] = char_args.pop('skills')
            else:
                char_args.setdefault('skill_ids', [])

            opponents[opponent_id] = Character(entity_id=opponent_id, **char_args)
        except TypeError as e:
            print(f"FEHLER beim Erstellen des Character-Objekts für Gegner-ID '{opponent_id}': {e}")
            print(f"  Übergebene Argumente an Character(): entity_id='{opponent_id}', {char_args}")
    return opponents

# --- Globale Variablen für einfachen Zugriff (Lazy Loading) ---
_skills_cache: typing.Optional[SkillsDict] = None
_character_classes_cache: typing.Optional[CharacterDefinitionsDict] = None
_opponents_cache: typing.Optional[CharacterDefinitionsDict] = None

def get_all_skills() -> SkillsDict:
    global _skills_cache
    if _skills_cache is None:
        _skills_cache = load_skills()
    return _skills_cache

def get_skill(skill_id: str) -> typing.Optional[Skill]:
    return get_all_skills().get(skill_id)

def get_all_character_classes() -> CharacterDefinitionsDict:
    global _character_classes_cache
    if _character_classes_cache is None:
        _character_classes_cache = load_character_classes()
    return _character_classes_cache

def get_character_class(class_id: str) -> typing.Optional[Character]:
    return get_all_character_classes().get(class_id)

def get_all_opponents() -> CharacterDefinitionsDict:
    global _opponents_cache
    if _opponents_cache is None:
        _opponents_cache = load_opponents()
    return _opponents_cache

def get_opponent(opponent_id: str) -> typing.Optional[Character]:
    return get_all_opponents().get(opponent_id)


if __name__ == '__main__':
    print("Lade Skills...")
    skills = get_all_skills()
    if skills:
        first_skill_id = next(iter(skills.keys()), None)
        if first_skill_id:
            print(f"  Erfolgreich {len(skills)} Skill-Objekte geladen.")
            print(f"  Erstes Skill-Objekt: {skills[first_skill_id]}")
            print(f"    -> Kosten: {skills[first_skill_id].get_cost_amount()} {skills[first_skill_id].get_cost_resource()}")
        else:
            print("  Keine Skills geladen.")

    print("\nLade Charakterklassen...")
    character_classes = get_all_character_classes()
    if character_classes:
        first_class_id = next(iter(character_classes.keys()), None)
        if first_class_id:
            print(f"  Erfolgreich {len(character_classes)} Charakterklassen-Objekte geladen.")
            print(f"  Erstes Klassen-Objekt: {character_classes[first_class_id]}")
            if hasattr(character_classes[first_class_id], 'get_attribute'):
                 print(f"    -> STR: {character_classes[first_class_id].get_attribute('STR')}")
        else:
            print("  Keine Charakterklassen geladen.")


    print("\nLade Gegner...")
    opponents = get_all_opponents()
    if opponents:
        first_opponent_id = next(iter(opponents.keys()), None)
        if first_opponent_id:
            print(f"  Erfolgreich {len(opponents)} Gegner-Definitions-Objekte geladen.")
            print(f"  Erstes Gegner-Objekt: {opponents[first_opponent_id]}")
            if hasattr(opponents[first_opponent_id], 'get_attribute'):
                print(f"    -> CON: {opponents[first_opponent_id].get_attribute('CON')}")
            print(f"    -> XP: {opponents[first_opponent_id].xp_reward}")
        else:
            print("  Keine Gegner geladen.")


    print("\n--- Beispiel: Zugriff auf Skill 'fireball' ---")
    fireball = get_skill("fireball")
    if fireball:
        print(f"Gefunden: {fireball}")
        print(f"  Beschreibung: {fireball.description}")
    else:
        print("Skill 'fireball' nicht gefunden.")

