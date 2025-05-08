"""
Charakter-Definition

Definiert die Struktur eines Charakter-Templates.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class CharacterTemplate:
    """
    Repräsentiert ein Charakter-Template mit allen Basiseigenschaften.
    
    Attribute:
        id (str): Die eindeutige ID des Charakters/der Klasse
        name (str): Der angezeigte Name
        description (str): Die Beschreibung
        primary_attributes (Dict[str, int]): Die Primärattribute (STR, DEX, etc.)
        combat_values (Dict[str, int]): Kampfwerte (HP, Mana, etc.)
        skills (List[str]): IDs der verfügbaren Skills
        tags (List[str]): Tags für den Charakter (z.B. WARRIOR, MELEE)
    """
    id: str
    name: str
    description: str
    primary_attributes: Dict[str, int]
    combat_values: Dict[str, int]
    skills: List[str]
    tags: List[str]
    
    @staticmethod
    def from_dict(char_id: str, data: Dict[str, Any]) -> 'CharacterTemplate':
        """
        Erstellt eine CharacterTemplate-Instanz aus einer Dictionary.
        
        Args:
            char_id (str): Die ID des Charakters
            data (Dict[str, Any]): Die Rohdaten aus der JSON5-Datei
            
        Returns:
            CharacterTemplate: Eine neue CharacterTemplate-Instanz
        """
        return CharacterTemplate(
            id=char_id,
            name=data.get('name', char_id),
            description=data.get('description', ''),
            primary_attributes=data.get('primary_attributes', {}),
            combat_values=data.get('combat_values', {}),
            skills=data.get('skills', []),
            tags=data.get('tags', []),
        )
    
    def get_attribute(self, attribute: str) -> int:
        """
        Gibt den Wert eines Primärattributs zurück.
        
        Args:
            attribute (str): Der Name des Attributs (z.B. 'STR')
            
        Returns:
            int: Der Wert des Attributs oder 0, wenn nicht vorhanden
        """
        return self.primary_attributes.get(attribute, 0)
    
    def get_combat_value(self, value: str) -> int:
        """
        Gibt den Wert eines Kampfwerts zurück.
        
        Args:
            value (str): Der Name des Kampfwerts (z.B. 'base_hp')
            
        Returns:
            int: Der Wert oder 0, wenn nicht vorhanden
        """
        return self.combat_values.get(value, 0)
    
    def has_tag(self, tag: str) -> bool:
        """
        Prüft, ob der Charakter einen bestimmten Tag hat.
        
        Args:
            tag (str): Der zu prüfende Tag
            
        Returns:
            bool: True, wenn der Tag vorhanden ist, sonst False
        """
        return tag in self.tags


class OpponentTemplate(CharacterTemplate):
    """
    Erweitert CharacterTemplate um gegner-spezifische Eigenschaften.
    
    Zusätzliche Attribute:
        level (int): Das Level des Gegners
        xp_reward (int): Die XP-Belohnung bei Besiegen des Gegners
        ai_strategy (str): Die zu verwendende KI-Strategie-ID
        weaknesses (List[str]): Schwächen gegen bestimmte Schadenstypen
    """
    
    def __init__(self, 
                 id: str,
                 name: str,
                 description: str,
                 primary_attributes: Dict[str, int],
                 combat_values: Dict[str, int],
                 skills: List[str],
                 tags: List[str],
                 level: int,
                 xp_reward: int,
                 ai_strategy: str,
                 weaknesses: Optional[List[str]] = None):
        super().__init__(id, name, description, primary_attributes, 
                         combat_values, skills, tags)
        self.level = level
        self.xp_reward = xp_reward
        self.ai_strategy = ai_strategy
        self.weaknesses = weaknesses or []
    
    @staticmethod
    def from_dict(opp_id: str, data: Dict[str, Any]) -> 'OpponentTemplate':
        """
        Erstellt eine OpponentTemplate-Instanz aus einer Dictionary.
        
        Args:
            opp_id (str): Die ID des Gegners
            data (Dict[str, Any]): Die Rohdaten aus der JSON5-Datei
            
        Returns:
            OpponentTemplate: Eine neue OpponentTemplate-Instanz
        """
        return OpponentTemplate(
            id=opp_id,
            name=data.get('name', opp_id),
            description=data.get('description', ''),
            primary_attributes=data.get('primary_attributes', {}),
            combat_values=data.get('combat_values', {}),
            skills=data.get('skills', []),
            tags=data.get('tags', []),
            level=data.get('level', 1),
            xp_reward=data.get('xp_reward', 0),
            ai_strategy=data.get('ai_strategy', 'basic_melee'),
            weaknesses=data.get('weaknesses', []),
        )
