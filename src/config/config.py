"""
Konfigurationsdatei für das RPG-Projekt.
Hier werden globale Einstellungen und Parameter definiert.
"""

# Verzeichnispfade
BASE_DIR = "python-rpg-projekt"
SRC_DIR = f"{BASE_DIR}/src"
LOGS_DIR = f"{BASE_DIR}/logs"
REPORTS_DIR = f"{BASE_DIR}/reports"
ASSETS_DIR = f"{BASE_DIR}/assets"
TEMPLATES_DIR = f"{SRC_DIR}/ui/templates"
STYLES_DIR = f"{SRC_DIR}/ui/styles"

# JSON-Datenpfade
SKILLS_JSON = f"{SRC_DIR}/definitions/skills.json"
CHARACTERS_JSON = f"{SRC_DIR}/definitions/characters.json"

# Parameter für das Spiel
DEFAULT_PLAYER_HEALTH = 100
DEFAULT_PLAYER_MANA = 50
DEFAULT_EXP_PER_LEVEL = 1000

# Debugging und Logging
DEBUG_MODE = True
LOG_FILE = f"{LOGS_DIR}/debug_logs/rpg_debug.log"

# RL-Training Parameter
RL_ENV_NAME = "RPGEnv-v0"
RL_MODEL_DIR = f"{SRC_DIR}/ai/models"
RL_MAX_EPISODES = 10000
RL_MAX_TIMESTEPS = 200

if __name__ == "__main__":
    # Testet die Konfigurationswerte
    print("Konfigurationswerte erfolgreich geladen:")
    print(f"Basisverzeichnis: {BASE_DIR}")
    print(f"JSON-Daten: {SKILLS_JSON}, {CHARACTERS_JSON}")
