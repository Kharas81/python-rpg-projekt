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

if __name__ == '__main__': # PYTHONPATH Anpassung nur wenn direkt ausgeführt
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)

try:
    from src.utils import logging_setup 
    from src.environment.rpg_env import RPGEnv 
    from stable_baselines3 import PPO # Beispiel für SB3
    from stable_baselines3.common.env_util import make_vec_env # Für parallele Umgebungen
    from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback # Für Checkpoints und Evaluierung
    # Weitere SB3 Importe nach Bedarf
except ImportError as e:
    print(f"Fehler bei initialen Imports in rl_training.py: {e}. "
          "Stellen Sie sicher, dass Stable Baselines3 und PyTorch/TensorFlow installiert sind "
          "(`pip install stable-baselines3[extra]`) und PYTHONPATH korrekt ist.")
    sys.exit(1)

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
    
    # opponent_setup_config wird direkt an RPGEnv übergeben
    opponent_setup_for_env = env_conf_from_file.get("opponent_setup", 
                                                     {"num_opponents": 1, "level_pool": "1-2", "ids": ["goblin_lv1"]}) # Default
    
    max_episode_steps = env_conf_from_file.get("max_episode_steps", 50)
    reward_weights_for_env = env_conf_from_file.get("reward_weights")

    total_timesteps = run_conf.get("total_timesteps")
    num_training_episodes = run_conf.get("num_training_episodes") # Wird in SB3 nicht direkt für learn() verwendet
    log_interval_sb3 = run_conf.get("log_interval_sb3_learn", 2048) # SB3 logt nach Timesteps
    checkpoint_interval_sb3 = run_conf.get("checkpoint_interval_sb3_learn", 10000)
    model_save_path_prefix = run_conf.get("model_save_path_prefix", "models/rl_agent") # z.B. models/ppo_krieger
    
    use_curriculum = adv_conf.get("use_curriculum_learning", False)
    curriculum_file = adv_conf.get("curriculum_definition_file")
    num_parallel = adv_conf.get("num_parallel_runs", 1)

    logger.info(f"Agent: {hero_id} | Algo: {rl_algorithm_name} | Opponent Setup: {opponent_setup_for_env}")
    
    if not total_timesteps and not num_training_episodes:
        logger.error("Weder 'total_timesteps' noch 'num_training_episodes' in run_config. Training nicht möglich.")
        return
    if num_training_episodes and not total_timesteps:
        logger.warning("'num_training_episodes' ist für SB3 learn() nicht direkt nutzbar. Bitte 'total_timesteps' setzen.")
        # Fallback: grobe Schätzung, wenn nur Episoden gegeben sind
        total_timesteps = num_training_episodes * max_episode_steps 


    # --- Umgebung erstellen ---
    try:
        # Funktion, um die Umgebung zu erstellen (nötig für make_vec_env)
        def create_env_fn():
            env_instance = RPGEnv(
                hero_id=hero_id,
                opponent_setup_config=opponent_setup_for_env,
                max_episode_steps=max_episode_steps,
                reward_config=reward_weights_for_env 
            )
            return env_instance

        if num_parallel > 1:
            logger.info(f"Verwende {num_parallel} parallele Umgebungen für das Training.")
            # `DummyVecEnv` ist einfacher zu debuggen, `SubprocVecEnv` für echte Parallelität
            env = make_vec_env(create_env_fn, n_envs=num_parallel, vec_env_cls=None) # None -> auto-select (oft DummyVecEnv)
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
        # Sicherstellen, dass Speicherverzeichnisse existieren
        save_dir = os.path.dirname(model_save_path_prefix)
        if save_dir: os.makedirs(save_dir, exist_ok=True) # Für Modelle
        checkpoint_dir = os.path.join(save_dir, "checkpoints")
        os.makedirs(checkpoint_dir, exist_ok=True) # Für Checkpoints
        tensorboard_log_dir = os.path.join(os.path.dirname(save_dir) if save_dir else ".", "rl_tensorboard_logs", os.path.basename(model_save_path_prefix))
        os.makedirs(tensorboard_log_dir, exist_ok=True)


        # Callbacks
        checkpoint_callback = CheckpointCallback(
            save_freq=max(1, checkpoint_interval_sb3 // num_parallel), # Frequenz pro VecEnv-Step
            save_path=checkpoint_dir,
            name_prefix=os.path.basename(model_save_path_prefix)
        )
        # EvalCallback kann hier auch nützlich sein, um während des Trainings zu evaluieren
        # eval_env = create_env_fn() # Separate Eval-Umgebung
        # eval_callback = EvalCallback(eval_env, best_model_save_path=os.path.join(save_dir, "best_model/"),
        #                              log_path=os.path.join(save_dir, "eval_logs/"), eval_freq=max(1, 5000 // num_parallel),
        #                              deterministic=True, render=False)


        # Hyperparameter aus agent_config laden
        learning_rate = agent_conf.get("learning_rate", 3e-4)
        n_steps_ppo = agent_conf.get("n_steps_ppo", 2048) # Für PPO: Anzahl Schritte pro Rollout-Buffer-Füllung pro Env
        batch_size_ppo = agent_conf.get("batch_size_ppo", 64) 
        gamma = agent_conf.get("gamma", 0.99)
        # ... weitere spezifische Parameter für den Algorithmus ...

        if rl_algorithm_name == "PPO":
            model = PPO("MlpPolicy", env, verbose=1, 
                        learning_rate=learning_rate, 
                        n_steps=n_steps_ppo // num_parallel if num_parallel > 0 else n_steps_ppo, # Anpassen für VecEnv
                        batch_size=batch_size_ppo, 
                        gamma=gamma,
                        tensorboard_log=tensorboard_log_dir
                        # Weitere PPO Parameter hier...
                       )
        else:
            logger.error(f"Unbekannter oder nicht unterstützter RL-Algorithmus: {rl_algorithm_name}")
            if hasattr(env, 'close'): env.close()
            return

        logger.info(f"Starte Training des {rl_algorithm_name}-Agenten für ca. {total_timesteps} Timesteps...")
        # TODO: Curriculum Learning Logik hier einbauen, falls use_curriculum == True
        # Dies würde die Umgebung oder deren Konfiguration zwischen Trainingsphasen ändern.

        model.learn(
            total_timesteps=total_timesteps, 
            callback=[checkpoint_callback], # eval_callback hier hinzufügen, falls gewünscht
            progress_bar=True
        )

        final_model_path = f"{model_save_path_prefix}_final.zip"
        model.save(final_model_path)
        logger.info(f"Training abgeschlossen. Finale Modell gespeichert unter: {final_model_path}")

    except Exception as e:
        logger.error(f"Ein Fehler ist während des RL-Trainings aufgetreten: {e}", exc_info=True)
    finally:
        if hasattr(env, 'close'): 
            env.close()
        # if 'eval_env' in locals() and hasattr(eval_env, 'close'):
        #     eval_env.close()

    logger.info("RL-Trainingsprozess beendet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Agent Training Skript.")
    parser.add_argument("--config", type=str, required=True, help="Pfad zur RL-Setup-Konfigurationsdatei (.json5).")
    args = parser.parse_args()
    # Logging wird durch logging_setup.py aus main.py oder beim direkten Import von RPGEnv initialisiert.
    # Für direktes Ausführen dieses Skripts, stellen wir sicher, dass es grundlegend konfiguriert ist.
    if not logging.getLogger().hasHandlers(): # Prüfen, ob schon Handler da sind
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    train_agent(args.config)