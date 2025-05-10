"""
Loader für JSON5-Daten

Lädt JSON5-Dateien und konvertiert sie in Python-Objekte.
"""
import os
import json5
from typing import Dict, Any, List, Type, TypeVar, Optional

from .character import CharacterTemplate, OpponentTemplate
from .skill import SkillDefinition
from .item import ItemDefinition

# Type-Variable für generisches Laden
T = TypeVar('T')


def load_json5_file(filepath: str) -> Dict[str, Any]:
    """
    Lädt eine JSON5-Datei und gibt den Inhalt als Dictionary zurück.
    
    Args:
        filepath (str): Der Pfad zur JSON5-Datei
        
    Returns:
        Dict[str, Any]: Die geladenen Daten
        
    Raises:
        FileNotFoundError: Wenn die Datei nicht gefunden wird
        json5.Json5Error: Wenn die Datei kein gültiges JSON5 enthält
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"JSON5-Datei nicht gefunden: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as file:
        try:
            return json5.load(file)
        except Exception as e:
            raise json5.Json5Error(f"Fehler beim Laden der JSON5-Datei {filepath}: {str(e)}")


def load_templates(json_path: str, 
                  template_class: Type[T], 
                  prefix: Optional[str] = None) -> Dict[str, T]:
    """
    Lädt Templates aus einer JSON5-Datei.
    
    Args:
        json_path (str): Der Pfad zur JSON5-Datei
        template_class (Type[T]): Die Klasse, in die die Daten konvertiert werden sollen
        prefix (Optional[str]): Ein optionales Präfix für die IDs
        
    Returns:
        Dict[str, T]: Ein Dictionary mit den geladenen Templates
    """
    data = load_json5_file(json_path)
    results = {}
    
    for template_id, template_data in data.items():
        full_id = f"{prefix}_{template_id}" if prefix else template_id
        results[full_id] = template_class.from_dict(full_id, template_data)
    
    return results


def load_characters(json_path: str) -> Dict[str, CharacterTemplate]:
    """
    Lädt Charakterdefinitionen aus einer JSON5-Datei.
    
    Args:
        json_path (str): Der Pfad zur characters.json5
        
    Returns:
        Dict[str, CharacterTemplate]: Ein Dictionary mit den geladenen Charakteren
    """
    return load_templates(json_path, CharacterTemplate)


def load_opponents(json_path: str) -> Dict[str, OpponentTemplate]:
    """
    Lädt Gegnerdefinitionen aus einer JSON5-Datei.
    
    Args:
        json_path (str): Der Pfad zur opponents.json5
        
    Returns:
        Dict[str, OpponentTemplate]: Ein Dictionary mit den geladenen Gegnern
    """
    return load_templates(json_path, OpponentTemplate)


def load_skills(json_path: str) -> Dict[str, SkillDefinition]:
    """
    Lädt Skilldefinitionen aus einer JSON5-Datei.
    
    Args:
        json_path (str): Der Pfad zur skills.json5
        
    Returns:
        Dict[str, SkillDefinition]: Ein Dictionary mit den geladenen Skills
    """
    return load_templates(json_path, SkillDefinition)


def load_items(json_path: str) -> Dict[str, ItemDefinition]:
    """
    Lädt Itemdefinitionen aus einer JSON5-Datei.
    
    Args:
        json_path (str): Der Pfad zur items.json5
        
    Returns:
        Dict[str, ItemDefinition]: Ein Dictionary mit den geladenen Items
    """
    return load_templates(json_path, ItemDefinition)
