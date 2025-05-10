# src/ai/ai_dispatcher.py
"""
Wählt die passende KI-Strategie basierend auf Charakterdaten (insbesondere ai_strategy_id).
Erstellt und gibt eine Instanz der entsprechenden Strategieklasse zurück.
"""
import logging
from typing import Optional, List, Dict, Any, Type 

from src.ai.strategies.basic_melee import BasicMeleeStrategy
from src.ai.strategies.basic_ranged import BasicRangedStrategy
from src.ai.strategies.support_caster import SupportCasterStrategy

from src.game_logic.entities import CharacterInstance # Direktimport ok
from src.definitions.skill import SkillTemplate
from src.definitions.character import CharacterTemplate 
from src.definitions.loader import load_skill_templates, load_character_templates 

logger = logging.getLogger(__name__)

STRATEGY_MAP: Dict[str, Type[Any]] = {
    "basic_melee": BasicMeleeStrategy,
    "basic_ranged": BasicRangedStrategy,
    "support_caster": SupportCasterStrategy,
}

_SKILL_DEFINITIONS: Optional[Dict[str, SkillTemplate]] = None
_CHARACTER_DEFINITIONS: Optional[Dict[str, CharacterTemplate]] = None

def _ensure_definitions_loaded():
    """Stellt sicher, dass Skill- und Charakterdefinitionen geladen sind."""
    global _SKILL_DEFINITIONS, _CHARACTER_DEFINITIONS # KORREKTUR: global deklarieren
    if _SKILL_DEFINITIONS is None:
        try:
            _SKILL_DEFINITIONS = load_skill_templates()
        except Exception as e:
            logger.critical(f"Fehler beim Laden der Skill-Definitionen im AI Dispatcher: {e}")
            _SKILL_DEFINITIONS = {} 
    
    if _CHARACTER_DEFINITIONS is None: 
        try:
            _CHARACTER_DEFINITIONS = load_character_templates()
        except Exception as e:
            logger.critical(f"Fehler beim Laden der Charakter-Definitionen im AI Dispatcher: {e}")
            _CHARACTER_DEFINITIONS = {} 

def get_ai_strategy_instance(actor: 'CharacterInstance', 
                               all_entities_in_combat: List['CharacterInstance']) -> Optional[Any]:
    _ensure_definitions_loaded() 

    if not _SKILL_DEFINITIONS: 
        logger.error(f"AI Dispatcher kann keine Strategie erstellen, da Skill-Definitionen fehlen.")
        return None

    strategy_id: Optional[str] = None
    if hasattr(actor.base_template, 'ai_strategy_id'):
        strategy_id = actor.base_template.ai_strategy_id
    
    if not strategy_id:
        logger.warning(f"Akteur '{actor.name}' hat keine 'ai_strategy_id' in seinem Template. Keine Strategie verwendet.")
        return None 

    strategy_class = STRATEGY_MAP.get(strategy_id)

    if not strategy_class:
        logger.error(f"Unbekannte ai_strategy_id '{strategy_id}' für Akteur '{actor.name}'. Keine passende KI-Strategie gefunden.")
        return None

    try:
        if strategy_class is BasicMeleeStrategy:
            instance = strategy_class(actor=actor, skill_definitions=_SKILL_DEFINITIONS)
        elif strategy_class is BasicRangedStrategy:
            if not _CHARACTER_DEFINITIONS: 
                logger.error(f"Charakter-Definitionen nicht geladen, kann BasicRangedStrategy nicht erstellen.")
                return None
            instance = strategy_class(actor=actor, skill_definitions=_SKILL_DEFINITIONS, character_definitions=_CHARACTER_DEFINITIONS)
        elif strategy_class is SupportCasterStrategy:
            instance = strategy_class(actor=actor, 
                                      all_entities_in_combat=all_entities_in_combat, 
                                      skill_definitions=_SKILL_DEFINITIONS,
                                      character_definitions=_CHARACTER_DEFINITIONS or {}) 
        else:
            logger.warning(f"Strategieklasse '{strategy_class.__name__}' hat keinen spezifischen Instanziierungs-Pfad im Dispatcher. Versuche generische Instanziierung.")
            instance = strategy_class(actor=actor, skill_definitions=_SKILL_DEFINITIONS) 
            
        logger.info(f"KI-Strategie '{strategy_class.__name__}' für Akteur '{actor.name}' (ID: {strategy_id}) instanziiert.")
        return instance
    except Exception as e:
        logger.error(f"Fehler bei der Instanziierung der KI-Strategie '{strategy_class.__name__}' für Akteur '{actor.name}': {e}", exc_info=True) # exc_info hinzugefügt
        return None

# ... (Rest der Datei, __main__ Block bleibt gleich)
if __name__ == '__main__':
    from src.game_logic.entities import CharacterInstance
    from src.definitions.loader import load_opponent_templates 
    from src.config.config import CONFIG 

    print("\n--- Teste AI Dispatcher ---")
    try:
        opp_templates = load_opponent_templates()
        if not opp_templates:
            raise Exception("Konnte keine Gegner-Templates für den Test laden.")
        
        goblin_melee_template = opp_templates.get("goblin_lv1") 
        goblin_archer_template = opp_templates.get("goblin_archer_lv2") 
        goblin_shaman_template = opp_templates.get("goblin_shaman_lv3") 
        
        class DummyOpponentTemplateNoAI:
            id = "dummy_no_ai"; name = "Dummy No AI Strategy"; primary_attributes = {"STR": 10}; base_hp = 10
            combat_values = {}; skills = []; level = 1
        
        class DummyOpponentTemplateUnknownAI:
            id = "dummy_unknown_ai"; name = "Dummy Unknown AI Strategy"; primary_attributes = {"STR": 10}; base_hp = 10
            combat_values = {}; skills = []; level = 1; ai_strategy_id = "unknown_strategy"

        if not goblin_melee_template or not goblin_archer_template or not goblin_shaman_template:
            raise Exception("Benötigte Goblin-Templates für Dispatcher-Test nicht gefunden.")

        actor_melee = CharacterInstance(base_template=goblin_melee_template)
        actor_ranged = CharacterInstance(base_template=goblin_archer_template)
        actor_support = CharacterInstance(base_template=goblin_shaman_template)
        actor_no_ai = CharacterInstance(base_template=DummyOpponentTemplateNoAI())
        actor_unknown_ai = CharacterInstance(base_template=DummyOpponentTemplateUnknownAI())

        dummy_combat_list = [actor_melee, actor_ranged, actor_support]

        print("\n-- Teste get_ai_strategy_instance --")

        strategy_melee = get_ai_strategy_instance(actor_melee, dummy_combat_list)
        print(f"Für '{actor_melee.name}' (Strategie-ID: '{getattr(actor_melee.base_template, 'ai_strategy_id', 'N/A')}'): Erhaltene Strategie-Instanz: {type(strategy_melee).__name__ if strategy_melee else 'None'}")
        assert isinstance(strategy_melee, BasicMeleeStrategy)

        strategy_ranged = get_ai_strategy_instance(actor_ranged, dummy_combat_list)
        print(f"Für '{actor_ranged.name}' (Strategie-ID: '{getattr(actor_ranged.base_template, 'ai_strategy_id', 'N/A')}'): Erhaltene Strategie-Instanz: {type(strategy_ranged).__name__ if strategy_ranged else 'None'}")
        assert isinstance(strategy_ranged, BasicRangedStrategy)

        strategy_support = get_ai_strategy_instance(actor_support, dummy_combat_list)
        print(f"Für '{actor_support.name}' (Strategie-ID: '{getattr(actor_support.base_template, 'ai_strategy_id', 'N/A')}'): Erhaltene Strategie-Instanz: {type(strategy_support).__name__ if strategy_support else 'None'}")
        assert isinstance(strategy_support, SupportCasterStrategy)
        
        strategy_no_ai = get_ai_strategy_instance(actor_no_ai, dummy_combat_list)
        print(f"Für '{actor_no_ai.name}' (Strategie-ID: '{getattr(actor_no_ai.base_template, 'ai_strategy_id', 'N/A')}'): Erhaltene Strategie-Instanz: {type(strategy_no_ai).__name__ if strategy_no_ai else 'None'}")
        assert strategy_no_ai is None

        strategy_unknown_ai = get_ai_strategy_instance(actor_unknown_ai, dummy_combat_list)
        print(f"Für '{actor_unknown_ai.name}' (Strategie-ID: '{getattr(actor_unknown_ai.base_template, 'ai_strategy_id', 'N/A')}'): Erhaltene Strategie-Instanz: {type(strategy_unknown_ai).__name__ if strategy_unknown_ai else 'None'}")
        assert strategy_unknown_ai is None

    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in ai_dispatcher.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in ai_dispatcher.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    print("\n--- AI Dispatcher-Tests abgeschlossen ---")