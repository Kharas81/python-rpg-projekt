import typing
import logging

# Importiere die Basis-Definition und den Loader
try:
    from src.definitions.character import Character as CharacterDefinition
    from src.definitions import loader
    from src.game_logic.formulas import calculate_max_hp, calculate_attribute_bonus
    # Wir werden leveling.py später importieren, um Zirkelbezüge beim ersten Laden zu vermeiden.
    # from src.game_logic import leveling # Import erst in Methoden, die es brauchen
    from src.config import config # Für XP-Formel-Konstanten
except ModuleNotFoundError:
    print("WARNUNG: entities.py - Module nicht direkt geladen, versuche relativen Import (nur für Test)")
    from ..definitions.character import Character as CharacterDefinition
    from ..definitions import loader
    from .formulas import calculate_max_hp, calculate_attribute_bonus
    from ..config import config


logger = logging.getLogger(__name__)

class CharacterInstance:
    """
    Repräsentiere eine konkrete Instanz eines Charakters oder Gegners im Spiel
    mit dynamischem Zustand (HP, Mana, Effekte, XP etc.).
    """
    def __init__(self, definition: CharacterDefinition):
        self.definition: CharacterDefinition = definition
        self.name: str = definition.name
        self.level: int = definition.level # Startlevel aus Definition

        self.attributes: typing.Dict[str, int] = definition.attributes.copy()

        base_hp = self.definition.get_combat_value('base_hp')
        con = self.get_attribute('CON')
        self.max_hp: int = calculate_max_hp(base_hp, con)
        self.current_hp: int = self.max_hp

        self.max_mana: int = self.definition.get_combat_value('base_mana')
        self.current_mana: int = self.max_mana
        self.max_stamina: int = self.definition.get_combat_value('base_stamina')
        self.current_stamina: int = self.max_stamina
        self.max_energy: int = self.definition.get_combat_value('base_energy')
        self.current_energy: int = self.max_energy

        self.armor: int = self.definition.get_combat_value('armor')
        self.magic_resist: int = self.definition.get_combat_value('magic_resist')
        self.status_effects: typing.List[typing.Any] = []
        self.is_alive_flag: bool = True

        # XP und Leveling - Initialisierung
        self.current_xp: int = 0
        # xp_to_next_level wird initial über eine (noch zu erstellende) Funktion aus leveling.py gesetzt
        # Für den Moment setzen wir es basierend auf einer Funktion, die wir in leveling.py definieren
        # Dies erfordert, dass leveling.py existiert, wenn eine Instanz erstellt wird.
        # Wir rufen eine Hilfsmethode auf, die den Import von leveling dynamisch handhabt.
        self.xp_to_next_level: int = self._calculate_xp_for_level(self.level)


        logger.debug(f"Charakter-Instanz '{self.name}' (Lvl {self.level}) erstellt: "
                     f"HP={self.current_hp}/{self.max_hp}, XP={self.current_xp}/{self.xp_to_next_level}, "
                     f"Mana={self.current_mana}/{self.max_mana}, Stamina={self.current_stamina}/{self.max_stamina}, "
                     f"Energy={self.current_energy}/{self.max_energy}")

    def _calculate_xp_for_level(self, level_to_calculate_for: int) -> int:
        """Hilfsfunktion, um XP für das nächste Level zu holen. Importiert leveling dynamisch."""
        try:
            from src.game_logic import leveling # Import hier, um Zirkelbezug bei Modul-Load zu vermeiden
            return leveling.calculate_xp_for_level(level_to_calculate_for)
        except ImportError:
            logger.error("Modul 'leveling' konnte nicht für _calculate_xp_for_level importiert werden.")
            # Fallback, falls leveling.py noch nicht existiert oder ein Problem hat
            # Dies ist ein sehr einfacher Fallback und sollte im Normalbetrieb nicht erreicht werden.
            return 100 * level_to_calculate_for # Simpler Fallback


    def get_attribute(self, attr_name: str, base_value: bool = False) -> int:
        base_val = self.attributes.get(attr_name.upper(), 0)
        if base_value: return base_val
        modified_val = base_val
        return modified_val

    def get_attribute_bonus(self, attr_name: str) -> int:
        return calculate_attribute_bonus(self.get_attribute(attr_name))

    def get_current_resource(self, resource_type: str) -> int:
        res_type = resource_type.upper()
        if res_type == "MANA": return self.current_mana
        if res_type == "STAMINA": return self.current_stamina
        if res_type == "ENERGY": return self.current_energy
        if res_type == "NONE" or res_type == "": return 9999
        logger.warning(f"Unbekannter Ressourcentyp '{resource_type}' für '{self.name}'.")
        return 0

    def can_afford_cost(self, resource_type: str, amount: int) -> bool:
        if amount == 0 or resource_type.upper() == "NONE": return True
        return self.get_current_resource(resource_type) >= amount

    def pay_cost(self, resource_type: str, amount: int) -> bool:
        if not self.can_afford_cost(resource_type, amount):
            logger.warning(f"'{self.name}' kann Kosten von {amount} {resource_type} nicht bezahlen.")
            return False
        if amount == 0 or resource_type.upper() == "NONE": return True
        res_type = resource_type.upper()
        paid = False
        if res_type == "MANA": self.current_mana -= amount; paid = True
        elif res_type == "STAMINA": self.current_stamina -= amount; paid = True
        elif res_type == "ENERGY": self.current_energy -= amount; paid = True
        if paid: logger.info(f"'{self.name}' bezahlt {amount} {resource_type}. Neuer Stand: {self.get_current_resource(resource_type)}")
        return paid

    def take_damage(self, amount: int):
        if amount <= 0 or not self.is_alive_flag: return
        self.current_hp -= amount
        logger.info(f"'{self.name}' erleidet {amount} Schaden. HP: {self.current_hp}/{self.max_hp}")
        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_alive_flag = False
            logger.info(f"'{self.name}' wurde besiegt!")

    def heal(self, amount: int):
        if amount <= 0 or not self.is_alive_flag: return
        healed_amount = min(amount, self.max_hp - self.current_hp)
        if healed_amount > 0:
            self.current_hp += healed_amount
            logger.info(f"'{self.name}' wird um {healed_amount} HP geheilt. HP: {self.current_hp}/{self.max_hp}")

    def is_alive(self) -> bool:
        return self.is_alive_flag

    def gain_xp(self, amount: int):
        """Erhöht die XP des Charakters und prüft auf Level-Up."""
        if amount <= 0 or not self.is_alive(): # Nur lebende Charaktere bekommen XP
            return

        self.current_xp += amount
        logger.info(f"'{self.name}' erhält {amount} XP. Aktuelle XP: {self.current_xp}/{self.xp_to_next_level}")

        # Prüfe auf Level-Up (kann mehrmals hintereinander passieren)
        # Wir importieren leveling hier, um Zirkelbezüge zu vermeiden, falls leveling.py CharacterInstance importieren würde.
        try:
            from src.game_logic import leveling
            while self.is_alive() and self.current_xp >= self.xp_to_next_level:
                logger.info(f"LEVEL UP VORBEREITUNG für '{self.name}'! XP: {self.current_xp}/{self.xp_to_next_level}, Level: {self.level}")
                leveling.handle_level_up(self) # Ruft die Funktion im leveling-Modul auf
                # xp_to_next_level wird innerhalb von handle_level_up (indirekt über _calculate_xp_for_level) neu gesetzt
                logger.info(f"LEVEL UP für '{self.name}'! Neues Level: {self.level}. XP: {self.current_xp}/{self.xp_to_next_level}")
        except ImportError:
            logger.error("Modul 'leveling' konnte nicht für gain_xp (Level-Up) importiert werden.")
        except Exception as e: # Fange unerwartete Fehler beim Level-Up ab
            logger.error(f"Fehler während des Level-Up Prozesses für '{self.name}': {e}", exc_info=True)


    def __repr__(self) -> str:
        status = "Alive" if self.is_alive() else "Defeated"
        return (f"<CharacterInstance(name='{self.name}', Lvl={self.level}, XP={self.current_xp}/{self.xp_to_next_level}, "
                f"HP={self.current_hp}/{self.max_hp}, Mana={self.current_mana}/{self.max_mana}, "
                f"Stamina={self.current_stamina}/{self.max_stamina}, Energy={self.current_energy}/{self.max_energy}, Status={status})>")

# --- Testblock ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging
        setup_logging()
    except ImportError: print("WARNUNG: Logging konnte nicht initialisiert werden (für Test in entities.py).")

    # Erstelle eine Dummy leveling.py, falls sie noch nicht existiert, nur für diesen Test
    # Damit der _calculate_xp_for_level und gain_xp Test nicht fehlschlägt
    import sys
    from pathlib import Path
    project_root_for_test = Path(__file__).parent.parent.parent
    if str(project_root_for_test) not in sys.path:
        sys.path.insert(0, str(project_root_for_test))

    leveling_py_path = project_root_for_test / "src" / "game_logic" / "leveling.py"
    if not leveling_py_path.exists():
        print(f"INFO: Erstelle temporäre Dummy-Datei {leveling_py_path} für den Test von entities.py.")
        temp_leveling_content = """
import logging
logger = logging.getLogger(__name__)
try:
    from src.config import config
except: # Fallback, wenn Config nicht geladen werden kann
    class DummyConfig:
        def get_setting(self, key, default=None):
            if key == "game_settings.xp_level_base": return 100
            if key == "game_settings.xp_level_factor": return 1.5
            return default
    config = DummyConfig()

def calculate_xp_for_level(level_to_calculate_for: int) -> int:
    base_xp = config.get_setting("game_settings.xp_level_base", 100)
    factor = config.get_setting("game_settings.xp_level_factor", 1.5)
    # XP um Level (level_to_calculate_for + 1) zu erreichen, von Level level_to_calculate_for
    if level_to_calculate_for <= 0: return base_xp # Sollte nicht passieren
    # XP_needed = Base * (Factor ^ (CurrentLevel - 1))
    xp_needed = int(base_xp * (factor ** (level_to_calculate_for - 1)))
    logger.debug(f"XP benötigt für Lvl {level_to_calculate_for} -> {level_to_calculate_for+1}: {xp_needed}")
    return max(1, xp_needed) # Mindestens 1 XP

def handle_level_up(character_instance): # Akzeptiert CharacterInstance
    character_instance.current_xp -= character_instance.xp_to_next_level
    character_instance.level += 1
    # Hier würden Attribute etc. erhöht. MaxHP könnte neu berechnet werden.
    character_instance.current_hp = character_instance.max_hp # Voll heilen bei Level-Up (Beispiel)
    character_instance.xp_to_next_level = calculate_xp_for_level(character_instance.level)
    logger.info(f"DUMMY LEVEL UP: {character_instance.name} ist jetzt Level {character_instance.level}! Benötigt {character_instance.xp_to_next_level} XP für nächstes Level.")
"""
        with open(leveling_py_path, "w") as f:
            f.write(temp_leveling_content)


    print("\n--- CharacterInstance Test (inkl. XP) ---")
    try:
        krieger_def = loader.get_character_class("krieger")
        if not krieger_def:
             print("FEHLER: Krieger-Definition konnte nicht laden.")
        else:
             krieger_inst = CharacterInstance(krieger_def) # Lvl 1, XP 0/100 (aus Dummy-leveling.py)
             print(f"Initial: {krieger_inst}")
             assert krieger_inst.current_xp == 0
             assert krieger_inst.level == 1
             # Erwartete XP für Level 2 (aus Dummy): 100 * (1.5^(1-1)) = 100
             assert krieger_inst.xp_to_next_level == 100, f"Erwartet 100 XP, bekommen {krieger_inst.xp_to_next_level}"


             print("\nXP-Gewinn (kein Level-Up):")
             krieger_inst.gain_xp(50) # XP: 50/100
             assert krieger_inst.current_xp == 50
             assert krieger_inst.level == 1
             print(f"Nach 50 XP: {krieger_inst}")

             print("\nXP-Gewinn (Level-Up):")
             krieger_inst.gain_xp(70) # Total XP: 120. Level-Up! 120 - 100 = 20 Rest-XP.
                                      # Neues Level 2. XP für Lvl 3: 100 * 1.5 = 150
             assert krieger_inst.level == 2, f"Erwartet Level 2, ist {krieger_inst.level}"
             assert krieger_inst.current_xp == 20, f"Erwartet 20 Rest-XP, ist {krieger_inst.current_xp}"
             assert krieger_inst.xp_to_next_level == 150, f"Erwartet 150 XP für Lvl 3, ist {krieger_inst.xp_to_next_level}"
             print(f"Nach Level-Up (total 120 XP): {krieger_inst}")

             print("\nXP-Gewinn (mehrere Level-Ups, falls möglich):")
             # Krieger ist Lvl 2, XP 20/150. Gib ihm genug XP für mehrere Level.
             # Um Lvl 3 zu erreichen: 150 - 20 = 130 XP
             # Um Lvl 4 zu erreichen (von Lvl 3): 100 * 1.5^2 = 225 XP
             # Total für Lvl 3 und 4: 130 + 225 = 355 XP
             krieger_inst.gain_xp(400) # Sollte Lvl 4 erreichen
             # Lvl 2 (20/150) + 400 XP = 420 XP
             # Lvl Up 2->3: 420-150 = 270 XP übrig, Lvl 3. XP für Lvl 4 = 225
             # Lvl Up 3->4: 270-225 = 45 XP übrig, Lvl 4. XP für Lvl 5 = 100 * 1.5^3 = 337 (oder 338 wg. int)
             assert krieger_inst.level == 4, f"Erwartet Level 4, ist {krieger_inst.level}"
             assert krieger_inst.current_xp == 45, f"Erwartet 45 Rest-XP, ist {krieger_inst.current_xp}"
             # XP für Lvl 5 (von 4): 100 * (1.5^(4-1)) = 100 * 3.375 = 337
             assert krieger_inst.xp_to_next_level == 337 or krieger_inst.xp_to_next_level == 338, f"Erwartet 337/338 XP für Lvl 5, ist {krieger_inst.xp_to_next_level}"
             print(f"Nach vielen XP (+400): {krieger_inst}")


             print("\nAlle Entity-XP-Tests erfolgreich.")
    except Exception as e:
        logger.error(f"Fehler im CharacterInstance XP Testblock: {e}", exc_info=True)
        print(f"FEHLER im Test: {e}")

    # Entferne die Dummy-Datei wieder, wenn sie erstellt wurde
    if 'temp_leveling_content' in locals() and leveling_py_path.exists():
        print(f"INFO: Entferne temporäre Dummy-Datei {leveling_py_path}.")
        leveling_py_path.unlink()

