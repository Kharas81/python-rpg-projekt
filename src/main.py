# src/main.py

import logging
from pathlib import Path
import sys # Wird genutzt, um das Programm bei kritischen Fehlern zu beenden

# Importiere Logging-Setup und Loader-Funktionen
# Annahme: Dieses Skript wird vom Projekt-Root ausgeführt oder src ist im PYTHONPATH
try:
    from src.utils.logging_setup import setup_logging
    from src.definitions.loaders import (
        load_stats_definitions_from_json,
        load_character_classes_from_json,
        load_skills_from_json
    )
    # Importiere Definitionstypen und die Character-Klasse
    from src.definitions.base_definitions import DefinitionsDatabase, ClassDatabase, SkillDatabase
    from src.game_logic.character import Character
except ImportError as e:
     # Hilfreiche Fehlermeldung, falls das Skript nicht korrekt ausgeführt wird
     print(f"Import-Fehler: {e}. Stelle sicher, dass du das Skript vom Projekt-Root-Verzeichnis ausführst (z.B. 'python src/main.py') oder dass 'src' im PYTHONPATH ist.", file=sys.stderr)
     sys.exit(1)


# Hole einen Logger für dieses Hauptmodul
# Logging muss zuerst konfiguriert werden, bevor dies effektiv genutzt wird
logger = logging.getLogger(__name__) # Logger für __main__ holen

def main():
    """Hauptfunktion und Einstiegspunkt des Spiels."""
    # 1. Logging konfigurieren (Allererster Schritt!)
    # Das Level kann hier oder in logging_setup.py angepasst werden (z.B. logging.DEBUG für mehr Details)
    setup_logging(log_level=logging.INFO)

    logger.info("=========================")
    logger.info("=== RPG Spiel gestartet ===")
    logger.info("=========================")

    # 2. Pfade zu den Definitionsdateien bestimmen
    try:
        # Finde das Projekt-Root-Verzeichnis relativ zu dieser Datei
        # Path(__file__) -> /.../src/main.py
        # .parent -> /.../src/
        # .parent -> /.../ (Projekt-Root)
        project_root = Path(__file__).resolve().parent.parent
        definitions_base_path = project_root / "src" / "definitions"
        json_data_path = definitions_base_path / "json_data"
        classes_file_path = json_data_path / "character_classes.json"
        skills_file_path = json_data_path / "skills.json"

        logger.info(f"Projekt-Root angenommen als: {project_root.absolute()}")
        logger.info(f"Lade Definitionen aus: {json_data_path.absolute()}")

        # Prüfen, ob das Definitionsverzeichnis existiert
        if not json_data_path.is_dir():
             logger.critical(f"Kritischer Fehler: Definitionsverzeichnis nicht gefunden unter '{json_data_path}'")
             print(f"FEHLER: Definitionsverzeichnis nicht gefunden: {json_data_path}", file=sys.stderr)
             sys.exit(1) # Programm beenden

    except Exception as e:
         logger.exception(f"Kritischer Fehler beim Bestimmen der Pfade: {e}")
         print(f"FEHLER: Konnte Pfade nicht korrekt bestimmen: {e}", file=sys.stderr)
         sys.exit(1)

    # 3. Definitionen laden
    stats_db: Optional[DefinitionsDatabase] = None
    class_db: Optional[ClassDatabase] = None
    skill_db: Optional[SkillDatabase] = None
    load_success = True

    try:
        logger.info("Lade Stats/Attributes/Resources/Flags...")
        stats_db = load_stats_definitions_from_json(json_data_path)
        logger.info(f"-> {len(stats_db)} Stat-Definitionen geladen.")

        logger.info("Lade Charakterklassen...")
        class_db = load_character_classes_from_json(classes_file_path)
        logger.info(f"-> {len(class_db)} Klassen-Definitionen geladen.")

        logger.info("Lade Skills...")
        skill_db = load_skills_from_json(skills_file_path)
        logger.info(f"-> {len(skill_db)} Skill-Definitionen geladen.")

    except FileNotFoundError as e:
         logger.critical(f"Kritischer Ladefehler: Definitionsdatei nicht gefunden: {e}")
         print(f"FEHLER: Eine benötigte Definitionsdatei wurde nicht gefunden. Details im Log oder Konsole.", file=sys.stderr)
         load_success = False
    except (KeyError, TypeError, Exception) as e:
        # Logge den vollen Traceback für unerwartete Fehler beim Laden/Parsen
        logger.critical(f"Kritischer Ladefehler beim Verarbeiten der Definitionen: {e}", exc_info=True)
        print(f"FEHLER: Problem beim Laden der Definitionen. Details im Log oder Konsole.", file=sys.stderr)
        load_success = False

    # 4. Spiel-Logik starten (nur wenn Laden erfolgreich war)
    if load_success and stats_db is not None and class_db is not None and skill_db is not None:
        logger.info("Definitionen erfolgreich geladen. Initialisiere Spiel...")

        # 5. Beispiel-Charakter erstellen
        try:
            # Wähle eine Klasse zum Testen (z.B. Krieger)
            player_class_id = "WARRIOR"
            player_class_def = class_db.get(player_class_id)

            if not player_class_def:
                 logger.error(f"Spielerklasse '{player_class_id}' nicht in Klassendatenbank gefunden!")
                 print(f"FEHLER: Gewählte Spielerklasse '{player_class_id}' ist nicht definiert.", file=sys.stderr)
                 sys.exit(1)

            # Erstelle den Charakter-Instanz
            player_character = Character(name="Held", class_definition=player_class_def, skill_db=skill_db)
            logger.info(f"Beispiel-Charakter '{player_character.name}' erstellt.")

            # 6. Test-Ausgabe und Aktionen
            print("\n" + "="*30)
            print(" Charakterinformationen:")
            print("="*30)
            # Die __str__ Methode der Character-Klasse wird hier genutzt
            print(player_character)

            print("\n" + "="*30)
            print(" Testaktionen:")
            print("="*30)

            # Beispiel: Schaden nehmen
            damage_amount = 25
            damage_type = "PHYSICAL"
            logger.info(f"Simuliere {damage_amount} {damage_type} Schaden für '{player_character.name}'...")
            print(f"\n> Aktion: {player_character.name} erleidet {damage_amount} {damage_type} Schaden...")
            player_character.take_damage(damage_amount, damage_type)
            # print(f"  Aktuelle HP: {player_character.current_resources.get('HP', 'N/A')}") # Wird schon von take_damage geloggt/geprinted

            # Beispiel: Ressource verbrauchen für einen Skill
            skill_to_use_id = "power_strike" # Ein Skill des Kriegers
            skill_to_use = player_character.known_skills.get(skill_to_use_id)

            if skill_to_use and skill_to_use.cost:
                 # Nimm den ersten (und oft einzigen) Eintrag im Kosten-Dict
                 resource_id, cost_amount = next(iter(skill_to_use.cost.items()))
                 logger.info(f"Simuliere Ressourcenverbrauch für Skill '{skill_to_use.name}': {cost_amount} {resource_id}...")
                 print(f"\n> Aktion: Versuche '{skill_to_use.name}' zu nutzen (Kosten: {cost_amount} {resource_id})...")
                 success = player_character.consume_resource(resource_id, cost_amount)
                 print(f"  -> {'Erfolgreich' if success else 'Fehlgeschlagen (nicht genug Ressource?)'}")
                 # print(f"  Aktuelle {resource_id}: {player_character.current_resources.get(resource_id, 'N/A')}") # Wird schon geloggt

            elif skill_to_use:
                 logger.info(f"Test-Skill '{skill_to_use.name}' hat keine Kosten.")
                 print(f"\n> Info: '{skill_to_use.name}' hat keine Ressourcenkosten.")
            else:
                 logger.warning(f"Test-Skill '{skill_to_use_id}' nicht beim Charakter '{player_character.name}' gefunden.")
                 print(f"\n> Info: Test-Skill '{skill_to_use_id}' nicht beim Charakter gefunden.")

            print("\n" + "="*30)
            logger.info("Initiale Test-Sequenz in main.py abgeschlossen.")
            # TODO: Hier würde später die eigentliche Spiel-Schleife beginnen
            # (z.B. Warten auf Spieler-Input in einer CLI)

        except Exception as e:
             # Fange alle unerwarteten Fehler während der Spiel-Initialisierung ab
             logger.exception(f"Unerwarteter Fehler nach dem Laden der Definitionen: {e}")
             print(f"FEHLER: Ein unerwarteter Laufzeitfehler ist aufgetreten. Details im Log.", file=sys.stderr)
             sys.exit(1)

    else:
        # Fall, falls das Laden der Definitionen fehlgeschlagen ist
        logger.error("Spielstart abgebrochen aufgrund von Fehlern beim Laden der Definitionen.")
        # Die detaillierte Fehlermeldung wurde schon vorher ausgegeben.
        print("FEHLER: Spiel konnte nicht gestartet werden (Definitionen fehlen).", file=sys.stderr)
        sys.exit(1) # Beende mit Fehlercode

    logger.info("======================")
    logger.info("=== RPG Spiel beendet ===")
    logger.info("======================")


if __name__ == "__main__":
    # Dieser Block wird ausgeführt, wenn das Skript direkt gestartet wird
    # (z.B. über "python src/main.py" im Terminal vom Projekt-Root aus)
    main()