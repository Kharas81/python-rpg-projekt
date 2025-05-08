"""
RPG Environment

Eine Gymnasium-kompatible Umgebung für das RPG-System.
"""
import time
from typing import Dict, List, Any, Optional, Tuple, Union, Set
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import logging

from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter, CombatAction
from src.environment.env_state import EnvironmentState
from src.environment.action_manager import ActionManager
from src.environment.observation_manager import ObservationManager
from src.environment.reward_calculator import RewardCalculator
from src.definitions.character import get_character_template
from src.utils.logging_setup import get_logger

# Logger für dieses Modul
logger = get_logger(__name__)


class RPGEnvironment(gym.Env):
    """
    Eine Gymnasium-kompatible Umgebung für das RPG-System.
    
    Diese Umgebung ermöglicht es, Reinforcement Learning mit dem RPG-System zu nutzen.
    Sie implementiert die Methoden reset(), step() und render() gemäß dem Gymnasium-Interface.
    """
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 1}
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialisiert die Umgebung mit einer optionalen Konfiguration.
        
        Args:
            config (Dict[str, Any], optional): Konfigurationseinstellungen für die Umgebung
        """
        super().__init__()
        
        self.config = config or {}
        
        # Manager-Instanzen erstellen
        self.action_manager = ActionManager(
            max_skills=self.config.get('max_skills', 10),
            max_targets=self.config.get('max_targets', 10)
        )
        
        self.observation_manager = ObservationManager(
            max_players=self.config.get('max_players', 4),
            max_opponents=self.config.get('max_opponents', 6),
            max_skills=self.config.get('max_skills', 10),
            max_status_effects=self.config.get('max_status_effects', 10),
            feature_size=self.config.get('feature_size', 15)
        )
        
        self.reward_calculator = RewardCalculator(config=self.config.get('reward_config', {}))
        
        # Gymnasium Spaces definieren
        self.action_space = self.action_manager.get_action_space()
        self.observation_space = self.observation_manager.get_observation_space()
        
        # Zustand initialisieren
        self.state = None
        self.curriculum_level = self.config.get('curriculum_level', 1)
        self.render_mode = self.config.get('render_mode', 'ansi')
        
        logger.info(f"RPGEnvironment initialisiert mit Action Space: {self.action_space}, Observation Space: {self.observation_space}")
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict]:
        """
        Setzt die Umgebung zurück und startet eine neue Episode.
        
        Args:
            seed (Optional[int]): Seed für die Zufallsgenerierung
            options (Optional[Dict[str, Any]]): Optionale Konfigurationsoptionen
            
        Returns:
            Tuple[np.ndarray, Dict]: Beobachtung und zusätzliche Informationen
        """
        super().reset(seed=seed)
        options = options or {}
        
        # Verwende übergebene Optionen oder Standardkonfiguration
        curriculum_level = options.get('curriculum_level', self.curriculum_level)
        
        # Charaktere und Gegner erstellen
        player_characters = self._create_player_characters(curriculum_level)
        opponent_characters = self._create_opponents(curriculum_level)
        
        # Kampf erstellen
        encounter = CombatEncounter(player_characters, opponent_characters)
        encounter.start_combat()  # Initialisiert Runde 1, Zugreihenfolge, etc.
        
        # Umgebungszustand erstellen
        self.state = EnvironmentState(
            encounter=encounter,
            player_characters=player_characters,
            opponent_characters=opponent_characters,
            current_round=encounter.round,
            curriculum_level=curriculum_level
        )
        
        # Initialen Zustand beobachten
        observation = self.observation_manager.observe(self.state)
        
        # Info-Dictionary erstellen
        info = {
            'action_mask': self.action_manager.get_action_mask(
                self.state.current_character,
                self.state.valid_targets
            ),
            'state_info': self.state.get_state_representation()
        }
        
        return observation, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Führt einen Schritt in der Umgebung aus.
        
        Args:
            action (int): Die auszuführende Aktion
            
        Returns:
            Tuple[np.ndarray, float, bool, bool, Dict]: Beobachtung, Belohnung, beendet, abgeschnitten, Info
        """
        if self.state is None:
            raise RuntimeError("Environment muss mit reset() initialisiert werden, bevor step() aufgerufen werden kann.")
        
        # Bestimmen, ob der aktuelle Zug vom Spieler oder vom Gegner ist
        is_player_turn = self.state.is_player_turn
        
        # Aktion decodieren
        decoded_action = self.action_manager.decode_action(
            action_id=action,
            character=self.state.current_character,
            valid_targets=self.state.valid_targets
        )
        
        if decoded_action is None:
            logger.warning(f"Ungültige Aktion: {action}")
            return self._handle_invalid_action()
        
        skill_id, target = decoded_action
        
        # Combat Action erstellen
        combat_action = self.action_manager.create_combat_action(
            character=self.state.current_character,
            skill_id=skill_id,
            target=target
        )
        
        if combat_action is None:
            logger.warning(f"Konnte keine Combat Action erstellen: {skill_id}, {target}")
            return self._handle_invalid_action()
        
        # Aktion ausführen
        action_result = self.state.encounter.combat_system.execute_action(combat_action)
        
        # Belohnung berechnen
        reward = self.reward_calculator.calculate_reward(
            is_player_turn=is_player_turn,
            action_result=action_result,
            character=self.state.current_character,
            targets=self.state.valid_targets,
            player_characters=self.state.player_characters,
            opponent_characters=self.state.opponent_characters,
            winner=self.state.encounter.winner if self.state.encounter.check_combat_end() else None
        )
        
        # Zum nächsten Charakter wechseln
        self.state.next_character()
        
        # Prüfen, ob die Episode beendet ist
        terminated = self.state.check_episode_done()
        truncated = False  # Wir implementieren kein Abschneiden in diesem Beispiel
        
        # Beobachtung extrahieren
        observation = self.observation_manager.observe(self.state)
        
        # Info-Dictionary erstellen
        info = {
            'action_mask': self.action_manager.get_action_mask(
                self.state.current_character,
                self.state.valid_targets
            ),
            'state_info': self.state.get_state_representation(),
            'action_result': {
                'damage_dealt': sum(action_result.damage_dealt.values()),
                'healing_done': sum(action_result.healing_done.values()),
                'kills': len(action_result.deaths)
            }
        }
        
        # Schrittzähler erhöhen
        self.state.step_count += 1
        
        return observation, reward, terminated, truncated, info
    
    def render(self) -> Optional[Union[str, np.ndarray]]:
        """
        Rendert den aktuellen Zustand der Umgebung.
        
        Returns:
            Optional[Union[str, np.ndarray]]: Die gerenderte Darstellung der Umgebung
        """
        if self.render_mode == 'ansi':
            return self._render_ansi()
        
        return None
    
    def _render_ansi(self) -> str:
        """
        Rendert den aktuellen Zustand als ANSI-Text.
        
        Returns:
            str: Die gerenderte Textdarstellung
        """
        if self.state is None:
            return "Umgebung wurde noch nicht initialisiert."
        
        output = []
        output.append("\n" + "=" * 60)
        output.append(f" KAMPFZUSTAND (Runde {self.state.current_round}) ")
        output.append("=" * 60)
        
        output.append("\nSPIELER:")
        for player in self.state.player_characters:
            hp_percent = int((player.hp / player.get_max_hp()) * 100) if player.get_max_hp() > 0 else 0
            status = "[TOT]" if not player.is_alive() else ""
            output.append(f"- {player.name} {status}: HP {player.hp}/{player.get_max_hp()} ({hp_percent}%)")
            
            # Resourcen anzeigen
            if player.base_combat_values.get('base_mana', 0) > 0:
                output.append(f"  Mana: {player.mana}/{player.base_combat_values.get('base_mana')}")
            if player.base_combat_values.get('base_stamina', 0) > 0:
                output.append(f"  Ausdauer: {player.stamina}/{player.base_combat_values.get('base_stamina')}")
            if player.base_combat_values.get('base_energy', 0) > 0:
                output.append(f"  Energie: {player.energy}/{player.base_combat_values.get('base_energy')}")
        
        output.append("\nGEGNER:")
        for opponent in self.state.opponent_characters:
            hp_percent = int((opponent.hp / opponent.get_max_hp()) * 100) if opponent.get_max_hp() > 0 else 0
            status = "[TOT]" if not opponent.is_alive() else ""
            output.append(f"- {opponent.name} {status}: HP {opponent.hp}/{opponent.get_max_hp()} ({hp_percent}%)")
        
        output.append("\nAKTUELLER CHARAKTER:")
        if self.state.current_character:
            output.append(f"- {self.state.current_character.name} ({self.state.current_character_index}. in Zugreihenfolge)")
            output.append(f"- Verfügbare Skills: {', '.join(self.state.current_character.skill_ids)}")
            
            if self.state.valid_targets:
                output.append(f"- Gültige Ziele: {', '.join(t.name for t in self.state.valid_targets)}")
            else:
                output.append("- Keine gültigen Ziele verfügbar!")
        else:
            output.append("- Kein aktueller Charakter")
        
        output.append("\n" + "-" * 60 + "\n")
        
        return "\n".join(output)
    
    def _handle_invalid_action(self) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Behandelt ungültige Aktionen.
        
        Returns:
            Tuple[np.ndarray, float, bool, bool, Dict]: Standardergebnis für ungültige Aktionen
        """
        # Bestrafung für ungültige Aktion
        invalid_reward = -1.0
        
        # Beobachtung und Info unverändert zurückgeben
        observation = self.observation_manager.observe(self.state)
        
        info = {
            'action_mask': self.action_manager.get_action_mask(
                self.state.current_character,
                self.state.valid_targets
            ),
            'state_info': self.state.get_state_representation(),
            'invalid_action': True
        }
        
        # Episode nicht beenden
        terminated = False
        truncated = False
        
        # Schrittzähler trotzdem erhöhen
        self.state.step_count += 1
        
        return observation, invalid_reward, terminated, truncated, info
    
    def _create_player_characters(self, curriculum_level: int) -> List[CharacterInstance]:
        """
        Erstellt Spielercharaktere basierend auf dem Curriculum-Level.
        
        Args:
            curriculum_level (int): Das aktuelle Curriculum-Level
            
        Returns:
            List[CharacterInstance]: Die erstellten Spielercharaktere
        """
        # Standardkonfiguration: 1-2 Spieler
        num_players = min(curriculum_level, 2)
        players = []
        
        # Verfügbare Charakterklassen
        available_classes = ['krieger', 'magier', 'schurke', 'kleriker']
        
        # Charaktere erstellen
        for i in range(num_players):
            class_id = available_classes[i % len(available_classes)]
            template = get_character_template(class_id)
            
            if template:
                # Level basierend auf Curriculum-Level (aber nie über 5)
                char_level = min(1 + (curriculum_level // 3), 5)
                
                character = CharacterInstance.from_template(
                    template=template,
                    level=char_level
                )
                
                # Spieler-Flag hinzufügen (für die Belohnungsberechnung)
                character.is_player = True
                
                players.append(character)
            else:
                logger.error(f"Konnte Charakter-Template für {class_id} nicht laden.")
        
        return players
    
    def _create_opponents(self, curriculum_level: int) -> List[CharacterInstance]:
        """
        Erstellt Gegner basierend auf dem Curriculum-Level.
        
        Args:
            curriculum_level (int): Das aktuelle Curriculum-Level
            
        Returns:
            List[CharacterInstance]: Die erstellten Gegner
        """
        # Anzahl der Gegner basierend auf Curriculum-Level
        num_opponents = 1 + (curriculum_level // 2)
        max_opponents = 5  # Maximale Anzahl an Gegnern
        num_opponents = min(num_opponents, max_opponents)
        
        # Gegnertypen nach Schwierigkeit sortiert
        opponent_types = [
            'skelett',              # Einfach
            'goblin',               # Einfach
            'goblin_schamane',      # Mittel
            'orc',                  # Mittel-Schwer
            'orc_hauptmann',        # Schwer
            'nekromant'             # Sehr schwer
        ]
        
        opponents = []
        
        # Gegnervielfalt basierend auf Curriculum-Level
        difficulty_range = min(curriculum_level, len(opponent_types))
        
        for i in range(num_opponents):
            # Bei höherem Curriculum-Level häufiger schwerere Gegner auswählen
            difficulty_index = min(
                int(np.random.beta(curriculum_level, 5) * difficulty_range),
                difficulty_range - 1
            )
            
            opponent_id = opponent_types[difficulty_index]
            from src.definitions.character import get_opponent_template
            
            template = get_opponent_template(opponent_id)
            
            if template:
                # Level basierend auf Curriculum-Level
                opponent_level = min(1 + (curriculum_level // 2), 5)
                
                # Bei höherem Curriculum-Level zufällig ein höheres Level vergeben
                if curriculum_level > 3 and np.random.random() < 0.3:
                    opponent_level += 1
                
                opponent = CharacterInstance.from_template(
                    template=template,
                    level=opponent_level
                )
                
                # Gegner-Flag hinzufügen (für die Belohnungsberechnung)
                opponent.is_player = False
                
                opponents.append(opponent)
            else:
                logger.error(f"Konnte Gegner-Template für {opponent_id} nicht laden.")
        
        return opponents