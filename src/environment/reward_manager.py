# src/environment/reward_manager.py
"""
Verwaltet die Berechnung der Rewards für die RL-Umgebung.
"""
import logging
from typing import List, Dict, Any, Optional, SupportsFloat

# Importiere relevante Klassen für Typ-Hinweise und Datenzugriff
if True: # Um Zirkularimporte zu vermeiden
    from src.environment.state_manager import EnvStateManager
    from src.game_logic.entities import CharacterInstance

logger = logging.getLogger(__name__)

class RewardManager:
    def __init__(self,
                 reward_config: Optional[Dict[str, float]] = None): # Konfiguration für Reward-Gewichte
        
        # Standard-Reward-Gewichte, können über reward_config überschrieben werden
        self.config = {
            "step_penalty": -0.01,          # Malus pro Schritt
            "invalid_action_penalty": -1.0,   # Strafe für Auswahl einer ungültigen/maskierten Aktion
            "no_target_penalty": -0.5,      # Strafe, wenn gültiger Skill, aber kein Ziel gefunden
            "damage_to_opponent_mult": 0.2, # Reward-Multiplikator pro Schadenspunkt an Gegnern
            "heal_hero_mult": 0.1,          # Reward-Multiplikator pro Heilpunkt am Helden
            "damage_to_hero_penalty_mult": -0.3, # Malus-Multiplikator pro Schadenspunkt am Helden
            "opponent_defeated_bonus": 10.0, # Bonus pro besiegtem Gegner
            "hero_defeated_penalty": -50.0,  # Strafe, wenn Held besiegt wird
            "all_opponents_defeated_bonus": 50.0, # Großer Bonus für Sieg
            "max_steps_reached_penalty": -10.0 # Malus, wenn Zeitlimit erreicht
        }
        if reward_config:
            self.config.update(reward_config) # Überschreibe Defaults mit übergebener Config

        logger.info(f"RewardManager initialisiert mit Konfiguration: {self.config}")

        # Um Zustandsänderungen für die Reward-Berechnung zu verfolgen
        self.hp_at_turn_start: Dict[str, int] = {} # instance_id -> hp

    def record_hp_at_turn_start(self, participants: List[CharacterInstance]):
        """Speichert die HP aller Teilnehmer zu Beginn eines Zuges."""
        self.hp_at_turn_start = {p.instance_id: p.current_hp for p in participants if p}

    def calculate_reward_for_hero_action(self, 
                                         state_manager: EnvStateManager,
                                         action_was_valid_by_mask: bool,
                                         action_was_executable: bool, # Hat StateManager.execute_hero_action True zurückgegeben?
                                         hero_skill_id: Optional[str]
                                         ) -> SupportsFloat:
        """
        Berechnet den Reward für die Aktion des Helden.
        Diese Funktion wird nach der Heldenaktion aufgerufen.
        """
        reward: SupportsFloat = self.config.get("step_penalty", -0.01)
        hero = state_manager.get_hero()
        
        if not hero: # Sollte nicht passieren
            return reward 

        if not action_was_valid_by_mask:
            reward += self.config.get("invalid_action_penalty", -1.0)
            logger.debug(f"RewardManager: Strafe für ungültige maskierte Aktion: {self.config.get('invalid_action_penalty', -1.0)}")
            return reward # Keine weiteren Rewards/Penalties für diese Aktion

        if not action_was_executable: # z.B. kein Ziel gefunden, obwohl Skill ein Ziel brauchte
            reward += self.config.get("no_target_penalty", -0.5)
            logger.debug(f"RewardManager: Strafe für nicht ausführbare Aktion (z.B. kein Ziel): {self.config.get('no_target_penalty', -0.5)}")
            return reward

        # Belohnung für Schaden an Gegnern
        for opp in state_manager.get_live_opponents(): # Iteriere nur über lebende Gegner
            if opp.instance_id in self.hp_at_turn_start:
                damage_done = self.hp_at_turn_start[opp.instance_id] - opp.current_hp
                if damage_done > 0:
                    damage_reward = damage_done * self.config.get("damage_to_opponent_mult", 0.2)
                    reward += damage_reward
                    logger.debug(f"RewardManager: +{damage_reward:.2f} für {damage_done} Schaden an {opp.name}")
                if opp.is_defeated and self.hp_at_turn_start.get(opp.instance_id, 0) > 0 : # War vorher lebend
                    defeated_bonus = self.config.get("opponent_defeated_bonus", 10.0)
                    reward += defeated_bonus
                    logger.debug(f"RewardManager: +{defeated_bonus:.2f} für Besiegen von {opp.name}")


        # Belohnung für Heilung des Helden / Strafe für Selbstschaden
        if hero.instance_id in self.hp_at_turn_start:
            hp_change_hero = hero.current_hp - self.hp_at_turn_start[hero.instance_id]
            if hp_change_hero > 0: # Heilung
                heal_reward = hp_change_hero * self.config.get("heal_hero_mult", 0.1)
                reward += heal_reward
                logger.debug(f"RewardManager: +{heal_reward:.2f} für {hp_change_hero} Selbstheilung")
            elif hp_change_hero < 0: # Selbstschaden
                # Selbstschaden wird bereits als "Schaden am Helden" behandelt, wenn Gegner agieren
                # Hier könnte man eine spezifische Strafe für Skills geben, die den Helden verletzen.
                # Fürs Erste lassen wir das, um doppelte Strafen zu vermeiden.
                pass
        
        return reward

    def calculate_reward_after_opponent_turns(self, state_manager: EnvStateManager) -> SupportsFloat:
        """
        Berechnet Rewards/Strafen basierend auf dem, was die Gegner dem Helden angetan haben.
        Diese Funktion wird nach den Zügen aller Gegner aufgerufen.
        """
        reward_from_opp_turn: SupportsFloat = 0.0
        hero = state_manager.get_hero()

        if not hero: return 0.0

        if hero.instance_id in self.hp_at_turn_start: # hp_at_turn_start sollte vom Beginn des *Heldenzuges* sein
            # Wir brauchen eigentlich HP *vor* den Gegnerzügen
            # Für den Moment nehmen wir an, hp_at_turn_start wurde vor den Gegnerzügen aktualisiert,
            # oder wir vergleichen einfach mit dem Zustand *nach* der Heldenaktion.
            # Besser: Der StateManager oder die Env muss den HP-Wert des Helden *vor* den Gegnerzügen speichern.
            # Annahme für jetzt: hp_at_turn_start wurde *nicht* aktualisiert seit der Heldenaktion.
            
            # Diese Logik ist tricky, da hp_at_turn_start sich auf den *Beginn des Heldenzuges* bezieht.
            # Schaden durch Gegner passiert *nach* der Heldenaktion.
            # Der RewardManager braucht hier den HP-Stand des Helden *unmittelbar bevor* die Gegner dran waren.
            # Fürs Erste lassen wir diesen Teil weg, da wir diesen Zwischenzustand nicht explizit speichern.
            # Der Schaden am Helden wird im `get_final_episode_rewards` behandelt, wenn er besiegt ist.
            pass

        # Hier könnte man auch Rewards für das Ausweichen von Angriffen etc. geben.
        return reward_from_opp_turn


    def get_final_episode_rewards(self, 
                                  state_manager: EnvStateManager, 
                                  max_steps_reached: bool) -> SupportsFloat:
        """
        Berechnet finale Rewards am Ende einer Episode (Sieg, Niederlage, Zeitlimit).
        """
        final_reward: SupportsFloat = 0.0
        hero = state_manager.get_hero()

        terminated, hero_won, _ = state_manager.check_combat_end_conditions()

        if terminated:
            if hero_won:
                final_reward += self.config.get("all_opponents_defeated_bonus", 50.0)
                logger.debug(f"RewardManager: +{self.config.get('all_opponents_defeated_bonus', 50.0):.2f} für Sieg (alle Gegner besiegt).")
            elif hero and hero.is_defeated: # Sicherstellen, dass Held existiert
                final_reward += self.config.get("hero_defeated_penalty", -50.0)
                logger.debug(f"RewardManager: {self.config.get('hero_defeated_penalty', -50.0):.2f} für Niederlage (Held besiegt).")
        elif max_steps_reached: # Truncated
            final_reward += self.config.get("max_steps_reached_penalty", -10.0)
            logger.debug(f"RewardManager: {self.config.get('max_steps_reached_penalty', -10.0):.2f} für Erreichen des Zeitlimits.")
            
        return final_reward


if __name__ == '__main__':
    print("--- Teste RewardManager ---")
    # Benötigt einen mock EnvStateManager und CharacterInstances für vollständige Tests.
    # Hier nur ein einfacher Test der Konfiguration.
    
    reward_manager_default = RewardManager()
    print(f"Default Config: {reward_manager_default.config}")

    custom_rewards = {
        "step_penalty": -0.05,
        "damage_to_opponent_mult": 0.3,
        "hero_defeated_penalty": -75.0
    }
    reward_manager_custom = RewardManager(reward_config=custom_rewards)
    print(f"Custom Config: {reward_manager_custom.config}")
    assert reward_manager_custom.config["step_penalty"] == -0.05
    assert reward_manager_custom.config["damage_to_opponent_mult"] == 0.3
    assert reward_manager_custom.config["hero_defeated_penalty"] == -75.0
    assert reward_manager_custom.config["heal_hero_mult"] == 0.1 # Nicht überschrieben, sollte Default sein

    # Beispielhafte Nutzung (erfordert Mock-Objekte)
    # Mock StateManager und Charaktere erstellen...
    # state_mock = MockStateManager() 
    # reward_manager_default.record_hp_at_turn_start(state_mock.get_all_live_participants())
    # ... simuliere Heldenaktion ...
    # reward1 = reward_manager_default.calculate_reward_for_hero_action(state_mock, True, True, "some_skill")
    # ... simuliere Gegnerzüge ...
    # reward2 = reward_manager_default.calculate_reward_after_opponent_turns(state_mock)
    # ... simuliere Episodenende ...
    # final_reward = reward_manager_default.get_final_episode_rewards(state_mock, False)
    # print(f"Beispiel-Rewards: Aktion={reward1}, Gegnerzug={reward2}, Final={final_reward}")

    print("\n--- RewardManager-Tests (rudimentär) abgeschlossen ---")