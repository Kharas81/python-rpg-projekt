from typing import List, Optional, Dict, Any
import sys

# Zugriff auf geladene Definitionen und Modelle
try:
    from definitions import loader
    from definitions.models import (
        ClassDefinition, AttributeDefinition, CombatStatDefinition, SkillDefinition,
        AttributesSet, ClassCombatStats
    )
except ImportError:
    # Fallback für direktes Ausführen oder wenn PYTHONPATH nicht korrekt ist
    try:
        from src.definitions import loader
        from src.definitions.models import (
            ClassDefinition, AttributeDefinition, CombatStatDefinition, SkillDefinition,
            AttributesSet, ClassCombatStats
        )
    except ImportError:
        print("FEHLER: Konnte Definitionsmodule in character.py nicht importieren.", file=sys.stderr)
        sys.exit(1)


class Character:
    """
    Repräsentiert eine Charakterinstanz im Spiel (Spieler oder NPC).
    Verwaltet den Zustand wie HP, Attribute, Skills, Effekte etc.
    """
    def __init__(self, name: str, class_id: str):
        self.name: str = name
        self.class_id: str = class_id

        # Lade die Klassendefinition
        self.character_class: Optional[ClassDefinition] = loader.get_class(class_id)
        if not self.character_class:
            # TODO: Bessere Fehlerbehandlung / Logging
            raise ValueError(f"Ungültige Klassen-ID '{class_id}' für Charakter '{name}'.")

        # Basiswerte aus der Klassendefinition
        self.base_attributes: AttributesSet = self.character_class.starting_attributes
        self.base_combat_stats: ClassCombatStats = self.character_class.starting_combat_stats

        # Aktuelle Werte - initialisiert mit Basiswerten, können sich ändern
        self.level: int = 1
        self.xp: int = 0
        self.current_attributes: AttributesSet = self.base_attributes # Vorerst Kopie, später ggf. eigene Instanz für Modifikationen
        self.current_combat_stats: Dict[str, Any] = {} # Wird unten befüllt

        # Skills & Effekte
        self.known_skill_ids: List[str] = list(self.character_class.starting_skills) # IDs der bekannten Skills
        # Optional: Direkt SkillDefinition Objekte speichern?
        # self.known_skills: List[SkillDefinition] = [loader.get_skill(sid) for sid in self.character_class.starting_skills if loader.get_skill(sid)]
        self.active_effects: List[Any] = [] # TODO: Eigene Klasse für StatusEffekte

        # Inventar & Ausrüstung (Platzhalter)
        self.inventory: List[Any] = []
        self.equipment: Dict[str, Any] = {} # z.B. {"weapon": item_obj, "armor": item_obj}

        # Initialisiere aktuelle Kampfwerte
        self._initialize_combat_stats()

    def _initialize_combat_stats(self):
        """Setzt die initialen aktuellen Kampfwerte basierend auf Attributen und Klasse."""
        # HP
        con_value = self.current_attributes.CON
        max_hp = 50 + con_value * 5 # Formel aus Doku 
        self.current_combat_stats["MAX_HP"] = max_hp
        self.current_combat_stats["CURRENT_HP"] = max_hp

        # Ressourcen (Mana, Stamina, Energy)
        self.current_combat_stats["MAX_MANA"] = self.base_combat_stats.max_mana
        self.current_combat_stats["CURRENT_MANA"] = self.current_combat_stats["MAX_MANA"]
        self.current_combat_stats["MAX_STAMINA"] = self.base_combat_stats.max_stamina
        self.current_combat_stats["CURRENT_STAMINA"] = self.current_combat_stats["MAX_STAMINA"]
        self.current_combat_stats["MAX_ENERGY"] = self.base_combat_stats.max_energy
        self.current_combat_stats["CURRENT_ENERGY"] = self.current_combat_stats["MAX_ENERGY"]

        # Verteidigung
        self.current_combat_stats["ARMOR"] = self.base_combat_stats.base_armor
        self.current_combat_stats["MAGIC_RESIST"] = self.base_combat_stats.base_magic_resist

        # Offensive Stats (Beispiele, basierend auf Attributen)
        # TODO: Diese Berechnungen verfeinern und evtl. in eigene Methoden auslagern
        str_bonus = (self.current_attributes.STR - 10) // 2
        dex_bonus = (self.current_attributes.DEX - 10) // 2
        int_bonus = (self.current_attributes.INT - 10) // 2
        wis_bonus = (self.current_attributes.WIS - 10) // 2

        # Genauigkeit/Ausweichen für Trefferchance-Berechnung 
        self.current_combat_stats["ACCURACY_MODIFIER"] = dex_bonus
        self.current_combat_stats["EVASION_MODIFIER"] = dex_bonus

        # Basis-Trefferchance (könnte auch aus config kommen)
        self.current_combat_stats["BASE_HIT_CHANCE"] = 90 # Prozent

        # Initiative (Beispiel)
        self.current_combat_stats["INITIATIVE"] = 10 + dex_bonus

        # Attribut-Boni für Schaden/Heilung speichern? Oder bei Bedarf berechnen?
        # self.current_combat_stats["STR_BONUS"] = str_bonus
        # self.current_combat_stats["DEX_BONUS"] = dex_bonus
        # self.current_combat_stats["INT_BONUS"] = int_bonus
        # self.current_combat_stats["WIS_BONUS"] = wis_bonus

    # --- Zugriffs-Methoden ---
    def get_attribute(self, attr_id: str) -> int:
        """Gibt den aktuellen Wert eines Primärattributs zurück."""
        # Nutzt getattr, um sicher auf Attribute von current_attributes zuzugreifen
        return getattr(self.current_attributes, attr_id.upper(), 0)

    def get_combat_stat(self, stat_id: str) -> Optional[Any]:
        """Gibt den aktuellen Wert eines Kampfwerts zurück."""
        return self.current_combat_stats.get(stat_id.upper())

    def get_known_skills(self) -> List[Optional[SkillDefinition]]:
         """Gibt die SkillDefinition-Objekte der bekannten Skills zurück."""
         return [loader.get_skill(sid) for sid in self.known_skill_ids]

    # --- Zustandsprüfungen ---
    def is_alive(self) -> bool:
        """Prüft, ob der Charakter noch Lebenspunkte hat."""
        return self.get_combat_stat("CURRENT_HP") > 0

    # --- Aktionen / Zustandsänderungen (Beispiele) ---
    def apply_damage(self, amount: int, damage_type: str):
        """Verrechnet eingehenden Schaden unter Berücksichtigung von Resistenzen."""
        if not self.is_alive():
            return

        reduction = 0
        if damage_type.upper() == "PHYSICAL":
            reduction = self.get_combat_stat("ARMOR") or 0
        elif damage_type.upper() in ["FIRE", "FROST", "HOLY", "MAGIC"]: # Annahme: Alle nicht-physischen Typen nutzen Magieresistenz
             reduction = self.get_combat_stat("MAGIC_RESIST") or 0
        # TODO: Andere Schadensarten?

        actual_damage = max(1, amount - reduction) # Schaden kann nicht unter 1 fallen 
        current_hp = self.get_combat_stat("CURRENT_HP")
        new_hp = max(0, current_hp - actual_damage) # HP können nicht unter 0 fallen
        self.current_combat_stats["CURRENT_HP"] = new_hp
        print(f"{self.name} erleidet {actual_damage} {damage_type}-Schaden (reduziert um {reduction}). HP: {new_hp}/{self.get_combat_stat('MAX_HP')}")
        if not self.is_alive():
            print(f"{self.name} wurde besiegt!")

    def apply_heal(self, amount: int):
        """Heilt den Charakter, bis maximal MAX_HP."""
        if not self.is_alive(): # Kann man besiegte Ziele heilen? Vorerst nein.
            return

        current_hp = self.get_combat_stat("CURRENT_HP")
        max_hp = self.get_combat_stat("MAX_HP")
        effective_heal = min(amount, max_hp - current_hp) # Heile nicht über max HP hinaus
        if effective_heal > 0:
            self.current_combat_stats["CURRENT_HP"] += effective_heal
            print(f"{self.name} wird um {effective_heal} HP geheilt. HP: {self.get_combat_stat('CURRENT_HP')}/{max_hp}")
        else:
             print(f"{self.name} ist bereits bei vollen HP.")


    def consume_resource(self, resource_type: Optional[str], amount: int) -> bool:
        """
        Prüft, ob genug Ressource vorhanden ist und zieht sie ab.
        Gibt True zurück, wenn erfolgreich, sonst False.
        """
        if not resource_type or amount <= 0:
            return True # Keine Kosten oder ungültiger Betrag

        res_type_upper = resource_type.upper()
        current_res_key = f"CURRENT_{res_type_upper}"
        current_amount = self.get_combat_stat(current_res_key)

        if current_amount is None:
            print(f"WARNUNG: Charakter {self.name} hat keine Ressource '{resource_type}'.")
            return False # Charakter hat diese Ressource nicht

        if current_amount >= amount:
            self.current_combat_stats[current_res_key] -= amount
            print(f"{self.name} verbraucht {amount} {resource_type}. Übrig: {self.current_combat_stats[current_res_key]}")
            return True
        else:
            print(f"{self.name} hat nicht genug {resource_type} (benötigt {amount}, hat {current_amount}).")
            return False

    # --- TODO: Weitere Methoden ---
    # def add_xp(self, amount: int): ... # Mit Level-Up Check
    # def level_up(self): ... # Erhöhung von Attributen/Stats, ggf. neue Skills
    # def calculate_derived_stats(self): ... # Methode, um Stats neu zu berechnen, wenn sich Attribute ändern
    # def add_effect(self, effect): ...
    # def remove_effect(self, effect): ...
    # def update_effects(self): ... # Pro Runde aufrufen

    # --- Darstellung ---
    def display_status(self):
        """Gibt den aktuellen Status des Charakters auf der Konsole aus."""
        print(f"\n--- Status: {self.name} ({self.character_class.name} Lvl {self.level}) ---")
        print(f"  HP: {self.get_combat_stat('CURRENT_HP')} / {self.get_combat_stat('MAX_HP')}")
        # Ressourcen anzeigen, wenn vorhanden
        for res in ["MANA", "STAMINA", "ENERGY"]:
             max_res = self.get_combat_stat(f"MAX_{res}")
             if max_res is not None:
                 cur_res = self.get_combat_stat(f"CURRENT_{res}")
                 print(f"  {res}: {cur_res} / {max_res}")

        print(f"  Attribute: STR={self.get_attribute('STR')} DEX={self.get_attribute('DEX')} "
              f"INT={self.get_attribute('INT')} CON={self.get_attribute('CON')} WIS={self.get_attribute('WIS')}")
        print(f"  Kampfwerte: Rüstung={self.get_combat_stat('ARMOR')} MagRes={self.get_combat_stat('MAGIC_RESIST')} "
              f"Init={self.get_combat_stat('INITIATIVE')}") # Weitere Stats hinzufügen?
        print(f"  XP: {self.xp} / ???") # TODO: XP bis zum nächsten Level anzeigen
        known_skills = self.get_known_skills()
        print(f"  Bekannte Skills: {', '.join([s.name for s in known_skills if s]) or 'Keine'}")
        # print(f"  Aktive Effekte: {self.active_effects or 'Keine'}") # Wenn Effekte implementiert sind
        print("-" * (len(self.name) + 24))

    def __str__(self):
        return f"{self.name} ({self.character_class.name} Lvl {self.level})"

