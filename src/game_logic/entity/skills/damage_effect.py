"""
Damage Effect Module

Implementiert die Logik für Schadenseffekte von Skills.
"""

import logging
from typing import Dict, Any, List

from src.definitions.data_service import data_service

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class DamageEffect:
    """
    Prozessor für Schadenseffekte von Skills.
    
    Diese Klasse verarbeitet die Anwendung von Schadenseffekten auf Ziele.
    """
    
    def apply(self, source: 'Entity', effect: Dict[str, Any],  # noqa: F821
              targets: List['Entity'], results: Dict[str, Any]) -> str:  # noqa: F821
        """
        Wendet einen Schadenseffekt auf Ziele an.
        
        Args:
            source: Quelle des Effekts
            effect: Effektdaten
            targets: Ziele des Effekts
            results: Bisherige Ergebnisse
            
        Returns:
            Nachricht über den angewendeten Effekt
        """
        damage_type = effect["damage_type"]
        scaling_attribute = effect.get("scaling_attribute", "strength")
        base_value = effect["base_value"]
        
        # Basiswert ermitteln
        if base_value == "weapon_damage":
            # Lade Basiswaffenschaden aus der Konfiguration
            base_damage = data_service.get_base_weapon_damage()
        else:
            base_damage = base_value
        
        # Attributsbonus
        attribute_bonus = source.get_attribute_bonus(scaling_attribute)
        
        # Waffen-Schadenmodifikatoren würden hier berücksichtigt
        
        # Formel auswerten
        formula = effect["scaling_formula"]
        # Ersetze Platzhalter in der Formel
        formula = formula.replace("base", str(base_damage))
        formula = formula.replace("attribute_bonus", str(attribute_bonus))
        formula = formula.replace("attribute", str(source.attributes[scaling_attribute]))
        
        try:
            damage = eval(formula)
        except Exception as e:
            logger.error(f"Fehler beim Auswerten der Schadensformel: {e}")
            damage = base_damage + attribute_bonus
        
        # Runde auf ganze Zahlen
        damage = int(damage)
        
        message = ""
        
        # Wende Schaden auf alle Ziele an
        for i, target in enumerate(targets):
            # Für sekundäre Ziele (bei Flächenangriffen)
            if i > 0 and "secondary_targets_modifier" in effect:
                damage_mod = int(damage * effect["secondary_targets_modifier"])
            else:
                damage_mod = damage
            
            # Führe spezielle Modifikatoren für Kreaturtypen aus
            if "creature_type_modifiers" in effect and target.creature_type in effect["creature_type_modifiers"]:
                type_modifier = effect["creature_type_modifiers"][target.creature_type]
                damage_mod = int(damage_mod * type_modifier)
                message += f"Effektmodifikator für {target.creature_type}: x{type_modifier}! "
            
            # Füge Schaden zu
            actual_damage, is_critical = target.take_damage(damage_mod, damage_type)
            
            # Speichere Ergebnis
            if target.unique_id not in results["targets"]:
                results["targets"][target.unique_id] = []
            
            results["targets"][target.unique_id].append({
                "type": "damage",
                "damage_type": damage_type,
                "amount": actual_damage,
                "is_critical": is_critical
            })
            
            # Erstelle Nachricht
            crit_text = " (Kritisch!)" if is_critical else ""
            message += f"{source.name} fügt {target.name} {actual_damage} {damage_type}-Schaden zu{crit_text}. "
        
        return message
