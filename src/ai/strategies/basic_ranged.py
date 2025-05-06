import random
import logging
import typing

# Importiere notwendige Klassen und Funktionen
try:
    from src.game_logic.entities import CharacterInstance
    from src.definitions import loader # Um Skill-Details zu bekommen
except ImportError:
    print("WARNUNG: basic_ranged.py - Module nicht direkt geladen (für Test).")
    from ...game_logic.entities import CharacterInstance
    from ...definitions import loader

logger = logging.getLogger(__name__)

# Type Hint für die Rückgabe: (Skill-ID oder None, Ziel-Instanz oder None)
AIAction = typing.Tuple[typing.Optional[str], typing.Optional[CharacterInstance]]

def choose_action(actor: CharacterInstance, possible_targets: typing.List[CharacterInstance]) -> AIAction:
    """
    Sehr einfache AI-Strategie für Fernkämpfer.
    Wählt den ersten verfügbaren (bevorzugt kostenlosen) Angriffs-Skill
    und ein zufälliges lebendes Ziel.

    Args:
        actor: Die CharacterInstance, die die Aktion ausführt.
        possible_targets: Eine Liste von möglichen Zielen (CharacterInstances).

    Returns:
        Ein Tupel (skill_id, target_instance) oder (None, None), wenn keine Aktion möglich ist.
    """
    logger.debug(f"AI Strategy 'basic_ranged' für '{actor.name}' wird ausgeführt.")

    living_targets = [target for target in possible_targets if target.is_alive()]
    if not living_targets:
        logger.warning(f"'{actor.name}' hat keine lebenden Ziele für 'basic_ranged'.")
        return None, None

    chosen_skill_id: typing.Optional[str] = None

    # Suche nach nutzbarem Angriffs-Skill (kostenlos bevorzugt)
    # Annahme: Jeder Schadens-Skill dieses Actors ist ein "Fernkampf"-Skill für diese Strategie
    free_attack_skill: typing.Optional[str] = None
    payable_attack_skill: typing.Optional[str] = None

    for skill_id in actor.definition.skill_ids:
        skill = loader.get_skill(skill_id)
        if not skill: continue

        is_attack = any(eff.get("type") == "DAMAGE" for eff in skill.effects)
        if not is_attack: continue # Überspringe Nicht-Angriffs-Skills

        cost_resource = skill.get_cost_resource()
        cost_amount = skill.get_cost_amount()

        if cost_amount == 0: # Kostenloser Skill gefunden
             if free_attack_skill is None: # Nimm den ersten kostenlosen
                  free_attack_skill = skill_id
        elif actor.can_afford_cost(cost_resource, cost_amount): # Bezahlbarer Skill gefunden
             if payable_attack_skill is None: # Nimm den ersten bezahlbaren
                  payable_attack_skill = skill_id

    # Wähle primär den kostenlosen, sonst den bezahlbaren
    if free_attack_skill:
        chosen_skill_id = free_attack_skill
        logger.debug(f"Kostenloser Angriffs-Skill für 'basic_ranged' gefunden: '{chosen_skill_id}'")
    elif payable_attack_skill:
        chosen_skill_id = payable_attack_skill
        logger.debug(f"Bezahlbarer Angriffs-Skill für 'basic_ranged' gefunden: '{chosen_skill_id}'")
    else:
        logger.warning(f"'{actor.name}' konnte keinen passenden Skill für 'basic_ranged' finden oder bezahlen.")
        return None, None

    # Wähle ein zufälliges lebendes Ziel
    chosen_target = random.choice(living_targets)
    logger.info(f"AI 'basic_ranged' wählt Aktion für '{actor.name}': Skill='{chosen_skill_id}', Ziel='{chosen_target.name}'")

    return chosen_skill_id, chosen_target


# --- Testblock ---
if __name__ == '__main__':
    try:
        import sys
        from pathlib import Path
        project_dir = Path(__file__).parent.parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging
        setup_logging()
        from src.definitions import loader
        from src.game_logic.entities import CharacterInstance
    except ImportError as e:
        print(f"FEHLER bei Test-Setup in basic_ranged.py: {e}")
        exit(1)

    print("\n--- AI Strategy Test: basic_ranged ---")

    # Lade Definitionen
    archer_def = loader.get_opponent("skelett_bogenschuetze_lv2") # Hat 'basic_shot_phys' (kostenlos)
    krieger_def = loader.get_character_class("krieger") # Ziel

    if not archer_def or not krieger_def:
         print("FEHLER: Notwendige Definitionen für Test nicht geladen.")
         exit(1)

    # Erstelle Instanzen
    archer_actor = CharacterInstance(archer_def)
    krieger_target = CharacterInstance(krieger_def)
    krieger_target_dead = CharacterInstance(krieger_def)
    krieger_target_dead.name = "Krieger (Tot)"
    krieger_target_dead.take_damage(999) # Sicherstellen, dass er tot ist

    possible_targets = [krieger_target, krieger_target_dead]
    print(f"\nBogenschütze (Actor): {archer_actor}")
    print(f"Mögliche Ziele: {[t.name for t in possible_targets]} (Status: {[t.is_alive() for t in possible_targets]})")

    # Führe die Strategie aus
    skill_choice, target_choice = choose_action(archer_actor, possible_targets)

    print(f"\nGewählte Aktion:")
    print(f"  Skill ID: {skill_choice}")
    print(f"  Ziel: {target_choice.name if target_choice else 'None'}")

    # Prüfungen
    assert skill_choice == "basic_shot_phys", f"Falscher Skill gewählt: {skill_choice}"
    assert target_choice is krieger_target, "Falsches Ziel gewählt (sollte der lebende Krieger sein)."

    # Test mit keinen lebenden Zielen
    print("\nTest ohne lebende Ziele:")
    skill_choice_no_target, target_choice_no_target = choose_action(archer_actor, [krieger_target_dead])
    assert skill_choice_no_target is None, "Sollte keinen Skill wählen ohne Ziel."
    assert target_choice_no_target is None, "Sollte kein Ziel wählen ohne Ziel."
    print("  -> Korrekt keine Aktion gewählt.")


    print("\nAlle AI basic_ranged Tests erfolgreich.")

