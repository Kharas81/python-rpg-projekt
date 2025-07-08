# src/ai/action_selector.py
"""
Diese Klasse kapselt die Logik zur Auswahl einer Aktion für einen gegebenen Akteur.
Sie dient als Brücke zwischen dem Spielzustand und den verschiedenen KI-Controllern.
"""
import logging
from typing import Tuple, Optional, TYPE_CHECKING

# Projektinterne Imports
from src.game_logic.entities import CharacterInstance
from src.game_logic.player_controller import RLPlayerController
from src.ai import ai_dispatcher

# TYPE_CHECKING-Block zur Vermeidung von zirkulären Imports
if TYPE_CHECKING:
    from src.game_logic.game_state_manager import GameStateManager

logger = logging.getLogger(__name__)

class ActionSelector:
    """
    Entscheidet, welche Aktion ein Charakter ausführt, basierend darauf,
    ob es sich um einen RL-gesteuerten Spieler oder eine KI-gesteuerte NPC-Einheit handelt.
    """
    def __init__(self, player_controller: Optional[RLPlayerController]):
        self.player_controller = player_controller
        logger.info("ActionSelector initialisiert.")

    def select_action(self, actor: CharacterInstance, gsm: 'GameStateManager') -> Tuple[str, Optional[CharacterInstance]]:
        """
        Wählt einen Skill und ein Ziel für den aktuellen Akteur aus.

        Args:
            actor: Der Charakter, der am Zug ist.
            gsm: Der GameStateManager, um Kontext für die Entscheidung bereitzustellen.

        Returns:
            Ein Tupel aus (skill_id, target_instance).
        """
        # --- Fallback-Aktion definieren ---
        fallback_skill = "skill_pass_turn"
        fallback_target = actor

        # --- Fall 1: Der Akteur ist der RL-gesteuerte Spieler ---
        if self.player_controller and actor.instance_id == gsm.player_agent_id:
            obs, mask = gsm.get_rl_observation_and_mask()
            action_id = self.player_controller.choose_action(obs, mask)
            
            if action_id is not None:
                decoded_action = gsm.action_manager.get_game_action(action_id, gsm)
                if decoded_action:
                    return decoded_action  # (skill_id, target_instance)
            
            logger.warning(f"RLPlayerController konnte keine gültige Aktion für '{actor.name}' finden. Fallback auf 'Passen'.")
            return fallback_skill, fallback_target

        # --- Fall 2: Der Akteur ist eine KI-gesteuerte Einheit (Gegner) ---
        else:
            # Holen der KI-Strategie über den Dispatcher
            strategy = ai_dispatcher.get_ai_strategy_instance(actor, gsm.character_manager.get_all_live_participants())
            
            if strategy:
                # Die KI benötigt eine Liste potenzieller Ziele
                potential_targets = [
                    char for char in gsm.character_manager.get_all_live_participants() 
                    if not char.is_defeated and actor.is_opponent_of(char)
                ]
                decision = strategy.decide_action(potential_targets)
                if decision:
                    return decision # (skill_id, target_instance)

            logger.debug(f"KI-Strategie für '{actor.name}' hat keine Aktion entschieden. Fallback auf 'Passen'.")
            return fallback_skill, fallback_target