from typing import List, Optional, Dict, Any
import sys

# Zugriff auf geladene Definitionen und Modelle
try:
    from definitions import loader
    from definitions.models import (
        EnemyDefinition, AttributeDefinition, CombatStatDefinition, SkillDefinition,
        AttributesSet, EnemyCombatStats
    )
except ImportError:
    # Fallback für direktes Ausführen oder wenn PYTHONPATH nicht korrekt ist
    try:
        from src.definitions import loader
        from src.definitions.models import (
            EnemyDefinition, AttributeDefinition, CombatStatDefinition, SkillDefinition,
            AttributesSet, EnemyCombatStats
        )
    except ImportError:
        print("FEHLER: Konnte Definitionsmodule in enemy.py nicht importieren.", file=sys.stderr)
        sys.exit(1)

class Enemy:
    """
    Repräsentiert eine Gegnerinstanz im Spiel.
    Verwaltet den Zustand wie HP, Attribute, Skills, etc.
    """
    def __init__(self, enemy_id: str):
        self.enemy_id: str = enemy_id

        # Lade die Gegnerdefinition
        self.definition: Optional[EnemyDefinition] = loader.get_enemy(enemy_id)
        if not self.definition:
            raise ValueError(f"Ungültige Gegner-ID '{enemy_id}'.")

        self.name: str = self.definition.name # Name aus der Definition
        self.level: int = self.definition.level # Level aus der Definition

        # Basiswerte aus der Definition
        self.base_attributes: AttributesSet = self.definition.attributes
        self.base_combat_stats: EnemyCombatStats = self.definition.combat_stats # Enthält Basis-HP etc.

        # Aktuelle Werte - initialisiert mit Basiswerten
        self.current_attributes: AttributesSet = self.base_attributes # Vorerst Kopie
        self.current_combat_stats: Dict[str, Any] = {} # Wird unten befüllt

        # Skills & Effekte
        self.known_skill_ids: List[str] = list(self.definition.skills)
        self.active_effects: List[Any] = [] # TODO: Eigene Klasse für StatusEffekte

        # Initialisiere aktuelle Kampfwerte
        self._initialize_combat_stats()

    def _initialize_combat_stats(self):
        """Setzt die initialen aktuellen Kampfwerte basierend auf Attributen und Definition."""
        # HP (Basis-HP kommt direkt aus der Definition, wo sie berechnet wurde)
        max_hp = self.base_combat_stats.base_hp
        self.current_combat_stats["MAX_HP"] = max_hp
        self.current_combat_stats["CURRENT_HP"] = max_hp

        # Ressourcen (Mana, Stamina, Energy) aus der Definition
        self.current_combat_stats["MAX_MANA"] = self.base_combat_stats.max_mana
        self.current_combat_stats["CURRENT_MANA"] = self.current_combat_stats["MAX_MANA"]
        self.current_combat_stats["MAX_STAMINA"] = self.base_combat_stats.max_stamina
        self.current_combat_stats["CURRENT_STAMINA"] = self.current_combat_stats["MAX_STAMINA"]
        self.current_combat_stats["MAX_ENERGY"] = self.base_combat_stats.max_energy
        self.current_combat_stats["CURRENT_ENERGY"] = self.current_combat_stats["MAX_ENERGY"]

        # Verteidigung aus der Definition
        self.current_combat_stats["ARMOR"] = self.base_combat_stats.base_armor
        self.current_combat_stats["MAGIC_RESIST"] = self.base_combat_stats.base_magic_resist

        # Offensive Stats (Beispiele, basierend auf Attributen)
        # TODO: Diese Berechnungen verfeinern
        str_bonus = (self.current_attributes.STR - 10) // 2
        dex_bonus = (self.current_attributes.DEX - 10) // 2
        int_bonus = (self.current_attributes.INT - 10) // 2
        wis_bonus = (self.current_attributes.WIS - 10) // 2

        # Genauigkeit/Ausweichen für Trefferchance-Berechnung
        self.current_combat_stats["ACCURACY_MODIFIER"] = dex_bonus
        self.current_combat_stats["EVASION_MODIFIER"] = dex_bonus

        # Basis-Trefferchance
        self.current_combat_stats["BASE_HIT_CHANCE"] = 90 # Prozent

        # Initiative (Beispiel)
        self.current_combat_stats["INITIATIVE"] = 10 + dex_bonus


    # --- Zugriffs-Methoden ---
    def get_attribute(self, attr_id: str) -> int:
        """Gibt den aktuellen Wert eines Primärattributs zurück."""
        return getattr(self.current_attributes, attr_id.upper(), 0)

    def get_combat_stat(self, stat_id: str) -> Optional[Any]:
        """Gibt den aktuellen Wert eines Kampfwerts zurück."""
        return self.current_combat_stats.get(stat_id.upper())

    def get_known_skills(self) -> List[Optional[SkillDefinition]]:
         """Gibt die SkillDefinition-Objekte der bekannten Skills zurück."""
         return [loader.get_skill(sid) for sid in self.known_skill_ids]

    def get_xp_reward(self) -> int:
        """Gibt die XP zurück, die dieser Gegner bei Besiegen gewährt."""
        return self.definition.xp_reward

    # --- Zustandsprüfungen ---
    def is_alive(self) -> bool:
        """Prüft, ob der Gegner noch Lebenspunkte hat."""
        return self.get_combat_stat("CURRENT_HP") > 0

    # --- Aktionen / Zustandsänderungen (Sehr ähnlich zu Character) ---
    def apply_damage(self, amount: int, damage_type: str):
        """Verrechnet eingehenden Schaden unter Berücksichtigung von Resistenzen."""
        if not self.is_alive():
            return

        reduction = 0
        if damage_type.upper() == "PHYSICAL":
            reduction = self.get_combat_stat("ARMOR") or 0
        elif damage_type.upper() in ["FIRE", "FROST", "HOLY", "MAGIC"]:
             reduction = self.get_combat_stat("MAGIC_RESIST") or 0

        actual_damage = max(1, amount - reduction)
        current_hp = self.get_combat_stat("CURRENT_HP")
        new_hp = max(0, current_hp - actual_damage)
        self.current_combat_stats["CURRENT_HP"] = new_hp
        print(f"{self.name} erleidet {actual_damage} {damage_type}-Schaden (reduziert um {reduction}). HP: {new_hp}/{self.get_combat_stat('MAX_HP')}")
        if not self.is_alive():
            print(f"{self.name} wurde besiegt!")

    def apply_heal(self, amount: int):
        """Heilt den Gegner, bis maximal MAX_HP."""
        if not self.is_alive():
            return

        current_hp = self.get_combat_stat("CURRENT_HP")
        max_hp = self.get_combat_stat("MAX_HP")
        effective_heal = min(amount, max_hp - current_hp)
        if effective_heal > 0:
            self.current_combat_stats["CURRENT_HP"] += effective_heal
            print(f"{self.name} wird um {effective_heal} HP geheilt. HP: {self.get_combat_stat('CURRENT_HP')}/{max_hp}")

    def consume_resource(self, resource_type: Optional[str], amount: int) -> bool:
        """Prüft, ob genug Ressource vorhanden ist und zieht sie ab."""
        if not resource_type or amount <= 0:
            return True

        res_type_upper = resource_type.upper()
        current_res_key = f"CURRENT_{res_type_upper}"
        current_amount = self.get_combat_stat(current_res_key)

        if current_amount is None:
            # Gegner hat diese Ressource nicht standardmäßig, ok wenn Skill sie nicht braucht
            return False # Skill kann nicht verwendet werden, wenn Ressource nicht existiert

        if current_amount >= amount:
            self.current_combat_stats[current_res_key] -= amount
            # Optional: Ausgabe für Gegner-Ressourcenverbrauch unterdrücken?
            # print(f"{self.name} verbraucht {amount} {resource_type}. Übrig: {self.current_combat_stats[current_res_key]}")
            return True
        else:
            # print(f"{self.name} hat nicht genug {resource_type}.") # Ausgabe unterdrücken?
            return False

    # --- TODO: Effekt-Methoden (add_effect, remove_effect, update_effects) ---

    # --- Darstellung ---
    def display_short_status(self):
         """Gibt eine kurze Statuszeile aus."""
         hp_str = f"HP: {self.get_combat_stat('CURRENT_HP')}/{self.get_combat_stat('MAX_HP')}"
         print(f"{self.name} (Lvl {self.level}) - {hp_str}")

    def __str__(self):
        return f"{self.name} (Lvl {self.level})"

