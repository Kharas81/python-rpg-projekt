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
                 primary_attributes: Dict[str, int], # z.B. {"STR": 10, "DEX": 12, ...}
                 combat_values: Dict[str, int],      # z.B. {"armor": 5, "initiative_bonus": 0, ...}
                 skills: List[str],                  # Liste von Skill-IDs
                 tags: Optional[List[str]] = None,   # z.B. ["GOBLINOID", "HUMANOID"]
                 weaknesses: Optional[List[str]] = None, # z.B. ["FIRE", "HOLY"]
                 resistances: Optional[List[str]] = None, # z.B. ["ICE"]
                 xp_reward: int = 0,
                 ai_strategy_id: Optional[str] = None): # ID der zu verwendenden KI-Strategie
        
        self.id: str = id
        self.name: str = name
        self.description: str = description
        self.level: int = level
        self.base_hp: int = base_hp

        self.primary_attributes: Dict[str, int] = primary_attributes
        self.combat_values: Dict[str, int] = combat_values # Enthält auch base_mana etc. falls vorhanden

        self.skills: List[str] = skills
        self.tags: List[str] = tags if tags else []
        self.weaknesses: List[str] = weaknesses if weaknesses else []
        self.resistances: List[str] = resistances if resistances else []
        
        self.xp_reward: int = xp_reward
        self.ai_strategy_id: Optional[str] = ai_strategy_id

    def __repr__(self) -> str:
        return (f"OpponentTemplate(id='{self.id}', name='{self.name}', level={self.level}, "
                f"base_hp={self.base_hp}, xp={self.xp_reward})")

if __name__ == '__main__':
    # Beispielhafte Erstellung eines OpponentTemplate-Objekts (nur zu Testzwecken)
    goblin_template_data = {
        "id": "goblin_test",
        "name": "Test Goblin",
        "description": "Ein Test-Goblin.",
        "level": 1,
        "base_hp": 50,
        "primary_attributes": {"STR": 8, "DEX": 12, "INT": 5, "CON": 9, "WIS": 6},
        "combat_values": {"armor": 2, "magic_resist": 0, "initiative_bonus": 0},
        "skills": ["basic_strike_phys"],
        "tags": ["GOBLINOID", "HUMANOID_TEST"],
        "weaknesses": ["FIRE"],
        "xp_reward": 50,
        "ai_strategy_id": "basic_melee"
    }
    
    goblin = OpponentTemplate(**goblin_template_data)
    print(goblin)
    print(f"Attribute des Goblins: {goblin.primary_attributes}")
    print(f"Skills des Goblins: {goblin.skills}")