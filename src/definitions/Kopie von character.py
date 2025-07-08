# src/definitions/character.py
"""
Definiert die Datenstruktur für Charakter-Templates, die aus JSON5-Dateien geladen werden.
"""
from typing import List, Dict, Optional

class CharacterTemplate:
    """
    Repräsentiert die Definition einer Charakterklasse (Template),
    wie sie in characters.json5 definiert ist.
    """
    def __init__(self,
                 id: str,
                 name: str,
                 description: str,
                 base_hp: int,
                 primary_attributes: Dict[str, int],
                 combat_values: Dict[str, int],
                 starting_skills: List[str],
                 resource_type: str,
                 asset_key: Optional[str] = None): # Hinzugefügter Parameter
        
        self.id: str = id
        self.name: str = name
        self.description: str = description
        self.asset_key = asset_key # Hinzugefügte Zuweisung
        
        self.base_hp: int = base_hp
        self.primary_attributes: Dict[str, int] = primary_attributes
        self.combat_values: Dict[str, int] = combat_values
        self.starting_skills: List[str] = starting_skills
        self.resource_type: str = resource_type

    def __repr__(self) -> str:
        return (f"CharacterTemplate(id='{self.id}', name='{self.name}', "
                f"base_hp={self.base_hp}, resource='{self.resource_type}')")