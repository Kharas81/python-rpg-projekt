# -*- coding: utf-8 -*-
"""rpg_config

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/12k8eGP7IeJPL7uj0Ii4iRqSxa_VAHjma
"""

# Generated/Overwritten on: 2025-04-16 11:20:00 # Zeitpunkt aktualisiert
# rpg_config.py
# V4: Changed SUMMARY_SAVE_DIR to 'Auswertungsberichte'.

import os

# --- Verzeichnispfade ---
BASE_PROJECT_PATH = os.getcwd()
LOG_DIR_BASE = os.path.join(BASE_PROJECT_PATH, "logs/ppo_klassen_lvl_v2/") # Beibehalten oder auch anpassen?
MODEL_DIR_BASE = os.path.join(BASE_PROJECT_PATH, "models/klassen_agenten_lvl_v2/")# Beibehalten oder auch anpassen?
# ******** NEUER NAME HIER ********
SUMMARY_SAVE_DIR = os.path.join(BASE_PROJECT_PATH, "Auswertungsberichte/") # Geändert! Kein _Lvl_2 mehr
# *********************************
NOTEBOOK_NAME = "RPG.ipynb" # Ggf. anpassen

# --- Trainingsparameter ---
TOTAL_TIMESTEPS_PER_CLASS = 50000
LOAD_EXISTING_MODELS = False
CLASSES_TO_TRAIN = ["Krieger", "Magier", "Schurke", "Kleriker"]
DEFAULT_PPO_PARAMS = {
    'policy': "MlpPolicy",
    'learning_rate': 3e-4,
    'n_steps': 2048,
    'batch_size': 64,
    'n_epochs': 10,
    'gamma': 0.99,
    'gae_lambda': 0.95,
    'clip_range': 0.2,
    'ent_coef': 0.0,
    'verbose': 0
}

# --- Evaluierungsparameter ---
N_EVAL_EPISODES = 100 # Wird aktuell nicht direkt von evaluate_agent_and_summarize V13+ genutzt
EVAL_DETERMINISTIC = True
MAX_TURNS = 100 # Max Züge pro Episode (in Env und Eval)

# --- Spiel-Balance / Charakter-Parameter ---
# Werden jetzt primär aus rpg_definitions.py und rpg_game_logic.py bestimmt.

print(f"Konfigurationsdatei rpg_config.py geschrieben/überschrieben (V4 - Ordner umbenannt).")
print(f"  - LOAD_EXISTING_MODELS: {LOAD_EXISTING_MODELS}")
print(f"  - Log Verzeichnis: {LOG_DIR_BASE}")
print(f"  - Modell Verzeichnis: {MODEL_DIR_BASE}")
print(f"  - Bericht Verzeichnis: {SUMMARY_SAVE_DIR}") # Ausgabe des neuen Namens

