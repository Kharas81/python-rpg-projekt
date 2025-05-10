# src/ai/strategies/basic_ranged.py
"""
Einfache Fernkampf-KI-Strategie.
Priorisiert taktische Ziele und Skills mit Status-Effekten.
"""
import random
import logging
from typing import Optional, List, Dict, Any, Tuple

# Importe für Typ-Annotationen und Zugriff auf Spielobjekte
if True: 
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate
    from src.definitions.character import CharacterTemplate # Für Ressourcentyp-Prüfung

logger = logging.getLogger(__name__)

class BasicRangedStrategy:
    """
    Eine KI-Strategie für Fernkämpfer.
    - Zielauswahl: Priorisiert Zauberkundige, dann schwächste Ziele.
    - Skill-Auswahl: Bevorzugt Skills mit Status-Effekten.
    """
    def __init__(self, actor: 'CharacterInstance', skill_definitions: Dict[str, 'SkillTemplate'], character_definitions: Dict[str, 'CharacterTemplate']):
        self.actor = actor
        self.skill_definitions = skill_definitions
        self.character_definitions = character_definitions # Um z.B. Ressourcentypen von Zielen zu prüfen

    def _is_target_caster_type(self, target: 'CharacterInstance') -> bool:
        """Prüft, ob das Ziel ein Zauberkundiger ist (z.B. Magier, Kleriker)."""
        if isinstance(target.base_template, CharacterTemplate): # Nur für Spieler-Charakter-Templates sinnvoll
            # Überprüfe den Ressourcentyp oder spezifische Klassen-IDs/Tags
            # Hier Annahme: Magier und Kleriker nutzen MANA als Hauptressource
            # ANNEX_GAME_DEFINITIONS_SUMMARY.md: Magier/Kleriker -> MANA
            if target.base_template.resource_type == "MANA":
                return True
            # Man könnte auch auf IDs prüfen: target.base_template.id in ["magier", "kleriker"]
        elif isinstance(target.base_template, OpponentTemplate): # Für Gegner
            # Gegner-Templates könnten Tags wie "CASTER" haben
            if "CASTER" in target.base_template.tags:
                return True
        return False

    def _skill_applies_debuff(self, skill_id: str) -> bool:
        """Prüft, ob ein Skill einen negativen Status-Effekt (Debuff) anwendet."""
        skill = self.skill_definitions.get(skill_id)
        if skill and skill.applied_status_effects:
            # Einfache Annahme: Jeder Statuseffekt, der nicht explizit positiv ist, ist ein Debuff
            # Eine genauere Prüfung würde das 'is_positive' Flag des StatusEffect selbst benötigen,
            # was wir hier nicht direkt haben (nur die SkillTemplate.AppliedEffectData).
            # Für den Moment gehen wir davon aus, dass die meisten angewendeten Effekte Debuffs sind,
            # oder wir könnten eine Blacklist/Whitelist von Effekt-IDs führen.
            # Hier nehmen wir an, dass 'applied_status_effects' meistens Debuffs sind.
            return True # Vereinfachung
        return False

    def choose_target(self, potential_targets: List['CharacterInstance']) -> Optional['CharacterInstance']:
        """
        Wählt ein Ziel aus einer Liste potenzieller Ziele.
        - 70% Chance, einen Zauberkundigen anzugreifen, falls vorhanden.
        - Sonst: 60% Chance, das Ziel mit den prozentual niedrigsten HP anzugreifen.
        - Rest zufällig.
        """
        if not potential_targets:
            return None

        valid_targets = [t for t in potential_targets if not t.is_defeated]
        if not valid_targets:
            return None

        caster_targets = [t for t in valid_targets if self._is_target_caster_type(t)]

        chosen_target: Optional[CharacterInstance] = None

        # 70% Chance für Caster-Ziel, wenn vorhanden
        if caster_targets and random.random() < 0.70:
            chosen_target = random.choice(caster_targets)
            logger.debug(f"'{self.actor.name}' (BasicRanged) wählt Caster-Ziel: '{chosen_target.name}'.")
        else:
            # 60% Chance für schwächstes Ziel (prozentuale HP)
            if random.random() < 0.60:
                valid_targets.sort(key=lambda t: (t.current_hp / t.max_hp) if t.max_hp > 0 else float('inf'))
                chosen_target = valid_targets[0]
                logger.debug(f"'{self.actor.name}' (BasicRanged) wählt schwächstes Ziel: '{chosen_target.name}' "
                             f"({chosen_target.current_hp}/{chosen_target.max_hp} HP).")
            else:
                chosen_target = random.choice(valid_targets)
                logger.debug(f"'{self.actor.name}' (BasicRanged) wählt zufälliges Ziel: '{chosen_target.name}'.")
        
        return chosen_target

    def choose_skill(self, available_skills: List[str], target: Optional['CharacterInstance']) -> Optional[str]:
        """
        Wählt einen Skill aus der Liste der verfügbaren Skills des Akteurs.
        - Bevorzugt Skills mit Status-Effekten (60% Chance).
        - Sonst wählt den Skill mit dem höchsten potenziellen Schaden.
        """
        if not available_skills:
            return None

        # Filtere Skills, die der Akteur tatsächlich nutzen kann (Ressourcen etc.)
        usable_skills = []
        for skill_id in available_skills:
            skill_template = self.skill_definitions.get(skill_id)
            if skill_template:
                # Einfache Ressourcenprüfung
                can_afford = False
                cost_type_upper = skill_template.cost.type.upper()
                if cost_type_upper == "NONE":
                    can_afford = True
                elif cost_type_upper == "MANA" and self.actor.current_mana >= skill_template.cost.value:
                    can_afford = True
                elif cost_type_upper == "STAMINA" and self.actor.current_stamina >= skill_template.cost.value:
                    can_afford = True
                elif cost_type_upper == "ENERGY" and self.actor.current_energy >= skill_template.cost.value:
                    can_afford = True
                
                if can_afford:
                    usable_skills.append(skill_id)
        
        if not usable_skills:
            return None

        skills_with_debuffs = [s_id for s_id in usable_skills if self._skill_applies_debuff(s_id)]

        chosen_skill_id: Optional[str] = None

        # 60% Chance, einen Skill mit Debuff zu wählen, wenn vorhanden
        if skills_with_debuffs and random.random() < 0.60:
            chosen_skill_id = random.choice(skills_with_debuffs)
            logger.debug(f"'{self.actor.name}' (BasicRanged) wählt Skill mit Debuff: '{chosen_skill_id}'.")
        else:
            # Sonst: Wähle den Skill mit dem höchsten potenziellen Schaden unter den offensiven Skills
            offensive_skills = []
            for s_id in usable_skills:
                skill = self.skill_definitions.get(s_id)
                if skill and skill.direct_effects and skill.direct_effects.base_damage is not None:
                    offensive_skills.append(s_id)
            
            if offensive_skills:
                offensive_skills.sort(key=lambda s_id: self._get_skill_potential_damage(s_id), reverse=True)
                chosen_skill_id = offensive_skills[0]
                logger.debug(f"'{self.actor.name}' (BasicRanged) wählt stärksten offensiven Skill: '{chosen_skill_id}'.")
            elif usable_skills: # Fallback: Wenn keine offensiven, aber andere nutzbare Skills
                chosen_skill_id = random.choice(usable_skills)
                logger.debug(f"'{self.actor.name}' (BasicRanged) wählt zufälligen verfügbaren Skill: '{chosen_skill_id}'.")

        return chosen_skill_id
    
    def _get_skill_potential_damage(self, skill_id: str) -> int:
        """
        Schätzt den potenziellen Schaden eines Skills. (Kopiert von BasicMelee, könnte ausgelagert werden).
        """
        skill = self.skill_definitions.get(skill_id)
        # Import für CONFIG hier, um zyklische Abhängigkeiten auf Modulebene zu vermeiden, falls base_weapon_damage genutzt wird
        try:
            from src.config.config import CONFIG
        except ImportError:
            CONFIG = None

        if not skill or not skill.direct_effects or skill.direct_effects.base_damage is None: # Nur für Schadensskills
             # Prüfe, ob es ein Skill mit base_damage: null ist, der Waffenschaden nutzt
            if skill and skill.direct_effects and skill.direct_effects.base_damage is None and CONFIG:
                base_damage = CONFIG.get("game_settings.base_weapon_damage", 5)
            else: # Kein Schadensskill oder keine Konfig
                return 0
        else:
            base_damage = skill.direct_effects.base_damage
        
        multiplier = skill.direct_effects.multiplier
        
        attr_bonus = 0
        if skill.direct_effects.scaling_attribute:
            attr_bonus = self.actor.get_attribute_bonus(skill.direct_effects.scaling_attribute)
            
        return int((base_damage + attr_bonus) * multiplier)

    def decide_action(self, potential_targets: List['CharacterInstance']) -> Optional[Tuple[str, 'CharacterInstance']]:
        """
        Trifft eine Entscheidung für die nächste Aktion (Skill und Ziel).
        Gibt ein Tupel (skill_id, target_instance) oder None zurück.
        """
        if not self.actor or self.actor.is_defeated or not self.actor.can_act:
            return None

        target = self.choose_target(potential_targets)
        if not target:
            logger.debug(f"'{self.actor.name}' (BasicRanged) findet kein Ziel.")
            return None
            
        actor_skills = self.actor.skills
        skill_id = self.choose_skill(actor_skills, target)

        if not skill_id:
            logger.debug(f"'{self.actor.name}' (BasicRanged) konnte keinen Skill auswählen.")
            return None
            
        logger.info(f"'{self.actor.name}' (BasicRanged) entscheidet sich für Skill '{skill_id}' auf Ziel '{target.name}'.")
        return skill_id, target


if __name__ == '__main__':
    from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
    from src.game_logic.entities import OpponentTemplate # Direktimport für Typ-Prüfung in _is_target_caster_type
    from src.config.config import CONFIG

    print("\n--- Teste BasicRangedStrategy ---")
    try:
        char_defs = load_character_templates()
        opp_defs = load_opponent_templates()
        skill_defs = load_skill_templates()

        # Akteur (Gegner-Fernkämpfer)
        # Goblin Archer hat 'basic_shot_phys'
        # Goblin Schamane hat 'weakening_curse' (Debuff) und 'basic_magic_bolt'
        ai_actor_template = opp_defs["goblin_archer_lv2"] 
        ai_actor = CharacterInstance(base_template=ai_actor_template, name_override="AI Archer")
        ai_actor.skills = ["basic_shot_phys"] # Standard
        
        # Testweise fügen wir einen Debuff-Skill hinzu
        # 'weakening_curse' ist im skills.json5 als MANA-Skill definiert. Archer hat kein Mana.
        # Um dies zu testen, geben wir dem Archer temporär Mana oder ändern den Skill.
        # Einfacher: Wir nehmen einen Schamanen als Akteur für den Debuff-Test.
        ai_shaman_template = opp_defs["goblin_shaman_lv3"]
        ai_shaman_actor = CharacterInstance(base_template=ai_shaman_template, name_override="AI Shaman Ranged Test")
        # Skills des Schamanen: basic_magic_bolt, weakening_curse, heal_lesser
        # weakening_curse ist ein Debuff.
        
        # Potenzielle Ziele
        player_krieger = CharacterInstance(base_template=char_defs["krieger"], name_override="Krieger (Non-Caster)")
        player_magier = CharacterInstance(base_template=char_defs["magier"], name_override="Magier (Caster)")
        player_magier.current_hp = int(player_magier.max_hp * 0.5) # Magier etwas angeschlagen

        targets = [player_krieger, player_magier]

        # Strategie-Instanz für Archer
        strategy_archer = BasicRangedStrategy(actor=ai_actor, skill_definitions=skill_defs, character_definitions=char_defs)
        # Strategie-Instanz für Shaman (für Debuff-Test)
        strategy_shaman = BasicRangedStrategy(actor=ai_shaman_actor, skill_definitions=skill_defs, character_definitions=char_defs)


        print(f"\nAI Akteur (Archer): {ai_actor.name} mit Skills: {ai_actor.skills}")
        print(f"AI Akteur (Shaman): {ai_shaman_actor.name} mit Skills: {ai_shaman_actor.skills}")
        print("Potenzielle Ziele:")
        for t in targets:
            print(f" - {t.name}: {t.current_hp}/{t.max_hp} HP, Caster: {strategy_archer._is_target_caster_type(t)}")

        # Teste Zielauswahl für Archer
        print("\n-- Teste Zielauswahl für Archer (mehrere Versuche) --")
        target_counts_archer = {t.name: 0 for t in targets}
        for _ in range(20): # Mehr Versuche für bessere Verteilung
            chosen_t = strategy_archer.choose_target(targets)
            if chosen_t:
                target_counts_archer[chosen_t.name] += 1
        print(f"Archer Zielauswahl-Verteilung (20 Versuche): {target_counts_archer} (erwarte mehr Magier)")

        # Teste Skillauswahl für Archer (hat nur basic_shot_phys)
        print("\n-- Teste Skillauswahl für Archer --")
        # Archer hat nur 'basic_shot_phys', sollte diesen immer wählen, wenn Ressourcen da
        ai_actor.current_stamina = ai_actor.max_stamina # Sicherstellen, dass Ressource da ist
        chosen_s_archer = strategy_archer.choose_skill(ai_actor.skills, player_magier)
        print(f"Archer gewählter Skill: {chosen_s_archer} (erwarte 'basic_shot_phys')")

        # Teste Skillauswahl für Shaman (hat Debuff 'weakening_curse' und 'basic_magic_bolt')
        print("\n-- Teste Skillauswahl für Shaman (mehrere Versuche) --")
        skill_counts_shaman = {s_id: 0 for s_id in ai_shaman_actor.skills}
        skill_counts_shaman["None"] = 0
        ai_shaman_actor.current_mana = ai_shaman_actor.max_mana # Sicherstellen, dass Mana da ist
        for _ in range(10):
            chosen_s_shaman = strategy_shaman.choose_skill(ai_shaman_actor.skills, player_magier)
            if chosen_s_shaman:
                skill_counts_shaman[chosen_s_shaman] += 1
            else:
                skill_counts_shaman["None"] +=1

        print(f"Shaman Skillauswahl-Verteilung (10 Versuche): {skill_counts_shaman} (erwarte mehr 'weakening_curse')")
        
        # Teste komplette Aktionsentscheidung für Archer
        print("\n-- Teste Aktionsentscheidung für Archer --")
        action_archer = strategy_archer.decide_action(targets)
        if action_archer:
            skill_chosen, target_chosen = action_archer
            print(f"Archer entschiedene Aktion: Skill '{skill_chosen}' auf Ziel '{target_chosen.name}'.")
        else:
            print("Archer: Keine Aktion entschieden.")

        # Teste komplette Aktionsentscheidung für Shaman
        print("\n-- Teste Aktionsentscheidung für Shaman --")
        action_shaman = strategy_shaman.decide_action(targets)
        if action_shaman:
            skill_chosen, target_chosen = action_shaman
            print(f"Shaman entschiedene Aktion: Skill '{skill_chosen}' auf Ziel '{target_chosen.name}'.")
        else:
            print("Shaman: Keine Aktion entschieden.")

    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in basic_ranged.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in basic_ranged.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- BasicRangedStrategy-Tests abgeschlossen ---")