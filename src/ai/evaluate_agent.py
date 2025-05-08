"""
Evaluate RL Agent

Skript zur Evaluierung trainierter RL-Agenten für das RPG-System.
"""
from typing import Dict, Any, Optional
import os
import time
import json

from src.utils.logging_setup import get_logger

# Logger für dieses Modul
logger = get_logger(__name__)

# Standardpfade
DEFAULT_MODEL_DIR = "src/ai/models"
DEFAULT_REPORT_DIR = "reports/rl_evaluation"


class AgentEvaluator:
    """
    Evaluiert trainierte RL-Agenten.
    
    Diese Klasse bietet Funktionen zur detaillierten Evaluierung trainierter
    RL-Agenten und zur Generierung von Berichten über deren Leistung.
    """
    def __init__(self, config_path: str = None):
        """
        Initialisiert den AgentEvaluator mit einer optionalen Konfiguration.
        
        Args:
            config_path (str, optional): Pfad zur Konfigurationsdatei
        """
        # Standardkonfiguration
        self.config = {
            'model_dir': DEFAULT_MODEL_DIR,
            'report_dir': DEFAULT_REPORT_DIR,
            'evaluation_episodes': 50,
            'verbose': 1
        }
        
        # Verzeichnisse erstellen
        os.makedirs(self.config['report_dir'], exist_ok=True)
    
    def evaluate_agent(self, model_path: str, level: int = None) -> Dict[str, Any]:
        """
        Evaluiert einen trainierten Agenten.
        
        Args:
            model_path (str): Pfad zum Modell
            level (int, optional): Das zu verwendende Level
            
        Returns:
            Dict[str, Any]: Die Evaluierungsergebnisse
        """
        # Platzhalter-Implementierung
        logger.info(f"Evaluiere Modell aus {model_path} auf Level {level}")
        time.sleep(1)  # Simulation der Evaluation
        
        # Mock-Ergebnis
        results = {
            'success': True,
            'model_path': model_path,
            'level': level,
            'episodes': self.config['evaluation_episodes'],
            'statistics': {
                'rewards': {
                    'min': 10.0,
                    'max': 50.0,
                    'avg': 30.0,
                    'total': 1500.0
                },
                'outcomes': {
                    'victories': 35,
                    'defeats': 15,
                    'victory_rate': 0.7
                }
            }
        }
        
        return results
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Speichert die Evaluierungsergebnisse in einer Datei.
        
        Args:
            results (Dict[str, Any]): Die zu speichernden Ergebnisse
            filename (Optional[str]): Der Dateiname (ohne Pfad)
            
        Returns:
            str: Der vollständige Pfad zur gespeicherten Datei
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"eval_results_{timestamp}.json"
        
        file_path = os.path.join(self.config['report_dir'], filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Ergebnisse in {file_path} gespeichert")
            return file_path
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Ergebnisse: {e}")
            return ""
