# src/definitions/loaders/__init__.py

# Importiert die Ladefunktionen, um sie einfacher verfügbar zu machen
# Beispiel: from definitions.loaders import load_stats_definitions, ...

from .stats_loader import load_stats_definitions_from_json
from .class_loader import load_character_classes_from_json
from .skill_loader import load_skills_from_json

# Optional: Definiere eine Funktion, die alles auf einmal lädt?
# from ..base_definitions import DefinitionsDatabase, ClassDatabase, SkillDatabase
# from pathlib import Path
#
# def load_all_definitions(base_data_path: str | Path) -> tuple[DefinitionsDatabase, ClassDatabase, SkillDatabase]:
#     """ Lädt alle Definitionstypen. """
#     json_data_path = Path(base_data_path) / 'json_data'
#     stats = load_stats_definitions_from_json(json_data_path)
#     classes = load_character_classes_from_json(json_data_path / 'character_classes.json')
#     skills = load_skills_from_json(json_data_path / 'skills.json')
#     return stats, classes, skills