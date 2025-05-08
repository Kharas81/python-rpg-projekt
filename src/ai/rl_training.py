"""
RL-Trainingsmodul

Enthält Funktionen und Klassen für das Training von Reinforcement Learning Agenten
für das RPG-System.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import os
import time
import json
import json5
import gymnasium as gym
import numpy as np
import torch
from datetime import datetime
from pathlib import Path
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.logger import configure
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
from sb3_contrib.common.wrappers import ActionMasker
from sb3_contrib.ppo_mask import MaskablePPO

from src.environment.rpg_env import RPGEnvironment
from src.utils.logging_setup import get_logger

# Logger für dieses Modul
logger = get_logger(__name__)

# Standardpfade für Modelle und Logs
DEFAULT_MODEL_DIR = "src/ai/models"
DEFAULT_LOG_DIR = "logs/rl_training"


def get_action_mask(env: gym.Env) -> np.ndarray:
    """
    Hilfsfunktion zum Extrahieren der Aktionsmaske aus der Umgebung.
    
    Diese Funktion wird vom ActionMasker verwendet, um die gültigen Aktionen zu bestimmen.
    
    Args:
        env (gym.Env): Die Umgebung, aus der die Aktionsmaske extrahiert wird
        
    Returns:
        np.ndarray: Die Aktionsmaske
    """
    return env.get_wrapper_attr('action_mask')


class ActionMaskingWrapper(gym.Wrapper):
    """
    Ein Wrapper für die RPG-Umgebung, der die Aktionsmaske bereitstellt.
    
    Dieser Wrapper ist notwendig, um die Aktionsmaske für MaskablePPO bereitzustellen.
    """
    def __init__(self, env: RPGEnvironment):
        """
        Initialisiert den ActionMaskingWrapper.
        
        Args:
            env (RPGEnvironment): Die zu wrappende Umgebung
        """
        super().__init__(env)
        self._action_mask = None
    
    def reset(self, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Setzt die Umgebung zurück und speichert die initiale Aktionsmaske.
        
        Returns:
            Tuple[np.ndarray, Dict[str, Any]]: Observation und Info
        """
        obs, info = self.env.reset(**kwargs)
        self._action_mask = info.get('action_mask', np.ones(self.env.action_space.n, dtype=np.int8))
        return obs, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Führt einen Schritt in der Umgebung aus und aktualisiert die Aktionsmaske.
        
        Args:
            action (int): Die auszuführende Aktion
            
        Returns:
            Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]: Observation, Reward, Terminated, Truncated, Info
        """
        obs, reward, terminated, truncated, info = self.env.step(action)
        self._action_mask = info.get('action_mask', np.ones(self.env.action_space.n, dtype=np.int8))
        return obs, reward, terminated, truncated, info
    
    @property
    def action_mask(self) -> np.ndarray:
        """
        Gibt die aktuelle Aktionsmaske zurück.
        
        Returns:
            np.ndarray: Die Aktionsmaske
        """
        return self._action_mask


class TrainingProgressCallback(BaseCallback):
    """
    Ein Callback für das Training, der den Fortschritt und die Belohnungen trackt.
    
    Dieser Callback wird verwendet, um den Trainingsfortschritt zu überwachen
    und detaillierte Metriken zu sammeln.
    """
    def __init__(self, verbose: int = 0, log_interval: int = 1000):
        """
        Initialisiert den TrainingProgressCallback.
        
        Args:
            verbose (int): Verbosity-Level
            log_interval (int): Intervall für das Logging in Schritten
        """
        super().__init__(verbose)
        self.log_interval = log_interval
        self.episode_rewards = []
        self.episode_lengths = []
        self.total_episodes = 0
        self.total_timesteps = 0
        self.start_time = time.time()
    
    def _on_step(self) -> bool:
        """
        Wird nach jedem Schritt aufgerufen.
        
        Returns:
            bool: True, wenn das Training fortgesetzt werden soll, sonst False
        """
        # Für jede Umgebung in einem VecEnv prüfen, ob ein Episode abgeschlossen wurde
        for info in self.locals['infos']:
            # Wenn die Episode beendet ist, die Belohnung und Länge speichern
            if 'episode' in info:
                self.episode_rewards.append(info['episode']['r'])
                self.episode_lengths.append(info['episode']['l'])
                self.total_episodes += 1
        
        # Fortschritt loggen
        if self.n_calls % self.log_interval == 0:
            self.total_timesteps = self.n_calls
            
            # Durchschnittliche Belohnung und Episodenlänge berechnen
            if self.episode_rewards:
                avg_reward = sum(self.episode_rewards[-100:]) / min(100, len(self.episode_rewards))
                avg_length = sum(self.episode_lengths[-100:]) / min(100, len(self.episode_lengths))
            else:
                avg_reward = 0.0
                avg_length = 0
            
            # Fortschritt und Metriken loggen
            elapsed_time = time.time() - self.start_time
            steps_per_second = self.n_calls / max(1e-8, elapsed_time)
            
            logger.info(
                f"Fortschritt: {self.n_calls} Schritte ({steps_per_second:.2f} steps/s), "
                f"{self.total_episodes} Episoden, "
                f"Durchschn. Reward: {avg_reward:.2f}, "
                f"Durchschn. Länge: {avg_length:.1f}"
            )
        
        return True
    
    def _on_training_end(self) -> None:
        """
        Wird am Ende des Trainings aufgerufen.
        """
        # Gesamtstatistiken loggen
        elapsed_time = time.time() - self.start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logger.info(
            f"Training abgeschlossen: {self.n_calls} Schritte, {self.total_episodes} Episoden, "
            f"Zeit: {int(hours):02d}:{int(minutes):02d}:{seconds:.2f}"
        )


class CurriculumTrainer:
    """
    Ein Trainer, der Curriculum Learning für das RPG-System implementiert.
    
    Mit Curriculum Learning wird die Schwierigkeit der Trainingsaufgaben
    schrittweise erhöht, um ein effektiveres Training zu ermöglichen.
    """
    def __init__(self, config_path: str = None):
        """
        Initialisiert den CurriculumTrainer mit einer optionalen Konfiguration.
        
        Args:
            config_path (str, optional): Pfad zur Konfigurationsdatei
        """
        # Standardkonfiguration
        self.config = {
            'curriculum_levels': 5,
            'episodes_per_level': 1000,
            'evaluation_episodes': 20,
            'model_dir': DEFAULT_MODEL_DIR,
            'log_dir': DEFAULT_LOG_DIR,
            'checkpoint_interval': 50000,
            'learning_rate': 3e-4,
            'n_steps': 2048,
            'batch_size': 64,
            'n_epochs': 10,
            'gamma': 0.99,
            'gae_lambda': 0.95,
            'clip_range': 0.2,
            'ent_coef': 0.01,
            'use_cuda': True,
            'max_level': 10
        }
        
        # Laden der Konfiguration, falls angegeben
        if config_path is not None:
            self._load_config(config_path)
        
        # Geräteauswahl (CUDA oder CPU)
        if self.config['use_cuda'] and torch.cuda.is_available():
            self.device = 'cuda'
            logger.info(f"CUDA verfügbar, verwende GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.device = 'cpu'
            logger.info("Verwende CPU für das Training")
        
        # Verzeichnisse erstellen
        os.makedirs(self.config['model_dir'], exist_ok=True)
        os.makedirs(self.config['log_dir'], exist_ok=True)
        
        # Aktuelle Trainingsmetadaten
        self.current_level = 1
        self.model = None
        self.env = None
    
    def _load_config(self, config_path: str) -> None:
        """
        Lädt die Konfiguration aus einer Datei.
        
        Args:
            config_path (str): Pfad zur Konfigurationsdatei
        """
        try:
            if config_path.endswith('.json') or config_path.endswith('.json5'):
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json5.load(f)
            elif config_path.endswith('.yml') or config_path.endswith('.yaml'):
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
            else:
                logger.warning(f"Unbekanntes Dateiformat für Konfiguration: {config_path}")
                return
            
            # Konfiguration aktualisieren
            self.config.update(loaded_config)
            logger.info(f"Konfiguration aus {config_path} geladen")
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konfiguration aus {config_path}: {e}")
    
    def _create_environment(self, level: int) -> gym.Env:
        """
        Erstellt die Trainingsumgebung für das angegebene Level.
        
        Args:
            level (int): Das Curriculum-Level
            
        Returns:
            gym.Env: Die erstellte Umgebung
        """
        # Umgebungskonfiguration für das aktuelle Level
        env_config = {
            'curriculum_level': level,
            'reward_config': {
                'weight_damage': 1.0 * (1 + 0.1 * level),  # Mehr Belohnung für Schaden auf höheren Levels
                'weight_healing': 1.2 * (1 + 0.1 * level),  # Mehr Belohnung für Heilung auf höheren Levels
                'weight_kill': 5.0,
                'weight_death': -10.0,
                'weight_victory': 20.0,
                'weight_defeat': -15.0,
            },
            'max_steps': 200 + 50 * level  # Längere Episoden auf höheren Levels
        }
        
        # RPG-Umgebung erstellen
        env = RPGEnvironment(config=env_config)
        
        # Mit ActionMasker wrappen
        env = ActionMaskingWrapper(env)
        
        return env
    
    def _create_model(self, env: gym.Env) -> MaskablePPO:
        """
        Erstellt das Trainingsmodell für die angegebene Umgebung.
        
        Args:
            env (gym.Env): Die Trainingsumgebung
            
        Returns:
            MaskablePPO: Das erstellte Modell
        """
        # Logger für die Trainingsmetriken konfigurieren
        log_path = os.path.join(self.config['log_dir'], f"level_{self.current_level}")
        os.makedirs(log_path, exist_ok=True)
        logger_sb3 = configure(log_path, ["stdout", "csv", "tensorboard"])
        
        # Modellkonfiguration
        model = MaskablePPO(
            MaskableActorCriticPolicy,
            env,
            learning_rate=self.config['learning_rate'],
            n_steps=self.config['n_steps'],
            batch_size=self.config['batch_size'],
            n_epochs=self.config['n_epochs'],
            gamma=self.config['gamma'],
            gae_lambda=self.config['gae_lambda'],
            clip_range=self.config['clip_range'],
            ent_coef=self.config['ent_coef'],
            verbose=1,
            device=self.device,
            tensorboard_log=log_path
        )
        
        return model
    
    def _load_latest_checkpoint(self, level: int) -> Optional[MaskablePPO]:
        """
        Versucht, den neuesten Checkpoint für das angegebene Level zu laden.
        
        Args:
            level (int): Das Curriculum-Level
            
        Returns:
            Optional[MaskablePPO]: Das geladene Modell oder None, wenn kein Checkpoint gefunden wurde
        """
        model_dir = os.path.join(self.config['model_dir'], f"level_{level}")
        
        if not os.path.exists(model_dir):
            return None
        
        # Alle ZIP-Dateien im Verzeichnis finden
        checkpoint_files = [f for f in os.listdir(model_dir) if f.endswith('.zip')]
        
        if not checkpoint_files:
            return None
        
        # Nach Zeitstempel sortieren (neueste zuerst)
        checkpoint_files.sort(reverse=True)
        latest_checkpoint = os.path.join(model_dir, checkpoint_files[0])
        
        try:
            logger.info(f"Lade Checkpoint: {latest_checkpoint}")
            model = MaskablePPO.load(latest_checkpoint)
            return model
        except Exception as e:
            logger.error(f"Fehler beim Laden des Checkpoints: {e}")
            return None
    
    def train_curriculum(self) -> None:
        """
        Führt das Curriculum-Training durch.
        
        Dies umfasst das schrittweise Training auf mehreren Schwierigkeitsstufen.
        """
        max_level = self.config.get('max_level', 5)
        episodes_per_level = self.config.get('episodes_per_level', 1000)
        
        # Mit Level 1 beginnen oder vorhandenes Training fortsetzen
        start_level = self.current_level
        
        for level in range(start_level, max_level + 1):
            self.current_level = level
            logger.info(f"=== Starte Training für Level {level} ===")
            
            # Umgebung für dieses Level erstellen
            env = self._create_environment(level)
            self.env = env
            
            # Prüfen, ob es einen Checkpoint für dieses Level gibt
            model = self._load_latest_checkpoint(level)
            
            if model is None:
                # Neues Modell erstellen oder das vorherige wiederverwenden
                if level > start_level and self.model is not None:
                    # Modell von vorherigem Level wiederverwenden
                    logger.info(f"Verwende Modell von Level {level-1}")
                    model = self.model
                    model.set_env(env)  # Neue Umgebung setzen
                else:
                    # Neues Modell erstellen
                    logger.info("Erstelle neues Modell")
                    model = self._create_model(env)
            
            self.model = model
            
            # Callbacks erstellen
            callbacks = []
            
            # Checkpoint-Callback
            checkpoint_dir = os.path.join(self.config['model_dir'], f"level_{level}")
            os.makedirs(checkpoint_dir, exist_ok=True)
            
            checkpoint_callback = CheckpointCallback(
                save_freq=self.config['checkpoint_interval'],
                save_path=checkpoint_dir,
                name_prefix=f"ppo_rpg_level{level}",
                save_replay_buffer=True,
                save_vecnormalize=True
            )
            callbacks.append(checkpoint_callback)
            
            # Fortschritts-Callback
            progress_callback = TrainingProgressCallback(log_interval=1000)
            callbacks.append(progress_callback)
            
            # Training für dieses Level
            total_timesteps = episodes_per_level * 200  # Ungefähre Anzahl von Schritten
            logger.info(f"Training für Level {level} mit {total_timesteps} Schritten")
            
            try:
                model.learn(
                    total_timesteps=total_timesteps,
                    callback=callbacks,
                    reset_num_timesteps=True  # Zurücksetzen der Schritte für jedes Level
                )
                
                # Modell speichern
                final_model_path = os.path.join(checkpoint_dir, f"final_model_level{level}")
                model.save(final_model_path)
                logger.info(f"Modell für Level {level} gespeichert: {final_model_path}")
                
                # Evaluieren
                self._evaluate_model(model, level)
                
            except Exception as e:
                logger.error(f"Fehler während des Trainings für Level {level}: {e}")
                # Versuchen, das Modell trotzdem zu speichern
                try:
                    emergency_path = os.path.join(checkpoint_dir, f"emergency_save_level{level}")
                    model.save(emergency_path)
                    logger.info(f"Notfall-Speicherung des Modells: {emergency_path}")
                except Exception as save_err:
                    logger.error(f"Konnte das Modell nicht speichern: {save_err}")
            
            # Umgebung schließen
            env.close()
        
        logger.info(f"Curriculum-Training abgeschlossen für alle {max_level} Level!")
    
    def _evaluate_model(self, model: MaskablePPO, level: int) -> None:
        """
        Evaluiert das trainierte Modell.
        
        Args:
            model (MaskablePPO): Das zu evaluierende Modell
            level (int): Das aktuelle Level
        """
        evaluation_episodes = self.config.get('evaluation_episodes', 20)
        
        logger.info(f"Evaluiere Modell für Level {level} über {evaluation_episodes} Episoden...")
        
        # Separate Umgebung für die Evaluierung erstellen
        eval_env = self._create_environment(level)
        
        # Metriken für die Evaluierung
        rewards = []
        episode_lengths = []
        victories = 0
        
        for episode in range(evaluation_episodes):
            obs, _ = eval_env.reset()
            done = False
            episode_reward = 0
            episode_length = 0
            
            while not done:
                action, _states = model.predict(obs, action_masks=eval_env.action_mask)
                obs, reward, terminated, truncated, info = eval_env.step(action)
                
                episode_reward += reward
                episode_length += 1
                done = terminated or truncated
                
                # Sieg/Niederlage tracken
                if done and 'state_info' in info:
                    if info['state_info'].get('winner') == 'players':
                        victories += 1
            
            rewards.append(episode_reward)
            episode_lengths.append(episode_length)
        
        # Ergebnisse berechnen
        avg_reward = sum(rewards) / len(rewards)
        avg_length = sum(episode_lengths) / len(episode_lengths)
        victory_rate = victories / evaluation_episodes
        
        # Ergebnisse loggen
        logger.info(f"Evaluierungsergebnisse für Level {level}:")
        logger.info(f"Durchschn. Reward: {avg_reward:.2f}")
        logger.info(f"Durchschn. Episodenlänge: {avg_length:.1f}")
        logger.info(f"Siegesrate: {victory_rate:.2%} ({victories}/{evaluation_episodes})")
        
        # Ergebnisse speichern
        results = {
            'level': level,
            'episodes': evaluation_episodes,
            'avg_reward': float(avg_reward),
            'avg_length': float(avg_length),
            'victory_rate': float(victory_rate),
            'victories': victories,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        results_dir = os.path.join(self.config['log_dir'], 'evaluation_results')
        os.makedirs(results_dir, exist_ok=True)
        
        results_file = os.path.join(results_dir, f"eval_level{level}_{int(time.time())}.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        eval_env.close()


def main(config_path: Optional[str] = None):
    """
    Hauptfunktion für das RL-Training.
    
    Args:
        config_path (Optional[str]): Pfad zur Konfigurationsdatei
    """
    start_time = time.time()
    
    logger.info("=== RL-Training gestartet ===")
    
    # Trainer mit Konfiguration erstellen
    trainer = CurriculumTrainer(config_path)
    
    try:
        # Training starten
        trainer.train_curriculum()
        
    except KeyboardInterrupt:
        logger.info("Training durch Benutzer unterbrochen.")
    except Exception as e:
        logger.error(f"Fehler während des Trainings: {e}", exc_info=True)
    finally:
        # Aufräumen
        if trainer.env is not None:
            trainer.env.close()
    
    # Trainingszeit berechnen
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    logger.info(f"=== RL-Training beendet ===")
    logger.info(f"Gesamtzeit: {int(hours):02d}:{int(minutes):02d}:{seconds:.2f}")


if __name__ == "__main__":
    import argparse
    
    # Kommandozeilenargumente parsen
    parser = argparse.ArgumentParser(description="RL-Training für das RPG-System")
    parser.add_argument("--config", type=str, default=None, help="Pfad zur Konfigurationsdatei (JSON5 oder YAML)")
    
    args = parser.parse_args()
    
    main(args.config)