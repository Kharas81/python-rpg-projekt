"""
Skript zur Evaluierung von trainierten RL-Agenten.
"""
import os
import sys
import time
import argparse
import json5
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import logging
import matplotlib.pyplot as plt

# Füge das Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Versuche, die RL-Bibliotheken zu importieren
try:
    import gymnasium as gym
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    LIBRARIES_AVAILABLE = True
except ImportError:
    LIBRARIES_AVAILABLE = False
    print("Warning: RL-Bibliotheken nicht verfügbar. Installiere gymnasium, stable-baselines3 und sb3-contrib.")

from src.environment.rpg_env import RPGEnv
from src.config.config import get_config
from src.utils.logging_setup import get_logger

# Der restliche Code bleibt unverändert
