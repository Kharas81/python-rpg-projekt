import random
import logging
import typing

# Importiere notwendige Klassen und Funktionen
try:
    from src.game_logic.entities import CharacterInstance
    from src.definitions import loader # Um Skill-Details zu bekommen
except ImportError:
    print("WARNUNG: support_caster.py - Module nicht direkt geladen (für Test).")
    from ...game_logic.entities import CharacterInstance
    from ...definitions import loader

logger = logging.getLogger(__name__)

# Type Hint für die Rückgabe: (Skill-ID oder None, Ziel-Instanz oder None)
AIAction = typing.Tuple[typing.Optional[str], typing.Optional[CharacterInstance]]

# --- Konfiguration für die Strategie (könnte später in eine Config-Datei) ---
HEAL_THRESHOLD_PERCENT = 0.5 # Bei 50% HP oder weniger heilen

def choose_action(actor: CharacterInstance,
                  possible_targets: typing.List[CharacterInstance],
                  allies: typing.Optional[typing.List[CharacterInstance]] = None # Vorerst ungenutzt
                  ) -> AIAction:
    """
    AI-Strategie für einen unterstützenden Caster (z.B. Goblin Schamane).
    Priorisiert Selbstheilung, dann Debuffs, dann Angriff.

    Args:
        actor: Die CharacterInstance, die die Aktion ausführt.
        possible_targets: Eine Liste von möglichen gegnerischen Zielen.
        allies: Eine Liste von Verbündeten (inkl. actor selbst). Vorerst ignoriert.

    Returns:
        Ein Tupel (skill_id, target_instance) oder (None, None), wenn keine Aktion möglich ist.
    """
    logger.debug(f"AI Strategy 'support_caster' für '{actor.name}' wird ausgeführt.")

    living_targets = [target for target in possible_targets if target.is_alive()]
    # TODO: Später living_allies berücksichtigen

    # --- Priorität 1: Selbstheilung ---
    heal_skill_id = "heal_lesser" # Hardcoded für Goblin Schamane
    heal_skill = loader.get_skill(heal_skill_id)
    if heal_skill and heal_skill_id in actor.definition.skill_ids: # Hat der Actor den Skill?
        # Prüfe, ob HP niedrig sind UND der Skill bezahlbar ist
        if actor.current_hp / actor.max_hp <= HEAL_THRESHOLD_PERCENT:
            if actor.can_afford_cost(heal_skill.get_cost_resource(), heal_skill.get_cost_amount()):
                logger.info(f"AI '{actor.name}': HP niedrig ({actor.current_hp}/{actor.max_hp}), wählt Selbstheilung mit '{heal_skill_id}'.")
                # Ziel ist der Actor selbst
                return heal_skill_id, actor
            else:
                 logger.debug(f"'{actor.name}' würde gerne heilen, hat aber nicht genug Ressourcen.")
        else:
             logger.debug(f"'{actor.name}' HP sind ok ({actor.current_hp}/{actor.max_hp}), keine Heilung nötig.")
    # TODO: Später Logik für das Heilen von Verbündeten hinzufügen

    # --- Priorität 2: Debuff (Weakening Curse) ---
    debuff_skill_id = "weakening_curse"
    debuff_effect_id = "WEAKENED" # Welchen Effekt dieser Skill anwendet
    debuff_skill = loader.get_skill(debuff_skill_id)
    if debuff_skill and debuff_skill_id in actor.definition.skill_ids and living_targets:
        # Prüfe, ob Skill bezahlbar ist
        if actor.can_afford_cost(debuff_skill.get_cost_resource(), debuff_skill.get_cost_amount()):
            # Finde Ziele, die den Debuff noch NICHT haben
            targets_without_debuff = [t for t in living_targets if not t.has_status_effect(debuff_effect_id)]
            if targets_without_debuff:
                chosen_target = random.choice(targets_without_debuff)
                logger.info(f"AI '{actor.name}': Wählt Debuff '{debuff_skill_id}' auf Ziel '{chosen_target.name}'.")
                return debuff_skill_id, chosen_target
            else:
                 logger.debug(f"Alle lebenden Ziele haben bereits '{debuff_effect_id}'.")
        else:
             logger.debug(f"'{actor.name}' kann sich '{debuff_skill_id}' nicht leisten.")


    # --- Priorität 3: Angriff (Basic Magic Bolt) ---
    attack_skill_id = "basic_magic_bolt"
    attack_skill = loader.get_skill(attack_skill_id)
    if attack_skill and attack_skill_id in actor.definition.skill_ids and living_targets:
         # Prüfe, ob Skill bezahlbar ist
         if actor.can_afford_cost(attack_skill.get_cost_resource(), attack_skill.get_cost_amount()):
              chosen_target = random.choice(living_targets)
              logger.info(f"AI '{actor.name}': Wählt Angriff '{attack_skill_id}' auf Ziel '{chosen_target.name}'.")
              return attack_skill_id, chosen_target
         else:
              logger.debug(f"'{actor.name}' kann sich '{attack_skill_id}' nicht leisten.")

    # --- Fallback: Keine Aktion ---
    logger.warning(f"AI '{actor.name}' konnte keine geeignete Aktion in 'support_caster' finden.")
    return None, None


# --- Testblock ---
if __name__ == '__main__':
    try:
        import sys
        from pathlib import Path
        project_dir = Path(__file__).parent.parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging; setup_logging()
        from src.definitions import loader
        from src.game_logic.entities import CharacterInstance
        from src.game_logic.effects import StatusEffect # Für manuelles Hinzufügen im Test
    except ImportError as e:
        print(f"FEHLER bei Test-Setup in support_caster.py: {e}"); exit(1)

    print("\n--- AI Strategy Test: support_caster ---")

    # Lade Definitionen
    shaman_def = loader.get_opponent("goblin_schamane_lv3") # Skills: bolt, weaken, heal | Mana 100
    krieger_def = loader.get_character_class("krieger") # Ziel
    if not shaman_def or not krieger_def: print("FEHLER: Definitionen nicht geladen."); exit(1)

    # Erstelle Instanzen
    shaman_actor = CharacterInstance(shaman_def)
    target1 = CharacterInstance(krieger_def)
    target2 = CharacterInstance(krieger_def); target2.name = "Krieger Zwo"
    possible_targets = [target1, target2]

    print(f"\nTest 1: Schamane ist gesund, Ziele sind gesund.")
    # Erwartet: Weakening Curse auf Target1 oder Target2
    skill_choice, target_choice = choose_action(shaman_actor, possible_targets)
    print(f"  -> Aktion: Skill='{skill_choice}', Ziel='{target_choice.name if target_choice else 'None'}'")
    assert skill_choice == "weakening_curse"
    assert target_choice in possible_targets

    print(f"\nTest 2: Schamane ist gesund, Target1 hat schon WEAKENED.")
    # Manuell Effekt hinzufügen für Test
    target1.add_status_effect({"id": "WEAKENED", "duration": 2, "potency": 3})
    print(f"Target1 Status: {target1}")
    # Erwartet: Weakening Curse auf Target2
    skill_choice, target_choice = choose_action(shaman_actor, possible_targets)
    print(f"  -> Aktion: Skill='{skill_choice}', Ziel='{target_choice.name if target_choice else 'None'}'")
    assert skill_choice == "weakening_curse"
    assert target_choice is target2
    target1.remove_status_effect("WEAKENED") # Aufräumen

    print(f"\nTest 3: Schamane ist gesund, beide Ziele haben WEAKENED.")
    target1.add_status_effect({"id": "WEAKENED", "duration": 2, "potency": 3})
    target2.add_status_effect({"id": "WEAKENED", "duration": 2, "potency": 3})
    # Erwartet: Basic Magic Bolt auf Target1 oder Target2
    skill_choice, target_choice = choose_action(shaman_actor, possible_targets)
    print(f"  -> Aktion: Skill='{skill_choice}', Ziel='{target_choice.name if target_choice else 'None'}'")
    assert skill_choice == "basic_magic_bolt"
    assert target_choice in possible_targets
    target1.remove_status_effect("WEAKENED"); target2.remove_status_effect("WEAKENED") # Aufräumen

    print(f"\nTest 4: Schamane ist verletzt (unter 50%).")
    shaman_actor.current_hp = shaman_actor.max_hp * 0.4 # Setze HP auf 40%
    print(f"Schamane Status: {shaman_actor}")
    # Erwartet: Heal Lesser auf sich selbst
    skill_choice, target_choice = choose_action(shaman_actor, possible_targets)
    print(f"  -> Aktion: Skill='{skill_choice}', Ziel='{target_choice.name if target_choice else 'None'}'")
    assert skill_choice == "heal_lesser"
    assert target_choice is shaman_actor
    shaman_actor.current_hp = shaman_actor.max_hp # Wieder voll heilen für nächsten Test

    print(f"\nTest 5: Schamane verletzt, aber nicht genug Mana zum Heilen.")
    shaman_actor.current_hp = shaman_actor.max_hp * 0.4
    shaman_actor.current_mana = 5 # Heal Lesser kostet 15
    print(f"Schamane Status: {shaman_actor}")
    # Erwartet: Weakening Curse (kostet 15, auch nicht genug) -> Basic Magic Bolt (kostet 1)
    skill_choice, target_choice = choose_action(shaman_actor, possible_targets)
    print(f"  -> Aktion: Skill='{skill_choice}', Ziel='{target_choice.name if target_choice else 'None'}'")
    assert skill_choice == "basic_magic_bolt" # Kann sich nur Bolt leisten
    assert target_choice in possible_targets
    shaman_actor.current_hp = shaman_actor.max_hp; shaman_actor.current_mana = shaman_actor.max_mana # Reset

    print("\nAlle AI support_caster Tests erfolgreich.")

