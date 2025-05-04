"""
Main Module

Haupteinstiegspunkt für das Python RPG Projekt.
"""

import logging
import sys
import argparse
from src.ui.cli.cli_manager import CLIManager

if __name__ == "__main__":
    # Kommandozeilenargumente parsen
    parser = argparse.ArgumentParser(description='Python RPG')
    parser.add_argument('--mode', choices=['auto', 'manual'], default='auto',
                      help='Betriebsmodus: auto für KI-Training, manual für interaktiven Modus')
    args = parser.parse_args()
    
    # Konfiguriere das Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("game.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Spiel gestartet im {args.mode}-Modus")
    
    # Starte die CLI im angegebenen Modus
    cli = CLIManager()
    try:
        cli.start(mode=args.mode)
    except KeyboardInterrupt:
        print("\nSpiel durch Benutzer beendet.")
        logger.info("Spiel durch Benutzer beendet (KeyboardInterrupt)")
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler: {str(e)}")
        print(f"\nEs ist ein Fehler aufgetreten: {str(e)}")
        print("Bitte überprüfe die Logdatei für mehr Informationen.")
    
    sys.exit(0)
