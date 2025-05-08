"""
Action Manager

Definiert den Aktionsraum und übersetzt zwischen diskreten Aktionen und Spielaktionen.
"""
from typing import Dict, List, Tuple, Any, Optional, Set
import numpy as np
import gymnasium as gym

from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatAction
from src.definitions.skill import get_skill_definition
from src.utils.logging_setup import get_logger

# Logger für dieses Modul
logger = get_logger(__name__)


class ActionManager:
    """
    Verwaltet den Aktionsraum für das RL-Environment.
    
    Übernimmt die Konvertierung zwischen diskreten Aktionen und Spielaktionen,
    und stellt Funktionen zur Validierung von Aktionen bereit.
    """
    def __init__(self, max_skills: int = 10, max_targets: int = 10):
        """
        Initialisiert den Action Manager.
        
        Args:
            max_skills (int): Maximale Anzahl an Skills, die ein Charakter haben kann
            max_targets (int): Maximale Anzahl an Zielen, die für einen Skill ausgewählt werden können
        """
        self.max_skills = max_skills
        self.max_targets = max_targets
        
        # Gesamtzahl der Aktionen: max_skills * max_targets + max_skills (für Selbst-Effekte)
        self.action_space_size = max_skills * max_targets + max_skills
        
        # Bekannte Skills für schnelleren Zugriff
        self.skill_cache = {}
    
    def get_action_space(self) -> gym.spaces.Discrete:
        """
        Gibt den Aktionsraum für das RL-Environment zurück.
        
        Returns:
            gym.spaces.Discrete: Der diskrete Aktionsraum
        """
        return gym.spaces.Discrete(self.action_space_size)
    
    def get_action_mask(self, character: CharacterInstance, valid_targets: List[CharacterInstance]) -> np.ndarray:
        """
        Erstellt eine Maske für gültige Aktionen.
        
        Args:
            character (CharacterInstance): Der aktuelle Charakter
            valid_targets (List[CharacterInstance]): Liste der gültigen Ziele
            
        Returns:
            np.ndarray: Binäre Maske mit 1 für gültige und 0 für ungültige Aktionen
        """
        # Initialisierung der Maske mit Nullen
        mask = np.zeros(self.action_space_size, dtype=np.int8)
        
        if not character or not character.can_act():
            return mask  # Keine gültigen Aktionen
        
        # Skills des Charakters durchgehen
        for skill_idx, skill_id in enumerate(character.skill_ids):
            if skill_idx >= self.max_skills:
                break  # Maximum erreicht
                
            # Skill-Definition abrufen
            skill_def = self._get_skill_definition(skill_id)
            if not skill_def:
                continue
                
            # Prüfen, ob der Charakter genug Ressourcen hat
            if not character.has_enough_resource(skill_def):
                continue
                
            # Für Selbst-Effekte
            if skill_def.is_self_effect():
                action_idx = self._encode_self_action(skill_idx)
                mask[action_idx] = 1
                continue
                
            # Für Aktionen auf andere Ziele
            for target_idx, target in enumerate(valid_targets):
                if target_idx >= self.max_targets:
                    break  # Maximum erreicht
                    
                if target.can_be_targeted():
                    action_idx = self._encode_action(skill_idx, target_idx)
                    mask[action_idx] = 1
        
        return mask
    
    def decode_action(self, 
                     action_id: int, 
                     character: CharacterInstance, 
                     valid_targets: List[CharacterInstance]) -> Optional[Tuple[str, Optional[CharacterInstance]]]:
        """
        Dekodiert eine diskrete Aktion in Skill-ID und Ziel.
        
        Args:
            action_id (int): Die diskrete Aktions-ID
            character (CharacterInstance): Der aktuelle Charakter
            valid_targets (List[CharacterInstance]): Liste der gültigen Ziele
            
        Returns:
            Optional[Tuple[str, Optional[CharacterInstance]]]: Skill-ID und Ziel (None für Selbst-Effekte)
        """
        # Prüfen, ob die Aktion in den Bereich des Selbst-Effekts fällt
        if action_id >= self.max_skills * self.max_targets:
            # Selbst-Effekt
            skill_idx = action_id - self.max_skills * self.max_targets
            if skill_idx >= len(character.skill_ids):
                logger.warning(f"Ungültiger Skill-Index: {skill_idx}")
                return None
            
            skill_id = character.skill_ids[skill_idx]
            return (skill_id, None)  # Kein Ziel für Selbst-Effekte
        
        # Aktion auf anderes Ziel
        skill_idx = action_id // self.max_targets
        target_idx = action_id % self.max_targets
        
        if skill_idx >= len(character.skill_ids):
            logger.warning(f"Ungültiger Skill-Index: {skill_idx}")
            return None
        
        if target_idx >= len(valid_targets):
            logger.warning(f"Ungültiges Ziel-Index: {target_idx}")
            return None
        
        skill_id = character.skill_ids[skill_idx]
        target = valid_targets[target_idx]
        
        return (skill_id, target)
    
    def create_combat_action(self, 
                           character: CharacterInstance, 
                           skill_id: str, 
                           target: Optional[CharacterInstance]) -> Optional[CombatAction]:
        """
        Erstellt eine CombatAction aus Skill-ID und Ziel.
        
        Args:
            character (CharacterInstance): Der ausführende Charakter
            skill_id (str): Die ID des Skills
            target (Optional[CharacterInstance]): Das Ziel (None für Selbst-Effekte)
            
        Returns:
            Optional[CombatAction]: Die erstellte CombatAction oder None bei Fehler
        """
        skill_def = self._get_skill_definition(skill_id)
        if not skill_def:
            logger.warning(f"Skill-Definition für {skill_id} nicht gefunden")
            return None
        
        # Bei Selbst-Effekten ist der Charakter selbst das Ziel
        primary_target = character if skill_def.is_self_effect() else target
        
        action = CombatAction(
            actor=character,
            skill=skill_def,
            primary_target=primary_target,
            secondary_targets=[]  # Aktuell keine Unterstützung für sekundäre Ziele
        )
        
        return action
    
    def _encode_action(self, skill_idx: int, target_idx: int) -> int:
        """
        Kodiert Skill-Index und Ziel-Index zu einer diskreten Aktion.
        
        Args:
            skill_idx (int): Index des Skills
            target_idx (int): Index des Ziels
            
        Returns:
            int: Die kodierte Aktions-ID
        """
        return skill_idx * self.max_targets + target_idx
    
    def _encode_self_action(self, skill_idx: int) -> int:
        """
        Kodiert einen Selbst-Effekt zu einer diskreten Aktion.
        
        Args:
            skill_idx (int): Index des Skills
            
        Returns:
            int: Die kodierte Aktions-ID für den Selbst-Effekt
        """
        return self.max_skills * self.max_targets + skill_idx
    
    def _get_skill_definition(self, skill_id: str):
        """
        Holt die Skill-Definition mit Caching.
        
        Args:
            skill_id (str): Die ID des Skills
            
        Returns:
            SkillDefinition: Die Skill-Definition oder None bei Fehler
        """
        if skill_id not in self.skill_cache:
            try:
                self.skill_cache[skill_id] = get_skill_definition(skill_id)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Skill-Definition für {skill_id}: {e}")
                return None
        
        return self.skill_cache[skill_id]