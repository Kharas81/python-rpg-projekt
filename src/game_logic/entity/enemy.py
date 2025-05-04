"""
Enemy Module

Dieses Modul definiert die Enemy-Klasse, die die speziellen Eigenschaften
und Funktionen für feindliche Charaktere implementiert.
"""

import logging
import random
from typing import Dict, Any, List, Optional, Tuple

from src.game_logic.entity.base_entity import Entity
from src.game_logic.entity.entity_types import EntityType

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class Enemy(Entity):
    """
    Klasse für einen feindlichen Charakter.
    
    Diese Klasse erweitert die Basisentität um feindspezifische Funktionalität
    wie Beute, KI-Verhalten und spezielle Fähigkeiten.
    """
    
    def __init__(self, enemy_id: str, data_dict: Dict[str, Any]) -> None:
        """
        Initialisiert einen neuen Feind.
        
        Args:
            enemy_id: Eindeutige ID für den Feind (z.B. "goblin", "dragon")
            data_dict: Dictionary mit den Daten des Feindes aus der JSON-Datei
        """
        # Rufe den Konstruktor der Elternklasse auf
        super().__init__(enemy_id, EntityType.ENEMY, data_dict)
        
        # Feindspezifische Eigenschaften
        self.experience_reward = data_dict.get("experience_reward", self.level * 10)
        self.gold_reward = data_dict.get("gold_reward", self.level * 5)
        
        # Beute-Tabelle
        self.loot_table = data_dict.get("loot_table", [])
        
        # KI-Verhaltensmuster für den Kampf
        self.aggression = data_dict.get("aggression", 0.5)  # 0.0 - 1.0, höher = aggressiver
        self.target_preference = data_dict.get("target_preference", "lowest_hp")  # lowest_hp, highest_threat, random
        self.flee_threshold = data_dict.get("flee_threshold", 0.2)  # HP-Prozentsatz für Fluchtversuch
        
        # Special Modifiers für bestimmte Feindtypen
        self.is_elite = data_dict.get("is_elite", False)
        self.is_boss = data_dict.get("is_boss", False)
        
        if self.is_elite:
            # Elite-Gegner sind stärker
            self._apply_elite_modifiers()
        
        if self.is_boss:
            # Bosse sind deutlich stärker
            self._apply_boss_modifiers()
        
        logger.info(f"Feind erstellt: {self.name} (Level {self.level}, HP: {self.current_hp})")
    
    def _apply_elite_modifiers(self) -> None:
        """
        Wendet Elite-Modifikatoren auf den Feind an.
        """
        # Erhöhe HP um 50%
        self.max_hp = int(self.max_hp * 1.5)
        self.current_hp = self.max_hp
        
        # Erhöhe Schaden und Verteidigung
        self.armor = int(self.armor * 1.2)
        self.magic_resistance = int(self.magic_resistance * 1.2)
        
        # Erhöhe Belohnungen
        self.experience_reward = int(self.experience_reward * 1.5)
        self.gold_reward = int(self.gold_reward * 1.5)
        
        # Füge "Elite" zum Namen hinzu
        self.name = f"Elite {self.name}"
    
    def _apply_boss_modifiers(self) -> None:
        """
        Wendet Boss-Modifikatoren auf den Feind an.
        """
        # Erhöhe HP um 200%
        self.max_hp = int(self.max_hp * 3)
        self.current_hp = self.max_hp
        
        # Erhöhe Schaden und Verteidigung
        self.armor = int(self.armor * 1.5)
        self.magic_resistance = int(self.magic_resistance * 1.5)
        
        # Erhöhe Belohnungen
        self.experience_reward = int(self.experience_reward * 3)
        self.gold_reward = int(self.gold_reward * 3)
    
    def select_action(self, battle_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wählt eine Aktion basierend auf dem aktuellen Kampfzustand.
        
        Diese Methode implementiert die KI-Logik für feindliche Entitäten.
        
        Args:
            battle_state: Zustand des Kampfes, einschließlich aller Entitäten
            
        Returns:
            Dictionary mit der ausgewählten Aktion
        """
        # Prüfe, ob der Feind fliehen sollte
        if (self.current_hp / self.max_hp) <= self.flee_threshold and not self.is_boss:
            flee_chance = 0.3 - (0.05 * len(battle_state["players"]))  # Erschwert mit mehr Spielern
            if random.random() < flee_chance:
                logger.info(f"{self.name} versucht zu fliehen!")
                return {
                    "type": "flee",
                    "source": self.unique_id
                }
        
        # Entscheide zwischen normalem Angriff und Skill
        if len(self.known_skills) > 0 and random.random() < 0.4:  # 40% Chance, einen Skill zu benutzen
            # Wähle zufälligen Skill
            usable_skills = [skill for skill in self.known_skills if self.can_use_skill(skill)]
            
            if usable_skills:
                selected_skill = random.choice(usable_skills)
                target = self._select_target(battle_state)
                
                logger.debug(f"{self.name} verwendet Skill {selected_skill} gegen {target['name']}")
                
                return {
                    "type": "skill",
                    "skill_id": selected_skill,
                    "source": self.unique_id,
                    "targets": [target["id"]]
                }
        
        # Standard-Angriff
        target = self._select_target(battle_state)
        
        logger.debug(f"{self.name} greift {target['name']} an")
        
        return {
            "type": "attack",
            "source": self.unique_id,
            "target": target["id"]
        }
    
    def _select_target(self, battle_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wählt ein Ziel für eine Aktion basierend auf der Zielauswahlstrategie.
        
        Args:
            battle_state: Zustand des Kampfes
            
        Returns:
            Ziel-Entity-Informationen
        """
        # Spieler als mögliche Ziele
        players = battle_state["players"]
        
        # Entferne besiegte Spieler von der Zielliste
        valid_targets = [p for p in players if p["current_hp"] > 0]
        
        if not valid_targets:
            # Keine gültigen Ziele, nimm irgendeinen Spieler (sollte nicht passieren)
            return random.choice(players)
        
        # Wähle Ziel basierend auf der Zielstrategie
        if self.target_preference == "lowest_hp":
            # Ziele auf den Spieler mit den wenigsten HP
            return min(valid_targets, key=lambda p: p["current_hp"])
        
        elif self.target_preference == "highest_threat":
            # Ziele auf den Spieler, der die größte Bedrohung darstellt (z.B. meisten Schaden verursacht hat)
            if "threat" in battle_state:
                return max(valid_targets, key=lambda p: battle_state["threat"].get(p["id"], 0))
            else:
                return random.choice(valid_targets)
        
        else:  # "random" oder unbekannte Strategie
            # Zufälliges Ziel wählen
            return random.choice(valid_targets)
    
    def get_loot(self) -> List[Dict[str, Any]]:
        """
        Generiert Beute basierend auf der Beute-Tabelle des Feindes.
        
        Returns:
            Liste von Beute-Gegenständen
        """
        loot_items = []
        
        for loot_entry in self.loot_table:
            chance = loot_entry.get("chance", 1.0)
            if random.random() <= chance:
                # Gegenstand fällt, füge ihn zur Beute hinzu
                item_id = loot_entry["item_id"]
                min_quantity = loot_entry.get("min_quantity", 1)
                max_quantity = loot_entry.get("max_quantity", 1)
                quantity = random.randint(min_quantity, max_quantity)
                
                loot_items.append({
                    "item_id": item_id,
                    "quantity": quantity
                })
        
        # Füge Gold hinzu (mit zufälliger Variation)
        gold_variation = random.uniform(0.8, 1.2)
        gold_amount = int(self.gold_reward * gold_variation)
        
        loot_items.append({
            "item_id": "gold",
            "quantity": gold_amount
        })
        
        logger.debug(f"{self.name} lässt {len(loot_items)} Gegenstände fallen")
        
        return loot_items
