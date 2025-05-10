"""
Item-Definition (Platzhalter)

Definiert die Struktur eines Items.
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ItemDefinition:
    """
    Repräsentiert ein Item mit allen notwendigen Eigenschaften (Platzhalter).
    
    Attribute:
        id (str): Die eindeutige ID des Items
        name (str): Der angezeigte Name
        description (str): Die Beschreibung
        item_type (str): Der Typ des Items (z.B. WEAPON, ARMOR)
        properties (Dict[str, Any]): Die Eigenschaften des Items
        tags (List[str]): Tags für das Item
    """
    id: str
    name: str
    description: str
    item_type: str
    properties: Dict[str, Any]
    tags: List[str]
    
    @staticmethod
    def from_dict(item_id: str, data: Dict[str, Any]) -> 'ItemDefinition':
        """
        Erstellt eine ItemDefinition-Instanz aus einer Dictionary.
        
        Args:
            item_id (str): Die ID des Items
            data (Dict[str, Any]): Die Rohdaten aus der JSON5-Datei
            
        Returns:
            ItemDefinition: Eine neue ItemDefinition-Instanz
        """
        return ItemDefinition(
            id=item_id,
            name=data.get('name', item_id),
            description=data.get('description', ''),
            item_type=data.get('item_type', 'MISC'),
            properties=data.get('properties', {}),
            tags=data.get('tags', []),
        )
