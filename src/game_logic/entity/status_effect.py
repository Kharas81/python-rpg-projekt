"""
Status Effect Module

Dieses Modul implementiert die Logik für Status-Effekte, die auf Entitäten
angewendet werden können, wie z.B. Betäubung, Gift oder Schilde.
"""

import logging
from typing import Dict, Any, Optional

from src.definitions.data_service import data_service

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class StatusEffectInstance:
    """
    Repräsentiert eine Instanz eines Status-Effekts auf einer Entität.
    
    Status-Effekte können eine Vielzahl von Auswirkungen haben, wie z.B.
    Verhindern von Aktionen, Verändern von Attributen oder Verursachen von
    Schaden über Zeit.
    """
    
    def __init__(self, effect_id: str, duration: int, 
                 source_entity_id: Optional[str] = None,
                 params: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialisiert einen Status-Effekt.
        
        Args:
            effect_id: ID des Status-Effekts in den Daten
            duration: Dauer in Runden
            source_entity_id: ID der Entität, die den Effekt verursacht hat
            params: Zusätzliche Parameter für den Effekt
        """
        self.effect_id = effect_id
        self.duration = duration
        self.source_entity_id = source_entity_id
        self.params = params or {}
        
        # Lade Effektdaten
        try:
            self.effect_data = data_service.get_status_effect(effect_id)
            self.name = self.effect_data["name"]
            self.description = self.effect_data["description"]
            self.icon = self.effect_data.get("icon", "?")
        except KeyError:
            logger.warning(f"Status-Effekt {effect_id} nicht gefunden, verwende Standardwerte")
            self.effect_data = {}
            self.name = effect_id
            self.description = "Unbekannter Effekt"
            self.icon = "?"
    
    def on_apply(self, entity: 'Entity') -> None:  # noqa: F821
        """
        Wird aufgerufen, wenn der Effekt auf eine Entität angewendet wird.
        
        Args:
            entity: Die Entität, auf die der Effekt angewendet wird
        """
        logger.debug(f"Status-Effekt {self.name} auf {entity.name} angewandt")
        
        # Wende Effekte auf die Entität an
        effects = self.effect_data.get("effects", [])
        
        if "prevent_actions" in effects:
            entity.can_act = False
        
        if "reduce_initiative" in effects:
            modifier = self.effect_data.get("initiative_modifier", 0)
            entity.initiative_modifier += modifier
        
        if "increase_initiative" in effects:
            modifier = self.effect_data.get("initiative_bonus", 0)
            entity.initiative_modifier += modifier
        
        if "reduce_accuracy" in effects:
            modifier = self.effect_data.get("accuracy_modifier", 0)
            entity.accuracy_modifier += modifier
        
        if "increase_defenses" in effects:
            armor_bonus = self.effect_data.get("armor_bonus", 0)
            magic_res_bonus = self.effect_data.get("magic_resistance_bonus", 0)
            entity.armor_modifier += armor_bonus
            entity.magic_resistance_modifier += magic_res_bonus
    
    def on_remove(self, entity: 'Entity') -> None:  # noqa: F821
        """
        Wird aufgerufen, wenn der Effekt von einer Entität entfernt wird.
        
        Args:
            entity: Die Entität, von der der Effekt entfernt wird
        """
        logger.debug(f"Status-Effekt {self.name} von {entity.name} entfernt")
        
        # Entferne Effekte von der Entität
        effects = self.effect_data.get("effects", [])
        
        if "prevent_actions" in effects:
            entity.can_act = True
        
        if "reduce_initiative" in effects:
            modifier = self.effect_data.get("initiative_modifier", 0)
            entity.initiative_modifier -= modifier
        
        if "increase_initiative" in effects:
            modifier = self.effect_data.get("initiative_bonus", 0)
            entity.initiative_modifier -= modifier
        
        if "reduce_accuracy" in effects:
            modifier = self.effect_data.get("accuracy_modifier", 0)
            entity.accuracy_modifier -= modifier
        
        if "increase_defenses" in effects:
            armor_bonus = self.effect_data.get("armor_bonus", 0)
            magic_res_bonus = self.effect_data.get("magic_resistance_bonus", 0)
            entity.armor_modifier -= armor_bonus
            entity.magic_resistance_modifier -= magic_res_bonus
    
    def on_turn(self, entity: 'Entity') -> None:  # noqa: F821
        """
        Wird zu Beginn eines Zuges für die Entität aufgerufen.
        
        Args:
            entity: Die Entität mit diesem Effekt
        """
        effects = self.effect_data.get("effects", [])
        
        # Führe Effekte aus, die jede Runde wirken
        if "damage_over_time" in effects:
            damage = self.effect_data.get("damage_per_turn", 0)
            damage_type = self.effect_data.get("damage_type", "untyped")
            logger.debug(f"{entity.name} erleidet {damage} {damage_type}-Schaden durch {self.name}")
            entity.take_damage(damage, damage_type)
        
        # Reduziere die verbleibende Dauer
        self.duration -= 1
        
        if self.duration <= 0:
            logger.debug(f"Status-Effekt {self.name} läuft aus für {entity.name}")
            entity.remove_status_effect(self.effect_id)
