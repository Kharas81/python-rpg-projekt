import json5
from pathlib import Path
import typing

# Pfad zum Verzeichnis mit den JSON5-Datendateien
# Path(__file__).parent ergibt das Verzeichnis, in dem loader.py liegt (also src/definitions/)
# DEFINITIONS_DIR zeigt dann auf src/definitions/json_data/
DEFINITIONS_DIR = Path(__file__).parent / "json_data"

# Typ-Aliase für bessere Lesbarkeit
SkillData = typing.Dict[str, typing.Any]
CharacterClassData = typing.Dict[str, typing.Any]
OpponentData = typing.Dict[str, typing.Any]

def _load_json_file(filename: str) -> typing.Dict[str, typing.Any]:
    """
    Eine Hilfsfunktion zum Laden und Parsen einer JSON5-Datei.

    Args:
        filename: Der Name der JSON5-Datei (ohne Pfad, z.B. "skills.json5").

    Returns:
        Ein Dictionary mit den Daten aus der JSON5-Datei.

    Raises:
        FileNotFoundError: Wenn die Datei nicht im DEFINITIONS_DIR gefunden wird.
        json5.JSON5DecodeError: Wenn die Datei ungültiges JSON5 enthält.
    """
    file_path = DEFINITIONS_DIR / filename
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json5.load(f)
        return data
    except FileNotFoundError:
        print(f"FEHLER: Definitionsdatei {file_path} nicht gefunden.")
        raise
    except json5.JSON5DecodeError as e:
        print(f"FEHLER: Fehler beim Parsen von {file_path}: {e}")
        raise

def load_skills() -> typing.Dict[str, SkillData]:
    """Lädt alle Skill-Definitionen aus skills.json5."""
    # Die Daten in skills.json5 sind bereits ein Dictionary von Skill-IDs zu Skill-Daten
    return _load_json_file("skills.json5")

def load_character_classes() -> typing.Dict[str, CharacterClassData]:
    """Lädt alle Charakterklassen-Definitionen aus characters.json5."""
    # Die Daten in characters.json5 sind bereits ein Dictionary von Klassen-IDs zu Klassendaten
    return _load_json_file("characters.json5")

def load_opponents() -> typing.Dict[str, OpponentData]:
    """Lädt alle Gegner-Definitionen aus opponents.json5."""
    # Die Daten in opponents.json5 sind bereits ein Dictionary von Gegner-IDs zu Gegnerdaten
    return _load_json_file("opponents.json5")

if __name__ == '__main__':
    # Einfacher Test-Block, um die Ladefunktionen zu prüfen, wenn das Skript direkt ausgeführt wird
    print("Lade Skills...")
    skills = load_skills()
    if skills:
        print(f"  Erfolgreich {len(skills)} Skills geladen. Erster Skill: {next(iter(skills.keys()))}")

    print("\nLade Charakterklassen...")
    character_classes = load_character_classes()
    if character_classes:
        print(f"  Erfolgreich {len(character_classes)} Charakterklassen geladen. Erste Klasse: {next(iter(character_classes.keys()))}")

    print("\nLade Gegner...")
    opponents = load_opponents()
    if opponents:
        print(f"  Erfolgreich {len(opponents)} Gegner geladen. Erster Gegner: {next(iter(opponents.keys()))}")

    print("\n--- Beispiel Skill-Daten ---")
    if skills:
        example_skill_id = next(iter(skills.keys()))
        print(json5.dumps(skills[example_skill_id], indent=2, ensure_ascii=False, quote_keys=True))

