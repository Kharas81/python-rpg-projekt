"""
Skill Loader Module

Dieses Modul ist verantwortlich für das Laden und Bereitstellen der Skill-Daten.
"""

import logging
from typing import Dict, Any, List, Optional

from .base_loader import BaseLoader

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class SkillLoader(BaseLoader):
    """
    Loader für Skill-Daten.
    """
    
    def __init__(self) -> None:
        """Initialisiert den SkillLoader."""
        super().__init__("skills.json")
    
    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        Gibt die Daten für einen bestimmten Skill zurück.
        
        Args:
            skill_id: ID des Skills
            
        Returns:
            Dict mit den Daten des Skills oder None, wenn der Skill nicht gefunden wird
        """
        data = self.get_data()
        if skill_id in data["skills"]:
            return data["skills"][skill_id]
        else:
            logger.debug(f"Skill nicht gefunden: {skill_id}")
            return None
    
    def get_all_skills(self) -> List[str]:
        """
        Gibt eine Liste aller verfügbaren Skill-IDs zurück.
        
        Returns:
            Liste der Skill-IDs
        """
        data = self.get_data()
        return list(data["skills"].keys())
    
    def get_status_effect(self, effect_id: str) -> Optional[Dict[str, Any]]:
        """
        Gibt die Daten für einen bestimmten Status-Effekt zurück.
        
        Args:
            effect_id: ID des Status-Effekts
            
        Returns:
            Dict mit den Daten des Status-Effekts oder None, wenn der Effekt nicht gefunden wird
        """
        data = self.get_data()
        if effect_id in data["status_effects"]:
            return data["status_effects"][effect_id]
        else:
            logger.debug(f"Status-Effekt nicht gefunden: {effect_id}")
            return None
    
    def get_all_status_effects(self) -> List[str]:
        """
        Gibt eine Liste aller verfügbaren Status-Effekt-IDs zurück.
        
        Returns:
            Liste der Status-Effekt-IDs
        """
        data = self.get_data()
        return list(data["status_effects"].keys())


# Singleton-Instanz erstellen
skill_loader = SkillLoader()
