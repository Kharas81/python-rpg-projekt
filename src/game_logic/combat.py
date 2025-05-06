import typing
import logging
import math
import random # Für die Trefferchance-Ermittlung

# Importiere unsere eigenen Module
try:
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import Skill
    from src.config import config
except ModuleNotFoundError:
    print("WARNUNG: combat.py - Module nicht direkt geladen, versuche relativen Import (nur für Test)")
    from .entities import CharacterInstance
    from ..definitions.skill import Skill
    from ..config import config


logger = logging.getLogger(__name__)

def calculate_skill_base_damage(attacker: CharacterInstance,
                                skill: Skill,
                                effect_index: int = 0) -> int:
    """
    Berechnet den Basis-Schaden eines spezifischen Effekts eines Skills,
    bevor Rüstung etc. berücksichtigt wird.
    """
    if not skill.effects or effect_index >= len(skill.effects):
        logger.warning(f"Skill '{skill.name}' hat keinen Effekt an Index {effect_index}.")
        return 0

    effect = skill.effects[effect_index]

    if effect.get("type") != "DAMAGE":
        logger.debug(f"Effekt '{effect.get('type')}' von Skill '{skill.name}' ist kein 'DAMAGE'-Effekt. Verursacht 0 Basisschaden.")
        return 0

    skill_base_val = effect.get("base_damage")
    if skill_base_val is None:
        actual_base_damage = config.get_setting("game_settings.base_weapon_damage", 5)
        # logger.debug(f"Skill '{skill.name}' Effekt {effect_index} hat keinen base_damage, verwende globalen default_weapon_damage: {actual_base_damage}")
    else:
        actual_base_damage = int(skill_base_val)
        # logger.debug(f"Skill '{skill.name}' Effekt {effect_index} base_damage: {actual_base_damage}")

    relevant_attribute: typing.Optional[str] = effect.get("attribute")
    attribute_bonus = 0
    if relevant_attribute:
        attribute_bonus = attacker.get_attribute_bonus(relevant_attribute)
        # logger.debug(f"Angreifer '{attacker.name}' Attribut-Bonus für '{relevant_attribute}': {attribute_bonus}")
    # else:
        # logger.debug(f"Skill '{skill.name}' Effekt {effect_index} spezifiziert kein Attribut für Bonus, Bonus ist 0.")

    multiplier = float(effect.get("multiplier", 1.0))
    # logger.debug(f"Skill '{skill.name}' Effekt {effect_index} Multiplikator: {multiplier}")

    raw_damage = (actual_base_damage + attribute_bonus) * multiplier
    calculated_damage = math.floor(raw_damage)

    logger.info(f"Basisschaden für '{attacker.name}' mit Skill '{skill.name}' (Effekt {effect_index}): "
                f"({actual_base_damage} [Base] + {attribute_bonus} [Bonus]) * {multiplier} [Mult] = {raw_damage:.2f} -> {calculated_damage}")

    return calculated_damage


def apply_damage_reduction(defender: CharacterInstance,
                           incoming_damage: int,
                           damage_type: str) -> int:
    """
    Reduziert den eingehenden Schaden basierend auf der Verteidigung des Ziels
    und dem Schadenstyp.
    """
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

    # logger.debug(f"Verteidiger '{defender.name}' hat {defense_value} {defense_type_str} gegen {damage_type.upper()} Schaden.")

    reduced_damage = incoming_damage - defense_value
    min_damage = config.get_setting("game_settings.min_damage", 1)
    final_damage = max(min_damage, reduced_damage)

    logger.info(f"Schadensreduktion für '{defender.name}': {incoming_damage} [Roh] - {defense_value} [{defense_type_str}] = {reduced_damage} "
                f"-> {final_damage} [Final] (Minimalschaden: {min_damage})")

    return final_damage


def check_hit_success(attacker: CharacterInstance, defender: CharacterInstance) -> bool:
    """
    Ermittelt, ob ein Angriff trifft, basierend auf Genauigkeit und Ausweichen.

    Args:
        attacker: Die CharacterInstance des Angreifers.
        defender: Die CharacterInstance des Verteidigers.

    Returns:
        True, wenn der Angriff trifft, sonst False.
    """
    # --- Werte aus der Konfiguration laden ---
    base_chance = config.get_setting("game_settings.hit_chance_base", 90)
    accuracy_factor = config.get_setting("game_settings.hit_chance_accuracy_factor", 3)
    evasion_factor = config.get_setting("game_settings.hit_chance_evasion_factor", 2)
    min_hit_chance = config.get_setting("game_settings.hit_chance_min", 5)
    max_hit_chance = config.get_setting("game_settings.hit_chance_max", 95)

    # --- Modifikatoren berechnen (basierend auf DEX-Bonus) ---
    # TODO: Später Status-Effekte wie ACCURACY_DOWN, SLOWED hier einbeziehen
    attacker_accuracy_mod = attacker.get_attribute_bonus('DEX')
    defender_evasion_mod = defender.get_attribute_bonus('DEX')

    logger.debug(f"Trefferchance-Berechnung für '{attacker.name}' (DEX-Bonus: {attacker_accuracy_mod}) vs "
                 f"'{defender.name}' (DEX-Bonus: {defender_evasion_mod})")

    # --- Trefferchance nach Formel berechnen ---
    hit_chance = base_chance + (attacker_accuracy_mod * accuracy_factor) - (defender_evasion_mod * evasion_factor)
    logger.debug(f"  Rohe Trefferchance: {base_chance} + ({attacker_accuracy_mod} * {accuracy_factor}) - ({defender_evasion_mod} * {evasion_factor}) = {hit_chance}%")

    # --- Trefferchance auf Min/Max begrenzen ---
    hit_chance = max(min_hit_chance, min(max_hit_chance, hit_chance))
    logger.info(f"  Finale Trefferchance (begrenzt auf {min_hit_chance}%-{max_hit_chance}%): {hit_chance}%")

    # --- Trefferwurf ---
    roll = random.randint(1, 100)
    hit = roll <= hit_chance

    logger.info(f"  Wurf: {roll} -> {'TREFFER!' if hit else 'Verfehlt!'} (Benötigt: <= {hit_chance})")
    return hit


# --- Testblock ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging
        setup_logging()
        from src.definitions import loader
    except ImportError:
        print("WARNUNG: Setup-Module für Test nicht gefunden. Logging ggf. nicht konfiguriert.")
        import sys
        from pathlib import Path
        project_dir = Path(__file__).parent.parent.parent
        if str(project_dir) not in sys.path:
            sys.path.insert(0, str(project_dir))
        from src.definitions import loader

    logger.info("Starte Tests für combat.py...")

    krieger_def = loader.get_character_class("krieger")   # DEX 10 -> Bonus 0
    goblin_def = loader.get_opponent("goblin_lv1")       # DEX 12 -> Bonus +1
    magier_def = loader.get_character_class("magier")     # DEX 10 -> Bonus 0
    # Erstelle einen Schurken für höhere DEX-Werte
    # (nehme an, 'schurke' existiert in characters.json5 mit DEX 14 -> Bonus +2)
    schurke_def = loader.get_character_class("schurke")   # DEX 14 -> Bonus +2

    basic_strike_skill = loader.get_skill("basic_strike_phys")
    fireball_skill = loader.get_skill("fireball")

    if not all([krieger_def, goblin_def, magier_def, schurke_def, basic_strike_skill, fireball_skill]):
        logger.critical("FEHLER: Notwendige Definitionen für Tests konnten nicht geladen werden.")
        exit()

    krieger_inst = CharacterInstance(krieger_def) # DEX-Bonus 0
    goblin_inst = CharacterInstance(goblin_def)   # DEX-Bonus +1
    magier_inst = CharacterInstance(magier_def)   # DEX-Bonus 0
    schurke_inst = CharacterInstance(schurke_def) # DEX-Bonus +2


    # --- Tests für calculate_skill_base_damage (gekürzt) ---
    logger.info("\n--- Test: calculate_skill_base_damage (Kurzform) ---")
    base_schaden_krieger_basic = calculate_skill_base_damage(krieger_inst, basic_strike_skill)
    assert base_schaden_krieger_basic == 7
    base_schaden_magier_fireball = calculate_skill_base_damage(magier_inst, fireball_skill)
    assert base_schaden_magier_fireball == 24


    # --- Tests für apply_damage_reduction (gekürzt) ---
    logger.info("\n--- Test: apply_damage_reduction (Kurzform) ---")
    final_dmg1 = apply_damage_reduction(goblin_inst, base_schaden_krieger_basic, "PHYSICAL") # 7 - 2 = 5
    assert final_dmg1 == 5
    final_dmg2 = apply_damage_reduction(goblin_inst, base_schaden_magier_fireball, "FIRE") # 24 - 0 = 24
    assert final_dmg2 == 24

    # --- Tests für check_hit_success ---
    logger.info("\n--- Test: check_hit_success ---")

    # Szenario 1: Krieger (DEX-Bonus 0) vs Goblin (DEX-Bonus +1)
    # Base: 90, AccFactor: 3, EvaFactor: 2
    # Chance = 90 + (0 * 3) - (1 * 2) = 90 - 2 = 88%
    logger.info(f"\nSzenario 1: {krieger_inst.name} (DEX-Bonus {krieger_inst.get_attribute_bonus('DEX')}) "
                f"vs {goblin_inst.name} (DEX-Bonus {goblin_inst.get_attribute_bonus('DEX')})")
    hits = 0
    runs = 10
    for i in range(runs):
        if check_hit_success(krieger_inst, goblin_inst):
            hits += 1
    logger.info(f"  -> Treffer in {runs} Versuchen: {hits} (Erwartet ca. 8-9 bei 88%)")

    # Szenario 2: Schurke (DEX-Bonus +2) vs Goblin (DEX-Bonus +1)
    # Chance = 90 + (2 * 3) - (1 * 2) = 90 + 6 - 2 = 94%
    logger.info(f"\nSzenario 2: {schurke_inst.name} (DEX-Bonus {schurke_inst.get_attribute_bonus('DEX')}) "
                f"vs {goblin_inst.name} (DEX-Bonus {goblin_inst.get_attribute_bonus('DEX')})")
    hits = 0
    for i in range(runs):
        if check_hit_success(schurke_inst, goblin_inst):
            hits += 1
    logger.info(f"  -> Treffer in {runs} Versuchen: {hits} (Erwartet ca. 9 bei 94%)")


    # Szenario 3: Krieger (DEX-Bonus 0) vs Schurke (DEX-Bonus +2)
    # Chance = 90 + (0 * 3) - (2 * 2) = 90 - 4 = 86%
    logger.info(f"\nSzenario 3: {krieger_inst.name} (DEX-Bonus {krieger_inst.get_attribute_bonus('DEX')}) "
                f"vs {schurke_inst.name} (DEX-Bonus {schurke_inst.get_attribute_bonus('DEX')})")
    hits = 0
    for i in range(runs):
        if check_hit_success(krieger_inst, schurke_inst):
            hits += 1
    logger.info(f"  -> Treffer in {runs} Versuchen: {hits} (Erwartet ca. 8-9 bei 86%)")

    # Szenario 4: Angreifer mit sehr niedrigem DEX-Bonus (hypothetisch)
    # Erstelle eine Dummy-Instanz für den Test
    class DummyLowDexChar(CharacterInstance):
        def get_attribute_bonus(self, attr_name: str) -> int:
            if attr_name.upper() == 'DEX': return -3 # Sehr niedriger DEX-Bonus
            return super().get_attribute_bonus(attr_name)

    low_dex_attacker_def = loader.get_character_class("krieger") # Basis ist egal, überschreiben Bonus
    if low_dex_attacker_def:
        low_dex_attacker = DummyLowDexChar(low_dex_attacker_def)
        low_dex_attacker.name = "Unglücksrabe"

        # Unglücksrabe (DEX-Bonus -3) vs Goblin (DEX-Bonus +1)
        # Chance = 90 + (-3 * 3) - (1 * 2) = 90 - 9 - 2 = 79%
        logger.info(f"\nSzenario 4: {low_dex_attacker.name} (DEX-Bonus {low_dex_attacker.get_attribute_bonus('DEX')}) "
                    f"vs {goblin_inst.name} (DEX-Bonus {goblin_inst.get_attribute_bonus('DEX')})")
        hits = 0
        for i in range(runs):
            if check_hit_success(low_dex_attacker, goblin_inst):
                hits += 1
        logger.info(f"  -> Treffer in {runs} Versuchen: {hits} (Erwartet ca. 7-8 bei 79%)")

    logger.info("\nAlle Tests für combat.py (inkl. Trefferchance) durchgelaufen.")
