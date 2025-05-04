"""
Status Effect Processor Module

Implementiert die Logik für das Anwenden von Statuseffekten durch Skills.
"""

import logging
import random
from typing import Dict, Any, List

from src.definitions.data_service import data_service

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class StatusEffectProcessor:
    """
    Prozessor für Statuseffekte von Skills.
    
    Diese Klasse verarbeitet die Anwendung von Statuseffekten auf Ziele.
    """
    
    def apply(self, source: 'Entity', effect: Dict[str, Any],  # noqa: F821
              targets: List['Entity'], results: Dict[str, Any]) -> str:  # noqa: F821
        """
        Wendet einen Statuseffekt auf Ziele an.
        
        Args:
            source: Quelle des Effekts
            effect: Effektdaten
            targets: Ziele des Effekts
            results: Bisherige Ergebnisse
            
        Returns:
            Nachricht über den angewendeten Effekt
        """
        status_effect = effect["status_effect"]
        duration = effect.get("duration", 1)
        chance = effect.get("chance", 1.0)
        
        message = ""
        
        # Wende Status-Effekt auf alle Ziele an
        for target in targets:
            # Würfle für Chance
            if random.random() <= chance:
                # Erstelle Parameter-Dict für zusätzliche Effektdaten
                params = {}
                for key, value in effect.items():
                    if key not in ["type", "status_effect", "duration", "chance"]:
                        params[key] = value
                
                # Füge Status-Effekt hinzu
                target.add_status_effect(status_effect, duration, source.unique_id, params)
                
                # Speichere Ergebnis
                if target.unique_id not in results["targets"]:
                    results["targets"][target.unique_id] = []
                
                results["targets"][target.unique_id].append({
                    "type": "status_effect",
                    "status_effect": status_effect,
                    "duration": duration,
                    "applied": True
                })
                
                # Erstelle Nachricht
                try:
                    effect_data = data_service.get_status_effect(status_effect)
                    effect_name = effect_data["name"]
                    message += f"{source.name} verursacht den Status '{effect_name}' bei {target.name} für {duration} Runden. "
                except KeyError:
                    message += f"{source.name} verursacht einen unbekannten Status-Effekt bei {target.name}. "
            else:
                # Status-Effekt wurde widerstanden
                if target.unique_id not in results["targets"]:
                    results["targets"][target.unique_id] = []
                
                results["targets"][target.unique_id].append({
                    "type": "status_effect",
                    "status_effect": status_effect,
                    "applied": False
                })
                
                message += f"{target.name} widersteht dem Status-Effekt von {source.name}. "
        
        return message
