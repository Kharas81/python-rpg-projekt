"""
RL-Training-Skript für das RPG-Projekt.
Dieses Skript trainiert einen RL-Agenten mit MaskablePPO und Action Masking.
"""

import os
import sys
import time
import argparse
import json5
import numpy as np
from typing import Dict, Any, List, Optional
import torch  # Wichtig für Aktivierungsfunktionen

# Füge das Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Importiere Gymnasium und Stable Baselines3
try:
    import gymnasium as gym
    from gymnasium.wrappers import TimeLimit
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
    from sb3_contrib.common.wrappers import ActionMasker
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
    from stable_baselines3.common.callbacks import BaseCallback
    LIBRARIES_AVAILABLE = True
except ImportError:
    LIBRARIES_AVAILABLE = False
    print("Fehler: RL-Bibliotheken nicht verfügbar. Bitte installieren Sie gymnasium, stable-baselines3 und sb3-contrib.")

from src.environment.rpg_env import RPGEnv
from src.config.config import get_config
from src.utils.logging_setup import get_logger


class TrainingMetricsCallback(BaseCallback):
    """
    Callback für die Verfolgung von Trainingsmetriken.
    Speichert Metriken wie Belohnungen, Episode-Längen, Erfolgsraten usw.
    """
    def __init__(self, verbose=0):
        super(TrainingMetricsCallback, self).__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        self.timesteps = []

    def _on_step(self) -> bool:
        """
        Wird bei jedem Umgebungsschritt aufgerufen.
        """
        for info in self.locals['infos']:
            if 'episode' in info:
                self.episode_rewards.append(info['episode']['r'])
                self.episode_lengths.append(info['episode']['l'])
                self.timesteps.append(self.num_timesteps)
        return True

    def plot_metrics(self, save_path: str) -> None:
        """
        Erstellt Plots für die gesammelten Metriken.
        """
        os.makedirs(save_path, exist_ok=True)

        # Belohnungen
        plt.figure(figsize=(10, 6))
        plt.plot(self.timesteps, self.episode_rewards)
        plt.xlabel('Timesteps')
        plt.ylabel('Episode Reward')
        plt.title('Belohnungen über die Zeit')
        plt.savefig(os.path.join(save_path, 'episode_rewards.png'))
        plt.close()

        # Episodenlängen
        plt.figure(figsize=(10, 6))
        plt.plot(self.timesteps, self.episode_lengths)
        plt.xlabel('Timesteps')
        plt.ylabel('Episodenlänge')
        plt.title('Episodenlängen über die Zeit')
        plt.savefig(os.path.join(save_path, 'episode_lengths.png'))
        plt.close()


def make_env(config_path: Optional[str], curriculum_level: int = 0, seed: int = 0) -> callable:
    """
    Erstellt eine Funktion, die eine neue Umgebung erzeugt.
    """
    def _init() -> gym.Env:
        env = RPGEnv(config_path)
        env.update_curriculum_level(curriculum_level)
        env.reset(seed=seed, options={'curriculum_level': curriculum_level})
        env = ActionMasker(env, lambda env: env.get_action_mask())
        env = TimeLimit(env, max_episode_steps=1000)
        return env
    return _init


def train_agent(config_path: Optional[str],
                n_envs: int = 4,
                total_timesteps: int = 100000,
                save_dir: str = 'src/ai/models') -> str:
    """
    Trainiert einen RL-Agenten mit MaskablePPO.
    """
    if not LIBRARIES_AVAILABLE:
        print("Fehler: RL-Bibliotheken nicht verfügbar!")
        return ""

    logger = get_logger('rl_training')
    logger.info("Starte RL-Training mit %d Umgebungen für %d Timesteps", n_envs, total_timesteps)

    # Konfiguration laden
    config = get_config(config_path)
    rl_settings = config.get('rl_settings', {})
    policy_kwargs = rl_settings.get('policy_kwargs', {})

    # Aktivierungsfunktion überprüfen
    if isinstance(policy_kwargs.get("activation_fn"), str):
        try:
            policy_kwargs["activation_fn"] = eval(policy_kwargs["activation_fn"])
        except Exception as e:
            raise ValueError(f"Ungültige Aktivierungsfunktion: {policy_kwargs['activation_fn']}. Fehler: {e}")

    # Umgebungen erstellen
    env_fns = [make_env(config_path, curriculum_level=0, seed=i) for i in range(n_envs)]
    vec_env = DummyVecEnv(env_fns)
    vec_env = VecMonitor(vec_env)

    # Speicherpfade
    os.makedirs(save_dir, exist_ok=True)
    checkpoint_callback = CheckpointCallback(save_freq=10000, save_path=save_dir, name_prefix="ppo_model")

    # Modell erstellen
    model = MaskablePPO(
        MaskableActorCriticPolicy,
        vec_env,
        verbose=1,
        policy_kwargs=policy_kwargs,
        tensorboard_log=os.path.join(save_dir, "logs"),
        **rl_settings.get('model_kwargs', {})
    )

    # Training
    try:
        logger.info("Training beginnt...")
        model.learn(total_timesteps=total_timesteps, callback=checkpoint_callback)
    except Exception as e:
        logger.error("Fehler während des Trainings: %s", str(e))
        raise

    # Modell speichern
    final_model_path = os.path.join(save_dir, "final_model")
    model.save(final_model_path)
    logger.info("Finales Modell gespeichert unter %s", final_model_path)

    return final_model_path


def main():
    """
    Hauptfunktion zum Ausführen des RL-Trainings.
    """
    parser = argparse.ArgumentParser(description="RL-Training für das RPG-Spiel")
    parser.add_argument('--config', type=str, default=None, help="Pfad zur Konfigurationsdatei")
    parser.add_argument('--timesteps', type=int, default=100000, help="Anzahl der Trainings-Timesteps")
    parser.add_argument('--n_envs', type=int, default=4, help="Anzahl paralleler Umgebungen")
    parser.add_argument('--save_dir', type=str, default="src/ai/models", help="Verzeichnis zum Speichern der Modelle")

    args = parser.parse_args()

    if not LIBRARIES_AVAILABLE:
        print("Fehler: RL-Bibliotheken sind nicht installiert!")
        return

    train_agent(
        config_path=args.config,
        n_envs=args.n_envs,
        total_timesteps=args.timesteps,
        save_dir=args.save_dir
    )


if __name__ == "__main__":
    main()