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
import datetime 
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
    from stable_baselines3.common.vec_env import SubprocVecEnv
    from src.config.user_config_manager import UserConfigManager 
    from tools.context_extractor import extract_and_save_context # NEU
    SB3_AVAILABLE = True
except ImportError as e:
    # Logger ist hier noch nicht sicher initialisiert, daher print
    print(f"FEHLER bei Stable Baselines3 oder anderen Imports in rl_training.py: {e}. ")
    SB3_AVAILABLE = False
    PPO=None; make_vec_env=None; CheckpointCallback=None; EvalCallback=None; Monitor=None
    DummyVecEnv=None; SubprocVecEnv=None; UserConfigManager=None; extract_and_save_context=None

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
    logger.info(f"Starte RL-Trainingsprozess: {description}")
    logger.info(f"Verwende Konfiguration: {config_path}")


    agent_conf = rl_config.get("agent_config", {})
    env_conf_from_file = rl_config.get("environment_config", {})
    run_conf = rl_config.get("run_config", {})
    adv_conf = rl_config.get("advanced_rl_config", {})

    hero_id = agent_conf.get("agent_hero_id", "krieger")
    rl_algorithm_name = agent_conf.get("rl_algorithm", "PPO").upper()
    opponent_setup_for_env = env_conf_from_file.get("opponent_setup", {"ids": ["goblin_lv1"]})
    max_episode_steps = env_conf_from_file.get("max_episode_steps", 50)
    reward_weights_for_env = env_conf_from_file.get("reward_weights")
    total_timesteps = run_conf.get("total_timesteps")
    
    if not total_timesteps:
        num_training_episodes = run_conf.get("num_training_episodes")
        total_timesteps = (num_training_episodes * max_episode_steps) if num_training_episodes else 2048 # Fallback
        logger.info(f"total_timesteps aus Episoden und Steps berechnet: {total_timesteps}")
    if total_timesteps <= 0: logger.error("total_timesteps muss positiv sein."); return
        
    log_interval_sb3 = run_conf.get("log_interval_sb3_learn", 1) 
    checkpoint_interval_sb3_model_save = run_conf.get("checkpoint_interval_sb3_model_save", 10000)
    
    # Basispfad für alle Artefakte dieses Laufs
    # model_save_path_prefix aus der Konfig ist eher der Name des Modells/Experiments
    experiment_prefix_from_config = run_conf.get("experiment_name_prefix", "rl_experiment")
    
    num_parallel = adv_conf.get("num_parallel_runs", 1)
    use_monitor = adv_conf.get("use_sb3_monitor", True)
    use_subproc_vec_env = adv_conf.get("use_subproc_vec_env", False) 


    # --- Experiment-Verzeichnisstruktur erstellen ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_name = f"{experiment_prefix_from_config}_{rl_algorithm_name.lower()}_{hero_id}_{timestamp}"
    
    project_root_for_logs = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
    base_run_dir = os.path.join(project_root_for_logs, "logs", "rl_runs_archive", experiment_name)
    os.makedirs(base_run_dir, exist_ok=True)
    logger.info(f"Alle Artefakte für diesen Lauf werden in '{base_run_dir}' gespeichert.")

    tensorboard_log_path = os.path.join(base_run_dir, "tensorboard")
    monitor_log_path = os.path.join(base_run_dir, "monitor") # Für VecEnv mit Monitor
    checkpoint_path = os.path.join(base_run_dir, "checkpoints")
    final_model_dir = os.path.join(base_run_dir, "models") 
    os.makedirs(tensorboard_log_path, exist_ok=True)
    os.makedirs(monitor_log_path, exist_ok=True)
    os.makedirs(checkpoint_path, exist_ok=True)
    os.makedirs(final_model_dir, exist_ok=True)
    
    context_file_path = os.path.join(base_run_dir, f"context__{experiment_name}.md")

    # --- Context Extractor aufrufen ---
    if extract_and_save_context:
        logger.info("Starte Context Extractor...")
        # Der Pfad zur RL-Konfigurationsdatei selbst sollte relativ zum Projekt-Root sein
        # für den Extractor, wenn er so konfiguriert ist.
        try:
            # config_path ist bereits absolut oder relativ zum Ausführungsort
            # Für den Extractor brauchen wir ihn relativ zum Projekt-Root, falls er nicht absolut ist
            if not os.path.isabs(config_path):
                # Annahme: config_path wurde relativ zum Projekt-Root übergeben (z.B. von main.py)
                # oder es ist ein Pfad, den der Extractor direkt verwenden kann.
                # Sicherer ist, einen absoluten Pfad zu übergeben.
                abs_config_path = os.path.abspath(config_path)
            else:
                abs_config_path = config_path

            # Der Extractor erwartet Pfade relativ zum Projekt-Root in seiner Konfig.
            # Wir übergeben den Pfad zur aktuell verwendeten RL-Konfig als additional_full_content_file.
            # Wenn der Extractor PROJECT_ROOT kennt, kann er relative Pfade korrekt auflösen.
            # Hier übergeben wir den relativen Pfad von PROJECT_ROOT (des Extractors) aus.
            # Dies ist etwas umständlich und hängt von der Implementierung des Extractors ab.
            # Einfacher: Der Extractor sollte absolute Pfade für additional_full_content_files akzeptieren.
            # Annahme: context_extractor.PROJECT_ROOT ist korrekt gesetzt.
            rel_config_path_for_extractor = os.path.relpath(abs_config_path, PROJECT_ROOT)


            # Wir erstellen eine temporäre Liste der zu extrahierenden Dateien,
            # damit wir die RL-Konfig hinzufügen können, ohne die globale Liste im Extractor zu ändern.
            additional_files_for_this_run = [rel_config_path_for_extractor]
            
            extracted_path = extract_and_save_context(
                run_timestamp_or_name=experiment_name, 
                output_filepath=context_file_path,
                additional_full_content_files=additional_files_for_this_run
            )
            if extracted_path:
                logger.info(f"Kontext erfolgreich nach '{extracted_path}' extrahiert.")
            else:
                logger.warning("Context Extractor konnte Kontext nicht erstellen.")

        except Exception as e_extract:
            logger.error(f"Fehler beim Aufrufen des Context Extractors: {e_extract}", exc_info=True)
    else:
        logger.warning("Context Extractor nicht verfügbar oder Import fehlgeschlagen.")

    env = None 
    eval_env_for_callback = None # Separate Env für EvalCallback
    try:
        def create_env_fn(is_eval=False): # is_eval um Monitor-Pfade ggf. zu unterscheiden
            env_instance = RPGEnv(
                hero_id=hero_id,
                opponent_setup_config=opponent_setup_for_env,
                max_episode_steps=max_episode_steps,
                reward_config=reward_weights_for_env,
                render_mode=None # Kein Rendering während Training
            )
            # Monitor wird durch make_vec_env hinzugefügt, wenn monitor_dir gesetzt ist.
            # Bei einer einzelnen Env müssen wir ihn manuell hinzufügen.
            return env_instance

        if num_parallel > 1 and make_vec_env:
            vec_env_cls_to_use = SubprocVecEnv if use_subproc_vec_env and SubprocVecEnv else DummyVecEnv
            logger.info(f"Verwende {num_parallel} parallele Umgebungen ({vec_env_cls_to_use.__name__}).")
            env = make_vec_env(
                create_env_fn, 
                n_envs=num_parallel, 
                vec_env_cls=vec_env_cls_to_use,
                monitor_dir=monitor_log_path if use_monitor and Monitor else None,
                monitor_kwargs=({"allow_early_resets": True, "info_keywords": ("is_success",)},) # Beispiel für info_keywords
            )
        else: # Einzelne Umgebung
            logger.info("Verwende eine einzelne Umgebung.")
            env = create_env_fn()
            if use_monitor and Monitor and not isinstance(env, gym.vector.VecEnv): # Nur wenn nicht schon von make_vec_env gewrapped
                 # Für eine einzelne Env braucht der Monitor einen expliziten Dateinamen-Präfix
                 # da make_vec_env dies normalerweise für mehrere Envs handhabt.
                 env = Monitor(env, filename=os.path.join(monitor_log_path, "monitor_0"), allow_early_resets=True, info_keywords=("is_success",))
        
        logger.info("RL-Umgebung(en) erfolgreich erstellt.")

        # EvalEnv für den EvalCallback
        if EvalCallback: # Nur wenn EvalCallback importiert werden konnte
            eval_env_for_callback = create_env_fn(is_eval=True) # Eigene Instanz
            if Monitor: # Auch die Eval-Env mit Monitor wrappen für saubere Statistiken
                eval_monitor_log_dir = os.path.join(base_run_dir, "eval_monitor_logs")
                os.makedirs(eval_monitor_log_dir, exist_ok=True)
                eval_env_for_callback = Monitor(eval_env_for_callback, os.path.join(eval_monitor_log_dir, "monitor_eval"))
        else:
            eval_env_for_callback = None # Kein EvalCallback, keine EvalEnv nötig


        if CheckpointCallback is None or (EvalCallback is None and eval_env_for_callback is not None) : 
            raise ImportError("SB3 Callbacks nicht verfügbar.")

        # Frequenz für Checkpoints anpassen an VecEnv Steps
        actual_checkpoint_save_freq = max(1, checkpoint_interval_sb3_model_save // num_parallel if num_parallel > 0 else checkpoint_interval_sb3_model_save)
        checkpoint_callback = CheckpointCallback(
            save_freq=actual_checkpoint_save_freq, 
            save_path=checkpoint_path, 
            name_prefix=experiment_name 
        )
        
        callbacks_list = [checkpoint_callback]
        if eval_env_for_callback and EvalCallback:
            eval_freq_steps = max(1, run_conf.get("eval_freq_sb3_learn", 5000) // num_parallel if num_parallel > 0 else run_conf.get("eval_freq_sb3_learn", 5000))
            eval_log_path_cb = os.path.join(base_run_dir, "eval_callback_logs") # Eigener Log-Pfad für Callback
            best_model_save_cb_path = os.path.join(final_model_dir, "best_model") # Speichert bestes Modell
            
            eval_callback_instance = EvalCallback(
                eval_env_for_callback, 
                best_model_save_path=best_model_save_cb_path, 
                log_path=eval_log_path_cb, 
                eval_freq=eval_freq_steps,
                n_eval_episodes=run_conf.get("n_eval_episodes_callback", 5),
                deterministic=True, render=False
            )
            callbacks_list.append(eval_callback_instance)
        
        # Hyperparameter
        learning_rate = agent_conf.get("learning_rate", 3e-4)
        n_steps_ppo_cfg = agent_conf.get("n_steps_ppo", 2048) 
        # n_steps ist pro Umgebung in VecEnv
        n_steps_ppo_per_env = max(128, n_steps_ppo_cfg // num_parallel if num_parallel > 0 and n_steps_ppo_cfg >= num_parallel else n_steps_ppo_cfg)
        batch_size_ppo = agent_conf.get("batch_size_ppo", 64) 
        gamma = agent_conf.get("gamma", 0.99)
        ent_coef = agent_conf.get("ent_coef", 0.0) 
        vf_coef = agent_conf.get("vf_coef", 0.5)  

        if PPO is None: raise ImportError("PPO von SB3 nicht verfügbar.")

        if rl_algorithm_name == "PPO":
            model = PPO( "MlpPolicy", env, verbose=1, 
                        learning_rate=learning_rate, n_steps=n_steps_ppo_per_env,
                        batch_size=batch_size_ppo, gamma=gamma,
                        ent_coef=ent_coef, vf_coef=vf_coef,
                        tensorboard_log=tensorboard_log_path 
                       )
        else:
            logger.error(f"Algorithmus {rl_algorithm_name} nicht implementiert."); return

        logger.info(f"Starte Training des {rl_algorithm_name}-Agenten für {total_timesteps} Timesteps...")
        logger.info(f"TensorBoard Logs werden hier gespeichert: {model.tensorboard_log}")
        
        model.learn(
            total_timesteps=int(total_timesteps), 
            callback=callbacks_list, 
            progress_bar=True,
            log_interval=log_interval_sb3 
        )

        final_model_save_name = f"{experiment_name}_final_{int(total_timesteps)}steps.zip"
        final_model_path = os.path.join(final_model_dir, final_model_save_name)
        model.save(final_model_path)
        logger.info(f"Training abgeschlossen. Finale Modell gespeichert unter: {final_model_path}")

        # Speichere Pfad zum besten/finalen Modell
        if UserConfigManager:
            ucm = UserConfigManager()
            best_model_zip = os.path.join(final_model_dir, "best_model", "best_model.zip")
            if os.path.exists(best_model_zip):
                ucm.set_preference("last_trained_model_path", os.path.abspath(best_model_zip))
                logger.info(f"Pfad zum besten Modell in user_preferences.json5 gespeichert: {os.path.abspath(best_model_zip)}")
            else: # Fallback auf finales Modell
                ucm.set_preference("last_trained_model_path", os.path.abspath(final_model_path))
                logger.info(f"Pfad zum finalen Modell in user_preferences.json5 gespeichert: {os.path.abspath(final_model_path)}")


    except Exception as e:
        logger.error(f"Ein Fehler ist während des RL-Trainings aufgetreten: {e}", exc_info=True)
    finally:
        if env and hasattr(env, 'close'): env.close()
        if eval_env_for_callback and hasattr(eval_env_for_callback, 'close'): eval_env_for_callback.close()

    logger.info(f"RL-Trainingsprozess für '{experiment_name}' beendet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Agent Training Skript.")
    parser.add_argument("--config", type=str, required=True, help="Pfad zur RL-Setup-Konfigurationsdatei (.json5).")
    args = parser.parse_args()
    
    if not logging.getLogger().hasHandlers(): 
        try:
            from src.utils import logging_setup 
            logger.info("Zentrales Logging-Setup für rl_training.py (direkter Aufruf) geladen.")
        except ImportError:
            # Kritisch, wenn das Haupt-Logging nicht funktioniert, aber für direktes Testen ein Fallback
            logging.basicConfig(level=logging.DEBUG, # DEBUG für direktes Ausführen
                                format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
            logger.info("Fallback-Logging (DEBUG) für rl_training.py aktiviert.")
    
    train_agent(args.config)
