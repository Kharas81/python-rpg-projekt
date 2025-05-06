import numpy as np
import logging
import typing
import math # KORREKTUR: Fehlender Import

try:
    from src.game_logic.entities import CharacterInstance
    from src.environment.action_manager import ActionManager, MAX_AGENT_SKILLS
except ImportError:
    logger_om_fallback = logging.getLogger(__name__ + "_fallback_om")
    logger_om_fallback.warning("ObservationManager: Konnte Module nicht direkt laden.")
    MAX_AGENT_SKILLS = 4
    class CharacterInstance:
        def __init__(self):
            self.name="Dummy"
            self.level=1
            self.current_hp=1
            self.max_hp=1
            self.current_mana=1
            self.max_mana=1
            self.current_stamina=1
            self.max_stamina=1
            self.current_energy=1
            self.max_energy=1
            self.definition=type('D',(),{'primary_resource':"NONE"})()
        def has_status_effect(self,id): return False
    class ActionManager:
        def __init__(self, pi): self._player_skills = [None]*MAX_AGENT_SKILLS
        def get_action_masks(self): return [True]*(MAX_AGENT_SKILLS+1)

logger = logging.getLogger(__name__)

OBS_SPACE_DIMS = 3 + 1 + MAX_AGENT_SKILLS + 2

class ObservationManager:
    def __init__(self, max_expected_level: float):
        self.observation_space_shape = (OBS_SPACE_DIMS,)
        self.max_expected_level = max_expected_level
        logger.info(f"ObservationManager initialisiert. Shape: {self.observation_space_shape}")

    def get_observation_space_shape(self) -> tuple:
        return self.observation_space_shape

    def get_observation(self,
                        player: CharacterInstance,
                        opponent: CharacterInstance,
                        action_manager: ActionManager) -> np.ndarray:
        if not player or not opponent or not action_manager:
            logger.error("Ungültige Eingaben für get_observation.")
            return np.zeros(self.observation_space_shape, dtype=np.float32)

        obs_list = []
        obs_list.append(player.current_hp / player.max_hp if player.max_hp > 0 else 0.0)
        primary_res_current, primary_res_max = 0.0, 0.0
        player_def = getattr(player, 'definition', None)
        if player_def and hasattr(player_def, 'primary_resource'):
            res_type = player_def.primary_resource
            if res_type == "MANA" and player.max_mana > 0:
                primary_res_current, primary_res_max = player.current_mana, player.max_mana
            elif res_type == "STAMINA" and player.max_stamina > 0:
                primary_res_current, primary_res_max = player.current_stamina, player.max_stamina
            elif res_type == "ENERGY" and player.max_energy > 0:
                primary_res_current, primary_res_max = player.current_energy, player.max_energy
        obs_list.append(primary_res_current / primary_res_max if primary_res_max > 0 else 0.0)
        obs_list.append(float(player.level) / self.max_expected_level)
        obs_list.append(opponent.current_hp / opponent.max_hp if opponent.max_hp > 0 else 0.0)

        action_masks = action_manager.get_action_masks()
        for i in range(MAX_AGENT_SKILLS):
            obs_list.append(1.0 if action_masks[i] else 0.0)

        obs_list.append(1.0 if hasattr(player, 'has_status_effect') and player.has_status_effect("STUNNED") else 0.0)
        obs_list.append(1.0 if hasattr(opponent, 'has_status_effect') and opponent.has_status_effect("STUNNED") else 0.0)

        final_obs = np.array(obs_list, dtype=np.float32)
        if final_obs.shape != self.observation_space_shape:
            logger.error(f"Fehlerhafte Observation-Shape! Erwartet {self.observation_space_shape}, bekommen {final_obs.shape}. Obs: {final_obs}")
            return np.zeros(self.observation_space_shape, dtype=np.float32)
        logger.debug(f"Observation erstellt: {final_obs}")
        return final_obs

if __name__ == '__main__':
    try:
        import sys; from pathlib import Path
        project_dir = Path(__file__).resolve().parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging; setup_logging()
        from src.definitions import loader
        from src.game_logic.entities import CharacterInstance as RealCharacterInstance
        from src.environment.action_manager import ActionManager as RealActionManager
    except ImportError as e:
        print(f"FEHLER bei Test-Setup in observation_manager.py: {e}"); exit(1)

    print("\n--- ObservationManager Test ---")
    krieger_def = loader.get_character_class("krieger")
    goblin_def = loader.get_opponent("goblin_lv1")
    if not krieger_def or not goblin_def: print("FEHLER: Definitionen nicht geladen."); exit(1)

    player = RealCharacterInstance(krieger_def)
    opponent = RealCharacterInstance(goblin_def)
    action_mgr = RealActionManager(player)
    obs_mgr = ObservationManager(max_expected_level=20.0)

    print(f"Observation Space Shape vom Manager: {obs_mgr.get_observation_space_shape()}")
    assert obs_mgr.get_observation_space_shape() == (OBS_SPACE_DIMS,)

    print("\nErste Beobachtung:")
    observation1 = obs_mgr.get_observation(player, opponent, action_mgr)
    print(f"  Observation 1 (Shape {observation1.shape}): {observation1}")
    assert observation1.shape == (OBS_SPACE_DIMS,)
    expected_obs1_part = [1.0, 1.0, 1/20, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    for i, val in enumerate(expected_obs1_part):
        assert math.isclose(observation1[i], val, rel_tol=1e-5), f"Obs1[{i}] erwartet ~{val}, war {observation1[i]}"

    print("\nBeobachtung nach etwas Schaden und Status-Effekt:")
    player.take_damage(55)
    opponent.take_damage(19)
    try:
        from src.game_logic.effects import StatusEffect
        opponent.add_status_effect({"id": "STUNNED", "duration": 1}, source_entity_id="test")
    except ImportError: print("WARNUNG: StatusEffect für Test nicht importierbar")
    player.current_stamina = 10

    observation2 = obs_mgr.get_observation(player, opponent, action_mgr)
    print(f"  Observation 2 (Shape {observation2.shape}): {observation2}")
    assert observation2.shape == (OBS_SPACE_DIMS,)
    expected_obs2_part = [0.5, 0.1, 1/20, 76/95, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    for i, val in enumerate(expected_obs2_part):
        assert math.isclose(observation2[i], val, rel_tol=1e-5), f"Obs2[{i}] erwartet ~{val}, war {observation2[i]}"
    print("\nAlle ObservationManager Tests erfolgreich.")