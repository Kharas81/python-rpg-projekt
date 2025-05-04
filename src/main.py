import argparse
import sys

# Füge das Projekt-Root zum Python-Pfad hinzu, falls nötig
# (nützlich, wenn man src/main.py direkt ausführt, aber besser ist es,
# das Projekt als Paket zu behandeln oder vom Root-Verzeichnis auszuführen)
# import os
# project_root = Path(__file__).parent.parent
# sys.path.insert(0, str(project_root))

# Importiere den Loader und die Zugriffsfunktionen
try:
    from definitions import loader
    from definitions.models import SkillDefinition, ClassDefinition, EnemyDefinition
except ImportError as e:
     # Versuche relativen Import, falls als Skript ausgeführt und src nicht im PYTHONPATH
    try:
        from src.definitions import loader
        from src.definitions.models import SkillDefinition, ClassDefinition, EnemyDefinition
    except ImportError:
        print("Fehler: Konnte Definitionsmodule nicht importieren.", file=sys.stderr)
        print("Stelle sicher, dass du das Skript vom Projekt-Root-Verzeichnis ausführst", file=sys.stderr)
        print(f"(z.B. 'python src/main.py') oder dass 'src' im PYTHONPATH ist.", file=sys.stderr)
        print(f"ImportError: {e}", file=sys.stderr)
        sys.exit(1) # Beenden, da Definitionen kritisch sind


def run_manual_mode():
    """Führt die Logik für den manuellen Spielmodus aus."""
    print("\n--- Manueller Modus gestartet ---")
    # Hier kommt später die interaktive Spiel-Logik hin (z.B. CLI-Schleife)

    # Testweise auf geladene Daten zugreifen:
    print("\n--- Testweise Zugriffe auf geladene Definitionen ---")

    # Klasse abrufen und ausgeben
    cleric_class: Optional[ClassDefinition] = loader.get_class("cleric")
    if cleric_class:
        print(f"\nKlasse gefunden: {cleric_class.name} ({cleric_class.id})")
        print(f"  Beschreibung: {cleric_class.description}")
        print(f"  Start-Attribute (STR): {cleric_class.starting_attributes.STR}")
        print(f"  Primär-Ressource: {cleric_class.primary_resource}")
        print(f"  Start-Skills: {cleric_class.starting_skills}")
    else:
        print("\nKlasse 'cleric' nicht gefunden.")

    # Skill abrufen und ausgeben
    heal_skill: Optional[SkillDefinition] = loader.get_skill("heal")
    if heal_skill:
        print(f"\nSkill gefunden: {heal_skill.name} ({heal_skill.id})")
        print(f"  Kosten: {heal_skill.cost.amount} {heal_skill.cost.resource}")
        print(f"  Ziel: {heal_skill.target_type}")
        for effect in heal_skill.effects:
            print(f"  Effekt: {effect.type}")
            if effect.type == "HEAL":
                print(f"    Basis-Heilung: {effect.base_value}")
                print(f"    Skaliert mit: {effect.scaling_attribute} (Faktor: {effect.scaling_factor})")
    else:
        print("\nSkill 'heal' nicht gefunden.")

     # Gegner abrufen und ausgeben
    goblin_shaman: Optional[EnemyDefinition] = loader.get_enemy("goblin_shaman_lvl3")
    if goblin_shaman:
        print(f"\nGegner gefunden: {goblin_shaman.name} (Level {goblin_shaman.level})")
        print(f"  Tags: {goblin_shaman.tags}")
        print(f"  HP (Basis): {goblin_shaman.combat_stats.base_hp}")
        print(f"  Skills: {goblin_shaman.skills}")
        print(f"  XP: {goblin_shaman.xp_reward}")
    else:
        print("\nGegner 'goblin_shaman_lvl3' nicht gefunden.")

    print("\n--- Manueller Modus Ende (Test) ---")


def run_auto_mode():
    """Führt die Logik für den automatisierten Modus aus."""
    print("\n--- Automatischer Modus gestartet ---")
    # Hier kommt später die Logik für KI-Training, Simulationen etc. hin
    print("\n--- Automatischer Modus Ende (Test) ---")


def main():
    """Hauptfunktion: Lädt Definitionen und startet den gewählten Modus."""
    # 1. Definitionen laden
    # ---------------------
    loader.load_definitions() # Lädt alle JSONs in die globalen Variablen im loader-Modul

    # 2. Kommandozeilenargumente parsen
    # --------------------------------
    parser = argparse.ArgumentParser(description="Startet das Python RPG Projekt.")
    parser.add_argument(
        '--mode',
        type=str,
        choices=['manual', 'auto'],
        required=True, # Modus muss angegeben werden
        help="Der Betriebsmodus: 'manual' für interaktives Spiel, 'auto' für automatisierte Läufe (z.B. KI)."
    )
    args = parser.parse_args()

    # 3. Entsprechenden Modus ausführen
    # -------------------------------
    if args.mode == 'manual':
        run_manual_mode()
    elif args.mode == 'auto':
        run_auto_mode()
    else:
        # Sollte durch choices nicht passieren, aber sicher ist sicher
        print(f"Unbekannter Modus: {args.mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Dieser Block wird nur ausgeführt, wenn das Skript direkt gestartet wird
    # (z.B. mit 'python src/main.py --mode manual')
    main()
