import random
from typing import List, Optional, Dict, Any, Tuple
import sys

try:
    from definitions import loader
    from definitions.models import (
        EnemyDefinition, AttributeDefinition, CombatStatDefinition, SkillDefinition,
        AttributesSet, EnemyCombatStats, ItemDefinition # ItemDefinition hinzugefügt für Konsistenz
    )
    from .status_effects import StatusEffect
    from .character import Character # Import Character für Type Hinting
except ImportError:
    try:
        from src.definitions import loader
        from src.definitions.models import (
            EnemyDefinition, AttributeDefinition, CombatStatDefinition, SkillDefinition,
            AttributesSet, EnemyCombatStats, ItemDefinition
        )
        from src.game_logic.status_effects import StatusEffect
        from src.game_logic.character import Character
    except ImportError as e: print(f"FEHLER in enemy.py: {e}", file=sys.stderr); sys.exit(1)

Combatant = Any

class Enemy:
    """ Repräsentiert eine Gegnerinstanz im Spiel mit einfacher KI. """
    def __init__(self, enemy_id: str):
        self.enemy_id: str = enemy_id
        self.definition: Optional[EnemyDefinition] = loader.get_enemy(enemy_id)
        if not self.definition: raise ValueError(f"Ungültige Gegner-ID: {enemy_id}")
        self.name: str = self.definition.name; self.level: int = self.definition.level
        self.base_attributes: AttributesSet = self.definition.attributes
        self.base_combat_stats: EnemyCombatStats = self.definition.combat_stats
        self.current_attributes: AttributesSet = self.base_attributes
        self.current_combat_stats: Dict[str, Any] = {}
        self.known_skill_ids: List[str] = list(self.definition.skills)
        self.active_effects: List[StatusEffect] = []
        # Gegner haben keine Ausrüstung im Spielersinne
        # self.equipment: Dict[str, Optional[ItemDefinition]] = {}
        self._initialize_combat_stats()

    # ... (_initialize_combat_stats, get_attribute, get_combat_stat unverändert) ...
    def _initialize_combat_stats(self):
        max_hp = self.base_combat_stats.base_hp; self.current_combat_stats["MAX_HP"] = max_hp; self.current_combat_stats["CURRENT_HP"] = max_hp
        self.current_combat_stats["MAX_MANA"] = self.base_combat_stats.max_mana; self.current_combat_stats["CURRENT_MANA"] = self.current_combat_stats["MAX_MANA"]
        self.current_combat_stats["MAX_STAMINA"] = self.base_combat_stats.max_stamina; self.current_combat_stats["CURRENT_STAMINA"] = self.current_combat_stats["MAX_STAMINA"]
        self.current_combat_stats["MAX_ENERGY"] = self.base_combat_stats.max_energy; self.current_combat_stats["CURRENT_ENERGY"] = self.current_combat_stats["MAX_ENERGY"]
        self.current_combat_stats["ARMOR"] = self.base_combat_stats.base_armor; self.current_combat_stats["MAGIC_RESIST"] = self.base_combat_stats.base_magic_resist
        self.current_combat_stats["BASE_HIT_CHANCE"] = 90; self.current_combat_stats["INITIATIVE_BASE"] = 10

    def get_attribute(self, attr_id: str) -> int:
        base_value = getattr(self.current_attributes, attr_id.upper(), 0); modifier = 0
        if attr_id.upper() == "STR":
            for effect in self.active_effects:
                if effect.effect_id == "WEAKENED" and effect.magnitude is not None: modifier += effect.magnitude
        return base_value + modifier

    def get_combat_stat(self, stat_id: str) -> Optional[Any]:
        stat_upper = stat_id.upper(); base_value = self.current_combat_stats.get(stat_upper); modifier = 0; percentage_mod = 1.0
        if stat_upper == "ARMOR":
            for effect in self.active_effects:
                if effect.effect_id == "DEFENSE_UP" and effect.magnitude is not None: modifier += effect.magnitude
        elif stat_upper == "MAGIC_RESIST":
             for effect in self.active_effects:
                if effect.effect_id == "DEFENSE_UP" and effect.magnitude is not None: modifier += effect.magnitude
        elif stat_upper == "INITIATIVE":
             dex_bonus = (self.get_attribute("DEX") - 10) // 2; base_value = self.current_combat_stats.get("INITIATIVE_BASE", 10) + dex_bonus
             for effect in self.active_effects:
                  if effect.effect_id == "INITIATIVE_UP" and effect.magnitude is not None: modifier += effect.magnitude
        elif stat_upper == "ACCURACY_MODIFIER":
             base_value = (self.get_attribute("DEX") - 10) // 2
             for effect in self.active_effects:
                  if effect.effect_id == "ACCURACY_DOWN": modifier -= 3
        elif stat_upper == "EVASION_MODIFIER":
             base_value = (self.get_attribute("DEX") - 10) // 2
             for effect in self.active_effects:
                  if effect.effect_id == "SLOWED": modifier -= 2
        if base_value is not None and isinstance(base_value, (int, float)): return (base_value + modifier) * percentage_mod
        return base_value

    # *** NEU: Methode zum Prüfen von Tags ***
    def has_tag(self, tag: str) -> bool:
        """ Prüft, ob der Gegner diesen Tag in seiner Definition hat. """
        if self.definition and self.definition.tags:
             # Vergleiche case-insensitiv für Robustheit
             return tag.upper() in (t.upper() for t in self.definition.tags)
        return False

    def has_effect(self, effect_id: str) -> bool: return any(e.effect_id == effect_id for e in self.active_effects)
    def get_known_skills(self) -> List[Optional[SkillDefinition]]: return [loader.get_skill(sid) for sid in self.known_skill_ids]
    def get_xp_reward(self) -> int: return self.definition.xp_reward
    def is_alive(self) -> bool: return (self.current_combat_stats.get("CURRENT_HP", 0)) > 0

    # ... (apply_damage, apply_heal, consume_resource, add_effect, remove_effect, tick_effects wie zuvor) ...
    def apply_damage(self, amount: int, damage_type: str):
        if not self.is_alive(): return
        reduction = 0
        if damage_type.upper() == "PHYSICAL": reduction = self.get_combat_stat("ARMOR") or 0
        elif damage_type.upper() in ["FIRE", "FROST", "HOLY", "MAGIC"]: reduction = self.get_combat_stat("MAGIC_RESIST") or 0
        actual_damage = max(1, amount - reduction)
        current_hp = self.current_combat_stats.get("CURRENT_HP", 0); new_hp = max(0, current_hp - actual_damage)
        self.current_combat_stats["CURRENT_HP"] = new_hp
        print(f"{self.name} erleidet {actual_damage} {damage_type}-Schaden (reduziert um {reduction}). HP: {new_hp}/{self.get_combat_stat('MAX_HP')}")
        if not self.is_alive(): print(f"{self.name} wurde besiegt!")

    def apply_heal(self, amount: int):
        if not self.is_alive(): return
        current_hp = self.current_combat_stats.get("CURRENT_HP", 0); max_hp = self.get_combat_stat("MAX_HP") or 0
        effective_heal = min(amount, max_hp - current_hp)
        if effective_heal > 0: self.current_combat_stats["CURRENT_HP"] += effective_heal

    def consume_resource(self, resource_type: Optional[str], amount: int) -> bool:
         if not resource_type or amount <= 0: return True
         res_type_upper = resource_type.upper(); current_res_key = f"CURRENT_{res_type_upper}"
         current_amount = self.get_combat_stat(current_res_key)
         if current_amount is None: return False
         if current_amount >= amount: self.current_combat_stats[current_res_key] -= amount; return True
         else: return False

    def add_effect(self, effect: StatusEffect):
        for existing_effect in self.active_effects:
            if existing_effect.effect_id == effect.effect_id: existing_effect.duration_remaining = effect.total_duration; return
        print(f"{self.name} erhält Effekt: '{effect.display_name}' ({effect.duration_remaining} Runden)."); self.active_effects.append(effect)

    def remove_effect(self, effect_to_remove: StatusEffect):
        try: self.active_effects.remove(effect_to_remove); print(f"Effekt '{effect_to_remove.display_name}' von {self.name} entfernt.")
        except ValueError: pass

    def tick_effects(self):
        if not self.is_alive(): return; print(f"  [{self.name} Effekt-Tick]")
        expired_effects: List[StatusEffect] = []
        for i in range(len(self.active_effects) - 1, -1, -1):
            effect = self.active_effects[i]
            if effect.effect_id == "BURNING":
                 burn_damage = effect.magnitude or 3
                 if burn_damage > 0: print(f"  > {self.name} erleidet {burn_damage} Schaden durch '{effect.display_name}'."); self.apply_damage(burn_damage, "FIRE")
                 if not self.is_alive(): return
            effect.tick_down()
            if effect.is_expired(): print(f"  > Effekt '{effect.display_name}' ist abgelaufen."); expired_effects.append(effect)
        for expired in expired_effects: self.remove_effect(expired)

    def choose_action(self, player_target: Character) -> Optional[Tuple[SkillDefinition, Combatant]]:
        if not self.is_alive(): return None
        usable_skills: List[SkillDefinition] = []
        for skill in self.get_known_skills():
            if skill:
                cost = skill.cost; can_afford = True
                if cost.resource and cost.amount > 0:
                     current_res = self.get_combat_stat(f"CURRENT_{cost.resource.upper()}");
                     if current_res is None or current_res < cost.amount: can_afford = False
                if can_afford: usable_skills.append(skill)
        if not usable_skills: print(f"{self.name} passt (keine Skills)."); return None

        action: Optional[Tuple[SkillDefinition, Combatant]] = None
        current_hp = self.get_combat_stat("CURRENT_HP") or 0; max_hp = self.get_combat_stat("MAX_HP") or 1
        if current_hp / max_hp < 0.4:
             heal_skill = next((s for s in usable_skills if s.id == "heal_lesser"), None)
             if heal_skill: print(f"[{self.name} KI]: HP niedrig -> Heilen."); return (heal_skill, self)
        weakening_curse_skill = next((s for s in usable_skills if s.id == "weakening_curse"), None)
        if weakening_curse_skill and not player_target.has_effect("WEAKENED"):
             if random.random() < 0.4: print(f"[{self.name} KI]: -> Spieler schwächen."); return (weakening_curse_skill, player_target)
        power_strike_skill = next((s for s in usable_skills if s.id == "power_strike"), None)
        if power_strike_skill:
             if random.random() < 0.6: print(f"[{self.name} KI]: -> Mächtiger Schlag!"); return (power_strike_skill, player_target)
        damaging_skills = [s for s in usable_skills if any(e.type == "DAMAGE" for e in s.effects)]
        if damaging_skills: chosen_skill = random.choice(damaging_skills); print(f"[{self.name} KI]: -> Zufallsangriff."); return (chosen_skill, player_target)
        else: chosen_skill = random.choice(usable_skills); print(f"[{self.name} KI]: -> Zufallsaktion."); target = player_target if chosen_skill.target_type != "SELF" else self; return (chosen_skill, target)
        return None

    def display_short_status(self):
         hp_str = f"HP: {self.current_combat_stats.get('CURRENT_HP', 0)}/{self.get_combat_stat('MAX_HP') or 0}"
         effects_str = ""
         if self.active_effects: effects_str = " [" + ", ".join([e.display_name for e in self.active_effects]) + "]"
         # *** NEU: Tags anzeigen für Bonus-vs-Type-Test ***
         tags_str = f" ({', '.join(self.definition.tags)})" if self.definition and self.definition.tags else ""
         print(f"{self.name} (Lvl {self.level}){tags_str} - {hp_str}{effects_str}")

    def __str__(self): return f"{self.name} (Lvl {self.level})"

