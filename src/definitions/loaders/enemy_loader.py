"""
Enemy Loader Module

Dieses Modul ist verantwortlich für das Laden und Bereitstellen der Gegner-Daten.
"""

import logging
from typing import Dict, Any, List, Optional

from .base_loader import BaseLoader

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class EnemyLoader(BaseLoader):
    """
    Loader für Gegner-Daten.
    """
    
    def __init__(self) -> None:
        """Initialisiert den EnemyLoader."""
        super().__init__("enemies.json")
    
    def get_enemy(self, enemy_id: str) -> Optional[Dict[str, Any]]:
        """
        Gibt die Daten für einen bestimmten Gegner zurück.
        
        Args:
            enemy_id: ID des Gegners
            
        Returns:
            Dict mit den Daten des Gegners oder None, wenn der Gegner nicht gefunden wird
        """
        data = self.get_data()
        if enemy_id in data["enemies"]:
            return data["enemies"][enemy_id]
        else:
            logger.debug(f"Gegner nicht gefunden: {enemy_id}")
            return None
    
    def get_all_enemies(self) -> List[str]:
        """
        Gibt eine Liste aller verfügbaren Gegner-IDs zurück.
        
        Returns:
            Liste der Gegner-IDs
        """
        data = self.get_data()
        return list(data["enemies"].keys())
    
    def get_enemy_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        Gibt die Daten für einen bestimmten Gegner-Skill zurück.
        
        Args:
            skill_id: ID des Gegner-Skills
            
        Returns:
            Dict mit den Daten des Skills oder None, wenn der Skill nicht gefunden wird
        """
        data = self.get_data()
        if "enemy_skills" in data and skill_id in data["enemy_skills"]:
            return data["enemy_skills"][skill_id]
        else:
            logger.debug(f"Gegner-Skill nicht gefunden: {skill_id}")
            return None
    
    def get_all_enemy_skills(self) -> List[str]:
        """
        Gibt eine Liste aller verfügbaren Gegner-Skill-IDs zurück.
        
        Returns:
            Liste der Gegner-Skill-IDs
        """
        data = self.get_data()
        if "enemy_skills" in data:
            return list(data["enemy_skills"].keys())
        else:
            return []


# Singleton-Instanz erstellen
enemy_loader = EnemyLoader()
