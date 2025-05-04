#!/usr/bin/env python3
"""
Python RPG Projekt - Hauptmodul

Dieses Modul startet das Spiel und dient als Einstiegspunkt.
"""

import os
import sys
import argparse

# Füge das Projektverzeichnis zum Pfad hinzu, damit Module gefunden werden
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def parse_arguments():
    """Verarbeitet Kommandozeilenargumente."""
    parser = argparse.ArgumentParser(description='Python RPG')
    parser.add_argument('--debug', action='store_true', help='Debug-Modus aktivieren')
    return parser.parse_args()

def setup_environment():
    """Richtet die Umgebung für das Spiel ein."""
    # Hier werden später Konfigurationen geladen, Logging eingerichtet etc.
    pass

def main():
    """Hauptfunktion des Spiels."""
    args = parse_arguments()
    setup_environment()
    
    print("=" * 50)
    print("Python RPG Projekt - Willkommen!")
    print("=" * 50)
    print("\nDas Spiel befindet sich im Aufbau.\n")
    
    # Hier wird später die Spiellogik gestartet

if __name__ == "__main__":
    main()
