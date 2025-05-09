"""
Berechnet Belohnungen für RL-Agenten basierend auf Spielzuständen und Aktionen.
"""
from typing import Dict, List, Any
import numpy as np
from src.environment.env_state import EnvState
from src.config.config import get_config


class RewardCalculator:
    """
    Berechnet und verwaltet Belohnungen für RL-Agenten.
    Ermöglicht die Anpassung der Belohnungsfunktion basierend auf Konfigurationen.
    """
    
    def __init__(self):
        """
        Initialisiert den RewardCalculator mit Konfigurationsparametern.
        """
        self.config = get_config()
        
        # Lade Belohnungsparameter aus settings.json5
        rl_settings = self.config.get('rl_settings', {})
        self.rewards = rl_settings.get('rewards', {})
        
        # Standardwerte für Belohnungen
        self.victory_reward = self.rewards.get('victory', 10.0)
        self.defeat_penalty = self.rewards.get('defeat', -10.0)
        self.damage_reward_factor = self.rewards.get('damage_factor', 0.1)
        self.healing_reward_factor = self.rewards.get('healing_factor', 0.2)
        self.kill_reward = self.rewards.get('kill', 1.0)
        self.ally_death_penalty = self.rewards.get('ally_death', -1.0)
        self.effect_application_reward = self.rewards.get('effect_application', 0.5)
        self.resource_efficiency_factor = self.rewards.get('resource_efficiency', 0.05)
        self.time_penalty = self.rewards.get('time_penalty', -0.01)  # Kleine Strafe pro Runde, um schnelles Handeln zu fördern
        
    def calculate_action_reward(self, state: EnvState, action_result: Dict[str, Any]) -> float:
        """
        Berechnet die Belohnung für eine einzelne Aktion.
        
        Args:
            state: Der aktuelle Umgebungszustand.
            action_result: Das Ergebnis der ausgeführten Aktion.
            
        Returns:
            float: Die berechnete Belohnung.
        """
        reward = 0.0
        
        # Belohnung für verursachten Schaden
        reward += action_result.get('damage_dealt', 0) * self.damage_reward_factor
        
        # Belohnung für Heilung
        reward += action_result.get('healing_done', 0) * self.healing_reward_factor
        
        # Belohnung für Kill
        if action_result.get('target_killed', False):
            reward += self.kill_reward
        
        # Strafe für Tod eines Verbündeten
        if action_result.get('ally_died', False):
            reward += self.ally_death_penalty
        
        # Belohnung für angewandte Statuseffekte
        reward += len(action_result.get('status_effects_applied', [])) * self.effect_application_reward
        
        # Belohnung für Ressourceneffizienz
        # Berechne das Verhältnis von erzielter Wirkung zu verbrauchten Ressourcen
        resource_cost = action_result.get('resource_cost', 0)
        effect_value = action_result.get('damage_dealt', 0) + action_result.get('healing_done', 0) * 2
        
        if resource_cost > 0 and effect_value > 0:
            efficiency = effect_value / resource_cost
            reward += efficiency * self.resource_efficiency_factor
        
        # Kleine Zeitstrafe für jede Runde (fördert schnelles Handeln)
        reward += self.time_penalty
        
        return reward
    
    def calculate_episode_reward(self, state: EnvState) -> float:
        """
        Berechnet die finale Belohnung für eine gesamte Episode (Kampf).
        
        Args:
            state: Der Umgebungszustand am Ende der Episode.
            
        Returns:
            float: Die berechnete Episodenbelohnung.
        """
        if not state.is_done:
            return 0.0
        
        # Prüfe, ob die Spieler gewonnen haben
        all_players_defeated = all(not pc.is_alive() for pc in state.player_characters) if state.player_characters else True
        all_opponents_defeated = all(not opp.is_alive() for opp in state.opponents) if state.opponents else True
        
        reward = 0.0
        
        # Belohnung für Sieg oder Strafe für Niederlage
        if all_opponents_defeated and not all_players_defeated:
            # Sieg
            reward += self.victory_reward
            
            # Bonus basierend auf der Anzahl der überlebenden Spieler
            surviving_players = sum(1 for pc in state.player_characters if pc.is_alive())
            reward += surviving_players * self.rewards.get('surviving_ally_bonus', 0.5)
            
            # Bonus basierend auf der Effizienz des Kampfes (weniger Runden)
            max_rounds = 20  # Angenommene maximale Rundenzahl
            round_factor = max(0, (max_rounds - state.current_round) / max_rounds)
            reward += round_factor * self.rewards.get('round_efficiency_bonus', 5.0)
            
        elif all_players_defeated:
            # Niederlage
            reward += self.defeat_penalty
            
            # Bonus basierend auf der Anzahl der besiegten Gegner
            defeated_opponents = sum(1 for opp in state.opponents if not opp.is_alive())
            reward += defeated_opponents * self.rewards.get('defeated_enemy_bonus', 0.3)
        
        return reward
    
    def get_reward_info(self, state: EnvState, action_result: Dict[str, Any]) -> Dict[str, float]:
        """
        Gibt detaillierte Informationen über die Belohnungskomponenten zurück.
        Hilfreich für Debugging und Überwachung des RL-Trainings.
        
        Args:
            state: Der aktuelle Umgebungszustand.
            action_result: Das Ergebnis der ausgeführten Aktion.
            
        Returns:
            Dict[str, float]: Ein Dictionary mit den einzelnen Belohnungskomponenten.
        """
        reward_components = {}
        
        # Aktionsbelohnungen
        if 'damage_dealt' in action_result:
            reward_components['damage_reward'] = action_result['damage_dealt'] * self.damage_reward_factor
            
        if 'healing_done' in action_result:
            reward_components['healing_reward'] = action_result['healing_done'] * self.healing_reward_factor
            
        if action_result.get('target_killed', False):
            reward_components['kill_reward'] = self.kill_reward
            
        if action_result.get('ally_died', False):
            reward_components['ally_death_penalty'] = self.ally_death_penalty
            
        status_effects_count = len(action_result.get('status_effects_applied', []))
        if status_effects_count > 0:
            reward_components['effect_reward'] = status_effects_count * self.effect_application_reward
            
        # Ressourceneffizienz
        resource_cost = action_result.get('resource_cost', 0)
        effect_value = action_result.get('damage_dealt', 0) + action_result.get('healing_done', 0) * 2
        
        if resource_cost > 0 and effect_value > 0:
            efficiency = effect_value / resource_cost
            reward_components['resource_efficiency'] = efficiency * self.resource_efficiency_factor
            
        # Zeitstrafe
        reward_components['time_penalty'] = self.time_penalty
        
        # Episodenbelohnungen
        if state.is_done:
            all_players_defeated = all(not pc.is_alive() for pc in state.player_characters) if state.player_characters else True
            all_opponents_defeated = all(not opp.is_alive() for opp in state.opponents) if state.opponents else True
            
            if all_opponents_defeated and not all_players_defeated:
                reward_components['victory_reward'] = self.victory_reward
                
                surviving_players = sum(1 for pc in state.player_characters if pc.is_alive())
                reward_components['surviving_ally_bonus'] = surviving_players * self.rewards.get('surviving_ally_bonus', 0.5)
                
                max_rounds = 20
                round_factor = max(0, (max_rounds - state.current_round) / max_rounds)
                reward_components['round_efficiency_bonus'] = round_factor * self.rewards.get('round_efficiency_bonus', 5.0)
                
            elif all_players_defeated:
                reward_components['defeat_penalty'] = self.defeat_penalty
                
                defeated_opponents = sum(1 for opp in state.opponents if not opp.is_alive())
                reward_components['defeated_enemy_bonus'] = defeated_opponents * self.rewards.get('defeated_enemy_bonus', 0.3)
        
        # Gesamtbelohnung
        reward_components['total_reward'] = sum(reward_components.values())
        
        return reward_components
