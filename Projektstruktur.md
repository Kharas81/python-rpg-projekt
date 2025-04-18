# Projektstruktur: Python-RPG-Projekt

Dies ist die strukturierte Übersicht des Projekts, basierend auf den definierten Modulen und Ordnern.

## Verzeichnisstruktur

```plaintext
python-rpg-projekt/
│
├── src/                           # Quellcode des Projekts
│   ├── config/                    # Konfigurations- und globale Parameter
│   │   └── config.py              # Globale Einstellungen (z.B. Verzeichnispfade, Parameter)
│   │
│   ├── definitions/               # Definitionen von Spielobjekten und Mechaniken
│   │   ├── skills.json            # JSON-Datei für alle Fähigkeiten (Skills)
│   │   ├── characters.json        # JSON-Datei für Charakterklassen und Basisattribute
│   │   ├── buffs_debuffs.py       # Buffs, Debuffs und zugehörige Konstanten
│   │   ├── resources.py           # Zuordnung von Primärfähigkeiten und Hauptressourcen
│   │   ├── loader.py              # Lädt und validiert JSON-Dateien (Skills, Charaktere)
│   │   └── __init__.py            # Aggregiert alle Definitionen
│   │
│   ├── environment/               # RL-Umgebung und Aktionen
│   │   ├── rpg_env.py             # Gym-basierte RL-Umgebung
│   │   ├── actions.py             # Definition möglicher Aktionen für den Agenten
│   │   └── __init__.py            # Importiert `rpg_env` und `actions`
│   │
│   ├── game_logic/                # Spiel- und Mechaniklogik
│   │   ├── combat.py              # Kampfsystem und Mechanik
│   │   ├── effects.py             # Verwaltung von Effekten (Buffs, Debuffs, DoT/HoT)
│   │   ├── leveling.py            # Logik für Levelaufstiege und XP-Berechnungen
│   │   ├── rpg_game_logic.py      # Hauptlogik für das RPG-System
│   │   └── __init__.py            # Aggregiert alle Submodule der Spielmechanik
│   │
│   ├── ui/                        # Benutzeroberfläche (UI)
│   │   ├── templates/             # HTML-Templates
│   │   │   └── main.html          # Haupt-UI als HTML-Datei
│   │   ├── styles/                # CSS-Dateien
│   │   │   └── styles.css         # Haupt-CSS für die HTML-UI
│   │   ├── ipywidgets/            # Widgets für interaktive UIs
│   │   │   └── rpg_widgets.py     # Logik zur Erstellung von ipywidgets für die UI
│   │   └── generate_ui.py         # Logik zur Generierung der HTML- oder Widget-basierten UI
│   │
│   ├── ai/                        # Geskriptete und RL-basierte KI
│   │   ├── scripted_ai.py         # Geskriptetes Gegnerverhalten
│   │   ├── rl_training.py         # RL-Training (z.B. mit `stable-baselines3`)
│   │   ├── models/                # Gespeicherte RL-Modelle
│   │   └── __init__.py            # Aggregiert KI-Module
│   │
│   ├── training/                  # Trainings- und Evaluierungs-Tools
│   │   ├── callbacks.py           # Eigene Callback-Klassen (z.B. `IPyWidgetProgressCallback`)
│   │   ├── utils.py               # Hilfsfunktionen für Training und Logging
│   │   ├── evaluation.py          # Evaluierung von Agenten und Erstellung von Berichten
│   │   ├── report_generator.py    # Generiert Berichte in TXT, CSV und HTML
│   │   └── __init__.py            # Importiert alle Trainingsmodule
│   │
│   └── main.py                    # Einstiegspunkt des Projekts
│       - Führt das Spiel oder die Trainingslogik aus
│
├── tests/                         # Tests für verschiedene Module
│   ├── test_config.py             # Tests für Konfigurationen
│   ├── test_definitions.py        # Tests für Skills, Charaktere, Buffs/Debuffs
│   ├── test_environment.py        # Tests für RL-Umgebung
│   ├── test_game_logic.py         # Tests für die Spiel- und Mechaniklogik
│   ├── test_ui.py                 # Tests für UI-Logik
│   ├── test_ai.py                 # Tests für KI-Logik
│   ├── test_training.py           # Tests für Trainings- und Logging-Tools
│   └── __init__.py                # Aggregiert alle Tests
│
├── logs/                          # Logging für Training und Debugging
│   ├── training_logs/             # Logs für Trainingsläufe
│   ├── gameplay_logs/             # Logs für Gameplay-Sessions
│   └── debug_logs/                # Debug-Ausgaben (z.B. aus Widgets)
│
├── reports/                       # Auswertungsberichte und Analysen
│   ├── training_reports/          # Berichte pro Trainingslauf (pro Klasse, Datum)
│   │   ├── txt/                   # Berichte im TXT-Format
│   │   ├── csv/                   # Berichte im CSV-Format
│   │   ├── html/                  # Berichte im HTML-Format
│   │   └── README.md              # Übersicht zu den generierten Berichten
│   ├── evaluation_reports/        # Berichte zu Modellbewertung und Performance
│   ├── strategy_analysis/         # Analysen zu Strategie und Mechaniken
│   └── __init__.py                # Aggregiert Berichtslogik (falls benötigt)
│
├── notebooks/                     # Jupyter/Colab-Notebooks für Experimente
│   ├── rl_experiments.ipynb       # Reinforcement Learning Training und Evaluierung
│   └── training_analysis.ipynb    # Analyse von Trainings-Logs und Berichten
│
├── docs/                          # Dokumentation des Projekts
│   ├── ENTSCHEIDUNGEN.md          # Wichtige Projektentscheidungen
│   ├── Projekt_Zusammenfassung.md # Zusammenfassung des Projektstatus
│   ├── examples.md                # Beispielanwendungen und Tutorials
│   └── README.md                  # Übersicht über das Projekt
│
├── assets/                        # Grafiken und sonstige Ressourcen
│   ├── images/                    # Bilder für UI und Spielwelt
│   │   └── ui/                    # UI-spezifische Bilder
│   ├── sounds/                    # Soundeffekte und Musik
│   │   └── effects/               # Soundeffekte für Fähigkeiten und Aktionen
│   └── models/                    # 3D-Modelle oder andere Assets
│
├── tools/                         # Hilfsskripte und Automatisierungen
│   ├── validate_data.py           # Skript zur Validierung von JSON-Daten (Skills, Charaktere)
│   ├── generate_reports.py        # Automatisches Erstellen von Berichten
│   └── clean_assets.py            # Entfernt ungenutzte Ressourcen aus `assets/`
│
└── requirements.txt               # Abhängigkeiten des Projekts
```

---

## Neues Modul: **`src/training/report_generator.py`**

```python
import os
import csv
import datetime

class ReportGenerator:
    def __init__(self, base_dir="reports/training_reports/"):
        self.base_dir = base_dir
        self.date_str = datetime.date.today().strftime('%Y-%m-%d')
        self.txt_dir = os.path.join(self.base_dir, "txt")
        self.csv_dir = os.path.join(self.base_dir, "csv")
        self.html_dir = os.path.join(self.base_dir, "html")
        os.makedirs(self.txt_dir, exist_ok=True)
        os.makedirs(self.csv_dir, exist_ok=True)
        os.makedirs(self.html_dir, exist_ok=True)

    def save_txt(self, report_data, filename="training_report.txt"):
        filepath = os.path.join(self.txt_dir, f"{self.date_str}_{filename}")
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(report_data)
        print(f"TXT-Bericht gespeichert: {filepath}")

    def save_csv(self, report_data, filename="training_report.csv"):
        filepath = os.path.join(self.csv_dir, f"{self.date_str}_{filename}")
        with open(filepath, mode="w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(report_data["headers"])
            writer.writerows(report_data["rows"])
        print(f"CSV-Bericht gespeichert: {filepath}")

    def save_html(self, report_data, filename="training_report.html"):
        filepath = os.path.join(self.html_dir, f"{self.date_str}_{filename}")
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(f"<html><body><h1>Training Report</h1><pre>{report_data}</pre></body></html>")
        print(f"HTML-Bericht gespeichert: {filepath}")
```