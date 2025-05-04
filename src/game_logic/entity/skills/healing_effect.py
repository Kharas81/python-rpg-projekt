"""
Healing Effect Module

Implementiert die Logik für Heilungseffekte von Skills.
"""

import logging
from typing import Dict, Any, List

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class HealingEffect:
    """
    Prozessor für Heilungseffekte von Skills.
    
    Diese Klasse verarbeitet die Anwendung von Heilungseffekten auf Ziele.
    """
    
    def apply(self, source: 'Entity', effect: Dict[str, Any],  # noqa: F821
              targets: List['Entity'], results: Dict[str, Any]) -> str:  # noqa: F821
        """
        Wendet einen Heilungseffekt auf Ziele an.
        
        Args:
            source: Quelle des Effekts
            effect: Effektdaten
            targets: Ziele des Effekts
            results: Bisherige Ergebnisse
            
        Returns:
            Nachricht über den angewendeten Effekt
        """
        scaling_attribute = effect.get("scaling_attribute", "wisdom")
        base_value = effect["base_value"]
        
        # Formel auswerten
        formula = effect["scaling_formula"]
        # Ersetze Platzhalter in der Formel
        formula = formula.replace("base", str(base_value))
        formula = formula.replace("attribute_bonus", str(source.get_attribute_bonus(scaling_attribute)))
        formula = formula.replace("attribute", str(source.attributes[scaling_attribute]))
        
        try:
            healing = eval(formula)
        except Exception as e:
            logger.error(f"Fehler beim Auswerten der Heilungsformel: {e}")
            healing = base_value + source.get_attribute_bonus(scaling_attribute)
        
        # Runde auf ganze Zahlen
        healing = int(healing)
        
        message = ""
        
        # Wende Heilung auf alle Ziele an
        for target in targets:
            actual_healing = target.heal(healing)
            
            # Speichere Ergebnis
            if target.unique_id not in results["targets"]:
                results["targets"][target.unique_id] = []
            
            results["targets"][target.unique_id].append({
                "type": "healing",
                "amount": actual_healing
            })
            
            # Erstelle Nachricht
            message += f"{source.name} heilt {target.name} um {actual_healing} HP. "
        
        return message
