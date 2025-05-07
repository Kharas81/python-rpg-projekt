import typing
import logging
import math
import random

# Importiere unsere eigenen Module
try:
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import Skill
    from src.config import config
    from src.game_logic import leveling # Import leveling für Type Checking / Klarheit
    if typing.TYPE_CHECKING:
         from src.game_logic.effects import StatusEffect # Nur für Type Checking
except ModuleNotFoundError:
    print("WARNUNG: combat.py - Module nicht direkt geladen, versuche relativen Import (nur für Test)")
    from .entities import CharacterInstance
    from ..definitions.skill import Skill
    from ..config import config
    from . import leveling
    if typing.TYPE_CHECKING:
         from .effects import StatusEffect


logger = logging.getLogger(__name__)

def calculate_skill_base_damage(attacker: CharacterInstance,
                                skill: Skill,
                                effect_index: int = 0) -> int:
    """
    Berechnet den Basis-Schaden eines spezifischen Effekts eines Skills,
    bevor Rüstung etc. berücksichtigt wird.
    """
    if not skill.effects: # Zuerst prüfen, ob überhaupt Effekte da sind
        logger.warning(f"Skill '{skill.name}' hat keine Effekte definiert.")
        return 0

    if effect_index >= len(skill.effects) or effect_index < 0: # Dann Index prüfen
        logger.warning(f"Skill '{skill.name}' hat keinen Effekt an Index {effect_index}. Verfügbare Indizes: 0 bis {len(skill.effects)-1}.")
        return 0

    # Jetzt ist sicher, dass skill.effects[effect_index] existiert
    effect = skill.effects[effect_index]

    if effect.get("type") != "DAMAGE":
        logger.debug(f"Effekt '{effect.get('type')}' (Index {effect_index}) von Skill '{skill.name}' ist kein 'DAMAGE'-Effekt. Verursacht 0 Basisschaden.")
        return 0

    # Ab hier ist 'effect' sicher ein 'DAMAGE'-Effekt
    skill_base_val = effect.get("base_damage")
    if skill_base_val is None:
        actual_base_damage = config.get_setting("game_settings.base_weapon_damage", 5)
        # logger.debug(f"Skill '{skill.name}' Effekt {effect_index} hat keinen base_damage, verwende globalen default_weapon_damage: {actual_base_damage}") # Gekürzt für weniger Logs
    else:
        actual_base_damage = int(skill_base_val)
        # logger.debug(f"Skill '{skill.name}' Effekt {effect_index} base_damage: {actual_base_damage}") # Gekürzt

    relevant_attribute: typing.Optional[str] = effect.get("attribute")
    attribute_bonus = 0
    if relevant_attribute:
        attribute_bonus = attacker.get_attribute_bonus(relevant_attribute)
        # logger.debug(f"Angreifer '{attacker.name}' Attribut-Bonus für '{relevant_attribute}': {attribute_bonus}") # Gekürzt
    # else:
        # logger.debug(f"Skill '{skill.name}' Effekt {effect_index} spezifiziert kein Attribut für Bonus, Bonus ist 0.") # Gekürzt

    multiplier = float(effect.get("multiplier", 1.0))
    # logger.debug(f"Skill '{skill.name}' Effekt {effect_index} Multiplikator: {multiplier}") # Gekürzt

    raw_damage = (actual_base_damage + attribute_bonus) * multiplier
    calculated_damage = math.floor(raw_damage)

    logger.info(f"Basisschaden für '{attacker.name}' mit Skill '{skill.name}' (Effekt {effect_index}): "
                f"({actual_base_damage} [Base] + {attribute_bonus} [Bonus]) * {multiplier} [Mult] = {raw_damage:.2f} -> {calculated_damage}")
    return calculated_damage

def apply_damage_reduction(defender: CharacterInstance, incoming_damage: int, damage_type: str) -> int:
    if incoming_damage <= 0: return 0
    defense_value = 0; defense_type_str = ""
    damage_type_upper = damage_type.upper()
    if damage_type_upper == "PHYSICAL": defense_value = defender.get_current_armor(); defense_type_str = "Rüstung"
    else: defense_value = defender.get_current_magic_resist(); defense_type_str = "Magieresistenz"
    reduced_damage = incoming_damage - defense_value; min_damage = config.get_setting("game_settings.min_damage", 1)
    final_damage = max(min_damage, reduced_damage); logger.info(f"Schadensreduktion für '{defender.name}': {incoming_damage} [Roh] - {defense_value} [{defense_type_str}] = {reduced_damage} -> {final_damage} [Final] (Minimalschaden: {min_damage})"); return final_damage

def check_hit_success(attacker: CharacterInstance, defender: CharacterInstance) -> bool:
    base_chance = config.get_setting("game_settings.hit_chance_base", 90); accuracy_factor = config.get_setting("game_settings.hit_chance_accuracy_factor", 3)
    evasion_factor = config.get_setting("game_settings.hit_chance_evasion_factor", 2); min_hit_chance = config.get_setting("game_settings.hit_chance_min", 5)
    max_hit_chance = config.get_setting("game_settings.hit_chance_max", 95); attacker_accuracy_mod = attacker.get_current_accuracy_modifier()
    defender_evasion_mod = defender.get_current_evasion_modifier()
    logger.debug(f"Trefferchance-Berechnung für '{attacker.name}' (AccMod: {attacker_accuracy_mod}) vs '{defender.name}' (EvaMod: {defender_evasion_mod})")
    hit_chance = base_chance + (attacker_accuracy_mod * accuracy_factor) - (defender_evasion_mod * evasion_factor)
    logger.debug(f"  Rohe Trefferchance: {base_chance} + ({attacker_accuracy_mod}*{accuracy_factor}) - ({defender_evasion_mod}*{evasion_factor}) = {hit_chance}%")
    hit_chance = max(min_hit_chance, min(max_hit_chance, hit_chance)); logger.info(f"  Finale Trefferchance (begrenzt auf {min_hit_chance}%-{max_hit_chance}%): {hit_chance}%")
    roll = random.randint(1, 100); hit = roll <= hit_chance; logger.info(f"  Wurf: {roll} -> {'TREFFER!' if hit else 'Verfehlt!'} (Benötigt: <= {hit_chance})"); return hit

def execute_attack_action(attacker: CharacterInstance, defender: CharacterInstance, skill_to_use: Skill) -> typing.Dict[str, typing.Any]:
    action_log = []; action_log.append(f"'{attacker.name}' (HP {attacker.current_hp}, Lvl {attacker.level}, XP {attacker.current_xp}/{attacker.xp_to_next_level}) versucht '{skill_to_use.name}' auf '{defender.name}'...")
    result: typing.Dict[str, typing.Any] = {
        "hit": False, "damage_dealt": 0, "defender_hp_after": defender.current_hp, "defender_is_alive": defender.is_alive(),
        "log_messages": action_log, "reason": None, "xp_awarded": 0, "applied_effects": [],
        "attacker_lvl_after": attacker.level, "attacker_xp_after": attacker.current_xp, "attacker_xp_next_after": attacker.xp_to_next_level }
    if not attacker.is_alive(): result["reason"]="Attacker not alive"; logger.warning(result["reason"]); action_log.append(result["reason"]); return result
    if not defender.is_alive(): result["reason"]="Defender already defeated"; logger.warning(result["reason"]); action_log.append(result["reason"]); return result
    cost_resource=skill_to_use.get_cost_resource(); cost_amount=skill_to_use.get_cost_amount()
    if cost_resource and cost_resource.upper()!="NONE" and cost_amount>0:
        if attacker.can_afford_cost(cost_resource, cost_amount):
            if not attacker.pay_cost(cost_resource, cost_amount): result["reason"]="Failed to pay cost"; logger.error(result["reason"]); action_log.append(result["reason"]); return result
            action_log.append(f"'{attacker.name}' bezahlt {cost_amount} {cost_resource}.")
        else:
            result["reason"]="Insufficient resources"; msg=f"'{attacker.name}' hat nicht genug {cost_resource}. Angriff abgebrochen."; logger.warning(msg); action_log.append(msg); return result
    else: action_log.append(f"Skill '{skill_to_use.name}' ist kostenlos.")
    if not check_hit_success(attacker, defender): action_log.append(f"...hat VERFEHLT."); result["hit"] = False; return result
    result["hit"] = True; action_log.append(f"...war ein TREFFER!")
    total_damage_dealt_this_action = 0; damage_effect_found = False
    for i, effect_data in enumerate(skill_to_use.effects):
        if effect_data.get("type") == "DAMAGE":
            damage_effect_found = True; action_log.append(f"  Verarbeite Schadenseffekt {i}...")
            base_damage = calculate_skill_base_damage(attacker, skill_to_use, effect_index=i)
            damage_type = effect_data.get("damage_type", "PHYSICAL").upper()
            final_damage = apply_damage_reduction(defender, base_damage, damage_type)
            action_log.append(f"    Finaler Schaden (Effekt {i}): {final_damage} {damage_type}")
            if final_damage > 0: defender.take_damage(final_damage); total_damage_dealt_this_action += final_damage
            else: action_log.append(f"    Kein Schaden (Effekt {i}) nach Reduktion.")
            break
    if not damage_effect_found: action_log.append(f"Skill '{skill_to_use.name}' hat keine 'DAMAGE'-Effekte.")
    applied_effect_ids = []
    if skill_to_use.applies_effects:
         action_log.append(f"  Wende Status-Effekte an...")
         for effect_to_apply_data in skill_to_use.applies_effects:
              effect_id = effect_to_apply_data.get("id")
              if effect_id: defender.add_status_effect(effect_to_apply_data, source_entity_id=attacker.definition.entity_id); action_log.append(f"    -> Effekt '{effect_id}' angewendet."); applied_effect_ids.append(effect_id)
              else: logger.warning(f"Ungültige Daten in applies_effects: {effect_to_apply_data}")
         result["applied_effects"] = applied_effect_ids
    result["damage_dealt"] = total_damage_dealt_this_action; result["defender_hp_after"] = defender.current_hp; result["defender_is_alive"] = defender.is_alive()
    if not defender.is_alive():
        action_log.append(f"'{defender.name}' wurde besiegt!")
        if attacker.is_alive() and hasattr(attacker,'gain_xp') and hasattr(defender.definition,'xp_reward'):
            xp_to_award = defender.definition.xp_reward
            if xp_to_award > 0: action_log.append(f"'{attacker.name}' erhält {xp_to_award} XP."); attacker.gain_xp(xp_to_award); result["xp_awarded"] = xp_to_award
            else: action_log.append(f"'{defender.name}' gibt keine XP.")
    result["attacker_lvl_after"]=attacker.level; result["attacker_xp_after"]=attacker.current_xp; result["attacker_xp_next_after"]=attacker.xp_to_next_level
    return result

# --- Testblock (Import-Handling korrigiert in vorheriger Iteration, Rest bleibt gleich) ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging; setup_logging()
        from src.definitions import loader
    except ImportError:
        print("WARNUNG: Setup-Module für Test nicht gefunden. Passe sys.path an und versuche erneut...")
        import sys; from pathlib import Path
        project_dir = Path(__file__).parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        try:
            from src.utils.logging_setup import setup_logging; setup_logging()
            from src.definitions import loader
        except ImportError as e_inner:
             print(f"FATAL: Konnte Module auch nach Pfadanpassung nicht laden: {e_inner}"); exit(1)
    logger.info("Starte Tests für combat.py (mit Effekt-Auswirkungen)...")
    krieger_def=loader.get_character_class("krieger"); goblin_def=loader.get_opponent("goblin_lv1")
    schurke_def=loader.get_character_class("schurke"); shield_bash_skill = loader.get_skill("shield_bash")
    frostbolt_skill = loader.get_skill("frostbolt"); distraction_skill = loader.get_skill("distraction")
    basic_strike_skill = loader.get_skill("basic_strike_phys")
    if not all([krieger_def, goblin_def, schurke_def, shield_bash_skill, frostbolt_skill, distraction_skill, basic_strike_skill]):
        logger.critical("FEHLER: Notwendige Definitionen für Tests konnten nicht geladen werden."); exit()
    logger.info("\n\n--- Test: Effekt-Auswirkungen auf Trefferchance ---")
    schurke_attacker = CharacterInstance(schurke_def); goblin_defender = CharacterInstance(goblin_def)
    logger.info(f"\nSzenario 1: {schurke_attacker.name} vs {goblin_defender.name} (Normal)"); check_hit_success(schurke_attacker, goblin_defender)
    logger.info(f"\nSzenario 2: {schurke_attacker.name} vs {goblin_defender.name} (Goblin SLOWED)")
    slowed_data = {"id": "SLOWED", "duration": 1, "potency": 2}; goblin_defender.add_status_effect(slowed_data); logger.info(f"Goblin Status: {goblin_defender}")
    check_hit_success(schurke_attacker, goblin_defender); goblin_defender.remove_status_effect("SLOWED")
    logger.info(f"\nSzenario 3: {schurke_attacker.name} (ACC_DOWN) vs {goblin_defender.name}")
    accuracy_down_data = {"id": "ACCURACY_DOWN", "duration": 2, "potency": 3}; schurke_attacker.add_status_effect(accuracy_down_data); logger.info(f"Schurke Status: {schurke_attacker}")
    check_hit_success(schurke_attacker, goblin_defender); schurke_attacker.remove_status_effect("ACCURACY_DOWN")
    logger.info(f"\nSzenario 4: Krieger Basic Strike (7 Roh) vs Goblin mit DEFENSE_UP (+3)")
    krieger_attacker = CharacterInstance(krieger_def); goblin_defender_defup = CharacterInstance(goblin_def)
    defense_up_data = {"id": "DEFENSE_UP", "duration": 1, "potency": 3}; goblin_defender_defup.add_status_effect(defense_up_data); logger.info(f"Goblin Status: {goblin_defender_defup}")
    final_dmg = apply_damage_reduction(goblin_defender_defup, 7, "PHYSICAL"); assert final_dmg == 2; logger.info(f"  -> Finaler Schaden gegen DEFENSE_UP: {final_dmg} (OK)")
    logger.info("\nAlle Tests für combat.py (inkl. Effekt-Auswirkungen) durchgelaufen.")

