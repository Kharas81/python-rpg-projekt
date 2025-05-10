# src/ai/evaluate_agent.py
"""
Skript zur Evaluierung eines trainierten Reinforcement Learning Agenten.
Nimmt eine RL-Setup-Konfigurationsdatei als Eingabe, die auch den Pfad
zum zu ladenden Modell enthält.
"""
import argparse
import logging
import json5 
import os
import sys
import numpy as np 
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
    from stable_baselines3 import PPO # Beispiel
    from stable_baselines3.common.evaluation import evaluate_policy 
except ImportError as e:
    print(f"Fehler bei initialen Imports in evaluate_agent.py: {e}.")
    PPO = None # Dummy
    evaluate_policy = None # Dummy

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

def evaluate_agent_performance(config_path: str):
    logger.info(f"Starte RL-Evaluierungsprozess mit Konfiguration: {config_path}")
    
    rl_config = load_rl_config(config_path)
    if not rl_config: return

    setup_type = rl_config.get("setup_type")
    if setup_type != "evaluation": # Sicherstellen, dass es eine Eval-Konfig ist
        logger.error(f"Falscher setup_type ('{setup_type}'). Erwartet 'evaluation'.")
        return

    description = rl_config.get("description", "Keine Beschreibung für Evaluierung")
    logger.info(f"Evaluierungsbeschreibung: {description}")

    agent_conf = rl_config.get("agent_config", {})
    env_conf_from_file = rl_config.get("environment_config", {})
    run_conf = rl_config.get("run_config", {})

    hero_id = agent_conf.get("agent_hero_id", "krieger")
    rl_algorithm_name = agent_conf.get("rl_algorithm", "PPO").upper()
    model_load_path = agent_conf.get("model_load_path")

    if not model_load_path or not os.path.exists(model_load_path):
        logger.error(f"Pfad zum trainierten Modell ('model_load_path': {model_load_path}) nicht gefunden oder nicht angegeben.")
        return

    opponent_setup_for_env = env_conf_from_file.get("opponent_setup", 
                                                     {"num_opponents": 1, "level_pool": "1-2", "ids": ["goblin_lv1"]})
    max_episode_steps = env_conf_from_file.get("max_episode_steps", 100)
    reward_weights_for_env = env_conf_from_file.get("reward_weights")

    num_evaluation_episodes = run_conf.get("num_evaluation_episodes", 10)
    deterministic_actions = run_conf.get("deterministic_actions", True) 

    logger.info(f"Lade Modell: {model_load_path} (Algorithmus: {rl_algorithm_name})")
    logger.info(f"Evaluiere für {num_evaluation_episodes} Episoden.")
    logger.info(f"Deterministische Aktionen: {deterministic_actions}")

    env = None
    try:
        env = RPGEnv(
            hero_id=hero_id,
            opponent_setup_config=opponent_setup_for_env,
            max_episode_steps=max_episode_steps,
            reward_config=reward_weights_for_env,
            render_mode='human' # Optional: 'human' für Anzeige während Eval, sonst None
        )
        logger.info("RL-Umgebung für Evaluierung erfolgreich erstellt.")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der RL-Umgebung für Evaluierung: {e}", exc_info=True)
        return

    model = None
    try:
        if PPO is None or evaluate_policy is None: # Prüfen ob SB3 geladen wurde
            logger.error("Stable Baselines3 konnte nicht importiert werden. Evaluierung abgebrochen.")
            if env and hasattr(env, 'close'): env.close()
            return

        if rl_algorithm_name == "PPO":
            model = PPO.load(model_load_path, env=env)
        else:
            logger.error(f"Unbekannter oder nicht unterstützter RL-Algorithmus zum Laden: {rl_algorithm_name}")
            if hasattr(env, 'close'): env.close()
            return
        
        logger.info(f"Modell '{model_load_path}' erfolgreich geladen.")

        # SB3 evaluate_policy verwenden
        logger.info(f"Starte Evaluierung mit SB3 evaluate_policy für {num_evaluation_episodes} Episoden...")
        episode_rewards, episode_lengths = evaluate_policy(
            model, 
            env, 
            n_eval_episodes=num_evaluation_episodes, 
            deterministic=deterministic_actions, 
            render=False, # 'human' Rendering wird von env.render() gesteuert, falls dort aktiviert
            return_episode_rewards=True # Wichtig, um Rewards und Längen zu bekommen
        )
        
        mean_reward = np.mean(episode_rewards) if episode_rewards else 0
        std_reward = np.std(episode_rewards) if episode_rewards else 0
        mean_length = np.mean(episode_lengths) if episode_lengths else 0

        logger.info("\n--- Evaluierungsergebnisse (SB3 evaluate_policy) ---")
        logger.info(f"Anzahl Episoden: {num_evaluation_episodes}")
        logger.info(f"Mittlerer Reward: {mean_reward:.2f} +/- {std_reward:.2f}")
        logger.info(f"Mittlere Episodenlänge: {mean_length:.2f}")

        # TODO: Zusätzliche Metriken wie Siegesrate manuell erfassen, falls nötig,
        # indem man eine eigene Schleife wie im rl_training Testblock implementiert
        # und den Env-Zustand (info-Dict) am Ende jeder Episode prüft.

    except Exception as e:
        logger.error(f"Ein Fehler ist während der RL-Evaluierung aufgetreten: {e}", exc_info=True)
    finally:
        if env and hasattr(env, 'close'):
            env.close()

    logger.info("RL-Evaluierungsprozess beendet.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RL Agent Evaluation Skript.")
    parser.add_argument("--config",type=str,required=True,help="Pfad zur RL-Setup-Konfigurationsdatei (.json5) für die Evaluierung.")
    args = parser.parse_args()
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
        logger.info("Fallback-Logging für evaluate_agent.py aktiviert.")
    evaluate_agent_performance(args.config)