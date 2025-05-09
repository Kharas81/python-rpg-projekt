"""
Skill-Definition

Definiert die Struktur eines Skills.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class StatusEffectDefinition:
    """
    Definition eines durch einen Skill anwendbaren Status-Effekts.
    
    Attribute:
        id (str): Die ID des Status-Effekts
        duration (int): Die Dauer in Runden
        potency (int): Die Stärke des Effekts
    """
    id: str
    duration: int
    potency: int
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'StatusEffectDefinition':
        """
        Erstellt eine StatusEffectDefinition aus einer Dictionary.
        
        Args:
            data (Dict[str, Any]): Die Rohdaten aus der JSON5-Datei
            
        Returns:
            StatusEffectDefinition: Eine neue StatusEffectDefinition-Instanz
        """
        return StatusEffectDefinition(
            id=data.get('id', ''),
            duration=data.get('duration', 1),
            potency=data.get('potency', 1),
        )


@dataclass
class SkillDefinition:
    """
    Repräsentiert einen Skill mit allen notwendigen Eigenschaften.
    
    Attribute:
        id (str): Die eindeutige ID des Skills
        name (str): Der angezeigte Name
        description (str): Die Beschreibung
        cost (Dict[str, Any]): Die Kosten (Wert und Typ)
        effects (Dict[str, Any]): Die Effekte (Schaden, Attribut, etc.)
        applies_effects (List[StatusEffectDefinition]): Angewandte Status-Effekte
    """
    id: str
    name: str
    description: str
    cost: Dict[str, Any]
    effects: Dict[str, Any]
    applies_effects: List[StatusEffectDefinition]
    
    @staticmethod
    def from_dict(skill_id: str, data: Dict[str, Any]) -> 'SkillDefinition':
        """
        Erstellt eine SkillDefinition-Instanz aus einer Dictionary.
        
        Args:
            skill_id (str): Die ID des Skills
            data (Dict[str, Any]): Die Rohdaten aus der JSON5-Datei
            
        Returns:
            SkillDefinition: Eine neue SkillDefinition-Instanz
        """
        applies_effects = []
        if 'applies_effects' in data:
            applies_effects = [StatusEffectDefinition.from_dict(effect) for effect in data['applies_effects']]
            
        return SkillDefinition(
            id=skill_id,
            name=data.get('name', skill_id),
            description=data.get('description', ''),
            cost=data.get('cost', {'value': 0, 'type': 'NONE'}),
            effects=data.get('effects', {}),
            applies_effects=applies_effects,
        )
    
    def get_cost_value(self) -> int:
        """
        Gibt den Kostenwert des Skills zurück.
        
        Returns:
            int: Der Kostenwert
        """
        return self.cost.get('value', 0)
    
    def get_cost_type(self) -> str:
        """
        Gibt den Kostentyp des Skills zurück.
        
        Returns:
            str: Der Kostentyp (z.B. 'MANA', 'STAMINA')
        """
        return self.cost.get('type', 'NONE')
    
    def get_base_damage(self, default_damage: Optional[int] = None) -> Optional[int]:
        """
        Gibt den Basisschaden des Skills zurück.
        
        Args:
            default_damage (Optional[int]): Der Standardwert, falls base_damage null ist
            
        Returns:
            Optional[int]: Der Basisschaden oder der Standardwert
        """
        base_damage = self.effects.get('base_damage')
        if base_damage is None and default_damage is not None:
            return default_damage
        return base_damage
    
    def get_scaling_attribute(self) -> str:
        """
        Gibt das Skalierungsattribut des Skills zurück.
        
        Returns:
            str: Das Skalierungsattribut (z.B. 'STR', 'INT')
        """
        return self.effects.get('scaling_attribute', '')
    
    def get_damage_type(self) -> str:
        """
        Gibt den Schadenstyp des Skills zurück.
        
        Returns:
            str: Der Schadenstyp (z.B. 'PHYSICAL', 'MAGICAL')
        """
        return self.effects.get('damage_type', 'PHYSICAL')
    
    def get_multiplier(self) -> float:
        """
        Gibt den Schadensmultiplikator des Skills zurück.
        
        Returns:
            float: Der Multiplikator (z.B. 1.0, 1.5)
        """
        return self.effects.get('multiplier', 1.0)
    
    def is_self_effect(self) -> bool:
        """
        Prüft, ob der Skill einen Selbst-Effekt hat.
        
        Returns:
            bool: True, wenn es ein Selbst-Effekt ist, sonst False
        """
        return self.effects.get('self_effect', False)
    
    def is_area_effect(self) -> bool:
        """
        Prüft, ob der Skill einen Flächeneffekt hat.
        
        Returns:
            bool: True, wenn es ein Flächeneffekt ist, sonst False
        """
        return 'area_type' in self.effects
    
    def get_area_type(self) -> str:
        """
        Gibt den Typ des Flächeneffekts zurück.
        
        Returns:
            str: Der Typ des Flächeneffekts (z.B. 'CLEAVE', 'SPLASH')
        """
        return self.effects.get('area_type', '')
