# src/game_logic/character.py

import logging # Import standard logging
from typing import Dict, List, Optional

# Import necessary definitions and config constants
from src.definitions.base_definitions import CharacterClassDefinition, SkillDefinition
from src.definitions.loaders import SkillDatabase # Type Alias for skill_db parameter
from src.config import BASE_HP, CON_HP_MODIFIER, ATTRIBUTE_BONUS_BASE, ATTRIBUTE_BONUS_DIVISOR

# Get a logger for this module
# Wichtig: Das Logging muss vorher durch setup_logging() konfiguriert worden sein!
logger = logging.getLogger(__name__)

class Character:
    """
    Repräsentiert einen Charakter im Spiel (Spieler, NPC, Gegner).
    Hält den aktuellen Zustand des Charakters.
    """
    def __init__(self, name: str, class_definition: CharacterClassDefinition, skill_db: SkillDatabase):
        """
        Initialisiert einen neuen Charakter.

        Args:
            name: Der Name des Charakters.
            class_definition: Die CharacterClassDefinition-Instanz für die Klasse des Charakters.
            skill_db: Die geladene Skill-Datenbank (Dict[str, SkillDefinition]) für Skill-Lookups.
        """
        self.name: str = name
        self.class_definition: CharacterClassDefinition = class_definition
        logger.info(f"Erstelle Charakter '{self.name}' mit Klasse '{self.class_definition.name}'.")

        # --- Attribute ---
        # Speichert die aktuellen Attributwerte. Initialisiert mit den Basiswerten der Klasse.
        # Wir kopieren das Dict, damit spätere Änderungen (Buffs/Debuffs) nur diesen Charakter betreffen.
        # Beinhaltet auch Basis-Kampfwerte und Ressourcen-Maxima, die im base_stats dict der Klasse stehen.
        self.attributes: Dict[str, int] = self.class_definition.base_stats.copy()
        logger.debug(f"'{self.name}' - Basis-Attribute/Stats initialisiert: {self.attributes}")

        # --- Combat Stats ---
        # Speichert aktuelle abgeleitete Kampfwerte, getrennt von primären Attributen,
        # initialisiert aus den Werten im (kopierten) attributes-Dict.
        self.combat_stats: Dict[str, int] = {}
        self.combat_stats["ARMOR"] = self.attributes.get("ARMOR", 0)
        self.combat_stats["MAGIC_RES"] = self.attributes.get("MAGIC_RES", 0)
        # TODO: Später berechnete Stats hinzufügen (Hit Chance, Evasion etc.)
        logger.debug(f"'{self.name}' - Initial Kampf-Stats: {self.combat_stats}")

        # --- Resources ---
        # Berechne maximale Ressourcen basierend auf Basiswerten und Formeln
        base_con = self.attributes.get("CON", ATTRIBUTE_BONUS_BASE) # Fallback auf Base 10 falls CON fehlt?
        if "CON" not in self.attributes:
             # Dieser Fall sollte nicht eintreten, wenn CON in primary_attributes definiert ist
             logger.warning(f"Konstitution ('CON') nicht in base_stats für Klasse '{self.class_definition.id}' gefunden! HP-Berechnung könnte ungenau sein.")

        # Berechne Max HP mit der Formel aus config
        max_hp = BASE_HP + base_con * CON_HP_MODIFIER
        self.max_resources: Dict[str, int] = {
            "HP": max_hp,
            "MANA": self.attributes.get("MANA", 0), # Nimmt Basis-Mana aus Klasse
            "STAMINA": self.attributes.get("STAMINA", 0), # Nimmt Basis-Stamina aus Klasse
            "ENERGY": self.attributes.get("ENERGY", 0) # Nimmt Basis-Energy aus Klasse
        }
        # Aktuelle Ressourcen initial auf Maximum setzen
        self.current_resources: Dict[str, int] = self.max_resources.copy()
        logger.debug(f"'{self.name}' - Ressourcen initialisiert: Max={self.max_resources}, Current={self.current_resources}")

        # --- Skills ---
        # Speichert die bekannten Skills des Charakters als Dict für schnellen Zugriff
        self.known_skills: Dict[str, SkillDefinition] = {}
        logger.debug(f"Lade Start-Skills für '{self.name}': {self.class_definition.starting_skills}")
        for skill_id in self.class_definition.starting_skills:
            skill_def = skill_db.get(skill_id)
            if skill_def:
                self.known_skills[skill_id] = skill_def
                logger.debug(f"'{self.name}' kennt jetzt Skill '{skill_id}'.")
            else:
                # Wichtig: Damit diese Warnung sichtbar wird, muss das Logging
                # (durch setup_logging) vorher konfiguriert worden sein!
                logger.warning(f"Start-Skill '{skill_id}' für Klasse '{self.class_definition.id}' wurde nicht in der Skill-Datenbank gefunden!")

        # --- Zustand ---
        self._is_defeated: bool = False # Interner Zustand, ob der Charakter besiegt ist

        # TODO: Später hinzufügen
        # self.status_effects: Dict[str, StatusEffectInstance] = {}
        # self.equipment: Dict[str, Optional[ItemDefinition]] = {} # z.B. "weapon", "armor"
        # self.level: int = 1
        # self.experience: int = 0


    def get_attribute(self, attribute_id: str) -> int:
        """Gibt den aktuellen Wert eines Attributs zurück (z.B. STR, DEX)."""
        # TODO: Später Boni von Ausrüstung / Effekten einrechnen
        base_value = self.attributes.get(attribute_id, 0)
        # Hier könnten Buffs/Debuffs verrechnet werden
        return base_value

    def get_attribute_bonus(self, attribute_id: str) -> int:
        """Berechnet den Bonus für ein gegebenes Attribut."""
        value = self.get_attribute(attribute_id)
        # Wende die globale Formel aus der Konfiguration an
        bonus = (value - ATTRIBUTE_BONUS_BASE) // ATTRIBUTE_BONUS_DIVISOR
        # logger.debug(f"Bonus für {attribute_id} ({value}) berechnet: {bonus}") # Optional: Sehr detailreiches Logging
        return bonus

    def get_combat_stat(self, stat_id: str) -> int:
        """Gibt den aktuellen Wert eines Kampfwertes zurück (z.B. ARMOR)."""
        # TODO: Später Boni von Ausrüstung / Effekten einrechnen
        base_value = self.combat_stats.get(stat_id, 0)
         # Hier könnten Buffs/Debuffs verrechnet werden
        return base_value

    def take_damage(self, amount: int, damage_type: str = "PHYSICAL"):
        """
        Verarbeitet erlittenen Schaden, berücksichtigt Resistenzen (vereinfacht)
        und aktualisiert den Zustand des Charakters.
        """
        if self._is_defeated:
            # logger.debug(f"'{self.name}' ist bereits besiegt, nimmt keinen Schaden mehr.") # Optional: Logging
            return

        # Schadensreduktion (Mitigation) - Beispielimplementierung
        mitigated_amount = amount
        if damage_type == "PHYSICAL":
             armor = self.get_combat_stat("ARMOR")
             # Beispiel Formel: Schaden * (100 / (100 + Rüstung)) - Mindestens 0 Schaden
             mitigated_amount = max(0, int(amount * (100 / (100 + armor))))
             # logger.debug(f"'{self.name}' - Physischer Schaden {amount} reduziert auf {mitigated_amount} durch Rüstung {armor}.")
        elif damage_type in ["MAGIC", "FIRE", "FROST", "HOLY"]: # etc.
             magic_res = self.get_combat_stat("MAGIC_RES")
             mitigated_amount = max(0, int(amount * (100 / (100 + magic_res))))
             # logger.debug(f"'{self.name}' - Mag. Schaden {amount} reduziert auf {mitigated_amount} durch Mag.Res {magic_res}.")
        else:
             logger.warning(f"Unbekannter Schadenstyp '{damage_type}' erhalten bei take_damage für '{self.name}'. Wende keine Mitigation an.")
             mitigated_amount = max(0, amount)


        actual_damage = mitigated_amount
        self.current_resources["HP"] = max(0, self.current_resources["HP"] - actual_damage)
        logger.info(f"'{self.name}' erleidet {actual_damage} {damage_type}-Schaden. HP: {self.current_resources['HP']}/{self.max_resources['HP']}")

        if self.current_resources["HP"] == 0:
            self._set_defeated_state()

    def heal(self, amount: int):
        """Heilt den Charakter bis zum Maximalwert."""
        if self._is_defeated:
             # logger.debug(f"'{self.name}' ist bereits besiegt, kann nicht geheilt werden.") # Optional: Logging
             return

        actual_heal = max(0, amount) # Keine negative Heilung
        old_hp = self.current_resources["HP"]
        max_hp = self.max_resources["HP"]
        self.current_resources["HP"] = min(max_hp, old_hp + actual_heal)

        healed_amount = self.current_resources["HP"] - old_hp
        if healed_amount > 0:
            logger.info(f"'{self.name}' wird um {healed_amount} HP geheilt. HP: {self.current_resources['HP']}/{max_hp}")
        # else:
            # logger.debug(f"'{self.name}' ist bereits bei vollen HP oder Heilung war 0.") # Optional: Logging


    def consume_resource(self, resource_id: str, amount: int) -> bool:
        """
        Versucht, eine Ressource zu verbrauchen.

        Args:
            resource_id: Die ID der Ressource (z.B. "MANA").
            amount: Der zu verbrauchende Betrag.

        Returns:
            True, wenn die Ressource erfolgreich verbraucht wurde, sonst False.
        """
        if amount <= 0:
            return True # Nichts zu verbrauchen oder ungültiger Betrag

        current_amount = self.current_resources.get(resource_id)
        if current_amount is None:
             logger.warning(f"Versuch, unbekannte Ressource '{resource_id}' für '{self.name}' zu verbrauchen.")
             return False # Ressource existiert nicht für diesen Charakter

        if current_amount >= amount:
            self.current_resources[resource_id] = current_amount - amount
            logger.debug(f"'{self.name}' verbraucht {amount} {resource_id}. Verbleibend: {self.current_resources[resource_id]}")
            return True
        else:
            logger.info(f"'{self.name}' hat nicht genug {resource_id} (benötigt {amount}, hat {current_amount}).")
            return False

    def is_alive(self) -> bool:
        """Prüft, ob der Charakter noch am Leben ist."""
        return not self._is_defeated

    def _set_defeated_state(self):
        """Interner Helper, um den Charakter als besiegt zu markieren."""
        if not self._is_defeated:
            self._is_defeated = True
            logger.info(f"'{self.name}' wurde besiegt!")
            # TODO: Event auslösen / Zustand für Spiel-Logik ändern (z.B. Entfernen aus Kampf)

    def __str__(self) -> str:
        """Gibt eine ausführliche String-Repräsentation des Charakters zurück."""
        resource_str = ", ".join(f"{k}: {self.current_resources.get(k, 0)}/{self.max_resources.get(k, 0)}" for k in self.max_resources)
        skill_names = [s.name for s in self.known_skills.values()] # Zeige Skill-Namen statt IDs
        return (f"--- Character: {self.name} ---\n"
                f"  Class: {self.class_definition.name}\n"
                f"  Status: {'Lebendig' if self.is_alive() else 'Besiegt'}\n"
                f"  Resources: {resource_str}\n"
                # f"  Attributes: {self.attributes}\n" # Kann lang sein, evtl. weglassen?
                # f"  Combat Stats: {self.combat_stats}\n"
                f"  Known Skills ({len(skill_names)}): {', '.join(skill_names) or 'Keine'}")


    def __repr__(self) -> str:
        """Gibt eine kompaktere Repräsentation zurück, nützlich in Listen etc."""
        return f"Character(name='{self.name}', class='{self.class_definition.id}')"