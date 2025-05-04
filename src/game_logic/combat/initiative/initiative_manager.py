"""
Initiative Manager Module

Verwaltet die Initiativreihenfolge und den Rundenfortschritt im Kampf.
"""

import logging
import random
from typing import Dict, List, Tuple, Any

from src.game_logic.entity.base_entity import Entity

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class InitiativeManager:
    """
    Manager für die Initiative und Rundenfortschritt im Kampf.
    
    Diese Klasse ist verantwortlich für die Berechnung der Initiativreihenfolge,
    die Verwaltung des aktuellen Zugs und den Wechsel zu neuen Runden.
    """
    
    def __init__(self) -> None:
        """
        Initialisiert einen neuen InitiativeManager.
        """
        self.initiative_order: List[Entity] = []
        self.current_entity_index: int = 0
        self.current_round: int = 0
        self.processed_entities: List[str] = []  # Liste der IDs der Entitäten, die in der aktuellen Runde schon gehandelt haben
    
    def calculate_initiative(self, entities: List[Entity]) -> List[Entity]:
        """
        Berechnet die Initiative für eine Liste von Entitäten und ordnet sie in der Initiativreihenfolge an.
        
        Args:
            entities: Liste aller am Kampf teilnehmenden Entitäten
            
        Returns:
            Liste der Entitäten, sortiert nach Initiative (höchste zuerst)
        """
        initiative_values = []
        
        # Berechne Initiative für jede Entität (Basiswert + Modifikator + Zufallswert)
        for entity in entities:
            base_initiative = entity.get_effective_initiative()
            initiative_roll = random.randint(1, 20)
            total_initiative = base_initiative + initiative_roll
            
            initiative_values.append((entity, total_initiative))
            logger.debug(f"Initiative für {entity.name}: {base_initiative} + {initiative_roll} = {total_initiative}")
        
        # Sortiere nach Initiative absteigend
        initiative_values.sort(key=lambda x: x[1], reverse=True)
        
        self.initiative_order = [item[0] for item in initiative_values]
        self.current_entity_index = 0
        self.current_round = 1
        self.processed_entities = []
        
        return self.initiative_order
    
    def get_current_entity(self) -> Entity:
        """
        Gibt die Entität zurück, die aktuell am Zug ist.
        
        Returns:
            Entität, die am Zug ist
        """
        return self.initiative_order[self.current_entity_index]
    
    def advance_to_next_entity(self, entities: List[Entity]) -> Tuple[Entity, bool, str]:
        """
        Wechselt zur nächsten Entität in der Initiativreihenfolge.
        
        Args:
            entities: Aktualisierte Liste aller am Kampf teilnehmenden Entitäten
            
        Returns:
            Tupel aus (nächste Entität, neue Runde begonnen, Nachricht)
        """
        # Aktualisiere die Initiative-Reihenfolge, um tote Entitäten zu entfernen
        self.initiative_order = [entity for entity in self.initiative_order if entity in entities and entity.is_alive()]
        
        # Wenn keine Entitäten übrig sind, gib None zurück
        if not self.initiative_order:
            return None, False, "Keine Entitäten mehr übrig."
        
        # Markiere die aktuelle Entität als verarbeitet
        current_entity = self.initiative_order[self.current_entity_index]
        self.processed_entities.append(current_entity.unique_id)
        
        # Erhöhe den Index
        self.current_entity_index += 1
        
        # Wenn das Ende der Initiativreihenfolge erreicht ist, beginne eine neue Runde
        new_round_started = False
        message = ""
        
        if self.current_entity_index >= len(self.initiative_order):
            self.current_round += 1
            self.current_entity_index = 0
            self.processed_entities = []
            new_round_started = True
            message = f"Runde {self.current_round} beginnt."
            logger.info(f"Neue Kampfrunde: {self.current_round}")
        
        # Überspringe tote Entitäten
        while (self.current_entity_index < len(self.initiative_order) and 
               (not self.initiative_order[self.current_entity_index].is_alive() or 
                self.initiative_order[self.current_entity_index].unique_id in self.processed_entities)):
            self.current_entity_index += 1
            
            # Wenn wir wieder am Ende angekommen sind, beginne eine neue Runde
            if self.current_entity_index >= len(self.initiative_order):
                self.current_round += 1
                self.current_entity_index = 0
                self.processed_entities = []
                new_round_started = True
                message = f"Runde {self.current_round} beginnt."
                logger.info(f"Neue Kampfrunde: {self.current_round}")
        
        # Wenn wir keine gültige Entität finden konnten, gib None zurück
        if self.current_entity_index >= len(self.initiative_order):
            return None, new_round_started, message
        
        return self.initiative_order[self.current_entity_index], new_round_started, message
    
    def get_initiative_order_names(self) -> List[str]:
        """
        Gibt die Namen der Entitäten in der Initiativreihenfolge zurück.
        
        Returns:
            Liste von Namen in der Initiativreihenfolge
        """
        return [entity.name for entity in self.initiative_order]
