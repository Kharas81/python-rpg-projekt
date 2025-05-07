import argparse
import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.utils.logging_setup import setup_logging
    from src.config import config
    # Importiere die UI-Funktion erst bei Bedarf
    from src.ui.cli_main_loop import run_simulation
except ModuleNotFoundError as e:
    print(f"FEHLER: Notwendige Module konnten nicht importiert werden: {e}", file=sys.stderr)
    print("Stelle sicher, dass das Skript aus dem Projekt-Root ausgeführt wird.", file=sys.stderr)
    sys.exit(1)

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Anwendung gestartet.")

    parser = argparse.ArgumentParser(description="Textbasiertes RPG mit optionaler AI-Integration.")
    modes = ["manual", "auto", "train", "evaluate"]
    default_mode = config.get_setting("game_settings.default_mode", "auto")
    parser.add_argument("--mode", type=str, choices=modes, default=default_mode,
                        help=f"Betriebsmodus. Verfügbar: {', '.join(modes)}. Standard: {default_mode}")
    args = parser.parse_args()
    logger.info(f"Betriebsmodus ausgewählt: {args.mode}")

    try:
        if args.mode == "manual":
            logger.info("Starte manuellen Spielmodus...")
            print("\nMANUAL MODE - Noch nicht implementiert.")
            pass

        elif args.mode == "auto":
            logger.info("Starte automatischen Simulationsmodus...")
            # === NEU: Rufe die Simulation auf ===
            run_simulation()
            # =====================================

        elif args.mode == "train":
            logger.info("Starte RL-Trainingsmodus...")
            print("\nTRAIN MODE - Noch nicht implementiert.")
            pass

        elif args.mode == "evaluate":
            logger.info("Starte RL-Evaluierungsmodus...")
            print("\nEVALUATE MODE - Noch nicht implementiert.")
            pass
        else:
             logger.error(f"Unbekannter Modus: {args.mode}"); sys.exit(1)

        logger.info(f"Modus '{args.mode}' erfolgreich ausgeführt.")

    except Exception as e:
        logger.critical(f"Ein unerwarteter Fehler ist im Modus '{args.mode}' aufgetreten!", exc_info=True)
        print(f"\nFATALER FEHLER: {e}. Siehe Logdatei für Details.", file=sys.stderr)
        sys.exit(1)

    logger.info("Anwendung normal beendet.")

if __name__ == "__main__":
    main()

