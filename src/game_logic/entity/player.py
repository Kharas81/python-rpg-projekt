"""
Player Module

Dieses Modul definiert die Player-Klasse, die die speziellen Eigenschaften
und Funktionen für spielbare Charaktere implementiert.
"""

import logging
from typing import Dict, Any, List, Optional

from src.game_logic.entity.base_entity import Entity
from src.game_logic.entity.entity_types import EntityType

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class Player(Entity):
    """
    Klasse für einen Spielercharakter.
    
    Diese Klasse erweitert die Basisentität um spielerspezifische Funktionalität
    wie Erfahrungspunkte, Inventar und Ausrüstung.
    """
    
    def __init__(self, player_id: str, data_dict: Dict[str, Any]) -> None:
        """
        Initialisiert einen neuen Spielercharakter.
        
        Args:
            player_id: Eindeutige ID für den Spieler (z.B. "warrior", "mage")
            data_dict: Dictionary mit den Daten des Spielers aus der JSON-Datei
        """
        # Rufe den Konstruktor der Elternklasse auf
        super().__init__(player_id, EntityType.PLAYER, data_dict)
        
        # Spielerspezifische Eigenschaften
        self.experience_points = data_dict.get("experience_points", 0)
        self.experience_to_level = self.calculate_exp_to_level()
        
        # Klassen und Spezialisierungen
        self.character_class = data_dict.get("character_class", "")
        self.specialization = data_dict.get("specialization", "")
        
        # Inventar und Ausrüstung (Placeholder, würde in einer tatsächlichen Implementierung
        # detaillierte Struktur haben)
        self.inventory_items = data_dict.get("inventory", [])
        self.equipped_items = data_dict.get("equipment", {})
        
        # Fortschritt und Quest-Status
        self.completed_quests = data_dict.get("completed_quests", [])
        self.active_quests = data_dict.get("active_quests", [])
        
        # Skill-Punkte und Talent-Punkte
        self.available_skill_points = data_dict.get("available_skill_points", 0)
        self.available_talent_points = data_dict.get("available_talent_points", 0)
        
        # Freundschaftswerte mit NPCs (für potenzielles Beziehungssystem)
        self.npc_relations = data_dict.get("npc_relations", {})
        
        logger.info(f"Spieler erstellt: {self.name} (Level {self.level}, "
                   f"Klasse: {self.character_class})")
    
    def calculate_exp_to_level(self) -> int:
        """
        Berechnet die benötigten Erfahrungspunkte für das nächste Level.
        
        Returns:
            Benötigte EP für das nächste Level
        """
        # Einfache quadratische Formel für EP-Kurve
        return 100 * (self.level ** 2)
    
    def gain_experience(self, amount: int) -> Dict[str, Any]:
        """
        Fügt dem Spieler Erfahrungspunkte hinzu und lässt ihn ggf. aufleveln.
        
        Args:
            amount: EP-Menge
            
        Returns:
            Dictionary mit Informationen zu gewonnenen EP und Level-Ups
        """
        result = {
            "gained_exp": amount,
            "old_exp": self.experience_points,
            "new_exp": self.experience_points + amount,
            "levelups": [],
            "old_level": self.level,
            "new_level": self.level
        }
        
        self.experience_points += amount
        logger.info(f"{self.name} erhält {amount} EP. Gesamt: {self.experience_points}")
        
        # Prüfe auf Level-Ups
        level_ups = 0
        while self.experience_points >= self.experience_to_level:
            level_up_info = self.level_up()
            result["levelups"].append(level_up_info)
            level_ups += 1
            
            # Berechne neue EP-Schwelle
            self.experience_to_level = self.calculate_exp_to_level()
        
        if level_ups > 0:
            result["new_level"] = self.level
        
        return result
    
    def level_up(self) -> Dict[str, Any]:
        """
        Erhöht das Level des Spielers und verwaltet dessen Auswirkungen.
        
        Erweitert die Basis-Level-Up-Funktionalität um spielerspezifische Aspekte.
        
        Returns:
            Dictionary mit Informationen zu den Änderungen durch das Level-Up
        """
        result = super().level_up()
        
        # Verwalte Skill- und Talent-Punkte
        self.available_skill_points += 1
        
        # Alle 3 Level erhalte einen Talent-Punkt
        if self.level % 3 == 0:
            self.available_talent_points += 1
            result["talent_point_gained"] = True
        
        result["skill_points_gained"] = 1
        result["available_skill_points"] = self.available_skill_points
        result["available_talent_points"] = self.available_talent_points
        
        # Hier könnten klassenspezifische Boni für das Level-Up hinzugefügt werden
        
        return result
    
    def regenerate_resources(self) -> None:
        """
        Regeneriert Ressourcen zu Beginn des Zuges.
        
        Überschreibt die Methode aus der Elternklasse mit spielerspezifischer Regeneration.
        """
        # Stärke erhöht Stamina-Regeneration
        if self.current_stamina is not None and self.max_stamina is not None:
            stamina_regen = 5 + self.get_attribute_bonus("strength")
            self.current_stamina = min(self.max_stamina, self.current_stamina + stamina_regen)
        
        # Geschicklichkeit erhöht Energie-Regeneration
        if self.current_energy is not None and self.max_energy is not None:
            energy_regen = 10 + self.get_attribute_bonus("dexterity")
            self.current_energy = min(self.max_energy, self.current_energy + energy_regen)
        
        # Intelligenz erhöht Mana-Regeneration
        if self.current_mana is not None and self.max_mana is not None:
            mana_regen = 5 + self.get_attribute_bonus("intelligence")
            self.current_mana = min(self.max_mana, self.current_mana + mana_regen)
    
    def equip_item(self, item_id: str) -> Dict[str, Any]:
        """
        Rüstet einen Gegenstand aus dem Inventar aus.
        
        Args:
            item_id: ID des auszurüstenden Gegenstands
            
        Returns:
            Dictionary mit Informationen zur Ausrüstungsaktion
        """
        # Ein einfacher Platzhalter für die Ausrüstungslogik
        # In einer tatsächlichen Implementierung würde hier mehr passieren
        
        return {
            "success": True,
            "message": f"{item_id} ausgerüstet",
            "equipped_item": item_id
        }
    
    def complete_quest(self, quest_id: str) -> Dict[str, Any]:
        """
        Schließt eine Quest ab und gibt Belohnungen.
        
        Args:
            quest_id: ID der abzuschließenden Quest
            
        Returns:
            Dictionary mit Informationen zur abgeschlossenen Quest
        """
        # Einfacher Platzhalter für die Quest-Abschluss-Logik
        # In einer tatsächlichen Implementierung würde hier mehr passieren
        
        if quest_id in self.active_quests and quest_id not in self.completed_quests:
            self.active_quests.remove(quest_id)
            self.completed_quests.append(quest_id)
            
            # Hier würden Quest-Belohnungen verarbeitet
            
            return {
                "success": True,
                "message": f"Quest {quest_id} abgeschlossen",
                "rewards": {
                    "experience": 100,
                    "gold": 50
                }
            }
        else:
            return {
                "success": False,
                "message": "Quest nicht aktiv oder bereits abgeschlossen"
            }
