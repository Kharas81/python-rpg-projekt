"""
Character Loader Module

Dieses Modul ist verantwortlich für das Laden und Bereitstellen der Charakterdaten.
"""

import logging
from typing import Dict, Any, List

from .base_loader import BaseLoader

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class CharacterLoader(BaseLoader):
    """
    Loader für Charakterdaten.
    """
    
    def __init__(self) -> None:
        """Initialisiert den CharacterLoader."""
        super().__init__("characters.json")
    
    def get_character_class(self, class_id: str) -> Dict[str, Any]:
        """
        Gibt die Daten für eine bestimmte Charakterklasse zurück.
        
        Args:
            class_id: ID der Charakterklasse (z.B. "warrior", "mage")
            
        Returns:
            Dict mit den Daten der Charakterklasse
            
        Raises:
            KeyError: Wenn die Charakterklasse nicht gefunden wird
        """
        data = self.get_data()
        if class_id not in data["character_classes"]:
            logger.error(f"Charakterklasse nicht gefunden: {class_id}")
            raise KeyError(f"Charakterklasse nicht gefunden: {class_id}")
        return data["character_classes"][class_id]
    
    def get_all_character_classes(self) -> List[str]:
        """
        Gibt eine Liste aller verfügbaren Charakterklassen-IDs zurück.
        
        Returns:
            Liste der Charakterklassen-IDs
        """
        data = self.get_data()
        return list(data["character_classes"].keys())
    
    def get_base_weapon_damage(self) -> int:
        """
        Gibt den Basis-Waffenschaden zurück.
        
        Returns:
            Basis-Waffenschaden
        """
        data = self.get_data()
        return data.get("base_weapon_damage", 5)
    
    def get_hit_chance_parameters(self) -> Dict[str, float]:
        """
        Gibt die Parameter für die Trefferchance-Berechnung zurück.
        
        Returns:
            Dict mit den Parametern für die Trefferchance-Berechnung
        """
        data = self.get_data()
        return {
            "base_hit_chance": data.get("base_hit_chance", 90),
            "hit_chance_accuracy_factor": data.get("hit_chance_accuracy_factor", 3),
            "hit_chance_evasion_factor": data.get("hit_chance_evasion_factor", 2)
        }


# Singleton-Instanz erstellen
character_loader = CharacterLoader()
