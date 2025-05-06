import typing
import logging

# Importiere die Basis-Definition und den Loader
# Annahme: Läuft im Kontext von 'src' oder sys.path ist angepasst
try:
    from src.definitions.character import Character as CharacterDefinition # Umbenannt zur Klarheit
    from src.definitions import loader
    from src.game_logic.formulas import calculate_max_hp, calculate_attribute_bonus
except ModuleNotFoundError:
    # Einfacher Fallback für direktes Testen, wenn sys.path nicht angepasst wurde
    print("WARNUNG: Konnte Module nicht direkt laden, versuche relativen Import (nur für Test)")
    from ..definitions.character import Character as CharacterDefinition
    from ..definitions import loader
    from .formulas import calculate_max_hp, calculate_attribute_bonus


logger = logging.getLogger(__name__)

class CharacterInstance:
    """
    Repräsentiert eine konkrete Instanz eines Charakters oder Gegners im Spiel
    mit dynamischem Zustand (HP, Mana, Effekte etc.).
    """
    def __init__(self, definition: CharacterDefinition):
        """
        Initialisiert eine Charakter-Instanz basierend auf einer Definition.

        Args:
            definition: Das Character-Definitionsobjekt (geladen via loader).
        """
        self.definition: CharacterDefinition = definition
        self.name: str = definition.name
        self.level: int = definition.level

        # Attribute kopieren (könnten sich später durch Effekte ändern)
        self.attributes: typing.Dict[str, int] = definition.attributes.copy()

        # Max HP berechnen und aktuelle HP setzen
        base_hp = self.definition.get_combat_value('base_hp')
        con = self.get_attribute('CON') # Nutzt die Methode unten
        self.max_hp: int = calculate_max_hp(base_hp, con)
        self.current_hp: int = self.max_hp

        # Max/Current Mana, Stamina, Energy initialisieren
        self.max_mana: int = self.definition.get_combat_value('base_mana')
        self.current_mana: int = self.max_mana
        self.max_stamina: int = self.definition.get_combat_value('base_stamina')
        self.current_stamina: int = self.max_stamina
        self.max_energy: int = self.definition.get_combat_value('base_energy')
        self.current_energy: int = self.max_energy

        # Rüstung und Magieresistenz (können sich durch Effekte ändern)
        self.armor: int = self.definition.get_combat_value('armor')
        self.magic_resist: int = self.definition.get_combat_value('magic_resist')

        # Status-Effekte (Liste oder Dict, hier erstmal leer)
        self.status_effects: typing.List[typing.Any] = [] # TODO: Eigene Klasse für Effekte?

        self.is_alive_flag: bool = True

        logger.debug(f"Charakter-Instanz '{self.name}' erstellt: HP={self.current_hp}/{self.max_hp}")

    def get_attribute(self, attr_name: str, base_value: bool = False) -> int:
        """
        Gibt den aktuellen Wert eines Attributs zurück.
        TODO: Berücksichtigt später Modifikatoren durch Status-Effekte.

        Args:
            attr_name: Der Name des Attributs (z.B. "STR").
            base_value: Wenn True, wird der Basiswert ohne Modifikatoren zurückgegeben.

        Returns:
            Der (ggf. modifizierte) Attributwert.
        """
        # Momentan nur der Basiswert
        # Später: Basiswert holen und Modifikatoren aus self.status_effects anwenden
        base_val = self.attributes.get(attr_name.upper(), 0)
        if base_value:
            return base_val
        else:
            # Hier Logik für Modifikatoren einfügen
            modified_val = base_val # Platzhalter
            return modified_val

    def get_attribute_bonus(self, attr_name: str) -> int:
        """Berechnet den Attribut-Bonus für das aktuelle Attribut."""
        current_value = self.get_attribute(attr_name)
        return calculate_attribute_bonus(current_value)

    def take_damage(self, amount: int):
        """Verringert die aktuellen HP um den gegebenen Betrag."""
        if amount <= 0 or not self.is_alive_flag:
            return # Kein Schaden oder bereits besiegt

        self.current_hp -= amount
        logger.info(f"'{self.name}' erleidet {amount} Schaden. HP: {self.current_hp}/{self.max_hp}")

        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_alive_flag = False
            logger.info(f"'{self.name}' wurde besiegt!")
            # TODO: Event auslösen?

    def heal(self, amount: int):
        """Erhöht die aktuellen HP um den gegebenen Betrag, maximal bis max_hp."""
        if amount <= 0 or not self.is_alive_flag:
            return

        healed_amount = min(amount, self.max_hp - self.current_hp)
        if healed_amount > 0:
            self.current_hp += healed_amount
            logger.info(f"'{self.name}' wird um {healed_amount} HP geheilt. HP: {self.current_hp}/{self.max_hp}")
        else:
             logger.debug(f"'{self.name}' ist bereits bei vollen HP.")


    def is_alive(self) -> bool:
        """Gibt zurück, ob die Instanz noch am Leben ist."""
        return self.is_alive_flag

    def __repr__(self) -> str:
        status = "Alive" if self.is_alive() else "Defeated"
        return f"<CharacterInstance(name='{self.name}', HP={self.current_hp}/{self.max_hp}, Status={status})>"


# --- Testblock ---
if __name__ == '__main__':
    # Benötigt funktionierendes Logging und Config für den Loader
    try:
        # Versuche, das Logging zu initialisieren, falls nicht schon geschehen
        from src.utils.logging_setup import setup_logging
        setup_logging()
    except ImportError:
        print("WARNUNG: Logging konnte nicht initialisiert werden (für Test).")


    print("\n--- CharacterInstance Test ---")

    # Lade Definitionen (angenommen, loader funktioniert)
    try:
        krieger_def = loader.get_character_class("krieger")
        goblin_def = loader.get_opponent("goblin_lv1")

        if not krieger_def or not goblin_def:
             print("FEHLER: Konnte Definitionen nicht laden. Stelle sicher, dass loader.py funktioniert.")
        else:
             print(f"\nErstelle Instanz für: {krieger_def}")
             krieger_instance = CharacterInstance(krieger_def)
             print(f"  -> {krieger_instance}")
             print(f"  -> STR Bonus: {krieger_instance.get_attribute_bonus('STR')}")


             print(f"\nErstelle Instanz für: {goblin_def}")
             goblin_instance = CharacterInstance(goblin_def)
             print(f"  -> {goblin_instance}")
             print(f"  -> DEX Bonus: {goblin_instance.get_attribute_bonus('DEX')}")


             print("\nSimuliere Schaden:")
             damage_to_goblin = 30
             print(f"Goblin erleidet {damage_to_goblin} Schaden...")
             goblin_instance.take_damage(damage_to_goblin)
             print(f"  -> Status Goblin: {goblin_instance}")

             print("\nSimuliere Heilung:")
             heal_to_goblin = 15
             print(f"Goblin wird um {heal_to_goblin} HP geheilt...")
             goblin_instance.heal(heal_to_goblin)
             print(f"  -> Status Goblin: {goblin_instance}")

             print("\nSimuliere tödlichen Schaden:")
             fatal_damage = 1000
             print(f"Goblin erleidet {fatal_damage} Schaden...")
             goblin_instance.take_damage(fatal_damage)
             print(f"  -> Status Goblin: {goblin_instance}")
             print(f"  -> Ist Goblin noch am Leben? {goblin_instance.is_alive()}")

             print("\nVersuche, besiegten Goblin zu heilen:")
             goblin_instance.heal(50)
             print(f"  -> Status Goblin: {goblin_instance}")


    except Exception as e:
        logger.error(f"Fehler im CharacterInstance Testblock: {e}", exc_info=True)
        print(f"FEHLER im Test: {e}")
