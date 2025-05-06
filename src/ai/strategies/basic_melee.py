import random
import logging
import typing

# Importiere notwendige Klassen und Funktionen
try:
    from src.game_logic.entities import CharacterInstance
    from src.definitions import loader # Um Skill-Details zu bekommen
except ImportError:
    print("WARNUNG: basic_melee.py - Module nicht direkt geladen (für Test).")
    # Fallback für isolierten Test (vereinfacht)
    from ...game_logic.entities import CharacterInstance
    from ...definitions import loader


logger = logging.getLogger(__name__)

# Type Hint für die Rückgabe: (Skill-ID oder None, Ziel-Instanz oder None)
AIAction = typing.Tuple[typing.Optional[str], typing.Optional[CharacterInstance]]

def choose_action(actor: CharacterInstance, possible_targets: typing.List[CharacterInstance]) -> AIAction:
    """
    Sehr einfache AI-Strategie für Nahkämpfer.
    Wählt den ersten verfügbaren Angriffs-Skill und ein zufälliges Ziel.
    Priorisiert kostenlose Skills.

    Args:
        actor: Die CharacterInstance, die die Aktion ausführt.
        possible_targets: Eine Liste von möglichen Zielen (CharacterInstances).

    Returns:
        Ein Tupel (skill_id, target_instance) oder (None, None), wenn keine Aktion möglich ist.
    """
    logger.debug(f"AI Strategy 'basic_melee' für '{actor.name}' wird ausgeführt.")

    # Filtere nur lebende Ziele heraus
    living_targets = [target for target in possible_targets if target.is_alive()]

    if not living_targets:
        logger.warning(f"'{actor.name}' hat keine lebenden Ziele für 'basic_melee'.")
        return None, None # Keine Aktion möglich

    # Finde einen nutzbaren Skill (Priorität: kostenloser Angriff)
    chosen_skill_id: typing.Optional[str] = None

    # 1. Suche nach kostenlosen Angriffs-Skills
    for skill_id in actor.definition.skill_ids:
        skill = loader.get_skill(skill_id)
        if not skill: continue # Skill nicht gefunden

        is_attack = any(eff.get("type") == "DAMAGE" for eff in skill.effects)
        cost_amount = skill.get_cost_amount()

        if is_attack and cost_amount == 0:
             chosen_skill_id = skill_id
             logger.debug(f"Kostenloser Angriffs-Skill gefunden: '{chosen_skill_id}'")
             break # Nimm den ersten gefundenen

    # 2. Wenn kein kostenloser gefunden, suche nach bezahlbarem Angriffs-Skill
    if not chosen_skill_id:
        for skill_id in actor.definition.skill_ids:
            skill = loader.get_skill(skill_id)
            if not skill: continue

            is_attack = any(eff.get("type") == "DAMAGE" for eff in skill.effects)
            cost_resource = skill.get_cost_resource()
            cost_amount = skill.get_cost_amount()

            # Prüfe, ob Skill ein Angriff ist UND ob Kosten gedeckt sind
            if is_attack and actor.can_afford_cost(cost_resource, cost_amount):
                chosen_skill_id = skill_id
                logger.debug(f"Bezahlbarer Angriffs-Skill gefunden: '{chosen_skill_id}'")
                break # Nimm den ersten gefundenen

    # Wenn immer noch kein Skill gefunden wurde
    if not chosen_skill_id:
        logger.warning(f"'{actor.name}' konnte keinen passenden Skill für 'basic_melee' finden oder bezahlen.")
        return None, None

    # Wähle ein zufälliges lebendes Ziel
    chosen_target = random.choice(living_targets)
    logger.info(f"AI 'basic_melee' wählt Aktion für '{actor.name}': Skill='{chosen_skill_id}', Ziel='{chosen_target.name}'")

    return chosen_skill_id, chosen_target


# --- Testblock ---
if __name__ == '__main__':
    try:
        # Setup für Tests (Logging, Pfad, Loader)
        import sys
        from pathlib import Path
        project_dir = Path(__file__).parent.parent.parent.parent # Annahme: Diese Datei ist in src/ai/strategies/
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging
        setup_logging()
        # Re-importiere loader nach Pfadanpassung
        from src.definitions import loader
        from src.game_logic.entities import CharacterInstance # Importiere CharacterInstance für Tests
    except ImportError as e:
        print(f"FEHLER bei Test-Setup in basic_melee.py: {e}")
        exit(1)

    print("\n--- AI Strategy Test: basic_melee ---")

    # Lade Definitionen
    goblin_def = loader.get_opponent("goblin_lv1") # Hat 'basic_strike_phys' (kostenlos)
    krieger_def = loader.get_character_class("krieger") # Ziel

    if not goblin_def or not krieger_def:
         print("FEHLER: Notwendige Definitionen für Test nicht geladen.")
         exit(1)

    # Erstelle Instanzen
    goblin_actor = CharacterInstance(goblin_def)
    krieger_target = CharacterInstance(krieger_def)
    # Füge ein weiteres mögliches (aber vielleicht totes) Ziel hinzu
    krieger_target_2 = CharacterInstance(krieger_def)
    krieger_target_2.name = "Krieger (Besiegt)"
    krieger_target_2.take_damage(krieger_target_2.max_hp + 10) # Besiegen

    possible_targets = [krieger_target, krieger_target_2]
    print(f"\nGoblin (Actor): {goblin_actor}")
    print(f"Mögliche Ziele: {[t.name for t in possible_targets]} (Status: {[t.is_alive() for t in possible_targets]})")

    # Führe die Strategie aus
    skill_choice, target_choice = choose_action(goblin_actor, possible_targets)

    print(f"\nGewählte Aktion:")
    print(f"  Skill ID: {skill_choice}")
    print(f"  Ziel: {target_choice.name if target_choice else 'None'}")

    # Prüfungen
    assert skill_choice == "basic_strike_phys", f"Falscher Skill gewählt: {skill_choice}"
    assert target_choice is krieger_target, "Falsches Ziel gewählt (sollte der lebende Krieger sein)."

    print("\nTest mit Gegner ohne kostenlosen Skill (Goblin-Krieger):")
    goblin_warrior_def = loader.get_opponent("goblin_krieger_lv2") # Hat 'basic_strike_phys', 'power_strike' (Stamina 20)
    if not goblin_warrior_def: print("FEHLER: Goblin-Krieger nicht geladen."); exit(1)

    goblin_warrior_actor = CharacterInstance(goblin_warrior_def) # Genug Stamina (80)
    krieger_target_3 = CharacterInstance(krieger_def)
    possible_targets_2 = [krieger_target_3]
    print(f"Goblin-Krieger (Actor): {goblin_warrior_actor}")

    skill_choice_gw, target_choice_gw = choose_action(goblin_warrior_actor, possible_targets_2)
    print(f"Gewählte Aktion (Goblin-Krieger): Skill={skill_choice_gw}, Ziel={target_choice_gw.name if target_choice_gw else 'None'}")
    # Sollte basic_strike_phys wählen, da es der erste Skill ist und kostenlos ist.
    assert skill_choice_gw == "basic_strike_phys"

    print("\nTest mit Gegner ohne genug Ressourcen für teuren Skill:")
    goblin_warrior_actor.current_stamina = 10 # Nicht genug für Power Strike (20)
    print(f"Goblin-Krieger (Actor) mit wenig Stamina: {goblin_warrior_actor}")
    skill_choice_gw_low_stam, target_choice_gw_low_stam = choose_action(goblin_warrior_actor, possible_targets_2)
    print(f"Gewählte Aktion (Wenig Stamina): Skill={skill_choice_gw_low_stam}, Ziel={target_choice_gw_low_stam.name if target_choice_gw_low_stam else 'None'}")
    # Sollte immer noch basic_strike_phys wählen.
    assert skill_choice_gw_low_stam == "basic_strike_phys"


    print("\nAlle AI basic_melee Tests erfolgreich.")

