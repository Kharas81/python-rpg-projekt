import gymnasium as gym
from gymnasium import spaces
import numpy as np
import logging
import typing
import random

# Importiere unsere Spiel-Logik und Definitionen
try:
    from src.definitions import loader
    from src.game_logic.entities import CharacterInstance
    from src.game_logic import combat
    from src.ai import ai_dispatcher
    from src.definitions.skill import Skill
    from src.environment.action_manager import ActionManager, PASS_ACTION_INDEX, MAX_AGENT_SKILLS
    from src.environment.observation_manager import ObservationManager
    from src.environment.reward_calculator import RewardCalculator
except ImportError:
    logger_env_fallback = logging.getLogger(__name__ + "_fallback_env")
    logger_env_fallback.error("FEHLER: Konnte src-Module nicht laden in rpg_env.py. Fallback-Dummies werden verwendet.")

    MAX_AGENT_SKILLS_fallback = 4
    PASS_ACTION_INDEX_fallback = MAX_AGENT_SKILLS_fallback

    class DummySkill:
        def __init__(self, skill_id="dummy_skill", name=None):
            self.skill_id = skill_id
            self.name = name if name else skill_id
        def get_cost_resource(self): # KORRIGIERT: Separate Zeile
            return "NONE"
        def get_cost_amount(self): # KORRIGIERT: Separate Zeile
            return 0

    class DummyCharacterDefinition:
        def __init__(self, name="DummyDef", skill_ids=None, primary_resource="NONE"):
            self.name = name
            self.skill_ids = skill_ids if skill_ids is not None else []
            self.primary_resource = primary_resource

    class DummyCharacterInstance:
        def __init__(self, definition=None):
            self.definition = definition if definition else DummyCharacterDefinition()
            self.name = self.definition.name
            self.level = 1
            self.current_hp = 10
            self.max_hp = 10
            self.current_mana = 10
            self.max_mana = 10
            self.current_stamina = 10
            self.max_stamina = 10
            self.current_energy = 10
            self.max_energy = 10
            self.active_status_effects = []
        def is_alive(self): # KORRIGIERT
            return True
        def can_act(self): # KORRIGIERT
            return True
        def has_status_effect(self, effect_id): # KORRIGIERT
            return False
        def can_afford_cost(self, res, amount): # KORRIGIERT
            return True
        def pay_cost(self, res, amount): # KORRIGIERT
            return True
        def get_attribute_bonus(self, attr_name): # KORRIGIERT
            return 0
        def tick_status_effects(self): # KORRIGIERT
            pass
        def take_damage(self, amount): # KORRIGIERT
            self.current_hp -=amount
            if self.current_hp < 0:
                self.current_hp = 0
        def __repr__(self): # KORRIGIERT
            return f"<DummyChar {self.name} HP: {self.current_hp}>"

    loader = type('DummyLoader', (), {
        'get_character_class': lambda x: DummyCharacterDefinition(name=x, skill_ids=[f"s{i}" for i in range(MAX_AGENT_SKILLS_fallback)]) if x else None,
        'get_opponent': lambda x: DummyCharacterDefinition(name=x, skill_ids=[f"os{i}" for i in range(MAX_AGENT_SKILLS_fallback)]) if x else None,
        'get_skill': lambda x: DummySkill(x) if x else None
    })()
    combat = type('DummyCombat', (), {'execute_attack_action': lambda a,b,c: {"hit": False, "damage_dealt": 0, "defender_hp_after": 0, "defender_is_alive": True, "log_messages":[] }})()
    ai_dispatcher = type('DummyAIDispatcher', (), {'get_ai_action': lambda a,b: (None,None)})()

    class ActionManager:
        def __init__(self,player_instance):
            self.action_space=spaces.Discrete(MAX_AGENT_SKILLS_fallback+1)
            if player_instance and hasattr(player_instance, 'definition') and hasattr(player_instance.definition, 'skill_ids'):
                 self._player_skills = [DummySkill(sid) for sid in player_instance.definition.skill_ids[:MAX_AGENT_SKILLS_fallback]]
                 self._player_skills.extend([None] * (MAX_AGENT_SKILLS_fallback - len(self._player_skills)))
            else:
                self._player_skills = [DummySkill(f"dummy_s{i}") for i in range(MAX_AGENT_SKILLS_fallback)]
        def get_action_masks(self):
            return [True]*(MAX_AGENT_SKILLS_fallback+1)
        def get_skill_for_action(self,idx):
            if 0 <= idx < len(self._player_skills):
                return self._player_skills[idx]
            return None

    class ObservationManager:
        def __init__(self, max_lvl):
            self.shape = (3+1+MAX_AGENT_SKILLS_fallback+2,)
        def get_observation_space_shape(self):
            return self.shape
        def get_observation(self, p, o, am):
            return np.zeros(self.shape, dtype=np.float32)

    # class RewardCalculator ist oben schon definiert
    if 'MAX_AGENT_SKILLS' not in globals(): MAX_AGENT_SKILLS = MAX_AGENT_SKILLS_fallback
    if 'PASS_ACTION_INDEX' not in globals(): PASS_ACTION_INDEX = PASS_ACTION_INDEX_fallback
    RealCharacterInstanceGlobal = DummyCharacterInstance


logger = logging.getLogger(__name__)

OBS_SPACE_DIMS = 3 + 1 + MAX_AGENT_SKILLS + 2

class RPGEnv(gym.Env):
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 4}

    def __init__(self, render_mode: typing.Optional[str] = None,
                 player_class_id: str = "krieger",
                 opponent_id: str = "goblin_lv1",
                 max_expected_level: int = 20):
        super().__init__()
        self.player_class_id = player_class_id
        self.opponent_id = opponent_id
        self.render_mode = render_mode
        self.max_expected_level = float(max_expected_level)
        self.player: typing.Optional[CharacterInstance] = None
        self.opponent: typing.Optional[CharacterInstance] = None
        self.current_round: int = 0
        self.max_rounds: int = 100
        self.action_manager: typing.Optional[ActionManager] = None
        self.observation_manager: typing.Optional[ObservationManager] = None
        self.reward_calculator: typing.Optional[RewardCalculator] = None

        try:
            from src.game_logic.entities import CharacterInstance as RealCharacterInstance_Init
            temp_player_def_init = loader.get_character_class(self.player_class_id)
            if not temp_player_def_init :
                raise RuntimeError(f"Spielerdefinition '{self.player_class_id}' für Env-Init nicht geladen.")
            temp_player_inst_init = RealCharacterInstance_Init(temp_player_def_init)
        except (RuntimeError, ImportError) as e:
            logger_init_fallback = logging.getLogger(__name__ + "_init_fallback_env") # Eigener Loggername
            logger_init_fallback.warning(f"Verwende DummyCharacterInstance für temporäre Spielerinstanz im Env-Konstruktor wegen Fehler: {e}")
            global RealCharacterInstanceGlobal
            temp_player_inst_init = RealCharacterInstanceGlobal(DummyCharacterDefinition(name=player_class_id, skill_ids=[f"s{i}" for i in range(MAX_AGENT_SKILLS)]))

        self.action_manager = ActionManager(temp_player_inst_init)
        self.observation_manager = ObservationManager(max_expected_level=self.max_expected_level)
        self.reward_calculator = RewardCalculator()

        self.action_space = self.action_manager.action_space
        self.observation_space = spaces.Box(low=0, high=1, shape=self.observation_manager.get_observation_space_shape(), dtype=np.float32)
        logger.info(f"RPGEnv initialisiert. Action Space: {self.action_space}, Observation Space: {self.observation_space}")

    def _update_player_skills_in_action_manager(self):
        if self.player and self.action_manager:
            self.action_manager.player_instance = self.player
            self.action_manager._update_player_skills()
        elif self.action_manager:
             self.action_manager._player_skills = [None] * MAX_AGENT_SKILLS

    def _get_observation(self) -> np.ndarray:
        if self.player is None or self.opponent is None or self.action_manager is None or self.observation_manager is None:
            return np.zeros(self.observation_space.shape, dtype=self.observation_space.dtype)
        return self.observation_manager.get_observation(self.player, self.opponent, self.action_manager)

    def action_masks(self) -> typing.List[bool]:
        if self.action_manager:
            return self.action_manager.get_action_masks()
        return [False] * (MAX_AGENT_SKILLS + 1)

    def _get_info(self) -> dict:
        return {
            "player_hp": self.player.current_hp if self.player else -1,
            "opponent_hp": self.opponent.current_hp if self.opponent else -1,
            "round": self.current_round
        }

    def reset(self, seed: typing.Optional[int] = None, options: typing.Optional[dict] = None) -> typing.Tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        logger.info("Umgebung wird zurückgesetzt.")
        try:
            from src.game_logic.entities import CharacterInstance as RealCharacterInstance_Reset
        except ImportError:
            global RealCharacterInstanceGlobal
            RealCharacterInstance_Reset = RealCharacterInstanceGlobal

        player_def = loader.get_character_class(self.player_class_id)
        opponent_def = loader.get_opponent(self.opponent_id)
        if not player_def or not opponent_def:
            raise RuntimeError("Fehler beim Laden der Definitionen in reset().")
        self.player = RealCharacterInstance_Reset(player_def)
        self.opponent = RealCharacterInstance_Reset(opponent_def)
        
        self.action_manager = ActionManager(self.player)
        self.observation_manager = ObservationManager(max_expected_level=self.max_expected_level)
        
        self.action_space = self.action_manager.action_space
        self.observation_space = spaces.Box(low=0, high=1, shape=self.observation_manager.get_observation_space_shape(), dtype=np.float32)

        self.current_round = 0
        logger.info(f"Reset: Spieler '{self.player.name}', Gegner '{self.opponent.name}'")
        return self._get_observation(), self._get_info()

    def step(self, action: int) -> typing.Tuple[np.ndarray, float, bool, bool, dict]:
        if self.player is None or self.opponent is None or self.action_manager is None or self.reward_calculator is None:
            raise RuntimeError("Umgebung nicht vollständig initialisiert (Manager fehlt).")

        self.current_round += 1
        logger.info(f"\n--- Runde {self.current_round} (RL Step) ---")
        logger.info(f"Spieler: {self.player} | Gegner: {self.opponent}")
        logger.info(f"Agent wählt Aktion: {action}")

        terminated = False
        truncated = False
        player_action_description = "Nichts getan"
        player_action_result: typing.Optional[dict] = None
        opponent_action_result: typing.Optional[dict] = None
        action_was_invalid = False
        action_was_pass = False

        opponent_hp_before_player_turn = self.opponent.current_hp if self.opponent else 0
        player_hp_before_opponent_turn = self.player.current_hp if self.player else 0

        current_action_masks = self.action_masks()

        if not (hasattr(self.player, 'is_alive') and hasattr(self.player, 'can_act')):
            logger.error("Dummy Player Instanz oder fehlerhafte Player Instanz in step(). Episode wird beendet.")
            terminated = True
            # player_won ist False, wenn der Spieler nicht handeln kann und die Episode deshalb endet
            final_reward = self.reward_calculator.calculate_reward(
                None, None, player_hp_before_opponent_turn, 0,
                opponent_hp_before_player_turn, opponent_hp_before_player_turn,
                True, False, # player_died_by_dot, opponent_died_by_dot
                terminated, False, # episode_terminated, player_won
                True, False, # action_was_invalid, action_was_pass
                truncated # time_limit_reached (False hier)
            )
            return self._get_observation(), final_reward, terminated, truncated, self._get_info()


        if not current_action_masks[action]:
            action_was_invalid = True
            logger.warning(f"Agent wählte ungültige Aktion {action} (Maske: {current_action_masks}). Strafe.")
            player_action_description = f"Ungültige Aktion {action}"
        elif self.player.is_alive() and self.player.can_act():
            skill_to_use = self.action_manager.get_skill_for_action(action)
            if action == PASS_ACTION_INDEX or (skill_to_use is None and action == PASS_ACTION_INDEX) :
                action_was_pass = True
                player_action_description = "Passen"
                logger.info(f"Spieler ({self.player.name}) passt.")
            elif skill_to_use:
                player_action_description = f"Skill '{skill_to_use.name}' auf '{self.opponent.name}'"
                logger.info(f"Spieler ({self.player.name}) führt {player_action_description} aus.")
                player_action_result = combat.execute_attack_action(self.player, self.opponent, skill_to_use)
                if not self.opponent.is_alive():
                    terminated = True
                    logger.info("Gegner besiegt durch Spieler!")
            else:
                action_was_invalid = True # Sollte durch Maske nicht passieren, aber als Sicherheit
                player_action_description = f"Fehler bei Aktionsinterpretation {action}"
                logger.error(f"Agent wählte Aktion {action}, die weder Passen noch ein gültiger Skill-Slot ist.")
        elif self.player.is_alive(): # Aber nicht self.player.can_act()
            player_action_description = "Kann nicht handeln (z.B. STUNNED)"
            logger.info(f"Spieler ({self.player.name}) {player_action_description}.")
        
        player_hp_after_player_action = self.player.current_hp if self.player else 0

        # Gegner-Zug
        if not terminated and self.opponent.is_alive() and self.opponent.can_act():
            logger.info(f"Gegner ({self.opponent.name}) ist am Zug.")
            opponent_skill_id, target = ai_dispatcher.get_ai_action(self.opponent, [self.player])
            if opponent_skill_id and target:
                opponent_skill = loader.get_skill(opponent_skill_id)
                if opponent_skill:
                    logger.info(f"Gegner ({self.opponent.name}) führt Skill '{opponent_skill.name}' auf '{self.player.name}' aus.")
                    opponent_action_result = combat.execute_attack_action(self.opponent, self.player, opponent_skill)
                    if not self.player.is_alive():
                        terminated = True
                        logger.info("Spieler besiegt durch Gegner!")
                else:
                    logger.error(f"Gegner-AI wählte ungültigen Skill '{opponent_skill_id}'.")
            else:
                logger.info(f"Gegner-AI findet keine Aktion oder Ziel.")
        elif not terminated and self.opponent.is_alive():
             logger.info(f"Gegner ({self.opponent.name}) kann nicht handeln.")

        # Effekte ticken und auf Tod durch Effekte prüfen
        player_died_by_dot = False
        opponent_died_by_dot = False
        if hasattr(self.player, 'is_alive') and self.player.is_alive(): # Prüfe ob player existiert und lebt
            hp_before_tick = self.player.current_hp
            if hasattr(self.player, 'tick_status_effects'):
                self.player.tick_status_effects()
            if not terminated and not self.player.is_alive() and hp_before_tick > 0 :
                player_died_by_dot = True
                terminated = True
                logger.info("Spieler durch eigene Effekte besiegt!")

        if hasattr(self.opponent, 'is_alive') and self.opponent.is_alive(): # Prüfe ob opponent existiert und lebt
            hp_before_tick_opp = self.opponent.current_hp
            if hasattr(self.opponent, 'tick_status_effects'):
                self.opponent.tick_status_effects()
            if not terminated and not self.opponent.is_alive() and hp_before_tick_opp > 0:
                opponent_died_by_dot = True
                terminated = True
                logger.info("Gegner durch eigene Effekte besiegt!")

        # Zeitlimit prüfen
        if not terminated and self.current_round >= self.max_rounds:
            logger.info(f"Maximalzahl von {self.max_rounds} Runden erreicht.")
            truncated = True # truncated wird True, wenn Zeitlimit erreicht

        # Endgültigen Status bestimmen für Reward
        player_won_status: typing.Optional[bool] = None
        if terminated: # Nur wenn Episode durch Sieg/Niederlage endet
            player_alive_at_end = self.player.is_alive() if hasattr(self.player, 'is_alive') else False
            opponent_alive_at_end = self.opponent.is_alive() if hasattr(self.opponent, 'is_alive') else False

            if player_alive_at_end and not opponent_alive_at_end:
                player_won_status = True
            elif not player_alive_at_end and opponent_alive_at_end:
                player_won_status = False
            elif not player_alive_at_end and not opponent_alive_at_end: # Beide besiegt (z.B. durch DoT)
                 player_won_status = None # Unentschieden oder wer zuerst starb, ist relevant
            # (Fall, wo beide leben und terminated=True ist, sollte nicht passieren, es sei denn durch externe Logik)

        reward = self.reward_calculator.calculate_reward(
            player_action_result=player_action_result,
            opponent_action_result=opponent_action_result,
            player_hp_before_opponent_turn=player_hp_before_opponent_turn,
            player_hp_after_opponent_turn=self.player.current_hp if self.player else 0,
            opponent_hp_before_player_turn=opponent_hp_before_player_turn,
            opponent_hp_after_player_turn=self.opponent.current_hp if self.opponent else 0,
            player_died_by_dot=player_died_by_dot,
            opponent_died_by_dot=opponent_died_by_dot,
            episode_terminated=terminated, # Wichtig: Ist es ein endgültiges Ende?
            player_won=player_won_status,
            action_was_invalid=action_was_invalid,
            action_was_pass=action_was_pass,
            time_limit_reached=truncated # truncated wegen Zeitlimit wird hier als time_limit_reached übergeben
        )

        observation = self._get_observation()
        info = self._get_info()
        info["player_action"] = player_action_description
        logger.info(f"Runde {self.current_round} Ende. Reward: {reward:.2f}, Terminated: {terminated}, Truncated: {truncated}")
        return observation, reward, terminated, truncated, info

    def render(self): # KORRIGIERT
        if self.render_mode == 'human' or self.render_mode == 'ansi':
            if self.player and self.opponent:
                output = (f"\n--- Runde {self.current_round} ---\n"
                          f"Spieler: {self.player}\n"
                          f"Gegner: {self.opponent}\n"
                          f"{'-'*20}\n")
                if self.render_mode == 'human':
                    print(output)
                    # Gemäß Gymnasium API sollte render() für 'human' Mode None zurückgeben
                    return None
                elif self.render_mode == 'ansi':
                    return output
            else:
                if self.render_mode == 'ansi':
                    return "Umgebung nicht initialisiert (bitte reset() aufrufen)."
        return None

    def close(self):
        logger.info("RPGEnv wird geschlossen.")

if __name__ == '__main__':
    try:
        import sys
        from pathlib import Path
        project_dir = Path(__file__).resolve().parent.parent.parent
        if str(project_dir) not in sys.path:
            sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging
        setup_logging()
    except ImportError:
        print("FEHLER: Logging-Setup für rpg_env.py Test nicht gefunden.")

    print("\n--- Test der RPGEnv mit Managern (vollständig korrigiert) ---")
    env = RPGEnv(render_mode='human', player_class_id="krieger", opponent_id="goblin_lv1")

    from gymnasium.utils.env_checker import check_env
    try:
        print("\nPrüfe Umgebung mit Gymnasium env_checker...")
        check_env(env, warn=True, skip_render_check=True)
        print("Env Check (Basis) bestanden.")
    except Exception as e:
        print(f"FEHLER beim Env Check: {e}")

    print("\nTeste reset():")
    obs, info = env.reset()
    print(f"  Observation nach Reset (Shape {obs.shape}): {obs}")
    print(f"  Info nach Reset: {info}")
    if env.observation_space.shape is not None :
        assert obs.shape == env.observation_space.shape, "Observation Shape stimmt nicht mit Space überein!"

    print("\nTeste einige Steps mit Action Masks:")
    for i in range(10): # Reduziere Runden für schnelle Tests, wenn nötig
        action_mask = env.action_masks()
        print(f"\n-- Step {i+1} --")
        print(f"  Player: {env.player}")
        print(f"  Verfügbare Aktionen (Maske): {action_mask}")
        valid_actions = [idx for idx, v in enumerate(action_mask) if v]
        if not valid_actions:
            print("  Keine gültigen Aktionen für Spieler!")
            break
        action_to_take = random.choice(valid_actions)
        print(f"  Wähle Aktion {action_to_take} (aus {valid_actions})")
        obs, reward, terminated, truncated, info = env.step(action_to_take)
        env.render()
        print(f"  Observation (Shape {obs.shape}): {obs}")
        print(f"  Reward: {reward}")
        print(f"  Terminated: {terminated}, Truncated: {truncated}")
        print(f"  Info: {info}")
        if terminated or truncated:
            print("Episode beendet.")
            break
    env.close()
    print("\nRPGEnv Test abgeschlossen.")