from typing import List, Optional, Dict, Any, Tuple
import sys

try:
    from definitions import loader
    from definitions.models import (
        ClassDefinition, AttributeDefinition, CombatStatDefinition, SkillDefinition,
        AttributesSet, ClassCombatStats, ItemDefinition
    )
    from .status_effects import StatusEffect
except ImportError:
    try:
        from src.definitions import loader
        from src.definitions.models import (
            ClassDefinition, AttributeDefinition, CombatStatDefinition, SkillDefinition,
            AttributesSet, ClassCombatStats, ItemDefinition
        )
        from src.game_logic.status_effects import StatusEffect
    except ImportError as e: print(f"FEHLER in character.py: {e}", file=sys.stderr); sys.exit(1)

class Character:
    """ Repräsentiert eine Charakterinstanz im Spiel. """
    def __init__(self, name: str, class_id: str):
        self.name: str = name; self.class_id: str = class_id
        self.character_class: Optional[ClassDefinition] = loader.get_class(class_id)
        if not self.character_class: raise ValueError(f"Ungültige Klasse: {class_id}")
        self.base_attributes: AttributesSet = self.character_class.starting_attributes
        self.base_combat_stats: ClassCombatStats = self.character_class.starting_combat_stats
        self.level: int = 1; self.xp: int = 0
        self.current_attributes: AttributesSet = self.base_attributes
        self.current_combat_stats: Dict[str, Any] = {}
        self.known_skill_ids: List[str] = list(self.character_class.starting_skills)
        self.active_effects: List[StatusEffect] = []
        self.inventory: List[Any] = []
        self.equipment_slots = ["WEAPON_MAIN", "CHEST", "HEAD", "LEGS", "FEET"]
        self.equipment: Dict[str, Optional[ItemDefinition]] = {slot: None for slot in self.equipment_slots}
        self._initialize_combat_stats()
        self._assign_starting_equipment()

    def _assign_starting_equipment(self):
        start_weapon_id = None
        if self.class_id == "warrior": start_weapon_id = "short_sword"
        elif self.class_id == "mage": start_weapon_id = "wooden_staff"
        elif self.class_id == "rogue": start_weapon_id = "dagger"
        elif self.class_id == "cleric": start_weapon_id = "rusty_mace"
        if start_weapon_id:
            weapon = loader.get_item(start_weapon_id)
            if weapon and weapon.slot == "WEAPON_MAIN": self.equip_item(weapon)
            else: print(f"WARNUNG: Startwaffe '{start_weapon_id}' nicht gefunden/ausrüstbar.")

    def equip_item(self, item: ItemDefinition) -> bool:
        if not item.slot or item.slot not in self.equipment_slots: return False
        print(f"{self.name} rüstet '{item.name}' aus."); self.equipment[item.slot] = item; return True

    def unequip_item(self, slot: str) -> Optional[ItemDefinition]:
        if slot not in self.equipment_slots: return None
        item = self.equipment.get(slot)
        if item: print(f"{self.name} legt '{item.name}' ab."); self.equipment[slot] = None
        return item

    def get_equipped_item(self, slot: str) -> Optional[ItemDefinition]: return self.equipment.get(slot)

    def _initialize_combat_stats(self):
        con = self.current_attributes.CON; max_hp = 50 + con * 5
        self.current_combat_stats["MAX_HP"] = max_hp; self.current_combat_stats["CURRENT_HP"] = max_hp
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
        stat_upper = stat_id.upper(); base_value = self.current_combat_stats.get(stat_upper); modifier = 0; item_bonus = 0; percentage_mod = 1.0
        if stat_upper == "ARMOR" or stat_upper == "MAGIC_RESIST":
             for item in self.equipment.values():
                  if item and item.stats: item_bonus += getattr(item.stats, stat_upper.lower(), 0) or 0
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
        if base_value is not None and isinstance(base_value, (int, float)): return (base_value + item_bonus + modifier) * percentage_mod
        elif item_bonus != 0: return (item_bonus + modifier) * percentage_mod
        elif modifier != 0 and isinstance(modifier, (int, float)): return modifier * percentage_mod
        return base_value

    # *** NEU: Methode zum Prüfen von Tags (für Spieler aktuell nicht relevant, aber konsistent) ***
    def has_tag(self, tag: str) -> bool:
        """ Prüft, ob der Charakter diesen Tag hat (z.B. von Rasse, Klasse). Aktuell nicht genutzt. """
        # Beispiel: return tag.upper() in (self.character_class.tags or [])
        return False # Spieler haben (noch) keine Tags

    def has_effect(self, effect_id: str) -> bool: return any(e.effect_id == effect_id for e in self.active_effects)
    def get_known_skills(self) -> List[Optional[SkillDefinition]]: return [loader.get_skill(sid) for sid in self.known_skill_ids]
    def is_alive(self) -> bool: return (self.current_combat_stats.get("CURRENT_HP", 0)) > 0

    # ... (apply_damage, apply_heal, consume_resource, add_effect, remove_effect, tick_effects wie zuvor) ...
    def apply_damage(self, amount: int, damage_type: str):
        if not self.is_alive(): return; reduction = 0
        if damage_type.upper() == "PHYSICAL": reduction = self.get_combat_stat("ARMOR") or 0
        elif damage_type.upper() in ["FIRE", "FROST", "HOLY", "MAGIC"]: reduction = self.get_combat_stat("MAGIC_RESIST") or 0
        actual_damage = max(1, amount - reduction); current_hp = self.current_combat_stats.get("CURRENT_HP", 0); new_hp = max(0, current_hp - actual_damage)
        self.current_combat_stats["CURRENT_HP"] = new_hp; print(f"{self.name} erleidet {actual_damage} {damage_type}-Schaden (reduziert um {reduction}). HP: {new_hp}/{self.get_combat_stat('MAX_HP')}")
        if not self.is_alive(): print(f"{self.name} wurde besiegt!")
    def apply_heal(self, amount: int):
        if not self.is_alive(): return; current_hp = self.current_combat_stats.get("CURRENT_HP", 0); max_hp = self.get_combat_stat("MAX_HP") or 0
        effective_heal = min(amount, max_hp - current_hp)
        if effective_heal > 0: self.current_combat_stats["CURRENT_HP"] += effective_heal; print(f"{self.name} wird um {effective_heal} HP geheilt. HP: {self.current_combat_stats['CURRENT_HP']}/{max_hp}")
    def consume_resource(self, resource_type: Optional[str], amount: int) -> bool:
        if not resource_type or amount <= 0: return True; res_type_upper = resource_type.upper(); current_res_key = f"CURRENT_{res_type_upper}"
        current_amount = self.get_combat_stat(current_res_key); if current_amount is None: return False
        if current_amount >= amount: self.current_combat_stats[current_res_key] -= amount; print(f"{self.name} verbraucht {amount} {resource_type}. Übrig: {self.current_combat_stats[current_res_key]}"); return True
        else: print(f"{self.name} hat nicht genug {resource_type}..."); return False
    def add_effect(self, effect: StatusEffect):
        for existing_effect in self.active_effects:
            if existing_effect.effect_id == effect.effect_id: existing_effect.duration_remaining = effect.total_duration; return
        print(f"{self.name} erhält Effekt: '{effect.display_name}' ({effect.duration_remaining} Runden)."); self.active_effects.append(effect)
    def remove_effect(self, effect_to_remove: StatusEffect):
        try: self.active_effects.remove(effect_to_remove); print(f"Effekt '{effect_to_remove.display_name}' von {self.name} entfernt.")
        except ValueError: pass
    def tick_effects(self):
        if not self.is_alive(): return; print(f"  [{self.name} Effekt-Tick]"); expired_effects: List[StatusEffect] = []
        for i in range(len(self.active_effects) - 1, -1, -1):
            effect = self.active_effects[i]
            if effect.effect_id == "BURNING":
                 burn_damage = effect.magnitude or 3
                 if burn_damage > 0: print(f"  > {self.name} erleidet {burn_damage} Schaden durch '{effect.display_name}'."); self.apply_damage(burn_damage, "FIRE")
                 if not self.is_alive(): return
            effect.tick_down()
            if effect.is_expired(): print(f"  > Effekt '{effect.display_name}' ist abgelaufen."); expired_effects.append(effect)
        for expired in expired_effects: self.remove_effect(expired)

    def display_status(self):
        print(f"\n--- Status: {self.name} ({self.character_class.name} Lvl {self.level}) ---")
        hp = self.current_combat_stats.get("CURRENT_HP", 0); max_hp = self.get_combat_stat("MAX_HP") or 0; print(f"  HP: {hp} / {max_hp}")
        for res in ["MANA", "STAMINA", "ENERGY"]: max_res = self.get_combat_stat(f"MAX_{res}");
        if max_res is not None: print(f"  {res.capitalize()}: {self.current_combat_stats.get(f'CURRENT_{res}')} / {max_res}")
        effect_str = ", ".join([str(e) for e in self.active_effects]) or "Keine"; print(f"  Aktive Effekte: {effect_str}")
        print("  Ausrüstung:"); equipped_items_str = [];
        for slot, item in self.equipment.items():
             if item: equipped_items_str.append(f"{slot}: {item.name}")
        print(f"    {', '.join(equipped_items_str) or 'Nichts angelegt'}")
        print(f"  Attribute: STR={self.get_attribute('STR')} DEX={self.get_attribute('DEX')} INT={self.get_attribute('INT')} CON={self.get_attribute('CON')} WIS={self.get_attribute('WIS')}")
        print(f"  Kampfwerte: Rüstung={self.get_combat_stat('ARMOR')} MagRes={self.get_combat_stat('MAGIC_RESIST')} Init={self.get_combat_stat('INITIATIVE')}")
        print(f"  XP: {self.xp} / ???")
        known_skills = self.get_known_skills(); print(f"  Bekannte Skills: {', '.join([s.name for s in known_skills if s]) or 'Keine'}")
        print("-" * (len(self.name) + 24))

    def __str__(self): return f"{self.name} ({self.character_class.name} Lvl {self.level})"

