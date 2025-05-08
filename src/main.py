"""
Haupteinstiegspunkt für das Python-RPG-Projekt

Analysiert Befehlszeilenargumente und startet das Spiel im entsprechenden Modus.
"""
import os
import sys
import argparse
import logging
from typing import Dict, Any

# Stellen sicher, dass src im Python-Pfad ist
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.utils.logging_setup import setup_logging
from src.config.config import get_config


def parse_args() -> argparse.Namespace:
    """
    Analysiert die Befehlszeilenargumente.
    
    Returns:
        argparse.Namespace: Die analysierten Argumente
    """
    parser = argparse.ArgumentParser(description='Python RPG mit KI-Komponenten')
    
    # Betriebsmodus
    parser.add_argument(
        '--mode', 
        type=str, 
        choices=['manual', 'auto', 'train', 'evaluate'], 
        default='auto',
        help='Betriebsmodus: manual (interaktiv), auto (Simulation), train (RL-Training), evaluate (RL-Evaluierung)'
    )
    
    # Simulationsparameter
    parser.add_argument(
        '--players',
        type=int,
        default=2,
        help='Anzahl der Spielercharaktere für den Auto-Modus'
    )
    
    parser.add_argument(
        '--encounters',
        type=int,
        default=3,
        help='Anzahl der Begegnungen für den Auto-Modus'
    )
    
    # Optional: Loglevel überschreiben
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Überschreibt das in der Konfiguration festgelegte Log-Level'
    )
    
    # Optional: Pfad zu einer alternativen Konfigurationsdatei
    parser.add_argument(
        '--config',
        type=str,
        help='Pfad zu einer alternativen settings.json5-Datei'
    )
    
    return parser.parse_args()


def run_manual_mode() -> None:
    """
    Startet das Spiel im manuellen (interaktiven) Modus.
    Diese Funktion ist ein Platzhalter und wird später implementiert.
    """
    logger = logging.getLogger('rpg.main')
    logger.info("Starte Spiel im manuellen Modus (interaktiv)")
    logger.warning("Der manuelle Modus ist noch nicht implementiert!")


def run_auto_mode(num_players: int = 2, num_encounters: int = 3) -> None:
    """
    Startet das Spiel im automatischen (Simulations-) Modus.
    
    Args:
        num_players (int): Anzahl der Spielercharaktere
        num_encounters (int): Anzahl der zu simulierenden Begegnungen
    """
    logger = logging.getLogger('rpg.main')
    logger.info(f"Starte Spiel im automatischen Modus (Simulation mit {num_players} Spielern, {num_encounters} Begegnungen)")
    
    try:
        # Pfade zu den JSON5-Dateien
        base_path = os.path.dirname(__file__)
        characters_path = os.path.join(base_path, "definitions", "json_data", "characters.json5")
        skills_path = os.path.join(base_path, "definitions", "json_data", "skills.json5")
        opponents_path = os.path.join(base_path, "definitions", "json_data", "opponents.json5")
        
        # CLI-Simulation importieren und ausführen
        from src.ui.cli_main_loop import run_simulation
        run_simulation(characters_path, skills_path, opponents_path)
        
    except Exception as e:
        logger.exception(f"Fehler im automatischen Modus: {str(e)}")


def run_train_mode() -> None:
    """
    Startet das RL-Training.
    Diese Funktion ist ein Platzhalter und wird später implementiert.
    """
    logger = logging.getLogger('rpg.main')
    logger.info("Starte RL-Training")
    logger.warning("Der Trainingsmodus ist noch nicht implementiert!")


def run_evaluate_mode() -> None:
    """
    Evaluiert ein trainiertes RL-Modell.
    Diese Funktion ist ein Platzhalter und wird später implementiert.
    """
    logger = logging.getLogger('rpg.main')
    logger.info("Starte RL-Evaluierung")
    logger.warning("Der Evaluierungsmodus ist noch nicht implementiert!")


def main() -> None:
    """
    Hauptfunktion des Programms.
    Analysiert Argumente und startet das Spiel im entsprechenden Modus.
    """
    args = parse_args()
    
    # Logger einrichten
    logger = setup_logging('rpg')
    
    # Log-Level überschreiben, falls angegeben
    if args.log_level:
        logger.setLevel(getattr(logging, args.log_level))
    
    # Konfiguration laden
    config = get_config()
    
    # Wichtige Informationen loggen
    logger.info(f"Python RPG gestartet im Modus: {args.mode}")
    logger.info(f"Python-Version: {sys.version}")
    logger.debug(f"Konfiguration geladen: {config.get('game_settings')}")
    
    # Je nach Modus die entsprechende Funktion aufrufen
    try:
        if args.mode == 'manual':
            run_manual_mode()
        elif args.mode == 'auto':
            run_auto_mode(args.players, args.encounters)
        elif args.mode == 'train':
            run_train_mode()
        elif args.mode == 'evaluate':
            run_evaluate_mode()
        else:
            logger.error(f"Ungültiger Modus: {args.mode}")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Programm durch Benutzer abgebrochen")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler: {str(e)}")
        sys.exit(1)
    
    logger.info("Programm normal beendet")


if __name__ == "__main__":
    main()
