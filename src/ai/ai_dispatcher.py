# src/ai/ai_dispatcher.py
"""
Wählt die passende KI-Strategie basierend auf Charakterdaten (insbesondere ai_strategy_id).
Erstellt und gibt eine Instanz der entsprechenden Strategieklasse zurück.
"""
import logging
from typing import Optional, List, Dict, Any, Type # Type für Klassenreferenzen

# Importiere die konkreten Strategieklassen
from src.ai.strategies.basic_melee import BasicMeleeStrategy
from src.ai.strategies.basic_ranged import BasicRangedStrategy
from src.ai.strategies.support_caster import SupportCasterStrategy

# Importe für Typ-Annotationen und Zugriff auf Spielobjekte
if True: # Um Zirkularimport zu vermeiden
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate
    from src.definitions.character import CharacterTemplate # Für BasicRangedStrategy
    from src.definitions.loader import load_skill_templates, load_character_templates # Für Skill/Char-Definitionen

logger = logging.getLogger(__name__)

# Mapping von Strategie-IDs (aus opponents.json5) zu Strategieklassen
# Hier verwenden wir Type[Any] oder spezifischer Type[BasicMeleeStrategy] etc. wenn bekannt.
# Type[Any] ist flexibler, wenn Strategieklassen unterschiedliche Konstruktoren hätten,
# aber hier sind sie ähnlich genug.
STRATEGY_MAP: Dict[str, Type[Any]] = {
    "basic_melee": BasicMeleeStrategy,
    "basic_ranged": BasicRangedStrategy,
    "support_caster": SupportCasterStrategy,
    # Weitere Strategien hier hinzufügen
}

# Globale Caches für Definitionen, um sie nicht jedes Mal neu zu laden
_SKILL_DEFINITIONS: Optional[Dict[str, 'SkillTemplate']] = None
_CHARACTER_DEFINITIONS: Optional[Dict[str, 'CharacterTemplate']] = None

def _ensure_definitions_loaded():
    """Stellt sicher, dass Skill- und Charakterdefinitionen geladen sind."""
    global _SKILL_DEFINITIONS, _CHARACTER_DEFINITIONS
    if _SKILL_DEFINITIONS is None:
        try:
            _SKILL_DEFINITIONS = load_skill_templates()
        except Exception as e:
            logger.critical(f"Fehler beim Laden der Skill-Definitionen im AI Dispatcher: {e}")
            _SKILL_DEFINITIONS = {} # Fallback
    
    if _CHARACTER_DEFINITIONS is None: # Wird von BasicRangedStrategy benötigt
        try:
            _CHARACTER_DEFINITIONS = load_character_templates()
        except Exception as e:
            logger.critical(f"Fehler beim Laden der Charakter-Definitionen im AI Dispatcher: {e}")
            _CHARACTER_DEFINITIONS = {} # Fallback


def get_ai_strategy_instance(actor: 'CharacterInstance', 
                               all_entities_in_combat: List['CharacterInstance']) -> Optional[Any]:
    """
    Erstellt und gibt eine Instanz der passenden KI-Strategie für den Akteur zurück.

    Args:
        actor: Die Charakterinstanz, für die die KI-Strategie benötigt wird.
        all_entities_in_combat: Eine Liste aller Entitäten im aktuellen Kampf,
                                notwendig für Strategien, die Verbündete/Gegner berücksichtigen.

    Returns:
        Eine Instanz einer KI-Strategieklasse oder None, wenn keine passende Strategie gefunden wird.
    """
    _ensure_definitions_loaded() # Sicherstellen, dass Definitionen verfügbar sind

    if not _SKILL_DEFINITIONS: # Wenn Skill-Definitionen nicht geladen werden konnten
        logger.error(f"AI Dispatcher kann keine Strategie erstellen, da Skill-Definitionen fehlen.")
        return None

    # Die ai_strategy_id sollte im OpponentTemplate des Akteurs gespeichert sein.
    strategy_id: Optional[str] = None
    if hasattr(actor.base_template, 'ai_strategy_id'):
        strategy_id = actor.base_template.ai_strategy_id
    
    if not strategy_id:
        logger.warning(f"Akteur '{actor.name}' hat keine 'ai_strategy_id' in seinem Template. "
                       f"Verwende Standardstrategie (falls definiert) oder keine Strategie.")
        # Hier könnte man eine Default-Strategie festlegen, z.B. BasicMeleeStrategy
        # strategy_id = "basic_melee" # Beispiel für einen Default
        return None # Fürs Erste keine Strategie, wenn nicht explizit definiert

    strategy_class = STRATEGY_MAP.get(strategy_id)

    if not strategy_class:
        logger.error(f"Unbekannte ai_strategy_id '{strategy_id}' für Akteur '{actor.name}'. "
                     f"Keine passende KI-Strategie gefunden.")
        return None

    try:
        # Instanziiere die Strategie. Beachte, dass unterschiedliche Strategien
        # unterschiedliche Argumente im Konstruktor erwarten könnten.
        if strategy_class is BasicMeleeStrategy:
            instance = strategy_class(actor=actor, skill_definitions=_SKILL_DEFINITIONS)
        elif strategy_class is BasicRangedStrategy:
            if not _CHARACTER_DEFINITIONS: # BasicRanged benötigt auch Charakter-Definitionen
                logger.error(f"Charakter-Definitionen nicht geladen, kann BasicRangedStrategy nicht erstellen.")
                return None
            instance = strategy_class(actor=actor, skill_definitions=_SKILL_DEFINITIONS, character_definitions=_CHARACTER_DEFINITIONS)
        elif strategy_class is SupportCasterStrategy:
            if not _CHARACTER_DEFINITIONS: # Wird zwar nicht direkt genutzt, aber konsistent
                 _CHARACTER_DEFINITIONS = {} # Leeres Dict, falls nicht geladen
            instance = strategy_class(actor=actor, 
                                      all_entities_in_combat=all_entities_in_combat, 
                                      skill_definitions=_SKILL_DEFINITIONS,
                                      character_definitions=_CHARACTER_DEFINITIONS or {}) # Fallback auf leeres Dict
        else:
            # Fallback für andere Strategien, die vielleicht nur actor und skill_definitions brauchen
            logger.warning(f"Strategieklasse '{strategy_class.__name__}' hat keinen spezifischen Instanziierungs-Pfad im Dispatcher. Versuche generische Instanziierung.")
            # Dies ist ein Platzhalter. Im Idealfall hat jede Strategie eine klare Schnittstelle.
            # Wenn neue Strategien hinzukommen, muss dieser Dispatcher angepasst werden.
            instance = strategy_class(actor=actor, skill_definitions=_SKILL_DEFINITIONS) 
            # ACHTUNG: Dies könnte fehlschlagen, wenn die Strategie andere Argumente erwartet!

        logger.info(f"KI-Strategie '{strategy_class.__name__}' für Akteur '{actor.name}' (ID: {strategy_id}) instanziiert.")
        return instance
    except Exception as e:
        logger.error(f"Fehler bei der Instanziierung der KI-Strategie '{strategy_class.__name__}' "
                     f"für Akteur '{actor.name}': {e}")
        return None


if __name__ == '__main__':
    # Testen des AI Dispatchers
    from src.game_logic.entities import CharacterInstance
    from src.definitions.loader import load_opponent_templates # Nur Opponent-Templates für den Test
    from src.config.config import CONFIG # Stellt sicher, dass CONFIG und damit auch Definitionen geladen werden

    print("\n--- Teste AI Dispatcher ---")
    try:
        # Lade Gegner-Templates (enthält ai_strategy_id)
        # load_skill_templates() und load_character_templates() werden von _ensure_definitions_loaded() aufgerufen.
        opp_templates = load_opponent_templates()
        if not opp_templates:
            raise Exception("Konnte keine Gegner-Templates für den Test laden.")

        # Erstelle Test-Akteure mit verschiedenen Strategie-IDs
        goblin_melee_template = opp_templates.get("goblin_lv1") # ai_strategy_id: "basic_melee"
        goblin_archer_template = opp_templates.get("goblin_archer_lv2") # ai_strategy_id: "basic_ranged"
        goblin_shaman_template = opp_templates.get("goblin_shaman_lv3") # ai_strategy_id: "support_caster"
        
        # Erstelle Dummy-Gegner ohne Strategie-ID für Fehlertest
        class DummyOpponentTemplateNoAI:
            id = "dummy_no_ai"
            name = "Dummy No AI Strategy"
            primary_attributes = {"STR": 10}
            base_hp = 10
            combat_values = {}
            skills = []
            level = 1
            # KEINE ai_strategy_id
        
        class DummyOpponentTemplateUnknownAI:
            id = "dummy_unknown_ai"
            name = "Dummy Unknown AI Strategy"
            primary_attributes = {"STR": 10}
            base_hp = 10
            combat_values = {}
            skills = []
            level = 1
            ai_strategy_id = "unknown_strategy"


        if not goblin_melee_template or not goblin_archer_template or not goblin_shaman_template:
            raise Exception("Benötigte Goblin-Templates für Dispatcher-Test nicht gefunden.")

        actor_melee = CharacterInstance(base_template=goblin_melee_template)
        actor_ranged = CharacterInstance(base_template=goblin_archer_template)
        actor_support = CharacterInstance(base_template=goblin_shaman_template)
        actor_no_ai = CharacterInstance(base_template=DummyOpponentTemplateNoAI())
        actor_unknown_ai = CharacterInstance(base_template=DummyOpponentTemplateUnknownAI())

        # Dummy-Liste für all_entities_in_combat (wird nur von SupportCasterStrategy benötigt)
        dummy_combat_list = [actor_melee, actor_ranged, actor_support]

        print("\n-- Teste get_ai_strategy_instance --")

        strategy_melee = get_ai_strategy_instance(actor_melee, dummy_combat_list)
        print(f"Für '{actor_melee.name}' (Strategie-ID: '{getattr(actor_melee.base_template, 'ai_strategy_id', 'N/A')}'): "
              f"Erhaltene Strategie-Instanz: {type(strategy_melee).__name__ if strategy_melee else 'None'}")
        assert isinstance(strategy_melee, BasicMeleeStrategy)

        strategy_ranged = get_ai_strategy_instance(actor_ranged, dummy_combat_list)
        print(f"Für '{actor_ranged.name}' (Strategie-ID: '{getattr(actor_ranged.base_template, 'ai_strategy_id', 'N/A')}'): "
              f"Erhaltene Strategie-Instanz: {type(strategy_ranged).__name__ if strategy_ranged else 'None'}")
        assert isinstance(strategy_ranged, BasicRangedStrategy)

        strategy_support = get_ai_strategy_instance(actor_support, dummy_combat_list)
        print(f"Für '{actor_support.name}' (Strategie-ID: '{getattr(actor_support.base_template, 'ai_strategy_id', 'N/A')}'): "
              f"Erhaltene Strategie-Instanz: {type(strategy_support).__name__ if strategy_support else 'None'}")
        assert isinstance(strategy_support, SupportCasterStrategy)
        
        strategy_no_ai = get_ai_strategy_instance(actor_no_ai, dummy_combat_list)
        print(f"Für '{actor_no_ai.name}' (Strategie-ID: '{getattr(actor_no_ai.base_template, 'ai_strategy_id', 'N/A')}'): "
              f"Erhaltene Strategie-Instanz: {type(strategy_no_ai).__name__ if strategy_no_ai else 'None'}")
        assert strategy_no_ai is None

        strategy_unknown_ai = get_ai_strategy_instance(actor_unknown_ai, dummy_combat_list)
        print(f"Für '{actor_unknown_ai.name}' (Strategie-ID: '{getattr(actor_unknown_ai.base_template, 'ai_strategy_id', 'N/A')}'): "
              f"Erhaltene Strategie-Instanz: {type(strategy_unknown_ai).__name__ if strategy_unknown_ai else 'None'}")
        assert strategy_unknown_ai is None


    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in ai_dispatcher.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in ai_dispatcher.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- AI Dispatcher-Tests abgeschlossen ---")