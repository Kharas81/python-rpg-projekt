"""
Leveling-System

Enthält Funktionen und Klassen für das Leveling-System.
"""
from typing import Dict, Any, List, Optional

from src.game_logic.formulas import calculate_xp_for_level
from src.game_logic.entities import CharacterInstance
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class LevelingService:
    """
    Service zur Verwaltung von Erfahrungspunkten und Level-Aufstiegen.
    
    Diese Klasse verwaltet die XP-Vergabe und Level-Up-Logik für alle Charaktere.
    Sie ist vom konkreten Charakter-Zustand entkoppelt.
    """
    
    def __init__(self):
        """Initialisiert den Leveling-Service."""
        # Hier könnten zusätzliche Initialisierungen stattfinden, z.B.
        # das Laden von Level-Up-Belohnungen oder -Boni aus Konfigurationsdateien
        pass
    
    def award_xp(self, character: CharacterInstance, amount: int) -> bool:
        """
        Vergibt XP an einen Charakter und prüft auf Level-Aufstieg.
        
        Args:
            character (CharacterInstance): Der Charakter, der XP erhält
            amount (int): Die Menge an XP
            
        Returns:
            bool: True, wenn ein Level-Aufstieg stattfand, sonst False
        """
        if not character.is_alive():
            logger.debug(f"Keine XP für {character.name}, da nicht am Leben")
            return False
        
        # XP vergeben
        character.xp += amount
        logger.info(f"{character.name} erhält {amount} XP, neue Gesamtsumme: {character.xp}")
        
        # Prüfen, ob ein Level-Aufstieg möglich ist
        current_level = character.level
        new_level = self.calculate_level_from_xp(character.xp)
        
        if new_level > current_level:
            # Level-Aufstieg durchführen
            levels_gained = new_level - current_level
            logger.info(f"{character.name} steigt {levels_gained} Level auf!")
            
            # Für jeden gewonnenen Level die Boni anwenden
            for _ in range(levels_gained):
                self._apply_level_up(character)
            
            return True
        
        return False
    
    def calculate_level_from_xp(self, xp: int) -> int:
        """
        Berechnet das Level basierend auf XP.
        
        Args:
            xp (int): Die Gesamtsumme an XP
            
        Returns:
            int: Das daraus resultierende Level
        """
        level = 1
        while True:
            xp_for_next = calculate_xp_for_level(level + 1)
            if xp_for_next > xp:
                break
            level += 1
        
        return level
    
    def get_xp_for_next_level(self, character: CharacterInstance) -> int:
        """
        Berechnet die XP, die für das nächste Level benötigt werden.
        
        Args:
            character (CharacterInstance): Der Charakter
            
        Returns:
            int: Die benötigte XP für das nächste Level
        """
        next_level = character.level + 1
        return calculate_xp_for_level(next_level)
    
    def get_xp_progress_percentage(self, character: CharacterInstance) -> float:
        """
        Berechnet den XP-Fortschritt in Prozent zum nächsten Level.
        
        Args:
            character (CharacterInstance): Der Charakter
            
        Returns:
            float: Der Fortschritt in Prozent (0-100)
        """
        current_level_xp = calculate_xp_for_level(character.level)
        next_level_xp = calculate_xp_for_level(character.level + 1)
        
        if next_level_xp <= current_level_xp:  # Sicherheit für Edge-Cases
            return 100.0
        
        xp_for_level = next_level_xp - current_level_xp
        current_xp_in_level = character.xp - current_level_xp
        
        progress = (current_xp_in_level / xp_for_level) * 100.0
        return max(0.0, min(100.0, progress))  # Auf 0-100% beschränken
    
    def _apply_level_up(self, character: CharacterInstance) -> None:
        """
        Wendet die Level-Up-Logik auf einen Charakter an.
        
        Args:
            character (CharacterInstance): Der Charakter, der aufsteigt
        """
        character.level += 1
        logger.info(f"{character.name} ist auf Level {character.level} aufgestiegen!")
        
        # Volle Heilung und Ressourcenwiederherstellung
        max_hp = character.get_max_hp()
        character.hp = max_hp
        
        for resource_type in ['MANA', 'STAMINA', 'ENERGY']:
            resource_key = f"base_{resource_type.lower()}"
            max_resource = character.base_combat_values.get(resource_key, 0)
            if max_resource > 0:
                if resource_type == 'MANA':
                    character.mana = max_resource
                elif resource_type == 'STAMINA':
                    character.stamina = max_resource
                elif resource_type == 'ENERGY':
                    character.energy = max_resource
        
        # Hier könnten weitere Level-Up-Boni angewendet werden, z.B.:
        # - Neue Skills freischalten
        # - Attributpunkte vergeben
        # - Kampfwerte erhöhen
        # Diese Logik würde in späteren Versionen implementiert werden.


# Globale Instanz des Leveling-Service
leveling_service = LevelingService()


def get_leveling_service() -> LevelingService:
    """
    Gibt die globale Instanz des Leveling-Service zurück.
    
    Returns:
        LevelingService: Die globale Instanz
    """
    return leveling_service
