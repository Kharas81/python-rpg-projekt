"""
Support-Caster-Strategie

Implementiert eine KI-Strategie für Unterstützungs-Zauberwirker.
"""
import random
from typing import List, Optional, Dict, Any, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillDefinition
from src.ai.strategies.base_strategy import BaseStrategy
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class SupportCasterStrategy(BaseStrategy):
    """
    KI-Strategie für Unterstützer und Heiler.
    
    Diese Strategie priorisiert:
    1. Heilung von verletzten Verbündeten
    2. Unterstützungszauber auf Verbündete
    3. Schwächungszauber auf Gegner
    4. Direkte Angriffe als letzte Wahl
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
        valid_enemies = self._get_valid_targets(enemies)
        valid_allies = self._get_valid_targets(allies)
        
        if not valid_enemies and not valid_allies:
            logger.debug(f"{self.character.name} hat keine gültigen Ziele")
            return None, None, []
        
        # Verfügbare Skills kategorisieren
        healing_skills = []
        buff_skills = []
        debuff_skills = []
        attack_skills = []
        
        for skill_id, skill in available_skills.items():
            if not self._can_use_skill(skill):
                continue
                
            if 'base_healing' in skill.effects:
                healing_skills.append(skill)
            elif skill.is_self_effect() or (skill.applies_effects and any(e.id.endswith('_UP') for e in skill.applies_effects)):
                buff_skills.append(skill)
            elif skill.applies_effects and any(e.id.endswith('_DOWN') or e.id in ('STUNNED', 'SLOWED', 'WEAKENED') for e in skill.applies_effects):
                debuff_skills.append(skill)
            elif 'base_damage' in skill.effects or skill.get_base_damage() is not None:
                attack_skills.append(skill)
        
        # Entscheidungslogik
        chosen_skill = None
        target = None
        secondary_targets = []
        
        # 1. Prüfen, ob ein Verbündeter stark verletzt ist (< 50% HP)
        # und ob wir einen Heilzauber haben
        wounded_allies = [ally for ally in valid_allies if ally.hp < ally.get_max_hp() * 0.5]
        
        if wounded_allies and healing_skills:
            # Healing-Priorität: am stärksten verletzter Verbündeter
            chosen_skill = random.choice(healing_skills)
            target = self._get_lowest_health_percentage_target(wounded_allies)
            logger.debug(f"{self.character.name} heilt {target.name} mit {chosen_skill.name}")
        
        # 2. Prüfen, ob wir Buff-Skills haben und jemand diese gebrauchen könnte
        elif buff_skills and valid_allies and random.random() < 0.7:  # 70% Chance für Buff-Priorisierung
            chosen_skill = random.choice(buff_skills)
            
            # Ziel für Buff: Entweder self-effect oder stärkster Verbündeter
            if chosen_skill.is_self_effect():
                target = self.character
            else:
                # Einen starken Verbündeten auswählen (z.B. mit hohem Schaden)
                target = self._get_strongest_target(valid_allies)
            
            logger.debug(f"{self.character.name} verstärkt {target.name} mit {chosen_skill.name}")
        
        # 3. Prüfen, ob wir Debuff-Skills haben und Gegner da sind
        elif debuff_skills and valid_enemies and random.random() < 0.6:  # 60% Chance für Debuff-Priorisierung
            chosen_skill = random.choice(debuff_skills)
            
            # Priorität für Debuff: starke Gegner oder Caster
            caster_enemies = self._filter_targets_by_tag(valid_enemies, "CASTER")
            
            if caster_enemies and random.random() < 0.7:
                target = self._get_strongest_target(caster_enemies)
            else:
                target = self._get_strongest_target(valid_enemies)
            
            logger.debug(f"{self.character.name} schwächt {target.name} mit {chosen_skill.name}")
            
            # Bei Flächeneffekten sekundäre Ziele hinzufügen
            if chosen_skill.is_area_effect() and len(valid_enemies) > 1:
                area_type = chosen_skill.get_area_type()
                
                if area_type == 'SPLASH':
                    secondary_targets = [t for t in valid_enemies if t != target]
        
        # 4. Als letzte Option: Angriff, falls möglich
        elif attack_skills and valid_enemies:
            chosen_skill = random.choice(attack_skills)
            
            # Priorität für Angriff: schwache oder verletzliche Gegner
            if random.random() < 0.6:
                target = self._get_weakest_target(valid_enemies)
            else:
                target = self._get_random_target(valid_enemies)
            
            logger.debug(f"{self.character.name} greift {target.name} mit {chosen_skill.name} an")
            
            # Bei Flächeneffekten sekundäre Ziele hinzufügen
            if chosen_skill.is_area_effect() and len(valid_enemies) > 1:
                area_type = chosen_skill.get_area_type()
                
                if area_type == 'SPLASH':
                    secondary_targets = [t for t in valid_enemies if t != target]
        
        # Wenn keine passende Aktion gefunden wurde
        if not chosen_skill:
            # Einfach irgendeinen verfügbaren Skill wählen
            all_usable_skills = [s for s_id, s in available_skills.items() if self._can_use_skill(s)]
            
            if not all_usable_skills:
                logger.debug(f"{self.character.name} hat keine verwendbaren Skills")
                return None, None, []
            
            chosen_skill = random.choice(all_usable_skills)
            
            # Standard-Ziel basierend auf Skill-Typ wählen
            if chosen_skill.is_self_effect():
                target = self.character
            elif 'base_healing' in chosen_skill.effects:
                target = self._get_random_target([a for a in valid_allies if a.hp < a.get_max_hp()])
                target = target or self.character  # Fallback auf selbst, wenn kein verletztes Ziel
            else:
                target = self._get_random_target(valid_enemies) if valid_enemies else None
        
        if target:
            logger.debug(f"{self.character.name} (Support-KI) wählt {chosen_skill.name} mit Ziel {target.name}")
        else:
            logger.warning(f"{self.character.name} hat Skill {chosen_skill.name} gewählt, aber kein gültiges Ziel gefunden")
            return None, None, []
        
        return chosen_skill, target, secondary_targets
