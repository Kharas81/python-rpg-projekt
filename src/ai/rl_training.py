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
from typing import Optional, Dict, Any, List # KORREKTUR: Notwendige Typ-Hinweise importieren

# PYTHONPATH Anpassung für direktes Ausführen
if __name__ == '__main__':
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)

try:
    from src.utils import logging_setup 
    from src.environment.rpg_env import RPGEnv 
    from stable_baselines3 import PPO 
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.callbacks import CheckpointCallback 
except ImportError as e:
    # Logger ist hier noch nicht initialisiert, daher print
    print(f"Fehler bei initialen Imports in rl_training.py: {e}. "
          "Stellen Sie sicher, dass Stable Baselines3 und PyTorch/TensorFlow installiert sind "
          "(`pip install stable-baselines3[extra]`) und PYTHONPATH korrekt ist.")
    # Hier nicht sys.exit(1), damit der Rest des Moduls ggf. noch für Import-Tests geladen werden kann,
    # aber die train_agent Funktion wird fehlschlagen.
    # In einer Produktionsumgebung wäre sys.exit(1) hier sinnvoll, wenn SB3 fehlt.
    PPO = None # Dummy, um spätere Code-Referenzen nicht crashen zu lassen, wenn SB3 fehlt
    make_vec_env = None
    CheckpointCallback = None


logger = logging.getLogger(__name__) # Logger erst nach sys.path Anpassung und pot. logging_setup holen

def load_rl_config(config_path: str) -> Optional[Dict[str, Any]]:
    """Lädt eine RL-Setup-Konfigurationsdatei."""
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
    """
    Hauptfunktion zum Trainieren eines RL-Agenten.
    """
    logger.info(f"Starte RL-Trainingsprozess mit Konfiguration: {config_path}")
    
    rl_config = load_rl_config(config_path)
    if not rl_config:
        return

    setup_type = rl_config.get("setup_type")
    if setup_type != "training":
        logger.error(f"Falscher setup_type ('{setup_type}') in Konfigurationsdatei. Erwartet 'training'.")
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
    num_training_episodes = run_conf.get("num_training_episodes") 
    log_interval_sb3 = run_conf.get("log_interval_sb3_learn", 1) # Klein für Test
    checkpoint_interval_sb3 = run_conf.get("checkpoint_interval_sb3_learn", 1000) # Pro VecEnv Step
    model_save_path_prefix = run_conf.get("model_save_path_prefix", "models/rl_agent") 
    
    use_curriculum = adv_conf.get("use_curriculum_learning", False)
    curriculum_file = adv_conf.get("curriculum_definition_file")
    num_parallel = adv_conf.get("num_parallel_runs", 1)

    logger.info(f"Agent: {hero_id} | Algo: {rl_algorithm_name} | Opponent Setup: {opponent_setup_for_env}")
    
    if not total_timesteps: # SB3 braucht total_timesteps
        if num_training_episodes:
            logger.warning("'num_training_episodes' ist für SB3 learn() nicht direkt nutzbar. Setze total_timesteps = num_episodes * max_steps.")
            total_timesteps = num_training_episodes * max_episode_steps
        else:
            logger.error("Weder 'total_timesteps' noch 'num_training_episodes' in run_config. Training nicht möglich.")
            return
    if total_timesteps == 0 : # Wenn num_training_episodes * max_episode_steps 0 ist
        logger.error("total_timesteps ist 0. Training nicht möglich.")
        return


    # --- Umgebung erstellen ---
    env = None # Initialisiere env außerhalb des try-Blocks für finally
    try:
        def create_env_fn():
            env_instance = RPGEnv(
                hero_id=hero_id,
                opponent_setup_config=opponent_setup_for_env, # RPGEnv muss dies verarbeiten
                max_episode_steps=max_episode_steps,
                reward_config=reward_weights_for_env 
            )
            return env_instance

        if num_parallel > 1 and make_vec_env: # make_vec_env könnte None sein, wenn SB3 nicht importiert wurde
            logger.info(f"Verwende {num_parallel} parallele Umgebungen für das Training.")
            env = make_vec_env(create_env_fn, n_envs=num_parallel)
        else:
            logger.info("Verwende eine einzelne Umgebung für das Training.")
            env = create_env_fn()
        
        logger.info("RL-Umgebung(en) erfolgreich erstellt.")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der RL-Umgebung(en): {e}", exc_info=True)
        return

    # --- Agent erstellen und trainieren ---
    model = None
    try:
        if PPO is None or CheckpointCallback is None: # Prüfen ob SB3 geladen wurde
            logger.error("Stable Baselines3 konnte nicht importiert werden. Training abgebrochen.")
            if env and hasattr(env, 'close'): env.close()
            return

        save_dir = os.path.dirname(model_save_path_prefix)
        if save_dir: os.makedirs(save_dir, exist_ok=True) 
        checkpoint_dir = os.path.join(save_dir if save_dir else ".", "checkpoints") # Fallback für checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True) 
        
        # Tensorboard Log-Verzeichnis relativ zum Projekt-Root oder einem spezifischen Log-Ordner
        # z.B. logs/rl_tensorboard_logs/experiment_name
        experiment_name = os.path.basename(model_save_path_prefix) if model_save_path_prefix else "default_rl_run"
        tensorboard_log_dir = os.path.join("logs", "rl_tensorboard_logs", experiment_name)
        os.makedirs(tensorboard_log_dir, exist_ok=True)


        checkpoint_callback = CheckpointCallback(
            save_freq=max(1, checkpoint_interval_sb3 // num_parallel), 
            save_path=checkpoint_dir,
            name_prefix=os.path.basename(model_save_path_prefix) if model_save_path_prefix else "rl_model"
        )
        
        learning_rate = agent_conf.get("learning_rate", 3e-4)
        n_steps_ppo = agent_conf.get("n_steps_ppo", 2048) 
        batch_size_ppo = agent_conf.get("batch_size_ppo", 64) 
        gamma = agent_conf.get("gamma", 0.99)

        if rl_algorithm_name == "PPO":
            model = PPO("MlpPolicy", env, verbose=1, 
                        learning_rate=learning_rate, 
                        n_steps=n_steps_ppo // num_parallel if num_parallel > 0 and n_steps_ppo >= num_parallel else n_steps_ppo,
                        batch_size=batch_size_ppo, 
                        gamma=gamma,
                        tensorboard_log=tensorboard_log_dir
                       )
        else:
            logger.error(f"Unbekannter oder nicht unterstützter RL-Algorithmus: {rl_algorithm_name}")
            if hasattr(env, 'close'): env.close()
            return

        logger.info(f"Starte Training des {rl_algorithm_name}-Agenten für {total_timesteps} Timesteps...")
        
        # TODO: Curriculum Learning
        # if use_curriculum and curriculum_file:
        #    logger.info(f"Curriculum Learning aktiviert mit Datei: {curriculum_file}")
        #    # Implementiere Logik zum Laden des Curriculums und Anpassen der Env Parameter
        
        model.learn(
            total_timesteps=int(total_timesteps), # Muss int sein
            callback=[checkpoint_callback], 
            progress_bar=True,
            log_interval=log_interval_sb3 # Wie oft SB3 intern logt (z.B. für Tensorboard)
        )

        final_model_path = f"{model_save_path_prefix}_final.zip"
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
    
    # Logging für das Skript selbst. logging_setup aus main.py sollte bereits das globale Logging konfiguriert haben.
    # Wenn dieses Skript jedoch direkt aufgerufen wird, ist es möglicherweise nicht initialisiert.
    if not logging.getLogger().hasHandlers(): 
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
        logger.info("Fallback-Logging für rl_training.py aktiviert, da kein globaler Handler gefunden wurde.")
    
    train_agent(args.config)