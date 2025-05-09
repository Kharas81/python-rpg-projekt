"""
Basis-Fernkampf-Strategie

Implementiert eine einfache KI-Strategie für Fernkämpfer.
"""
import random
from typing import List, Optional, Dict, Any, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillDefinition
from src.ai.strategies.base_strategy import BaseStrategy
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class BasicRangedStrategy(BaseStrategy):
    """
    Einfache KI-Strategie für Fernkämpfer.
    
    Diese Strategie priorisiert:
    1. Taktische Positionierung (nicht implementiert in dieser Version)
    2. Schwächere Ziele oder Magier/Heiler
    3. Skills mit Status-Effekten, wenn verfügbar
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
        
        # Verfügbare Skills sortieren
        skills_with_effects = []  # Skills mit Statuseffekten
        normal_attack_skills = []  # Normale Angriffsfertigkeiten
        other_skills = []  # Andere Skills (Heilung, Buff, etc.)
        
        for skill_id, skill in available_skills.items():
            if self._can_use_skill(skill):
                if skill.applies_effects and ('base_damage' in skill.effects or skill.get_base_damage() is not None):
                    skills_with_effects.append(skill)
                elif 'base_damage' in skill.effects or skill.get_base_damage() is not None:
                    normal_attack_skills.append(skill)
                else:
                    other_skills.append(skill)
        
        # Skills mit Status-Effekten bevorzugen, dann normale Angriffe, dann andere
        all_usable_skills = skills_with_effects + normal_attack_skills + other_skills
        
        if not all_usable_skills:
            logger.debug(f"{self.character.name} hat keine verwendbaren Skills")
            return None, None, []
        
        # Skill-Auswahl-Logik
        chosen_skill = None
        
        # Mit 60% Wahrscheinlichkeit Status-Effekt-Skills verwenden, wenn verfügbar
        if skills_with_effects and random.random() < 0.6:
            chosen_skill = random.choice(skills_with_effects)
        # Mit 30% Wahrscheinlichkeit normale Angriffe verwenden, wenn verfügbar
        elif normal_attack_skills and random.random() < 0.3:
            chosen_skill = random.choice(normal_attack_skills)
        # Sonst zufälligen Skill wählen
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
            # Angriffs-Skill
            
            # Priorität: Magier/Caster > Schwache Ziele > Zufällig
            caster_targets = self._filter_targets_by_tag(valid_targets, "CASTER")
            
            if caster_targets and random.random() < 0.7:
                # Mit 70% Wahrscheinlichkeit Caster angreifen, wenn vorhanden
                target = self._get_weakest_target(caster_targets)
            elif random.random() < 0.6:
                # Mit 60% Wahrscheinlichkeit das schwächste Ziel wählen
                target = self._get_weakest_target(valid_targets)
            else:
                # Sonst zufälliges Ziel
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
        
        logger.debug(f"{self.character.name} (Fernkampf-KI) wählt {chosen_skill.name} mit Ziel {target.name if target else 'keines'}")
        
        return chosen_skill, target, secondary_targets
