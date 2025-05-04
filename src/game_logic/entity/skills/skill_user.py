"""
Skill User Module

Dieses Modul definiert die SkillUser-Mixin-Klasse, die Funktionalität für die
Verwendung von Skills bereitstellt.
"""

import logging
from typing import Dict, Any, List, Optional

from src.definitions.data_service import data_service
from src.game_logic.entity.skills.damage_effect import DamageEffect
from src.game_logic.entity.skills.healing_effect import HealingEffect
from src.game_logic.entity.skills.shield_effect import ShieldEffect
from src.game_logic.entity.skills.status_effect_processor import StatusEffectProcessor

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class SkillUser:
    """
    Mixin-Klasse für Entitäten, die Skills verwenden können.
    
    Diese Klasse stellt Methoden bereit, um zu prüfen, ob Skills eingesetzt werden
    können und um diese auf Ziele anzuwenden.
    """
    
    def can_use_skill(self, skill_id: str) -> bool:
        """
        Prüft, ob die Entität einen bestimmten Skill einsetzen kann.
        
        Args:
            skill_id: ID des Skills
            
        Returns:
            True, wenn der Skill eingesetzt werden kann, sonst False
        """
        if not self.can_act:  # type: ignore
            logger.debug(f"{self.name} kann nicht handeln und daher keine Skills einsetzen")  # type: ignore
            return False
        
        if skill_id not in self.known_skills:  # type: ignore
            logger.debug(f"{self.name} kennt den Skill {skill_id} nicht")  # type: ignore
            return False
        
        # Lade Skill-Daten
        try:
            skill_data = data_service.get_skill(skill_id)
        except KeyError:
            logger.error(f"Skill {skill_id} nicht in der Datenbank gefunden")
            return False
        
        # Prüfe Ressourcenanforderungen
        cost_type = skill_data["cost"]["type"]
        cost_amount = skill_data["cost"]["amount"]
        
        if cost_type == "stamina":
            if self.current_stamina is None or self.current_stamina < cost_amount:  # type: ignore
                logger.debug(f"{self.name} hat nicht genug Stamina für {skill_id}")  # type: ignore
                return False
        elif cost_type == "energy":
            if self.current_energy is None or self.current_energy < cost_amount:  # type: ignore
                logger.debug(f"{self.name} hat nicht genug Energie für {skill_id}")  # type: ignore
                return False
        elif cost_type == "mana":
            if self.current_mana is None or self.current_mana < cost_amount:  # type: ignore
                logger.debug(f"{self.name} hat nicht genug Mana für {skill_id}")  # type: ignore
                return False
        
        return True
    
    def use_skill(self, skill_id: str, targets: List['Entity']) -> Dict[str, Any]:  # noqa: F821
        """
        Führt einen Skill gegen bestimmte Ziele aus.
        
        Args:
            skill_id: ID des Skills
            targets: Liste der Zielentitäten
            
        Returns:
            Dictionary mit Ergebnissen der Skill-Nutzung
        """
        if not self.can_use_skill(skill_id):
            return {"success": False, "message": f"{self.name} kann {skill_id} nicht einsetzen"}  # type: ignore
        
        # Lade Skill-Daten
        skill_data = data_service.get_skill(skill_id)
        
        # Ressourcen abziehen
        cost_type = skill_data["cost"]["type"]
        cost_amount = skill_data["cost"]["amount"]
        
        if cost_type == "stamina":
            self.current_stamina -= cost_amount  # type: ignore
        elif cost_type == "energy":
            self.current_energy -= cost_amount  # type: ignore
        elif cost_type == "mana":
            self.current_mana -= cost_amount  # type: ignore
        
        # Skill-Effekte anwenden
        results = {"success": True, "targets": {}, "message": ""}
        
        # Prozessoren für verschiedene Effekttypen
        damage_effect = DamageEffect()
        healing_effect = HealingEffect()
        shield_effect = ShieldEffect()
        status_effect_processor = StatusEffectProcessor()
        
        # Wende Effekte an
        for effect in skill_data["effects"]:
            effect_type = effect["type"]
            
            if effect_type == "damage":
                results["message"] += damage_effect.apply(self, effect, targets, results)  # type: ignore
            elif effect_type == "healing":
                results["message"] += healing_effect.apply(self, effect, targets, results)  # type: ignore
            elif effect_type == "shield":
                results["message"] += shield_effect.apply(self, effect, targets, results)  # type: ignore
            elif effect_type == "status":
                results["message"] += status_effect_processor.apply(self, effect, targets, results)  # type: ignore
        
        return results
