# src/definitions/loader.py
"""
Lädt Spieldefinitionen (Charaktere, Skills, etc.) aus JSON5-Dateien.
"""
import json5
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Importiere die Template-Klassen aus den benachbarten Modulen
# Wir gehen davon aus, dass loader.py im selben Verzeichnis (definitions) wie character.py und skill.py liegt.
try:
    from .character import CharacterTemplate #, validate_character_data (optional, da Validierung im Konstruktor)
    from .skill import SkillTemplate #, validate_skill_data (optional)
except ImportError:
    # Fallback für den Fall, dass das Skript direkt ausgeführt wird und der relative Import fehlschlägt
    from character import CharacterTemplate
    from skill import SkillTemplate

# Standardpfad zum json_data Verzeichnis, relativ zu diesem loader.py Skript
# Später könnten wir diesen Pfad auch aus einer globalen Konfiguration (settings.json5) beziehen.
DEFAULT_DATA_DIR = Path(__file__).parent / "json_data"
logger = logging.getLogger(__name__) # Erstellt einen Logger für dieses Modul

def _load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Private Hilfsfunktion zum Laden und Parsen einer einzelnen JSON5-Datei.

    Args:
        file_path (Path): Der Pfad zur JSON5-Datei.

    Returns:
        List[Dict[str, Any]]: Eine Liste von Dictionaries, die aus der JSON5-Datei geladen wurden.
                               Gibt eine leere Liste zurück, wenn die Datei nicht existiert oder
                               ein Fehler beim Parsen auftritt.
    """
    if not file_path.is_file():
        logger.error(f"Definitionsdatei nicht gefunden: {file_path}")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json5.load(f)
        if not isinstance(data, list):
            logger.error(f"JSON-Daten in {file_path} sind keine Liste von Objekten.")
            return []
        return data
    except json5.JSONDecodeError as e:
        logger.error(f"Fehler beim Parsen der JSON5-Datei {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Lesen von {file_path} aufgetreten: {e}")
        return []

def load_character_templates(data_dir: Path = DEFAULT_DATA_DIR) -> Dict[str, CharacterTemplate]:
    """
    Lädt Charakter-Vorlagen aus der 'characters.json5'-Datei im angegebenen Verzeichnis.

    Args:
        data_dir (Path, optional): Das Verzeichnis, in dem sich 'characters.json5' befindet.
                                   Standard ist DEFAULT_DATA_DIR.

    Returns:
        Dict[str, CharacterTemplate]: Ein Dictionary von Charakter-Vorlagen,
                                      wobei die ID des Charakters der Schlüssel ist.
    """
    character_file = data_dir / "characters.json5"
    raw_character_data = _load_json_file(character_file)
    character_templates: Dict[str, CharacterTemplate] = {}

    for entry in raw_character_data:
        if not isinstance(entry, dict):
            logger.warning(f"Ungültiger Eintrag in {character_file} übersprungen (kein Dictionary): {entry}")
            continue
        try:
            # Die Validierung der erforderlichen Schlüssel und Typen erfolgt
            # größtenteils im Konstruktor von CharacterTemplate.
            # if not validate_character_data(entry): # Optionale zusätzliche Validierung hier
            #     logger.warning(f"Ungültige Charakterdaten in {character_file} übersprungen: {entry.get('id', 'UNKNOWN_ID')}")
            #     continue
            template = CharacterTemplate(**entry) # Entpackt das Dictionary als Keyword-Argumente
            if template.id in character_templates:
                logger.warning(f"Doppelte Charakter-ID '{template.id}' in {character_file} gefunden. Überschreibe vorherigen Eintrag.")
            character_templates[template.id] = template
        except ValueError as e:
            logger.warning(f"Fehler beim Erstellen des CharacterTemplate für ID '{entry.get('id', 'NO_ID')}' "
                           f"aus {character_file}: {e}. Eintrag wird übersprungen.")
        except TypeError as e: # Fängt Fehler bei falschen Argumenten für den Konstruktor ab
             logger.warning(f"Typfehler beim Erstellen des CharacterTemplate für ID '{entry.get('id', 'NO_ID')}' "
                           f"aus {character_file} (möglicherweise falsche/fehlende Schlüssel in JSON): {e}. Eintrag wird übersprungen.")
    logger.info(f"{len(character_templates)} Charakter-Vorlagen erfolgreich aus {character_file} geladen.")
    return character_templates

def load_skill_templates(data_dir: Path = DEFAULT_DATA_DIR) -> Dict[str, SkillTemplate]:
    """
    Lädt Skill-Vorlagen aus der 'skills.json5'-Datei im angegebenen Verzeichnis.

    Args:
        data_dir (Path, optional): Das Verzeichnis, in dem sich 'skills.json5' befindet.
                                   Standard ist DEFAULT_DATA_DIR.

    Returns:
        Dict[str, SkillTemplate]: Ein Dictionary von Skill-Vorlagen,
                                  wobei die ID des Skills der Schlüssel ist.
    """
    skill_file = data_dir / "skills.json5"
    raw_skill_data = _load_json_file(skill_file)
    skill_templates: Dict[str, SkillTemplate] = {}

    for entry in raw_skill_data:
        if not isinstance(entry, dict):
            logger.warning(f"Ungültiger Eintrag in {skill_file} übersprungen (kein Dictionary): {entry}")
            continue
        try:
            # Die Validierung der erforderlichen Schlüssel und Typen erfolgt
            # größtenteils im Konstruktor von SkillTemplate.
            template = SkillTemplate(**entry)
            if template.id in skill_templates:
                logger.warning(f"Doppelte Skill-ID '{template.id}' in {skill_file} gefunden. Überschreibe vorherigen Eintrag.")
            skill_templates[template.id] = template
        except ValueError as e:
            logger.warning(f"Fehler beim Erstellen des SkillTemplate für ID '{entry.get('id', 'NO_ID')}' "
                           f"aus {skill_file}: {e}. Eintrag wird übersprungen.")
        except TypeError as e:
             logger.warning(f"Typfehler beim Erstellen des SkillTemplate für ID '{entry.get('id', 'NO_ID')}' "
                           f"aus {skill_file} (möglicherweise falsche/fehlende Schlüssel in JSON): {e}. Eintrag wird übersprungen.")
    logger.info(f"{len(skill_templates)} Skill-Vorlagen erfolgreich aus {skill_file} geladen.")
    return skill_templates

def load_all_definitions(data_dir: Path = DEFAULT_DATA_DIR) -> Tuple[Dict[str, CharacterTemplate], Dict[str, SkillTemplate]]:
    """
    Lädt alle Basis-Definitionen (Charaktere und Skills).

    Args:
        data_dir (Path, optional): Das Verzeichnis, das die JSON5-Datendateien enthält.
                                   Standard ist DEFAULT_DATA_DIR.

    Returns:
        Tuple[Dict[str, CharacterTemplate], Dict[str, SkillTemplate]]:
            Ein Tupel, das die geladenen Charakter-Vorlagen und Skill-Vorlagen enthält.
    """
    logger.info(f"Lade alle Definitionen aus Verzeichnis: {data_dir}")
    character_templates = load_character_templates(data_dir)
    skill_templates = load_skill_templates(data_dir)
    logger.info("Alle Basis-Definitionen geladen.")
    return character_templates, skill_templates

if __name__ == '__main__':
    # Dieser Block wird nur ausgeführt, wenn loader.py direkt als Skript gestartet wird.
    # Dient zum schnellen Testen des Laders.
    # Für ein richtiges Logging müsste logging_setup.py bereits konfiguriert sein.
    # Da wir das noch nicht haben, verwenden wir basicConfig für eine einfache Konsolenausgabe.
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    logger.info("Starte Testlauf für den Definitionslader...")
    # Verwende den Standardpfad, der relativ zu diesem Skript ist
    # oder gib einen expliziten Pfad an, z.B. Path("src/definitions/json_data")
    # wenn du das Skript vom Projekt-Root-Verzeichnis aus startest.
    # Für diesen Test gehen wir davon aus, dass json_data neben loader.py liegt.

    loaded_characters, loaded_skills = load_all_definitions()

    if loaded_characters:
        logger.info("\nGeladene Charaktere:")
        for char_id, char_template in loaded_characters.items():
            logger.info(f"  ID: {char_id}, Name: {char_template.name}, Attribute: {char_template.attributes}, Skills: {char_template.skills}")
    else:
        logger.warning("Keine Charaktere geladen.")

    if loaded_skills:
        logger.info("\nGeladene Skills:")
        for skill_id, skill_template in loaded_skills.items():
            logger.info(f"  ID: {skill_id}, Name: {skill_template.name}, Kosten: {skill_template.cost}, Effekte: {skill_template.effects}")
    else:
        logger.warning("Keine Skills geladen.")

    logger.info("\nTestlauf für Definitionslader beendet.")