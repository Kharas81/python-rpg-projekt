import logging
import typing

# Importiere die spezifischen Strategie-Module
try:
    from src.ai.strategies import basic_melee
    from src.ai.strategies import basic_ranged
    from src.ai.strategies import support_caster # NEU importiert
    from src.game_logic.entities import CharacterInstance
except ImportError:
    print("WARNUNG: ai_dispatcher.py - Module nicht direkt geladen (für Test).")
    from .strategies import basic_melee
    from .strategies import basic_ranged
    from .strategies import support_caster # NEU importiert
    from ..game_logic.entities import CharacterInstance


logger = logging.getLogger(__name__)

AIAction = typing.Tuple[typing.Optional[str], typing.Optional[CharacterInstance]]

# Mapping von Strategie-Namen zu Funktionen aktualisieren
STRATEGY_MAP: typing.Dict[str, typing.Callable[[CharacterInstance, typing.List[CharacterInstance]], AIAction]] = {
    "basic_melee": basic_melee.choose_action,
    "basic_ranged": basic_ranged.choose_action,
    "support_caster": support_caster.choose_action, # NEU hinzugefügt
}

DEFAULT_STRATEGY_FUNC = basic_melee.choose_action
DEFAULT_STRATEGY_NAME = "basic_melee"

def get_ai_action(actor: CharacterInstance, possible_targets: typing.List[CharacterInstance]) -> AIAction:
    """Wählt die passende AI-Strategie aus und führt sie aus."""
    # Implementierung bleibt gleich wie zuvor...
    strategy_name = getattr(actor.definition, 'ai_strategy', None)
    strategy_func = None; chosen_strategy_name = "None"
    if strategy_name:
        strategy_func = STRATEGY_MAP.get(strategy_name)
        if strategy_func: chosen_strategy_name = strategy_name; logger.debug(f"Dispatcher: Verwende Strategie '{strategy_name}' für '{actor.name}'.")
        else: logger.warning(f"Dispatcher: Unbekannte Strategie '{strategy_name}' -> Fallback '{DEFAULT_STRATEGY_NAME}'."); strategy_func = DEFAULT_STRATEGY_FUNC; chosen_strategy_name = f"{DEFAULT_STRATEGY_NAME} (Fallback)"
    else: logger.warning(f"Dispatcher: Keine AI-Strategie -> Fallback '{DEFAULT_STRATEGY_NAME}'."); strategy_func = DEFAULT_STRATEGY_FUNC; chosen_strategy_name = f"{DEFAULT_STRATEGY_NAME} (Fallback)"
    if strategy_func:
        try: return strategy_func(actor, possible_targets)
        except Exception as e: logger.error(f"Fehler bei AI-Strategie '{chosen_strategy_name}' für '{actor.name}': {e}", exc_info=True); return None, None
    else: logger.error(f"Dispatcher: Konnte keine Strategiefunktion finden für '{actor.name}'."); return None, None


# --- Testblock (Erweitert für neue Strategie) ---
if __name__ == '__main__':
    try:
        import sys; from pathlib import Path
        project_dir = Path(__file__).parent.parent.parent; sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging; setup_logging()
        from src.definitions import loader
        from src.game_logic.entities import CharacterInstance
        from src.definitions.character import Character as CharacterDefinition
    except ImportError as e: print(f"FEHLER bei Test-Setup in ai_dispatcher.py: {e}"); exit(1)

    print("\n--- AI Dispatcher Test (inkl. support_caster) ---")

    # Lade Definitionen
    goblin_def = loader.get_opponent("goblin_lv1")             # ai_strategy: "basic_melee"
    archer_def = loader.get_opponent("skelett_bogenschuetze_lv2") # ai_strategy: "basic_ranged"
    shaman_def = loader.get_opponent("goblin_schamane_lv3")     # ai_strategy: "support_caster"
    krieger_def = loader.get_character_class("krieger")       # Ziel

    if not all([goblin_def, archer_def, shaman_def, krieger_def]):
         print("FEHLER: Notwendige Definitionen für Test nicht geladen."); exit(1)

    # Erstelle Instanzen
    goblin_actor = CharacterInstance(goblin_def)
    archer_actor = CharacterInstance(archer_def)
    shaman_actor = CharacterInstance(shaman_def) # Mana=100
    krieger_target = CharacterInstance(krieger_def)
    possible_targets = [krieger_target]

    print(f"\nTeste Dispatcher mit Goblin ({goblin_def.ai_strategy}):")
    action1 = get_ai_action(goblin_actor, possible_targets)
    print(f"  -> Ergebnis: Skill='{action1[0]}', Ziel='{action1[1].name if action1[1] else 'None'}'")
    assert action1[0] == "basic_strike_phys"

    print(f"\nTeste Dispatcher mit Bogenschütze ({archer_def.ai_strategy}):")
    action_archer = get_ai_action(archer_actor, possible_targets)
    print(f"  -> Ergebnis: Skill='{action_archer[0]}', Ziel='{action_archer[1].name if action_archer[1] else 'None'}'")
    assert action_archer[0] == "basic_shot_phys"

    print(f"\nTeste Dispatcher mit Schamane ({shaman_def.ai_strategy}) - Gesund:")
    action_shaman1 = get_ai_action(shaman_actor, possible_targets)
    print(f"  -> Ergebnis: Skill='{action_shaman1[0]}', Ziel='{action_shaman1[1].name if action_shaman1[1] else 'None'}'")
    # Erwartet: Weakening Curse auf Krieger
    assert action_shaman1[0] == "weakening_curse"
    assert action_shaman1[1] is krieger_target

    print(f"\nTeste Dispatcher mit Schamane ({shaman_def.ai_strategy}) - Verletzt:")
    shaman_actor.current_hp = shaman_actor.max_hp * 0.4 # Unter 50% HP
    action_shaman2 = get_ai_action(shaman_actor, possible_targets)
    print(f"  -> Ergebnis: Skill='{action_shaman2[0]}', Ziel='{action_shaman2[1].name if action_shaman2[1] else 'None'}'")
    # Erwartet: Heal Lesser auf sich selbst
    assert action_shaman2[0] == "heal_lesser"
    assert action_shaman2[1] is shaman_actor

    print("\nAlle AI Dispatcher Tests (inkl. support_caster) erfolgreich.")

