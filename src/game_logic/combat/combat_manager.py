"""
Combat Manager Module

Koordiniert den Kampfablauf zwischen Spielern und Gegnern.
"""

import logging
from typing import Dict, List, Optional, Any

from src.game_logic.entity.base_entity import Entity
from src.game_logic.entity.player import Player
from src.game_logic.entity.enemy import Enemy
from src.game_logic.combat.initiative.initiative_manager import InitiativeManager
from src.game_logic.combat.actions.action_resolver import ActionResolver
from src.game_logic.combat.rewards.reward_calculator import RewardCalculator

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class CombatManager:
    """
    Verwaltet den Kampfablauf zwischen Spielern und Gegnern.
    
    Diese Klasse koordiniert den gesamten Kampfprozess und delegiert
    spezifische Aufgaben an spezialisierte Manager-Klassen.
    """
    
    def __init__(self) -> None:
        """
        Initialisiert einen neuen CombatManager.
        """
        self.players: List[Player] = []
        self.enemies: List[Enemy] = []
        self.initiative_manager = InitiativeManager()
        self.action_resolver = ActionResolver()
        self.reward_calculator = RewardCalculator()
        self.current_round: int = 0
        self.combat_active: bool = False
        self.combat_log: List[str] = []
        
        logger.info("Combat Manager initialisiert")
    
    def start_combat(self, players: List[Player], enemies: List[Enemy]) -> Dict[str, Any]:
        """
        Startet einen neuen Kampf zwischen den angegebenen Spielern und Gegnern.
        
        Args:
            players: Liste der teilnehmenden Spieler
            enemies: Liste der teilnehmenden Gegner
            
        Returns:
            Dictionary mit Informationen zum gestarteten Kampf
        """
        self.players = players
        self.enemies = enemies
        self.current_round = 1
        self.combat_active = True
        self.combat_log = []
        
        # Initialisiere Action Resolver
        self.action_resolver.initialize_combat_stats(enemies)
        
        # Berechne Initiative und setze Reihenfolge
        all_entities = players + enemies
        initiative_order = self.initiative_manager.calculate_initiative(all_entities)
        
        logger.info(f"Kampf gestartet: {len(players)} Spieler gegen {len(enemies)} Gegner")
        
        message = "Der Kampf beginnt!\n\n"
        message += "Teilnehmende Spieler:\n"
        for player in players:
            message += f"- {player.name} (HP: {player.current_hp}/{player.max_hp})\n"
        
        message += "\nGegner:\n"
        for enemy in enemies:
            message += f"- {enemy.name} (HP: {enemy.current_hp}/{enemy.max_hp})\n"
        
        message += f"\nRunde 1 beginnt. {initiative_order[0].name} ist am Zug."
        self.combat_log.append(message)
        
        return {
            "success": True,
            "message": message,
            "initiative_order": [entity.name for entity in initiative_order],
            "current_entity": initiative_order[0].name,
        }
    
    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt eine Aktion für die aktuelle Entität aus.
        
        Args:
            action: Dictionary mit Informationen zur auszuführenden Aktion
            
        Returns:
            Dictionary mit Informationen zum Ergebnis der Aktion
        """
        if not self.combat_active:
            return {"success": False, "message": "Der Kampf ist nicht aktiv."}
        
        current_entity = self.initiative_manager.get_current_entity()
        all_entities = self.players + self.enemies
        
        # Führe die Aktion aus
        results = self.action_resolver.resolve_action(action, current_entity, all_entities)
        
        # Wenn die Aktion erfolgreich war
        if results.get("success", False):
            if "message" in results:
                self.combat_log.append(results["message"])
            
            # Wenn eine Entität geflohen ist, entferne sie aus den Listen
            if results.get("fled", False) and "entity_id" in results:
                fled_entity_id = results["entity_id"]
                self.players = [p for p in self.players if p.unique_id != fled_entity_id]
                self.enemies = [e for e in self.enemies if e.unique_id != fled_entity_id]
            
            # Prüfe, ob der Kampf beendet ist
            if self._check_combat_end():
                results["combat_end"] = True
                results["winner"] = "players" if any(player.is_alive() for player in self.players) else "enemies"
                
                # Berechne Belohnungen, wenn Spieler gewonnen haben
                if results["winner"] == "players":
                    defeated_enemies = [e for e in self.enemies if not e.is_alive()]
                    xp_info = self.reward_calculator.calculate_experience(defeated_enemies, self.players)
                    loot = self.reward_calculator.calculate_loot(defeated_enemies)
                    
                    results["experience_reward"] = xp_info
                    results["loot"] = loot
                    
                    # Verteile die Belohnungen an die Spieler
                    reward_results = self.reward_calculator.distribute_rewards(
                        self.players, xp_info["player_xp"], loot
                    )
                    
                    results["reward_distribution"] = reward_results
            else:
                # Gehe zur nächsten Entität
                next_entity, new_round, message = self.initiative_manager.advance_to_next_entity(
                    self.players + self.enemies
                )
                
                if new_round:
                    self.current_round = self.initiative_manager.current_round
                    self._process_round_effects()
                    self.combat_log.append(message)
                
                if next_entity:
                    results["next_entity"] = next_entity.name
                else:
                    # Keine gültige nächste Entität gefunden, prüfe auf Kampfende
                    self._check_combat_end()
                    results["combat_end"] = True
                    results["winner"] = "undecided"
        
        return results
    
    def _process_round_effects(self) -> None:
        """
        Verarbeitet Effekte, die zu Beginn einer neuen Runde auftreten.
        """
        # Verarbeite Rundeneffekte für alle lebenden Entitäten
        all_entities = self.players + self.enemies
        for entity in all_entities:
            if entity.is_alive():
                entity.handle_turn_start()
    
    def _check_combat_end(self) -> bool:
        """
        Prüft, ob der Kampf beendet ist.
        
        Ein Kampf ist beendet, wenn entweder alle Spieler oder alle Gegner besiegt sind.
        
        Returns:
            True, wenn der Kampf beendet ist, sonst False
        """
        # Prüfe, ob alle Spieler besiegt sind
        all_players_defeated = True
        for player in self.players:
            if player.is_alive():
                all_players_defeated = False
                break
        
        if all_players_defeated:
            self.combat_active = False
            logger.info("Kampf beendet: Alle Spieler wurden besiegt.")
            self.combat_log.append("Alle Spieler wurden besiegt. Der Kampf ist vorbei.")
            return True
        
        # Prüfe, ob alle Gegner besiegt sind
        all_enemies_defeated = True
        for enemy in self.enemies:
            if enemy.is_alive():
                all_enemies_defeated = False
                break
        
        if all_enemies_defeated:
            self.combat_active = False
            logger.info("Kampf beendet: Alle Gegner wurden besiegt.")
            self.combat_log.append("Alle Gegner wurden besiegt. Der Kampf ist vorbei.")
            return True
        
        # Der Kampf ist noch nicht beendet
        return False
    
    def get_combat_summary(self) -> Dict[str, Any]:
        """
        Gibt eine Zusammenfassung des aktuellen Kampfes zurück.
        
        Returns:
            Dictionary mit Informationen zum aktuellen Kampfzustand
        """
        return {
            "active": self.combat_active,
            "round": self.current_round,
            "players": [
                {
                    "name": player.name,
                    "id": player.unique_id,
                    "current_hp": player.current_hp,
                    "max_hp": player.max_hp,
                    "status_effects": [effect_id for effect_id in player.status_effects]
                }
                for player in self.players
            ],
            "enemies": [
                {
                    "name": enemy.name,
                    "id": enemy.unique_id,
                    "current_hp": enemy.current_hp,
                    "max_hp": enemy.max_hp,
                    "status_effects": [effect_id for effect_id in enemy.status_effects]
                }
                for enemy in self.enemies
            ],
            "initiative_order": self.initiative_manager.get_initiative_order_names(),
            "current_entity": self.initiative_manager.get_current_entity().name if self.combat_active else None,
            "statistics": self.action_resolver.get_statistics(),
            "log": self.combat_log[-10:] if self.combat_log else []  # Die letzten 10 Einträge
        }
    
    def get_current_entity(self) -> Optional[Entity]:
        """
        Gibt die aktuelle Entität zurück, die am Zug ist.
        
        Returns:
            Die aktuelle Entität oder None, wenn kein Kampf aktiv ist
        """
        if not self.combat_active:
            return None
        
        return self.initiative_manager.get_current_entity()
    
    def get_valid_targets(self, action_type: str, source: Entity) -> List[Dict[str, Any]]:
        """
        Gibt eine Liste der gültigen Ziele für eine bestimmte Aktion zurück.
        
        Args:
            action_type: Typ der Aktion ("attack", "skill", "item")
            source: Entität, die die Aktion ausführt
            
        Returns:
            Liste von gültigen Zielen mit ID und Namen
        """
        valid_targets = []
        
        if isinstance(source, Player):
            # Spieler können Gegner angreifen oder mit manchen Skills Verbündete unterstützen
            if action_type == "attack":
                for enemy in self.enemies:
                    if enemy.is_alive():
                        valid_targets.append({
                            "id": enemy.unique_id,
                            "name": enemy.name,
                            "type": "enemy"
                        })
            elif action_type == "skill":
                # Bei Skills können je nach Typ Gegner oder Verbündete gültig sein
                # (Hier vereinfacht - in vollem Spiel würden wir den Skill-Typ prüfen)
                for enemy in self.enemies:
                    if enemy.is_alive():
                        valid_targets.append({
                            "id": enemy.unique_id,
                            "name": enemy.name,
                            "type": "enemy"
                        })
                
                for player in self.players:
                    if player.is_alive():
                        valid_targets.append({
                            "id": player.unique_id,
                            "name": player.name,
                            "type": "player"
                        })
            elif action_type == "item":
                # Ähnlich wie bei Skills
                for enemy in self.enemies:
                    if enemy.is_alive():
                        valid_targets.append({
                            "id": enemy.unique_id,
                            "name": enemy.name,
                            "type": "enemy"
                        })
                
                for player in self.players:
                    if player.is_alive():
                        valid_targets.append({
                            "id": player.unique_id,
                            "name": player.name,
                            "type": "player"
                        })
        
        elif isinstance(source, Enemy):
            # Gegner zielen hauptsächlich auf Spieler ab
            if action_type in ["attack", "skill"]:
                for player in self.players:
                    if player.is_alive():
                        valid_targets.append({
                            "id": player.unique_id,
                            "name": player.name,
                            "type": "player"
                        })
            # Manche Gegner könnten andere Gegner heilen etc.
            if action_type == "skill":
                for enemy in self.enemies:
                    if enemy != source and enemy.is_alive():
                        valid_targets.append({
                            "id": enemy.unique_id,
                            "name": enemy.name,
                            "type": "enemy"
                        })
        
        return valid_targets
