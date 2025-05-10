# src/game_logic/combat.py
"""
Modul für die Abwicklung von Kampfaktionen, Trefferberechnung, Schadensanwendung,
Anwendung von Skills und Effekten.
"""
import random
import logging
from typing import List, Optional, Tuple

from src.game_logic.entities import CharacterInstance
from src.definitions.skill import SkillTemplate, SkillEffectData, AppliedEffectData
from src.definitions.loader import load_skill_templates # Um Skill-Objekte zu erhalten
from src.game_logic import formulas
from src.game_logic.effects import create_status_effect, StatusEffect # Zum Erstellen und Anwenden von Effekten

# Erhalte einen Logger für dieses Modul
logger = logging.getLogger(__name__)

# Lade Skill-Definitionen einmalig beim Importieren des Moduls
# Dies dient als Cache für Skill-Objekte.
try:
    SKILL_DEFINITIONS: dict[str, SkillTemplate] = load_skill_templates()
except Exception as e:
    logger.critical(f"FATAL: Skill-Definitionen konnten nicht geladen werden in combat.py: {e}")
    SKILL_DEFINITIONS = {} # Leeres Dict, um Abstürze zu vermeiden, aber Kampf wird nicht funktionieren

class CombatHandler:
    """
    Verwaltet und führt Kampfaktionen zwischen Charakterinstanzen aus.
    """
    def __init__(self):
        # Potenziell Zustand hier speichern, wenn ein Kampf über mehrere Runden geht,
        # z.B. eine Liste der Teilnehmer, aktuelle Runde etc.
        # Für den Moment fokussieren wir uns auf die Ausführung einzelner Aktionen.
        pass

    def _get_skill_template(self, skill_id: str) -> Optional[SkillTemplate]:
        """Holt ein SkillTemplate-Objekt aus den geladenen Definitionen."""
        skill = SKILL_DEFINITIONS.get(skill_id)
        if not skill:
            logger.error(f"Skill-Template mit ID '{skill_id}' nicht gefunden.")
        return skill

    def _check_action_usability(self, actor: CharacterInstance, skill_id: str, target: Optional[CharacterInstance]) -> Tuple[bool, Optional[str], Optional[SkillTemplate]]:
        """Überprüft, ob der Akteur die Aktion (Skill) ausführen kann."""
        if not actor.can_act:
            return False, f"'{actor.name}' kann nicht handeln (z.B. betäubt).", None
        if actor.is_defeated:
            return False, f"'{actor.name}' ist besiegt und kann keine Aktionen ausführen.", None

        skill = self._get_skill_template(skill_id)
        if not skill:
            return False, f"Skill '{skill_id}' unbekannt.", None

        # Ressourcenkosten prüfen
        if not actor.consume_resource(skill.cost.value, skill.cost.type):
            return False, f"Nicht genügend {skill.cost.type} ({actor.name} hat {getattr(actor, 'current_' + skill.cost.type.lower(), 0)}, benötigt {skill.cost.value}).", skill
        
        # TODO: Weitere Prüfungen (Reichweite, Sichtlinie, Waffentyp etc. falls relevant)
        # Zielvalidierung (gibt es ein Ziel, wenn der Skill eines benötigt?)
        if skill.target_type not in ["SELF", "NONE"] and not target: # NONE für Skills ohne Ziel, SELF für Selbst-Skills
             # TODO: Spezifischere Target-Typen wie ALLY_SINGLE, ENEMY_SINGLE etc. prüfen
            if skill.target_type not in ["ENEMY_ALL", "ALLY_ALL", "ENEMY_CLEAVE", "ENEMY_SPLASH"]: # Flächeneffekte könnten ohne spezifisches Primärziel funktionieren
                return False, f"Skill '{skill.name}' erfordert ein Ziel, aber keines wurde angegeben.", skill
        
        return True, None, skill


    def execute_skill_action(self, actor: CharacterInstance, skill_id: str, targets: List[CharacterInstance]):
        """
        Führt eine Skill-Aktion vom Akteur auf die Ziele aus.
        targets: Eine Liste von Zielen. Für Single-Target-Skills ist dies eine Liste mit einem Element.
                 Für AoE-Skills kann sie mehrere Elemente enthalten.
        """
        if not targets: # Keine Ziele angegeben
            logger.warning(f"Keine Ziele für Skill '{skill_id}' von '{actor.name}' angegeben. Aktion abgebrochen.")
            # Ressourcen wiederherstellen, falls sie bereits abgezogen wurden
            # (Dies hängt davon ab, wo consume_resource im Flow aufgerufen wird.
            #  In _check_action_usability wird es bereits abgezogen. Das ist eine Designentscheidung.)
            # skill_temp = self._get_skill_template(skill_id)
            # if skill_temp: actor.restore_resource(skill_temp.cost.value, skill_temp.cost.type)
            return

        primary_target = targets[0] # Das erste Ziel in der Liste ist oft das Primärziel

        can_act, reason, skill = self._check_action_usability(actor, skill_id, primary_target)
        if not can_act or not skill:
            logger.warning(f"Aktion '{skill_id}' von '{actor.name}' auf '{primary_target.name if primary_target else 'N/A'}' fehlgeschlagen: {reason}")
            # Wichtig: Wenn consume_resource in _check_action_usability die Ressourcen bereits abgezogen hat
            # und die Aktion hier fehlschlägt, müssen die Ressourcen zurückgegeben werden!
            # Dies ist ein häufiges Problem in solchen Designs.
            # Option 1: consume_resource erst nach allen Prüfungen aufrufen.
            # Option 2: Ressourcen hier explizit zurückgeben, wenn _check_action_usability True war, aber etwas anderes fehlschlägt.
            # Für den Moment: Wenn _check_action_usability fehlschlägt (can_act=False), wurden Ressourcen NICHT verbraucht,
            # AUSSER die Prüfung auf Ressourcenkosten war der Grund des Fehlschlags.
            # Wenn der Grund der Ressourcenmangel war, ist es korrekt, dass sie nicht verbraucht wurden.
            # Wenn der Grund z.B. "kann nicht handeln" war, dann hat consume_resource nicht stattgefunden.
            # Dies erfordert eine sorgfältige Implementierung von _check_action_usability.
            # AKTUELLE LOGIK: _check_action_usability zieht Ressourcen ab, WENN ALLE ANDEREN PRÜFUNGEN OK WAREN.
            # Wenn also _check_action_usability `False` zurückgibt und `skill` `None` ist, wurden Ressourcen nicht berührt.
            # Wenn `can_act` `False` ist, `skill` aber existiert, bedeutet das, die Ressourcenprüfung schlug fehl.
            if reason and "Nicht genügend" not in reason and skill: # Wenn Aktion aus anderem Grund als Ressourcen fehlschlägt, aber Ressourcen schon weg
                 actor.restore_resource(skill.cost.value, skill.cost.type) # Ressourcen zurückgeben
            return

        logger.info(f"'{actor.name}' setzt Skill '{skill.name}' (ID: {skill_id}) ein.")

        # --- Zielauswahl basierend auf skill.target_type ---
        # Die `targets`-Liste, die übergeben wird, sollte bereits die korrekten Ziele enthalten,
        # basierend auf der KI oder Spielerwahl und dem Skill-Typ.
        # Hier verarbeiten wir diese Liste.

        affected_targets: List[CharacterInstance] = []
        if skill.target_type == "SELF":
            affected_targets = [actor]
        elif skill.target_type == "ENEMY_SINGLE" or skill.target_type == "ALLY_SINGLE":
            if primary_target and not primary_target.is_defeated:
                affected_targets = [primary_target]
        elif skill.target_type == "ENEMY_CLEAVE": # Hauptziel + 1 weiteres (Annahme: targets[0] ist Haupt, targets[1] ist Cleave)
            if primary_target and not primary_target.is_defeated:
                affected_targets.append(primary_target)
            if len(targets) > 1 and targets[1] and not targets[1].is_defeated: # Sekundäres Ziel
                affected_targets.append(targets[1])
        elif skill.target_type == "ENEMY_SPLASH": # Alle übergebenen Ziele
            affected_targets = [t for t in targets if t and not t.is_defeated]
        # TODO: Weitere Target-Typen wie ENEMY_ALL, ALLY_ALL etc.
        else: # Fallback oder unbekannter Typ
            if primary_target and not primary_target.is_defeated:
                affected_targets = [primary_target]
        
        if not affected_targets:
            logger.info(f"Keine gültigen Ziele für '{skill.name}' gefunden.")
            actor.restore_resource(skill.cost.value, skill.cost.type) # Ressourcen zurückgeben
            return

        # --- Effekte auf jedes betroffene Ziel anwenden ---
        for current_target_char in affected_targets:
            logger.debug(f"Verarbeite Skill '{skill.name}' von '{actor.name}' auf Ziel '{current_target_char.name}'.")

            # 1. Trefferchance prüfen (nur für offensive Skills auf Gegner)
            # TODO: Unterscheiden, ob der Skill offensiv ist und ein Trefferwurf nötig ist.
            #       Heilungen oder Buffs auf Verbündete treffen automatisch.
            #       Für den Moment nehmen wir an, dass dies für Schadens-Skills auf Gegner gilt.
            is_offensive_on_enemy = skill.target_type.startswith("ENEMY_") and (skill.direct_effects and skill.direct_effects.base_damage is not None)

            hit_roll_successful = True
            if is_offensive_on_enemy:
                # Genauigkeit des Akteurs, Ausweichen des Ziels
                # TODO: Diese Werte müssten von Status-Effekten beeinflusst werden können.
                #       CharacterInstance.accuracy und .evasion sind Basiswerte.
                #       Wir brauchen effektive Werte. Fürs Erste die Basiswerte.
                hit_chance = formulas.calculate_hit_chance(actor.accuracy, current_target_char.evasion)
                roll = random.randint(1, 100)
                hit_roll_successful = roll <= hit_chance
                
                if hit_roll_successful:
                    logger.info(f"'{actor.name}' trifft '{current_target_char.name}' mit '{skill.name}' (Wurf: {roll} <= Chance: {hit_chance}%).")
                else:
                    logger.info(f"'{actor.name}' verfehlt '{current_target_char.name}' mit '{skill.name}' (Wurf: {roll} > Chance: {hit_chance}%).")
                    # Wenn verfehlt, werden weder Schaden noch Statuseffekte des Skills angewendet.
                    continue # Nächstes Ziel, falls AoE

            # 2. Direkte Effekte anwenden (Schaden/Heilung)
            if skill.direct_effects:
                effect_data: SkillEffectData = skill.direct_effects
                
                # Basisschaden des Skills (kann von game_settings.base_weapon_damage kommen)
                base_skill_damage = effect_data.base_damage
                if base_skill_damage is None and CONFIG: # base_damage: null -> nutze Standardwaffenschaden
                    base_skill_damage = CONFIG.get("game_settings.base_weapon_damage", 5)
                elif base_skill_damage is None: # Fallback, falls CONFIG nicht da
                    base_skill_damage = 5
                
                # Attributbonus des Akteurs
                actor_attr_bonus = 0
                if effect_data.scaling_attribute:
                    actor_attr_bonus = actor.get_attribute_bonus(effect_data.scaling_attribute)
                
                # Kritischer Treffer? (Nur für Schaden)
                is_critical_hit = False
                if effect_data.base_damage is not None: # Nur für Schadensskills
                    crit_chance_roll = random.random() # 0.0 bis 1.0
                    if crit_chance_roll < effect_data.bonus_crit_chance: # bonus_crit_chance ist 0-1
                        is_critical_hit = True
                        logger.info(f"KRITISCHER TREFFER von '{actor.name}' auf '{current_target_char.name}'!")

                if effect_data.base_damage is not None: # Schadenslogik
                    raw_damage = formulas.calculate_damage(
                        base_damage_skill=base_skill_damage,
                        attribute_bonus=actor_attr_bonus,
                        multiplier_skill=effect_data.multiplier,
                        critical_hit=is_critical_hit,
                        critical_multiplier=effect_data.critical_multiplier
                    )
                    # TODO: Bonusschaden gegen bestimmte Tags (effect_data.bonus_damage_vs_tags)
                    
                    # TODO: Schadens-Typ berücksichtigen (effect_data.damage_type)
                    current_target_char.take_damage(raw_damage, damage_type=effect_data.damage_type or "PHYSICAL")
                
                elif effect_data.base_healing is not None: # Heilungslogik
                    # Heilung trifft normalerweise automatisch, keine Trefferchance-Prüfung
                    raw_healing = math.floor( # Nutze math.floor oder ceil nach Bedarf
                        (effect_data.base_healing + actor_attr_bonus) * effect_data.healing_multiplier
                    )
                    current_target_char.heal(raw_healing)

            # 3. Status-Effekte anwenden (applies_effects)
            if skill.applied_status_effects:
                for applied_effect_data in skill.applied_status_effects:
                    # Anwendungschance prüfen
                    if random.random() > applied_effect_data.application_chance: # Chance ist 0.0-1.0
                        logger.debug(f"Anwendung von Effekt '{applied_effect_data.effect_id}' auf '{current_target_char.name}' fehlgeschlagen (Chance: {applied_effect_data.application_chance:.0%}).")
                        continue

                    # Neuen Effekt erstellen
                    new_effect = create_status_effect(
                        effect_id=applied_effect_data.effect_id,
                        target=current_target_char,
                        source_actor=actor,
                        duration_rounds=applied_effect_data.duration_rounds,
                        potency=applied_effect_data.potency,
                        scales_with_attribute=applied_effect_data.scales_with_attribute,
                        attribute_potency_multiplier=applied_effect_data.attribute_potency_multiplier
                    )
                    
                    if new_effect:
                        # Prüfen, ob ein Effekt desselben Typs bereits auf dem Ziel ist
                        existing_effect: Optional[StatusEffect] = None
                        for eff in current_target_char.status_effects:
                            if eff.effect_id == new_effect.effect_id:
                                existing_effect = eff
                                break
                        
                        if existing_effect:
                            if not existing_effect.is_stackable: # Standardverhalten: nicht stapelbar
                                # Effekt auffrischen (gemäß ANNEX: Dauer MAX, Stärke überschreiben)
                                existing_effect.refresh(
                                    new_duration=applied_effect_data.duration_rounds, 
                                    new_potency=applied_effect_data.potency,
                                    new_scales_with_attribute=applied_effect_data.scales_with_attribute,
                                    new_attribute_potency_multiplier=applied_effect_data.attribute_potency_multiplier
                                )
                                logger.info(f"Status-Effekt '{existing_effect.name}' auf '{current_target_char.name}' aufgefrischt.")
                            else:
                                # TODO: Logik für stapelbare Effekte (selten, aber möglich)
                                current_target_char.status_effects.append(new_effect)
                                new_effect.on_apply()
                        else: # Effekt ist neu auf dem Ziel
                            current_target_char.status_effects.append(new_effect)
                            new_effect.on_apply()
        
        # TODO: XP-Vergabe, wenn ein Gegner durch die Aktion besiegt wurde.
        # Dies sollte außerhalb dieser Funktion geschehen, nachdem alle Aktionen einer Runde/eines Kampfes abgeschlossen sind.

# --- Hilfsfunktionen für den Kampfablauf (optional hier oder in einer Kampfmanager-Klasse) ---

def get_initiative_order(participants: List[CharacterInstance]) -> List[CharacterInstance]:
    """Sortiert eine Liste von Kampfteilnehmern nach ihrer aktuellen Initiative (höchste zuerst)."""
    # Bei Gleichstand könnte man eine zweite Sortierregel (z.B. DEX, Zufall) hinzufügen.
    return sorted(participants, key=lambda p: p.current_initiative, reverse=True)

def process_beginning_of_turn_effects(character: CharacterInstance):
    """Verarbeitet Status-Effekte, die zu Beginn des Zuges ausgelöst werden (on_tick)."""
    if character.is_defeated:
        return

    logger.debug(f"--- Beginn des Zuges für {character.name} ---")
    effects_to_remove: List[StatusEffect] = []
    
    # Kopie der Liste, da Effekte sich selbst entfernen könnten während der Iteration
    for effect in list(character.status_effects): 
        effect.on_tick() # Führt Schaden über Zeit etc. aus
        if character.is_defeated: # Effekt-Tick könnte den Charakter besiegen
            logger.debug(f"{character.name} wurde durch einen Effekt-Tick besiegt.")
            break # Keine weiteren Ticks für diesen Charakter in dieser Runde
            
        if effect.tick_duration(): # Reduziert Dauer und prüft, ob abgelaufen
            effects_to_remove.append(effect)
            
    for eff_rem in effects_to_remove:
        eff_rem.on_remove()
        if eff_rem in character.status_effects: # Sicherstellen, dass es noch da ist
            character.status_effects.remove(eff_rem)

    # Schildpunkte können durch Effekte (wie Burning) direkt reduziert werden, ohne take_damage
    # Sicherstellen, dass Schildpunkte nicht negativ werden, falls Effekte sie direkt manipulieren.
    if character.shield_points < 0: character.shield_points = 0

if __name__ == '__main__':
    import math # Für ceil/floor in Heilungsberechnung oben, falls math nicht schon importiert wurde
    from src.definitions.loader import load_character_templates, load_opponent_templates
    from src.config.config import CONFIG # Stellt sicher, dass CONFIG geladen ist

    print("\n--- Teste CombatHandler ---")
    
    # Setup (ähnlich wie im entities-Test)
    try:
        char_templates = load_character_templates()
        opp_templates = load_opponent_templates()

        krieger_template = char_templates["krieger"]
        magier_template = char_templates["magier"]
        goblin_template = opp_templates["goblin_lv1"]
        goblin_shaman_template = opp_templates.get("goblin_shaman_lv3") # Hat Heal-Skill
        if not goblin_shaman_template: raise ValueError("Goblin Schamane nicht gefunden")


        spieler_krieger = CharacterInstance(base_template=krieger_template, name_override="Krieger Test")
        spieler_magier = CharacterInstance(base_template=magier_template, name_override="Magier Test")
        gegner_goblin1 = CharacterInstance(base_template=goblin_template, name_override="Goblin Alpha")
        gegner_goblin2 = CharacterInstance(base_template=goblin_template, name_override="Goblin Beta")
        gegner_shaman = CharacterInstance(base_template=goblin_shaman_template, name_override="Goblin Schamane")
        
        # Anpassung der Attribute für Testzwecke
        spieler_krieger.accuracy = 10 # Um Trefferchance zu erhöhen
        spieler_krieger.attributes["STR"] = 16 # Bonus +3
        spieler_magier.attributes["INT"] = 18 # Bonus +4
        gegner_goblin1.evasion = 2 # Um Ausweichen zu testen

        combat_handler = CombatHandler()

        print("\n-- Test: Krieger (STR 16) greift Goblin Alpha (HP 50, Armor 2) mit 'power_strike' an --")
        # Power Strike: base 6, STR scaling, x1.5
        # Erwarteter Schaden: (6 Basis + 3 STR-Bonus) * 1.5 = 9 * 1.5 = 13.5 -> floor(13) = 13
        # Reduziert um Rüstung 2 -> 11 Schaden.
        # Kritisch: (13 * 1.5 KritMult) = 19.5 -> floor(19) = 19. Reduziert um 2 -> 17.
        print(f"Vor Angriff: {gegner_goblin1.name} HP: {gegner_goblin1.current_hp}")
        combat_handler.execute_skill_action(actor=spieler_krieger, skill_id="power_strike", targets=[gegner_goblin1])
        print(f"Nach Angriff: {gegner_goblin1.name} HP: {gegner_goblin1.current_hp}")
        
        print("\n-- Test: Magier (INT 18) greift Goblin Beta (HP 50, MagRes 0) mit 'fireball' an --")
        # Fireball: base 8, INT scaling, x1.5. Applies BURNING (Pot 3, Dur 2R)
        # Erwarteter Schaden: (8 Basis + 4 INT-Bonus) * 1.5 = 12 * 1.5 = 18
        # BURNING Potency: 3 (Basis) + (4 INT Bonus * 0.0 Skalierung, wenn nicht im Skill definiert) -> für Test mit Skalierung:
        # Annahme: Skill "fireball" in JSON hat scales_with_attribute="INT", attribute_potency_multiplier=0.25 für den Effekt
        # Dann wäre Burning Potency = 3 + (4 * 0.25) = 3 + 1 = 4
        # Hier wird die Definition aus skills.json5 genommen, die keine Skalierung für Burning hat. Potency bleibt 3.
        print(f"Vor Angriff: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {len(gegner_goblin2.status_effects)}")
        combat_handler.execute_skill_action(actor=spieler_magier, skill_id="fireball", targets=[gegner_goblin2])
        print(f"Nach Angriff: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {gegner_goblin2.status_effects}")

        print("\n-- Test: Tick-Effekte für Goblin Beta (Burning) --")
        process_beginning_of_turn_effects(gegner_goblin2) # 1. Tick
        print(f"Nach 1. Tick: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {gegner_goblin2.status_effects}")
        process_beginning_of_turn_effects(gegner_goblin2) # 2. Tick
        print(f"Nach 2. Tick: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {gegner_goblin2.status_effects}") # Effekt sollte weg sein, wenn Dauer 2R
        process_beginning_of_turn_effects(gegner_goblin2) # 3. Tick (Effekt sollte weg sein)
        print(f"Nach 3. Tick: {gegner_goblin2.name} HP: {gegner_goblin2.current_hp}, Effekte: {gegner_goblin2.status_effects}")

        print("\n-- Test: Goblin Schamane (WIS 12) heilt Goblin Alpha mit 'heal_lesser' --")
        # heal_lesser: base_heal 10, WIS scaling, heal_multiplier 0.3
        # WIS 12 -> Bonus +1
        # Erwartete Heilung: (10 Basis + 1 WIS-Bonus) * 0.3 = 11 * 0.3 = 3.3 -> floor(3) = 3
        gegner_goblin1.current_hp = 10 # Setze HP niedrig für Test
        print(f"Vor Heilung: {gegner_goblin1.name} HP: {gegner_goblin1.current_hp}")
        combat_handler.execute_skill_action(actor=gegner_shaman, skill_id="heal_lesser", targets=[gegner_goblin1])
        print(f"Nach Heilung: {gegner_goblin1.name} HP: {gegner_goblin1.current_hp}")

        print("\n-- Test: Initiative-Reihenfolge --")
        spieler_krieger.current_initiative = 20
        spieler_magier.current_initiative = 15
        gegner_goblin1.current_initiative = 18
        teilnehmer = [spieler_magier, gegner_goblin1, spieler_krieger]
        geordnete_teilnehmer = get_initiative_order(teilnehmer)
        print("Erwartete Reihenfolge: Krieger (20), Goblin (18), Magier (15)")
        print(f"Tatsächliche Reihenfolge: {[p.name for p in geordnete_teilnehmer]}")
        
        print("\n-- Test: Krieger (Kosten: 5 Stamina) greift mit 'basic_strike_phys' an --")
        # basic_strike_phys: Kosten 5 Stamina
        print(f"Krieger Stamina vor basic_strike_phys: {spieler_krieger.current_stamina}")
        combat_handler.execute_skill_action(actor=spieler_krieger, skill_id="basic_strike_phys", targets=[gegner_goblin1])
        print(f"Krieger Stamina nach basic_strike_phys: {spieler_krieger.current_stamina}")
        print(f"Goblin HP nach basic_strike_phys: {gegner_goblin1.current_hp}")

        print("\n-- Test: Magier wirkt 'arcane_barrier' (Schild) auf sich selbst --")
        # arcane_barrier: Potency 15 (aus JSON, keine Skalierung definiert)
        print(f"Magier Schild vor arcane_barrier: {spieler_magier.shield_points}")
        combat_handler.execute_skill_action(actor=spieler_magier, skill_id="arcane_barrier", targets=[spieler_magier])
        print(f"Magier Schild nach arcane_barrier: {spieler_magier.shield_points}")
        print(f"Magier Status Effekte: {spieler_magier.status_effects}")


    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in combat.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in combat.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- Combat-Tests abgeschlossen ---")