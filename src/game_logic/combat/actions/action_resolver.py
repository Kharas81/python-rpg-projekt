"""
Action Resolver Module

Verarbeitet und löst Kampfaktionen zwischen Entitäten auf.
"""

import logging
import random
from typing import Dict, List, Optional, Any

from src.game_logic.entity.base_entity import Entity
from src.game_logic.entity.player import Player
from src.game_logic.entity.enemy import Enemy

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class ActionResolver:
    """
    Löst Kampfaktionen zwischen Entitäten auf.
    
    Diese Klasse ist verantwortlich für die Ausführung von Angriffen,
    Skills, Fluchtversuchen und Item-Nutzungen im Kampf.
    """
    
    def __init__(self) -> None:
        """
        Initialisiert einen neuen ActionResolver.
        """
        self.threat_table: Dict[str, Dict[str, int]] = {}
        self.damage_dealt: Dict[str, int] = {}
        self.damage_taken: Dict[str, int] = {}
        self.healing_done: Dict[str, int] = {}
    
    def initialize_combat_stats(self, enemies: List[Enemy]) -> None:
        """
        Initialisiert die Kampfstatistiken für einen neuen Kampf.
        
        Args:
            enemies: Liste der Gegner im Kampf
        """
        self.threat_table = {enemy.unique_id: {} for enemy in enemies}
        self.damage_dealt = {}
        self.damage_taken = {}
        self.healing_done = {}
    
    def resolve_action(self, action: Dict[str, Any], entity: Entity, 
                      all_entities: List[Entity]) -> Dict[str, Any]:
        """
        Verarbeitet eine Kampfaktion und gibt das Ergebnis zurück.
        
        Args:
            action: Dictionary mit Informationen zur Aktion
            entity: Entität, die die Aktion ausführt
            all_entities: Liste aller Entitäten im Kampf
            
        Returns:
            Dictionary mit Informationen zum Ergebnis der Aktion
        """
        if not entity.can_act:
            logger.info(f"{entity.name} kann nicht handeln.")
            return {
                "success": True,
                "message": f"{entity.name} ist betäubt und kann nicht handeln.",
                "skipped": True
            }
        
        action_type = action.get("type", "")
        
        if action_type == "attack":
            target_id = action.get("target", "")
            target = self._find_entity_by_id(target_id, all_entities)
            
            if target:
                return self._execute_attack(entity, target)
            else:
                return {"success": False, "message": "Ungültiges Ziel."}
        
        elif action_type == "skill":
            skill_id = action.get("skill_id", "")
            target_ids = action.get("targets", [])
            targets = [self._find_entity_by_id(target_id, all_entities) for target_id in target_ids]
            targets = [target for target in targets if target]  # Entferne None-Werte
            
            if targets:
                return self._execute_skill(entity, skill_id, targets)
            else:
                return {"success": False, "message": "Ungültiges Ziel."}
        
        elif action_type == "flee":
            return self._execute_flee(entity, all_entities)
        
        elif action_type == "item":
            item_id = action.get("item_id", "")
            target_id = action.get("target", "")
            target = self._find_entity_by_id(target_id, all_entities)
            
            if target:
                return self._execute_use_item(entity, item_id, target)
            else:
                return {"success": False, "message": "Ungültiges Ziel."}
        
        else:
            return {"success": False, "message": "Ungültige Aktion."}
    
    def _find_entity_by_id(self, entity_id: str, all_entities: List[Entity]) -> Optional[Entity]:
        """
        Findet eine Entität anhand ihrer ID.
        
        Args:
            entity_id: ID der zu findenden Entität
            all_entities: Liste aller Entitäten im Kampf
            
        Returns:
            Die gefundene Entität oder None, wenn keine Entität mit der ID gefunden wurde
        """
        for entity in all_entities:
            if entity.unique_id == entity_id:
                return entity
        return None
    
    def _execute_attack(self, attacker: Entity, target: Entity) -> Dict[str, Any]:
        """
        Führt einen normalen Angriff aus.
        
        Args:
            attacker: Angreifende Entität
            target: Ziel des Angriffs
            
        Returns:
            Dictionary mit Informationen zum Ergebnis des Angriffs
        """
        # Berechne Trefferchance
        hit_chance = 0.9  # Basis-Trefferchance
        hit_chance += attacker.get_hit_chance_modifier() * 0.03  # Genauigkeitsbonus
        hit_chance -= target.get_evasion_modifier() * 0.02  # Ausweichbonus
        
        # Begrenze Trefferchance
        hit_chance = max(0.05, min(0.95, hit_chance))
        
        # Würfeln für Treffer
        hit_roll = random.random()
        
        if hit_roll > hit_chance:
            # Angriff verfehlt
            message = f"{attacker.name} greift {target.name} an, aber verfehlt!"
            logger.debug(f"Angriff verfehlt: {hit_roll:.2f} > {hit_chance:.2f}")
            return {
                "success": True,
                "hit": False,
                "message": message
            }
        
        # Bestimme den passenden Basis-Skill basierend auf der Entität
        skill_id = self._determine_basic_attack_skill(attacker)
        
        # Führe den Basis-Skill aus
        skill_results = attacker.use_skill(skill_id, [target])
        
        # Aktualisiere Bedrohungstabelle und Schadensstatistik
        if isinstance(target, Enemy) and isinstance(attacker, Player):
            enemy_id = target.unique_id
            if enemy_id in self.threat_table:
                self.threat_table[enemy_id][attacker.unique_id] = self.threat_table[enemy_id].get(attacker.unique_id, 0) + 10
        
        # Erhöhe die Schadensstatistik
        if "targets" in skill_results:
            for target_id, effects in skill_results["targets"].items():
                for effect in effects:
                    if effect["type"] == "damage":
                        self.damage_dealt[attacker.unique_id] = self.damage_dealt.get(attacker.unique_id, 0) + effect["amount"]
                        self.damage_taken[target_id] = self.damage_taken.get(target_id, 0) + effect["amount"]
        
        return {
            "success": True,
            "hit": True,
            "message": skill_results.get("message", f"{attacker.name} greift {target.name} an."),
            "skill_results": skill_results
        }
    
    def _determine_basic_attack_skill(self, entity: Entity) -> str:
        """
        Bestimmt den grundlegenden Angriffsskill für eine Entität.
        
        Args:
            entity: Die Entität, für die der Skill bestimmt werden soll
            
        Returns:
            ID des passenden Basis-Angriffsskills
        """
        if isinstance(entity, Player):
            if entity.character_class == "warrior":
                return "basic_strike_phys"
            elif entity.character_class == "rogue":
                return "basic_strike_finesse"
            elif entity.character_class == "mage":
                return "basic_magic_bolt"
            elif entity.character_class == "cleric":
                return "basic_holy_spark"
            else:
                return "basic_strike_phys"
        else:
            # Für Gegner basierend auf ihrem entity_id Präfix
            if "skelett" in entity.id.lower():
                return "basic_strike_phys"
            elif "goblin" in entity.id.lower():
                return "basic_strike_phys"
            elif "ratte" in entity.id.lower():
                return "basic_strike_finesse"
            else:
                return "basic_strike_phys"  # Fallback
    
    def _execute_skill(self, caster: Entity, skill_id: str, targets: List[Entity]) -> Dict[str, Any]:
        """
        Führt einen Skill aus.
        
        Args:
            caster: Entität, die den Skill ausführt
            skill_id: ID des auszuführenden Skills
            targets: Liste der Ziele
            
        Returns:
            Dictionary mit Informationen zum Ergebnis des Skills
        """
        # Prüfe, ob der Skill eingesetzt werden kann
        if not caster.can_use_skill(skill_id):
            return {
                "success": False,
                "message": f"{caster.name} kann den Skill '{skill_id}' nicht einsetzen."
            }
        
        # Führe den Skill aus
        skill_results = caster.use_skill(skill_id, targets)
        
        # Aktualisiere Bedrohungstabelle und Schadensstatistik
        for target in targets:
            if isinstance(target, Enemy) and isinstance(caster, Player):
                enemy_id = target.unique_id
                if enemy_id in self.threat_table:
                    self.threat_table[enemy_id][caster.unique_id] = self.threat_table[enemy_id].get(caster.unique_id, 0) + 15
        
        # Erhöhe die Schadensstatistik
        if "targets" in skill_results:
            for target_id, effects in skill_results["targets"].items():
                for effect in effects:
                    if effect["type"] == "damage":
                        self.damage_dealt[caster.unique_id] = self.damage_dealt.get(caster.unique_id, 0) + effect["amount"]
                        self.damage_taken[target_id] = self.damage_taken.get(target_id, 0) + effect["amount"]
                    elif effect["type"] == "healing":
                        self.healing_done[caster.unique_id] = self.healing_done.get(caster.unique_id, 0) + effect["amount"]
        
        return {
            "success": True,
            "message": skill_results.get("message", f"{caster.name} setzt {skill_id} ein."),
            "skill_results": skill_results
        }
    
    def _execute_flee(self, entity: Entity, all_entities: List[Entity]) -> Dict[str, Any]:
        """
        Führt einen Fluchtversuch aus.
        
        Args:
            entity: Entität, die fliehen möchte
            all_entities: Liste aller Entitäten im Kampf
            
        Returns:
            Dictionary mit Informationen zum Ergebnis des Fluchtversuchs
        """
        # Spieler können immer fliehen (für einfaches Spiel)
        if isinstance(entity, Player):
            message = f"{entity.name} ist aus dem Kampf geflohen!"
            logger.info(message)
            
            return {
                "success": True,
                "fled": True,
                "entity_id": entity.unique_id,
                "message": message
            }
        
        # Gegner haben eine Chance zu fliehen basierend auf ihrer Gesundheit
        if isinstance(entity, Enemy):
            hp_percentage = entity.current_hp / entity.max_hp
            flee_chance = 0.3 - (0.2 * hp_percentage)  # Höhere Chance bei weniger HP
            
            if random.random() < flee_chance:
                message = f"{entity.name} ist aus dem Kampf geflohen!"
                logger.info(message)
                
                return {
                    "success": True,
                    "fled": True,
                    "entity_id": entity.unique_id,
                    "message": message
                }
            
            message = f"{entity.name} versucht zu fliehen, wird aber daran gehindert!"
            logger.info(message)
            
            return {
                "success": True,
                "fled": False,
                "message": message
            }
        
        return {
            "success": False,
            "message": "Unbekannte Entität versucht zu fliehen."
        }
    
    def _execute_use_item(self, user: Entity, item_id: str, target: Entity) -> Dict[str, Any]:
        """
        Führt die Verwendung eines Items aus.
        
        Args:
            user: Entität, die das Item verwendet
            item_id: ID des zu verwendenden Items
            target: Ziel der Item-Verwendung
            
        Returns:
            Dictionary mit Informationen zum Ergebnis der Item-Verwendung
        """
        # Hier würde eine Implementierung für die Verwendung von Items folgen
        # Da dies eine separate Komponente erfordert, hier nur ein Platzhalter
        return {
            "success": False,
            "message": "Item-Verwendung noch nicht implementiert."
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Gibt Statistiken zum aktuellen Kampf zurück.
        
        Returns:
            Dictionary mit Kampfstatistiken
        """
        return {
            "threat_table": self.threat_table,
            "damage_dealt": self.damage_dealt,
            "damage_taken": self.damage_taken,
            "healing_done": self.healing_done
        }
