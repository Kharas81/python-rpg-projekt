import argparse
import sys
import time # Für kleine Pausen
from typing import Optional, List

# Importiere den Loader, Modelle und die Spiellogik-Klassen
try:
    from definitions import loader
    from definitions.models import SkillDefinition
    from game_logic.character import Character
    from game_logic.enemy import Enemy
    from game_logic.combat import CombatEncounter, Combatant
except ImportError as e:
    # Fallback
    try:
        from src.definitions import loader
        from src.definitions.models import SkillDefinition
        from src.game_logic.character import Character
        from src.game_logic.enemy import Enemy
        from src.game_logic.combat import CombatEncounter, Combatant
    except ImportError:
        print("Fehler: Konnte Definitions- oder game_logic-Module nicht importieren.", file=sys.stderr)
        # ... (Rest der Fehlermeldung wie gehabt)
        sys.exit(1)

def _get_validated_input(prompt: str, max_value: int) -> int:
    """ Fragt den Benutzer nach einer Zahl zwischen 1 und max_value. """
    while True:
        try:
            choice = input(prompt)
            value = int(choice)
            if 1 <= value <= max_value:
                return value
            else:
                print(f"Ungültige Eingabe. Bitte eine Zahl zwischen 1 und {max_value} eingeben.")
        except ValueError:
            print("Ungültige Eingabe. Bitte eine Zahl eingeben.")
        except EOFError: # Falls Input-Stream unerwartet endet
             print("\nEingabe abgebrochen.")
             return -1 # Signal für Abbruch

def _handle_player_turn(player: Character, combat: CombatEncounter):
    """ Verwaltet die Aktionen des Spielers während seines Zuges. """
    print("\nDu bist am Zug!")

    # 1. Verfügbare Skills anzeigen (die genug Ressourcen haben)
    available_skills: List[Tuple[int, SkillDefinition]] = []
    print("Verfügbare Skills:")
    skill_index = 1
    for skill in player.get_known_skills():
        if not skill: continue # Überspringe, falls Skill nicht geladen wurde

        cost = skill.cost
        can_afford = True
        resource_str = ""
        if cost.resource and cost.amount > 0:
             current_res = player.get_combat_stat(f"CURRENT_{cost.resource.upper()}")
             if current_res is None or current_res < cost.amount:
                 can_afford = False
             resource_str = f"({cost.amount} {cost.resource})"

        if can_afford:
            print(f"  {skill_index}. {skill.name} {resource_str}")
            available_skills.append((skill_index, skill))
            skill_index += 1
        else:
             print(f"  -- {skill.name} {resource_str} (Nicht genug Ressourcen!) --")

    if not available_skills:
        print("Du hast keine einsetzbaren Skills!")
        # Spieler passt diese Runde / oder Standardangriff?
        # Vorerst: passt
        print(f"{player.name} passt.")
        time.sleep(1) # Kurze Pause
        return

    # 2. Skill auswählen
    prompt = f"Wähle einen Skill (1-{len(available_skills)}): "
    chosen_skill_index = _get_validated_input(prompt, len(available_skills))
    if chosen_skill_index == -1: return # Eingabe abgebrochen

    # Finde den ausgewählten Skill
    selected_skill: Optional[SkillDefinition] = None
    for index, skill_def in available_skills:
        if index == chosen_skill_index:
            selected_skill = skill_def
            break

    if not selected_skill:
         print("Interner Fehler: Ausgewählter Skill nicht gefunden.")
         return

    # 3. Ziel auswählen (falls nötig)
    target: Optional[Combatant] = None
    if selected_skill.target_type == "SELF":
        target = player
        print(f"Ziel: {target.name}")
    elif selected_skill.target_type in ["ENEMY_SINGLE", "AREA_ENEMY"]: # AREA_ENEMY wählt fürs Erste auch nur ein Hauptziel
        living_enemies = combat.get_living_enemies()
        if not living_enemies:
             print("Keine Ziele verfügbar!")
             return

        print("Wähle ein Ziel:")
        for i, enemy in enumerate(living_enemies):
            print(f"  {i+1}. {enemy.name} (Lvl {enemy.level}) - HP: {enemy.get_combat_stat('CURRENT_HP')}/{enemy.get_combat_stat('MAX_HP')}")

        prompt = f"Wähle ein Ziel (1-{len(living_enemies)}): "
        chosen_target_index = _get_validated_input(prompt, len(living_enemies))
        if chosen_target_index == -1: return # Eingabe abgebrochen

        target = living_enemies[chosen_target_index - 1] # Index ist 0-basiert

    elif selected_skill.target_type == "ALLY_SINGLE":
         # TODO: Verbündeten-Auswahl implementieren, falls es welche gibt
         print("Zielfindung für Verbündete noch nicht implementiert. Ziel: Selbst.")
         target = player # Vorerst auf sich selbst
    else:
         print(f"Unbekannter Zieltyp '{selected_skill.target_type}'. Aktion abgebrochen.")
         return

    if not target:
         print("Konnte kein gültiges Ziel bestimmen.")
         return

    # 4. Skill anwenden
    combat.apply_skill(player, target, selected_skill)
    time.sleep(1) # Kurze Pause nach der Aktion


def run_manual_mode():
    """Führt die Logik für den manuellen Spielmodus aus, inkl. Testkampf."""
    print("\n--- Manueller Modus gestartet ---")
    player: Optional[Character] = None

    try:
        # --- 1. Charakter erstellen ---
        player = Character(name="Held", class_id="warrior") # Oder andere Klasse zum Testen wählen
        print(f"\nCharakter '{player.name}' ({player.character_class.name}) wurde erstellt.")

        # --- 2. Gegner erstellen ---
        enemy_id_to_fight = "goblin_lvl1" # Oder anderen Gegner wählen
        enemy_def = loader.get_enemy(enemy_id_to_fight)
        if not enemy_def:
             print(f"FEHLER: Gegnerdefinition '{enemy_id_to_fight}' nicht gefunden.")
             return
        print(f"\nEin wilder '{enemy_def.name}' erscheint!")
        opponent = Enemy(enemy_id=enemy_id_to_fight)

        # --- 3. Kampf starten ---
        combat = CombatEncounter(player=player, enemies=[opponent])
        combat.start_combat()

        # --- 4. Interaktive Kampfschleife ---
        while not combat.is_combat_over():
            combat.display_combat_status()
            current_combatant: Optional[Combatant] = combat.get_current_combatant()

            if current_combatant is None: break # Sicherheit

            # --- Spieler-Zug ---
            if current_combatant is player:
                _handle_player_turn(player, combat)

            # --- Gegner-Zug (immer noch vereinfacht) ---
            elif isinstance(current_combatant, Enemy):
                print(f"\n{current_combatant.name} ist am Zug.")
                time.sleep(0.5) # Kurze Denkpause ;)
                target_player = combat.player
                if target_player.is_alive():
                    enemy_skills = current_combatant.get_known_skills()
                    # Einfache KI: Wähle einen zufälligen, einsetzbaren Skill
                    usable_skills = []
                    for skill in enemy_skills:
                        if skill:
                             cost = skill.cost
                             can_afford = True
                             if cost.resource and cost.amount > 0:
                                 current_res = current_combatant.get_combat_stat(f"CURRENT_{cost.resource.upper()}")
                                 if current_res is None or current_res < cost.amount:
                                     can_afford = False
                             if can_afford:
                                  usable_skills.append(skill)

                    if usable_skills:
                        skill_to_use = random.choice(usable_skills)
                        combat.apply_skill(current_combatant, target_player, skill_to_use)
                    else:
                        print(f"{current_combatant.name} hat keine einsetzbaren Skills und passt.")
                else:
                     print("Spieler ist bereits besiegt.")

                time.sleep(1) # Pause nach Gegnerzug

            # --- Nächster Zug vorbereiten ---
            if not combat.is_combat_over():
                 combat.next_turn()


        # --- 5. Kampfende ---
        print("\n--- Kampf beendet ---")
        # (Restliche Ausgabe wie gehabt)
        if combat.status == "PLAYER_VICTORY" and player:
             print(f"Glückwunsch, {player.name}!")
        elif combat.status == "PLAYER_DEFEAT":
             print("Leider verloren.")
        else:
             print("Kampf endete unerwartet.")


    except ValueError as e:
        print(f"\nFehler bei der Initialisierung: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nEin unerwarteter Fehler ist im manuellen Modus aufgetreten: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

    print("\n--- Manueller Modus Ende ---")


def run_auto_mode():
    """Führt die Logik für den automatisierten Modus aus."""
    print("\n--- Automatischer Modus gestartet ---")
    # TODO: Implement auto mode logic
    print("\n--- Automatischer Modus Ende ---")


def main():
    """Hauptfunktion: Lädt Definitionen und startet den gewählten Modus."""
    loader.load_definitions()
    parser = argparse.ArgumentParser(description="Startet das Python RPG Projekt.")
    parser.add_argument(
        '--mode', type=str, choices=['manual', 'auto'], required=True,
        help="Der Betriebsmodus: 'manual' für interaktives Spiel, 'auto' für automatisierte Läufe."
    )
    args = parser.parse_args()

    if args.mode == 'manual':
        run_manual_mode()
    elif args.mode == 'auto':
        run_auto_mode()
    else:
        print(f"Unbekannter Modus: {args.mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Import random für Gegner-KI
    import random
    main()
