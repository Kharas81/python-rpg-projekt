"""
Shield Effect Module

Implementiert die Logik für Schildeffekte von Skills.
"""

import logging
from typing import Dict, Any, List

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class ShieldEffect:
    """
    Prozessor für Schildeffekte von Skills.
    
    Diese Klasse verarbeitet die Anwendung von Schildeffekten auf Ziele.
    """
    
    def apply(self, source: 'Entity', effect: Dict[str, Any],  # noqa: F821
              targets: List['Entity'], results: Dict[str, Any]) -> str:  # noqa: F821
        """
        Wendet einen Schildeffekt auf Ziele an.
        
        Args:
            source: Quelle des Effekts
            effect: Effektdaten
            targets: Ziele des Effekts
            results: Bisherige Ergebnisse
            
        Returns:
            Nachricht über den angewendeten Effekt
        """
        scaling_attribute = effect.get("scaling_attribute", "intelligence")
        base_value = effect["base_value"]
        duration = effect.get("duration", 1)
        
        # Formel auswerten
        formula = effect["scaling_formula"]
        formula = formula.replace("base", str(base_value))
        formula = formula.replace("attribute_bonus", str(source.get_attribute_bonus(scaling_attribute)))
        formula = formula.replace("attribute", str(source.attributes[scaling_attribute]))
        
        try:
            shield_value = eval(formula)
        except Exception as e:
            logger.error(f"Fehler beim Auswerten der Schildformel: {e}")
            shield_value = base_value + source.attributes[scaling_attribute]
        
        # Runde auf ganze Zahlen
        shield_value = int(shield_value)
        
        message = ""
        
        # Wende Schild auf alle Ziele an
        for target in targets:
            # Füge Schild als Status-Effekt hinzu
            target.add_status_effect("shield", duration, source.unique_id, {
                "shield_value": shield_value
            })
            
            # Speichere Ergebnis
            if target.unique_id not in results["targets"]:
                results["targets"][target.unique_id] = []
            
            results["targets"][target.unique_id].append({
                "type": "shield",
                "amount": shield_value,
                "duration": duration
            })
            
            # Erstelle Nachricht
            message += f"{source.name} gibt {target.name} einen Schild mit {shield_value} Absorption für {duration} Runden. "
        
        return message
