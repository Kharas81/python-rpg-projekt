"""
Evaluate RL Agent

Skript zur Evaluierung trainierter RL-Agenten für das RPG-System.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
import os
import time
import json
import json5
import gymnasium as gym
import numpy as np
from datetime import datetime
from pathlib import Path
from sb3_contrib.ppo_mask import MaskablePPO

from src.environment.rpg_env import RPGEnvironment
from src.environment.action_manager import ActionMaskingWrapper
from src.utils.logging_setup import get_logger

# Logger für dieses Modul
logger = get_logger(__name__)

# Standardpfade
DEFAULT_MODEL_DIR = "src/ai/models"
DEFAULT_REPORT_DIR = "reports/rl_evaluation"


class AgentEvaluator:
    """
    Evaluiert trainierte RL-Agenten.
    
    Diese Klasse bietet Funktionen zur detaillierten Evaluierung trainierter
    RL-Agenten und zur Generierung von Berichten über deren Leistung.
    """
    def __init__(self, config_path: str = None):
        """
        Initialisiert den AgentEvaluator mit einer optionalen Konfiguration.
        
        Args:
            config_path (str, optional): Pfad zur Konfigurationsdatei
        """
        # Standardkonfiguration
        self.config = {
            'model_dir': DEFAULT_MODEL_DIR,
            'report_dir': DEFAULT_REPORT_DIR,
            'evaluation_episodes': 50,
            'verbose': 1,
            'render_mode': 'ansi'
        }
        
        # Laden der Konfiguration, falls angegeben
        if config_path is not None:
            self._load_config(config_path)
        
        # Verzeichnisse erstellen
        os.makedirs(self.config['report_dir'], exist_ok=True)
    
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
        Erstellt eine Evaluierungsumgebung für das angegebene Level.
        
        Args:
            level (int): Das Curriculum-Level
            
        Returns:
            gym.Env: Die erstellte Umgebung
        """
        # Umgebungskonfiguration für das aktuelle Level
        env_config = {
            'curriculum_level': level,
            'render_mode': self.config['render_mode']
        }
        
        # RPG-Umgebung erstellen
        env = RPGEnvironment(config=env_config)
        
        # Mit ActionMasker wrappen
        env = ActionMaskingWrapper(env)
        
        return env
    
    def load_model(self, model_path: str) -> Optional[MaskablePPO]:
        """
        Lädt ein trainiertes Modell.
        
        Args:
            model_path (str): Pfad zum Modell
            
        Returns:
            Optional[MaskablePPO]: Das geladene Modell oder None bei Fehler
        """
        try:
            logger.info(f"Lade Modell: {model_path}")
            model = MaskablePPO.load(model_path)
            return model
        except Exception as e:
            logger.error(f"Fehler beim Laden des Modells {model_path}: {e}")
            return None
    
    def evaluate_agent(self, model_path: str, level: int = None) -> Dict[str, Any]:
        """
        Evaluiert einen trainierten Agenten.
        
        Args:
            model_path (str): Pfad zum Modell
            level (int, optional): Das zu verwendende Level. Falls None, wird das Level aus dem Modellpfad abgeleitet
            
        Returns:
            Dict[str, Any]: Die Evaluierungsergebnisse
        """
        # Level aus dem Modellpfad ableiten, falls nicht angegeben
        if level is None:
            # Versuche, das Level aus dem Pfad zu extrahieren (z.B. "level_5/model.zip")
            path_parts = Path(model_path).parts
            for part in path_parts:
                if part.startswith("level_"):
                    try:
                        level = int(part.split("_")[1])
                        break
                    except:
                        pass
            
            # Fallback
            if level is None:
                level = 1
                logger.warning(f"Konnte kein Level aus dem Modellpfad ableiten, verwende Level {level}")
        
        # Modell laden
        model = self.load_model(model_path)
        if model is None:
            return {
                'success': False,
                'error': 'Modell konnte nicht geladen werden',
                'path': model_path
            }
        
        # Umgebung erstellen
        env = self._create_environment(level)
        
        # Evaluierungsparameter
        episodes = self.config['evaluation_episodes']
        verbose = self.config['verbose']
        
        logger.info(f"Evaluiere Modell über {episodes} Episoden auf Level {level}...")
        
        # Metriken für die Evaluierung
        rewards = []
        episode_lengths = []
        victories = 0
        defeats = 0
        draws = 0
        
        # Detaillierte Metriken
        total_damage_dealt = 0
        total_healing_done = 0
        total_kills = 0
        player_deaths = 0
        actions_taken = {
            'attacks': 0,
            'heals': 0,
            'buffs': 0,
            'debuffs': 0,
            'other': 0
        }
        
        # Evaluierungsschleife
        for episode in range(episodes):
            if verbose >= 1:
                logger.info(f"Episode {episode+1}/{episodes}")
            
            obs, info = env.reset()
            done = False
            episode_reward = 0
            episode_length = 0
            
            while not done:
                # Aktion auswählen
                action, _states = model.predict(obs, action_masks=env.action_mask)
                
                # Aktion ausführen
                obs, reward, terminated, truncated, info = env.step(action)
                
                # Statistiken sammeln
                episode_reward += reward
                episode_length += 1
                done = terminated or truncated
                
                # Detaillierte Statistiken sammeln
                if 'action_result' in info:
                    total_damage_dealt += info['action_result'].get('damage_dealt', 0)
                    total_healing_done += info['action_result'].get('healing_done', 0)
                    total_kills += info['action_result'].get('kills', 0)
                
                # Aktionstyp zählen (vereinfacht)
                if 'action_type' in info:
                    action_type = info.get('action_type', 'other')
                    if action_type in actions_taken:
                        actions_taken[action_type] += 1
                    else:
                        actions_taken['other'] += 1
                
                # Ausgabe für detaillierte Verfolgung
                if verbose >= 2:
                    env.render()
                    if 'action_result' in info:
                        logger.debug(f"Schaden: {info['action_result'].get('damage_dealt', 0)}, "
                                    f"Heilung: {info['action_result'].get('healing_done', 0)}, "
                                    f"Kills: {info['action_result'].get('kills', 0)}")
                    time.sleep(0.5)  # Kurze Pause für bessere Lesbarkeit
                
                # Spielergebnisse tracken
                if done and 'state_info' in info:
                    if info['state_info'].get('winner') == 'players':
                        victories += 1
                        if verbose >= 1:
                            logger.info(f"Episode {episode+1}: Sieg!")
                    elif info['state_info'].get('winner') == 'opponents':
                        defeats += 1
                        if verbose >= 1:
                            logger.info(f"Episode {episode+1}: Niederlage!")
                    else:
                        draws += 1
                        if verbose >= 1:
                            logger.info(f"Episode {episode+1}: Unentschieden!")
            
            rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            
            if verbose >= 1:
                logger.info(f"Episode {episode+1}: Reward={episode_reward:.2f}, Länge={episode_length}")
        
        # Ergebnisse berechnen
        avg_reward = sum(rewards) / len(rewards)
        avg_length = sum(episode_lengths) / len(episode_lengths)
        victory_rate = victories / episodes
        defeat_rate = defeats / episodes
        draw_rate = draws / episodes
        
        # Durchschnittswerte pro Episode berechnen
        avg_damage_per_episode = total_damage_dealt / episodes
        avg_healing_per_episode = total_healing_done / episodes
        avg_kills_per_episode = total_kills / episodes
        
        # Ergebnisse loggen
        logger.info(f"\n=== Evaluierungsergebnisse für Level {level} ===")
        logger.info(f"Durchschn. Reward: {avg_reward:.2f}")
        logger.info(f"Durchschn. Episodenlänge: {avg_length:.1f}")
        logger.info(f"Siegesrate: {victory_rate:.2%} ({victories}/{episodes})")
        logger.info(f"Niederlagenrate: {defeat_rate:.2%} ({defeats}/{episodes})")
        if draws > 0:
            logger.info(f"Unentschieden: {draw_rate:.2%} ({draws}/{episodes})")
        
        logger.info(f"\n=== Kampfstatistiken ===")
        logger.info(f"Durchschn. Schaden pro Episode: {avg_damage_per_episode:.1f}")
        logger.info(f"Durchschn. Heilung pro Episode: {avg_healing_per_episode:.1f}")
        logger.info(f"Durchschn. Kills pro Episode: {avg_kills_per_episode:.1f}")
        
        # Umgebung schließen
        env.close()
        
        # Ergebnisse als Dictionary zusammenfassen
        results = {
            'success': True,
            'model_path': model_path,
            'level': level,
            'episodes': episodes,
            'statistics': {
                'rewards': {
                    'min': float(min(rewards)),
                    'max': float(max(rewards)),
                    'avg': float(avg_reward),
                    'total': float(sum(rewards))
                },
                'episode_lengths': {
                    'min': int(min(episode_lengths)),
                    'max': int(max(episode_lengths)),
                    'avg': float(avg_length)
                },
                'outcomes': {
                    'victories': victories,
                    'defeats': defeats,
                    'draws': draws,
                    'victory_rate': float(victory_rate),
                    'defeat_rate': float(defeat_rate),
                    'draw_rate': float(draw_rate)
                },
                'combat': {
                    'total_damage': float(total_damage_dealt),
                    'total_healing': float(total_healing_done),
                    'total_kills': int(total_kills),
                    'avg_damage_per_episode': float(avg_damage_per_episode),
                    'avg_healing_per_episode': float(avg_healing_per_episode),
                    'avg_kills_per_episode': float(avg_kills_per_episode)
                },
                'actions': actions_taken
            },
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return results
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Speichert die Evaluierungsergebnisse in einer Datei.
        
        Args:
            results (Dict[str, Any]): Die zu speichernden Ergebnisse
            filename (Optional[str]): Der Dateiname (ohne Pfad). Falls None, wird ein Name generiert
            
        Returns:
            str: Der vollständige Pfad zur gespeicherten Datei
        """
        if filename is None:
            # Dateiname aus Modellpfad und Zeitstempel generieren
            model_name = results.get('model_path', '').split('/')[-1].split('.')[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            level = results.get('level', 0)
            filename = f"eval_{model_name}_level{level}_{timestamp}.json"
        
        # Vollständigen Pfad erstellen
        file_path = os.path.join(self.config['report_dir'], filename)
        
        # Ergebnisse speichern
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Evaluierungsergebnisse gespeichert: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Ergebnisse: {e}")
            return ""


def main(model_path: str, level: Optional[int] = None, config_path: Optional[str] = None):
    """
    Hauptfunktion für die Evaluierung.
    
    Args:
        model_path (str): Pfad zum zu evaluierenden Modell
        level (Optional[int]): Das zu verwendende Level. Falls None, wird das Level aus dem Modellpfad abgeleitet
        config_path (Optional[str]): Pfad zur Konfigurationsdatei
    """
    logger.info("=== Agent-Evaluierung gestartet ===")
    
    # Evaluator erstellen
    evaluator = AgentEvaluator(config_path)
    
    # Modell evaluieren
    results = evaluator.evaluate_agent(model_path, level)
    
    # Ergebnisse speichern
    if results['success']:
        evaluator.save_results(results)
    
    logger.info("=== Agent-Evaluierung beendet ===")


if __name__ == "__main__":
    import argparse
    
    # Kommandozeilenargumente parsen
    parser = argparse.ArgumentParser(description="Evaluierung von RL-Agenten für das RPG-System")
    parser.add_argument("model_path", type=str, help="Pfad zum zu evaluierenden Modell")
    parser.add_argument("--level", type=int, default=None, help="Das zu verwendende Level")
    parser.add_argument("--config", type=str, default=None, help="Pfad zur Konfigurationsdatei")
    
    args = parser.parse_args()
    
    main(args.model_path, args.level, args.config)