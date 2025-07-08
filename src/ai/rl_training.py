# src/ai/rl_training.py
"""
Skript zum Trainieren eines Reinforcement Learning Agenten für das RPG-Spiel.
Orchestriert den Trainingsprozess durch Aufruf von Hilfsfunktionen aus
rl_setup_utils und rl_utils. Unterstützt Standard-Training und Curriculum Learning.
"""
import os
import sys
import time
import argparse
import logging
import datetime
import cProfile
import pstats
import json5
from typing import Optional, Dict, Any, List, Callable, Tuple, Type
import gymnasium as gym
import numpy as np

# --- PYTHONPATH Anpassung ---
SCRIPT_DIR_RL_TRAINING = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT_RL_TRAINING = os.path.dirname(SCRIPT_DIR_RL_TRAINING)
PROJECT_ROOT_FROM_RL_TRAINING = os.path.dirname(SRC_ROOT_RL_TRAINING)
if PROJECT_ROOT_FROM_RL_TRAINING not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_FROM_RL_TRAINING)

# --- Lazy Loading der Module ---
_logging_setup_module = None
try:
    from src.utils import logging_setup as _logging_setup_module_import_early
    _logging_setup_module = _logging_setup_module_import_early
except ImportError: pass

logger = logging.getLogger(__name__)

# --- Haupt-Imports ---
try:
    from stable_baselines3.common.base_class import BaseAlgorithm
    from stable_baselines3.common.vec_env import VecEnv
    from stable_baselines3.common.logger import configure as sb3_logger_configure
    from src.config.user_config_manager import UserConfigManager
    from src.ui import cli_output
    from src.ai import rl_setup_utils, rl_utils
    try: from tools.context_extractor import extract_and_save_context
    except ImportError as e: extract_and_save_context = None; logger.warning(f"Context Extractor nicht importiert: {e}")
    SB3_AVAILABLE = True
except ImportError as e:
    print(f"FATAL: Wichtige RL-Module nicht importiert: {e}. Installation prüfen.")
    sys.exit(1)

def robust_get_action_masks(env_instance_possibly_wrapped: gym.Env) -> np.ndarray:
    """Sucht rekursiv nach der action_masks Methode in einer (möglicherweise gewrappten) Umgebung."""
    current_env = env_instance_possibly_wrapped
    while hasattr(current_env, 'env'):
        if hasattr(current_env, 'action_masks') and callable(current_env.action_masks):
            return current_env.action_masks() # type: ignore
        current_env = getattr(current_env, 'env') # type: ignore
    if hasattr(current_env, 'action_masks') and callable(current_env.action_masks):
        return current_env.action_masks() # type: ignore
    raise AttributeError(f"Konnte action_masks() in {type(current_env).__name__} nicht finden.")

def load_rl_config(config_path: str) -> Optional[Dict[str, Any]]:
    """Lädt die RL-Konfiguration sicher aus einer JSON5-Datei."""
    if not os.path.exists(config_path):
        logger.error(f"RL-Konfigurationsdatei nicht gefunden: {config_path}")
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json5.load(f)
    except Exception as e:
        logger.error(f"Fehler beim Laden der RL-Konfiguration '{config_path}': {e}", exc_info=True)
        return None

def _actual_training_logic(config_path_str: str, rl_config: Dict[str, Any], is_batch_mode: bool = False):
    """Hauptlogik, die den Trainingsprozess orcherstriert."""
    cli_output.set_execution_context("rl_training")
    
    start_timestamp = datetime.datetime.now()
    paths = rl_utils.setup_experiment_paths(
        base_output_dir_config_val=rl_config.get("output_base_directory"),
        project_root_path=PROJECT_ROOT_FROM_RL_TRAINING,
        experiment_prefix=rl_config.get("run_config", {}).get("experiment_name_prefix", "rl_experiment"),
        algorithm_name=rl_config.get("agent_config", {}).get("rl_algorithm", "PPO").upper(),
        hero_id=rl_config.get("agent_config", {}).get("agent_hero_id", "krieger"),
        start_timestamp=start_timestamp
    )
    
    cli_output.print_message(f"Experiment-Name: {paths['run_specific_identifier']}", force_console=True)
    if not is_batch_mode:
        try: input("Drücke Enter zum Fortfahren oder Strg+C zum Abbrechen...")
        except KeyboardInterrupt: cli_output.print_message("\nTraining abgebrochen.", cli_output.Colors.YELLOW, force_console=True); return

    rl_utils.initialize_run_logging_and_context(config_path_str, paths, _logging_setup_module, extract_and_save_context)

    # --- Curriculum Learning Logik ---
    adv_conf = rl_config.get("advanced_rl_config", {})
    use_curriculum = adv_conf.get("use_curriculum_learning", False)
    curriculum_stages = []
    total_curriculum_timesteps = 0

    if use_curriculum:
        curriculum_path = adv_conf.get("curriculum_definition_file")
        if curriculum_path:
            full_curriculum_path = os.path.join(PROJECT_ROOT_FROM_RL_TRAINING, curriculum_path)
            try:
                with open(full_curriculum_path, 'r', encoding='utf-8') as f:
                    curriculum_data = json5.load(f)
                curriculum_stages = curriculum_data.get("stages", [])
                total_curriculum_timesteps = sum(stage.get("timesteps", 0) for stage in curriculum_stages)
                logger.info(f"Curriculum Learning aktiviert. {len(curriculum_stages)} Stufen mit insgesamt {total_curriculum_timesteps} Timesteps geladen aus: {curriculum_path}")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Curriculum-Datei '{full_curriculum_path}': {e}. Fallback auf Standard-Training.", exc_info=True)
                use_curriculum = False
        else:
            logger.warning("`use_curriculum_learning` ist true, aber keine `curriculum_definition_file` angegeben. Fallback auf Standard-Training.")
            use_curriculum = False

    # --- Umgebung, Modell & Callbacks Setup ---
    train_vec_env, eval_vec_env = rl_setup_utils.create_vectorized_environments(rl_config, paths, paths["run_specific_identifier"], robust_get_action_masks)
    if not train_vec_env: logger.critical("Erstellung der Trainingsumgebung fehlgeschlagen. Abbruch."); return

    callbacks = rl_setup_utils.setup_training_callbacks(rl_config, paths, paths["run_specific_identifier"], eval_vec_env)
    model = rl_setup_utils.create_rl_model(rl_config, train_vec_env, paths["tensorboard_log_path"])
    if not model: logger.critical("Erstellung des RL-Modells fehlgeschlagen. Abbruch."); return
    
    rl_setup_utils.configure_sb3_model_logger(model, paths["tensorboard_log_path"], sb3_logger_configure)

    # --- Training ---
    try:
        if use_curriculum and curriculum_stages:
            # Curriculum-Trainingsschleife
            for i, stage in enumerate(curriculum_stages):
                stage_timesteps = stage.get("timesteps", 0)
                stage_opponent_setup = stage.get("opponent_setup")
                logger.info(f"--- Starte Curriculum Stufe {i+1}/{len(curriculum_stages)} für {stage_timesteps} Timesteps ---")
                logger.info(f"Gegner-Setup für diese Stufe: {stage_opponent_setup}")

                # Umgebung mit dem neuen Gegner-Setup aktualisieren
                if hasattr(train_vec_env, 'env_method'):
                    train_vec_env.env_method("reset", options={"opponent_setup": stage_opponent_setup})
                if eval_vec_env and hasattr(eval_vec_env, 'env_method'):
                    eval_vec_env.env_method("reset", options={"opponent_setup": stage_opponent_setup})
                
                # Wichtig: reset_num_timesteps=False, damit die Timesteps über die Stufen hinweg weiterzählen
                model.learn(total_timesteps=stage_timesteps, callback=callbacks, progress_bar=True, reset_num_timesteps=False)
            
            total_timesteps_trained = total_curriculum_timesteps
        else:
            # Standard-Trainingsschleife
            total_timesteps_trained = int(rl_config.get("run_config", {}).get("total_timesteps", 2048))
            logger.info(f"Starte Standard-Training für {total_timesteps_trained} Timesteps...")
            model.learn(total_timesteps=total_timesteps_trained, callback=callbacks, progress_bar=True)
        
        # --- Post-Processing ---
        final_model_save_path = os.path.join(paths["final_model_dir"], f"{paths['run_specific_identifier']}_final_{total_timesteps_trained}steps.zip")
        model.save(final_model_save_path)
        
        rl_utils.perform_post_training_tasks(
            rl_config_dict=rl_config, config_file_path_str=config_path_str, paths=paths,
            start_timestamp=start_timestamp, total_timesteps_trained=total_timesteps_trained,
            policy_used=model.policy.__class__.__name__,
            hero_id_for_readme=rl_config.get("agent_config", {}).get("agent_hero_id", "krieger"),
            algo_name_for_readme=rl_config.get("agent_config", {}).get("rl_algorithm", "PPO").upper(),
            chkpt_interval_for_readme=rl_config.get("run_config", {}).get("checkpoint_interval_sb3_model_save", 10000),
            project_root_path=PROJECT_ROOT_FROM_RL_TRAINING,
            user_config_manager_class=UserConfigManager
        )

    except Exception as e:
        logger.error(f"Ein schwerwiegender Fehler ist im Training aufgetreten: {e}", exc_info=True)
    finally:
        if train_vec_env: train_vec_env.close()
        if eval_vec_env: eval_vec_env.close()
        cli_output.set_execution_context(None)
        logger.info(f"RL Trainingsprozess für '{paths['run_specific_identifier']}' beendet.")

def train_agent_entry_point(config_path: str, run_profiling: bool = False, batch_mode: bool = False):
    """Einstiegspunkt für das Training, steuert das Profiling."""
    rl_conf = load_rl_config(config_path)
    if not rl_conf: sys.exit(1)
    
    if run_profiling:
        profiler = cProfile.Profile()
        profiler.enable()
        logger.info(f"Starte Training MIT PROFILING für: {config_path}")
        try:
            _actual_training_logic(config_path, rl_conf, is_batch_mode=batch_mode)
        finally:
            profiler.disable()
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            stats_dir = os.path.join(PROJECT_ROOT_FROM_RL_TRAINING, "logs", "profiling_data", f"profile_{ts}")
            os.makedirs(stats_dir, exist_ok=True)
            stats_file = os.path.join(stats_dir, "training_profile.prof")
            report_file = os.path.join(stats_dir, "training_report.txt")
            profiler.dump_stats(stats_file)
            with open(report_file, 'w') as f:
                pstats.Stats(profiler, stream=f).sort_stats('cumulative').print_stats(50)
            logger.info(f"Profiling-Daten gespeichert. Rohdaten: {stats_file}, Bericht: {report_file}")
    else:
        logger.info(f"Starte Training OHNE Profiling für: {config_path} (Batch-Modus: {batch_mode})")
        _actual_training_logic(config_path, rl_conf, is_batch_mode=batch_mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Agent Training Skript.")
    parser.add_argument("--config", type=str, required=True, help="Pfad zur RL-Setup-Konfigurationsdatei (.json5).")
    parser.add_argument("--profile", action="store_true", help="Aktiviere Profiling für diesen Lauf.")
    parser.add_argument("--batch_mode", action="store_true", help="Führe das Training im nicht-interaktiven Batch-Modus aus.")
    args = parser.parse_args()

    # Logging-Setup für direkten Skriptaufruf
    if _logging_setup_module and UserConfigManager:
        ucm_instance = UserConfigManager()
        _logging_setup_module.set_user_config_manager_for_logging(ucm_instance)
        _logging_setup_module.setup_logging(force_reconfigure=True)
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s][%(name)s]: %(message)s')
        logger.info("Minimales Fallback-Logging aktiviert.")

    train_agent_entry_point(args.config, args.profile, args.batch_mode)