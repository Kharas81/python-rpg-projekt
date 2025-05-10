# src/ai/strategies/basic_melee.py
"""
Einfache Nahkampf-KI-Strategie.
Priorisiert offensive Aktionen gegen das schwächste Ziel.
"""
import random
import logging
from typing import Optional, List, Dict, Any

# Importe für Typ-Annotationen und Zugriff auf Spielobjekte
if True: # Um Zirkularimport zu vermeiden, falls entities CharacterInstance direkt importieren würde
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate
    # SKILL_DEFINITIONS wird hier nicht direkt geladen, da die Strategie Skill-IDs liefert,
    # und der CombatHandler die SkillTemplates auflöst.

logger = logging.getLogger(__name__)

class BasicMeleeStrategy:
    """
    Eine einfache KI-Strategie für Nahkämpfer.
    - Zielauswahl: Schwächstes Ziel (nach prozentualen HP) oder zufällig.
    - Skill-Auswahl: Bevorzugt offensive Skills, wählt stärksten verfügbaren Angriff.
    """
    def __init__(self, actor: 'CharacterInstance', skill_definitions: Dict[str, 'SkillTemplate']):
        self.actor = actor
        # skill_definitions werden übergeben, um Skill-Eigenschaften zu prüfen (z.B. Schaden, Typ)
        self.skill_definitions = skill_definitions


    def _is_skill_offensive(self, skill_id: str) -> bool:
        """Prüft, ob ein Skill primär offensiv ist (Schaden verursacht)."""
        skill = self.skill_definitions.get(skill_id)
        if skill and skill.direct_effects and skill.direct_effects.base_damage is not None:
            return True
        return False

    def _get_skill_potential_damage(self, skill_id: str) -> int:
        """
        Schätzt den potenziellen Schaden eines Skills.
        Vereinfacht: Basisschaden + (eigener Attributbonus * Multiplikator).
        Ignoriert kritische Treffer und Zielresistenzen für die Auswahl.
        """
        skill = self.skill_definitions.get(skill_id)
        if not skill or not self._is_skill_offensive(skill_id) or not skill.direct_effects:
            return 0

        base_damage = skill.direct_effects.base_damage or 0 # Annahme: 0 wenn null, könnte base_weapon_damage sein
        multiplier = skill.direct_effects.multiplier
        
        attr_bonus = 0
        if skill.direct_effects.scaling_attribute:
            attr_bonus = self.actor.get_attribute_bonus(skill.direct_effects.scaling_attribute)
            
        return int((base_damage + attr_bonus) * multiplier)


    def choose_target(self, potential_targets: List['CharacterInstance']) -> Optional['CharacterInstance']:
        """
        Wählt ein Ziel aus einer Liste potenzieller Ziele.
        - 80% Chance, das Ziel mit den prozentual niedrigsten HP anzugreifen.
        - 20% Chance, ein zufälliges Ziel anzugreifen.
        """
        if not potential_targets:
            return None

        valid_targets = [t for t in potential_targets if not t.is_defeated]
        if not valid_targets:
            return None

        # 80% Chance für schwächstes Ziel (prozentuale HP)
        if random.random() < 0.80:
            # Sortiere Ziele nach prozentualen HP (niedrigste zuerst)
            # Handle Division durch Null, falls max_hp 0 ist (sollte nicht passieren)
            valid_targets.sort(key=lambda t: (t.current_hp / t.max_hp) if t.max_hp > 0 else float('inf'))
            chosen_target = valid_targets[0]
            logger.debug(f"'{self.actor.name}' (BasicMelee) wählt schwächstes Ziel: '{chosen_target.name}' "
                         f"({chosen_target.current_hp}/{chosen_target.max_hp} HP).")
            return chosen_target
        else:
            chosen_target = random.choice(valid_targets)
            logger.debug(f"'{self.actor.name}' (BasicMelee) wählt zufälliges Ziel: '{chosen_target.name}'.")
            return chosen_target

    def choose_skill(self, available_skills: List[str], target: Optional['CharacterInstance']) -> Optional[str]:
        """
        Wählt einen Skill aus der Liste der verfügbaren Skills des Akteurs.
        - Filtert nach offensiven Skills.
        - Wählt mit 70% Chance den stärksten verfügbaren offensiven Skill.
        - Wählt mit 30% Chance einen zufälligen offensiven Skill.
        - Wenn keine offensiven Skills, aber andere Skills verfügbar, wähle zufällig.
        """
        if not available_skills:
            return None

        # Filtere Skills, die der Akteur tatsächlich nutzen kann (Ressourcen etc.)
        # Diese Prüfung sollte eigentlich der CombatHandler machen, bevor er die KI fragt,
        # oder die KI muss die Ressourcen des Akteurs kennen.
        # Für den Moment nehmen wir an, `available_skills` sind tatsächlich nutzbar.
        
        offensive_skills = []
        for skill_id in available_skills:
            skill_template = self.skill_definitions.get(skill_id)
            if skill_template and self._is_skill_offensive(skill_id):
                 # Ressourcenprüfung (vereinfacht)
                if self.actor.current_stamina >= skill_template.cost.value or \
                   self.actor.current_mana >= skill_template.cost.value or \
                   self.actor.current_energy >= skill_template.cost.value or \
                   skill_template.cost.type.upper() == "NONE":
                    offensive_skills.append(skill_id)

        if not offensive_skills:
            # Wenn keine offensiven Skills, aber andere Skills verfügbar sind, wähle einen zufälligen davon
            # (z.B. ein Self-Buff, den ein Nahkämpfer haben könnte).
            # Für eine reine Melee-Strategie ist das aber seltener der Fall.
            if available_skills:
                chosen_skill_id = random.choice(available_skills)
                logger.debug(f"'{self.actor.name}' (BasicMelee) hat keine offensiven Skills, wählt zufällig: '{chosen_skill_id}'.")
                return chosen_skill_id
            return None


        # 70% Chance für stärksten Skill
        if random.random() < 0.70:
            offensive_skills.sort(key=lambda s_id: self._get_skill_potential_damage(s_id), reverse=True)
            chosen_skill_id = offensive_skills[0]
            logger.debug(f"'{self.actor.name}' (BasicMelee) wählt stärksten Skill: '{chosen_skill_id}'.")
        else:
            chosen_skill_id = random.choice(offensive_skills)
            logger.debug(f"'{self.actor.name}' (BasicMelee) wählt zufälligen offensiven Skill: '{chosen_skill_id}'.")
            
        return chosen_skill_id

    def decide_action(self, potential_targets: List['CharacterInstance']) -> Optional[Tuple[str, 'CharacterInstance']]:
        """
        Trifft eine Entscheidung für die nächste Aktion (Skill und Ziel).
        Gibt ein Tupel (skill_id, target_instance) oder None zurück.
        """
        if not self.actor or self.actor.is_defeated or not self.actor.can_act:
            return None

        target = self.choose_target(potential_targets)
        if not target:
            logger.debug(f"'{self.actor.name}' (BasicMelee) findet kein Ziel.")
            return None
            
        # Akteur-Skills holen (Liste von Skill-IDs)
        actor_skills = self.actor.skills 
        skill_id = self.choose_skill(actor_skills, target)

        if not skill_id:
            logger.debug(f"'{self.actor.name}' (BasicMelee) konnte keinen Skill auswählen.")
            # Fallback: Basisangriff, falls vorhanden und kein anderer Skill gewählt wurde
            # Diese Logik müsste hier oder in choose_skill implementiert werden.
            # Fürs Erste: Wenn kein Skill, dann keine Aktion.
            return None
            
        logger.info(f"'{self.actor.name}' (BasicMelee) entscheidet sich für Skill '{skill_id}' auf Ziel '{target.name}'.")
        return skill_id, target


if __name__ == '__main__':
    # Testen der BasicMeleeStrategy
    from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
    from src.config.config import CONFIG # Stellt sicher, dass CONFIG geladen ist

    print("\n--- Teste BasicMeleeStrategy ---")
    try:
        char_templates = load_character_templates()
        opp_templates = load_opponent_templates()
        skill_defs = load_skill_templates() # Wichtig für die Strategie

        krieger_template = char_templates["krieger"] # Hat basic_strike_phys, power_strike
        goblin_template = opp_templates["goblin_lv1"] # Hat basic_strike_phys

        # Akteur (Gegner)
        ai_actor = CharacterInstance(base_template=goblin_template, name_override="AI Goblin")
        ai_actor.skills = ["basic_strike_phys", "power_strike"] # Gib ihm testweise mehr Skills
        
        # Potenzielle Ziele (Spieler)
        player1 = CharacterInstance(base_template=krieger_template, name_override="Player 1 (Full HP)")
        player2 = CharacterInstance(base_template=krieger_template, name_override="Player 2 (Low HP)")
        player2.current_hp = int(player2.max_hp * 0.3) # 30% HP

        targets = [player1, player2]

        # Strategie-Instanz
        strategy = BasicMeleeStrategy(actor=ai_actor, skill_definitions=skill_defs)

        print(f"\nAI Akteur: {ai_actor.name} mit Skills: {ai_actor.skills}")
        print("Potenzielle Ziele:")
        for t in targets:
            print(f" - {t.name}: {t.current_hp}/{t.max_hp} HP")

        # Teste Zielauswahl mehrmals
        print("\n-- Teste Zielauswahl (mehrere Versuche) --")
        target_counts = {player1.name: 0, player2.name: 0}
        for _ in range(10):
            chosen_t = strategy.choose_target(targets)
            if chosen_t:
                target_counts[chosen_t.name] += 1
        print(f"Zielauswahl-Verteilung über 10 Versuche: {target_counts} (erwarte mehr Player 2)")

        # Teste Skillauswahl
        # Annahme: power_strike ist stärker als basic_strike_phys
        print("\n-- Teste Skillauswahl (mehrere Versuche) --")
        skill_counts = {"power_strike": 0, "basic_strike_phys": 0, "None":0}
        # Stelle sicher, dass der AI-Akteur genug Ressourcen für power_strike hat
        ai_actor.current_stamina = ai_actor.max_stamina 
        for _ in range(10):
            chosen_s = strategy.choose_skill(ai_actor.skills, player2) # Ziel ist hier für Kontext, nicht zwingend für Auswahl
            if chosen_s:
                skill_counts[chosen_s] = skill_counts.get(chosen_s, 0) + 1
            else:
                skill_counts["None"] +=1
        print(f"Skillauswahl-Verteilung über 10 Versuche: {skill_counts} (erwarte mehr power_strike)")
        
        # Teste komplette Aktionsentscheidung
        print("\n-- Teste Aktionsentscheidung --")
        action = strategy.decide_action(targets)
        if action:
            skill_chosen, target_chosen = action
            print(f"Entschiedene Aktion: Skill '{skill_chosen}' auf Ziel '{target_chosen.name}'.")
        else:
            print("Keine Aktion entschieden.")
            
        print("\n-- Test: Akteur hat nicht genug Ressourcen für stärksten Skill --")
        ai_actor.current_stamina = 1 # Nicht genug für power_strike (kostet 15 lt. JSON)
        action_low_res = strategy.decide_action(targets)
        if action_low_res:
            skill_chosen, target_chosen = action_low_res
            print(f"Entschiedene Aktion bei niedrigen Ressourcen: Skill '{skill_chosen}' auf Ziel '{target_chosen.name}'. (Erwarte basic_strike_phys)")
        else:
            print("Keine Aktion entschieden bei niedrigen Ressourcen.")


    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in basic_melee.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in basic_melee.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- BasicMeleeStrategy-Tests abgeschlossen ---")