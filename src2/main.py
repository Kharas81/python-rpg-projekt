"""
Haupteinstiegspunkt für das Python-RPG-Projekt

Analysiert Befehlszeilenargumente oder verwendet ein interaktives Menü
und startet das Spiel im entsprechenden Modus.
"""
import os
import sys
import argparse
import logging
from typing import Dict, Any

# Stellen sicher, dass src im Python-Pfad ist
# Dies ist eine temporäre Lösung; für größere Projekte wird die Installation als Paket empfohlen.
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
    # Das Argument ist optional, da wir ein Menü anbieten
    parser.add_argument(
        '--mode',
        type=str,
        choices=['manual', 'auto', 'train', 'evaluate'],
        help='Betriebsmodus: manual (interaktiv), auto (Simulation), train (RL-Training), evaluate (RL-Evaluierung). Wenn nicht angegeben, wird ein Menü angezeigt.'
    )

    # Simulationsparameter
    parser.add_argument(
        '--players',
        type=int,
        default=2, # Standardwert für CLI
        help='Anzahl der Spielercharaktere für den Auto-Modus (CLI)'
    )

    parser.add_argument(
        '--encounters',
        type=int,
        default=3, # Standardwert für CLI
        help='Anzahl der Begegnungen für den Auto-Modus (CLI)'
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

    # Bekannte Argumente parsen, um unbekannte (z.B. für Sub-Skripte) zu ignorieren
    # args, unknown = parser.parse_known_args() # Könnte nützlich sein, wenn Sub-Skripte eigene Argumente haben
    # Rückgabe nur der bekannten Argumente für dieses Skript
    return parser.parse_args()


# Die Modus-Funktionen akzeptieren nun das Konfigurationsobjekt
def run_manual_mode(config: Dict[str, Any]) -> None:
    """
    Startet das Spiel im manuellen (interaktiven) Modus.
    Diese Funktion ist ein Platzhalter und wird später implementiert.

    Args:
        config (Dict[str, Any]): Das geladene Konfigurationsobjekt.
    """
    logger = logging.getLogger('rpg.main')
    logger.info("Starte Spiel im manuellen Modus (interaktiv)")
    # Beispielhafte Nutzung der Konfiguration (kann später erweitert werden)
    logger.debug(f"Manuelle Modus-Einstellungen aus Konfiguration: {config.get('manual_settings', 'Nicht gefunden')}")
    logger.warning("Der manuelle Modus ist noch nicht implementiert!")


# Die Modus-Funktionen akzeptieren nun das Konfigurationsobjekt
# Korrigiert: num_players und num_encounters werden an run_simulation übergeben
def run_auto_mode(config: Dict[str, Any], num_players: int = 2, num_encounters: int = 3) -> None:
    """
    Startet das Spiel im automatischen (Simulations-) Modus.

    Args:
        config (Dict[str, Any]): Das geladene Konfigurationsobjekt.
        num_players (int): Anzahl der Spielercharaktere
        num_encounters (int): Anzahl der zu simulierenden Begegnungen
    """
    logger = logging.getLogger('rpg.main')
    logger.info(f"Starte Spiel im automatischen Modus (Simulation mit {num_players} Spielern, {num_encounters} Begegnungen)")

    try:
        # Pfade zu den JSON5-Dateien - Ideal wäre es, diese aus der Konfiguration zu laden
        # Stattdessen werden sie hier noch hartkodiert, aber die Konfiguration ist verfügbar.
        base_path = os.path.dirname(__file__)
        # TODO: Pfade aus der Konfiguration laden, z.B. config.get('data_paths', {})
        characters_path = os.path.join(base_path, "definitions", "json_data", "characters.json5")
        skills_path = os.path.join(base_path, "definitions", "json_data", "skills.json5")
        opponents_path = os.path.join(base_path, "definitions", "json_data", "opponents.json5")

        # CLI-Simulation importieren und ausführen
        # Der späte Import wird beibehalten, könnte aber auch am Anfang erfolgen.
        from src.ui.cli_main_loop import run_simulation
        # run_simulation müsste ggf. auch die Konfiguration erhalten
        # KORREKTUR: num_players und num_encounters werden nun übergeben
        run_simulation(characters_path, skills_path, opponents_path, num_players, num_encounters)

    except Exception as e:
        logger.exception(f"Fehler im automatischen Modus: {str(e)}")


# Die Modus-Funktionen akzeptieren nun das Konfigurationsobjekt
def run_train_mode(config: Dict[str, Any]) -> None:
    """
    Startet das RL-Training.
    Diese Funktion ist ein Platzhalter und wird später implementiert.

    Args:
        config (Dict[str, Any]): Das geladene Konfigurationsobjekt.
    """
    logger = logging.getLogger('rpg.main')
    logger.info("Starte RL-Training")
    # Beispielhafte Nutzung der Konfiguration (kann später erweitert werden)
    logger.debug(f"Trainings-Einstellungen aus Konfiguration: {config.get('train_settings', 'Nicht gefunden')}")
    logger.warning("Der Trainingsmodus ist noch nicht implementiert!")


# Die Modus-Funktionen akzeptieren nun das Konfigurationsobjekt
def run_evaluate_mode(config: Dict[str, Any]) -> None:
    """
    Evaluiert ein trainiertes RL-Modell.
    Diese Funktion ist ein Platzhalter und wird später implementiert.

    Args:
        config (Dict[str, Any]): Das geladene Konfigurationsobjekt.
    """
    logger = logging.getLogger('rpg.main')
    logger.info("Starte RL-Evaluierung")
    # Beispielhafte Nutzung der Konfiguration (kann später erweitert werden)
    logger.debug(f"Evaluierungs-Einstellungen aus Konfiguration: {config.get('evaluate_settings', 'Nicht gefunden')}")
    logger.warning("Der Evaluierungsmodus ist noch nicht implementiert!")


def display_menu() -> tuple[str, int, int]:
    """
    Zeigt ein interaktives Menü an und holt die Benutzerauswahl.

    Returns:
        tuple[str, int, int]: Gewählter Modus, Anzahl Spieler, Anzahl Begegnungen
    """
    print("\n--- Python RPG Menü ---")
    print("Bitte wählen Sie einen Modus:")
    print("1. Manueller Modus (Interaktiv)")
    print("2. Automatischer Modus (Simulation)")
    print("3. RL Training")
    print("4. RL Evaluierung")
    print("-----------------------")

    while True:
        choice = input("Ihre Wahl (1-4): ")
        if choice == '1':
            mode = 'manual'
            players = 0 # Nicht benötigt im manuellen Modus
            encounters = 0 # Nicht benötigt im manuellen Modus
            break
        elif choice == '2':
            mode = 'auto'
            while True:
                try:
                    players = int(input("Anzahl Spieler für Simulation (Standard 2): ") or "2")
                    if players < 1:
                        print("Bitte geben Sie eine positive Zahl ein.")
                        continue
                    break
                except ValueError:
                    print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")
            while True:
                try:
                    encounters = int(input("Anzahl Begegnungen für Simulation (Standard 3): ") or "3")
                    if encounters < 0:
                         print("Bitte geben Sie eine nicht-negative Zahl ein.")
                         continue
                    break
                except ValueError:
                    print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")
            break
        elif choice == '3':
            mode = 'train'
            players = 0 # Nicht benötigt im Trainingsmodus
            encounters = 0 # Nicht benötigt im Trainingsmodus
            break
        elif choice == '4':
            mode = 'evaluate'
            players = 0 # Nicht benötigt im Evaluierungsmodus
            encounters = 0 # Nicht benötigt im Evaluierungsmodus
            break
        else:
            print("Ungültige Auswahl. Bitte geben Sie eine Zahl zwischen 1 und 4 ein.")

    return mode, players, encounters


def main() -> None:
    """
    Hauptfunktion des Programms.
    Analysiert Argumente oder zeigt ein Menü und startet das Spiel im entsprechenden Modus.
    """
    args = parse_args()

    # Logger einrichten (frühzeitig, um auch Probleme beim Parsen/Menü zu loggen)
    logger = setup_logging('rpg')

    # Log-Level überschreiben, falls angegeben
    if args.log_level:
        try:
            logger.setLevel(getattr(logging, args.log_level.upper()))
        except AttributeError:
             logger.warning(f"Ungültiges Log-Level '{args.log_level}' übergeben. Verwende Standard-Level.")


    # Konfiguration laden
    # Die Konfiguration wird hier geladen und dann an die Modus-Funktionen übergeben
    # TODO: Pfad zur Konfigurationsdatei aus args.config nutzen, falls vorhanden
    config = get_config()

    # Bestimme den Modus und Parameter: CLI-Argumente haben Vorrang vor Menü
    if args.mode:
        # Modus wurde über CLI angegeben
        mode = args.mode
        players = args.players
        encounters = args.encounters
        logger.info(f"Modus '{mode}' über Befehlszeile gewählt.")
    else:
        # Kein Modus über CLI angegeben, Menü anzeigen
        mode, players, encounters = display_menu()
        logger.info(f"Modus '{mode}' über Menü gewählt.")
        # Aktualisiere args Namespace, falls Menü verwendet wurde (optional, aber nützlich)
        args.mode = mode
        args.players = players
        args.encounters = encounters


    # Wichtige Informationen loggen
    logger.info(f"Python RPG gestartet im Modus: {args.mode}")
    logger.info(f"Python-Version: {sys.version}")
    logger.debug(f"Konfiguration geladen: {config.get('game_settings')}") # Beispiel für Konfigurationszugriff

    # Je nach Modus die entsprechende Funktion aufrufen
    try:
        if args.mode == 'manual':
            # Konfiguration an die Funktion übergeben
            run_manual_mode(config)
        elif args.mode == 'auto':
            # Konfiguration und spezifische Argumente übergeben
            # KORREKTUR: num_players und num_encounters werden nun an run_auto_mode übergeben
            run_auto_mode(config, players, encounters)
        elif args.mode == 'train':
            # Konfiguration an die Funktion übergeben
            run_train_mode(config)
        elif args.mode == 'evaluate':
            # Konfiguration an die Funktion übergeben
            run_evaluate_mode(config)
        else:
            # Dieser Fall sollte nach der Menü-Logik nicht mehr auftreten,
            # aber als Fallback für ungültige CLI-Argumente beibehalten.
            logger.error(f"Interner Fehler: Ungültiger Modus '{args.mode}' nach Auswahl/Parsing.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Programm durch Benutzer abgebrochen")
        sys.exit(0)
    except Exception as e:
        # Generische Fehlerbehandlung - kann für spezifischere Fehler verfeinert werden
        logger.exception(f"Unerwarteter Fehler: {str(e)}")
        sys.exit(1)

    logger.info("Programm normal beendet")


if __name__ == "__main__":
    main()
