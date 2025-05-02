# src/definitions/loaders/skill_loader.py

import logging
from pathlib import Path
from typing import Union, List, Dict, Any

# Nutze relativen Import für base_definitions und common
from ..base_definitions import EffectDefinition, SkillDefinition, SkillDatabase
from .common import load_json_file

logger = logging.getLogger(__name__)

def load_skills_from_json(file_path: Union[str, Path]) -> SkillDatabase:
    """
    Lädt Skill-Definitionen aus der angegebenen JSON-Datei.
    """
    skills: SkillDatabase = {}
    skill_file = Path(file_path)

    logger.info(f"Lade Skills aus Datei: {skill_file.absolute()}")

    try:
        data = load_json_file(skill_file) # Nutze die Hilfsfunktion
        if data is None:
            return skills # Keine Daten geladen

        if not isinstance(data, list):
            logger.error(f"Unerwartetes Format in {skill_file.name}. Erwartet: Liste.")
            raise TypeError(f"Die Datei {skill_file.name} muss eine Liste von Objekten enthalten.")

        for entry in data:
            skill_id = entry.get('id', 'N/A') # Für Fehlermeldungen
            if not isinstance(entry, dict):
                 logger.warning(f"Ungültiger Skill-Eintrag (kein Dict) in {skill_file.name}. Überspringe: {entry}")
                 continue
            try:
                loaded_effects = []
                if 'effects' in entry and isinstance(entry['effects'], list):
                    for effect_data in entry['effects']:
                        if not isinstance(effect_data, dict):
                             logger.warning(f"Ungültiger Effekt-Eintrag (kein Dict) in Skill '{skill_id}'. Überspringe: {effect_data}")
                             continue
                        try:
                             effect = EffectDefinition(**effect_data)
                             loaded_effects.append(effect)
                        except TypeError as te:
                             logger.error(f"Typfehler beim Erstellen von EffectDefinition für Effekt in Skill '{skill_id}': {effect_data}. Fehler: {te}")
                             raise # Fehler weitergeben

                # Verlassen uns auf Dataclass für Typ-Checks der Hauptfelder
                skill_def = SkillDefinition(
                    id=entry['id'],
                    name=entry['name'],
                    description=entry['description'],
                    cost=entry.get('cost', {}),
                    target=entry['target'],
                    effects=loaded_effects
                )

                if skill_def.id in skills:
                     logger.warning(f"Doppelte Skill-ID '{skill_def.id}' gefunden in {skill_file.name}. Überschreibe!")
                skills[skill_def.id] = skill_def

            except (KeyError, TypeError) as e: # Fängt fehlende Keys oder falsche Typen bei Dataclass-Erstellung ab
                logger.error(f"Fehler beim Erstellen von SkillDefinition für Eintrag '{skill_id}' in {skill_file.name}. Fehler: {e}")
                raise

    except FileNotFoundError:
         logger.error(f"Skill-Datei nicht gefunden: {file_path}")
         raise
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Laden von {skill_file.name} aufgetreten: {e}")
        raise

    logger.info(f"{len(skills)} Skills erfolgreich geladen.")
    return skills