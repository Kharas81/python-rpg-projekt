# examples/01_load_and_show_definitions.py

"""
Dieses Beispielskript demonstriert, wie die Definitionsdateien (Charaktere, Skills, etc.)
und die Spieleinstellungen geladen und grundlegend inspiziert werden können.
Es berücksichtigt die benutzerdefinierten Exceptions und die neuen Datenklassen.

Ausführung vom Projekt-Root-Verzeichnis:
python examples/01_load_and_show_definitions.py
"""

import sys
from pathlib import Path
from typing import Type # Für isinstance mit Type-Objekten

# Füge das 'src'-Verzeichnis zum sys.path hinzu
EXAMPLES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXAMPLES_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Importiere die Ladefunktionen, Konfigurationen und die neuen Datenklassen/Exceptions
try:
    from definitions.loader import (
        load_game_settings,
        load_character_definitions,
        load_skill_definitions,
        load_opponent_definitions
    )
    from config.config import GAME_SETTINGS, LOGGING_SETTINGS, RL_SETTINGS
    from utils.exceptions import RPGBaseException # Basise всех наших ошибок
    # Spezifische Datenklassen für isinstance-Prüfungen
    from definitions.skill import (
        BaseEffectDefinition, DamageEffectDefinition, HealEffectDefinition, ApplyStatusEffectDefinition,
        BonusVsTypeData # Obwohl nicht direkt für isinstance, gut zu wissen
    )
    from definitions.character import CharacterDefinition
    from definitions.opponent import OpponentDefinition

except ImportError as e:
    print(f"FEHLER beim Importieren der Module. Stelle sicher, dass das Skript vom Projekt-Root ausgeführt wird "
          f"oder der PYTHONPATH korrekt gesetzt ist. Fehler: {e}")
    sys.exit(1)

def show_loaded_data():
    """Lädt alle Definitionen und Einstellungen und gibt eine Zusammenfassung aus."""
    print("--- Lade und zeige Definitionen und Einstellungen (Version mit Refactoring) ---")

    # Fehlerbehandlung für Ladevorgänge
    # noinspection PyBroadException
    try:
        # --- Spieleinstellungen ---
        # load_game_settings() wird bereits beim Import von config.config ausgeführt.
        # Wenn hier ein Fehler auftritt, würde config.py eine CriticalConfigError werfen.
        if GAME_SETTINGS: # Prüft, ob GAME_SETTINGS erfolgreich initialisiert wurde
            print("\n### Spieleinstellungen (aus config.GAME_SETTINGS):")
            for key, value in GAME_SETTINGS.items():
                print(f"  {key}: {value}")
        else:
            # Dieser Fall sollte durch CriticalConfigError im config-Modul eigentlich nicht eintreten,
            # es sei denn, die settings.json5 ist gültig, aber 'game_settings' fehlt komplett.
            print("\nWARNUNG: GAME_SETTINGS ist leer. Wurde settings.json5 korrekt geladen und enthält 'game_settings'?")
        
        if LOGGING_SETTINGS:
            print("\n### Logging-Einstellungen (aus config.LOGGING_SETTINGS):")
            for key, value in LOGGING_SETTINGS.items():
                print(f"  {key}: {value}")
        else:
            print("\nWARNUNG: LOGGING_SETTINGS ist leer.")


        # --- Charakterdefinitionen ---
        characters = load_character_definitions()
        if characters:
            print(f"\n### Charakterdefinitionen (Anzahl: {len(characters)}):")
            for char_id, char_def in characters.items():
                # char_def ist jetzt eine CharacterDefinition-Instanz
                print(f"  ID: {char_def.id}, Name: {char_def.name} ({char_def.description})")
                print(f"    STR: {char_def.primary_attributes.get('STR')}, HP-Basis: {char_def.base_combat_values.get('base_hp')}")
                print(f"    Start-Skills: {', '.join(char_def.starting_skills) if char_def.starting_skills else 'Keine'}")
        else: # Sollte nicht eintreten, da Exceptions geworfen werden
            print("\nFehler: Charakterdefinitionen konnten nicht geladen werden (sollte Exception sein).")

        # --- Skilldefinitionen ---
        skills = load_skill_definitions()
        if skills:
            print(f"\n### Skilldefinitionen (Anzahl: {len(skills)}):")
            for skill_id, skill_def in skills.items():
                # skill_def ist eine SkillDefinition-Instanz
                print(f"  ID: {skill_def.id}, Name: {skill_def.name} ({skill_def.description})")
                print(f"    Kosten: {skill_def.cost.value} {skill_def.cost.type}, Ziel: {skill_def.target_type}")
                print(f"    Effekte ({len(skill_def.effects)}):")
                for i, effect in enumerate(skill_def.effects):
                    # effect ist eine Instanz von BaseEffectDefinition oder einer ihrer Unterklassen
                    print(f"      {i+1}. Typ: {effect.type}, Chance: {effect.application_chance*100:.0f}%")
                    if isinstance(effect, DamageEffectDefinition):
                        bonus_info = ""
                        if effect.bonus_vs_type:
                            bonus_info = f" (Bonus: x{effect.bonus_vs_type.bonus_multiplier} vs {effect.bonus_vs_type.tag})"
                        pen_info = ""
                        if effect.armor_penetration_percent and effect.armor_penetration_percent > 0:
                            pen_info = f", Rüst.Ign.: {effect.armor_penetration_percent*100:.0f}%"
                        print(f"         Schaden ({effect.damage_type}): Basis {effect.base_damage or 'Waffe'}, "
                              f"Skaliert mit {effect.scaling_attribute or '-'}"
                              f"{f' x{effect.attribute_multiplier}' if effect.attribute_multiplier else ''}"
                              f"{pen_info}{bonus_info}")
                    elif isinstance(effect, HealEffectDefinition):
                        print(f"         Heilung: Basis {effect.base_heal}, "
                              f"Skaliert mit {effect.scaling_attribute or '-'}"
                              f"{f' +{effect.flat_heal_bonus_per_attribute_point}/Pkt' if effect.flat_heal_bonus_per_attribute_point else ''}")
                    elif isinstance(effect, ApplyStatusEffectDefinition):
                        print(f"         Status: '{effect.status_effect_id}', Dauer: {effect.duration_rounds} Rnd, "
                              f"Potenz: {effect.potency}")
                    else:
                        print(f"         Unbekannter spezifischer Effekttyp: {type(effect).__name__}")
        else:
            print("\nFehler: Skilldefinitionen konnten nicht geladen werden (sollte Exception sein).")

        # --- Gegnerdefinitionen ---
        opponents = load_opponent_definitions()
        if opponents:
            print(f"\n### Gegnerdefinitionen (Anzahl: {len(opponents)}):")
            for opp_id, opp_def in opponents.items():
                # opp_def ist jetzt eine OpponentDefinition-Instanz
                print(f"  ID: {opp_def.id}, Name: {opp_def.name} (Lvl: {opp_def.level}) - {opp_def.description}")
                print(f"    XP: {opp_def.xp_reward}, Tags: {', '.join(opp_def.tags) if opp_def.tags else 'Keine'}")
                print(f"    CON: {opp_def.primary_attributes.get('CON')}, Basis Mana: {opp_def.base_combat_values.get('base_mana', 0)}")
                print(f"    Skills: {', '.join(opp_def.skills) if opp_def.skills else 'Keine'}")
        else:
            print("\nFehler: Gegnerdefinitionen konnten nicht geladen werden (sollte Exception sein).")

    except RPGBaseException as e: # Fängt alle unsere benutzerdefinierten Exceptions ab
        print(f"\nFEHLER BEIM LADEN DER DEFINITIONEN ODER KONFIGURATION:")
        print(f"  Typ: {type(e).__name__}")
        print(f"  Nachricht: {e}")
        if hasattr(e, 'filepath') and e.filepath: # type: ignore
            print(f"  Datei: {e.filepath}") # type: ignore
        if hasattr(e, 'original_exception') and e.original_exception: # type: ignore
            print(f"  Ursache: {type(e.original_exception).__name__}: {e.original_exception}") # type: ignore
        print("Das Skript wird aufgrund dieses Fehlers beendet.")
        sys.exit(1) # Beende das Skript bei einem Fehler
    except Exception as e: # Fängt alle anderen, unerwarteten Python-Exceptions ab
        print(f"\nEIN UNERWARTETER ALLGEMEINER FEHLER IST AUFGETRETEN:")
        print(f"  Typ: {type(e).__name__}")
        print(f"  Nachricht: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


    print("\n--- Ende der Anzeige ---")

if __name__ == '__main__':
    show_loaded_data()
    print("\nBeispielskript erfolgreich ausgeführt (oder Fehler wurden oben angezeigt).")
    print(f"Um dieses Skript auszuführen, navigiere ins Projekt-Root-Verzeichnis und verwende:")
    print(f"python {Path('examples') / Path(__file__).name}")