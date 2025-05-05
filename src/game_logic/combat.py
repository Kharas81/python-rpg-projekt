import random
import sys
import time
from typing import List, Optional, Union, Tuple

try:
    from .character import Character
    from .enemy import Enemy
    from .status_effects import StatusEffect
    from definitions import loader
    from definitions.models import SkillDefinition, SkillEffectDefinition, ItemDefinition
except ImportError:
    try:
        from src.game_logic.character import Character
        from src.game_logic.enemy import Enemy
        from src.game_logic.status_effects import StatusEffect
        from src.definitions import loader
        from src.definitions.models import SkillDefinition, SkillEffectDefinition, ItemDefinition
    except ImportError as e: print(f"FEHLER in combat.py: {e}", file=sys.stderr); sys.exit(1)

Combatant = Union[Character, Enemy]
BASE_HIT_CHANCE = 90; HIT_CHANCE_ACCURACY_FACTOR = 3; HIT_CHANCE_EVASION_FACTOR = 2
MIN_HIT_CHANCE = 5; MAX_HIT_CHANCE = 95
DEFAULT_EFFECT_MAGNITUDES = {"BURNING": 3, "DEFENSE_UP": 3}
DEFAULT_UNARMED_DAMAGE = 1

class CombatEncounter:
    """ Verwaltet einen einzelnen Kampf. """
    def __init__(self, player: Character, enemies: List[Enemy]):
        self.player: Character = player; self.enemies: List[Enemy] = [e for e in enemies if e.is_alive()]
        if not self.enemies: raise ValueError("Keine Gegner im Kampf.")
        self.combatants: List[Combatant] = [self.player] + self.enemies
        self.turn_order: List[Combatant] = []; self.current_turn_index: int = 0
        self.round_number: int = 0; self.status: str = "PENDING"

    def _calculate_turn_order(self):
        self.turn_order = sorted(self.combatants, key=lambda c: c.get_combat_stat("INITIATIVE") or 0, reverse=True)
        self.current_turn_index = 0
        print("\nZugreihenfolge:"); [print(f"  {i+1}. {c.name} (Init: {c.get_combat_stat('INITIATIVE') or 0})") for i, c in enumerate(self.turn_order)]

    def start_combat(self):
        if self.status == "PENDING": print(f"\n--- Kampf beginnt! ---"); self.status = "ONGOING"; self.round_number = 1; self._calculate_turn_order()

    def get_current_combatant(self) -> Optional[Combatant]:
        if not self.turn_order or self.current_turn_index >= len(self.turn_order): return None
        return self.turn_order[self.current_turn_index]

    def next_turn(self) -> Optional[Combatant]:
        if self.status != "ONGOING": return None
        next_index = (self.current_turn_index + 1) % len(self.turn_order)
        if next_index < self.current_turn_index: self.round_number += 1; print(f"\n--- Runde {self.round_number} ---")
        self.current_turn_index = next_index
        current_combatant = self.get_current_combatant()
        processed = 0
        while current_combatant and not current_combatant.is_alive() and processed < len(self.turn_order):
            processed += 1; self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
            current_combatant = self.get_current_combatant()
        if not current_combatant or not current_combatant.is_alive(): return None
        current_combatant.tick_effects()
        if not current_combatant.is_alive(): return self.next_turn()
        if current_combatant.has_effect("STUNNED"): print(f"{current_combatant.name} ist betäubt!"); time.sleep(1); return self.next_turn()
        print(f"\n{current_combatant.name} ist am Zug.")
        return current_combatant

    def is_combat_over(self) -> bool:
        if self.status != "ONGOING": return True
        if not self.player.is_alive(): self.status = "PLAYER_DEFEAT"; print(f"\n--- Kampf verloren! ---"); return True
        if not self.get_living_enemies(): self.status = "PLAYER_VICTORY"; print(f"\n--- Kampf gewonnen! ---"); return True
        return False

    def get_living_enemies(self) -> List[Enemy]: return [e for e in self.enemies if e.is_alive()]
    def display_combat_status(self): print("\n--- Kampfstatus ---"); self.player.display_status(); print("-" * 20); [e.display_short_status() for e in self.get_living_enemies()]; print("-" * 20)

    def _calculate_hit_chance(self, attacker: Combatant, target: Combatant) -> int:
        acc_mod = attacker.get_combat_stat("ACCURACY_MODIFIER") or 0; eva_mod = target.get_combat_stat("EVASION_MODIFIER") or 0
        chance = (BASE_HIT_CHANCE + (acc_mod * HIT_CHANCE_ACCURACY_FACTOR) - (eva_mod * HIT_CHANCE_EVASION_FACTOR))
        return int(max(MIN_HIT_CHANCE, min(MAX_HIT_CHANCE, chance)))

    def apply_skill(self, attacker: Combatant, target: Combatant, skill: SkillDefinition) -> bool:
        if not attacker.is_alive() or not target.is_alive(): return False
        print(f"{attacker.name} setzt '{skill.name}' gegen {target.name} ein.")
        if not attacker.consume_resource(skill.cost.resource, skill.cost.amount): return False
        needs_hit_check = skill.target_type != "SELF"
        if needs_hit_check:
            hit_chance = self._calculate_hit_chance(attacker, target); roll = random.randint(1, 100)
            print(f"  (Trefferchance: {hit_chance}%, Wurf: {roll})")
            if roll > hit_chance: print(f"  >> {skill.name} verfehlt!"); return False
        print(f"  >> {skill.name} trifft!")
        for effect in skill.effects: self._apply_effect(attacker, target, effect, skill)
        return True

    def _apply_effect(self, attacker: Combatant, target: Combatant, effect: SkillEffectDefinition, skill: SkillDefinition):
        effect_type = effect.type.upper()
        if effect_type == "DAMAGE":
            base_dmg = 0
            if effect.base_value == "WEAPON":
                weapon: Optional[ItemDefinition] = None
                if hasattr(attacker, 'get_equipped_item'): weapon = attacker.get_equipped_item("WEAPON_MAIN")
                if weapon and weapon.stats and weapon.stats.damage is not None: base_dmg = weapon.stats.damage
                else: base_dmg = DEFAULT_UNARMED_DAMAGE
            elif isinstance(effect.base_value, int): base_dmg = effect.base_value

            scaling_bonus = 0
            if effect.scaling_attribute: scaling_bonus = (attacker.get_attribute(effect.scaling_attribute) - 10) // 2
            total_damage = (base_dmg + scaling_bonus) * (effect.multiplier or 1.0)

            # *** NEU: Bonus vs Type berücksichtigen ***
            if effect.bonus_vs_type and hasattr(target, 'has_tag'):
                if target.has_tag(effect.bonus_vs_type.type):
                     bonus_mod = 1.0 + effect.bonus_vs_type.modifier
                     print(f"  > Bonus ({effect.bonus_vs_type.modifier*100}%) gegen {effect.bonus_vs_type.type} angewendet!")
                     total_damage *= bonus_mod

            # TODO: Rüstungsdurchdringung hier oder in apply_damage?
            damage_type = effect.damage_type or "UNKNOWN"
            target.apply_damage(int(round(total_damage)), damage_type)

        elif effect_type == "HEAL":
             base_heal = effect.base_value or 0; scaling_heal = 0
             if effect.scaling_attribute and effect.scaling_factor: scaling_heal = attacker.get_attribute(effect.scaling_attribute) * effect.scaling_factor
             total_heal = base_heal + scaling_heal; target.apply_heal(int(round(total_heal)))

        elif effect_type == "APPLY_STATUS":
             if effect.status_effect and effect.duration is not None:
                 display_name_map = {"STUNNED":"Betäubt", "BURNING":"Brennt", "SLOWED":"Verlangsamt", "ACCURACY_DOWN":"Genauigkeit runter", "INITIATIVE_UP":"Initiative rauf", "DEFENSE_UP":"Verteidigung rauf", "WEAKENED":"Geschwächt"}
                 display_name = display_name_map.get(effect.status_effect, effect.status_effect)
                 magnitude = effect.magnitude if effect.magnitude is not None else DEFAULT_EFFECT_MAGNITUDES.get(effect.status_effect)
                 status_effect_instance = StatusEffect(effect_id=effect.status_effect, display_name=display_name, total_duration=effect.duration, duration_remaining=effect.duration, magnitude=magnitude, caster=attacker, source_skill_id=skill.id)
                 apply_chance = effect.chance or 1.0
                 if random.random() < apply_chance: target.add_effect(status_effect_instance)
                 else: print(f"  > Effekt '{display_name}' hat widerstanden!")
             else: print(f"WARNUNG: Unvollständige APPLY_STATUS Definition für Skill '{skill.name}'.")

        elif effect_type == "ABSORB_SHIELD": print(f"  > Effekt 'ABSORB_SHIELD'. (Logik fehlt!)")
        else: print(f"WARNUNG: Unbekannter Effekt-Typ '{effect.type}'")

