import typing
import logging
import math

# Importiere unsere eigenen Module
try:
    from src.config import config
    # Wir importieren CharacterInstance nur für Type Hinting oder als Funktionsparameter,
    # um Zirkelbezüge beim Laden zu vermeiden, falls entities.py auch leveling importiert.
    if typing.TYPE_CHECKING:
        from src.game_logic.entities import CharacterInstance
except ModuleNotFoundError:
    print("WARNUNG: leveling.py - Module nicht direkt geladen (für Test).")
    # Fallback, wenn Config nicht geladen werden kann (für isolierten Test)
    class DummyConfig:
        def get_setting(self, key, default=None):
            if key == "game_settings.xp_level_base": return 100
            if key == "game_settings.xp_level_factor": return 1.5
            return default
    config = DummyConfig()
    if typing.TYPE_CHECKING:
        # Dieser Teil ist knifflig für isolierte Tests ohne korrekten PYTHONPATH.
        # Für den Moment gehen wir davon aus, dass es für Type Checking nicht kritisch ist.
        pass


logger = logging.getLogger(__name__)

def calculate_xp_for_level(current_character_level: int) -> int:
    """
    Berechnet die XP, die benötigt werden, um von current_character_level
    zum nächsten Level aufzusteigen.

    Formel: BasisXP * (XP_Faktor ^ (current_character_level - 1))
    Dies sind die XP, die man auf dem aktuellen Level sammeln muss.

    Args:
        current_character_level: Das aktuelle Level des Charakters.

    Returns:
        Die Anzahl der XP, die für den Aufstieg zum nächsten Level benötigt werden.
    """
    base_xp = config.get_setting("game_settings.xp_level_base", 100)
    factor = config.get_setting("game_settings.xp_level_factor", 1.5)

    if current_character_level <= 0: # Sollte nicht vorkommen, aber als Absicherung
        logger.warning(f"Ungültiges Level {current_character_level} für XP-Berechnung. Gebe Basis-XP zurück.")
        return base_xp

    # XP benötigt, um von Level L nach L+1 zu kommen: BasisXP * Faktor^(L-1)
    xp_needed = math.ceil(base_xp * (factor ** (current_character_level - 1)))

    logger.debug(f"XP benötigt für Aufstieg von Lvl {current_character_level} -> {current_character_level + 1}: "
                 f"{base_xp} * ({factor} ** ({current_character_level} - 1)) = {xp_needed}")
    return max(1, int(xp_needed)) # Mindestens 1 XP, und als int zurückgeben


def handle_level_up(character: 'CharacterInstance'):
    """
    Führt einen Levelaufstieg für den gegebenen Charakter durch.
    Diese Funktion wird von CharacterInstance.gain_xp() aufgerufen.

    Args:
        character: Die CharacterInstance, die aufsteigt.
    """
    if not character.is_alive():
        logger.warning(f"Versuch, Level-Up für besiegten Charakter '{character.name}' durchzuführen.")
        return

    # Überschüssige XP werden für das nächste Level gutgeschrieben
    character.current_xp -= character.xp_to_next_level
    character.level += 1

    logger.info(f"LEVEL UP! '{character.name}' ist jetzt Level {character.level}.")

    # TODO: Hier würden Attributerhöhungen, Skill-Freischaltungen etc. implementiert.
    # Fürs Erste: Vollständige Heilung bei Level-Up
    character.current_hp = character.max_hp
    character.current_mana = character.max_mana # Auch Ressourcen auffüllen
    character.current_stamina = character.max_stamina
    character.current_energy = character.max_energy
    logger.info(f"'{character.name}' wurde bei Level-Up vollständig geheilt und Ressourcen aufgefüllt.")

    # XP für das *neue* nächste Level berechnen
    character.xp_to_next_level = calculate_xp_for_level(character.level)

    logger.info(f"'{character.name}' (Lvl {character.level}) benötigt nun {character.xp_to_next_level} XP für das nächste Level. "
                f"Aktuelle XP: {character.current_xp}")


# --- Testblock ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging
        setup_logging()
        # Für den Test von handle_level_up benötigen wir eine CharacterInstance
        # Um Zirkelbezüge bei direktem Test zu umgehen, importieren wir hier dynamisch
        # oder erstellen eine sehr einfache Dummy-Klasse nur für diesen Test.
        from src.game_logic.entities import CharacterInstance
        from src.definitions import loader
    except ImportError as e:
        print(f"WARNUNG: Setup-Module für Test nicht gefunden in leveling.py: {e}")
        # Erstelle eine sehr simple Dummy CharacterInstance, wenn der Import fehlschlägt
        class DummyCharacterInstance:
            def __init__(self, name, level, current_xp, xp_to_next_level, max_hp):
                self.name = name
                self.level = level
                self.current_xp = current_xp
                self.xp_to_next_level = xp_to_next_level
                self.max_hp = max_hp
                self.current_hp = max_hp
                self.max_mana = 10
                self.current_mana = 10
                self.max_stamina = 10
                self.current_stamina = 10
                self.max_energy = 10
                self.current_energy = 10
            def is_alive(self): return True
        CharacterInstance = DummyCharacterInstance # Überschreibe für den Test
        class DummyDefinition:
            def __init__(self, name="DummyDef", level=1):
                self.name = name
                self.level = level
        loader = None # loader wird in diesem Dummy-Szenario nicht direkt genutzt

    print("--- Leveling Logic Test ---")

    print("\nTest calculate_xp_for_level():")
    # config: base=100, factor=1.5
    # Lvl 1 -> 2: 100 * 1.5^0 = 100
    # Lvl 2 -> 3: 100 * 1.5^1 = 150
    # Lvl 3 -> 4: 100 * 1.5^2 = 225
    # Lvl 4 -> 5: 100 * 1.5^3 = 337.5 -> 338 (ceil)
    # Lvl 5 -> 6: 100 * 1.5^4 = 506.25 -> 507 (ceil)
    expected_xp = {1: 100, 2: 150, 3: 225, 4: 338, 5: 507}
    for lvl, exp_xp in expected_xp.items():
        calculated = calculate_xp_for_level(lvl)
        print(f"  XP für Lvl {lvl} -> {lvl+1}: {calculated} (Erwartet: {exp_xp})")
        assert calculated == exp_xp, f"Fehler bei XP für Lvl {lvl}: Erwartet {exp_xp}, war {calculated}"

    print("\nTest handle_level_up():")
    if CharacterInstance.__name__ == "DummyCharacterInstance": # Verwende Dummy, falls echter Import fehlschlug
        print("  (Verwende Dummy CharacterInstance für diesen Test)")
        char_def_dummy = DummyDefinition(name="TestCharDef", level=1)
        # Simuliere CharacterInstance-Attribute, die von handle_level_up erwartet werden
        test_char = CharacterInstance(name="Tester", level=1, current_xp=120, xp_to_next_level=100, max_hp=50)
    elif loader: # Versuche, eine echte Instanz zu laden
        print("  (Verwende echte CharacterInstance für diesen Test)")
        krieger_def_test = loader.get_character_class("krieger")
        if krieger_def_test:
            test_char = CharacterInstance(krieger_def_test) # Lvl 1, XP 0/100
            test_char.current_xp = 120 # Genug XP für Level Up
            test_char.xp_to_next_level = calculate_xp_for_level(1) # Sollte 100 sein
        else:
            print("FEHLER: Krieger-Definition für Test nicht geladen. Überspringe handle_level_up Test.")
            test_char = None
    else:
        test_char = None


    if test_char:
        print(f"  Charakter vor Level-Up: Lvl={test_char.level}, XP={test_char.current_xp}/{test_char.xp_to_next_level}")
        handle_level_up(test_char)
        print(f"  Charakter nach Level-Up: Lvl={test_char.level}, XP={test_char.current_xp}/{test_char.xp_to_next_level}, HP={test_char.current_hp}/{test_char.max_hp}")
        assert test_char.level == 2
        assert test_char.current_xp == 20 # 120 - 100
        assert test_char.xp_to_next_level == 150 # XP für Lvl 2 -> 3

        # Teste noch ein Level-Up
        test_char.current_xp = 160 # 10 mehr als benötigt für Lvl 3 (150)
        print(f"  Charakter vor zweitem Level-Up: Lvl={test_char.level}, XP={test_char.current_xp}/{test_char.xp_to_next_level}")
        handle_level_up(test_char)
        print(f"  Charakter nach zweitem Level-Up: Lvl={test_char.level}, XP={test_char.current_xp}/{test_char.xp_to_next_level}, HP={test_char.current_hp}/{test_char.max_hp}")
        assert test_char.level == 3
        assert test_char.current_xp == 10 # 160 - 150
        assert test_char.xp_to_next_level == 225 # XP für Lvl 3 -> 4

    print("\nAlle Leveling-Tests erfolgreich (wenn keine Assertions fehlschlugen).")

