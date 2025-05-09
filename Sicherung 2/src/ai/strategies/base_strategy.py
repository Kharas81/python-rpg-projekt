"""
Basis-Strategie

Definiert die abstrakte Basisklasse für alle KI-Strategien.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillDefinition
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class BaseStrategy(ABC):
    """
    Abstrakte Basisklasse für alle KI-Strategien.
    
    Alle konkreten KI-Strategien müssen von dieser Klasse erben und
    die abstrakte Methode choose_action implementieren.
    """
    
    def __init__(self, character: CharacterInstance):
        """
        Initialisiert die Strategie für einen bestimmten Charakter.
        
        Args:
            character (CharacterInstance): Der Charakter, der diese Strategie verwendet
        """
        self.character = character
        self.name = self.__class__.__name__
    
    @abstractmethod
    def choose_action(self, allies: List[CharacterInstance], enemies: List[CharacterInstance], 
                      available_skills: Dict[str, SkillDefinition]) -> Tuple[Optional[SkillDefinition], 
                                                                            Optional[CharacterInstance], 
                                                                            List[CharacterInstance]]:
        """
        Wählt eine Aktion basierend auf der aktuellen Kampfsituation aus.
        
        Args:
            allies (List[CharacterInstance]): Liste der verbündeten Charaktere
            enemies (List[CharacterInstance]): Liste der feindlichen Charaktere
            available_skills (Dict[str, SkillDefinition]): Verfügbare Skills mit ihren Definitionen
            
        Returns:
            Tuple[Optional[SkillDefinition], Optional[CharacterInstance], List[CharacterInstance]]: 
            Der gewählte Skill, das Hauptziel und sekundäre Ziele (für Flächeneffekte)
        """
        pass
    
    def _get_valid_targets(self, characters: List[CharacterInstance]) -> List[CharacterInstance]:
        """
        Filtert die Liste der Charaktere nach gültigen Zielen.
        
        Args:
            characters (List[CharacterInstance]): Liste der zu filternden Charaktere
            
        Returns:
            List[CharacterInstance]: Liste der gültigen Ziele
        """
        return [char for char in characters if char.can_be_targeted()]
    
    def _get_weakest_target(self, targets: List[CharacterInstance]) -> Optional[CharacterInstance]:
        """
        Findet das schwächste Ziel (mit den wenigsten HP) in der Liste.
        
        Args:
            targets (List[CharacterInstance]): Liste der Ziele
            
        Returns:
            Optional[CharacterInstance]: Das schwächste Ziel oder None, wenn keine Ziele vorhanden sind
        """
        if not targets:
            return None
        
        return min(targets, key=lambda char: char.hp)
    
    def _get_strongest_target(self, targets: List[CharacterInstance]) -> Optional[CharacterInstance]:
        """
        Findet das stärkste Ziel (mit den meisten HP) in der Liste.
        
        Args:
            targets (List[CharacterInstance]): Liste der Ziele
            
        Returns:
            Optional[CharacterInstance]: Das stärkste Ziel oder None, wenn keine Ziele vorhanden sind
        """
        if not targets:
            return None
        
        return max(targets, key=lambda char: char.hp)
    
    def _get_lowest_health_percentage_target(self, targets: List[CharacterInstance]) -> Optional[CharacterInstance]:
        """
        Findet das Ziel mit dem niedrigsten HP-Prozentsatz.
        
        Args:
            targets (List[CharacterInstance]): Liste der Ziele
            
        Returns:
            Optional[CharacterInstance]: Das Ziel mit dem niedrigsten HP-Prozentsatz oder None, wenn keine Ziele vorhanden sind
        """
        if not targets:
            return None
        
        return min(targets, key=lambda char: char.hp / char.get_max_hp())
    
    def _get_random_target(self, targets: List[CharacterInstance]) -> Optional[CharacterInstance]:
        """
        Wählt ein zufälliges Ziel aus der Liste aus.
        
        Args:
            targets (List[CharacterInstance]): Liste der Ziele
            
        Returns:
            Optional[CharacterInstance]: Ein zufälliges Ziel oder None, wenn keine Ziele vorhanden sind
        """
        import random
        if not targets:
            return None
        
        return random.choice(targets)
    
    def _filter_targets_by_tag(self, targets: List[CharacterInstance], tag: str) -> List[CharacterInstance]:
        """
        Filtert die Liste der Ziele nach einem bestimmten Tag.
        
        Args:
            targets (List[CharacterInstance]): Liste der Ziele
            tag (str): Der zu filternde Tag
            
        Returns:
            List[CharacterInstance]: Liste der Ziele mit dem angegebenen Tag
        """
        return [char for char in targets if char.has_tag(tag)]
    
    def _can_use_skill(self, skill: SkillDefinition) -> bool:
        """
        Prüft, ob der Charakter einen bestimmten Skill verwenden kann.
        
        Args:
            skill (SkillDefinition): Der zu prüfende Skill
            
        Returns:
            bool: True, wenn der Skill verwendet werden kann, sonst False
        """
        return self.character.has_enough_resource(skill)
