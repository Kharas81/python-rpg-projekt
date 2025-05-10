# src/ai/strategies/support_caster.py
"""
KI-Strategie für unterstützende Zauberwirker.
Priorisiert Heilung, Buffs für Verbündete, Debuffs für Gegner, dann Angriff.
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

class SupportCasterStrategy:
    """
    Eine KI-Strategie für unterstützende Zauberwirker.
    Prioritäten:
    1. Heilung von Verbündeten mit niedrigen HP.
    2. Buffs auf Verbündete (die noch nicht gebufft sind oder deren Buffs auslaufen).
    3. Debuffs auf starke Gegner oder Caster-Gegner.
    4. Offensive Angriffe als letzte Option.
    """
    def __init__(self, actor: 'CharacterInstance', 
                 all_entities_in_combat: List['CharacterInstance'], # Um Verbündete/Gegner zu finden
                 skill_definitions: Dict[str, 'SkillTemplate'], 
                 character_definitions: Dict[str, 'CharacterTemplate']): # Unbenutzt, aber konsistent
        self.actor = actor
        self.all_entities_in_combat = all_entities_in_combat # Komplette Liste aller Charaktere im Kampf
        self.skill_definitions = skill_definitions
        # self.character_definitions = character_definitions

    def _get_allies(self) -> List['CharacterInstance']:
        """Gibt eine Liste der Verbündeten des Akteurs zurück (inklusive sich selbst)."""
        # Annahme: Alle Instanzen, die nicht als "Gegner" des Akteurs gelten, sind Verbündete.
        # Dies erfordert eine klare Definition von Teams oder Fraktionen.
        # Für den Moment eine vereinfachte Annahme:
        # Wenn der actor ein "opponent"-Template hat, sind andere "opponent"-Templates Verbündete
        # und "character"-Templates sind Gegner. Vice versa.
        # Für eine robustere Lösung bräuchte man ein Fraktionssystem.
        
        # Vereinfachung: Alle Instanzen, die nicht der Akteur selbst sind und NICHT zu den "üblichen" Gegnern gehören.
        # Oder: Wenn Akteur ein Gegner ist, sind andere Gegner Verbündete.
        # Hier implementieren wir es so, dass es für einen NPC-Support-Caster funktioniert, der andere NPCs unterstützt.
        # Eine klarere Unterscheidung von Spieler-Team vs. Gegner-Team wäre besser.

        # Annahme: Die `all_entities_in_combat` Liste enthält alle.
        # Wir müssen entscheiden, wer ein Verbündeter ist.
        # Für einen NPC-Support-Caster sind andere NPCs desselben "Teams" Verbündete.
        # Für einen Spieler-Support-Caster sind andere Spieler Verbündete.
        
        # TODO: Diese Logik muss verfeinert werden, sobald Fraktionen/Teams klar definiert sind.
        # Für den Moment: Wenn der Akteur ein "opponent"-Template hat, sind andere mit "opponent"-Template Verbündete.
        actor_is_opponent_type = hasattr(self.actor.base_template, 'xp_reward') # Heuristik: Gegner haben xp_reward

        allies = []
        for entity in self.all_entities_in_combat:
            if entity.is_defeated:
                continue
            
            entity_is_opponent_type = hasattr(entity.base_template, 'xp_reward')
            if actor_is_opponent_type == entity_is_opponent_type: # Gleicher "Typ" (beide Gegner oder beide Spieler)
                allies.append(entity)
        return allies

    def _get_opponents(self) -> List['CharacterInstance']:
        """Gibt eine Liste der Gegner des Akteurs zurück."""
        actor_is_opponent_type = hasattr(self.actor.base_template, 'xp_reward')
        opponents = []
        for entity in self.all_entities_in_combat:
            if entity.is_defeated:
                continue
            entity_is_opponent_type = hasattr(entity.base_template, 'xp_reward')
            if actor_is_opponent_type != entity_is_opponent_type: # Unterschiedlicher "Typ"
                opponents.append(entity)
        return opponents

    def _is_skill_type(self, skill_id: str, skill_type: str) -> bool:
        """
        Prüft, ob ein Skill einem bestimmten Typ entspricht (HEAL, BUFF, DEBUFF, OFFENSIVE).
        skill_type: "HEAL", "BUFF_ALLY", "DEBUFF_ENEMY", "OFFENSIVE_ENEMY"
        """
        skill = self.skill_definitions.get(skill_id)
        if not skill: return False

        if skill_type == "HEAL":
            return skill.direct_effects is not None and skill.direct_effects.base_healing is not None
        
        if skill_type == "BUFF_ALLY": # Buffs sind positive Status-Effekte auf Verbündete
            if skill.target_type in ["ALLY_SINGLE", "ALLY_ALL", "SELF"] and skill.applied_status_effects:
                # Annahme: Positive Effekte werden als Buffs klassifiziert.
                # Dies erfordert, dass wir das 'is_positive' Flag im StatusEffect oder eine ähnliche Logik haben.
                # Für den Moment prüfen wir, ob es überhaupt angewandte Effekte gibt.
                # Zukünftig: `any(eff_data.is_positive for eff_data in skill.applied_status_effects)`
                return True # Vereinfachung
            return False

        if skill_type == "DEBUFF_ENEMY": # Debuffs sind negative Status-Effekte auf Gegner
            if skill.target_type in ["ENEMY_SINGLE", "ENEMY_ALL", "ENEMY_CLEAVE", "ENEMY_SPLASH"] and skill.applied_status_effects:
                return True # Vereinfachung
            return False

        if skill_type == "OFFENSIVE_ENEMY":
            return skill.target_type.startswith("ENEMY_") and \
                   skill.direct_effects is not None and \
                   skill.direct_effects.base_damage is not None
        
        return False


    def _can_actor_use_skill(self, skill_id: str) -> bool:
        """Prüft, ob der Akteur den Skill ressourcentechnisch einsetzen kann."""
        skill_template = self.skill_definitions.get(skill_id)
        if not skill_template: return False
        
        cost_type_upper = skill_template.cost.type.upper()
        if cost_type_upper == "NONE": return True
        if cost_type_upper == "MANA" and self.actor.current_mana >= skill_template.cost.value: return True
        if cost_type_upper == "STAMINA" and self.actor.current_stamina >= skill_template.cost.value: return True
        if cost_type_upper == "ENERGY" and self.actor.current_energy >= skill_template.cost.value: return True
        return False

    def decide_action(self, potential_targets_unused: List['CharacterInstance']) -> Optional[Tuple[str, 'CharacterInstance']]:
        """
        Trifft eine Entscheidung basierend auf der Prioritätenliste.
        `potential_targets_unused` wird hier ignoriert, da Ziele basierend auf Skill-Typ gewählt werden.
        """
        if not self.actor or self.actor.is_defeated or not self.actor.can_act:
            return None

        allies = self._get_allies()
        opponents = self._get_opponents()
        
        # 1. Heilung von Verbündeten
        healing_skills = [s_id for s_id in self.actor.skills if self._is_skill_type(s_id, "HEAL") and self._can_actor_use_skill(s_id)]
        if healing_skills:
            # Finde verletzte Verbündete (sortiert nach niedrigsten prozentualen HP)
            injured_allies = sorted(
                [ally for ally in allies if ally.current_hp < ally.max_hp and not ally.is_defeated],
                key=lambda a: (a.current_hp / a.max_hp) if a.max_hp > 0 else float('inf')
            )
            if injured_allies:
                target_for_heal = injured_allies[0] # Am stärksten verletzter Verbündeter
                # Wähle den besten verfügbaren Heilskill (z.B. stärkste Heilung, oder einfach der erste)
                # Für Einfachheit: Erster verfügbarer Heilskill
                chosen_skill_id = healing_skills[0] 
                logger.info(f"'{self.actor.name}' (SupportCaster) entscheidet sich für Heilung: Skill '{chosen_skill_id}' auf '{target_for_heal.name}'.")
                return chosen_skill_id, target_for_heal

        # 2. Buffs auf Verbündete
        buff_skills = [s_id for s_id in self.actor.skills if self._is_skill_type(s_id, "BUFF_ALLY") and self._can_actor_use_skill(s_id)]
        if buff_skills:
            # Finde Verbündete, die einen bestimmten Buff noch nicht haben (komplexer)
            # Vereinfachung: Wirke einen zufälligen Buff auf einen zufälligen Verbündeten (oder sich selbst)
            # der noch nicht "voll" gebufft ist.
            # TODO: Bessere Logik, um zu prüfen, welche Buffs sinnvoll sind und wer sie braucht.
            target_for_buff = random.choice(allies) if allies else None
            if target_for_buff:
                chosen_skill_id = random.choice(buff_skills)
                logger.info(f"'{self.actor.name}' (SupportCaster) entscheidet sich für Buff: Skill '{chosen_skill_id}' auf '{target_for_buff.name}'.")
                return chosen_skill_id, target_for_buff
        
        # 3. Debuffs auf Gegner
        debuff_skills = [s_id for s_id in self.actor.skills if self._is_skill_type(s_id, "DEBUFF_ENEMY") and self._can_actor_use_skill(s_id)]
        if debuff_skills and opponents:
            # Zielauswahl für Debuffs: Starke Gegner oder Caster
            # Vereinfachung: Zufälliger Gegner
            target_for_debuff = random.choice(opponents)
            chosen_skill_id = random.choice(debuff_skills)
            logger.info(f"'{self.actor.name}' (SupportCaster) entscheidet sich für Debuff: Skill '{chosen_skill_id}' auf '{target_for_debuff.name}'.")
            return chosen_skill_id, target_for_debuff

        # 4. Offensive Angriffe
        offensive_skills = [s_id for s_id in self.actor.skills if self._is_skill_type(s_id, "OFFENSIVE_ENEMY") and self._can_actor_use_skill(s_id)]
        if offensive_skills and opponents:
            # Zielauswahl: Zufälliger Gegner
            target_for_attack = random.choice(opponents)
            # Wähle stärksten Offensivskill
            offensive_skills.sort(key=lambda s_id: self._get_skill_potential_damage(s_id), reverse=True)
            chosen_skill_id = offensive_skills[0]
            logger.info(f"'{self.actor.name}' (SupportCaster) entscheidet sich für Angriff: Skill '{chosen_skill_id}' auf '{target_for_attack.name}'.")
            return chosen_skill_id, target_for_attack

        logger.debug(f"'{self.actor.name}' (SupportCaster) konnte keine passende Aktion finden.")
        return None # Keine Aktion gefunden

    def _get_skill_potential_damage(self, skill_id: str) -> int: # Kopiert von BasicRanged
        skill = self.skill_definitions.get(skill_id)
        try: from src.config.config import CONFIG
        except ImportError: CONFIG = None

        if not skill or not skill.direct_effects or skill.direct_effects.base_damage is None:
            if skill and skill.direct_effects and skill.direct_effects.base_damage is None and CONFIG:
                base_damage = CONFIG.get("game_settings.base_weapon_damage", 5)
            else: return 0
        else: base_damage = skill.direct_effects.base_damage
        
        multiplier = skill.direct_effects.multiplier
        attr_bonus = 0
        if skill.direct_effects.scaling_attribute:
            attr_bonus = self.actor.get_attribute_bonus(skill.direct_effects.scaling_attribute)
        return int((base_damage + attr_bonus) * multiplier)


if __name__ == '__main__':
    from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
    from src.config.config import CONFIG

    print("\n--- Teste SupportCasterStrategy ---")
    try:
        char_defs = load_character_templates()
        opp_defs = load_opponent_templates()
        skill_defs = load_skill_templates()

        # Akteur (Support Caster - z.B. Goblin Schamane)
        # Hat: basic_magic_bolt, weakening_curse, heal_lesser
        ai_actor_template = opp_defs["goblin_shaman_lv3"]
        ai_actor = CharacterInstance(base_template=ai_actor_template, name_override="AI Support Shaman")
        ai_actor.current_mana = ai_actor.max_mana # Volles Mana für Tests

        # Verbündeter des Schamanen (ein anderer Goblin)
        ally_goblin_template = opp_defs["goblin_lv1"]
        ally_goblin = CharacterInstance(base_template=ally_goblin_template, name_override="Ally Goblin")
        
        # Gegner (Spieler)
        player_krieger = CharacterInstance(base_template=char_defs["krieger"], name_override="Player Krieger")
        player_magier = CharacterInstance(base_template=char_defs["magier"], name_override="Player Magier")

        # Kampfteilnehmerliste
        # Wichtig: Die Reihenfolge oder genaue Zusammensetzung beeinflusst _get_allies/_get_opponents
        # Hier nehmen wir an, AI Support Shaman und Ally Goblin sind ein Team, Spieler sind das andere.
        # Da die Heuristik auf 'xp_reward' basiert, sollte das funktionieren.
        combat_participants = [ai_actor, ally_goblin, player_krieger, player_magier]

        strategy = SupportCasterStrategy(actor=ai_actor, 
                                          all_entities_in_combat=combat_participants,
                                          skill_definitions=skill_defs,
                                          character_definitions=char_defs)

        print(f"\nAI Akteur: {ai_actor.name} mit Skills: {ai_actor.skills}")
        print("Verbündete des Akteurs:")
        for ally_char in strategy._get_allies(): print(f" - {ally_char.name}")
        print("Gegner des Akteurs:")
        for opp_char in strategy._get_opponents(): print(f" - {opp_char.name}")


        # Szenario 1: Verbündeter ist stark verletzt -> Erwarte Heilung
        print("\n-- Szenario 1: Verbündeter stark verletzt --")
        ally_goblin.current_hp = int(ally_goblin.max_hp * 0.2) # 20% HP
        print(f"{ally_goblin.name} HP: {ally_goblin.current_hp}/{ally_goblin.max_hp}")
        action1 = strategy.decide_action([]) # `potential_targets` wird von dieser Strategie ignoriert
        if action1:
            skill_chosen, target_chosen = action1
            print(f"Aktion 1: Skill '{skill_chosen}' (erwarte 'heal_lesser') auf '{target_chosen.name}' (erwarte '{ally_goblin.name}').")
        else:
            print("Aktion 1: Keine Aktion entschieden.")
        ally_goblin.current_hp = ally_goblin.max_hp # Reset für nächstes Szenario

        # Szenario 2: Kein Verbündeter verletzt, Gegner vorhanden -> Erwarte Debuff oder Angriff
        print("\n-- Szenario 2: Kein Verbündeter verletzt, Gegner vorhanden --")
        # Um Buff-Logik zu überspringen (da nicht gut implementiert), fügen wir temporär keine Buff-Skills hinzu.
        # ai_actor.skills = [s for s in ai_actor.skills if not strategy._is_skill_type(s, "BUFF_ALLY")]

        action2 = strategy.decide_action([])
        if action2:
            skill_chosen, target_chosen = action2
            print(f"Aktion 2: Skill '{skill_chosen}' (erwarte Debuff 'weakening_curse' oder Angriff 'basic_magic_bolt') auf Gegner '{target_chosen.name}'.")
        else:
            print("Aktion 2: Keine Aktion entschieden.")
            
        # Szenario 3: Nur noch Gegner, keine Heil/Buff/Debuff-Optionen (oder keine Ressourcen dafür)
        print("\n-- Szenario 3: Nur noch Angriffsoptionen --")
        ai_actor.skills = ["basic_magic_bolt"] # Nur noch Angriffsskill
        ai_actor.current_mana = ai_actor.max_mana
        action3 = strategy.decide_action([])
        if action3:
            skill_chosen, target_chosen = action3
            print(f"Aktion 3: Skill '{skill_chosen}' (erwarte 'basic_magic_bolt') auf Gegner '{target_chosen.name}'.")
        else:
            print("Aktion 3: Keine Aktion entschieden.")
            
        # Szenario 4: Keine Ressourcen für irgendwas
        print("\n-- Szenario 4: Keine Ressourcen --")
        ai_actor.skills = ["basic_magic_bolt", "weakening_curse", "heal_lesser"] # Alle Skills wieder da
        ai_actor.current_mana = 0
        action4 = strategy.decide_action([])
        if action4:
            skill_chosen, target_chosen = action4
            print(f"Aktion 4: Skill '{skill_chosen}' auf '{target_chosen.name}'. (Sollte keine Aktion sein)")
        else:
            print("Aktion 4: Keine Aktion entschieden (korrekt, da keine Ressourcen).")


    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in support_caster.py: {e}.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in support_caster.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- SupportCasterStrategy-Tests abgeschlossen ---")