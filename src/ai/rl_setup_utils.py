# src/ai/rl_setup_utils.py
"""
Hilfsfunktionen für das Setup von RL-Trainingsläufen: Umgebungserstellung,
Callback-Konfiguration, Modellerstellung und Logger-Konfiguration.
"""
import os
import logging
from typing import Dict, Any, Optional, List, Callable, Tuple, Type

import gymnasium as gym
import numpy as np

try:
    from stable_baselines3 import PPO
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
    from sb3_contrib.common.wrappers import ActionMasker
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv
    from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, BaseCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.base_class import BaseAlgorithm
    from stable_baselines3.common.logger import Logger as SB3Logger, configure as sb3_logger_configure
except ImportError as e:
    logging.getLogger(__name__).error(f"Fehler beim Import von SB3/SB3-Contrib in rl_setup_utils: {e}")
    # Dummy-Zuweisungen, damit der Rest des Codes nicht sofort bricht
    PPO = MaskablePPO = MaskableActorCriticPolicy = ActionMasker = None # type: ignore
    make_vec_env = DummyVecEnv = SubprocVecEnv = VecEnv = None # type: ignore
    CheckpointCallback = EvalCallback = BaseCallback = None # type: ignore
    Monitor = BaseAlgorithm = SB3Logger = sb3_logger_configure = None # type: ignore


from src.environment.rpg_env import RPGEnv

logger = logging.getLogger(__name__)

def create_vectorized_environments(
    rl_config: Dict[str, Any],
    paths: Dict[str, str],
    run_identifier: str,
    robust_get_action_masks_fn: Callable[[gym.Env], np.ndarray]
) -> Tuple[Optional[VecEnv], Optional[VecEnv]]:
    """
    Erstellt und konfiguriert die vektorisierten Trainings- und Evaluierungsumgebungen.
    """
    if not all([RPGEnv, Monitor, ActionMasker, DummyVecEnv, make_vec_env]):
        logger.error("Eine oder mehrere Kernkomponenten für Umgebungserstellung nicht verfügbar.")
        return None, None

    agent_conf = rl_config.get("agent_config", {})
    env_conf_from_file = rl_config.get("environment_config", {})
    adv_conf = rl_config.get("advanced_rl_config", {})

    num_parallel = adv_conf.get("num_parallel_runs", 1)
    use_monitor = adv_conf.get("use_sb3_monitor", True)
    use_subproc_vec_env = adv_conf.get("use_subproc_vec_env", False) and num_parallel > 1
    rl_algorithm_name_for_masker = agent_conf.get("rl_algorithm", "PPO").upper()

    def create_env_fn(is_eval: bool = False, suffix: str = "") -> Callable[[], gym.Env]:
        def _init() -> gym.Env:
            env_config_for_creation = {
                "hero_id": agent_conf.get("agent_hero_id", "krieger"),
                "opponent_setup": env_conf_from_file.get("opponent_setup"),
                "max_episode_steps": env_conf_from_file.get("max_episode_steps"),
                "reward_weights": env_conf_from_file.get("reward_weights"),
            }
            env_instance = RPGEnv(env_config=env_config_for_creation)
            
            if use_monitor and Monitor:
                monitor_kwargs = {"allow_early_resets": True, "info_keywords": ("is_success", "termination_reason")}
                log_dir_for_monitor = paths["eval_callback_log_dir"] if is_eval else paths["monitor_log_path_base"]
                os.makedirs(log_dir_for_monitor, exist_ok=True)
                monitor_filename = os.path.join(log_dir_for_monitor, f"monitor_{run_identifier}{suffix}.csv")
                env_instance = Monitor(env_instance, monitor_filename, **monitor_kwargs)
            
            if rl_algorithm_name_for_masker == "MASKABLEPPO" and ActionMasker:
                env_instance = ActionMasker(env_instance, robust_get_action_masks_fn)
            return env_instance
        return _init

    vec_env_cls = SubprocVecEnv if use_subproc_vec_env else DummyVecEnv
    train_env = make_vec_env(
        create_env_fn(is_eval=False, suffix="_train" if num_parallel == 1 else ""),
        n_envs=num_parallel,
        vec_env_cls=vec_env_cls
    )
    
    eval_env = DummyVecEnv([create_env_fn(is_eval=True, suffix="_eval_cb")]) if EvalCallback and Monitor else None

    return train_env, eval_env


def setup_training_callbacks(
    rl_config: Dict[str, Any],
    paths: Dict[str, str],
    run_identifier: str,
    eval_env: Optional[VecEnv]
) -> List[BaseCallback]:
    """
    Konfiguriert und gibt eine Liste von Trainings-Callbacks zurück.
    """
    if not BaseCallback or not CheckpointCallback:
        return []

    run_conf = rl_config.get("run_config", {})
    callbacks_list: List[BaseCallback] = []
    
    chckpt_pth = paths.get("checkpoint_path")
    if chckpt_pth:
        os.makedirs(chckpt_pth, exist_ok=True)
        checkpoint_callback = CheckpointCallback(
            save_freq=run_conf.get("checkpoint_interval_sb3_model_save", 10000),
            save_path=chckpt_pth,
            name_prefix=run_identifier
        )
        callbacks_list.append(checkpoint_callback)

    if eval_env and EvalCallback:
        eval_log_path_cb = paths.get("eval_callback_log_dir")
        best_model_save_path_cb = os.path.join(paths.get("final_model_dir", "."), "best_model_via_callback")

        # KORREKTUR: Explizit die Verzeichnisse für den Eval-Callback erstellen
        if eval_log_path_cb:
            os.makedirs(eval_log_path_cb, exist_ok=True)
        if best_model_save_path_cb:
            os.makedirs(best_model_save_path_cb, exist_ok=True)
        
        eval_callback_instance = EvalCallback(
            eval_env,
            best_model_save_path=best_model_save_path_cb,
            log_path=eval_log_path_cb,
            eval_freq=run_conf.get("eval_freq_sb3_learn", 5000),
            n_eval_episodes=run_conf.get("n_eval_episodes_callback", 5),
            deterministic=True,
            render=False
        )
        callbacks_list.append(eval_callback_instance)
        logger.info(f"EvalCallback konfiguriert: LogPath='{eval_log_path_cb}', BestModelPath='{best_model_save_path_cb}'")
    
    return callbacks_list


def create_rl_model(
    rl_config: Dict[str, Any],
    train_vec_env: VecEnv,
    tensorboard_log_path: str
) -> Optional[BaseAlgorithm]:
    """
    Erstellt und konfiguriert das RL-Modell basierend auf der Konfiguration.
    """
    agent_conf = rl_config.get("agent_config", {})
    rl_algorithm_name = agent_conf.get("rl_algorithm", "PPO").upper()
    
    model_params = {
        "learning_rate": agent_conf.get("learning_rate", 3e-4),
        "gamma": agent_conf.get("gamma", 0.99),
        "n_steps": agent_conf.get("n_steps_ppo", 2048),
        "batch_size": agent_conf.get("batch_size_ppo", 64),
        "n_epochs": agent_conf.get("n_epochs_ppo", 10),
        "gae_lambda": agent_conf.get("gae_lambda_ppo", 0.95),
        "clip_range": agent_conf.get("clip_range_ppo", 0.2),
        "ent_coef": agent_conf.get("ent_coef", 0.0),
        "vf_coef": agent_conf.get("vf_coef", 0.5),
        "max_grad_norm": agent_conf.get("max_grad_norm_ppo", 0.5),
        "policy_kwargs": agent_conf.get("policy_kwargs", None),
        "verbose": 0,
        "tensorboard_log": tensorboard_log_path,
    }

    model = None
    if rl_algorithm_name == "MASKABLEPPO" and MaskablePPO:
        logger.info(f"Verwende MaskablePPO Agenten.")
        model = MaskablePPO(MaskableActorCriticPolicy, train_vec_env, **model_params)
    elif rl_algorithm_name == "PPO" and PPO:
        logger.info(f"Verwende Standard PPO Agenten.")
        model = PPO("MlpPolicy", train_vec_env, **model_params)
    else:
        logger.error(f"Algorithmus '{rl_algorithm_name}' nicht verfügbar oder unbekannt.")

    return model

def configure_sb3_model_logger(
    model: Optional[BaseAlgorithm],
    tensorboard_log_path: str,
    sb3_logger_configure_fn: Optional[Callable]
) -> None:
    """
    Konfiguriert den Logger für das SB3-Modell manuell.
    """
    if not model or not sb3_logger_configure_fn:
        return

    tb_log_path = model.tensorboard_log or tensorboard_log_path
    if tb_log_path:
        os.makedirs(tb_log_path, exist_ok=True)
        manual_logger = sb3_logger_configure_fn(folder=tb_log_path, format_strings=["stdout", "tensorboard"])
        model.set_logger(manual_logger)
        logger.info(f"SB3 Logger manuell für Modell auf Pfad '{tb_log_path}' gesetzt.")