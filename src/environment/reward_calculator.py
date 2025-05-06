import logging
import typing
import math # Notwendig für math.isclose

try:
    from src.config import config
except ImportError:
    logger_rc_fallback = logging.getLogger(__name__ + "_fallback_rc")
    logger_rc_fallback.warning("RewardCalculator: Konnte config nicht laden, verwende Standardgewichte.")
    class DummyConfig:
        def get_setting(self, key, default=None):
            if key == "rl_rewards.damage_dealt_factor": return 0.1
            if key == "rl_rewards.damage_taken_factor": return -0.15
            if key == "rl_rewards.victory": return 10.0
            if key == "rl_rewards.defeat": return -10.0
            if key == "rl_rewards.invalid_action": return -2.0
            if key == "rl_rewards.pass_action": return -0.1
            if key == "rl_rewards.time_limit": return -5.0
            if key == "rl_rewards.opponent_killed_by_dot": return 10.0
            if key == "rl_rewards.player_killed_by_dot": return -10.0
            return default
    config = DummyConfig()

logger = logging.getLogger(__name__)

class RewardCalculator:
    def __init__(self):
        self.reward_weight_damage_dealt = config.get_setting("rl_rewards.damage_dealt_factor", 0.1)
        self.reward_weight_damage_taken = config.get_setting("rl_rewards.damage_taken_factor", -0.15)
        self.reward_victory = config.get_setting("rl_rewards.victory", 10.0)
        self.reward_defeat = config.get_setting("rl_rewards.defeat", -10.0)
        self.reward_invalid_action = config.get_setting("rl_rewards.invalid_action", -2.0)
        self.reward_pass_action = config.get_setting("rl_rewards.pass_action", -0.1)
        self.reward_time_limit = config.get_setting("rl_rewards.time_limit", -5.0)
        self.reward_opponent_killed_by_dot = config.get_setting("rl_rewards.opponent_killed_by_dot", 10.0)
        self.reward_player_killed_by_dot = config.get_setting("rl_rewards.player_killed_by_dot", -10.0)

        logger.info("RewardCalculator initialisiert mit folgenden Gewichten:")
        logger.info(f"  Damage Dealt Factor: {self.reward_weight_damage_dealt}")
        logger.info(f"  Damage Taken Factor: {self.reward_weight_damage_taken}")
        # ... (weitere Log-Ausgaben für Gewichte können hier stehen)

    def calculate_reward(self,
                         player_action_result: typing.Optional[dict],
                         opponent_action_result: typing.Optional[dict],
                         player_hp_before_opponent_turn: int,
                         player_hp_after_opponent_turn: int,
                         opponent_hp_before_player_turn: int,
                         opponent_hp_after_player_turn: int,
                         player_died_by_dot: bool,
                         opponent_died_by_dot: bool,
                         episode_terminated: bool,
                         player_won: typing.Optional[bool],
                         action_was_invalid: bool,
                         action_was_pass: bool,
                         time_limit_reached: bool
                         ) -> float:
        reward = 0.0

        # KORREKTUR: Ungültige Aktion und Passen außerhalb der player_action_result-Prüfung behandeln
        if action_was_invalid:
            reward += self.reward_invalid_action
            logger.debug(f"  Reward: Ungültige Spieleraktion ({self.reward_invalid_action:.2f})")
        elif action_was_pass: # elif, da eine Aktion nicht gleichzeitig ungültig und ein Passen sein kann
            reward += self.reward_pass_action
            logger.debug(f"  Reward: Spieler passt ({self.reward_pass_action:.2f})")

        # Belohnung für Aktionen des Spielers (wenn es ein Aktionsergebnis gibt und nicht ungültig/passen)
        if player_action_result and not action_was_invalid and not action_was_pass:
            if player_action_result.get("hit", False):
                damage_dealt_by_player = player_action_result.get("damage_dealt", 0)
                if damage_dealt_by_player > 0:
                    reward += damage_dealt_by_player * self.reward_weight_damage_dealt
                    logger.debug(f"  Reward: Spieler verursacht {damage_dealt_by_player} Schaden ({damage_dealt_by_player * self.reward_weight_damage_dealt:.2f})")

        # Strafe für Schaden durch Gegner
        if opponent_action_result:
            if opponent_action_result.get("hit", False):
                damage_taken_from_opponent = opponent_action_result.get("damage_dealt", 0)
                if damage_taken_from_opponent > 0:
                    reward += damage_taken_from_opponent * self.reward_weight_damage_taken
                    logger.debug(f"  Reward: Spieler erleidet {damage_taken_from_opponent} Schaden ({damage_taken_from_opponent * self.reward_weight_damage_taken:.2f})")

        # Belohnung/Strafe für Ende der Episode
        if episode_terminated:
            if player_won is True:
                reward += self.reward_victory
                logger.debug(f"  Reward: Spieler hat gewonnen! ({self.reward_victory:.2f})")
            elif player_won is False:
                reward += self.reward_defeat
                logger.debug(f"  Reward: Spieler wurde besiegt! ({self.reward_defeat:.2f})")
            elif opponent_died_by_dot and player_won is None:
                reward += self.reward_opponent_killed_by_dot
                logger.debug(f"  Reward: Gegner durch DoT besiegt! ({self.reward_opponent_killed_by_dot:.2f})")
            elif player_died_by_dot and player_won is None:
                reward += self.reward_player_killed_by_dot
                logger.debug(f"  Reward: Spieler durch DoT besiegt! ({self.reward_player_killed_by_dot:.2f})")

        if time_limit_reached:
            reward += self.reward_time_limit
            logger.debug(f"  Reward: Zeitlimit erreicht ({self.reward_time_limit:.2f})")

        logger.info(f"RewardCalculator: Berechneter Gesamt-Reward für den Schritt: {reward:.2f}")
        return reward

if __name__ == '__main__':
    try:
        import sys; from pathlib import Path
        project_dir = Path(__file__).resolve().parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging; setup_logging()
    except ImportError as e:
        print(f"FEHLER bei Test-Setup in reward_calculator.py: {e}"); exit(1)

    print("\n--- RewardCalculator Test ---")
    calculator = RewardCalculator()

    player_res1 = {"hit": True, "damage_dealt": 10}
    reward1 = calculator.calculate_reward(player_res1, None, 100, 100, 50, 40, False, False, False, None, False, False, False)
    print(f"Test 1 (Spieler trifft, Schaden): Reward = {reward1:.2f} (Erwartet ~{10 * calculator.reward_weight_damage_dealt:.2f})")
    assert math.isclose(reward1, 10 * calculator.reward_weight_damage_dealt)

    opponent_res2 = {"hit": True, "damage_dealt": 15}
    reward2 = calculator.calculate_reward(None, opponent_res2, 100, 85, 50, 50, False, False, False, None, False, False, False)
    print(f"Test 2 (Spieler getroffen, Schaden): Reward = {reward2:.2f} (Erwartet ~{15 * calculator.reward_weight_damage_taken:.2f})")
    assert math.isclose(reward2, 15 * calculator.reward_weight_damage_taken)

    player_res3 = {"hit": True, "damage_dealt": 50}
    reward3 = calculator.calculate_reward(player_res3, None, 100, 100, 50, 0, False, False, True, True, False, False, False)
    expected_r3 = (50 * calculator.reward_weight_damage_dealt) + calculator.reward_victory
    print(f"Test 3 (Spieler gewinnt): Reward = {reward3:.2f} (Erwartet ~{expected_r3:.2f})")
    assert math.isclose(reward3, expected_r3)

    opponent_res4 = {"hit": True, "damage_dealt": 100}
    reward4 = calculator.calculate_reward(None, opponent_res4, 100, 0, 50, 50, False, False, True, False, False, False, False)
    expected_r4 = (100 * calculator.reward_weight_damage_taken) + calculator.reward_defeat
    print(f"Test 4 (Spieler verliert): Reward = {reward4:.2f} (Erwartet ~{expected_r4:.2f})")
    assert math.isclose(reward4, expected_r4)

    # KORRIGIERTER TEST 5: action_was_invalid ist True
    reward5 = calculator.calculate_reward(None, None, 100, 100, 50, 50, False, False, False, None, True, False, False)
    print(f"Test 5 (Ungültige Aktion): Reward = {reward5:.2f} (Erwartet {calculator.reward_invalid_action:.2f})")
    assert math.isclose(reward5, calculator.reward_invalid_action)

    # KORRIGIERTER TEST 6: action_was_pass ist True
    reward6 = calculator.calculate_reward(None, None, 100, 100, 50, 50, False, False, False, None, False, True, False)
    print(f"Test 6 (Passen): Reward = {reward6:.2f} (Erwartet {calculator.reward_pass_action:.2f})")
    assert math.isclose(reward6, calculator.reward_pass_action)

    reward7 = calculator.calculate_reward(None, None, 100, 100, 50, 50, False, False, False, None, False, False, True)
    print(f"Test 7 (Zeitlimit): Reward = {reward7:.2f} (Erwartet {calculator.reward_time_limit:.2f})")
    assert math.isclose(reward7, calculator.reward_time_limit)

    reward8 = calculator.calculate_reward(None, None, 100,100, 10,0, False,True, True, True, False,False,False)
    expected_r8 = calculator.reward_victory
    print(f"Test 8 (Gegner durch DoT besiegt, Spieler gewinnt): Reward = {reward8:.2f} (Erwartet {expected_r8:.2f})")
    assert math.isclose(reward8, expected_r8)

    print("\nAlle RewardCalculator Tests erfolgreich.")