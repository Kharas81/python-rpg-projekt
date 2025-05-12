# src/ai/rl_training.py
"""
Skript zum Trainieren eines Reinforcement Learning Agenten für das RPG-Spiel.
Nimmt eine RL-Setup-Konfigurationsdatei als Eingabe.
"""
import argparse
import logging
import json5 
import os
import sys
from typing import Optional, Dict, Any, List 

if __name__ == '__main__' and __package__ is None: 
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
    try:
        from src.utils import logging_setup 
    except ImportError:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
        logging.info("Fallback-Logging für rl_training.py (vor Haupt-Imports) aktiviert.")

try:
    from src.environment.rpg_env import RPGEnv 
    from stable_baselines3 import PPO 
    from stable_baselines3.common.env_util import make_vec_env, DummyVecEnv 
    from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback 
    from stable_baselines3.common.monitor import Monitor 
    SB3_AVAILABLE = True
except ImportError as e:
    print(f"FEHLER bei Stable Baselines3 Imports in rl_training.py: {e}. ")
    SB3_AVAILABLE = False
    PPO = None 
    make_vec_env = None
    CheckpointCallback = None
    EvalCallback = None
    Monitor = None
    DummyVecEnv = None

logger = logging.getLogger(__name__) 

def load_rl_config(config_path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(config_path):
        logger.error(f"RL-Konfigurationsdatei nicht gefunden: {config_path}")
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json5.load(f)
        logger.info(f"RL-Konfiguration erfolgreich aus '{config_path}' geladen.")
        return config
    except Exception as e:
        logger.error(f"Fehler beim Laden der RL-Konfiguration aus '{config_path}': {e}", exc_info=True)
        return None

def train_agent(config_path: str):
    logger.info(f"Starte RL-Trainingsprozess mit Konfiguration: {config_path}")
    
    if not SB3_AVAILABLE: 
        logger.error("Stable Baselines3 ist nicht verfügbar. Training kann nicht gestartet werden.")
        return

    rl_config = load_rl_config(config_path)
    if not rl_config: return

    setup_type = rl_config.get("setup_type")
    if setup_type != "training":
        logger.error(f"Falscher setup_type ('{setup_type}'). Erwartet 'training'.")
        return

    description = rl_config.get("description", "Keine Beschreibung")
    logger.info(f"Trainingsbeschreibung: {description}")

    agent_conf = rl_config.get("agent_config", {})
    env_conf_from_file = rl_config.get("environment_config", {})
    run_conf = rl_config.get("run_config", {})
    adv_conf = rl_config.get("advanced_rl_config", {})

    hero_id = agent_conf.get("agent_hero_id", "krieger")
    rl_algorithm_name = agent_conf.get("rl_algorithm", "PPO").upper()
    
    opponent_setup_for_env = env_conf_from_file.get("opponent_setup", 
                                                     {"num_opponents": 1, "level_pool": "1-2", "ids": ["goblin_lv1"]})
    
    max_episode_steps = env_conf_from_file.get("max_episode_steps", 50)
    reward_weights_for_env = env_conf_from_file.get("reward_weights")

    total_timesteps = run_conf.get("total_timesteps")
    if not total_timesteps: 
        num_training_episodes = run_conf.get("num_training_episodes")
        if num_training_episodes:
            total_timesteps = num_training_episodes * max_episode_steps
            logger.info(f"Berechne total_timesteps: {num_training_episodes} Episoden * {max_episode_steps} Steps/Episode = {total_timesteps} Timesteps.")
        else:
            logger.error("Weder 'total_timesteps' noch 'num_training_episodes' sinnvoll in run_config. Training nicht möglich.")
            return
    if total_timesteps <= 0:
        logger.error(f"total_timesteps ({total_timesteps}) muss positiv sein. Training nicht möglich.")
        return
        
    log_interval_sb3 = run_conf.get("log_interval_sb3_learn", 1) 
    checkpoint_interval_sb3 = run_conf.get("checkpoint_interval_sb3_learn", 1000) 
    model_save_path_prefix = run_conf.get("model_save_path_prefix", "models/rl_agent") 
    
    num_parallel = adv_conf.get("num_parallel_runs", 1)
    use_monitor = adv_conf.get("use_sb3_monitor", True)

    logger.info(f"Agent: {hero_id} | Algo: {rl_algorithm_name} | Opponent Setup: {opponent_setup_for_env}")
    logger.info(f"Trainiere für {total_timesteps} totale Zeitschritte.")

    env = None 
    try:
        def create_env_fn():
            env_instance = RPGEnv(
                hero_id=hero_id,
                opponent_setup_config=opponent_setup_for_env,
                max_episode_steps=max_episode_steps,
                reward_config=reward_weights_for_env 
            )
            if use_monitor and Monitor is not None: 
                monitor_log_dir_base = os.path.join("logs", "sb3_monitor_logs")
                experiment_name_for_monitor = os.path.basename(model_save_path_prefix) if model_save_path_prefix else "default_run"
                monitor_log_path = os.path.join(monitor_log_dir_base, experiment_name_for_monitor)
                os.makedirs(monitor_log_path, exist_ok=True)
                # Wenn num_parallel > 1, muss jeder Worker einen eigenen Monitor-Pfad haben oder der Monitor
                # muss um den VecEnv Wrapper außen herum gelegt werden (letzteres ist üblicher).
                # Für den Moment: Bei num_parallel=1 ist der Pfad okay.
                env_instance = Monitor(env_instance, filename=os.path.join(monitor_log_path, "monitor_log_0"), allow_early_resets=True)
            return env_instance

        if num_parallel > 1 and make_vec_env and DummyVecEnv : # Sicherstellen, dass DummyVecEnv auch da ist
            logger.info(f"Verwende {num_parallel} parallele Umgebungen für das Training.")
            env = make_vec_env(create_env_fn, n_envs=num_parallel, vec_env_cls=DummyVecEnv)
            # Wenn VecEnv verwendet wird, wird der Monitor typischerweise um jede einzelne Sub-Umgebung gelegt,
            # oder der VecEnv selbst bietet Logging-Möglichkeiten. SB3's make_vec_env kann `Monitor` automatisch hinzufügen.
            # Wir haben ihn schon in create_env_fn, was für DummyVecEnv ok sein sollte.
        else:
            logger.info("Verwende eine einzelne Umgebung für das Training.")
            env = create_env_fn() 
        
        logger.info("RL-Umgebung(en) erfolgreich erstellt.")

        save_dir = os.path.dirname(model_save_path_prefix)
        if save_dir and not os.path.exists(save_dir): os.makedirs(save_dir, exist_ok=True) 
        
        experiment_base_name = os.path.basename(model_save_path_prefix) if model_save_path_prefix else "rl_model"
        checkpoint_dir = os.path.join(save_dir if save_dir else ".", "checkpoints", experiment_base_name)
        os.makedirs(checkpoint_dir, exist_ok=True) 
        
        tensorboard_log_dir = os.path.join("logs", "rl_tensorboard_logs", experiment_base_name)
        os.makedirs(tensorboard_log_dir, exist_ok=True) # KORREKTUR: Korrekten Variablennamen verwenden

        if CheckpointCallback is None: raise ImportError("CheckpointCallback von SB3 nicht verfügbar.")
        checkpoint_callback = CheckpointCallback(
            save_freq=max(1, checkpoint_interval_sb3 // num_parallel if num_parallel > 0 else checkpoint_interval_sb3), 
            save_path=checkpoint_dir,
            name_prefix=experiment_base_name 
        )
        
        learning_rate = agent_conf.get("learning_rate", 3e-4)
        n_steps_ppo = agent_conf.get("n_steps_ppo", 2048) 
        batch_size_ppo = agent_conf.get("batch_size_ppo", 64) 
        gamma = agent_conf.get("gamma", 0.99)
        ent_coef = agent_conf.get("ent_coef", 0.0) 
        vf_coef = agent_conf.get("vf_coef", 0.5)  

        if PPO is None: raise ImportError("PPO von SB3 nicht verfügbar.")
        if rl_algorithm_name == "PPO":
            model = PPO("MlpPolicy", env, verbose=1, 
                        learning_rate=learning_rate, 
                        n_steps=max(1, n_steps_ppo // num_parallel if num_parallel > 0 else n_steps_ppo),
                        batch_size=batch_size_ppo, 
                        gamma=gamma,
                        ent_coef=ent_coef,
                        vf_coef=vf_coef,
                        tensorboard_log=tensorboard_log_dir
                       )
        else:
            logger.error(f"Unbekannter oder nicht implementierter RL-Algorithmus: {rl_algorithm_name}")
            if hasattr(env, 'close'): env.close()
            return

        logger.info(f"Starte Training des {rl_algorithm_name}-Agenten für {total_timesteps} Timesteps...")
        
        model.learn(
            total_timesteps=int(total_timesteps), 
            callback=[checkpoint_callback], 
            progress_bar=True,
            log_interval=log_interval_sb3 
        )

        final_model_path = f"{model_save_path_prefix}_final_{total_timesteps}steps.zip"
        model.save(final_model_path)
        logger.info(f"Training abgeschlossen. Finale Modell gespeichert unter: {final_model_path}")

    except Exception as e:
        logger.error(f"Ein Fehler ist während des RL-Trainings aufgetreten: {e}", exc_info=True)
    finally:
        if env and hasattr(env, 'close'): 
            env.close()

    logger.info("RL-Trainingsprozess beendet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Agent Training Skript.")
    parser.add_argument("--config", type=str, required=True, help="Pfad zur RL-Setup-Konfigurationsdatei (.json5).")
    args = parser.parse_args()
    
    if not logging.getLogger().hasHandlers(): 
        try:
            from src.utils import logging_setup 
            logger.info("Zentrales Logging-Setup für rl_training.py (direkter Aufruf) geladen.")
        except ImportError:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
            logger.info("Fallback-Logging für rl_training.py aktiviert.")
    
    train_agent(args.config)
