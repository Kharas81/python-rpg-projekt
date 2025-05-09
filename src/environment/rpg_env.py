"""
Implementierung einer Gymnasium-kompatiblen Umgebung für das RPG-Spiel.
Diese Umgebung kann für RL-Training mit Bibliotheken wie Stable Baselines3 verwendet werden.
"""
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
import gymnasium as gym
from gymnasium.spaces import Box, Discrete

from src.environment.env_state import EnvState  # Hilfsklasse für den Zustand
from src.environment.observation_manager import ObservationManager
from src.environment.action_manager import ActionManager
from src.environment.reward_calculator import RewardCalculator
from src.config.config import get_config
from src.utils.logging_setup import get_logger


class RPGEnv(gym.Env):
    """
    Gymnasium-kompatible Umgebung für das RPG-Spiel.
    Implementiert die standard Gym-Schnittstelle mit zusätzlichen Funktionen für Action Masking.
    """
    
    metadata = {"render.modes": ["human"]}

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialisiert die RPG-Umgebung.
        
        Args:
            config_path: Optionaler Pfad zu einer Konfigurationsdatei.
        """
        super(RPGEnv, self).__init__()
        
        # Konfiguration laden
        self.config = get_config(config_path)
        self.logger = get_logger('rpg_env')
        
        # Manager für Umgebungskomponenten
        self.observation_manager = ObservationManager()
        self.action_manager = ActionManager()
        self.reward_calculator = RewardCalculator()
        
        # Umgebungszustand
        self.state = EnvState()
        
        # Gym-Umgebungseigenschaften
        obs_space = self.observation_manager.get_observation_space()
        self.observation_space = Box(
            low=obs_space["low"],
            high=obs_space["high"],
            shape=obs_space["shape"],
            dtype=np.float32
        )
        self.action_space = Discrete(self.action_manager.action_space_size)
        
        # Action Masking für MaskablePPO
        self.action_mask = None
        
        # Training-Konfiguration
        rl_settings = self.config.get('rl_settings', {})
        self.max_episode_steps = rl_settings.get('max_episode_steps', 100)
        self.current_step = 0
        
        # Curriculum Learning
        self.curriculum_level = 0
        self.curriculum_settings = rl_settings.get('curriculum', {})
        
        self.logger.info("RPGEnv initialized with observation space: %s, action space: %s",
                      str(self.observation_space), str(self.action_space))
    
    def update_curriculum_level(self, level: int) -> None:
        """
        Aktualisiert das Curriculum-Level für dynamische Schwierigkeitsanpassung.
        
        Args:
            level: Das neue Curriculum-Level.
        """
        if level != self.curriculum_level:
            self.curriculum_level = level
            self.logger.info("Curriculum level updated to %d", level)
            self._setup_environment(level)
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Setzt die Umgebung zurück und gibt die initiale Beobachtung zurück.
        
        Args:
            seed: Optionaler Seed für die Zufallszahlengenerierung.
            options: Optionale Konfigurationsoptionen für den Reset.
            
        Returns:
            Tuple[np.ndarray, Dict[str, Any]]: Ein Tupel aus Observation und Info-Dictionary.
        """
        super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)
        
        # Extrahiere Optionen
        options = options or {}
        curriculum_level = options.get('curriculum_level', self.curriculum_level)
        
        # Umgebungszustand zurücksetzen
        self._setup_environment(curriculum_level)
        
        # Aktionsmaske aktualisieren
        self.action_mask = self.action_manager.get_action_mask(self.state)
        
        # Observation erstellen
        observation = self.observation_manager.get_observation(self.state)
        
        # Info-Dictionary erstellen
        info = {
            'action_mask': self.action_mask,
            'curriculum_level': self.curriculum_level,
            'episode_step': self.current_step
        }
        
        self.logger.info("Environment reset with curriculum level: %d", self.curriculum_level)
        
        return observation, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Führt einen Schritt in der Umgebung aus und gibt das Ergebnis zurück.
        
        Args:
            action: Die auszuführende Aktion.
            
        Returns:
            Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
                Ein Tupel aus Observation, Belohnung, terminated-Flag, truncated-Flag und Info-Dictionary.
        """
        # Überprüfe, ob die Aktion gültig ist
        if self.action_mask is not None and action >= 0 and action < len(self.action_mask) and self.action_mask[action] == 0:
            self.logger.warning("Invalid action %d selected. Using random valid action instead.", action)
            # Wenn ungültig, wähle eine zufällige gültige Aktion
            valid_actions = np.where(self.action_mask == 1)[0]
            if len(valid_actions) > 0:
                action = np.random.choice(valid_actions)
            else:
                # Wenn keine gültigen Aktionen, verwende eine Standardaktion
                action = 0
        
        # Aktion ausführen und Belohnung berechnen
        reward = self.action_manager.execute_action(self.state, action)
        
        # Schrittzähler erhöhen
        self.current_step += 1
        
        # Prüfe, ob die Episode beendet ist
        done = self.state.is_done or self.current_step >= self.max_episode_steps
        
        # In Gym v0.26+ gibt es zwei Flags: terminated (echtes Ende) und truncated (abgeschnitten)
        terminated = self.state.is_done
        truncated = not terminated and done
        
        # Observation und Action Mask aktualisieren
        observation = self.observation_manager.get_observation(self.state)
        self.action_mask = self.action_manager.get_action_mask(self.state)
        
        # Info-Dictionary erstellen
        info = {
            'action_mask': self.action_mask,
            'curriculum_level': self.curriculum_level,
            'episode_step': self.current_step,
            'is_success': self._is_success() if done else False
        }
        
        if done:
            # Episodenbelohnung hinzufügen
            episode_reward = self.reward_calculator.calculate_episode_reward(self.state)
            reward += episode_reward
            info['episode_reward'] = episode_reward
            info['total_reward'] = self.state.accumulated_reward + episode_reward
            
            # Kampfstatistiken für Analyse
            if hasattr(self.state, 'combat_history'):
                info['combat_history'] = self.state.combat_history
        
        self.logger.debug("Step %d: Action %d, Reward %.2f, Done %s", 
                       self.current_step, action, reward, str(done))
        
        return observation, reward, terminated, truncated, info
    
    def _setup_environment(self, curriculum_level: int) -> None:
        """
        Richtet die Umgebung basierend auf dem Curriculum-Level ein.
        
        Args:
            curriculum_level: Das zu verwendende Curriculum-Level.
        """
        # Curriculum-Level speichern
        self.curriculum_level = curriculum_level
        
        # Zustand zurücksetzen
        self.state.reset()
        
        # Schrittanzahl zurücksetzen
        self.current_step = 0
        
        # Bestimme die Spieler und Gegner basierend auf dem Curriculum-Level
        player_templates, opponent_templates = self._get_curriculum_templates(curriculum_level)
        
        # Initialisiere den Kampf mit den ausgewählten Templates
        self.state.reset(player_templates=player_templates, opponent_templates=opponent_templates)
    
    def _get_curriculum_templates(self, level: int) -> Tuple[List[str], List[str]]:
        """
        Bestimmt die Spieler- und Gegner-Templates basierend auf dem Curriculum-Level.
        
        Args:
            level: Das Curriculum-Level.
            
        Returns:
            Tuple[List[str], List[str]]: Ein Tupel aus Spieler- und Gegner-Templates.
        """
        # Lade die Curriculum-Einstellungen
        curriculum = self.curriculum_settings.get('levels', {})
        
        # Finde das passende Level
        level_config = curriculum.get(str(level), curriculum.get('0', {}))
        
        # Extrahiere Templates
        player_templates = level_config.get('player_templates', ['krieger'])  # Standardmäßig Krieger
        opponent_templates = level_config.get('opponent_templates', ['goblin_lv1'])  # Standardmäßig Goblin Level 1
        
        return player_templates, opponent_templates
    
    def _is_success(self) -> bool:
        """
        Prüft, ob die Episode erfolgreich war (Spieler haben gewonnen).
        
        Returns:
            bool: True, wenn die Spieler gewonnen haben, False sonst.
        """
        # Prüfe, ob alle Gegner besiegt sind und mindestens ein Spieler noch lebt
        all_opponents_defeated = all(not opp.is_alive() for opp in self.state.opponents) if self.state.opponents else True
        any_player_alive = any(pc.is_alive() for pc in self.state.player_characters) if self.state.player_characters else False
        
        return all_opponents_defeated and any_player_alive