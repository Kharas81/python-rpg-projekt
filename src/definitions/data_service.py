"""
Data Service Module

Dieses Modul stellt einen zentralen Zugriffsservice für alle Daten im Spiel bereit,
indem es die spezialisierten Loader zusammenführt.
"""

import logging
from typing import Dict, Any, List, Optional

from src.definitions.loaders.character_loader import character_loader
from src.definitions.loaders.skill_loader import skill_loader
from src.definitions.loaders.enemy_loader import enemy_loader

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class DataService:
    """
    Zentraler Service für den Zugriff auf alle Spieldaten.
    
    Diese Klasse vereinfacht den Zugriff, indem sie die spezialisierten Loader
    zusammenführt und eine einheitliche Schnittstelle bietet.
    """
    
    def __init__(self) -> None:
        """Initialisiert den DataService."""
        self._character_loader = character_loader
        self._skill_loader = skill_loader
        self._enemy_loader = enemy_loader
    
    def reload_all(self) -> None:
        """Lädt alle Daten neu."""
        self._character_loader.get_data(reload=True)
        self._skill_loader.get_data(reload=True)
        self._enemy_loader.get_data(reload=True)
        logger.info("Alle Daten wurden neu geladen.")
    
    def get_character_class(self, class_id: str) -> Dict[str, Any]:
        """
        Gibt die Daten für eine bestimmte Charakterklasse zurück.
        
        Args:
            class_id: ID der Charakterklasse
            
        Returns:
            Dict mit den Daten der Charakterklasse
            
        Raises:
            KeyError: Wenn die Charakterklasse nicht gefunden wird
        """
        return self._character_loader.get_character_class(class_id)
    
    def get_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        Gibt die Daten für einen bestimmten Skill zurück.
        
        Args:
            skill_id: ID des Skills
            
        Returns:
            Dict mit den Daten des Skills
            
        Raises:
            KeyError: Wenn der Skill nicht gefunden wird
        """
        # Versuche, einen Spieler-Skill zu finden
        skill = self._skill_loader.get_skill(skill_id)
        if skill is not None:
            return skill
        
        # Versuche, einen Gegner-Skill zu finden
        enemy_skill = self._enemy_loader.get_enemy_skill(skill_id)
        if enemy_skill is not None:
            return enemy_skill
        
        # Skill wurde nicht gefunden
        logger.error(f"Skill nicht gefunden: {skill_id}")
        raise KeyError(f"Skill nicht gefunden: {skill_id}")
    
    def get_enemy(self, enemy_id: str) -> Dict[str, Any]:
        """
        Gibt die Daten für einen bestimmten Gegner zurück.
        
        Args:
            enemy_id: ID des Gegners
            
        Returns:
            Dict mit den Daten des Gegners
            
        Raises:
            KeyError: Wenn der Gegner nicht gefunden wird
        """
        enemy = self._enemy_loader.get_enemy(enemy_id)
        if enemy is None:
            logger.error(f"Gegner nicht gefunden: {enemy_id}")
            raise KeyError(f"Gegner nicht gefunden: {enemy_id}")
        return enemy
    
    def get_status_effect(self, effect_id: str) -> Dict[str, Any]:
        """
        Gibt die Daten für einen bestimmten Status-Effekt zurück.
        
        Args:
            effect_id: ID des Status-Effekts
            
        Returns:
            Dict mit den Daten des Status-Effekts
            
        Raises:
            KeyError: Wenn der Status-Effekt nicht gefunden wird
        """
        effect = self._skill_loader.get_status_effect(effect_id)
        if effect is None:
            logger.error(f"Status-Effekt nicht gefunden: {effect_id}")
            raise KeyError(f"Status-Effekt nicht gefunden: {effect_id}")
        return effect
    
    def get_all_character_classes(self) -> List[str]:
        """
        Gibt eine Liste aller verfügbaren Charakterklassen zurück.
        
        Returns:
            Liste der Charakterklassen-IDs
        """
        return self._character_loader.get_all_character_classes()
    
    def get_all_enemies(self) -> List[str]:
        """
        Gibt eine Liste aller verfügbaren Gegner zurück.
        
        Returns:
            Liste der Gegner-IDs
        """
        return self._enemy_loader.get_all_enemies()
    
    def get_base_weapon_damage(self) -> int:
        """
        Gibt den Basis-Waffenschaden zurück.
        
        Returns:
            Basis-Waffenschaden
        """
        return self._character_loader.get_base_weapon_damage()
    
    def get_hit_chance_parameters(self) -> Dict[str, float]:
        """
        Gibt die Parameter für die Trefferchance-Berechnung zurück.
        
        Returns:
            Dict mit den Parametern für die Trefferchance-Berechnung
        """
        return self._character_loader.get_hit_chance_parameters()


# Singleton-Instanz für einfachen Zugriff
data_service = DataService()
