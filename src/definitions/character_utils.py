"""
Character Utility Funktionen

Bietet Hilfsfunktionen zum Laden und Abrufen von Charakter- und Gegner-Templates.
"""
import os
import json
import json5
from typing import Dict, Optional, List, Any

from src.utils.logging_setup import get_logger
from src.definitions.character import CharacterTemplate, OpponentTemplate

# Logger für dieses Modul
logger = get_logger(__name__)

# Pfade zu den Template-Dateien
CHARACTER_TEMPLATES_PATH = os.path.join('src', 'definitions', 'json_data', 'characters.json5')
OPPONENT_TEMPLATES_PATH = os.path.join('src', 'definitions', 'json_data', 'opponents.json5')

# Caches für Templates
_character_templates_cache = {}
_opponent_templates_cache = {}


def _load_json5_file(file_path: str) -> Dict[str, Any]:
    """
    Lädt eine JSON5-Datei.
    
    Args:
        file_path (str): Der Pfad zur JSON5-Datei
        
    Returns:
        Dict[str, Any]: Der geladene Inhalt oder ein leeres Dictionary bei Fehler
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json5.load(f)
    except Exception as e:
        logger.error(f"Fehler beim Laden der JSON5-Datei {file_path}: {e}")
        return {}


def _load_character_templates() -> None:
    """Lädt alle Charakter-Templates aus der JSON5-Datei."""
    global _character_templates_cache
    
    if _character_templates_cache:  # Bereits geladen
        return
    
    data = _load_json5_file(CHARACTER_TEMPLATES_PATH)
    
    for template_id, template_data in data.items():
        try:
            _character_templates_cache[template_id] = CharacterTemplate.from_dict(
                char_id=template_id, 
                data=template_data
            )
        except Exception as e:
            logger.error(f"Fehler beim Laden des Charakter-Templates {template_id}: {e}")


def _load_opponent_templates() -> None:
    """Lädt alle Gegner-Templates aus der JSON5-Datei."""
    global _opponent_templates_cache
    
    if _opponent_templates_cache:  # Bereits geladen
        return
    
    data = _load_json5_file(OPPONENT_TEMPLATES_PATH)
    
    for template_id, template_data in data.items():
        try:
            _opponent_templates_cache[template_id] = OpponentTemplate.from_dict(
                opp_id=template_id, 
                data=template_data
            )
        except Exception as e:
            logger.error(f"Fehler beim Laden des Gegner-Templates {template_id}: {e}")


def get_character_template(template_id: str) -> Optional[CharacterTemplate]:
    """
    Gibt ein Charakter-Template anhand der ID zurück.
    
    Args:
        template_id (str): Die ID des Templates
        
    Returns:
        Optional[CharacterTemplate]: Das gefundene Template oder None, wenn nicht gefunden
    """
    _load_character_templates()
    
    template = _character_templates_cache.get(template_id)
    if not template:
        logger.warning(f"Charakter-Template mit ID {template_id} nicht gefunden!")
    
    return template


def get_opponent_template(template_id: str) -> Optional[OpponentTemplate]:
    """
    Gibt ein Gegner-Template anhand der ID zurück.
    
    Args:
        template_id (str): Die ID des Templates
        
    Returns:
        Optional[OpponentTemplate]: Das gefundene Template oder None, wenn nicht gefunden
    """
    _load_opponent_templates()
    
    template = _opponent_templates_cache.get(template_id)
    if not template:
        logger.warning(f"Gegner-Template mit ID {template_id} nicht gefunden!")
    
    return template


def get_all_character_templates() -> Dict[str, CharacterTemplate]:
    """
    Gibt alle verfügbaren Charakter-Templates zurück.
    
    Returns:
        Dict[str, CharacterTemplate]: Alle Charakter-Templates
    """
    _load_character_templates()
    return _character_templates_cache


def get_all_opponent_templates() -> Dict[str, OpponentTemplate]:
    """
    Gibt alle verfügbaren Gegner-Templates zurück.
    
    Returns:
        Dict[str, OpponentTemplate]: Alle Gegner-Templates
    """
    _load_opponent_templates()
    return _opponent_templates_cache
