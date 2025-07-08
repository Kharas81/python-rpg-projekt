# src/definitions/opponent.py
"""
Definiert die Datenstruktur für Gegner-Templates, die aus JSON5-Dateien geladen werden.
"""
from typing import List, Dict, Optional

class OpponentTemplate:
    """
    Repräsentiert die Definition eines Gegnertyps (Template),
    wie sie in opponents.json5 definiert ist.
    """
    def __init__(self,
                 id: str,
                 name: str,
                 description: str,
                 level: int,
                 base_hp: int,
                 primary_attributes: Dict[str, int],
                 combat_values: Dict[str, int],
                 skills: List[str],
                 xp_reward: int,
                 tags: Optional[List[str]] = None,
                 weaknesses: Optional[List[str]] = None,
                 resistances: Optional[List[str]] = None,
                 ai_strategy_id: Optional[str] = None,
                 asset_key: Optional[str] = None): # Hinzugefügter Parameter
        
        self.id: str = id
        self.name: str = name
        self.description: str = description
        self.asset_key = asset_key # Hinzugefügte Zuweisung

        self.level: int = level
        self.base_hp: int = base_hp
        self.primary_attributes: Dict[str, int] = primary_attributes
        self.combat_values: Dict[str, int] = combat_values
        self.skills: List[str] = skills
        self.tags: List[str] = tags if tags else []
        self.weaknesses: List[str] = weaknesses if weaknesses else []
        self.resistances: List[str] = resistances if resistances else []
        self.xp_reward: int = xp_reward
        self.ai_strategy_id: Optional[str] = ai_strategy_id

    def __repr__(self) -> str:
        return (f"OpponentTemplate(id='{self.id}', name='{self.name}', level={self.level})")