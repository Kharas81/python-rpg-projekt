"""
Reward Calculator for RPG Environment

Diese Klasse ist verantwortlich für die Berechnung der Belohnung
basierend auf dem Kampfergebnis und den RL-Einstellungen.
"""
from typing import Dict, Any, Optional

from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter # Für Winner-Check etc.
# combat_result_agent ist typischerweise ein CombatResult-Objekt, aber um Zirkelimporte
# mit CombatSystem zu vermeiden, verwenden wir Any oder definieren eine leichtere Struktur.
# Fürs Erste nehmen wir an, combat_result_agent ist das von CombatSystem.execute_action zurückgegebene Objekt.

from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

class RewardCalculator:
    def __init__(self, reward_settings: Dict[str, float]):
        self.reward_settings = reward_settings
        logger.info(f"RewardCalculator initialisiert mit Einstellungen: {self.reward_settings}")

    def calculate_reward(self,
                         combat_result_agent: Optional[Any], # Typisch: CombatResult-Instanz
                         action_taken_by_agent: bool,
                         prev_agent_hp: int,
                         agent_character: Optional[CharacterInstance],
                         current_encounter: Optional[CombatEncounter],
                         is_terminated: bool,
                         is_truncated: bool,
                         max_steps_penalty_applies: bool # True, wenn max_steps erreicht und nicht schon terminated
                         ) -> float:
        """
        Berechnet die Belohnung für den aktuellen Zeitschritt.
        """
        if not self.reward_settings:
            logger.warning("Keine Reward-Einstellungen im RewardCalculator gefunden. Gebe 0.0 Belohnung.")
            return 0.0

        current_reward = float(self.reward_settings.get('time_penalty_per_step', -0.01))

        if not action_taken_by_agent:
            current_reward += float(self.reward_settings.get('invalid_action_penalty', -1.0))
            # Keine weiteren positiven Rewards, wenn keine valide Aktion ausgeführt wurde
            return current_reward

        # Belohnungen/Malusse basierend auf der Agentenaktion und deren direktem Ergebnis
        if combat_result_agent and agent_character and current_encounter:
            # Prüfen, ob combat_result_agent die erwarteten Attribute hat
            action_details = getattr(combat_result_agent, 'action', None)
            damage_dealt = getattr(combat_result_agent, 'damage_dealt', {})
            healing_done = getattr(combat_result_agent, 'healing_done', {})
            deaths = getattr(combat_result_agent, 'deaths', [])

            if action_details and action_details.actor == agent_character:
                # Schaden an Gegnern
                damage_to_opponents = sum(
                    val for char, val in damage_dealt.items()
                    if char in current_encounter.opponents
                )
                current_reward += damage_to_opponents * float(self.reward_settings.get('damage_dealt_factor', 0.1))

                # Heilung auf Spielerseite
                healing_on_players = sum(
                    val for char, val in healing_done.items()
                    if char in current_encounter.players
                )
                current_reward += healing_on_players * float(self.reward_settings.get('healing_factor', 0.2))

                # Gegner durch Agentenaktion besiegt
                for dead_char in deaths:
                    if dead_char in current_encounter.opponents:
                        current_reward += float(self.reward_settings.get('enemy_defeated_reward', 5.0))
                
                # Optional: Malus für "Friendly Fire" oder ineffektive Heilung
                # damage_to_allies = sum(val for char, val in damage_dealt.items() if char in current_encounter.players and char != agent_character)
                # current_reward -= damage_to_allies * float(self.reward_settings.get('friendly_fire_penalty_factor', 0.5))


        # Malus für erlittenen Schaden des Agenten in diesem Step
        if agent_character and agent_character.hp < prev_agent_hp:
            hp_lost = prev_agent_hp - agent_character.hp
            # damage_taken_factor sollte negativ in den Settings sein, oder hier * -1 multipliziert werden
            damage_taken_factor = float(self.reward_settings.get('damage_taken_factor', -0.05))
            current_reward += hp_lost * damage_taken_factor


        # Große Belohnungen/Malusse für Episodenende
        if is_terminated and current_encounter: # Kampf regulär beendet
            if current_encounter.winner == 'players':
                current_reward += float(self.reward_settings.get('victory_reward', 50.0))
            elif current_encounter.winner == 'opponents':
                current_reward += float(self.reward_settings.get('defeat_penalty', -50.0))
            # Man könnte auch einen kleinen Bonus/Malus für unentschieden geben
            # elif current_encounter.winner is None:
            #     current_reward += float(self.reward_settings.get('draw_penalty', -5.0))


        if is_truncated and max_steps_penalty_applies: # Max steps erreicht ohne Sieg/Niederlage
            current_reward += float(self.reward_settings.get('max_steps_penalty', -1.0))
            
        # logger.debug(f"RewardCalculator: Berechnete Belohnung = {current_reward:.4f}")
        return current_reward