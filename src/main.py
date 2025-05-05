import argparse
import sys
import time
import random
from typing import Optional, List, Dict, Tuple

try:
    from definitions import loader
    from definitions.models import SkillDefinition, ClassDefinition, ItemDefinition
    from game_logic.character import Character
    from game_logic.enemy import Enemy
    from game_logic.combat import CombatEncounter, Combatant
except ImportError:
    try:
        from src.definitions import loader
        from src.definitions.models import SkillDefinition, ClassDefinition, ItemDefinition
        from src.game_logic.character import Character
        from src.game_logic.enemy import Enemy
        from src.game_logic.combat import CombatEncounter, Combatant
    except ImportError as e: print(f"FEHLER in main.py: {e}", file=sys.stderr); sys.exit(1)

def _get_validated_input(prompt: str, max_value: int) -> int:
    while True:
        try:
            choice = input(prompt)
            value = int(choice)
            if 1 <= value <= max_value: return value
            else: print(f"Ungültige Zahl (1-{max_value}).")
        except ValueError: print("Bitte Zahl eingeben.")
        except EOFError: print("\nAbbruch."); return -1

def _handle_player_turn(player: Character, combat: CombatEncounter):
    print("\nDu bist am Zug!"); available_skills: List[Tuple[int, SkillDefinition]] = []
    print("Verfügbare Skills:"); skill_index = 1
    for skill in player.get_known_skills():
        if not skill: continue
        cost = skill.cost; can_afford = True; resource_str = ""
        if cost.resource and cost.amount > 0:
             current_res = player.get_combat_stat(f"CURRENT_{cost.resource.upper()}")
             if current_res is None or current_res < cost.amount: can_afford = False
             resource_str = f"({cost.amount} {cost.resource})"
        if can_afford: print(f"  {skill_index}. {skill.name} {resource_str}"); available_skills.append((skill_index, skill)); skill_index += 1
        else: print(f"  -- {skill.name} {resource_str} (Nicht genug Ressourcen!) --")
    if not available_skills: print(f"{player.name} passt."); time.sleep(1); return
    prompt = f"Wähle einen Skill (1-{len(available_skills)}): "
    chosen_skill_index = _get_validated_input(prompt, len(available_skills))
    if chosen_skill_index == -1: return
    selected_skill: Optional[SkillDefinition] = next((s for i, s in available_skills if i == chosen_skill_index), None)
    if not selected_skill: print("Skill nicht gefunden."); return
    target: Optional[Combatant] = None
    if selected_skill.target_type == "SELF": target = player
    elif selected_skill.target_type in ["ENEMY_SINGLE", "AREA_ENEMY"]:
        living_enemies = combat.get_living_enemies()
        if not living_enemies: print("Keine Ziele!"); return
        print("Wähle ein Ziel:")
        for i, enemy in enumerate(living_enemies): print(f"  {i+1}. {enemy}")
        prompt = f"Wähle ein Ziel (1-{len(living_enemies)}): "
        chosen_target_index = _get_validated_input(prompt, len(living_enemies))
        if chosen_target_index == -1: return
        target = living_enemies[chosen_target_index - 1]
    else: print(f"Zieltyp {selected_skill.target_type} nicht unterstützt."); return
    if not target: print("Kein gültiges Ziel."); return
    combat.apply_skill(player, target, selected_skill)
    time.sleep(1)

def _create_player_character() -> Optional[Character]:
    print("\n--- Charaktererstellung ---"); available_classes: List[Tuple[int, ClassDefinition]] = []
    class_map: Dict[int, str] = {}; index = 1; print("Verfügbare Klassen:")
    all_classes: Dict[str, ClassDefinition] = loader.get_all_classes()
    if not all_classes: print("FEHLER: Keine Klassen geladen!", file=sys.stderr); return None
    for class_id, class_def in all_classes.items():
        print(f"\n  {index}. {class_def.name}"); print(f"     {class_def.description}")
        available_classes.append((index, class_def)); class_map[index] = class_id; index += 1
    if not available_classes: print("Keine Klassen verfügbar.", file=sys.stderr); return None
    prompt = f"\nWähle deine Klasse (1-{len(available_classes)}): "
    chosen_class_index = _get_validated_input(prompt, len(available_classes))
    if chosen_class_index == -1: return None
    chosen_class_id = class_map.get(chosen_class_index)
    if not chosen_class_id: print("Ungültiger Klassenindex.", file=sys.stderr); return None

    # Namenswahl mit korrektem try...except
    chosen_name = "";
    while not chosen_name:
        try:
             chosen_name = input("Gib den Namen deines Charakters ein: ").strip()
             if not chosen_name:
                 print("Name darf nicht leer sein.")
        # *** KORREKTUR: except Block für EOFError ***
        except EOFError:
             print("\nEingabe abgebrochen.")
             return None # Signal für Abbruch

    # Charakter erstellen
    try:
        player = Character(name=chosen_name, class_id=chosen_class_id)
        print(f"\nWillkommen, {player.name} der {player.character_class.name}!")
        return player
    except ValueError as e:
        print(f"\nFehler bei der Charaktererstellung: {e}", file=sys.stderr)
        return None

def run_manual_mode():
    print("\n--- Manueller Modus gestartet ---")
    player = _create_player_character()
    if not player: print("Charaktererstellung fehlgeschlagen."); return
    player.display_status()
    enemy_id_to_fight = "goblin_lvl1"
    enemy_def = loader.get_enemy(enemy_id_to_fight)
    if not enemy_def: print(f"FEHLER: Gegner '{enemy_id_to_fight}' nicht gefunden."); return
    print(f"\nEin wilder '{enemy_def.name}' erscheint!")
    opponent = Enemy(enemy_id=enemy_id_to_fight)
    combat = CombatEncounter(player=player, enemies=[opponent])
    combat.start_combat()
    while not combat.is_combat_over():
        combat.display_combat_status()
        current_combatant: Optional[Combatant] = combat.get_current_combatant()
        if current_combatant is None: break
        if current_combatant is player: _handle_player_turn(player, combat)
        elif isinstance(current_combatant, Enemy):
            print(f"\n{current_combatant.name} ist am Zug."); time.sleep(0.5)
            target_player = combat.player
            if target_player.is_alive():
                action_tuple = current_combatant.choose_action(target_player)
                if action_tuple: skill_to_use, target = action_tuple; combat.apply_skill(current_combatant, target, skill_to_use)
                else: print(f"{current_combatant.name} passt.")
            time.sleep(1)
        if not combat.is_combat_over(): combat.next_turn()
    print("\n--- Kampf beendet ---")
    if combat.status == "PLAYER_VICTORY" and player: print(f"Glückwunsch, {player.name}!")
    elif combat.status == "PLAYER_DEFEAT": print("Leider verloren.")
    else: print("Kampf endete unerwartet.")
    print("\n--- Manueller Modus Ende ---")

def run_auto_mode(): print("\n--- Automatischer Modus gestartet --- \n--- Automatischer Modus Ende ---")

def main():
    loader.load_definitions()
    parser = argparse.ArgumentParser(description="Startet das Python RPG Projekt.")
    parser.add_argument('--mode', type=str, choices=['manual', 'auto'], required=True, help="Betriebsmodus")
    args = parser.parse_args()
    if args.mode == 'manual': run_manual_mode()
    elif args.mode == 'auto': run_auto_mode()
    else: print(f"Unbekannter Modus: {args.mode}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__": main()

