import logging
import logging.handlers
from pathlib import Path
import sys

# Importiere unser Konfigurationsmodul, um auf settings.json5 zuzugreifen
# Wir gehen davon aus, dass dieses Skript als Teil des Pakets 'src' läuft
# oder dass der Python-Pfad so gesetzt ist, dass 'src' gefunden wird.
try:
    from src.config import config
except ModuleNotFoundError:
    # Fallback für den Fall, dass das Skript isoliert getestet wird
    # und 'src' nicht direkt im Pfad ist. Füge das Projektverzeichnis hinzu.
    # Das ist eher ein Workaround für Tests, die Struktur sollte im Betrieb stimmen.
    project_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_dir))
    from src.config import config


def setup_logging():
    """Konfiguriert das Python logging System basierend auf settings.json5."""

    # --- Einstellungen aus der Konfiguration holen ---
    log_level_str = config.get_setting("logging.log_level", "INFO").upper()
    log_to_console = config.get_setting("logging.log_to_console", True)
    log_to_file = config.get_setting("logging.log_to_file", True)
    log_file_rel_path = config.get_setting("logging.log_file", "logs/rpg_game.log")
    log_format_str = config.get_setting("logging.log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_date_format = config.get_setting("logging.log_date_format", "%Y-%m-%d %H:%M:%S")

    # --- Log-Level umwandeln ---
    log_level = getattr(logging, log_level_str, logging.INFO) # Wandelt "INFO" in logging.INFO um, Fallback auf INFO

    # --- Root-Logger konfigurieren ---
    # Wichtig: Beim ersten Mal konfigurieren. Spätere Aufrufe von setup_logging sollten das bedenken.
    # logging.basicConfig() sollte vermieden werden, wenn man Handler manuell hinzufügt.
    root_logger = logging.getLogger()
    # Nur konfigurieren, wenn noch keine Handler gesetzt sind, um doppelte Logs zu vermeiden
    if not root_logger.hasHandlers():
        root_logger.setLevel(log_level) # Setzt das minimale Level für den Logger selbst

        # --- Formatter erstellen ---
        formatter = logging.Formatter(log_format_str, datefmt=log_date_format)

        # --- Konsole-Handler ---
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout) # Explizit sys.stdout verwenden
            console_handler.setFormatter(formatter)
            # Der Handler-Level kann unabhängig vom Root-Level sein (aber nicht niedriger als Root effektiv)
            # Hier setzen wir ihn gleich dem Root-Level
            console_handler.setLevel(log_level)
            root_logger.addHandler(console_handler)
            logging.info("Logging auf Konsole konfiguriert.") # Frühe Log-Nachricht

        # --- Datei-Handler (Rotating) ---
        if log_to_file:
            # Stelle sicher, dass der Pfad relativ zum Projekt-Root ist
            log_file_path = config.PROJECT_ROOT / log_file_rel_path

            try:
                # Erstelle das Log-Verzeichnis, falls es nicht existiert
                log_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Verwende RotatingFileHandler für besseres Log-Management
                # Rotiert, wenn die Datei 10MB erreicht, behält 5 alte Dateien
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(log_level) # Nimmt auch alle Nachrichten ab diesem Level auf
                root_logger.addHandler(file_handler)
                logging.info(f"Logging in Datei konfiguriert: {log_file_path}")
            except Exception as e:
                logging.error(f"Fehler beim Konfigurieren des Datei-Loggings nach {log_file_path}: {e}", exc_info=True)
                # Logge den Fehler zumindest auf der Konsole, falls die vorhanden ist

    else:
         logging.warning("setup_logging() wurde erneut aufgerufen, aber Logger hat bereits Handler. Überspringe Neukonfiguration.")


# --- Testblock ---
if __name__ == '__main__':
    print("--- Logging Setup Test ---")
    print(f"Versuche Logging zu konfigurieren basierend auf: {config.CONFIG_FILE_PATH}")

    # Konfiguration aufrufen
    setup_logging()

    # Beispiel-Logs von verschiedenen Modulen/Loggern
    logger_main = logging.getLogger("main_test")
    logger_utils = logging.getLogger("utils_test")

    print("\nSchreibe Beispiel-Log-Nachrichten...")

    logger_main.debug("Diese Debug-Nachricht sollte nur erscheinen, wenn log_level auf DEBUG steht.")
    logger_main.info("Eine Info-Nachricht vom Haupt-Test.")
    logger_main.warning("Eine Warnung vom Haupt-Test.")
    logger_utils.info("Eine Info-Nachricht vom Utils-Test.")
    logger_utils.error("Ein Fehler ist aufgetreten!", exc_info=False) # exc_info=True würde Traceback hinzufügen

    try:
        x = 1 / 0
    except ZeroDivisionError:
        logger_main.critical("Ein kritischer Fehler mit Traceback!", exc_info=True)

    print("\n--- Test Ende ---")
    print(f"Prüfe die Konsole und die Datei '{config.get_setting('logging.log_file')}' (falls aktiviert).")

