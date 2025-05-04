"""
NPC Module

Dieses Modul definiert die NPC-Klasse, die die speziellen Eigenschaften
und Funktionen für nicht-spielbare Charaktere implementiert.
"""

import logging
from typing import Dict, Any, List, Optional

from src.game_logic.entity.base_entity import Entity
from src.game_logic.entity.entity_types import EntityType

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class NPC(Entity):
    """
    Klasse für einen nicht-spielbaren Charakter (NPC).
    
    Diese Klasse erweitert die Basisentität um NPC-spezifische Funktionalität
    wie Dialoge, Händlerfunktionen und Quest-Vergabe.
    """
    
    def __init__(self, npc_id: str, data_dict: Dict[str, Any]) -> None:
        """
        Initialisiert einen neuen NPC.
        
        Args:
            npc_id: Eindeutige ID für den NPC (z.B. "merchant", "innkeeper")
            data_dict: Dictionary mit den Daten des NPCs aus der JSON-Datei
        """
        # Rufe den Konstruktor der Elternklasse auf
        super().__init__(npc_id, EntityType.NPC, data_dict)
        
        # NPC-spezifische Eigenschaften
        self.is_merchant = data_dict.get("is_merchant", False)
        self.is_quest_giver = data_dict.get("is_quest_giver", False)
        self.is_trainer = data_dict.get("is_trainer", False)
        
        # Gesprächsdaten
        self.dialogue_tree = data_dict.get("dialogue", {})
        self.current_dialogue_state = "greeting"
        
        # Waren für Händler
        self.inventory = data_dict.get("inventory", [])
        self.buy_rate = data_dict.get("buy_rate", 0.5)  # Kauft Waren für 50% des Verkaufspreises
        self.sell_rate = data_dict.get("sell_rate", 1.0)  # Verkauft Waren zum vollen Preis
        
        # Quest-Daten
        self.available_quests = data_dict.get("available_quests", [])
        self.training_options = data_dict.get("training_options", [])
        
        # Beziehungen und Stimmung
        self.default_mood = data_dict.get("default_mood", "neutral")
        self.current_mood = self.default_mood
        self.faction = data_dict.get("faction", "neutral")
        
        logger.info(f"NPC erstellt: {self.name} ({', '.join(self._get_roles())})")
    
    def _get_roles(self) -> List[str]:
        """
        Gibt eine Liste der Rollen dieses NPCs zurück.
        
        Returns:
            Liste der Rollen
        """
        roles = []
        if self.is_merchant:
            roles.append("Händler")
        if self.is_quest_giver:
            roles.append("Questgeber")
        if self.is_trainer:
            roles.append("Trainer")
        if not roles:
            roles.append("Bewohner")
        return roles
    
    def get_dialogue(self, player_info: Dict[str, Any], topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Gibt den Dialog für ein bestimmtes Thema zurück.
        
        Args:
            player_info: Informationen über den Spieler
            topic: Dialogthema (verwendet current_dialogue_state wenn None)
            
        Returns:
            Dialog-Informationen
        """
        if topic:
            self.current_dialogue_state = topic
        
        # Suche passenden Dialog
        dialogue = self.dialogue_tree.get(self.current_dialogue_state, {})
        
        # Prüfe Bedingungen für Dialogoptionen
        available_options = []
        for option in dialogue.get("options", []):
            if self._check_dialogue_condition(option, player_info):
                available_options.append({
                    "text": option["text"],
                    "topic": option["next_topic"]
                })
        
        # Formatiere Text mit Spielerinformationen
        dialogue_text = dialogue.get("text", "...")
        if "{player_name}" in dialogue_text:
            dialogue_text = dialogue_text.replace("{player_name}", player_info.get("name", "Abenteurer"))
        
        return {
            "text": dialogue_text,
            "options": available_options,
            "speaker": self.name,
            "mood": self.current_mood
        }
    
    def _check_dialogue_condition(self, option: Dict[str, Any], player_info: Dict[str, Any]) -> bool:
        """
        Prüft, ob eine Dialogoption für den Spieler verfügbar sein sollte.
        
        Args:
            option: Dialogoption
            player_info: Informationen über den Spieler
            
        Returns:
            True, wenn die Option verfügbar ist, sonst False
        """
        if "condition" not in option:
            return True
        
        condition = option["condition"]
        
        # Prüfe Questbedingungen
        if "quest_completed" in condition:
            quest_id = condition["quest_completed"]
            if quest_id not in player_info.get("completed_quests", []):
                return False
        
        if "quest_active" in condition:
            quest_id = condition["quest_active"]
            if quest_id not in player_info.get("active_quests", []):
                return False
        
        if "quest_not_started" in condition:
            quest_id = condition["quest_not_started"]
            if (quest_id in player_info.get("active_quests", []) or 
                quest_id in player_info.get("completed_quests", [])):
                return False
        
        # Prüfe Level-Anforderung
        if "min_level" in condition:
            min_level = condition["min_level"]
            if player_info.get("level", 1) < min_level:
                return False
        
        # Prüfe Beziehungsanforderung
        if "min_relation" in condition:
            min_relation = condition["min_relation"]
            relation_value = player_info.get("npc_relations", {}).get(self.id, 0)
            if relation_value < min_relation:
                return False
        
        # Prüfe Attributsanforderung
        if "min_attribute" in condition:
            for attr, value in condition["min_attribute"].items():
                if player_info.get("attributes", {}).get(attr, 0) < value:
                    return False
        
        return True
    
    def get_merchant_inventory(self) -> List[Dict[str, Any]]:
        """
        Gibt das aktuelle Warenangebot des Händlers zurück.
        
        Returns:
            Liste von Handelsgegenständen mit Preisen
        """
        if not self.is_merchant:
            return []
        
        return [
            {
                "item_id": item["item_id"],
                "quantity": item.get("quantity", 1),
                "price": int(item["base_price"] * self.sell_rate)
            }
            for item in self.inventory
        ]
    
    def get_buy_price(self, item_id: str, base_price: int) -> int:
        """
        Berechnet den Preis, den der Händler für einen Gegenstand zahlt.
        
        Args:
            item_id: ID des Gegenstands
            base_price: Basispreis des Gegenstands
            
        Returns:
            Kaufpreis
        """
        return int(base_price * self.buy_rate)
    
    def get_available_quests(self, player_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Gibt die für den Spieler verfügbaren Quests zurück.
        
        Args:
            player_info: Informationen über den Spieler
            
        Returns:
            Liste von verfügbaren Quests
        """
        if not self.is_quest_giver:
            return []
        
        available = []
        completed_quests = player_info.get("completed_quests", [])
        active_quests = player_info.get("active_quests", [])
        player_level = player_info.get("level", 1)
        
        for quest_info in self.available_quests:
            quest_id = quest_info["quest_id"]
            
            # Überspringen, wenn Quest bereits aktiv oder abgeschlossen ist
            if quest_id in active_quests or quest_id in completed_quests:
                continue
            
            # Überspringen, wenn Spieler nicht das erforderliche Level hat
            if player_level < quest_info.get("min_level", 1):
                continue
            
            # Überspringen, wenn Voraussetzungsquests nicht abgeschlossen sind
            prerequisites = quest_info.get("prerequisites", [])
            if not all(prereq_id in completed_quests for prereq_id in prerequisites):
                continue
            
            available.append({
                "quest_id": quest_id,
                "title": quest_info["title"],
                "preview_text": quest_info.get("preview_text", "Eine Quest ist verfügbar.")
            })
        
        return available
    
    def get_training_options(self, player_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Gibt die verfügbaren Trainingsoptionen für den Spieler zurück.
        
        Args:
            player_info: Informationen über den Spieler
            
        Returns:
            Liste von verfügbaren Trainingsoptionen
        """
        if not self.is_trainer:
            return []
        
        available = []
        player_skills = player_info.get("known_skills", [])
        player_level = player_info.get("level", 1)
        
        for option in self.training_options:
            skill_id = option["skill_id"]
            
            # Überspringen, wenn Spieler den Skill bereits beherrscht
            if skill_id in player_skills:
                continue
            
            # Überspringen, wenn Spieler nicht das erforderliche Level hat
            if player_level < option.get("min_level", 1):
                continue
            
            # Überspringen, wenn Spieler nicht die erforderlichen Attribute hat
            attributes_required = option.get("attribute_requirements", {})
            player_attributes = player_info.get("attributes", {})
            
            if any(player_attributes.get(attr, 0) < value for attr, value in attributes_required.items()):
                continue
            
            available.append({
                "skill_id": skill_id,
                "name": option["name"],
                "description": option["description"],
                "cost": option["cost"]
            })
        
        return available
