"""
Basis-Nahkampf-Strategie

Implementiert eine einfache KI-Strategie für Nahkämpfer.
"""
import random
from typing import List, Optional, Dict, Any, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillDefinition
from src.ai.strategies.base_strategy import BaseStrategy
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class BasicMeleeStrategy(BaseStrategy):
    """
    Einfache KI-Strategie für Nahkämpfer.
    
    Diese Strategie priorisiert:
    1. Schwache Ziele (geringere HP)
    2. Offensive Skills gegenüber defensiven
    3. Stärkere Angriffe, wenn genug Ressourcen vorhanden sind
    """
    
    def choose_action(self, allies: List[CharacterInstance], enemies: List[CharacterInstance], 
                      available_skills: Dict[str, SkillDefinition]) -> Tuple[Optional[SkillDefinition], 
                                                                            Optional[CharacterInstance], 
                                                                            List[CharacterInstance]]:
        """
        Wählt eine Aktion basierend auf der aktuellen Kampfsituation aus.
        
        Args:
            allies (List[CharacterInstance]): Liste der verbündeten Charaktere
            enemies (List[CharacterInstance]): Liste der feindlichen Charaktere
            available_skills (Dict[str, SkillDefinition]): Verfügbare Skills mit ihren Definitionen
            
        Returns:
            Tuple[Optional[SkillDefinition], Optional[CharacterInstance], List[CharacterInstance]]: 
            Der gewählte Skill, das Hauptziel und sekundäre Ziele
        """
        if not self.character.can_act():
            logger.debug(f"{self.character.name} kann nicht handeln")
            return None, None, []
        
        # Gültige Ziele finden
        valid_targets = self._get_valid_targets(enemies)
        if not valid_targets:
            logger.debug(f"{self.character.name} hat keine gültigen Ziele")
            return None, None, []
        
        # Verfügbare Skills sortieren (offensive zuerst)
        offensive_skills = []
        other_skills = []
        
        for skill_id, skill in available_skills.items():
            if self._can_use_skill(skill):
                if 'base_damage' in skill.effects or skill.get_base_damage() is not None:
                    offensive_skills.append(skill)
                else:
                    other_skills.append(skill)
        
        # Offensive Skills nach Schaden sortieren (stärkste zuerst)
        offensive_skills.sort(
            key=lambda s: (s.get_base_damage() or 0) * s.get_multiplier(),
            reverse=True
        )
        
        # Alle verfügbaren Skills kombinieren
        all_usable_skills = offensive_skills + other_skills
        
        if not all_usable_skills:
            logger.debug(f"{self.character.name} hat keine verwendbaren Skills")
            return None, None, []
        
        # Skill auswählen (mit 70% Chance den stärksten Angriff, sonst zufällig)
        if random.random() < 0.7 and offensive_skills:
            chosen_skill = offensive_skills[0]
        else:
            chosen_skill = random.choice(all_usable_skills)
        
        # Ziel auswählen
        target = None
        secondary_targets = []
        
        if chosen_skill.is_self_effect():
            # Selbst-Effekt
            target = self.character
        elif 'base_healing' in chosen_skill.effects:
            # Heilungs-Skill - den am meisten verletzten Verbündeten auswählen
            wounded_allies = [ally for ally in allies if ally.hp < ally.get_max_hp() and ally.is_alive()]
            if wounded_allies:
                target = self._get_lowest_health_percentage_target(wounded_allies)
        else:
            # Angriffs-Skill - mit 80% Chance das schwächste Ziel, sonst zufällig
            if random.random() < 0.8:
                target = self._get_weakest_target(valid_targets)
            else:
                target = self._get_random_target(valid_targets)
            
            # Bei Flächeneffekten sekundäre Ziele auswählen
            if chosen_skill.is_area_effect() and len(valid_targets) > 1:
                area_type = chosen_skill.get_area_type()
                
                if area_type == 'CLEAVE':
                    # Bei Cleave ein weiteres zufälliges Ziel wählen
                    other_targets = [t for t in valid_targets if t != target]
                    if other_targets:
                        secondary_targets = [random.choice(other_targets)]
                
                elif area_type == 'SPLASH':
                    # Bei Splash alle Ziele im Bereich wählen
                    # Für Einfachheit: alle anderen Ziele hinzufügen
                    secondary_targets = [t for t in valid_targets if t != target]
        
        logger.debug(f"{self.character.name} (Nahkampf-KI) wählt {chosen_skill.name} mit Ziel {target.name if target else 'keines'}")
        
        return chosen_skill, target, secondary_targets
