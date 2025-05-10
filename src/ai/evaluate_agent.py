# src/ai/evaluate_agent.py
"""
Skript zur Evaluierung eines trainierten Reinforcement Learning Agenten.
Nimmt eine RL-Setup-Konfigurationsdatei als Eingabe, die auch den Pfad
zum zu ladenden Modell enthält.
"""
import argparse
import logging
import json5 # Zum Laden der RL-Konfigurationsdatei
import os
import sys
import numpy as np # Für Metriken

# PYTHONPATH anpassen für direktes Ausführen
if __name__ == '__main__':
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)

try:
    from src.utils import logging_setup
    from src.environment.rpg_env import RPGEnv
    # from stable_baselines3 import PPO # Oder welcher Agent auch immer verwendet wurde
    # from stable_baselines3.common.evaluation import evaluate_policy # Nützlich für SB3
except ImportError as e:
    print(f"Fehler bei initialen Imports in evaluate_agent.py: {e}.")
    sys.exit(1)

logger = logging.getLogger(__name__)

def load_rl_config(config_path: str) -> Optional[Dict[str, Any]]:
    # Identisch zu rl_training.py, könnte ausgelagert werden
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

def evaluate_agent_performance(config_path: str):
    """
    Hauptfunktion zur Evaluierung eines trainierten RL-Agenten.
    """
    logger.info(f"Starte RL-Evaluierungsprozess mit Konfiguration: {config_path}")
    
    rl_config = load_rl_config(config_path)
    if not rl_config:
        return

    setup_type = rl_config.get("setup_type")
    if setup_type != "evaluation":
        logger.error(f"Falscher setup_type ('{setup_type}') in Konfigurationsdatei. Erwartet 'evaluation'.")
        return

    description = rl_config.get("description", "Keine Beschreibung für Evaluierung")
    logger.info(f"Evaluierungsbeschreibung: {description}")

    agent_config = rl_config.get("agent_config", {})
    env_config_from_file = rl_config.get("environment_config", {})
    run_config = rl_config.get("run_config", {})

    hero_id = agent_config.get("agent_hero_id", "krieger")
    rl_algorithm = agent_config.get("rl_algorithm", "PPO").upper()
    model_load_path = agent_config.get("model_load_path")

    if not model_load_path or not os.path.exists(model_load_path):
        logger.error(f"Pfad zum trainierten Modell ('model_load_path': {model_load_path}) nicht gefunden oder nicht angegeben.")
        return

    opponent_setup = env_config_from_file.get("opponent_setup", {"num_opponents": 1, "level_pool": "1-2"})
    num_opps_for_env = opponent_setup.get("num_opponents", 1)
    temp_opponent_ids_for_env = ["goblin_lv1"] * num_opps_for_env # Vereinfachung, s. rl_training.py

    max_episode_steps = env_config_from_file.get("max_episode_steps", 100) # Kann für Eval anders sein
    # reward_weights = env_config_from_file.get("reward_weights")

    num_evaluation_episodes = run_config.get("num_evaluation_episodes", 10)
    deterministic_actions = run_config.get("deterministic_actions", True) # Im Eval oft deterministisch

    logger.info(f"Lade Modell: {model_load_path} (Algorithmus: {rl_algorithm})")
    logger.info(f"Evaluiere für {num_evaluation_episodes} Episoden.")
    logger.info(f"Deterministische Aktionen: {deterministic_actions}")

    # --- Umgebung erstellen ---
    try:
        env = RPGEnv(
            hero_id=hero_id,
            opponent_ids=temp_opponent_ids_for_env, # TODO: RPGEnv anpassen für opponent_setup
            max_episode_steps=max_episode_steps,
            # reward_config=reward_weights
        )
        logger.info("RL-Umgebung für Evaluierung erfolgreich erstellt.")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der RL-Umgebung für Evaluierung: {e}", exc_info=True)
        return

    # --- Agent laden und evaluieren (Platzhalter) ---
    logger.warning("RL-Agenten-Laden und Evaluierungslogik sind noch nicht implementiert.")

    # Beispielhafte (auskommentierte) Logik für Stable Baselines3:
    # try:
    #     if rl_algorithm == "PPO":
    #         model = PPO.load(model_load_path, env=env) # Env übergeben, damit Spaces etc. passen
    #     # elif rl_algorithm == "DQN":
    #     #     model = DQN.load(model_load_path, env=env)
    #     else:
    #         logger.error(f"Unbekannter oder nicht unterstützter RL-Algorithmus zum Laden: {rl_algorithm}")
    #         return
    #     
    #     logger.info(f"Modell '{model_load_path}' erfolgreich geladen.")
    #
    #     # Option 1: Manuelle Schleife für mehr Kontrolle über Metriken
    #     episode_rewards = []
    #     episode_lengths = []
    #     num_wins = 0
    #
    #     for i in range(num_evaluation_episodes):
    #         obs, info = env.reset()
    #         terminated = False
    #         truncated = False
    #         current_episode_reward = 0
    #         current_episode_length = 0
    #         while not terminated and not truncated:
    #             action, _states = model.predict(obs, deterministic=deterministic_actions)
    #             obs, reward, terminated, truncated, info = env.step(action)
    #             current_episode_reward += reward
    #             current_episode_length += 1
    #         
    #         episode_rewards.append(current_episode_reward)
    #         episode_lengths.append(current_episode_length)
    #         # Siegbedingung prüfen (muss aus info oder Env-Zustand kommen)
    #         # z.B. if not any(o.is_defeated for o in env.state_manager.get_live_opponents()): num_wins += 1
    #         logger.info(f"Eval-Episode {i+1}/{num_evaluation_episodes} beendet. Reward: {current_episode_reward:.2f}, Länge: {current_episode_length}")
    #
    #     mean_reward = np.mean(episode_rewards) if episode_rewards else 0
    #     std_reward = np.std(episode_rewards) if episode_rewards else 0
    #     mean_length = np.mean(episode_lengths) if episode_lengths else 0
    #     # win_rate = (num_wins / num_evaluation_episodes) * 100 if num_evaluation_episodes > 0 else 0
    #
    #     logger.info("\n--- Evaluierungsergebnisse ---")
    #     logger.info(f"Anzahl Episoden: {num_evaluation_episodes}")
    #     logger.info(f"Mittlerer Reward: {mean_reward:.2f} +/- {std_reward:.2f}")
    #     logger.info(f"Mittlere Episodenlänge: {mean_length:.2f}")
    #     # logger.info(f"Siegesrate: {win_rate:.2f}%")
    #
    #     # Option 2: SB3 evaluate_policy (einfacher, aber weniger flexibel bei Metriken)
    #     # mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=num_evaluation_episodes, deterministic=deterministic_actions, render=False)
    #     # logger.info(f"SB3 evaluate_policy: Mean reward: {mean_reward:.2f} +/- {std_reward:.2f} over {num_evaluation_episodes} episodes")
    #
    # except Exception as e:
    #     logger.error(f"Ein Fehler ist während der RL-Evaluierung aufgetreten: {e}", exc_info=True)
    # finally:
    #     if 'env' in locals() and hasattr(env, 'close'):
    #         env.close()

    logger.info("RL-Evaluierungsprozess (Platzhalter) beendet.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Agent Evaluation Skript.")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Pfad zur RL-Setup-Konfigurationsdatei (.json5) für die Evaluierung."
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    evaluate_agent_performance(args.config)