"""
Main Module

Haupteinstiegspunkt für das Python RPG Projekt.
"""

import logging
import sys
from src.ui.cli.cli_manager import CLIManager

if __name__ == "__main__":
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
    logger.info("Spiel gestartet")
    
    # Starte die CLI
    cli = CLIManager()
    try:
        cli.start()
    except KeyboardInterrupt:
        print("\nSpiel durch Benutzer beendet.")
        logger.info("Spiel durch Benutzer beendet (KeyboardInterrupt)")
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler: {str(e)}")
        print(f"\nEs ist ein Fehler aufgetreten: {str(e)}")
        print("Bitte überprüfe die Logdatei für mehr Informationen.")
    
    sys.exit(0)
