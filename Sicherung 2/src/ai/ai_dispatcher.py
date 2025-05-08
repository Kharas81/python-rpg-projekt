"""
AI-Dispatcher

Wählt die passende KI-Strategie basierend auf Charakter-Daten.
"""
from typing import Dict, Optional, List, Any

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillDefinition
from src.ai.strategies.base_strategy import BaseStrategy
from src.ai.strategies.basic_melee import BasicMeleeStrategy
from src.ai.strategies.basic_ranged import BasicRangedStrategy
from src.ai.strategies.support_caster import SupportCasterStrategy
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class AIDispatcher:
    """
    Verwaltet KI-Strategien und wählt die passende für einen Charakter aus.
    """
    
    def __init__(self):
        """Initialisiert den AI-Dispatcher."""
        # Dictionary zum Zwischenspeichern von Strategien für Charaktere
        self._character_strategies: Dict[str, BaseStrategy] = {}
        
        # Strategie-Map: Strategie-ID -> Strategie-Klasse
        self.strategy_map = {
            'basic_melee': BasicMeleeStrategy,
            'basic_ranged': BasicRangedStrategy,
            'support_caster': SupportCasterStrategy,
        }
    
    def get_strategy_for_character(self, character: CharacterInstance) -> Optional[BaseStrategy]:
        """
        Gibt die passende KI-Strategie für einen Charakter zurück.
        
        Args:
            character (CharacterInstance): Der Charakter
            
        Returns:
            Optional[BaseStrategy]: Die KI-Strategie oder None, wenn keine passende gefunden wird
        """
        # Prüfen, ob wir bereits eine Strategie für diesen Charakter haben
        if character.id in self._character_strategies:
            return self._character_strategies[character.id]
        
        # Strategie basierend auf AI-Strategy-Attribut wählen
        if hasattr(character, 'ai_strategy') and character.ai_strategy:
            strategy_id = character.ai_strategy
            strategy_class = self.strategy_map.get(strategy_id)
            
            if strategy_class:
                strategy = strategy_class(character)
                self._character_strategies[character.id] = strategy
                logger.debug(f"Strategie '{strategy_id}' für {character.name} gewählt")
                return strategy
        
        # Fallback: Strategie basierend auf Tags wählen
        if character.has_tag("CASTER") and character.has_tag("SUPPORT"):
            strategy = SupportCasterStrategy(character)
        elif character.has_tag("RANGED"):
            strategy = BasicRangedStrategy(character)
        else:
            # Standardmäßig Nahkampf-Strategie
            strategy = BasicMeleeStrategy(character)
        
        self._character_strategies[character.id] = strategy
        logger.debug(f"Fallback-Strategie '{strategy.__class__.__name__}' für {character.name} gewählt")
        return strategy
    
    def choose_action(self, character: CharacterInstance, 
                      allies: List[CharacterInstance], 
                      enemies: List[CharacterInstance],
                      available_skills: Dict[str, SkillDefinition]):
        """
        Wählt eine Aktion für einen Charakter basierend auf seiner KI-Strategie.
        
        Args:
            character (CharacterInstance): Der Charakter, für den eine Aktion gewählt wird
            allies (List[CharacterInstance]): Liste der verbündeten Charaktere
            enemies (List[CharacterInstance]): Liste der feindlichen Charaktere
            available_skills (Dict[str, SkillDefinition]): Verfügbare Skills mit ihren Definitionen
            
        Returns:
            Tuple: (gewählter Skill, Hauptziel, sekundäre Ziele) oder (None, None, []), wenn keine Aktion möglich ist
        """
        strategy = self.get_strategy_for_character(character)
        if not strategy:
            logger.warning(f"Keine KI-Strategie für {character.name} gefunden")
            return None, None, []
        
        # Strategisch Aktion wählen
        return strategy.choose_action(allies, enemies, available_skills)


# Globaler AI-Dispatcher
_ai_dispatcher = AIDispatcher()


def get_ai_dispatcher() -> AIDispatcher:
    """
    Gibt die globale Instanz des AI-Dispatchers zurück.
    
    Returns:
        AIDispatcher: Die globale Instanz
    """
    return _ai_dispatcher
