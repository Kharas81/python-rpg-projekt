import typing
import logging
import math
import random

# Importiere unsere eigenen Module
try:
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import Skill
    from src.config import config
    # Importiere leveling, da CharacterInstance.gain_xp() es verwendet.
    # Obwohl gain_xp den Import dynamisch macht, ist es gut, die Abhängigkeit hier klarzustellen.
    from src.game_logic import leveling
except ModuleNotFoundError:
    print("WARNUNG: combat.py - Module nicht direkt geladen, versuche relativen Import (nur für Test)")
    from .entities import CharacterInstance
    from ..definitions.skill import Skill
    from ..config import config
    from . import leveling


logger = logging.getLogger(__name__)

def calculate_skill_base_damage(attacker: CharacterInstance,
                                skill: Skill,
                                effect_index: int = 0) -> int:
    if not skill.effects or effect_index >= len(skill.effects):
        logger.warning(f"Skill '{skill.name}' hat keinen Effekt an Index {effect_index}.")
        return 0
    effect = skill.effects[effect_index]
    if effect.get("type") != "DAMAGE":
        return 0
    skill_base_val = effect.get("base_damage")
    if skill_base_val is None:
        actual_base_damage = config.get_setting("game_settings.base_weapon_damage", 5)
    else:
        actual_base_damage = int(skill_base_val)
    relevant_attribute: typing.Optional[str] = effect.get("attribute")
    attribute_bonus = 0
    if relevant_attribute:
        attribute_bonus = attacker.get_attribute_bonus(relevant_attribute)
    multiplier = float(effect.get("multiplier", 1.0))
    raw_damage = (actual_base_damage + attribute_bonus) * multiplier
    calculated_damage = math.floor(raw_damage)
    logger.info(f"Basisschaden für '{attacker.name}' mit Skill '{skill.name}' (Effekt {effect_index}): "
                f"({actual_base_damage} [Base] + {attribute_bonus} [Bonus]) * {multiplier} [Mult] = {raw_damage:.2f} -> {calculated_damage}")
    return calculated_damage


def apply_damage_reduction(defender: CharacterInstance,
                           incoming_damage: int,
                           damage_type: str) -> int:
    if incoming_damage <= 0:
        return 0
    defense_value = 0
    defense_type_str = ""
    if damage_type.upper() == "PHYSICAL":
        defense_value = defender.armor
        defense_type_str = "Rüstung"
    else:
        defense_value = defender.magic_resist
        defense_type_str = "Magieresistenz"
    reduced_damage = incoming_damage - defense_value
    min_damage = config.get_setting("game_settings.min_damage", 1)
    final_damage = max(min_damage, reduced_damage)
    logger.info(f"Schadensreduktion für '{defender.name}': {incoming_damage} [Roh] - {defense_value} [{defense_type_str}] = {reduced_damage} "
                f"-> {final_damage} [Final] (Minimalschaden: {min_damage})")
    return final_damage


def check_hit_success(attacker: CharacterInstance, defender: CharacterInstance) -> bool:
    base_chance = config.get_setting("game_settings.hit_chance_base", 90)
    accuracy_factor = config.get_setting("game_settings.hit_chance_accuracy_factor", 3)
    evasion_factor = config.get_setting("game_settings.hit_chance_evasion_factor", 2)
    min_hit_chance = config.get_setting("game_settings.hit_chance_min", 5)
    max_hit_chance = config.get_setting("game_settings.hit_chance_max", 95)
    attacker_accuracy_mod = attacker.get_attribute_bonus('DEX')
    defender_evasion_mod = defender.get_attribute_bonus('DEX')
    hit_chance = base_chance + (attacker_accuracy_mod * accuracy_factor) - (defender_evasion_mod * evasion_factor)
    hit_chance = max(min_hit_chance, min(max_hit_chance, hit_chance))
    roll = random.randint(1, 100)
    hit = roll <= hit_chance
    logger.info(f"Angriff von '{attacker.name}' auf '{defender.name}': "
                f"Chance={hit_chance}%, Wurf={roll} -> {'TREFFER!' if hit else 'Verfehlt!'}")
    return hit


def execute_attack_action(attacker: CharacterInstance,
                          defender: CharacterInstance,
                          skill_to_use: Skill) -> typing.Dict[str, typing.Any]:
    action_log = []
    action_log.append(f"'{attacker.name}' (HP {attacker.current_hp}, Lvl {attacker.level}, XP {attacker.current_xp}/{attacker.xp_to_next_level}) "
                      f"versucht '{skill_to_use.name}' auf '{defender.name}' (HP {defender.current_hp}, Lvl {defender.level}).")

    initial_attacker_xp = attacker.current_xp
    xp_awarded_this_action = 0

    if not attacker.is_alive():
        msg = f"Angreifer '{attacker.name}' ist nicht am Leben. Angriff abgebrochen."
        logger.warning(msg)
        action_log.append(msg)
        return {"hit": False, "damage_dealt": 0, "defender_hp_after": defender.current_hp,
                "log_messages": action_log, "reason": "Attacker not alive", "xp_awarded": 0}

    if not defender.is_alive():
        msg = f"Ziel '{defender.name}' ist bereits besiegt. Angriff abgebrochen."
        logger.warning(msg)
        action_log.append(msg)
        return {"hit": False, "damage_dealt": 0, "defender_hp_after": defender.current_hp,
                "log_messages": action_log, "reason": "Defender already defeated", "xp_awarded": 0}

    cost_resource = skill_to_use.get_cost_resource()
    cost_amount = skill_to_use.get_cost_amount()
    if cost_resource and cost_resource.upper() != "NONE" and cost_amount > 0:
        if attacker.can_afford_cost(cost_resource, cost_amount):
            attacker.pay_cost(cost_resource, cost_amount)
            action_log.append(f"'{attacker.name}' bezahlt {cost_amount} {cost_resource} für '{skill_to_use.name}'. "
                              f"Neuer Stand: {attacker.get_current_resource(cost_resource)}")
        else:
            msg = (f"'{attacker.name}' hat nicht genug {cost_resource} für '{skill_to_use.name}' "
                   f"(benötigt {cost_amount}, hat {attacker.get_current_resource(cost_resource)}). Angriff abgebrochen.")
            logger.warning(msg)
            action_log.append(msg)
            return {"hit": False, "damage_dealt": 0, "defender_hp_after": defender.current_hp,
                    "log_messages": action_log, "reason": "Insufficient resources", "xp_awarded": 0}
    else:
        action_log.append(f"Skill '{skill_to_use.name}' hat keine Ressourcenkosten.")

    if not check_hit_success(attacker, defender):
        action_log.append(f"Angriff von '{attacker.name}' mit '{skill_to_use.name}' hat VERFEHLT.")
        return {"hit": False, "damage_dealt": 0, "defender_hp_after": defender.current_hp,
                "log_messages": action_log, "xp_awarded": 0}

    action_log.append(f"Angriff von '{attacker.name}' mit '{skill_to_use.name}' war ein TREFFER!")
    total_damage_dealt_this_action = 0
    damage_effect_found = False

    for i, effect_data in enumerate(skill_to_use.effects):
        if effect_data.get("type") == "DAMAGE":
            damage_effect_found = True
            action_log.append(f"  Verarbeite Schadenseffekt {i} von '{skill_to_use.name}'...")
            base_damage = calculate_skill_base_damage(attacker, skill_to_use, effect_index=i)
            damage_type = effect_data.get("damage_type", "PHYSICAL").upper()
            final_damage = apply_damage_reduction(defender, base_damage, damage_type)
            action_log.append(f"    Finaler Schaden (Effekt {i}): {final_damage} {damage_type}")

            if final_damage > 0:
                defender.take_damage(final_damage)
                action_log.append(f"    '{defender.name}' erleidet {final_damage} {damage_type} Schaden. "
                                  f"HP: {defender.current_hp}/{defender.max_hp}")
                total_damage_dealt_this_action += final_damage
            else:
                action_log.append(f"    Kein Schaden (Effekt {i}) nach Reduktion für '{defender.name}'.")
            break

    if not damage_effect_found:
        action_log.append(f"Skill '{skill_to_use.name}' hat keine 'DAMAGE'-Effekte. Verursacht 0 Schaden.")

    if not defender.is_alive():
        action_log.append(f"'{defender.name}' wurde durch diesen Angriff besiegt!")
        # XP Vergabe, wenn Verteidiger besiegt wurde UND Angreifer noch lebt
        if attacker.is_alive():
            xp_to_award = defender.definition.xp_reward
            if xp_to_award > 0:
                action_log.append(f"'{attacker.name}' besiegt '{defender.name}' und erhält {xp_to_award} XP.")
                attacker.gain_xp(xp_to_award) # gain_xp loggt bereits den XP-Gewinn und Level-Up
                xp_awarded_this_action = xp_to_award
            else:
                action_log.append(f"'{defender.name}' gibt keine XP.")
        else:
            action_log.append(f"Angreifer '{attacker.name}' ist ebenfalls nicht mehr am Leben, keine XP-Vergabe.")


    return {
        "hit": True,
        "damage_dealt": total_damage_dealt_this_action,
        "defender_hp_after": defender.current_hp,
        "defender_is_alive": defender.is_alive(),
        "log_messages": action_log,
        "xp_awarded": xp_awarded_this_action,
        "attacker_lvl_after": attacker.level, # Um Level-Ups im Test zu sehen
        "attacker_xp_after": attacker.current_xp,
        "attacker_xp_next_after": attacker.xp_to_next_level
    }


# --- Testblock ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging
        setup_logging()
        from src.definitions import loader
    except ImportError:
        print("WARNUNG: Setup-Module für Test nicht gefunden...")
        import sys; from pathlib import Path
        project_dir = Path(__file__).parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.definitions import loader

    logger.info("Starte Tests für combat.py (mit XP-Vergabe)...")

    krieger_def = loader.get_character_class("krieger")
    goblin_def = loader.get_opponent("goblin_lv1")       # XP Reward: 50
    # Erstelle einen weiteren Gegner für Multi-Kill-Tests, falls benötigt
    goblin_schamane_def = loader.get_opponent("goblin_schamane_lv3") # XP Reward: 100

    basic_strike_skill = loader.get_skill("basic_strike_phys")

    if not all([krieger_def, goblin_def, goblin_schamane_def, basic_strike_skill]):
        logger.critical("FEHLER: Notwendige Definitionen für Tests konnten nicht geladen werden.")
        exit()

    logger.info("\n\n--- Test: execute_attack_action mit XP-Vergabe ---")

    # Szenario: Krieger (Lvl 1, 0 XP) besiegt Goblin (gibt 50 XP)
    # Krieger braucht 100 XP für Lvl 2.
    krieger_attacker = CharacterInstance(krieger_def)
    goblin_defender = CharacterInstance(goblin_def) # HP: 95, Armor: 2, XP: 50
    logger.info(f"Start: {krieger_attacker}")
    logger.info(f"Start: {goblin_defender}")

    schaden_pro_treffer = 5 # Basic Strike (7) vs Goblin Armor (2)

    turn = 0
    while goblin_defender.is_alive() and krieger_attacker.is_alive() and turn < 50: # Max 50 Runden
        turn += 1
        logger.info(f"\n--- Runde {turn} (Krieger vs Goblin) ---")
        attack_result = execute_attack_action(krieger_attacker, goblin_defender, basic_strike_skill)
        logger.info("  Aktionsprotokoll (Krieger vs Goblin):")
        for msg in attack_result["log_messages"]: logger.info(f"    - {msg}")

        if not goblin_defender.is_alive():
            logger.info(f"'{goblin_defender.name}' in Runde {turn} besiegt.")
            assert attack_result["xp_awarded"] == goblin_def.xp_reward, f"Falsche XP! Erw: {goblin_def.xp_reward}, Bek: {attack_result['xp_awarded']}"
            assert krieger_attacker.current_xp == goblin_def.xp_reward, "Krieger XP nicht korrekt."
            assert krieger_attacker.level == 1, "Krieger sollte noch nicht Level 2 sein."
            logger.info(f"Krieger Status nach Sieg: {krieger_attacker}")
            break
        if turn == 40: logger.warning("Kampf dauert zu lange, Abbruch."); break

    # Krieger sollte jetzt 50 XP haben. Besiege noch einen Goblin Schamanen (100 XP) für Level Up
    if krieger_attacker.is_alive() and krieger_attacker.current_xp == 50:
        logger.info("\n--- Nächster Kampf: Krieger vs Goblin Schamane ---")
        schamane_defender = CharacterInstance(goblin_schamane_def) # HP: 90, Armor: 1, MR: 3, XP: 100
        logger.info(f"Start: {krieger_attacker}")
        logger.info(f"Start: {schamane_defender}")

        # Annahme: Krieger besiegt Schamanen (Details des Kampfes hier nicht ausgeschrieben)
        # Simuliere direkten XP-Gewinn, als ob der Kampf stattgefunden hätte
        # Für einen echten Test müsste der Kampf durchgespielt werden.
        # Hier simulieren wir nur den XP-Gewinn nach einem hypothetischen Sieg.

        # Damit der Test nicht zu lang wird, geben wir dem Schamanen wenig HP und dem Krieger hohen Schaden
        # oder wir fügen die XP direkt hinzu NACHDEM der Schamane theoretisch besiegt wurde.
        # Hier vereinfacht: Wir nehmen an, der Schamane wird besiegt und der Krieger erhält die XP.
        
        # Um den Kampf kurz zu halten, setzen wir die HP des Schamanen niedrig.
        schamane_defender.current_hp = 1 
        turn_s = 0
        while schamane_defender.is_alive() and krieger_attacker.is_alive() and turn_s < 5:
            turn_s +=1
            logger.info(f"\n--- Runde {turn_s} (Krieger vs Schamane) ---")
            attack_result_s = execute_attack_action(krieger_attacker, schamane_defender, basic_strike_skill)
            logger.info("  Aktionsprotokoll (Krieger vs Schamane):")
            for msg in attack_result_s["log_messages"]: logger.info(f"    - {msg}")

            if not schamane_defender.is_alive():
                logger.info(f"'{schamane_defender.name}' in Runde {turn_s} besiegt.")
                expected_total_xp = 50 + goblin_schamane_def.xp_reward # 50 + 100 = 150
                assert attack_result_s["xp_awarded"] == goblin_schamane_def.xp_reward
                assert krieger_attacker.current_xp == expected_total_xp - krieger_attacker.xp_to_next_level # XP nach Levelup
                assert krieger_attacker.level == 2 # Sollte Level 2 sein (100 XP für Lvl 1 -> 2)
                # XP für Lvl 3 ist 150. Rest-XP: 150 - 100 (für LvlUp) = 50.
                # dann von 50 auf 150 (Lvl2->3)
                # In unserem Fall: Krieger hatte 50 XP. Braucht 100 für Lvl 2.
                # Er bekommt 100 XP vom Schamanen. Total: 150 XP.
                # Level Up zu Lvl 2 (kostet 100 XP). Rest: 50 XP.
                # Nächstes Level (Lvl 3) braucht 150 XP.
                assert krieger_attacker.xp_to_next_level == 150 # XP für Lvl 2 -> 3 ist 150
                logger.info(f"Krieger Status nach Sieg über Schamane (Level Up!): {krieger_attacker}")
                break
            if turn_s == 4: logger.warning("Schamanen-Kampf dauert zu lange, Abbruch."); break
    else:
        logger.warning("Krieger hat den ersten Goblin nicht besiegt oder hat nicht 50 XP, überspringe zweiten Kampf.")


    logger.info("\nAlle Tests für combat.py (inkl. XP-Vergabe) durchgelaufen.")

