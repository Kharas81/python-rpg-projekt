"""
Reward Calculator Module

Berechnet Erfahrungspunkte und Beute für erfolgreiche Kämpfe.
"""

import logging
from typing import Dict, List, Any

from src.game_logic.entity.enemy import Enemy
from src.game_logic.entity.player import Player

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class RewardCalculator:
    """
    Berechnet Erfahrung und Beute für erfolgreiche Kämpfe.
    
    Diese Klasse ist verantwortlich für die Berechnung von Erfahrungspunkten
    und das Generieren von Beute nach einem erfolgreichen Kampf.
    """
    
    def __init__(self) -> None:
        """
        Initialisiert einen neuen RewardCalculator.
        """
        pass
    
    def calculate_experience(self, defeated_enemies: List[Enemy], 
                            participating_players: List[Player]) -> Dict[str, Any]:
        """
        Berechnet die Erfahrungspunkte für einen erfolgreichen Kampf.
        
        Args:
            defeated_enemies: Liste der besiegten Gegner
            participating_players: Liste der teilnehmenden Spieler
            
        Returns:
            Dictionary mit Informationen zur EP-Belohnung
        """
        total_xp = 0
        for enemy in defeated_enemies:
            total_xp += enemy.experience_reward
        
        # Verteile EP gleichmäßig auf alle Spieler
        xp_per_player = total_xp // len(participating_players) if participating_players else 0
        
        # Speichere die EP pro Spieler
        player_xp = {}
        for player in participating_players:
            player_xp[player.unique_id] = xp_per_player
        
        logger.info(f"Erfahrungsbelohnung: {total_xp} EP gesamt, {xp_per_player} EP pro Spieler")
        
        return {
            "total_xp": total_xp,
            "xp_per_player": xp_per_player,
            "player_xp": player_xp
        }
    
    def calculate_loot(self, defeated_enemies: List[Enemy]) -> List[Dict[str, Any]]:
        """
        Berechnet die Beute von besiegten Gegnern.
        
        Args:
            defeated_enemies: Liste der besiegten Gegner
            
        Returns:
            Liste von Beute-Items
        """
        all_loot = []
        
        for enemy in defeated_enemies:
            enemy_loot = enemy.get_loot()
            all_loot.extend(enemy_loot)
        
        logger.info(f"Beute: {len(all_loot)} Gegenstände")
        return all_loot
    
    def distribute_rewards(self, players: List[Player], 
                          xp_rewards: Dict[str, int],
                          loot: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verteilt Belohnungen an die Spieler.
        
        Args:
            players: Liste der Spieler
            xp_rewards: Dictionary mit EP pro Spieler
            loot: Liste der Beute-Items
            
        Returns:
            Dictionary mit Informationen zu den verteilten Belohnungen
        """
        results = {
            "player_level_ups": {},
            "distributed_loot": {}
        }
        
        # Verteile EP an Spieler
        for player in players:
            if player.unique_id in xp_rewards:
                xp = xp_rewards[player.unique_id]
                level_up_info = player.gain_experience(xp)
                
                if level_up_info["old_level"] != level_up_info["new_level"]:
                    results["player_level_ups"][player.unique_id] = level_up_info
        
        # Hier würde die Beute-Verteilung implementiert werden, falls ein Inventarsystem existiert
        # Für jetzt speichern wir einfach die gesamte Beute
        results["distributed_loot"] = loot
        
        return results
