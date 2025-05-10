"""
AI-Dispatcher

Wählt die passende KI-Strategie basierend auf Charakter-Daten.
"""
from typing import Dict, Optional, List, Any, Tuple

# Pfadkorrektur für den Fall, dass dieses Modul isoliert oder von einem anderen Kontext geladen wird
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillDefinition
from src.ai.strategies.base_strategy import BaseStrategy
from src.ai.strategies.basic_melee import BasicMeleeStrategy
from src.ai.strategies.basic_ranged import BasicRangedStrategy
from src.ai.strategies.support_caster import SupportCasterStrategy
from src.utils.logging_setup import get_logger # Sicherstellen, dass get_logger korrekt importiert wird


# Logger für dieses Modul
logger = get_logger(__name__) # Korrekte Verwendung von get_logger


class AIDispatcher:
    """
    Verwaltet KI-Strategien und wählt die passende für einen Charakter aus.
    """

    def __init__(self):
        """Initialisiert den AI-Dispatcher."""
        self._character_strategies: Dict[str, BaseStrategy] = {}
        self.strategy_map: Dict[str, type[BaseStrategy]] = { # Typ-Annotation für die Klasse selbst
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
        if character.id in self._character_strategies:
            return self._character_strategies[character.id]

        strategy_to_use: Optional[BaseStrategy] = None
        chosen_strategy_id: Optional[str] = None

        if hasattr(character, 'ai_strategy') and character.ai_strategy:
            strategy_id_from_char = character.ai_strategy
            strategy_class = self.strategy_map.get(strategy_id_from_char)

            if strategy_class:
                strategy_to_use = strategy_class(character)
                chosen_strategy_id = strategy_id_from_char
                logger.debug(f"Strategie '{chosen_strategy_id}' für {character.name} (via Charakter-Attribut) gewählt.")
            else:
                logger.warning(f"Charakter {character.name} hat ungültige ai_strategy '{strategy_id_from_char}'. Fallback wird versucht.")

        if not strategy_to_use: # Fallback-Logik
            if character.has_tag("CASTER") and character.has_tag("SUPPORT"):
                strategy_to_use = SupportCasterStrategy(character)
                chosen_strategy_id = "support_caster (Fallback)"
            elif character.has_tag("RANGED"):
                strategy_to_use = BasicRangedStrategy(character)
                chosen_strategy_id = "basic_ranged (Fallback)"
            else: # Standard-Fallback
                strategy_to_use = BasicMeleeStrategy(character)
                chosen_strategy_id = "basic_melee (Fallback)"
            logger.debug(f"Fallback-Strategie '{chosen_strategy_id}' für {character.name} gewählt.")
        
        if strategy_to_use:
            self._character_strategies[character.id] = strategy_to_use
        return strategy_to_use

    def choose_action(self,
                      character: CharacterInstance,
                      allies: List[CharacterInstance],
                      enemies: List[CharacterInstance],
                      available_skills: Dict[str, SkillDefinition]) \
            -> Tuple[Optional[SkillDefinition], Optional[CharacterInstance], List[CharacterInstance]]:
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
            logger.warning(f"Keine KI-Strategie für {character.name} gefunden. Keine Aktion möglich.")
            return None, None, []

        return strategy.choose_action(allies, enemies, available_skills)


# Globaler AI-Dispatcher (Singleton-ähnliches Muster)
_ai_dispatcher_instance: Optional[AIDispatcher] = None

def get_ai_dispatcher() -> AIDispatcher:
    """
    Gibt die globale Instanz des AI-Dispatchers zurück.

    Returns:
        AIDispatcher: Die globale Instanz
    """
    global _ai_dispatcher_instance
    if _ai_dispatcher_instance is None:
        _ai_dispatcher_instance = AIDispatcher()
    return _ai_dispatcher_instance