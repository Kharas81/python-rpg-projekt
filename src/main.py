# src/main.py
"""
Haupteinstiegspunkt für das RPG-Projekt.
Verarbeitet Kommandozeilenargumente und startet die entsprechende Logik.
"""

import argparse
import logging

# Importiere zuerst das Logging-Setup, damit es frühzeitig konfiguriert wird.
# Andere Module, die Log-Nachrichten ausgeben, profitieren dann davon.
try:
    import src.utils.logging_setup # Importiert und führt logging_setup.py aus
except ImportError:
    # Fallback, falls das Modul noch nicht existiert oder der Pfad nicht stimmt
    # Dies sollte idealerweise nicht passieren, wenn die Struktur korrekt ist.
    print("WARNUNG: src.utils.logging_setup konnte nicht importiert werden. Standard-Python-Logging wird verwendet.")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Erhalte einen Logger für dieses Modul
logger = logging.getLogger(__name__)

# Importiere die Konfiguration
try:
    from src.config.config import CONFIG
except ImportError:
    logger.critical("FATAL: Konfigurationsmodul src.config.config konnte nicht importiert werden. Abbruch.")
    # In einer realen Anwendung würde man hier möglicherweise das Programm beenden.
    # Für den Moment lassen wir es laufen, aber es wird wahrscheinlich später Fehler geben.
    CONFIG = None # Signalisiert, dass die Konfiguration fehlt

# Importiere Ladefunktionen für Definitionen (optional hier, je nachdem wann sie gebraucht werden)
# Könnte auch erst innerhalb der Modus-spezifischen Funktionen geladen werden.
try:
    from src.definitions.loader import load_all_definitions
except ImportError:
    logger.error("Fehler beim Importieren von src.definitions.loader. Definitionen können nicht geladen werden.")
    load_all_definitions = None # Signalisiert, dass Ladefunktion fehlt


def run_manual_mode():
    """Führt den manuellen Spielmodus aus (Platzhalter)."""
    logger.info("Starte manuellen Spielmodus...")
    if CONFIG:
        logger.info(f"Minimale Schadenseinstellung: {CONFIG.get('game_settings.min_damage')}")
    
    if load_all_definitions:
        try:
            logger.info("Lade Spieldefinitionen für manuellen Modus...")
            load_all_definitions()
            # Hier könnte man auf geladene Daten zugreifen, z.B. Charakter-Templates
            # from src.definitions.loader import _character_templates
            # if _character_templates:
            #    logger.info(f"{len(_character_templates)} Charakter-Templates geladen.")
        except Exception as e:
            logger.error(f"Fehler beim Laden der Definitionen im manuellen Modus: {e}")
            
    logger.warning("Manuelle Modus Logik ist noch nicht implementiert.")
    # TODO: Implementiere die Logik für den manuellen Modus (z.B. Spieler-Interaktion, Kampf etc.)
    print("\n--- Manueller Modus gestartet (Platzhalter) ---")
    print("Hier würde die Spielerinteraktion stattfinden.")
    print("----------------------------------------------\n")

def run_auto_mode():
    """Führt den automatischen Simulationsmodus aus (Platzhalter)."""
    logger.info("Starte automatischen Simulationsmodus...")
    if CONFIG:
        logger.info(f"XP Level Faktor: {CONFIG.get('game_settings.xp_level_factor')}")

    if load_all_definitions:
        try:
            logger.info("Lade Spieldefinitionen für automatischen Modus...")
            load_all_definitions()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Definitionen im automatischen Modus: {e}")

    logger.warning("Automatischer Modus Logik ist noch nicht implementiert.")
    # TODO: Implementiere die Logik für den automatischen Modus (z.B. Simulationsschleife)
    print("\n--- Automatischer Modus gestartet (Platzhalter) ---")
    print("Hier würde die Simulation automatisch ablaufen (z.B. Kämpfe).")
    # Beispiel: Import der CLI-Schleife und Start
    # try:
    #     from src.ui.cli_main_loop import start_simulation_loop
    #     start_simulation_loop()
    # except ImportError:
    #     logger.error("src.ui.cli_main_loop konnte nicht importiert werden für den Auto-Modus.")
    # except Exception as e:
    #     logger.error(f"Fehler beim Starten der Simulationsschleife: {e}")
    print("-------------------------------------------------\n")

def run_rl_training_mode():
    """Führt den RL-Trainingsmodus aus (Platzhalter)."""
    logger.info("Starte RL-Trainingsmodus...")
    if CONFIG:
        logger.info(f"RL spezifische Einstellungen: {CONFIG.get('rl_settings', 'Nicht konfiguriert')}")
    
    logger.warning("RL-Trainingsmodus Logik ist noch nicht implementiert.")
    # TODO: Implementiere die Logik für das RL-Training
    print("\n--- RL-Trainingsmodus gestartet (Platzhalter) ---")
    print("Hier würde das Training eines RL-Agenten stattfinden.")
    # Beispiel: Import und Aufruf des Trainingsskripts
    # try:
    #     from src.ai.rl_training import train_agent
    #     train_agent()
    # except ImportError:
    #     logger.error("src.ai.rl_training konnte nicht importiert werden.")
    # except Exception as e:
    #     logger.error(f"Fehler beim Starten des RL-Trainings: {e}")
    print("-------------------------------------------------\n")


def main():
    """
    Hauptfunktion, die Kommandozeilenargumente verarbeitet und den
    entsprechenden Betriebsmodus startet.
    """
    parser = argparse.ArgumentParser(description="Textbasiertes RPG-Projekt.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["manual", "auto", "train_rl"],
        default="auto", # Standardmodus, falls nichts angegeben wird
        help="Der Betriebsmodus des Spiels/der Simulation: "
             "'manual' für Spielerinteraktion, "
             "'auto' für automatische Simulation, "
             "'train_rl' für das Training eines RL-Agenten."
    )
    # Hier könnten weitere Argumente hinzugefügt werden, z.B.:
    # parser.add_argument("--level", type=str, help="Startlevel oder Szenario-Name.")
    # parser.add_argument("--config-file", type=str, help="Pfad zu einer alternativen Konfigurationsdatei.")

    args = parser.parse_args()
    
    logger.info(f"RPG-Projekt gestartet. Gewählter Modus: {args.mode}")

    if args.mode == "manual":
        run_manual_mode()
    elif args.mode == "auto":
        run_auto_mode()
    elif args.mode == "train_rl":
        run_rl_training_mode()
    else:
        # Sollte durch choices in argparse eigentlich nicht erreicht werden
        logger.error(f"Ungültiger Modus angegeben: {args.mode}")
        parser.print_help()

if __name__ == "__main__":
    # Dieser Block wird ausgeführt, wenn src/main.py direkt als Skript gestartet wird.
    main()