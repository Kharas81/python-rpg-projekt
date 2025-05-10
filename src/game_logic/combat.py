# src/game_logic/combat.py
"""
Modul für die Abwicklung von Kampfaktionen, Trefferberechnung, Schadensanwendung,
Anwendung von Skills und Effekten.
"""
import random
import logging
import math 
from typing import List, Optional, Tuple, Dict 

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillTemplate, SkillEffectData 
# AppliedEffectData wird nicht mehr direkt hier benötigt, da skill.applied_status_effects Objekte enthält
from src.definitions.loader import load_skill_templates 
from src.game_logic import formulas
from src.game_logic.effects import create_status_effect, StatusEffect 
from src.ui import cli_output # Import für Miss, Damage, Heal etc.

logger = logging.getLogger(__name__)

try:
    from src.config.config import CONFIG
except ImportError:
    logger.critical("FATAL: Konfigurationsmodul src.config.config konnte nicht importiert werden in combat.py.")
    CONFIG = None 

try:
    SKILL_DEFINITIONS: Dict[str, SkillTemplate] = load_skill_templates()
except Exception as e:
    logger.critical(f"FATAL: Skill-Definitionen konnten nicht geladen werden in combat.py: {e}")
    SKILL_DEFINITIONS = {}

class CombatHandler:
    def __init__(self):
        pass

    def _get_skill_template(self, skill_id: str) -> Optional[SkillTemplate]:
        skill = SKILL_DEFINITIONS.get(skill_id)
        if not skill:
            logger.error(f"Skill-Template mit ID '{skill_id}' nicht gefunden.")
        return skill

    def _check_action_usability(self, actor: CharacterInstance, skill_id: str, target: Optional[CharacterInstance]) -> Tuple[bool, Optional[str], Optional[SkillTemplate]]:
        if not actor.can_act:
            return False, f"'{actor.name}' kann nicht handeln (z.B. betäubt).", None
        if actor.is_defeated:
            return False, f"'{actor.name}' ist besiegt und kann keine Aktionen ausführen.", None

        skill = self._get_skill_template(skill_id)
        if not skill:
            return False, f"Skill '{skill_id}' unbekannt.", None
        
        if not actor.can_afford_skill(skill): # Verwendet die neue Methode in CharacterInstance
             return False, f"Nicht genügend {skill.cost.type} ({actor.name} hat {getattr(actor, 'current_' + skill.cost.type.lower(), 0)}, benötigt {skill.cost.value}).", skill
        
        if skill.target_type not in ["SELF", "NONE"] and not target: # NONE für Skills ohne Ziel
            # Spezifischere Target-Typen wie ALLY_SINGLE, ENEMY_SINGLE etc. erfordern ein Ziel.
            # Flächeneffekte könnten ohne spezifisches Primärziel funktionieren, wenn die Zielliste entsprechend gefüllt wird.
            if skill.target_type not in ["ENEMY_ALL", "ALLY_ALL", "ENEMY_CLEAVE", "ENEMY_SPLASH"]: 
                return False, f"Skill '{skill.name}' erfordert ein Ziel, aber keines wurde angegeben.", skill
        
        return True, None, skill

    def execute_skill_action(self, actor: CharacterInstance, skill_id: str, targets: List[CharacterInstance]):
        if not targets or not targets[0]: 
            logger.warning(f"Keine (gültigen) Primärziele für Skill '{skill_id}' von '{actor.name}' angegeben. Aktion abgebrochen.")
            return

        primary_target = targets[0] 
        can_act_check, reason_check, skill = self._check_action_usability(actor, skill_id, primary_target)
        
        if not can_act_check or not skill:
            logger.warning(f"Aktion '{skill_id}' von '{actor.name}' auf '{primary_target.name if primary_target else 'N/A'}' fehlgeschlagen (Vorabprüfung): {reason_check}")
            return

        if not actor.consume_resource(skill.cost.value, skill.cost.type):
            logger.warning(f"Aktion '{skill_id}' von '{actor.name}' fehlgeschlagen: Nicht genügend {skill.cost.type} (beim Versuch zu verbrauchen).")
            return

        logger.info(f"'{actor.name}' führt Skill '{skill.name}' (ID: {skill_id}) aus.")

        affected_targets: List[CharacterInstance] = []
        if skill.target_type == "SELF":
            affected_targets = [actor]
        elif skill.target_type in ["ENEMY_SINGLE", "ALLY_SINGLE"]:
            if primary_target and not primary_target.is_defeated:
                affected_targets = [primary_target]
        elif skill.target_type == "ENEMY_CLEAVE": 
            if primary_target and not primary_target.is_defeated:
                affected_targets.append(primary_target)
            # Füge bis zu N weitere Ziele hinzu, wenn targets mehr Elemente enthält
            # Hier vereinfacht: Nur das nächste Ziel in der 'targets'-Liste
            if len(targets) > 1 and targets[1] and not targets[1].is_defeated: 
                affected_targets.append(targets[1])
        elif skill.target_type == "ENEMY_SPLASH": 
            affected_targets = [t for t in targets if t and not t.is_defeated]
        # TODO: ALLY_ALL, ENEMY_ALL
        else: # Fallback oder unbekannter Typ, der ein Ziel erwartet
            if primary_target and not primary_target.is_defeated:
                affected_targets = [primary_target]
        
        if not affected_targets:
            logger.info(f"Keine gültigen Ziele für '{skill.name}' nach Filterung gefunden.")
            actor.restore_resource(skill.cost.value, skill.cost.type) # Ressourcen zurückgeben
            return

        for current_target_char in affected_targets:
            logger.debug(f"Verarbeite Skill '{skill.name}' von '{actor.name}' auf Ziel '{current_target_char.name}'.")

            # KORRIGIERTE Logik für is_offensive_skill und is_offensive_on_enemy
            is_offensive_skill = skill.direct_effects and \
                                 (skill.direct_effects.base_damage is not None or \
                                  (skill.direct_effects.base_damage is None and CONFIG and CONFIG.get("game_settings.base_weapon_damage") is not None))
            
            is_offensive_on_enemy = skill.target_type.startswith("ENEMY_") and is_offensive_skill
            hit_roll_successful = True 

            if is_offensive_on_enemy:
                hit_chance = formulas.calculate_hit_chance(actor.accuracy, current_target_char.evasion)
                roll = random.randint(1, 100)
                hit_roll_successful = roll <= hit_chance
                
                if hit_roll_successful:
                    logger.info(f"'{actor.name}' trifft '{current_target_char.name}' mit '{skill.name}' (Wurf: {roll} <= Chance: {hit_chance}%).")
                else:
                    logger.info(f"'{actor.name}' verfehlt '{current_target_char.name}' mit '{skill.name}' (Wurf: {roll} > Chance: {hit_chance}%).")
                    cli_output.display_miss(actor.name, current_target_char.name, skill.name)
                    continue 

            if hit_roll_successful: # Nur fortfahren, wenn Treffer erfolgreich war (oder nicht relevant war)
                if skill.direct_effects:
                    effect_data: SkillEffectData = skill.direct_effects
                    base_skill_damage_val = effect_data.base_damage
                    
                    # Zugriff auf CONFIG absichern
                    cfg_base_weapon_damage = 5 # Fallback
                    if CONFIG and hasattr(CONFIG, 'get'):
                        cfg_base_weapon_damage = CONFIG.get("game_settings.base_weapon_damage", 5)

                    if base_skill_damage_val is None: 
                        base_skill_damage_val = cfg_base_weapon_damage
                    
                    actor_attr_bonus = 0
                    if effect_data.scaling_attribute:
                        actor_attr_bonus = actor.get_attribute_bonus(effect_data.scaling_attribute)
                    
                    is_critical_hit = False
                    # Kritische Treffer nur für Schadens-Skills (offensive Skills)
                    if is_offensive_skill: # Verwende die bereits definierte Variable
                        crit_chance_roll = random.random() 
                        if crit_chance_roll < effect_data.bonus_crit_chance:
                            is_critical_hit = True
                            logger.info(f"KRITISCHER TREFFER von '{actor.name}' auf '{current_target_char.name}'!")
                            cli_output.print_message(f"KRITISCHER TREFFER von {actor.name}!", cli_output.Colors.LIGHT_YELLOW + cli_output.Colors.BOLD)

                    # Schadenslogik (nur wenn es ein offensiver Skill ist)
                    if is_offensive_skill: 
                        raw_damage = formulas.calculate_damage(
                            base_damage_skill=base_skill_damage_val,
                            attribute_bonus=actor_attr_bonus,
                            multiplier_skill=effect_data.multiplier,
                            critical_hit=is_critical_hit,
                            critical_multiplier=effect_data.critical_multiplier
                        )
                        damage_type_to_apply = effect_data.damage_type if effect_data.damage_type else "PHYSICAL"
                        shield_before_damage = current_target_char.shield_points
                        current_target_char.take_damage(raw_damage, damage_type=damage_type_to_apply) 
                        shield_absorbed = shield_before_damage - current_target_char.shield_points
                        if shield_absorbed < 0: shield_absorbed = 0 
                        
                        cli_output.display_damage_taken(
                            current_target_char.name, 
                            raw_damage, 
                            damage_type_to_apply,
                            current_target_char.current_hp,
                            current_target_char.max_hp,
                            absorbed_by_shield=shield_absorbed
                        )
                    
                    # Heilungslogik
                    elif effect_data.base_healing is not None: 
                        raw_healing = math.floor( 
                            (effect_data.base_healing + actor_attr_bonus) * effect_data.healing_multiplier
                        )
                        healed_amount = current_target_char.heal(raw_healing)
                        if healed_amount > 0:
                            cli_output.display_healing_received(
                                current_target_char.name,
                                healed_amount,
                                current_target_char.current_hp,
                                current_target_char.max_hp
                            )

                if skill.applied_status_effects: 
                    for applied_effect_obj in skill.applied_status_effects: 
                        if random.random() > applied_effect_obj.application_chance:
                            logger.debug(f"Anwendung von Effekt '{applied_effect_obj.effect_id}' auf '{current_target_char.name}' fehlgeschlagen (Chance: {applied_effect_obj.application_chance:.0%}).")
                            continue

                        new_effect = create_status_effect(
                            effect_id=applied_effect_obj.effect_id,
                            target=current_target_char,
                            source_actor=actor,
                            duration_rounds=applied_effect_obj.duration_rounds,
                            potency=applied_effect_obj.potency,
                            scales_with_attribute=applied_effect_obj.scales_with_attribute,
                            attribute_potency_multiplier=applied_effect_obj.attribute_potency_multiplier
                        )
                        if new_effect:
                            existing_effect = next((eff for eff in current_target_char.status_effects if eff.effect_id == new_effect.effect_id), None)
                            if existing_effect and not existing_effect.is_stackable:
                                existing_effect.refresh(
                                    new_duration=applied_effect_obj.duration_rounds, 
                                    new_potency=applied_effect_obj.potency,
                                    new_scales_with_attribute=applied_effect_obj.scales_with_attribute,
                                    new_attribute_potency_multiplier=applied_effect_obj.attribute_potency_multiplier
                                )
                                logger.info(f"Status-Effekt '{existing_effect.name}' auf '{current_target_char.name}' aufgefrischt.")
                            else: # Neu oder stapelbar
                                current_target_char.status_effects.append(new_effect)
                                new_effect.on_apply()
                                cli_output.display_status_effect_applied(current_target_char.name, new_effect.name, new_effect.remaining_duration)
        
def get_initiative_order(participants: List[CharacterInstance]) -> List[CharacterInstance]:
    return sorted(participants, key=lambda p: p.current_initiative, reverse=True)

def process_beginning_of_turn_effects(character: CharacterInstance):
    if character.is_defeated: return
    logger.debug(f"--- Beginn des Zuges für {character.name} ---")
    effects_to_remove: List[StatusEffect] = []
    
    for effect in list(character.status_effects): 
        effect.on_tick() 
        if character.is_defeated: 
            logger.debug(f"{character.name} wurde durch einen Effekt-Tick besiegt.")
            # Hier könnte man cli_output.display_character_status oder eine spezielle Nachricht ausgeben
            break             
        if effect.tick_duration(): 
            effects_to_remove.append(effect)
            
    for eff_rem in effects_to_remove:
        eff_rem.on_remove()
        if eff_rem in character.status_effects: 
            character.status_effects.remove(eff_rem)
            cli_output.display_status_effect_removed(character.name, eff_rem.name)

    if character.shield_points < 0: character.shield_points = 0

if __name__ == '__main__':
    from src.definitions.loader import load_character_templates, load_opponent_templates
    print("\n--- Teste CombatHandler ---")
    try:
        if CONFIG is None:
            print("WARNUNG: Globale CONFIG konnte nicht geladen werden, Tests könnten unzuverlässig sein.")
            class DummyConfig: # Minimaler Fallback für Tests
                def get(self, key, default=None):
                    if key == "game_settings.base_weapon_damage": return 5
                    if key == "game_settings.min_damage": return 1
                    return default if default is not None else 0
            _CONFIG_TEST_FALLBACK = DummyConfig() 
            # Im echten Lauf wird die globale CONFIG verwendet. Für Tests muss sie da sein.
            # Wenn CONFIG None ist, wird der Test wahrscheinlich fehlschlagen,
            # da die Formeln CONFIG erwarten.
            if CONFIG is None and _CONFIG_TEST_FALLBACK is not None: # Nur für diesen Testblock überschreiben
                 # Dieses Überschreiben der globalen Variable ist nur für den Test hier gedacht
                 # und nicht ideal, aber stellt sicher, dass die Tests laufen.
                 globals()['CONFIG'] = _CONFIG_TEST_FALLBACK # Pythonische Art, globale Variable zu setzen
                 print("HINWEIS: Globale CONFIG wurde für Tests mit DummyConfig überschrieben.")


        char_templates = load_character_templates()
        opp_templates = load_opponent_templates()
        
        # Lade Skills hier explizit, um sicherzustellen, dass SKILL_DEFINITIONS gefüllt ist
        if not SKILL_DEFINITIONS:
            print("Lade Skills explizit für CombatHandler-Test...")
            SKILL_DEFINITIONS.update(load_skill_templates())


        krieger_template = char_templates["krieger"]
        magier_template = char_templates["magier"]
        goblin_template = opp_templates["goblin_lv1"]
        goblin_shaman_template = opp_templates.get("goblin_shaman_lv3") 
        if not goblin_shaman_template: raise ValueError("Goblin Schamane nicht gefunden")

        spieler_krieger = CharacterInstance(base_template=krieger_template, name_override="Krieger Test")
        spieler_magier = CharacterInstance(base_template=magier_template, name_override="Magier Test")
        gegner_goblin1 = CharacterInstance(base_template=goblin_template, name_override="Goblin Alpha")
        gegner_goblin2 = CharacterInstance(base_template=goblin_template, name_override="Goblin Beta")
        gegner_shaman = CharacterInstance(base_template=goblin_shaman_template, name_override="Goblin Schamane")
        
        spieler_krieger.accuracy = 10 
        spieler_krieger.attributes["STR"] = 16 
        spieler_magier.attributes["INT"] = 18 
        gegner_goblin1.evasion = 2 
        
        gegner_goblin1.current_stamina = 100 # Stellen sicher, dass Gegner Ressourcen haben
        gegner_goblin1.accuracy = 5 # Geben wir dem Goblin etwas Genauigkeit
        gegner_goblin2.current_stamina = 100
        gegner_shaman.current_mana = 100
        spieler_krieger.current_stamina = 100 
        spieler_magier.current_mana = 100   

        combat_handler = CombatHandler()

        print("\n-- Test: Goblin Alpha greift Krieger Test mit 'basic_strike_phys' an --")
        # Annahme: basic_strike_phys kostet 0, base_damage ist null (nutzt Waffenschaden 5)
        # Goblin STR 8 -> Bonus -1. Waffenschaden 5. (5 + (-1)) * 1.0 = 4.
        # Krieger Rüstung 5. 4 - 5 = -1. Min Schaden 1.
        print(f"Vor Angriff: {spieler_krieger.name} HP: {spieler_krieger.current_hp}")
        combat_handler.execute_skill_action(actor=gegner_goblin1, skill_id="basic_strike_phys", targets=[spieler_krieger])
        print(f"Nach Angriff: {spieler_krieger.name} HP: {spieler_krieger.current_hp}")


        print("\n-- Test: Krieger (STR 16) greift Goblin Alpha (HP aktuell, Armor 2) mit 'power_strike' an --")
        print(f"Vor Angriff: {gegner_goblin1.name} HP: {gegner_goblin1.current_hp}")
        combat_handler.execute_skill_action(actor=spieler_krieger, skill_id="power_strike", targets=[gegner_goblin1])
        print(f"Nach Angriff: {gegner_goblin1.name} HP: {gegner_goblin1.current_hp}")
        
        print("\n-- Test: Magier (INT 18) greift Goblin Beta (HP aktuell, MagRes 0) mit 'fireball' an --")
        print(f"Vor Angriff: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {len(gegner_goblin2.status_effects)}")
        combat_handler.execute_skill_action(actor=spieler_magier, skill_id="fireball", targets=[gegner_goblin2])
        print(f"Nach Angriff: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {gegner_goblin2.status_effects}")

        print("\n-- Test: Tick-Effekte für Goblin Beta (Burning) --")
        process_beginning_of_turn_effects(gegner_goblin2) 
        print(f"Nach 1. Tick: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {gegner_goblin2.status_effects}")
        process_beginning_of_turn_effects(gegner_goblin2) 
        print(f"Nach 2. Tick: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {gegner_goblin2.status_effects}") 
        process_beginning_of_turn_effects(gegner_goblin2) 
        print(f"Nach 3. Tick: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {gegner_goblin2.status_effects}")

    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in combat.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in combat.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    print("\n--- Combat-Tests abgeschlossen ---")