import argparse
import logging
import sys
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu,
# um sicherzustellen, dass 'src' gefunden wird, egal wie das Skript ausgeführt wird.
# Dies ist oft nützlich, besonders wenn man aus Unterverzeichnissen testet oder IDEs verwendet.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Importiere unsere eigenen Module NACHDEM der Pfad angepasst wurde
try:
    from src.utils.logging_setup import setup_logging
    from src.config import config
    # Importiere Definitionen etc. erst bei Bedarf in den jeweiligen Modi
    # from src.definitions import loader
except ModuleNotFoundError as e:
    print(f"FEHLER: Notwendige Module konnten nicht importiert werden: {e}", file=sys.stderr)
    print("Stelle sicher, dass das Skript aus dem Projekt-Root ausgeführt wird oder der PYTHONPATH korrekt gesetzt ist.", file=sys.stderr)
    sys.exit(1) # Beende das Programm bei Importfehlern


def main():
    """Hauptfunktion der Anwendung."""

    # 1. Logging so früh wie möglich initialisieren
    # setup_logging() liest die Konfiguration über das config-Modul
    setup_logging()
    logger = logging.getLogger(__name__) # Logger für dieses Modul holen
    logger.info("Anwendung gestartet.")

    # 2. Kommandozeilen-Argumente parsen
    parser = argparse.ArgumentParser(description="Textbasiertes RPG mit optionaler AI-Integration.")

    # Mögliche Modi definieren
    modes = ["manual", "auto", "train", "evaluate"]
    default_mode = config.get_setting("game_settings.default_mode", "auto") # Hole Default aus Config oder nimm "auto"

    parser.add_argument(
        "--mode",
        type=str,
        choices=modes,
        default=default_mode,
        help=f"Der Betriebsmodus der Anwendung. Verfügbar: {', '.join(modes)}. Standard: {default_mode}"
    )
    # Hier könnten weitere Argumente hinzugefügt werden, z.B.:
    # parser.add_argument("--character", type=str, default="krieger", help="Spielercharakter-Klasse")
    # parser.add_argument("--level", type=int, default=1, help="Startlevel")

    args = parser.parse_args()

    logger.info(f"Betriebsmodus ausgewählt: {args.mode}")

    # 3. Logik basierend auf dem Modus ausführen (Platzhalter)
    try:
        if args.mode == "manual":
            logger.info("Starte manuellen Spielmodus...")
            # TODO: Manuelle Spielschleife hier aufrufen (z.B. aus src.ui)
            print("\nMANUAL MODE - Platzhalter - Drücke Strg+C zum Beenden")
            # Beispiel: import time; time.sleep(3600) # Warte, um etwas anzuzeigen
            pass # Nur Platzhalter

        elif args.mode == "auto":
            logger.info("Starte automatischen Simulationsmodus...")
            # TODO: Automatische Simulationsschleife hier aufrufen (z.B. aus src.ui.cli_main_loop)
            print("\nAUTO MODE - Platzhalter - Simulation würde jetzt laufen.")
            # Beispiel:
            # from src.ui.cli_main_loop import run_simulation
            # run_simulation()
            pass # Nur Platzhalter

        elif args.mode == "train":
            logger.info("Starte RL-Trainingsmodus...")
            # TODO: RL-Training hier aufrufen (z.B. aus src.ai.rl_training)
            print("\nTRAIN MODE - Platzhalter - Training würde jetzt gestartet.")
            # Beispiel:
            # from src.ai.rl_training import train_agent
            # train_agent()
            pass # Nur Platzhalter

        elif args.mode == "evaluate":
            logger.info("Starte RL-Evaluierungsmodus...")
            # TODO: RL-Evaluierung hier aufrufen (z.B. aus src.ai.evaluate_agent)
            print("\nEVALUATE MODE - Platzhalter - Evaluierung würde jetzt gestartet.")
            # Beispiel:
            # from src.ai.evaluate_agent import evaluate_agent
            # evaluate_agent()
            pass # Nur Platzhalter

        else:
            # Sollte durch argparse 'choices' eigentlich nicht erreichbar sein
            logger.error(f"Unbekannter Modus: {args.mode}")
            print(f"FEHLER: Unbekannter Modus '{args.mode}'.", file=sys.stderr)
            sys.exit(1)

        logger.info(f"Modus '{args.mode}' erfolgreich (als Platzhalter) ausgeführt.")

    except Exception as e:
        # Fange alle unerwarteten Fehler auf oberster Ebene ab und logge sie
        logger.critical(f"Ein unerwarteter Fehler ist im Modus '{args.mode}' aufgetreten!", exc_info=True)
        print(f"\nFATALER FEHLER: {e}. Siehe Logdatei für Details.", file=sys.stderr)
        sys.exit(1) # Beende mit Fehlercode

    logger.info("Anwendung normal beendet.")


if __name__ == "__main__":
    # Dieser Block wird ausgeführt, wenn das Skript direkt gestartet wird (z.B. python src/main.py)
    main()

