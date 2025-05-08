"""
Haupteinstiegspunkt

Parst Argumente und startet die Anwendung im gewünschten Modus.
"""
import os
import sys
import argparse
import logging
from typing import Dict, Any, List, Optional

# Projektpfad zum PYTHONPATH hinzufügen, um Imports aus src zu ermöglichen
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_path)

from src.config.config import get_config  # Geändert von load_config
from src.utils.logging_setup import setup_logging, get_logger
# Importiere die Funktionen aus der neuen character_utils.py
from src.definitions.character_utils import get_character_template, get_opponent_template
from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter
from src.ui.cli_main_loop import run_auto_simulation

# Module für den Trainingsmodus
try:
    from src.ai.rl_training import CurriculumTrainer
except ImportError:
    pass  # Ignorieren, falls nicht verfügbar

# Module für den Evaluierungsmodus
try:
    from src.ai.evaluate_agent import AgentEvaluator
except ImportError:
    pass  # Ignorieren, falls nicht verfügbar

# Logger für dieses Modul
logger = get_logger(__name__)


def parse_args():
    """
    Parst Kommandozeilenargumente.
    
    Returns:
        argparse.Namespace: Die geparsten Argumente
    """
    parser = argparse.ArgumentParser(description="RPG-System mit Reinforcement Learning")
    
    # Haupt-Betriebsmodus
    parser.add_argument(
        "--mode",
        type=str,
        choices=["manual", "auto", "train", "evaluate"],
        default="auto",
        help="Betriebsmodus: manual (Benutzereingabe), auto (automatische Simulation), "
             "train (RL-Training), evaluate (RL-Evaluierung)"
    )
    
    # Parameter für den Auto-Modus
    parser.add_argument(
        "--players",
        type=int,
        default=2,
        help="Anzahl der Spielercharaktere im Auto-Modus"
    )
    parser.add_argument(
        "--encounters",
        type=int,
        default=5,
        help="Anzahl der Kampfbegegnungen im Auto-Modus"
    )
    
    # Logging-Level
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging-Level"
    )
    
    # Config-Pfad
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Pfad zur Konfigurationsdatei (für RL-Modi)"
    )
    
    # Zusätzliche Parameter für RL-Modi
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Pfad zum Modell (für Evaluierungsmodus)"
    )
    
    parser.add_argument(
        "--level",
        type=int,
        default=1,
        help="Curriculum-Level für Training/Evaluierung"
    )
    
    return parser.parse_args()


def main():
    """
    Hauptfunktion, die die Anwendung startet.
    """
    # Kommandozeilenargumente parsen
    args = parse_args()
    
    # Logging-Setup
    setup_logging(level=getattr(logging, args.log_level))
    
    # Konfiguration laden
    config = get_config()  # Geändert von load_config
    
    logger.info(f"Starte im Modus: {args.mode}")
    
    try:
        if args.mode == "manual":
            logger.info("Manueller Modus noch nicht implementiert")
            # TODO: Implementierung des manuellen Modus
            
        elif args.mode == "auto":
            # Automatische Simulation starten
            run_auto_simulation(
                num_players=args.players,
                num_encounters=args.encounters
            )
            
        elif args.mode == "train":
            # RL-Training starten
            logger.info("Starte RL-Training")
            try:
                trainer = CurriculumTrainer(args.config)
                trainer.train_curriculum()
            except NameError:
                logger.error("RL-Module nicht verfügbar. Stelle sicher, dass alle erforderlichen Pakete installiert sind.")
            
        elif args.mode == "evaluate":
            # RL-Evaluierung starten
            logger.info("Starte RL-Evaluierung")
            if args.model is None:
                logger.error("Kein Modellpfad angegeben. Verwende --model PFAD")
                return
            
            try:
                evaluator = AgentEvaluator(args.config)
                results = evaluator.evaluate_agent(args.model, args.level)
                if results['success']:
                    evaluator.save_results(results)
            except NameError:
                logger.error("RL-Module nicht verfügbar. Stelle sicher, dass alle erforderlichen Pakete installiert sind.")
            
    except KeyboardInterrupt:
        logger.info("Programm durch Benutzer beendet")
    except Exception as e:
        logger.error(f"Fehler im Hauptprogramm: {e}", exc_info=True)
    
    logger.info("Programm beendet")


if __name__ == "__main__":
    main()
